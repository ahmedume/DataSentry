"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { models } from "@/lib/api";
import type { ModelOut } from "@/lib/types";

export default function ModelsPage() {
  return (
    <RequireAuth>
      <ModelsInner />
    </RequireAuth>
  );
}

function ModelsInner() {
  const [list, setList] = useState<ModelOut[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setList(await models.registry());
    } catch (e: any) {
      setError(e?.message || "Could not load models.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = stageFilter === "all" ? list : list.filter((m) => m.stage === stageFilter);

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Model Registry</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Trained models
          </h1>
          <p className="section-sub">Browse, filter by stage, and promote models through dev → staging → production.</p>
        </Reveal>

        <div className="tabs" style={{ marginTop: "var(--s-4)" }}>
          {["all", "dev", "staging", "production"].map((s) => (
            <button key={s} className={`tab ${stageFilter === s ? "active" : ""}`} onClick={() => setStageFilter(s)}>
              {s}
            </button>
          ))}
        </div>

        {error && <p className="alert">{error}</p>}
        {busy && list.length === 0 && <div className="loading"><span className="eyebrow">Loading</span><div className="bar" /></div>}

        <div style={{ marginTop: "var(--s-4)", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
          {filtered.length === 0 && !busy && (
            <p className="mono" style={{ color: "var(--ink-muted)" }}>No models in this stage.</p>
          )}
          {filtered.map((m) => (
            <ModelCard key={m.id} model={m} onUpdate={load} expanded={!!expanded[m.id]} onToggle={() => setExpanded((p) => ({ ...p, [m.id]: !p[m.id] }))} />
          ))}
        </div>
      </div>
    </main>
  );
}

function ModelCard({ model, onUpdate, expanded, onToggle }: { model: ModelOut; onUpdate: () => void; expanded: boolean; onToggle: () => void }) {
  const [busy, setBusy] = useState(false);

  async function promote(stage: string) {
    setBusy(true);
    try {
      await models.promote(model.id, stage);
      onUpdate();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  const nextStage = model.stage === "dev" ? "staging" : model.stage === "staging" ? "production" : null;
  const metrics = model.metrics || {};
  const importances = model.feature_importances || {};
  const impEntries = Object.entries(importances).sort((a, b) => b[1] - a[1]);
  const maxImp = Math.max(0.0001, ...impEntries.map(([, v]) => v));

  return (
    <div className="card" style={{ cursor: "pointer" }} onClick={onToggle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--s-2)" }}>
            <span className={`pill ${model.status === "READY" ? "ok" : model.status === "FAILED" ? "issue" : "live"}`}>{model.status}</span>
            <strong style={{ fontFamily: "var(--font-display)" }}>→ {model.target}</strong>
            <span className="meta">{model.task}</span>
            {model.current && <span className="pill ok">current</span>}
          </div>
          <span className="meta mono" style={{ marginTop: 4, display: "block" }}>
            stage: {model.stage || "—"} · created: {model.created_at ? new Date(model.created_at).toLocaleDateString() : "—"}
          </span>
        </div>
        <div style={{ display: "flex", gap: "var(--s-1)", alignItems: "center" }} onClick={(e) => e.stopPropagation()}>
          {nextStage && (
            <MagneticButton variant="solid" strength={0.2} onClick={() => promote(nextStage)} disabled={busy}>
              Promote to {nextStage}
            </MagneticButton>
          )}
          <span className="meta mono">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: "var(--s-3)", borderTop: "1px solid var(--border)", paddingTop: "var(--s-3)" }}>
          {Object.keys(metrics).length > 0 && (
            <div>
              <h4 className="eyebrow" style={{ color: "var(--ink-muted)", marginBottom: "var(--s-2)" }}>Metrics</h4>
              <div className="grid-cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(100px,1fr))" }}>
                {Object.entries(metrics).map(([k, v]) => (
                  <div key={k} className="kpi" style={{ padding: "var(--s-2)" }}>
                    <div className="n" style={{ fontSize: "var(--text-base)" }}>{typeof v === "number" ? v.toFixed(4) : String(v)}</div>
                    <div className="l">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {impEntries.length > 0 && (
            <div style={{ marginTop: "var(--s-3)" }}>
              <h4 className="eyebrow" style={{ color: "var(--ink-muted)", marginBottom: "var(--s-2)" }}>Feature importances</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-1)" }}>
                {impEntries.map(([col, val]) => (
                  <div key={col}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)" }}>
                      <span>{col}</span>
                      <span className="meta mono">{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
                    </div>
                    <div className="bar-track" style={{ marginTop: 2 }}>
                      <div className="bar-fill" style={{ width: `${Math.min(100, (Number(val) / maxImp) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(metrics).length === 0 && impEntries.length === 0 && (
            <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No metrics or feature importances available.</p>
          )}
        </div>
      )}
    </div>
  );
}
