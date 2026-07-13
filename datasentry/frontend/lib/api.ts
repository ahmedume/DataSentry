import type {
  DatasetOut,
  ProfilingOut,
  ColumnProfile,
  AiInsightOut,
  RecommendationOut,
  DiffSummary,
  NumericHistogram,
  CategoricalBars,
  MissingnessBars,
  UserOut,
  TokenResponse,
  ApiKeyOut,
  ConnectorOut,
  ConnectorTestResult,
  ConnectorIngestResult,
  DriftSnapshotOut,
  DriftComparison,
  TrainingJobOut,
  MonitorScheduleOut,
  MonitorRunOut,
  TeamOut,
  TeamMemberOut,
  WebhookOut,
  ModelOut,
  AuditOut,
  UsageOut,
  AnnotationOut,
  AnnotationCreate,
} from "./types";
import { getToken } from "./auth";

export type {
  DatasetOut,
  ProfilingOut,
  ColumnProfile,
  AiInsightOut,
  RecommendationOut,
  DiffSummary,
  NumericHistogram,
  CategoricalBars,
  MissingnessBars,
  UserOut,
  TokenResponse,
  ApiKeyOut,
  ConnectorOut,
  ConnectorTestResult,
  ConnectorIngestResult,
  DriftSnapshotOut,
  DriftComparison,
  TrainingJobOut,
  MonitorScheduleOut,
  MonitorRunOut,
  TeamOut,
  TeamMemberOut,
  WebhookOut,
  ModelOut,
  AuditOut,
  UsageOut,
  AnnotationOut,
  AnnotationCreate,
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...(init?.headers || {}), "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail: any = null;
    try {
      detail = await res.json();
    } catch {
      /* ignore */
    }
    const message = detail?.message || detail?.detail || res.statusText;
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Authenticated wrapper — attaches `Authorization: Bearer <token>` from localStorage. */
async function httpAuth<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return http<T>(path, { ...init, headers });
}

export const uploadCsv = async (file: File): Promise<{ dataset_id: string; status: string }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/datasets/upload`, { method: "POST", body: form });
  if (!res.ok) {
    let detail: any = null;
    try {
      detail = await res.json();
    } catch {
      /* ignore */
    }
    throw new Error(detail?.message || "Upload failed");
  }
  return res.json();
};

export const getDataset = (id: string) => httpAuth<DatasetOut>(`/api/v1/datasets/${id}`);
export const getProfile = (id: string) => httpAuth<ProfilingOut>(`/api/v1/datasets/${id}/profile`);
export const getInsights = (id: string) => httpAuth<AiInsightOut>(`/api/v1/datasets/${id}/insights`);
export const triggerInsights = (id: string) =>
  httpAuth<AiInsightOut>(`/api/v1/datasets/${id}/insights`, { method: "POST" });
export const getRecommendations = (id: string) => httpAuth<RecommendationOut[]>(`/api/v1/datasets/${id}/recommendations`);
export const triggerRecommendations = (id: string) =>
  httpAuth<{ dataset_id: string; status: string }>(`/api/v1/datasets/${id}/recommendations`, { method: "POST" });
export const applyCleaning = (id: string, accepted: string[]) =>
  httpAuth<{ dataset_id: string; cleaning_available: boolean; cleaned_exists: boolean }>(
    `/api/v1/datasets/${id}/cleaning/apply`,
    { method: "POST", body: JSON.stringify({ accepted_recommendation_ids: accepted }) }
  );
export const getCleaningDiff = (id: string) => httpAuth<DiffSummary>(`/api/v1/datasets/${id}/cleaning/diff`);
export const getNumericChart = (id: string, col: string) =>
  httpAuth<NumericHistogram>(`/api/v1/datasets/${id}/charts/numeric/${encodeURIComponent(col)}`);
export const getCategoricalChart = (id: string, col: string) =>
  httpAuth<CategoricalBars>(`/api/v1/datasets/${id}/charts/categorical/${encodeURIComponent(col)}`);
export const getMissingnessChart = (id: string) =>
  httpAuth<MissingnessBars>(`/api/v1/datasets/${id}/charts/missingness`);
export const requestReport = (id: string) =>
  httpAuth<{ dataset_id: string; status: string; download_ready: boolean }>(`/api/v1/datasets/${id}/report`, {
    method: "POST",
  });
export const getReportStatus = (id: string) =>
  httpAuth<{ dataset_id: string; status: string; error_message?: string; download_ready: boolean }>(
    `/api/v1/datasets/${id}/report/status`
  );
export const downloadCleanedUrl = (id: string) => `${API_BASE}/api/v1/datasets/${id}/download/cleaned`;
export const downloadReportUrl = (id: string) => `${API_BASE}/api/v1/datasets/${id}/report/download`;

export async function downloadWithAuth(url: string, filename: string) {
  const token = getToken();
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ===================== AUTH (v2) ===================== */
export const auth = {
  register: (email: string, password: string, display_name?: string) =>
    httpAuth<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    }),
  login: (email: string, password: string) =>
    httpAuth<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => httpAuth<UserOut>("/api/v1/auth/me"),
  listApiKeys: () => httpAuth<ApiKeyOut[]>("/api/v1/auth/api-keys"),
  createApiKey: (name: string, scopes: string[]) =>
    httpAuth<ApiKeyOut>("/api/v1/auth/api-keys", {
      method: "POST",
      body: JSON.stringify({ name, scopes }),
    }),
  deleteApiKey: (keyId: string) =>
    httpAuth<void>(`/api/v1/auth/api-keys/${encodeURIComponent(keyId)}`, { method: "DELETE" }),
};

/* ===================== CONNECTORS (v2) ===================== */
export const connectors = {
  list: () => httpAuth<ConnectorOut[]>("/api/v1/connectors"),
  create: (name: string, type: string, config: Record<string, unknown>) =>
    httpAuth<ConnectorOut>("/api/v1/connectors", {
      method: "POST",
      body: JSON.stringify({ name, type, config }),
    }),
  get: (id: string) => httpAuth<ConnectorOut>(`/api/v1/connectors/${id}`),
  remove: (id: string) => httpAuth<void>(`/api/v1/connectors/${id}`, { method: "DELETE" }),
  test: (id: string) =>
    httpAuth<ConnectorTestResult>(`/api/v1/connectors/${id}/test`, { method: "POST" }),
  ingest: (id: string) =>
    httpAuth<ConnectorIngestResult>(`/api/v1/connectors/${id}/ingest`, { method: "POST" }),
};

/* ===================== DRIFT (v2) ===================== */
export const drift = {
  createSnapshot: (datasetId: string, label?: string) =>
    httpAuth<DriftSnapshotOut>(
      `/api/v1/drift/snapshots?dataset_id=${encodeURIComponent(datasetId)}`,
      { method: "POST", body: JSON.stringify({ label }) }
    ),
  listSnapshots: () => httpAuth<DriftSnapshotOut[]>("/api/v1/drift/snapshots"),
  compare: (baselineId: string, currentId: string) =>
    httpAuth<DriftComparison>("/api/v1/drift/compare", {
      method: "POST",
      body: JSON.stringify({ baseline_id: baselineId, current_id: currentId }),
    }),
  compareDataset: (snapshotId: string, datasetId: string) =>
    httpAuth<DriftComparison>("/api/v1/drift/compare-dataset", {
      method: "POST",
      body: JSON.stringify({ snapshot_id: snapshotId, dataset_id: datasetId }),
    }),
};

/* ===================== TRAINING (v2) ===================== */
export const training = {
  start: (body: {
    target: string;
    task?: string;
    source_type: "dataset" | "connector";
    source_id: string;
    algorithm?: string;
  }) =>
    httpAuth<TrainingJobOut>("/api/v1/training", { method: "POST", body: JSON.stringify(body) }),
  list: () => httpAuth<TrainingJobOut[]>("/api/v1/training"),
  get: (id: string) => httpAuth<TrainingJobOut>(`/api/v1/training/${id}`),
};

/* ===================== MONITORING (v2) ===================== */
export const monitors = {
  list: () => httpAuth<MonitorScheduleOut[]>("/api/v1/monitors"),
  create: (body: {
    name: string;
    source_type: "dataset" | "connector";
    source_id: string;
    cadence_minutes: number;
    baseline_snapshot_id?: string;
    drift_threshold?: number;
  }) => httpAuth<MonitorScheduleOut>("/api/v1/monitors", { method: "POST", body: JSON.stringify(body) }),
  get: (id: string) => httpAuth<MonitorScheduleOut>(`/api/v1/monitors/${id}`),
  remove: (id: string) => httpAuth<void>(`/api/v1/monitors/${id}`, { method: "DELETE" }),
  run: (id: string) => httpAuth<MonitorRunOut>(`/api/v1/monitors/${id}/run`, { method: "POST" }),
  runs: (id: string) => httpAuth<MonitorRunOut[]>(`/api/v1/monitors/${id}/runs`),
};

/* ===================== DATASETS (v1, no auth) ===================== */
export const datasets = {
  list: () => http<DatasetOut[]>("/api/v1/datasets"),
  get: (id: string) => http<DatasetOut>(`/api/v1/datasets/${id}`),
};

/* ===================== TEAMS (v3) ===================== */
export const teams = {
  list: () => httpAuth<TeamOut[]>("/api/v1/teams"),
  create: (name: string) =>
    httpAuth<TeamOut>("/api/v1/teams", { method: "POST", body: JSON.stringify({ name }) }),
  listMembers: (teamId: string) => httpAuth<TeamMemberOut[]>(`/api/v1/teams/${teamId}/members`),
  addMember: (teamId: string, email: string, role: string) =>
    httpAuth<TeamMemberOut>(`/api/v1/teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),
  updateMemberRole: (teamId: string, userId: string, role: string) =>
    httpAuth<TeamMemberOut>(`/api/v1/teams/${teamId}/members/${userId}`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),
  removeMember: (teamId: string, userId: string) =>
    httpAuth<void>(`/api/v1/teams/${teamId}/members/${userId}`, { method: "DELETE" }),
  leave: (teamId: string) =>
    httpAuth<void>(`/api/v1/teams/${teamId}/leave`, { method: "POST" }),
  deleteTeam: (teamId: string) =>
    httpAuth<void>(`/api/v1/teams/${teamId}`, { method: "DELETE" }),
};

/* ===================== WEBHOOKS (v3) ===================== */
export const webhooks = {
  list: () => httpAuth<WebhookOut[]>("/api/v1/webhooks"),
  create: (url: string, events: string[], secret?: string) =>
    httpAuth<WebhookOut>("/api/v1/webhooks", {
      method: "POST",
      body: JSON.stringify({ url, events, secret }),
    }),
  toggle: (id: string) => httpAuth<WebhookOut>(`/api/v1/webhooks/${id}/toggle`, { method: "POST" }),
  remove: (id: string) => httpAuth<void>(`/api/v1/webhooks/${id}`, { method: "DELETE" }),
};

/* ===================== MODEL REGISTRY (v4) ===================== */
export const models = {
  registry: () => httpAuth<ModelOut[]>("/api/v1/models/registry"),
  list: () => httpAuth<ModelOut[]>("/api/v1/models"),
  get: (id: string) => httpAuth<ModelOut>(`/api/v1/models/${id}`),
  promote: (id: string, stage: string) =>
    httpAuth<ModelOut>(`/api/v1/models/${id}/promote`, {
      method: "POST",
      body: JSON.stringify({ stage }),
    }),
};

/* ===================== AUDIT (v4) ===================== */
export const audit = {
  list: (limit = 100) => httpAuth<AuditOut[]>(`/api/v1/audit?limit=${limit}`),
};

/* ===================== USAGE (v4) ===================== */
export const usage = {
  list: () => httpAuth<UsageOut[]>("/api/v1/usage"),
};

/* ===================== ANNOTATIONS (v3) ===================== */
export const annotations = {
  list: (datasetId: string) => httpAuth<AnnotationOut[]>(`/api/v1/datasets/${datasetId}/annotations`),
  create: (datasetId: string, body: AnnotationCreate) =>
    httpAuth<AnnotationOut>(`/api/v1/datasets/${datasetId}/annotations`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
