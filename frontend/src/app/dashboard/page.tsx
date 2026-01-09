"use client";

import { useEffect, useState } from "react";
import { isAuthenticated, logout } from "@/lib/auth";
import WardLatestTable from "@/components/WardLatestTable";
import WardHistoryChart from "@/components/WardHistoryChart";
import Card from "@/components/Card";

export default function DashboardPage() {
  const [selectedWard, setSelectedWard] = useState(1);
  const [hours, setHours] = useState(24);
  const [checkedAuth, setCheckedAuth] = useState(false);

  useEffect(() => {
    // auth check MUST happen inside useEffect
    if (!isAuthenticated()) {
      window.location.href = "/login";
    } else {
      setCheckedAuth(true);
    }
  }, []);

  // Prevent render until auth is confirmed
  if (!checkedAuth) {
    return <p style={{ padding: 24 }}>Checking authentication…</p>;
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 24 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <h1>Smart City Trash Dashboard</h1>
        <button onClick={logout}>Logout</button>
      </div>

      {/* Latest Table */}
      <Card>
        <h2>Latest Ward Fill Levels</h2>
        <WardLatestTable
          selectedWard={selectedWard}
          onSelectWard={setSelectedWard}
        />
      </Card>

      {/* History */}
      <Card>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <h2>Ward {selectedWard} – History</h2>

          <div>
            {[6, 12, 24].map((h) => (
              <button
                key={h}
                onClick={() => setHours(h)}
                style={{
                  marginLeft: 8,
                  background: hours === h ? "#1d4ed8" : "#2563eb",
                }}
              >
                Last {h}h
              </button>
            ))}
          </div>
        </div>

        <WardHistoryChart wardId={selectedWard} hours={hours} />
      </Card>
    </div>
  );
}
