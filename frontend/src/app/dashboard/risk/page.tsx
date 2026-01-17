"use client";

import { useEffect, useState } from "react";
import RiskTable from "@/components/RiskTable";
import { fetchLatestWardRisk } from "@/lib/api";
import { WardRiskLatest } from "@/types/risk";

export default function RiskDashboardPage() {
  const [data, setData] = useState<WardRiskLatest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const result = await fetchLatestWardRisk();
        setData(result);
      } catch (err) {
        setError("Failed to load risk data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return <div className="p-6">Loading risk data...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-500">{error}</div>;
  }

  if (!data || data.length === 0) {
    return <div className="p-6">No risk data available</div>;
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">🚨 Ward Risk Overview</h1>
      <RiskTable data={data} />
    </div>
  );
}
