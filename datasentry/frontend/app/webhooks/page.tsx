"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { webhooks } from "@/lib/api";
import type { WebhookOut } from "@/lib/types";

const ALL_EVENTS = ["dataset.uploaded", "dataset.profiled", "cleaning.completed", "drift.alert", "training.completed", "monitor.run"];

export default function WebhooksPage() {
  return (
    <RequireAuth>
      <WebhooksInner />
    </RequireAuth>
  );
}

function WebhooksInner() {
  const [list, setList] = useState<WebhookOut[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setList(await webhooks.list());
    } catch (e: any) {
      setError(e?.message || "Could not load webhooks.");
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
          <span className="eyebrow">Webhooks</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Outbound events
          </h1>
          <p className="section-sub">Send HTTP callbacks when datasets are uploaded, profiled, or drift is detected.</p>
        </Reveal>

        <div className="tabs">
          <button className="tab active" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Close" : "+ New webhook"}
          </button>
        </div>

        {showForm && <WebhookForm onCreated={() => { setShowForm(false); load(); }} />}

        {error && <p className="alert">{error}</p>}
        {busy && list.length === 0 && <div className="loading"><span className="eyebrow">Loading</span><div className="bar" /></div>}

        <div style={{ marginTop: "var(--s-4)", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
          {list.length === 0 && !busy && (
            <p className="mono" style={{ color: "var(--ink-muted)" }}>No webhooks yet.</p>
          )}
          {list.map((w) => (
            <WebhookRow key={w.id} wh={w} onChanged={load} />
          ))}
        </div>
      </div>
    </main>
  );
}

function WebhookForm({ onCreated }: { onCreated: () => void }) {
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<string[]>([]);
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function toggleEvent(e: string) {
    setEvents((prev) => (prev.includes(e) ? prev.filter((x) => x !== e) : [...prev, e]));
  }

  async function submit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!url.trim() || events.length === 0) {
      setError("URL and at least one event are required.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await webhooks.create(url.trim(), events, secret.trim() || undefined);
      onCreated();
    } catch (err: any) {
      setError(err?.message || "Failed to create webhook.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit} style={{ marginTop: "var(--s-4)" }}>
      <h3 style={{ marginBottom: "var(--s-3)" }}>New webhook</h3>
      <div className="field">
        <label htmlFor="whurl">URL</label>
        <input id="whurl" className="input" placeholder="https://hooks.example.com/notify" value={url} onChange={(e) => setUrl(e.target.value)} required />
      </div>
      <div className="field">
        <label>Events</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--s-2)" }}>
          {ALL_EVENTS.map((e) => (
            <label key={e} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "var(--text-sm)", cursor: "pointer" }}>
              <input type="checkbox" checked={events.includes(e)} onChange={() => toggleEvent(e)} />
              {e}
            </label>
          ))}
        </div>
      </div>
      <div className="field">
        <label htmlFor="whsecret">Secret (optional — auto-generated if blank)</label>
        <input id="whsecret" className="input" placeholder="leave blank for random" value={secret} onChange={(e) => setSecret(e.target.value)} />
      </div>
      {error && <p className="alert" style={{ marginBottom: "var(--s-2)" }}>{error}</p>}
      <MagneticButton variant="solid" type="submit" strength={0.3}>{busy ? "…" : "Create"}</MagneticButton>
    </form>
  );
}

function WebhookRow({ wh, onChanged }: { wh: WebhookOut; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);

  async function toggle() {
    setBusy(true);
    try {
      await webhooks.toggle(wh.id);
      onChanged();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await webhooks.remove(wh.id);
      onChanged();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="row-item">
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--s-2)" }}>
          <span className={`pill ${wh.active ? "ok" : "issue"}`}>{wh.active ? "active" : "inactive"}</span>
          <span className="meta mono" style={{ wordBreak: "break-all" }}>{wh.url}</span>
        </div>
        <div className="meta" style={{ marginTop: 4 }}>
          Events: {wh.events.join(", ") || "none"}
        </div>
      </div>
      <div className="row-actions">
        <button className="btn" disabled={busy} onClick={toggle}>
          {wh.active ? "Deactivate" : "Activate"}
        </button>
        <button className="btn btn--pop" disabled={busy} onClick={remove}>
          Delete
        </button>
      </div>
    </div>
  );
}
