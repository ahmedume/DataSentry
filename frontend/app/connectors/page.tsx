"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { connectors } from "@/lib/api";
import type { ConnectorOut } from "@/lib/types";

type ConnType = "local" | "postgres" | "s3";

export default function ConnectorsPage() {
  return (
    <RequireAuth>
      <ConnectorsInner />
    </RequireAuth>
  );
}

function ConnectorsInner() {
  const [list, setList] = useState<ConnectorOut[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setList(await connectors.list());
    } catch (e: any) {
      setError(e?.message || "Could not load connectors.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Connectors</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Data sources
          </h1>
          <p className="section-sub">
            Wire local files, Postgres, or S3 buckets. Secrets are redacted on read and never echoed back.
          </p>
        </Reveal>

        <div className="tabs">
          <button className="tab active" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Close" : "+ New connector"}
          </button>
        </div>

        {showForm && (
          <Reveal>
            <ConnectorForm
              onCreated={() => {
                setShowForm(false);
                load();
              }}
            />
          </Reveal>
        )}

        {error && <p className="alert">{error}</p>}
        {busy && list.length === 0 && <div className="loading"><span className="eyebrow">Loading</span><div className="bar" /></div>}

        <div style={{ marginTop: "var(--s-4)" }}>
          {list.length === 0 && !busy && (
            <p className="mono" style={{ color: "var(--ink-muted)" }}>
              No connectors yet. Add one to start ingesting data.
            </p>
          )}
          {list.map((c) => (
            <ConnectorRow key={c.id} conn={c} onChanged={load} />
          ))}
        </div>
      </div>
    </main>
  );
}

function ConnectorForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState<ConnType>("local");
  const [path, setPath] = useState("");
  const [dsn, setDsn] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("5432");
  const [dbname, setDbname] = useState("");
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [bucket, setBucket] = useState("");
  const [key, setKey] = useState("");
  const [secret, setSecret] = useState("");
  const [region, setRegion] = useState("us-east-1");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function buildConfig(): Record<string, unknown> {
    if (type === "local") return { path };
    if (type === "postgres") {
      if (dsn.trim()) return { dsn: dsn.trim() };
      return { host, port: Number(port) || 5432, dbname, user, password };
    }
    return { bucket, key, secret, region };
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await connectors.create(name, type, buildConfig());
      onCreated();
    } catch (err: any) {
      setError(err?.message || "Failed to create connector.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit} style={{ marginTop: 0, marginBottom: "var(--s-4)" }}>
      <h3 style={{ marginBottom: "var(--s-3)" }}>New connector</h3>
      <div className="field">
        <label htmlFor="cname">Name</label>
        <input id="cname" className="input" placeholder="production-db" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>

      <div className="field">
        <label htmlFor="ctype">Type</label>
        <select id="ctype" className="select" value={type} onChange={(e) => setType(e.target.value as ConnType)}>
          <option value="local">Local file</option>
          <option value="postgres">PostgreSQL</option>
          <option value="s3">S3 bucket</option>
        </select>
      </div>

      {type === "local" && (
        <div className="field">
          <label htmlFor="cpath">File path</label>
          <input id="cpath" className="input" placeholder="/data/feed.csv" value={path} onChange={(e) => setPath(e.target.value)} required />
        </div>
      )}

      {type === "postgres" && (
        <>
          <div className="field">
            <label htmlFor="cdsn">DSN (optional — overrides fields below)</label>
            <input id="cdsn" className="input" placeholder="postgresql://user:pass@host:5432/db" value={dsn} onChange={(e) => setDsn(e.target.value)} />
          </div>
          <div className="grid-cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(140px,1fr))" }}>
            <div className="field"><label>Host</label><input className="input" value={host} onChange={(e) => setHost(e.target.value)} /></div>
            <div className="field"><label>Port</label><input className="input" value={port} onChange={(e) => setPort(e.target.value)} /></div>
            <div className="field"><label>Database</label><input className="input" value={dbname} onChange={(e) => setDbname(e.target.value)} /></div>
            <div className="field"><label>User</label><input className="input" value={user} onChange={(e) => setUser(e.target.value)} /></div>
            <div className="field"><label>Password</label><input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          </div>
        </>
      )}

      {type === "s3" && (
        <div className="grid-cards" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px,1fr))" }}>
          <div className="field"><label>Bucket</label><input className="input" value={bucket} onChange={(e) => setBucket(e.target.value)} required /></div>
          <div className="field"><label>Access key</label><input className="input" value={key} onChange={(e) => setKey(e.target.value)} /></div>
          <div className="field"><label>Secret</label><input className="input" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} /></div>
          <div className="field"><label>Region</label><input className="input" value={region} onChange={(e) => setRegion(e.target.value)} /></div>
        </div>
      )}

      {error && <p className="alert" style={{ marginBottom: "var(--s-3)" }}>{error}</p>}
      <MagneticButton variant="solid" type="submit" strength={0.3}>
        {busy ? "Creating…" : "Create connector"}
      </MagneticButton>
    </form>
  );
}

function ConnectorRow({ conn, onChanged }: { conn: ConnectorOut; onChanged: () => void }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>, label: string) {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
    } catch (e: any) {
      setMsg(`${label}: ${e?.message || "error"}`);
    } finally {
      setBusy(false);
    }
  }

  const cfg = conn.config || {};
  const secretKeys = Object.keys(cfg).filter((k) => /pass|secret|key|token|dsn/i.test(k));

  return (
    <div className="row-item">
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--s-2)" }}>
          <span className={`pill ${conn.last_error ? "issue" : "ok"}`}>{conn.type}</span>
          <strong style={{ fontFamily: "var(--font-display)" }}>{conn.name}</strong>
        </div>
        <div className="meta" style={{ marginTop: 6 }}>
          {secretKeys.length > 0
            ? `${Object.keys(cfg).filter((k) => !secretKeys.includes(k)).map((k) => `${k}=${String(cfg[k])}`).join("  ·  ") || "secrets redacted"}`
            : Object.entries(cfg).map(([k, v]) => `${k}=${String(v)}`).join("  ·  ")}
          {conn.last_error && <span className="pop">  ·  last error: {conn.last_error}</span>}
        </div>
        {msg && <div className="meta" style={{ marginTop: 6, color: "var(--accent)" }}>{msg}</div>}
      </div>
      <div className="row-actions">
        <button className="btn" disabled={busy}
          onClick={() => run(async () => {
            const r = await connectors.test(conn.id);
            setMsg(r.ok ? "Connection test OK" : `Test failed: ${r.error || "unknown"}`);
          }, "Test")}>
          Test
        </button>
        <button className="btn" disabled={busy}
          onClick={() => run(async () => {
            const r = await connectors.ingest(conn.id);
            if (r.dataset_id) {
              setMsg(`Ingested → dataset ${r.dataset_id.slice(0, 8)}`);
            } else {
              setMsg(`Ingest queued (${r.status})`);
            }
          }, "Ingest")}>
          Ingest
        </button>
        <button className="btn btn--pop" disabled={busy}
          onClick={() => run(async () => {
            await connectors.remove(conn.id);
            onChanged();
          }, "Delete")}>
          Delete
        </button>
      </div>
    </div>
  );
}
