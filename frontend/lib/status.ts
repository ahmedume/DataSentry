/* Normalize the various drift/run status vocabularies across the API into
   three buckets the UI can colour consistently. */
export type DriftBucket = "STABLE" | "WARN" | "DRIFT";

export function normDrift(s?: string | null): DriftBucket {
  if (!s) return "STABLE";
  const u = s.toUpperCase();
  if (u === "STABLE" || u === "OK" || u === "READY" || u === "PASS") return "STABLE";
  if (u === "WARN" || u === "WARNING") return "WARN";
  return "DRIFT"; // DRIFT, ALERT, FAIL, FAILED
}

export function driftClass(s?: string | null): string {
  const b = normDrift(s);
  return b === "STABLE" ? "pill ok" : b === "WARN" ? "pill warn" : "pill issue";
}

export function driftLabel(s?: string | null): string {
  return normDrift(s);
}

export type RunBucket = "RUNNING" | "READY" | "FAILED";

export function normRun(s?: string | null): RunBucket {
  const u = (s || "").toUpperCase();
  if (u === "RUNNING" || u === "QUEUED" || u === "STARTED") return "RUNNING";
  if (u === "FAILED" || u === "FAIL") return "FAILED";
  return "READY";
}

export function runClass(s?: string | null): string {
  const b = normRun(s);
  return b === "READY" ? "pill ok" : b === "RUNNING" ? "pill live" : "pill issue";
}
