"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthed } from "@/lib/auth";

/* Client-side guard for token-protected app pages. Since the v2 API is
   bearer-only and there is no NextAuth session, we gate on the localStorage
   token and bounce to /login when it's missing. */
export default function RequireAuth({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [ok, setOk] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (isAuthed()) {
      setOk(true);
    } else {
      router.replace("/login");
    }
    setChecked(true);
  }, [router]);

  if (!checked) {
    return (
      <main className="shell">
        <div className="wrap dash">
          <div className="loading">
            <span className="eyebrow">Authenticating</span>
            <h2 className="section-title" style={{ marginTop: "var(--s-3)" }}>
              Checking session…
            </h2>
            <div className="bar" />
          </div>
        </div>
      </main>
    );
  }

  if (!ok) return null;
  return <>{children}</>;
}
