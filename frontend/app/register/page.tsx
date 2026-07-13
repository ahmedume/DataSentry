"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { auth } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      const res = await auth.register(email, password, displayName || undefined);
      setToken(res.access_token);
      router.push("/connectors");
    } catch (err: any) {
      setError(err?.message || "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <Nav />
      <section className="wrap" style={{ padding: "var(--s-7) 0 var(--s-8)", minHeight: "70vh" }}>
        <div className="split">
          <Reveal>
            <span className="eyebrow">Get started</span>
            <h1 className="section-title" style={{ fontSize: "var(--text-2xl)", marginTop: "var(--s-3)" }}>
              Stand up your own <span className="accent">data sentry</span>.
            </h1>
            <p className="section-sub" style={{ maxWidth: "42ch" }}>
              Create an account to wire up connectors, monitor drift, and train models — all on your data.
            </p>
            <p className="meta mono" style={{ marginTop: "var(--s-5)", color: "var(--ink-muted)" }}>
              Already registered?{" "}
              <a href="/login" className="accent" style={{ borderBottom: "1px solid var(--accent)" }}>
                Log in
              </a>
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <form className="panel" onSubmit={submit} style={{ marginTop: 0 }}>
              <h2 className="section-title" style={{ fontSize: "var(--text-xl)" }}>Create account</h2>
              <div className="field" style={{ marginTop: "var(--s-4)" }}>
                <label htmlFor="name">Display name (optional)</label>
                <input
                  id="name"
                  type="text"
                  className="input"
                  placeholder="Ada Lovelace"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoComplete="name"
                />
              </div>
              <div className="field">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  className="input"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  className="input"
                  placeholder="at least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                />
              </div>
              {error && <p className="alert" role="alert">{error}</p>}
              <MagneticButton variant="solid" type="submit" strength={0.3}>
                {busy ? "Creating…" : "Create account"}
              </MagneticButton>
            </form>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
