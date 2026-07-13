"use client";

import { useRef, useState } from "react";
import { uploadCsv } from "@/lib/api";
import DatasetListPanel from "@/components/DatasetListPanel";

interface UploadResult {
  dataset_id: string;
  status: string;
}

export default function UploadDropzone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [showList, setShowList] = useState(false);

  async function handleFile(file: File) {
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const res = await uploadCsv(file);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        className="upload"
      >
        <h2 style={{ fontSize: "var(--text-lg)", fontWeight: 600, marginBottom: "var(--s-1)" }}>
          Drag &amp; drop a CSV here
        </h2>
        <p>or click to choose a file (max 200MB)</p>
        <span className="mono" style={{ marginTop: "var(--s-3)", display: "inline-block", color: "var(--accent)" }}>
          .csv only
        </span>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>
      {busy && (
        <p className="mono" style={{ color: "var(--accent)", display: "flex", alignItems: "center", gap: "var(--s-2)" }}>
          <span className="dot dot--live" /> Uploading &amp; queuing profiling job…
        </p>
      )}
      {result && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "var(--s-3)",
            flexWrap: "wrap",
          }}
        >
          <p className="mono" style={{ color: "var(--accent)", margin: 0 }}>
            ✓ Uploaded — profiling queued
          </p>
          <button className="btn btn--solid" onClick={() => setShowList((v) => !v)}>
            {showList ? "Hide datasets" : "View datasets"}
          </button>
        </div>
      )}
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {showList && <DatasetListPanel />}
    </div>
  );
}
