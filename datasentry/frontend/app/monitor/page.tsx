"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { datasets, drift, monitors } from "@/lib/api";
import type {
  DatasetOut,
  DriftSnapshotOut,
  DriftComparison,
  MonitorScheduleOut,
  MonitorRunOut,
} from "@/lib/types";
import { driftClass, driftLabel, normDrift, runClass } from "@/lib/status";

export default function MonitorPage() {
  return (
    <RequireAuth>
      <MonitorInner />
    </RequireAuth>
  );
}

function MonitorInner() {
  const [dsets, setDsets] = useState<DatasetOut[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  const loadDatasets = useCallback(async () => {
    try {
      setDsets(await datasets.list());
    } catch {
      /* no auth needed; ignore */
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Monitor</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Drift detection & scheduling
          </h1>
          <p className="section-sub">
            Snapshot a dataset, compare two points in time, and schedule recurring drift checks.
          </p>
        </Reveal>

        <div className="split" style={{ marginTop: "var(--s-4)" }}>
          {/* Dataset picker */}
          <Reveal>
            <div className="panel">
              <h3 style={{ marginBottom: "var(--s-3)" }}>Datasets</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
                {dsets.length === 0 && (
                  <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No datasets.</p>
                )}
                {dsets.map((d) => (
                  <button
                    key={d.id}
                    className={`row-item ${selected === d.id ? "selected" : ""}`}
                    style={{
                      textAlign: "left",
                      cursor: "pointer",
                      borderColor: selected === d.id ? "var(--accent)" : undefined,
                    }}
                    onClick={() => setSelected(d.id)}
                  >
                    <div style={{ minWidth: 0 }}>
                      <strong style={{ fontFamily: "var(--font-display)", display: "block" }}>
                        {d.original_filename}
                      </strong>
                      <span className="meta">{d.row_count?.toLocaleString() ?? "—"} rows · {d.id.slice(0, 8)}</span>
                    </div>
                    {selected === d.id && <span className="dot dot--live" />}
                  </button>
                ))}
              </div>
            </div>
          </Reveal>

          {/* Right: drift + schedules for selected dataset */}
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-5)" }}>
            {selected ? (
              <DriftPanel datasetId={selected} />
            ) : (
              <Reveal>
                <div className="panel">
                  <p className="meta mono" style={{ color: "var(--ink-muted)" }}>
                    Select a dataset to capture snapshots and compare drift.
                  </p>
                </div>
              </Reveal>
            )}
            <SchedulePanel datasetId={selected} />
          </div>
        </div>
      </div>
    </main>
  );
}

/* ---------------- Drift snapshots + compare ---------------- */
function DriftPanel({ datasetId }: { datasetId: string }) {
  const [snaps, setSnaps] = useState<DriftSnapshotOut[]>([]);
  const [comparison, setComparison] = useState<DriftComparison | null>(null);
  const [baseId, setBaseId] = useState<string>("");
  const [currId, setCurrId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const all = await drift.listSnapshots();
      const mine = all.filter((s) => s.dataset_id === datasetId);
      setSnaps(mine);
      if (!baseId && mine.length) setBaseId(mine[0].id);
      if (!currId && mine.length > 1) setCurrId(mine[1].id);
    } catch (e: any) {
      setError(e?.message || "Could not load snapshots.");
    }
  }, [datasetId, baseId, currId]);

  useEffect(() => {
    load();
  }, [load]);

  async function snapshot() {
    setBusy(true);
    setError(null);
    try {
      await drift.createSnapshot(datasetId);
      await load();
    } catch (e: any) {
      setError(e?.message || "Snapshot failed.");
    } finally {
      setBusy(false);
    }
  }

  async function compare() {
    if (!baseId || !currId) return;
    setBusy(true);
    setError(null);
    try {
      setComparison(await drift.compare(baseId, currId));
    } catch (e: any) {
      setError(e?.message || "Comparison failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Reveal>
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--s-2)" }}>
          <h3>Drift snapshots</h3>
          <MagneticButton variant="ghost" onClick={snapshot} strength={0.25}>
            {busy ? "Working…" : "+ Capture snapshot"}
          </MagneticButton>
        </div>
        <p className="muted" style={{ marginBottom: "var(--s-3)" }}>
          A snapshot freezes a statistical fingerprint of the current data.
        </p>

        {snaps.length === 0 && <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No snapshots yet.</p>}
        {snaps.length > 0 && (
          <div className="grid-cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px,1fr))", marginBottom: "var(--s-3)" }}>
            {snaps.map((s) => (
              <div key={s.id} className="kpi">
                <div className="n" style={{ fontSize: "var(--text-lg)" }}>{s.label}</div>
                <div className="l">{s.row_count?.toLocaleString() ?? "?"} rows · {new Date(s.created_at || "").toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        )}

        {snaps.length >= 2 && (
          <div className="field" style={{ marginTop: "var(--s-3)" }}>
            <label>Baseline</label>
            <select className="select" value={baseId} onChange={(e) => setBaseId(e.target.value)}>
              {snaps.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </div>
        )}
        {snaps.length >= 2 && (
          <div className="field">
            <label>Current</label>
            <select className="select" value={currId} onChange={(e) => setCurrId(e.target.value)}>
              {snaps.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </div>
        )}
        {snaps.length >= 2 && (
          <MagneticButton variant="solid" onClick={compare} strength={0.3}>Compare</MagneticButton>
        )}

        {error && <p className="alert" style={{ marginTop: "var(--s-3)" }}>{error}</p>}
        {comparison && <ComparisonView comp={comparison} />}
      </section>
    </Reveal>
  );
}

function ComparisonView({ comp }: { comp: DriftComparison }) {
  const results = comp.results;
  const max = Math.max(0.0001, ...results.columns.map((c) => c.drift_score));
  return (
    <div className="panel" style={{ marginTop: "var(--s-4)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--s-3)", marginBottom: "var(--s-3)" }}>
        <span className={driftClass(results.status)}>{driftLabel(results.status)}</span>
        <span className="meta mono" style={{ color: "var(--ink-muted)" }}>
          max drift {results.max_drift?.toFixed(4)}
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
        {results.columns.map((c) => (
          <div key={c.name}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)" }}>
              <span>{c.name}</span>
              <span className="meta mono">{c.drift_score?.toFixed(4)} · {normDrift(c.status)}</span>
            </div>
            <div className="bar-track" style={{ marginTop: 4 }}>
              <div
                className={`bar-fill ${normDrift(c.status) === "DRIFT" ? "issue" : normDrift(c.status) === "WARN" ? "warn" : ""}`}
                style={{ width: `${Math.min(100, (c.drift_score / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
        {results.columns.length === 0 && (
          <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No comparable columns.</p>
        )}
      </div>
    </div>
  );
}

/* ---------------- Monitor schedules + runs ---------------- */
function SchedulePanel({ datasetId }: { datasetId: string | null }) {
  const [schedules, setSchedules] = useState<MonitorScheduleOut[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSchedules(await monitors.list());
    } catch (e: any) {
      setError(e?.message || "Could not load schedules.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const mine = schedules.filter((s) => !datasetId || s.source_id === datasetId);

  return (
    <Reveal>
      <section className="card">
        <h3>Monitor schedules</h3>
        <p className="muted" style={{ marginBottom: "var(--s-3)" }}>
          Recurring drift checks against a baseline snapshot of a source.
        </p>
        <ScheduleForm datasetId={datasetId} onCreated={load} />
        {error && <p className="alert" style={{ marginTop: "var(--s-3)" }}>{error}</p>}

        <div style={{ marginTop: "var(--s-4)", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
          {mine.length === 0 && <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No schedules for this source yet.</p>}
          {mine.map((s) => (
            <div key={s.id} className="row-item" style={{ flexDirection: "column", alignItems: "stretch" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--s-3)", flexWrap: "wrap" }}>
                <div>
                  <strong style={{ fontFamily: "var(--font-display)" }}>{s.name}</strong>
                  <div className="meta">
                    {s.source_type} · every {s.cadence_minutes}m · threshold {s.drift_threshold}
                    {s.last_run_at && ` · last ${new Date(s.last_run_at).toLocaleString()}`}
                  </div>
                </div>
                <div className="row-actions">
                  <button className="btn" onClick={() => { setExpanded(expanded === s.id ? null : s.id); }}>
                    {expanded === s.id ? "Hide runs" : "Runs"}
                  </button>
                  <button className="btn btn--pop" onClick={async () => { await monitors.remove(s.id); load(); }}>
                    Delete
                  </button>
                </div>
              </div>
              {expanded === s.id && <RunList scheduleId={s.id} />}
            </div>
          ))}
        </div>
      </section>
    </Reveal>
  );
}

function ScheduleForm({ datasetId, onCreated }: { datasetId: string | null; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [cadence, setCadence] = useState("1440");
  const [threshold, setThreshold] = useState("0.2");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!datasetId) {
      setError("Select a dataset first.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await monitors.create({
        name: name || "untitled monitor",
        source_type: "dataset",
        source_id: datasetId,
        cadence_minutes: Number(cadence) || 1440,
        drift_threshold: Number(threshold) || 0.2,
      });
      setName("");
      onCreated();
    } catch (err: any) {
      setError(err?.message || "Could not create schedule.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="panel" style={{ marginTop: 0, marginBottom: "var(--s-3)" }}>
      <div className="grid-cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px,1fr))" }}>
        <div className="field"><label>Name</label><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="daily-check" /></div>
        <div className="field"><label>Cadence (minutes)</label><input className="input" type="number" value={cadence} onChange={(e) => setCadence(e.target.value)} /></div>
        <div className="field"><label>Drift threshold</label><input className="input" type="number" step="0.05" value={threshold} onChange={(e) => setThreshold(e.target.value)} /></div>
      </div>
      {error && <p className="alert" style={{ marginBottom: "var(--s-3)" }}>{error}</p>}
      <MagneticButton variant="solid" type="submit" strength={0.3}>
        {busy ? "Creating…" : "Add schedule"}
      </MagneticButton>
    </form>
  );
}

function RunList({ scheduleId }: { scheduleId: string }) {
  const [runs, setRuns] = useState<MonitorRunOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const load = useCallback(async () => {
    try {
      setRuns(await monitors.runs(scheduleId));
    } catch (e: any) {
      setError(e?.message || "Could not load runs.");
    }
  }, [scheduleId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runNow() {
    setPolling(true);
    setError(null);
    try {
      await monitors.run(scheduleId);
      // poll until the run settles (eager mode completes synchronously)
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 800));
        const list = await monitors.runs(scheduleId);
        setRuns(list);
        const latest = list[0];
        if (latest && (latest.status === "READY" || latest.status === "FAILED")) break;
      }
    } catch (e: any) {
      setError(e?.message || "Run failed.");
    } finally {
      setPolling(false);
    }
  }

  return (
    <div style={{ marginTop: "var(--s-3)" }}>
      <div style={{ display: "flex", gap: "var(--s-2)", alignItems: "center", marginBottom: "var(--s-2)" }}>
        <button className="btn" onClick={runNow} disabled={polling}>{polling ? "Running…" : "Run now"}</button>
        {error && <span className="pop mono" style={{ fontSize: "var(--text-xs)" }}>{error}</span>}
      </div>
      {runs.length === 0 && <p className="meta mono" style={{ color: "var(--ink-muted)" }}>No runs yet.</p>}
      {runs.map((r) => (
        <div key={r.id} className="row-item" style={{ marginBottom: "var(--s-2)" }}>
          <div>
            <div style={{ display: "flex", gap: "var(--s-2)", alignItems: "center" }}>
              <span className={runClass(r.status)}>{r.status}</span>
              {r.drift_status && <span className={driftClass(r.drift_status)}>{driftLabel(r.drift_status)}</span>}
            </div>
            <div className="meta">
              {r.rows_processed != null && `${r.rows_processed.toLocaleString()} rows · `}
              {r.started_at && new Date(r.started_at).toLocaleString()}
            </div>
          </div>
          {r.drift_summary && (
            <div style={{ width: "100%", marginTop: "var(--s-2)" }}>
              <div className="meta mono" style={{ marginBottom: 4 }}>max drift {r.drift_summary.max_drift?.toFixed(4)}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {r.drift_summary.columns.slice(0, 8).map((c) => (
                  <div key={c.name} style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)" }}>
                    <span>{c.name}</span>
                    <span className="meta mono">{c.drift_score?.toFixed(4)} · {normDrift(c.status)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
