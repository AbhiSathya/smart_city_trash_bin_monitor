from fastapi import APIRouter, HTTPException    # type: ignore
from sqlalchemy import text                 # type: ignore
from app.db import engine
from app.models import WardLatest, WardHistory
from typing import List

router = APIRouter(prefix="/wards", tags=["wards"])


@router.get("/latest", response_model=List[WardLatest])
def get_latest_all_wards():
    query = text("""
        SELECT ward, window_start, window_end, avg_fill_level
        FROM ward_latest_fill_level
        ORDER BY ward;
    """)

    with engine.connect() as conn:
        result = conn.execute(query).mappings().all()

    return result


@router.get("/{ward_id}/latest", response_model=WardLatest)
def get_latest_for_ward(ward_id: int):
    query = text("""
        SELECT ward, window_start, window_end, avg_fill_level
        FROM ward_latest_fill_level
        WHERE ward = :ward_id;
    """)

    with engine.connect() as conn:
        row = conn.execute(query, {"ward_id": ward_id}).mappings().first()

    if not row:
        return {
            "ward": ward_id,
            "avg_fill_level": None,
            "window_start": None,
            "window_end": None
        }
    return row


@router.get("/{ward_id}/history", response_model=List[WardHistory])
def get_ward_history(ward_id: int, hours: int = 24, limit: int = 100):
    query = text("""
        SELECT window_end, avg_fill_level
        FROM ward_fill_level_agg
        WHERE ward = :ward_id
          AND window_end >= NOW() - INTERVAL ':hours hours'
        ORDER BY window_end;
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT window_end, avg_fill_level
                FROM ward_fill_level_agg
                WHERE ward = :ward_id
                AND window_end >= NOW() - (:hours || ' hours')::INTERVAL
                ORDER BY window_end DESC
                LIMIT :limit
            """),
            {
                "ward_id": ward_id,
                "hours": hours,
                "limit": limit
            }
        ).mappings().all()


    if not rows:
        return []
    return rows
