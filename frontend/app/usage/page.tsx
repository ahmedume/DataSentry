"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import Reveal from "@/components/Reveal";
import { usage } from "@/lib/api";
import type { UsageOut } from "@/lib/types";

export default function UsagePage() {
  return (
    <RequireAuth>
      <UsageInner />
    </RequireAuth>
  );
}

function UsageInner() {
  const [rows, setRows] = useState<UsageOut[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setRows(await usage.list());
    } catch (e: any) {
      setError(e?.message || "Could not load usage data.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const total = rows.reduce((s, r) => s + r.count, 0);
  const byEndpoint = rows.reduce<Record<string, number>>((acc, r) => {
    acc[r.endpoint] = (acc[r.endpoint] || 0) + r.count;
    return acc;
  }, {});

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">API Usage</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Metering
          </h1>
          <p className="section-sub">Daily API call counts grouped by endpoint.</p>
        </Reveal>

        <Reveal delay={0.05}>
          <div className="grid-cards" style={{ marginTop: "var(--s-4)" }}>
            <div className="kpi"><div className="n">{total.toLocaleString()}</div><div className="l">Total calls</div></div>
            <div className="kpi"><div className="n">{rows.length}</div><div className="l">Records</div></div>
            <div className="kpi"><div className="n">{Object.keys(byEndpoint).length}</div><div className="l">Endpoints used</div></div>
          </div>
        </Reveal>

        {error && <p className="alert">{error}</p>}
        {busy && rows.length === 0 && <div className="loading"><span className="eyebrow">Loading</span><div className="bar" /></div>}

        {rows.length > 0 && (
          <Reveal delay={0.1}>
            <div style={{ marginTop: "var(--s-4)", overflowX: "auto" }}>
              <table className="usage-table" style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                    <th className="mono" style={{ padding: "var(--s-2)", color: "var(--ink-muted)", fontSize: "var(--text-sm)" }}>Endpoint</th>
                    <th className="mono" style={{ padding: "var(--s-2)", color: "var(--ink-muted)", fontSize: "var(--text-sm)" }}>Day</th>
                    <th className="mono" style={{ padding: "var(--s-2)", color: "var(--ink-muted)", fontSize: "var(--text-sm)", textAlign: "right" }}>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "var(--s-2)", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>{r.endpoint}</td>
                      <td style={{ padding: "var(--s-2)", fontSize: "var(--text-sm)" }}>{r.day}</td>
                      <td style={{ padding: "var(--s-2)", textAlign: "right", fontSize: "var(--text-sm)" }}>{r.count.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        )}

        {rows.length === 0 && !busy && (
          <p className="mono" style={{ color: "var(--ink-muted)", marginTop: "var(--s-4)" }}>No usage data yet.</p>
        )}
      </div>
    </main>
  );
}
