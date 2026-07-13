"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import RequireAuth from "@/components/RequireAuth";
import {
  getProfile,
  getInsights,
  triggerInsights,
  getRecommendations,
  triggerRecommendations,
  applyCleaning,
  getCleaningDiff,
  getNumericChart,
  getCategoricalChart,
  getMissingnessChart,
  requestReport,
  getReportStatus,
  downloadWithAuth,
  downloadCleanedUrl,
  downloadReportUrl,
  annotations,
  DatasetOut,
  ProfilingOut,
  AiInsightOut,
  RecommendationOut,
  DiffSummary,
  NumericHistogram,
  CategoricalBars,
  MissingnessBars,
  AnnotationOut,
} from "@/lib/api";
import { useJobPoller } from "@/components/JobStatusPoller";
import MissingValueTable from "@/components/MissingValueTable";
import OutlierTable from "@/components/OutlierTable";
import AIInsightCard from "@/components/AIInsightCard";
import CleaningRecommendationCard from "@/components/CleaningRecommendationCard";
import HistogramChart from "@/components/HistogramChart";
import CategoricalBarChart from "@/components/CategoricalBarChart";
import Reveal from "@/components/Reveal";
import MagneticButton from "@/components/MagneticButton";

type Tab = "overview" | "quality" | "insights" | "cleaning" | "charts" | "report" | "annotations" | "summary";

const TABS: Tab[] = ["overview", "quality", "insights", "cleaning", "charts", "report", "annotations", "summary"];

export default function DatasetDashboard() {
  return (
    <RequireAuth>
      <DatasetInner />
    </RequireAuth>
  );
}

function DatasetInner() {
  const params = useParams();
  const datasetId = String(params.id);
  const { dataset, ready, failed } = useJobPoller(datasetId);

  const [tab, setTab] = useState<Tab>("overview");
  const [profile, setProfile] = useState<ProfilingOut | null>(null);
  const [insights, setInsights] = useState<AiInsightOut | null>(null);
  const [recs, setRecs] = useState<RecommendationOut[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [diff, setDiff] = useState<DiffSummary | null>(null);
  const [cleaningBusy, setCleaningBusy] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      const p = await getProfile(datasetId);
      setProfile(p);
    } catch {
      /* not ready */
    }
  }, [datasetId]);

  useEffect(() => {
    if (ready) loadProfile();
  }, [ready, loadProfile]);

  useEffect(() => {
    if (!ready) return;
    getInsights(datasetId).then(setInsights).catch(() => {});
    getRecommendations(datasetId).then(setRecs).catch(() => {});
  }, [ready, datasetId]);

  const [insightsLoading, setInsightsLoading] = useState(false);
  const [recsLoading, setRecsLoading] = useState(false);

  useEffect(() => {
    if (!ready || tab !== "insights" || insights?.available || insightsLoading) return;
    setInsightsLoading(true);
    triggerInsights(datasetId)
      .then((r) => {
        setInsights(r);
        if (!r.available) {
          const poll = setInterval(async () => {
            try {
              const n = await getInsights(datasetId);
              if (n.available) { setInsights(n); clearInterval(poll); }
            } catch { /* retry */ }
          }, 2000);
        } else {
          setInsights(r);
        }
      })
      .catch(() => {})
      .finally(() => setInsightsLoading(false));
  }, [ready, tab, datasetId, insights, insightsLoading]);

  useEffect(() => {
    if (!ready || tab !== "cleaning" || recs.length > 0 || recsLoading) return;
    setRecsLoading(true);
    triggerRecommendations(datasetId)
      .catch(() => {})
      .finally(() => {
        setRecsLoading(false);
        getRecommendations(datasetId).then(setRecs).catch(() => {});
      });
  }, [ready, tab, datasetId, recs, recsLoading]);

  if (!ready)
    return (
      <main className="shell">
        <div className="wrap dash">
          <div className="loading">
            <span className="eyebrow">Dataset · {datasetId.slice(0, 8)}</span>
            <h2 className="section-title" style={{ marginTop: "var(--s-3)" }}>
              Profiling your dataset…
            </h2>
            <p className="muted" style={{ color: "var(--ink-muted)" }}>
              <span className="dot dot--live" /> Status: {dataset?.status || "QUEUED"}
            </p>
            {failed && <p className="alert" style={{ marginTop: "var(--s-3)" }}>Failed: {dataset?.error_message}</p>}
            <div className="bar" />
          </div>
        </div>
      </main>
    );

  const numericCols = profile?.columns.filter((c) => c.is_numeric) || [];
  const categoricalCols = profile?.columns.filter((c) => c.is_categorical) || [];

  return (
    <main className="shell">
      <nav className="nav wrap" style={{ marginBottom: 0 }}>
        <a href="/" className="brand">
          DATA<b>·</b>SENTRY
        </a>
        <span className="mono" style={{ color: "var(--ink-muted)" }}>
          {dataset?.original_filename || datasetId}
        </span>
      </nav>

      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Dataset intelligence</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            {dataset?.original_filename || "Your dataset"}
          </h1>
        </Reveal>

        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`tab ${tab === t ? "active" : ""}`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "overview" && profile && (
          <div className="tab-content">
            <div className="grid-cards stagger">
              <div className="kpi"><div className="n">{profile.row_count.toLocaleString()}</div><div className="l">Rows</div></div>
              <div className="kpi"><div className="n">{profile.column_count}</div><div className="l">Columns</div></div>
              <div className="kpi"><div className="n">{(profile.byte_size / 1024).toFixed(0)}k</div><div className="l">Size (KB)</div></div>
              <div className="kpi"><div className="n">{profile.duplicate_row_count}</div><div className="l">Duplicate rows</div></div>
            </div>
            <p className="mono" style={{ marginTop: "var(--s-3)", color: "var(--ink-muted)" }}>
              File: {dataset?.original_filename}
            </p>
          </div>
        )}

        {tab === "quality" && profile && (
          <div className="tab-content space-y-4">
            <section className="card">
              <h3>Missing values</h3>
              <MissingValueTable columns={profile.columns} />
            </section>
            <section className="card">
              <h3>Outliers (numeric, IQR)</h3>
              <OutlierTable columns={profile.columns} />
            </section>
          </div>
        )}

        {tab === "insights" && insights && <div className="tab-content"><AIInsightCard insight={insights} /></div>}

        {tab === "cleaning" && (
          <div className="tab-content">
            <CleaningTab
              datasetId={datasetId}
              recs={recs}
              checked={checked}
              setChecked={setChecked}
              cleaningBusy={cleaningBusy}
              onApply={async () => {
                setCleaningBusy(true);
                const ids = Object.keys(checked).filter((k) => checked[k]);
                try {
                  await applyCleaning(datasetId, ids);
                  for (let i = 0; i < 30; i++) {
                    await new Promise((r) => setTimeout(r, 1000));
                    try {
                      const d = await getCleaningDiff(datasetId);
                      setDiff(d);
                      break;
                    } catch {
                      /* still applying */
                    }
                  }
                } finally {
                  setCleaningBusy(false);
                }
              }}
              diff={diff}
            />
          </div>
        )}

        {tab === "charts" && (
          <div className="tab-content">
            <ChartsTab
              datasetId={datasetId}
              numericCols={numericCols.map((c) => c.name)}
              categoricalCols={categoricalCols.map((c) => c.name)}
            />
          </div>
        )}

        {tab === "report" && <div className="tab-content"><ReportTab datasetId={datasetId} /></div>}

        {tab === "annotations" && <div className="tab-content"><AnnotationsTab datasetId={datasetId} /></div>}

        {tab === "summary" && profile && (
          <div className="tab-content">
            <SummaryTab profile={profile} insights={insights} dataset={dataset} />
          </div>
        )}
      </div>
    </main>
  );
}

function CleaningTab({
  datasetId,
  recs,
  checked,
  setChecked,
  onApply,
  cleaningBusy,
  diff,
}: {
  datasetId: string;
  recs: RecommendationOut[];
  checked: Record<string, boolean>;
  setChecked: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  onApply: () => void;
  cleaningBusy: boolean;
  diff: DiffSummary | null;
}) {
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadBusy, setDownloadBusy] = useState(false);

  const toggle = (id: string) => setChecked((c) => ({ ...c, [id]: !c[id] }));
  return (
    <div className="space-y-4">
      <p className="muted" style={{ color: "var(--ink-muted)" }}>
        Select the recommendations to apply (opt-in).
      </p>
      {recs.length === 0 && (
        <p className="rec">
          <span className="dot dot--live" style={{ marginTop: 6 }} />
          <span className="why">No issues detected — nothing to clean.</span>
        </p>
      )}
      {recs.map((r) => (
        <CleaningRecommendationCard key={r.id} rec={r} checked={!!checked[r.id]} onToggle={toggle} />
      ))}
      <MagneticButton variant="solid" onClick={onApply} strength={0.3}>
        {cleaningBusy ? "Applying…" : "Apply cleaning"}
      </MagneticButton>
      {diff && (
        <div className="card">
          <h3>Before / after</h3>
          <p className="muted">
            Rows: {diff.row_count_before} → {diff.row_count_after}{" "}
            ({diff.row_count_change >= 0 ? "+" : ""}{diff.row_count_change})
          </p>
          <p className="muted">Columns: {diff.column_count_before} → {diff.column_count_after}</p>
          {downloadError && <p className="alert" style={{ marginBottom: "var(--s-2)" }}>{downloadError}</p>}
          <MagneticButton
            variant="solid"
            onClick={async () => {
              setDownloadError(null);
              setDownloadBusy(true);
              try {
                await downloadWithAuth(downloadCleanedUrl(datasetId), `${datasetId}_cleaned.csv`);
              } catch (e: any) {
                setDownloadError(e.message || "Download failed");
              } finally {
                setDownloadBusy(false);
              }
            }}
            strength={0.3}
          >
            {downloadBusy ? "Downloading…" : "Download cleaned CSV"}
          </MagneticButton>
        </div>
      )}
    </div>
  );
}

function ChartsTab({ datasetId, numericCols, categoricalCols }: { datasetId: string; numericCols: string[]; categoricalCols: string[] }) {
  const [hist, setHist] = useState<Record<string, NumericHistogram>>({});
  const [cats, setCats] = useState<Record<string, CategoricalBars>>({});
  const [miss, setMiss] = useState<MissingnessBars | null>(null);

  useEffect(() => {
    numericCols.slice(0, 6).forEach((c) =>
      getNumericChart(datasetId, c)
        .then((d) => setHist((h) => ({ ...h, [c]: d })))
        .catch(() => {})
    );
    categoricalCols.slice(0, 6).forEach((c) =>
      getCategoricalChart(datasetId, c)
        .then((d) => setCats((k) => ({ ...k, [c]: d })))
        .catch(() => {})
    );
    getMissingnessChart(datasetId).then(setMiss).catch(() => {});
  }, [datasetId, numericCols, categoricalCols]);

  return (
    <div className="space-y-4">
      {miss && (
        <div className="chart-box">
          <h4>Missingness across columns</h4>
          <CategoricalBarChart
            data={{ column: "missingness", categories: miss.columns, counts: miss.missing_pct.map((p) => Math.round(p * 100)), omitted: false, reason: null }}
          />
        </div>
      )}
      {numericCols.map((c) => hist[c] && <HistogramChart key={c} data={hist[c]} />)}
      {categoricalCols.map((c) => cats[c] && <CategoricalBarChart key={c} data={cats[c]} />)}
    </div>
  );
}

function AnnotationsTab({ datasetId }: { datasetId: string }) {
  const [list, setList] = useState<AnnotationOut[]>([]);
  const [body, setBody] = useState("");
  const [columnName, setColumnName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setList(await annotations.list(datasetId));
    } catch {
      /* ignore */
    }
  }, [datasetId]);

  useEffect(() => {
    load();
  }, [load]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setError(null);
    setBusy(true);
    try {
      await annotations.create(datasetId, { body: body.trim(), column_name: columnName.trim() || null });
      setBody("");
      setColumnName("");
      load();
    } catch (err: any) {
      setError(err?.message || "Failed to add annotation.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form className="panel" onSubmit={add} style={{ marginTop: 0 }}>
        <h3 style={{ marginBottom: "var(--s-3)" }}>Add annotation</h3>
        <div className="field">
          <label htmlFor="anncol">Column (optional)</label>
          <input id="anncol" className="input" placeholder="leave blank for dataset-level" value={columnName} onChange={(e) => setColumnName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="annbody">Note</label>
          <textarea id="annbody" className="input" rows={3} placeholder="What did you notice?" value={body} onChange={(e) => setBody(e.target.value)} required />
        </div>
        {error && <p className="alert" style={{ marginBottom: "var(--s-2)" }}>{error}</p>}
        <MagneticButton variant="solid" type="submit" strength={0.3}>{busy ? "Saving…" : "Save annotation"}</MagneticButton>
      </form>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
        {list.length === 0 && <p className="mono" style={{ color: "var(--ink-muted)" }}>No annotations yet.</p>}
        {list.map((a) => (
          <div key={a.id} className="row-item">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--s-2)" }}>
                {a.column_name && <span className="pill ok">{a.column_name}</span>}
                <span className="meta mono">{a.author_id.slice(0, 8)}</span>
              </div>
              <p style={{ marginTop: 4, whiteSpace: "pre-wrap" }}>{a.body}</p>
              <span className="meta" style={{ fontSize: "var(--text-xs)", color: "var(--ink-muted)" }}>
                {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SummaryTab({ profile, insights, dataset }: { profile: ProfilingOut; insights: AiInsightOut | null; dataset: DatasetOut | null }) {
  const cols = profile.columns || [];
  const numeric = cols.filter((c) => c.is_numeric);
  const cat = cols.filter((c) => c.is_categorical);
  const highMissing = cols.filter((c) => (c.missing_pct || 0) > 0.5);
  const totalMissingCells = cols.reduce((s, c) => s + Math.round((c.missing_pct || 0) * profile.row_count), 0);
  const quality = highMissing.length === 0 && profile.duplicate_row_count === 0 ? "good" : highMissing.length <= 2 ? "fair" : "poor";

  return (
    <div className="space-y-4">
      <Reveal>
        <div className="grid-cards stagger">
          <div className="kpi"><div className="n">{profile.row_count.toLocaleString()}</div><div className="l">Rows</div></div>
          <div className="kpi"><div className="n">{profile.column_count}</div><div className="l">Columns</div></div>
          <div className="kpi"><div className="n">{numeric.length}</div><div className="l">Numeric</div></div>
          <div className="kpi"><div className="n">{cat.length}</div><div className="l">Categorical</div></div>
          <div className="kpi"><div className="n">{(profile.byte_size / 1024).toFixed(0)}k</div><div className="l">Size</div></div>
          <div className="kpi"><div className="n">{profile.duplicate_row_count}</div><div className="l">Duplicates</div></div>
          <div className="kpi"><div className="n">{totalMissingCells.toLocaleString()}</div><div className="l">Missing cells</div></div>
          <div className={`kpi ${quality === "good" ? "" : quality === "fair" ? "warn" : "alert"}`}>
            <div className="n" style={{ textTransform: "capitalize" }}>{quality}</div>
            <div className="l">Data quality</div>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <section className="card">
          <h3>Columns</h3>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Missing %</th>
                  <th>Outliers</th>
                  <th>Cardinality</th>
                  {insights?.available && <th>Explanation</th>}
                </tr>
              </thead>
              <tbody>
                {cols.map((c) => (
                  <tr key={c.name}>
                    <td className="mono">{c.name}</td>
                    <td>{c.is_numeric ? "numeric" : c.is_categorical ? "categorical" : c.dtype || "—"}</td>
                    <td>{(c.missing_pct * 100).toFixed(1)}%</td>
                    <td>{c.outlier_count || 0}</td>
                    <td>{c.cardinality ?? "—"}</td>
                    {insights?.available && (
                      <td className="muted" style={{ fontSize: "var(--text-sm)" }}>
                        {insights.column_explanations.find((e: any) => e.column === c.name)?.explanation || "—"}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </Reveal>

      {insights?.available && insights.risks_and_assumptions.length > 0 && (
        <Reveal>
          <section className="card">
            <h3>Risks & warnings</h3>
            <ul style={{ paddingLeft: "var(--s-3)" }}>
              {insights.risks_and_assumptions.map((r: string, i: number) => (
                <li key={i} className="muted" style={{ marginTop: "var(--s-1)" }}>{r}</li>
              ))}
            </ul>
          </section>
        </Reveal>
      )}
    </div>
  );
}


function ReportTab({ datasetId }: { datasetId: string }) {
  const [status, setStatus] = useState<string>("idle");
  const [err, setErr] = useState<string | null>(null);

  const generate = async () => {
    setStatus("QUEUED");
    setErr(null);
    try {
      await requestReport(datasetId);
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const s = await getReportStatus(datasetId);
        setStatus(s.status);
        if (s.status === "READY") break;
        if (s.status === "FAILED") {
          setErr(s.error_message || "Report generation failed");
          break;
        }
      }
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="space-y-4">
      <MagneticButton variant="solid" onClick={generate} strength={0.3}>
        Generate PDF report
      </MagneticButton>
      <p className="mono" style={{ color: "var(--ink-muted)" }}>Status: {status}</p>
      {err && <p className="alert">{err}</p>}
      {status === "READY" && (
        <MagneticButton variant="solid" onClick={() => downloadWithAuth(downloadReportUrl(datasetId), `${datasetId}_report.pdf`)} strength={0.3}>
          Download report PDF
        </MagneticButton>
      )}
    </div>
  );
}
