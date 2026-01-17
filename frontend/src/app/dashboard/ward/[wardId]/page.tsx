"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function WardRiskHistory() {
  const { wardId } = useParams();
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    fetch(
      `http://localhost:8000/wards/${wardId}/risk/history?hours=24`,
      { credentials: "include" }
    )
      .then((res) => res.json())
      .then(setData);
  }, [wardId]);

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">
        📈 Ward {wardId} — Risk History (24h)
      </h1>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <XAxis dataKey="window_end" />
          <YAxis />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="pct_bins_above_80"
            stroke="#dc2626"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
