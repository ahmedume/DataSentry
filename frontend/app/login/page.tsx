"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import MagneticButton from "@/components/MagneticButton";
import Reveal from "@/components/Reveal";
import { auth } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await auth.login(email, password);
      setToken(res.access_token);
      router.push("/connectors");
    } catch (err: any) {
      setError(err?.message || "Login failed.");
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
            <span className="eyebrow">Access</span>
            <h1 className="section-title" style={{ fontSize: "var(--text-2xl)", marginTop: "var(--s-3)" }}>
              Welcome back to the <span className="accent">lab</span>.
            </h1>
            <p className="section-sub" style={{ maxWidth: "42ch" }}>
              Sign in to manage connectors, schedule drift monitors, and train models on your own data.
            </p>
            <p className="meta mono" style={{ marginTop: "var(--s-5)", color: "var(--ink-muted)" }}>
              No account yet?{" "}
              <a href="/register" className="accent" style={{ borderBottom: "1px solid var(--accent)" }}>
                Create one
              </a>
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <form className="panel" onSubmit={submit} style={{ marginTop: 0 }}>
              <h2 className="section-title" style={{ fontSize: "var(--text-xl)" }}>Log in</h2>
              <div className="field" style={{ marginTop: "var(--s-4)" }}>
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
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>
              {error && <p className="alert" role="alert">{error}</p>}
              <MagneticButton variant="solid" type="submit" strength={0.3}>
                {busy ? "Signing in…" : "Log in"}
              </MagneticButton>
            </form>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
