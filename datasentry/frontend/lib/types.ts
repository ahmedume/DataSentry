export interface DatasetOut {
  id: string;
  original_filename: string;
  status: string;
  row_count: number | null;
  column_count: number | null;
  byte_size: number | null;
  error_message: string | null;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  count: number;
  missing_count: number;
  missing_pct: number;
  high_missing: boolean;
  unique_count: number;
  is_numeric: boolean;
  is_categorical: boolean;
  mean?: number | null;
  std?: number | null;
  min?: number | null;
  q1?: number | null;
  median?: number | null;
  q3?: number | null;
  max?: number | null;
  skew?: number | null;
  outlier_count?: number;
  cardinality?: number;
}

export interface ProfilingOut {
  dataset_id: string;
  row_count: number;
  column_count: number;
  byte_size: number;
  duplicate_row_count: number;
  columns: ColumnProfile[];
}

export interface AiInsightOut {
  dataset_id: string;
  column_explanations: { column: string; explanation: string }[];
  candidate_targets: string[];
  possible_tasks: string[];
  risks_and_assumptions: string[];
  available: boolean;
}

export interface RecommendationOut {
  id: string;
  column_name: string | null;
  issue_type: string;
  stat_reference: string;
  recommendation: string;
  rationale: string;
  accepted: boolean;
}

export interface DiffSummary {
  row_count_before: number;
  row_count_after: number;
  row_count_change: number;
  column_count_before: number;
  column_count_after: number;
  per_column_missing: { column: string; missing_pct_before: number; missing_pct_after: number }[];
}

export interface NumericHistogram {
  column: string;
  bins: number[];
  counts: number[];
  omitted: boolean;
}

export interface CategoricalBars {
  column: string;
  categories: string[];
  counts: number[];
  omitted: boolean;
  reason?: string | null;
}

export interface MissingnessBars {
  columns: string[];
  missing_pct: number[];
}

/* ===================== AUTH (v2) ===================== */
export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface ApiKeyOut {
  id: string;
  key_id: string;
  name: string;
  scopes: string[];
  full_key: string | null;
  active: boolean;
  created_at: string | null;
}

/* ===================== CONNECTORS (v2) ===================== */
export interface ConnectorOut {
  id: string;
  name: string;
  type: "local" | "postgres" | "s3" | string;
  config: Record<string, unknown>;
  enabled: boolean;
  last_tested_at: string | null;
  last_error: string | null;
  created_at: string | null;
}

export interface ConnectorTestResult {
  ok: boolean;
  error: string | null;
}

export interface ConnectorIngestResult {
  dataset_id: string | null;
  status: string;
}

/* ===================== DRIFT (v2) ===================== */
export interface DriftSnapshotOut {
  id: string;
  dataset_id: string;
  label: string;
  row_count: number | null;
  created_at: string | null;
}

export interface DriftColumnResult {
  name: string;
  type: string;
  drift_score: number;
  status: "STABLE" | "WARNING" | "ALERT" | string;
}

export interface DriftComparison {
  id: string;
  baseline_id: string;
  current_id: string;
  status: "STABLE" | "WARNING" | "ALERT" | string;
  results: {
    columns: DriftColumnResult[];
    max_drift: number;
    status: string;
    threshold?: number;
    alert_threshold?: number;
  };
  created_at: string | null;
}

/* ===================== TRAINING (v2) ===================== */
export interface TrainingJobOut {
  id: string;
  dataset_id: string | null;
  connector_id: string | null;
  target: string;
  task: string;
  status: string;
  metrics: Record<string, number> | null;
  feature_importances: Record<string, number> | null;
  model_path: string | null;
  error_message: string | null;
  created_at: string | null;
}

/* ===================== MONITORING (v2) ===================== */
export interface MonitorScheduleOut {
  id: string;
  name: string;
  source_type: "dataset" | "connector" | string;
  source_id: string;
  cadence_minutes: number;
  enabled: boolean;
  baseline_snapshot_id: string | null;
  drift_threshold: number;
  last_run_at: string | null;
}

export interface MonitorRunOut {
  id: string;
  schedule_id: string;
  status: "RUNNING" | "READY" | "FAILED" | string;
  drift_status: "STABLE" | "WARN" | "DRIFT" | null | string;
  rows_processed: number | null;
  drift_summary: {
    columns: DriftColumnResult[];
    max_drift: number;
    status: string;
    threshold?: number;
    alert_threshold?: number;
  } | null;
  snapshot_id: string | null;
  started_at: string | null;
  finished_at: string | null;
}

/* ===================== TEAMS (v3) ===================== */
export interface TeamOut {
  id: string;
  name: string;
  owner_id: string;
  created_at: string | null;
}

export interface TeamMemberOut {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
}

/* ===================== WEBHOOKS (v3) ===================== */
export interface WebhookOut {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  full_secret: string | null;
  created_at: string | null;
}

/* ===================== MODEL REGISTRY (v4) ===================== */
export interface ModelOut {
  id: string;
  target: string;
  task: string;
  status: string;
  stage: string;
  metrics: Record<string, number>;
  feature_importances: Record<string, number>;
  current: boolean;
  created_at: string | null;
}

/* ===================== AUDIT (v4) ===================== */
export interface AuditOut {
  id: string;
  actor_id: string | null;
  team_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  meta: Record<string, unknown>;
  created_at: string | null;
}

/* ===================== USAGE (v4) ===================== */
export interface UsageOut {
  endpoint: string;
  day: string;
  count: number;
}

/* ===================== ANNOTATIONS (v3) ===================== */
export interface AnnotationOut {
  id: string;
  dataset_id: string;
  author_id: string;
  column_name: string | null;
  body: string;
  created_at: string | null;
}

export interface AnnotationCreate {
  body: string;
  column_name?: string | null;
}
