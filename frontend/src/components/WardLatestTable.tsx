"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { WardLatest } from "@/types/ward";

interface Props {
  selectedWard: number;
  onSelectWard: (ward: number) => void;
}

export default function WardLatestTable({ selectedWard, onSelectWard }: Props) {
  const [data, setData] = useState<WardLatest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/wards/latest")
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading latest ward data…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;
  if (data.length === 0) return <p>No ward data available.</p>;

  return (
    <table width="100%" cellPadding={8}>
      <thead style={{ background: "#f1f5f9" }}>
        <tr>
          <th align="left">Ward</th>
          <th align="left">Avg Fill Level (%)</th>
          <th align="left">Window End</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr
            key={row.ward}
            onClick={() => onSelectWard(row.ward)}
            style={{
              cursor: "pointer",
              background: row.ward === selectedWard ? "#e0e7ff" : "transparent",
            }}
          >
            <td>{row.ward}</td>
            <td>{row.avg_fill_level.toFixed(1)}</td>
            <td>{new Date(row.window_end).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
