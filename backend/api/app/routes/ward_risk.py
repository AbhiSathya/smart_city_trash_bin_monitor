from fastapi import APIRouter, Depends      # type: ignore
from sqlalchemy import text                 # type: ignore
from typing import List 
from app.db import engine
from app.models.ward_risk import WardRiskLatest, WardRiskHistory  
from app.auth.dependencies import require_role

router = APIRouter(prefix="/wards", tags=["Ward Risk"])


@router.get("/latest/risk", response_model=List[WardRiskLatest], dependencies=[Depends(require_role(["viewer", "admin"]))])
def get_latest_ward_risk(hours: int = 24, threshold: int = 80):
    query = text("""
        SELECT
            r.ward,
            r.avg_fill_level,
            r.max_fill_level,
            r.min_fill_level,
            COUNT(b.bin_id) AS total_bins,
            r.bins_above_80,
            ROUND(
                (r.bins_above_80::numeric / NULLIF(COUNT(b.bin_id), 0)) * 100,
                2
            ) AS pct_bins_above_80,
            r.window_end
        FROM ward_fill_level_risk_agg r
        JOIN ward_bins b
            ON r.ward = b.ward
        WHERE r.window_end >= NOW() - INTERVAL :hours || ' HOURS'
          AND r.bins_above_80 >= :threshold
        GROUP BY
            r.ward,
            r.avg_fill_level,
            r.max_fill_level,
            r.min_fill_level,
            r.bins_above_80,
            r.window_end
        ORDER BY r.ward;
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"hours": hours, "threshold": threshold}).mappings().all()
    
    return [dict(row) for row in rows]



@router.get("/{ward_id}/risk/history", dependencies=[Depends(require_role(["viewer", "admin"]))])
def get_risk_history(ward_id: int, hours: int = 24):
    query = text("""
        SELECT
            r.ward,
            r.window_end,
            r.avg_fill_level,
            r.max_fill_level,
            r.min_fill_level,
            COUNT(b.bin_id) AS total_bins,
            r.bins_above_80,
            ROUND(
                (r.bins_above_80::numeric / NULLIF(COUNT(b.bin_id), 0)) * 100,
                2
            ) AS pct_bins_above_80
        FROM ward_fill_level_risk_agg r
        JOIN ward_bins b
            ON r.ward = b.ward
        WHERE r.ward = :ward_id
        AND r.window_end >= NOW() - (:hours || ' hours')::INTERVAL
        GROUP BY
            r.ward,
            r.window_end,
            r.avg_fill_level,
            r.max_fill_level,
            r.min_fill_level,
            r.bins_above_80
        ORDER BY r.window_end DESC;
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "ward_id": ward_id,
                "hours": hours
            }
        ).mappings().all()
    return rows



@router.get("/risky", response_model=List[WardRiskLatest], dependencies=[Depends(require_role(["viewer", "admin"]))])
def get_risky_wards():
    query = text("""
        SELECT
            r.ward,
            r.avg_fill_level,
            r.max_fill_level,
            r.min_fill_level,
            COUNT(b.bin_id) AS total_bins,
            r.bins_above_80,
            ROUND(
                (r.bins_above_80::numeric / NULLIF(COUNT(b.bin_id), 0)) * 100,
                2
            ) AS pct_bins_above_80,
            r.window_end
        FROM ward_fill_level_risk_agg r
        JOIN ward_bins b
            ON r.ward = b.ward
        WHERE r.bins_above_80 > 0
          AND r.window_end = (
              SELECT MAX(window_end)
              FROM ward_fill_level_risk_agg r2
              WHERE r2.ward = r.ward
          )
        GROUP BY
            r.ward,
            r.avg_fill_level,
            r.max_fill_level,
            r.min_fill_level,
            r.bins_above_80,
            r.window_end
        ORDER BY r.ward;
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    result = [dict(row) for row in rows]
    return result