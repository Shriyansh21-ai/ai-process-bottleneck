/**
 * TypeScript types mirroring the backend Pydantic response schemas.
 *
 * The existing frontend stack is JavaScript + Vite (not TS), which the milestone
 * requires we preserve, so the app source stays `.jsx`. These ambient types give
 * editors/tooling real, `any`-free contracts for every API payload and are
 * referenced from JSDoc (`@typedef import(...)`) in the service layer. They are
 * derived directly from:
 *   - src/schemas/auth.py
 *   - src/schemas/agent_run.py
 *   - src/schemas/agent_observability.py
 *   - src/api/routes/health.py
 */

// ----- Auth -----------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at?: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ----- Agent runs -----------------------------------------------------------

export type RunStatus =
  | "success"
  | "completed"
  | "failed"
  | "planning_failed"
  | "execution_failed"
  | "running"
  | "pending"
  | "approval_required";

export interface AgentRunSummary {
  run_id: number;
  session_id: string;
  user_query: string;
  status: string;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  steps_total?: number | null;
  execution_duration_ms?: number | null;
  retry_count?: number | null;
  confidence?: number | null;
  approved?: boolean | null;
  verification_status?: string | null;
}

export interface AgentRunDetail {
  run_id: number;
  session_id: string;
  user_query: string;
  status: string;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  execution_duration_ms?: number | null;
  plan?: unknown;
  execution_result?: unknown;
  verification_result?: unknown;
  final_response?: string | null;
  steps_total?: number | null;
  steps_success?: number | null;
  steps_failed?: number | null;
  retry_count?: number | null;
  tools_used?: unknown;
  execution_mode?: string | null;
  memory_used?: boolean | null;
  rag_used?: boolean | null;
  confidence?: number | null;
  approved?: boolean | null;
  llm_model?: string | null;
}

export interface AgentRunStep {
  id: number;
  step_id?: number | null;
  tool_name?: string | null;
  status?: string | null;
  execution_time_ms?: number | null;
  retry_count?: number | null;
  input_summary?: string | null;
  output_summary?: string | null;
  error?: string | null;
  created_at?: string | null;
}

export interface AgentRunStatistics {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  running_runs: number;
  pending_runs: number;
  other_runs: number;
  success_rate: number;
  failure_rate: number;
  average_duration_ms?: number | null;
}

export interface PaginatedAgentRuns {
  items: AgentRunSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ----- Observability (admin) ------------------------------------------------

export interface AgentHealthSummary {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  running_runs: number;
  success_rate: number;
  failure_rate: number;
  approval_rate: number;
  average_duration_ms?: number | null;
  average_confidence?: number | null;
  total_steps: number;
  successful_steps: number;
  failed_steps: number;
  total_retries: number;
  health_score: number;
  health_status: "no_data" | "unhealthy" | "degraded" | "healthy" | "excellent";
}

export interface ToolPerformanceSummary {
  tool_name: string;
  execution_count: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  average_duration_ms?: number | null;
  total_retries: number;
}

export interface FailureSummary {
  failure_type: string;
  count: number;
  percentage: number;
}

export interface ExecutionTrendPoint {
  bucket: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  average_duration_ms?: number | null;
  average_confidence?: number | null;
}

export interface AgentObservabilityResponse {
  health: AgentHealthSummary;
  tools: ToolPerformanceSummary[];
  failures: FailureSummary[];
  trends: ExecutionTrendPoint[];
}

// ----- Health ---------------------------------------------------------------

export interface HealthResponse {
  status: string;
  message: string;
}

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  checks: Record<string, string>;
}
