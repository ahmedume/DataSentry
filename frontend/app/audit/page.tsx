"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import Reveal from "@/components/Reveal";
import { audit } from "@/lib/api";
import type { AuditOut } from "@/lib/types";

export default function AuditPage() {
  return (
    <RequireAuth>
      <AuditInner />
    </RequireAuth>
  );
}

function AuditInner() {
  const [rows, setRows] = useState<AuditOut[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState(100);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setRows(await audit.list(limit));
    } catch (e: any) {
      setError(e?.message || "Could not load audit log.");
    } finally {
      setBusy(false);
    }
  }, [limit]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Audit Log</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Immutable event trail
          </h1>
          <p className="section-sub">All significant actions recorded append-only for compliance.</p>
        </Reveal>

        <div style={{ marginTop: "var(--s-3)", display: "flex", gap: "var(--s-2)", alignItems: "center" }}>
          <label className="mono" style={{ fontSize: "var(--text-sm)" }}>Limit:</label>
          <select className="select" value={limit} onChange={(e) => setLimit(Number(e.target.value))} style={{ width: "auto" }}>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </div>

        {error && <p className="alert">{error}</p>}
        {busy && rows.length === 0 && <div className="loading"><span className="eyebrow">Loading</span><div className="bar" /></div>}

        <div style={{ marginTop: "var(--s-4)" }}>
          {rows.length === 0 && !busy && (
            <p className="mono" style={{ color: "var(--ink-muted)" }}>No audit events yet.</p>
          )}
          {rows.map((r) => (
            <div key={r.id} className="row-item" style={{ flexWrap: "wrap" }}>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--s-2)", flexWrap: "wrap" }}>
                  <span className="pill live" style={{ fontSize: "var(--text-xs)" }}>{r.action}</span>
                  <span className="meta mono">
                    actor: {r.actor_id ? r.actor_id.slice(0, 8) : "system"}
                    {r.target_type ? ` · ${r.target_type}: ${r.target_id ? r.target_id.slice(0, 8) : "—"}` : ""}
                  </span>
                </div>
                <div className="meta" style={{ marginTop: 4, color: "var(--ink-muted)", fontSize: "var(--text-xs)" }}>
                  {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                  {Object.keys(r.meta || {}).length > 0 && ` · meta: ${JSON.stringify(r.meta)}`}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
