"use client";

import { motion, useMotionValueEvent, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import CinematicCanvas from "@/components/CinematicCanvas";
import MagneticButton from "@/components/MagneticButton";
import CountUp from "@/components/CountUp";
import Reveal from "@/components/Reveal";
import UploadDropzone from "@/components/UploadDropzone";
import { scrollStore } from "@/lib/scrollStore";

/* One pinned copy block, visible only inside its scroll window [a, b]. */
function Shot({
  p,
  a,
  b,
  children,
  align = "left",
}: {
  p: any;
  a: number;
  b: number;
  children: React.ReactNode;
  align?: "left" | "center";
}) {
  const opacity = useTransform(p, [a - 0.03, a, b, b + 0.03], [0, 1, 1, 0]);
  const y = useTransform(p, [a - 0.03, a, b, b + 0.03], [30, 0, 0, -30]);
  return (
    <motion.div
      className="shot-copy"
      style={{
        opacity,
        y,
        textAlign: align,
        alignItems: align === "center" ? "center" : "flex-start",
      }}
    >
      {children}
    </motion.div>
  );
}

const FEATURES = [
  {
    idx: "01",
    title: "Instant profiling",
    body: "Type inference, null rates, distributions, cardinality and correlation — generated the moment a file lands. No notebooks, no pandas boilerplate.",
    tag: "0 config",
  },
  {
    idx: "02",
    title: "Silent-killer audit",
    body: "We rank missing values, type mismatches, leakage, outliers and drift by the damage they do to your model — not by raw counts.",
    tag: "12 checks",
  },
  {
    idx: "03",
    title: "AI repair plans",
    body: "Plain-English explanations of what's wrong and why, plus a one-click plan: impute, encode, drop, normalize — with a live preview.",
    tag: "anthropic · optional",
  },
  {
    idx: "04",
    title: "Local-first",
    body: "Everything runs on your machine by default. Your data never leaves the box unless you point it at your own storage.",
    tag: "privacy by default",
  },
];

export default function Landing() {
  const cinemaRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: cinemaRef,
    offset: ["start start", "end end"],
  });

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    scrollStore.current = v;
  });

  return (
    <main className="shell">
      <Nav />

      {/* ===================== CINEMATIC SHOT SEQUENCE ===================== */}
      <section id="cinema" ref={cinemaRef} className="cinema">
        <div className="cinema-sticky">
          {/* WebGL canvas (fixed behind copy) */}
          <CinematicCanvas />

          {/* HUD */}
          <span className="corner tl">LIVING SCHEMA // real-time</span>
          <span className="corner br">SCROLL ↓ TO TRAVERSE</span>

          {/* Pinned copy overlays — synced to the same progress */}
          <div className="shot-stack">
            <Shot p={scrollYProgress} a={0.0} b={0.28}>
              <span className="eyebrow">Dataset intelligence</span>
              <motion.h1
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
              >
                Your data has a <span className="accent">story</span>.
                <br /> We read it.
              </motion.h1>
              <motion.p
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.35 }}
              >
                DataSentry profiles, audits, and cleans CSVs — turning the messy
                grid behind your model into a living, inspectable schema.
              </motion.p>
              <div className="hero-cta">
                <MagneticButton variant="solid" href="#upload" strength={0.5}>
                  Upload a CSV
                </MagneticButton>
                <MagneticButton variant="ghost" href="#how" strength={0.3}>
                  See how it works
                </MagneticButton>
              </div>
            </Shot>

            <Shot p={scrollYProgress} a={0.27} b={0.56}>
              <span className="eyebrow">01 — Profile</span>
              <h1 className="sm">
                See every column in <span className="accent">seconds</span>.
              </h1>
              <p>
                Type inference, distributions, cardinality, and correlation —
                auto-generated the moment a file lands. The lattice you see is your
                schema, rendered as a field of living points.
              </p>
            </Shot>

            <Shot p={scrollYProgress} a={0.55} b={0.82}>
              <span className="eyebrow" style={{ color: "var(--accent-pop)" }}>
                02 — Audit
              </span>
              <h1 className="sm">
                Catch the <span className="pop">silent killers</span>.
              </h1>
              <p>
                Missing values, type mismatches, leakage, outliers and drift —
                ranked by the damage they do to your model, not by raw counts.
              </p>
            </Shot>

            <Shot p={scrollYProgress} a={0.8} b={1.0}>
              <span className="eyebrow">03 — Prepare</span>
              <h1 className="sm">
                Ship <span className="accent">clean</span> data.
              </h1>
              <p>
                One-click repair plans: impute, encode, drop, normalize. Preview
                the result before you commit it to the pipeline.
              </p>
              <div className="hero-cta">
                <MagneticButton variant="solid" href="#upload" strength={0.5}>
                  Upload a CSV
                </MagneticButton>
              </div>
            </Shot>
          </div>
        </div>
      </section>

      {/* ===================== HOW / STATS ===================== */}
      <section id="how" className="wrap" style={{ padding: "var(--s-7) 0" }}>
        <Reveal>
          <span className="eyebrow">How it works</span>
          <h2 className="section-title">Three moves from raw to ready</h2>
          <p className="section-sub">
            No pipelines to wire. Drop a file, read the story, act on it.
          </p>
        </Reveal>
        <div className="statgrid" style={{ marginTop: "var(--s-4)" }}>
          <div className="stat">
            <div className="n">
              <CountUp to={2} suffix="s" />
            </div>
            <div className="l">Median profile time</div>
          </div>
          <div className="stat">
            <div className="n">
              <CountUp to={12} />
            </div>
            <div className="l">Quality checks / dataset</div>
          </div>
          <div className="stat">
            <div className="n">
              <CountUp to={0} suffix="%" />
            </div>
            <div className="l">Data sent to the cloud</div>
          </div>
          <div className="stat">
            <div className="n">
              <CountUp to={1} />
            </div>
            <div className="l">Click to a clean file</div>
          </div>
        </div>
      </section>

      {/* ===================== CAPABILITIES ===================== */}
      <section id="features" className="wrap features">
        {FEATURES.map((f, i) => (
          <Reveal key={f.idx} delay={i * 0.04}>
            <div className="frow">
              <div className="idx">{f.idx}</div>
              <div>
                <h3>{f.title}</h3>
                <span className="tag">{f.tag}</span>
              </div>
              <p>{f.body}</p>
            </div>
          </Reveal>
        ))}
      </section>

      {/* ===================== UPLOAD ===================== */}
      <section id="upload" className="wrap" style={{ padding: "var(--s-6) 0 var(--s-7)" }}>
        <Reveal>
          <span className="eyebrow">03 — Prepare</span>
          <h2 className="section-title">Drop a CSV and watch it come alive</h2>
          <p className="section-sub" style={{ maxWidth: "60ch" }}>
            Try it with any tabular file up to 200MB. Profiling runs locally and
            starts the moment the upload finishes.
          </p>
        </Reveal>
        <Reveal delay={0.1}>
          <div className="panel" style={{ marginTop: "var(--s-4)" }}>
            <UploadDropzone />
          </div>
        </Reveal>
      </section>

      <Footer />
    </main>
  );
}
