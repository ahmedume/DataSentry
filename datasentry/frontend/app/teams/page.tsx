"use client";

import { useCallback, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import RequireAuth from "@/components/RequireAuth";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { teams } from "@/lib/api";
import type { TeamOut, TeamMemberOut } from "@/lib/types";

export default function TeamsPage() {
  return (
    <RequireAuth>
      <TeamsInner />
    </RequireAuth>
  );
}

function TeamsInner() {
  const [list, setList] = useState<TeamOut[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [members, setMembers] = useState<Record<string, TeamMemberOut[]>>({});

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setList(await teams.list());
    } catch (e: any) {
      setError(e?.message || "Could not load teams.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleExpand = async (teamId: string) => {
    if (expanded[teamId]) {
      setExpanded((p) => ({ ...p, [teamId]: false }));
      return;
    }
    setExpanded((p) => ({ ...p, [teamId]: true }));
    try {
      const m = await teams.listMembers(teamId);
      setMembers((p) => ({ ...p, [teamId]: m }));
    } catch {
      /* ignore */
    }
  };

  return (
    <main className="shell">
      <Nav />
      <div className="wrap dash">
        <Reveal>
          <span className="eyebrow">Teams</span>
          <h1 className="section-title" style={{ fontSize: "var(--text-2xl)" }}>
            Collaboration
          </h1>
          <p className="section-sub">Create teams, invite members, and manage roles.</p>
        </Reveal>

        <CreateTeamForm onCreated={load} />

        {error && <p className="alert">{error}</p>}
        {busy && list.length === 0 && <div className="loading"><span className="eyebrow">Loading</span><div className="bar" /></div>}

        <div style={{ marginTop: "var(--s-4)", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
          {list.length === 0 && !busy && (
            <p className="mono" style={{ color: "var(--ink-muted)" }}>No teams yet. Create one above.</p>
          )}
          {list.map((t) => (
            <div key={t.id} className="card" style={{ cursor: "pointer" }} onClick={() => toggleExpand(t.id)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontFamily: "var(--font-display)" }}>{t.name}</strong>
                  <span className="meta" style={{ marginLeft: "var(--s-2)" }}>owner: {t.owner_id.slice(0, 8)}</span>
                </div>
                <span className="meta mono">{expanded[t.id] ? "▲" : "▼"}</span>
              </div>
              {expanded[t.id] && (
                <TeamDetail teamId={t.id} members={members[t.id] || []} onUpdate={load} />
              )}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

function CreateTeamForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    setBusy(true);
    try {
      await teams.create(name.trim());
      setName("");
      onCreated();
    } catch (err: any) {
      setError(err?.message || "Failed to create team.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit} style={{ marginTop: "var(--s-4)" }}>
      <div style={{ display: "flex", gap: "var(--s-2)", alignItems: "flex-end" }}>
        <div className="field" style={{ flex: 1, margin: 0 }}>
          <label htmlFor="tname">Team name</label>
          <input id="tname" className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. data-science" required />
        </div>
        <MagneticButton variant="solid" type="submit" strength={0.3}>{busy ? "…" : "Create"}</MagneticButton>
      </div>
      {error && <p className="alert" style={{ marginTop: "var(--s-2)" }}>{error}</p>}
    </form>
  );
}

function TeamDetail({ teamId, members, onUpdate }: { teamId: string; members: TeamMemberOut[]; onUpdate: () => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function addMember(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setError(null);
    setBusy(true);
    try {
      await teams.addMember(teamId, email.trim(), role);
      setEmail("");
      onUpdate();
    } catch (err: any) {
      setError(err?.message || "Failed to add member.");
    } finally {
      setBusy(false);
    }
  }

  const changeRole = async (userId: string, newRole: string) => {
    try {
      await teams.updateMemberRole(teamId, userId, newRole);
      onUpdate();
    } catch (err: any) {
      setError(err?.message || "Failed to update role.");
    }
  };

  const removeMember = async (userId: string) => {
    try {
      await teams.removeMember(teamId, userId);
      onUpdate();
    } catch (err: any) {
      setError(err?.message || "Failed to remove member.");
    }
  };

  return (
    <div style={{ marginTop: "var(--s-3)", borderTop: "1px solid var(--border)", paddingTop: "var(--s-3)" }}>
      <form onSubmit={addMember} style={{ display: "flex", gap: "var(--s-2)", marginBottom: "var(--s-3)" }}>
        <input className="input" placeholder="email@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ flex: 1 }} />
        <select className="select" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="viewer">viewer</option>
          <option value="member">member</option>
          <option value="admin">admin</option>
        </select>
        <MagneticButton variant="solid" type="submit" strength={0.2}>{busy ? "…" : "Add"}</MagneticButton>
      </form>
      {error && <p className="alert" style={{ marginBottom: "var(--s-2)" }}>{error}</p>}
      {members.map((m) => (
        <div key={m.user_id} className="row-item" style={{ marginBottom: "var(--s-1)" }}>
          <div>
            <strong style={{ fontFamily: "var(--font-display)" }}>{m.display_name || m.email}</strong>
            <span className="meta" style={{ marginLeft: "var(--s-2)" }}>{m.email} · {m.role}</span>
          </div>
          <div className="row-actions">
            {m.role !== "owner" && (
              <>
                <select className="select" value={m.role} onChange={(e) => changeRole(m.user_id, e.target.value)} style={{ width: "auto", padding: "2px 8px", fontSize: "var(--text-sm)" }}>
                  <option value="viewer">viewer</option>
                  <option value="member">member</option>
                  <option value="admin">admin</option>
                </select>
                <button className="btn btn--pop" onClick={() => removeMember(m.user_id)}>Remove</button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
