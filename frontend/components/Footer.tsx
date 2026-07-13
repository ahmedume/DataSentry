export default function Footer() {
  return (
    <footer className="site wrap">
      <span className="brand" style={{ fontSize: "var(--text-sm)" }}>
        DATA<b>·</b>SENTRY
      </span>
      <span className="mono">v1.0 — CSV quality &amp; preparation · local-first</span>
      <span className="mono">© {new Date().getFullYear()} — built for clean data</span>
    </footer>
  );
}
