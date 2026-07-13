"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";

export default function MagneticButton({
  children,
  onClick,
  href,
  variant = "solid",
  className = "",
  strength = 0.4,
  type = "button",
  disabled = false,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: "solid" | "ghost" | "pop";
  className?: string;
  strength?: number;
  type?: "button" | "submit";
  disabled?: boolean;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, { stiffness: 200, damping: 18 });
  const y = useSpring(my, { stiffness: 200, damping: 18 });
  const glowX = useTransform(mx, (v) => `${50 + v * 8}%`);
  const glowY = useTransform(my, (v) => `${50 + v * 8}%`);

  function move(e: React.MouseEvent) {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    mx.set(((e.clientX - r.left) / r.width - 0.5) * strength * 40);
    my.set(((e.clientY - r.top) / r.height - 0.5) * strength * 40);
  }
  function leave() {
    mx.set(0);
    my.set(0);
  }

  const cls =
    "btn " +
    (variant === "solid" ? "btn--solid" : variant === "pop" ? "btn--pop" : "") +
    " " +
    className;

  const inner = (
    <motion.span
      style={{ x, y, background: `radial-gradient(120px circle at ${glowX} ${glowY}, rgba(255,255,255,0.18), transparent 60%)` }}
      className="mag-inner"
    >
      {children}
    </motion.span>
  );

  if (href) {
    return (
      <a ref={ref as any} href={href} className={cls} onMouseMove={move} onMouseLeave={leave}
         style={{ display: "inline-flex", borderRadius: "var(--r-btn)" }}>
        {inner}
      </a>
    );
  }
  return (
    <button ref={ref} className={cls} onClick={onClick} onMouseMove={move} onMouseLeave={leave}
      type={type} disabled={disabled}
      style={{ display: "inline-flex", borderRadius: "var(--r-btn)" }}>
      {inner}
    </button>
  );
}
