"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { datasets, connectors, training } from "@/lib/api";
import type { DatasetOut, ConnectorOut, TrainingJobOut } from "@/lib/types";

export default function TrainingPage() {
  return (
    <RequireAuth>
      <TrainingInner />
    </RequireAuth>
  );
}

function TrainingInner() {
  const [jobs, setJobs] = useState<TrainingJobOut[]>([]);
  const [selected, setSelected] = useState<TrainingJobOut | null>(null);

  const load = useCallback(async () => {
    try {
      setJobs(await training.list());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Poll the selected job until it settles.
  useEffect(() => {
    if (!selected) return;
    if (selected.status === "READY" || selected.status === "FAILED") return;
    const t = setInterval(async () => {
      const j = await training.get(selected.id).catch(() => null);
      if (j) {
        setSelected(j);
        setJobs((prev) => prev.map((p) => (p.id === j.id ? j : p)));
        if (j.status === "READY" || j.status === "FAILED") clearInterval(t);
      }
    }, 1500);
    return () => clearInterval(t);
  }, [selected]);

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Train</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Model training
          </h1>
          <p className="section-sub">
            Start a supervised job on a dataset or connector, then inspect metrics and feature importances.
          </p>
        </Reveal>

        <div className="split" style={{ marginTop: "var(--s-4)" }}>
          <Reveal>
            <TrainingForm onStarted={async (id) => { await load(); const j = await training.get(id); setSelected(j); }} />
            <div style={{ marginTop: "var(--s-5)" }}>
              <h3 style={{ marginBottom: "var(--s-3)" }}>Jobs</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
                {jobs.length === 0 && <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No jobs yet.</p>}
                {jobs.map((j) => (
                  <button
                    key={j.id}
                    className="row-item"
                    style={{ textAlign: "left", cursor: "pointer", borderColor: selected?.id === j.id ? "var(--accent)" : undefined }}
                    onClick={() => setSelected(j)}
                  >
                    <div>
                      <strong style={{ fontFamily: "var(--font-display)", display: "block" }}>→ {j.target}</strong>
                      <span className="meta">{j.task} · {j.status}</span>
                    </div>
                    <span className={`pill ${j.status === "READY" ? "ok" : j.status === "FAILED" ? "issue" : "live"}`}>{j.status}</span>
                  </button>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            {selected ? <JobDetail job={selected} /> : (
              <div className="panel">
                <p className="meta mono" style={{ color: "var(--ink-muted)" }}>Start a job or pick one from the list to see results.</p>
              </div>
            )}
          </Reveal>
        </div>
      </div>
    </main>
  );
}

function TrainingForm({ onStarted }: { onStarted: (id: string) => void }) {
  const [sourceType, setSourceType] = useState<"dataset" | "connector">("dataset");
  const [dsets, setDsets] = useState<DatasetOut[]>([]);
  const [conns, setConns] = useState<ConnectorOut[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [target, setTarget] = useState("");
  const [task, setTask] = useState("auto");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    datasets.list().then(setDsets).catch(() => {});
    connectors.list().then(setConns).catch(() => {});
  }, []);

  const opts = sourceType === "dataset" ? dsets : conns;
  const label = sourceType === "dataset" ? "Dataset" : "Connector";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!sourceId || !target) {
      setError("Pick a source and enter a target column.");
      return;
    }
    setBusy(true);
    try {
      const job = await training.start({ source_type: sourceType, source_id: sourceId, target, task });
      onStarted(job.id);
    } catch (err: any) {
      setError(err?.message || "Training failed to start.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit} style={{ marginTop: 0 }}>
      <h3 style={{ marginBottom: "var(--s-3)" }}>Start a job</h3>
      <div className="field">
        <label>Source type</label>
        <select className="select" value={sourceType} onChange={(e) => { setSourceType(e.target.value as any); setSourceId(""); }}>
          <option value="dataset">Dataset</option>
          <option value="connector">Connector</option>
        </select>
      </div>
      <div className="field">
        <label>{label}</label>
        <select className="select" value={sourceId} onChange={(e) => setSourceId(e.target.value)} required>
          <option value="">— select —</option>
          {opts.map((o) => <option key={o.id} value={o.id}>{"original_filename" in o ? o.original_filename : o.name}</option>)}
        </select>
      </div>
      <div className="field">
        <label>Target column</label>
        <input className="input" placeholder="e.g. churn" value={target} onChange={(e) => setTarget(e.target.value)} required />
      </div>
      <div className="field">
        <label>Task</label>
        <select className="select" value={task} onChange={(e) => setTask(e.target.value)}>
          <option value="auto">auto</option>
          <option value="classification">classification</option>
          <option value="regression">regression</option>
        </select>
      </div>
      {error && <p className="alert" style={{ marginBottom: "var(--s-3)" }}>{error}</p>}
      <MagneticButton variant="solid" type="submit" strength={0.3}>
        {busy ? "Starting…" : "Train model"}
      </MagneticButton>
    </form>
  );
}

function JobDetail({ job }: { job: TrainingJobOut }) {
  const metrics = job.metrics || {};
  const metricEntries = Object.entries(metrics);
  const importances = job.feature_importances || {};
  const impEntries = Object.entries(importances).sort((a, b) => b[1] - a[1]);
  const maxImp = Math.max(0.0001, ...impEntries.map(([, v]) => v));

  return (
    <div className="panel" style={{ marginTop: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--s-2)" }}>
        <h3 style={{ margin: 0 }}>→ {job.target}</h3>
        <span className={`pill ${job.status === "READY" ? "ok" : job.status === "FAILED" ? "issue" : "live"}`}>{job.status}</span>
      </div>
      <p className="meta mono" style={{ color: "var(--ink-muted)", marginTop: 6 }}>
        {job.task} · {job.dataset_id ? "dataset" : job.connector_id ? "connector" : "—"} source
      </p>

      {job.status === "QUEUED" || job.status === "RUNNING" || job.status === "TRAINING" ? (
        <div className="loading" style={{ marginTop: "var(--s-3)", padding: "var(--s-5)" }}>
          <span className="eyebrow">Training</span>
          <p className="muted" style={{ marginTop: 8 }}>Job in progress — results will appear automatically.</p>
          <div className="bar" />
        </div>
      ) : null}

      {job.status === "FAILED" && (
        <p className="alert" style={{ marginTop: "var(--s-3)" }}>{job.error_message || "Training failed."}</p>
      )}

      {job.status === "READY" && (
        <>
          {metricEntries.length > 0 && (
            <div style={{ marginTop: "var(--s-4)" }}>
              <h4 className="eyebrow" style={{ color: "var(--ink-muted)" }}>Metrics</h4>
              <div className="grid-cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(120px,1fr))", marginTop: "var(--s-2)" }}>
                {metricEntries.map(([k, v]) => (
                  <div key={k} className="kpi">
                    <div className="n" style={{ fontSize: "var(--text-lg)" }}>{typeof v === "number" ? v.toFixed(4) : String(v)}</div>
                    <div className="l">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {impEntries.length > 0 && (
            <div style={{ marginTop: "var(--s-4)" }}>
              <h4 className="eyebrow" style={{ color: "var(--ink-muted)" }}>Feature importances</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)", marginTop: "var(--s-2)" }}>
                {impEntries.map(([col, val]) => (
                  <div key={col}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)" }}>
                      <span>{col}</span>
                      <span className="meta mono">{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
                    </div>
                    <div className="bar-track" style={{ marginTop: 4 }}>
                      <div className="bar-fill" style={{ width: `${Math.min(100, (Number(val) / maxImp) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {metricEntries.length === 0 && impEntries.length === 0 && (
            <p className="meta mono" style={{ color: "var(--ink-muted)", marginTop: "var(--s-3)" }}>
              Job finished but produced no metrics or importances.
            </p>
          )}
        </>
      )}
    </div>
  );
}
