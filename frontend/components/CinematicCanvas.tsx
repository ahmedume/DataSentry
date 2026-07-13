"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const LivingSchema = dynamic(() => import("./LivingSchema"), { ssr: false });

function StaticPoster() {
  // CSS-only fallback — thematically on-brand, zero GPU, accessible.
  return (
    <div className="poster" aria-hidden="true">
      <div className="poster-grid" />
      <div className="poster-core" />
      <style>{`
        .poster { position:absolute; inset:0; background:#0a0e14; overflow:hidden; }
        .poster-grid {
          position:absolute; inset:-20%; opacity:.5;
          background-image:
            radial-gradient(closest-side, rgba(0,229,160,.18), transparent 70%),
            linear-gradient(rgba(29,37,48,.6) 1px, transparent 1px),
            linear-gradient(90deg, rgba(29,37,48,.6) 1px, transparent 1px);
          background-size: 60% 60%, 38px 38px, 38px 38px;
          background-position: center, center, center;
          animation: drift 18s linear infinite alternate;
        }
        .poster-core {
          position:absolute; left:50%; top:50%; width:140px; height:140px;
          transform:translate(-50%,-50%); border-radius:50%;
          background: radial-gradient(circle at 35% 30%, #2bffba, #00e5a0 40%, rgba(0,229,160,0) 70%);
          box-shadow: 0 0 80px rgba(0,229,160,.45);
        }
        @keyframes drift { from { transform: translateY(0) } to { transform: translateY(-6%) } }
      `}</style>
    </div>
  );
}

export default function CinematicCanvas() {
  const [mode, setMode] = useState<"loading" | "3d" | "static">("loading");

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const coarse = window.matchMedia("(pointer: coarse)").matches;
    const cores = navigator.hardwareConcurrency || 4;
    const lowTier = coarse || cores <= 4;
    // 3D for capable desktops; static poster for reduced-motion / low-end.
    if (reduce) setMode("static");
    else setMode(lowTier ? "static" : "3d");
  }, []);

  if (mode === "static") return <StaticPoster />;
  if (mode === "loading") return null;
  return <LivingSchema quality={1} />;
}
