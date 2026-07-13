"use client";

import { datasets } from "@/lib/api";
import type { DatasetOut } from "@/lib/types";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

function fmtSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function statusPill(status: string) {
  const s = status.toLowerCase();
  if (s === "ready" || s === "completed") return "pill ok";
  if (s === "failed" || s === "error") return "pill issue";
  if (s === "processing" || s === "profiling") return "pill warn";
  return "pill live";
}

export default function DatasetListPanel() {
  const [list, setList] = useState<DatasetOut[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await datasets.list();
      setList(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  if (loading) {
    return (
      <div className="panel" style={{ marginTop: "var(--s-3)" }}>
        <p className="mono" style={{ textAlign: "center", padding: "var(--s-4) 0" }}>
          Loading datasets…
        </p>
      </div>
    );
  }

  if (list.length === 0) {
    return (
      <div className="panel" style={{ marginTop: "var(--s-3)" }}>
        <p className="mono" style={{ textAlign: "center", padding: "var(--s-4) 0" }}>
          No datasets uploaded yet.
        </p>
      </div>
    );
  }

  return (
    <div className="panel" style={{ marginTop: "var(--s-3)", overflowX: "auto" }}>
      <table className="data">
        <thead>
          <tr>
            <th>Filename</th>
            <th>Status</th>
            <th style={{ textAlign: "right" }}>Rows</th>
            <th style={{ textAlign: "right" }}>Columns</th>
            <th style={{ textAlign: "right" }}>Size</th>
          </tr>
        </thead>
        <tbody>
          {list.map((d) => (
            <tr key={d.id}>
              <td>
                <Link
                  href={`/datasets/${d.id}`}
                  style={{ color: "var(--accent)", textDecoration: "none" }}
                >
                  {d.original_filename}
                </Link>
              </td>
              <td>
                <span className={statusPill(d.status)}>{d.status}</span>
              </td>
              <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>
                {d.row_count?.toLocaleString() ?? "—"}
              </td>
              <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>
                {d.column_count?.toLocaleString() ?? "—"}
              </td>
              <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>
                {fmtSize(d.byte_size)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
