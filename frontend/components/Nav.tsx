"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MagneticButton from "./MagneticButton";
import { clearToken, isAuthed } from "@/lib/auth";

export default function Nav() {
  const router = useRouter();
  const [authed, setAuthed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setAuthed(isAuthed());
    setMounted(true);
  }, []);

  function logout() {
    clearToken();
    setAuthed(false);
    router.push("/");
  }

  return (
    <nav className="nav wrap">
      <a href="/" className="brand">
        DATA<b>·</b>SENTRY
      </a>
      <div className="nav-links">
        {mounted && authed ? (
          <>
            <a href="/" className="nav-link">Home</a>
            <a href="/datasets" className="nav-link">Datasets</a>
            <a href="/connectors" className="nav-link">Connectors</a>
            <a href="/monitor" className="nav-link">Monitor</a>
            <a href="/training" className="nav-link">Train</a>
            <a href="/teams" className="nav-link">Teams</a>
            <a href="/webhooks" className="nav-link">Webhooks</a>
            <a href="/models" className="nav-link">Models</a>
            <a href="/audit" className="nav-link">Audit</a>
            <a href="/usage" className="nav-link">Usage</a>
            <MagneticButton variant="ghost" onClick={logout} strength={0.3}>
              Log out
            </MagneticButton>
          </>
        ) : (
          <>
            <a href="/login" className="nav-link">Log in</a>
            <MagneticButton variant="solid" href="/register" strength={0.4}>
              Sign up
            </MagneticButton>
          </>
        )}
      </div>
    </nav>
  );
}
