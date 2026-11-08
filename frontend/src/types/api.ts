export type ProjectStatus = 'active' | 'archived'

export interface ApiErrorDetail {
  code: string
  message: string
  details?: unknown
}

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: ApiErrorDetail | null
  request_id: string | null
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Project {
  id: number
  owner_id: number
  name: string
  description: string | null
  base_url: string
  browser_type: string
  scan_config: Record<string, unknown> | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string | null
  base_url: string
  browser_type?: string
  scan_config?: Record<string, unknown> | null
}

export type ProjectUpdate = Partial<ProjectCreate> & {
  status?: ProjectStatus
}

export interface HealthResponse {
  status: string
  service: string
  version: string
}

export type TaskStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export type TaskType =
  | 'scan'
  | 'explore'
  | 'workflow_analysis'
  | 'case_generation'
  | 'script_generation'
  | 'execution'
  | 'failure_analysis'
  | 'debug'

export interface Task {
  task_id: string
  project_id: number | null
  task_type: TaskType
  status: TaskStatus
  progress: number
  message: string | null
  result: Record<string, unknown> | null
  error: string | null
  cancel_requested: boolean
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface TaskCreated {
  task_id: string
  task_type: TaskType
}

export interface TaskLog {
  level: string
  message: string
  created_at: string
}

export interface PageSummary {
  id: number
  url: string
  title: string | null
  depth: number
  status: string
  http_status: number | null
  source: string
  element_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface PageElement {
  id: number
  element_type: string
  tag: string
  role: string | null
  accessible_name: string | null
  label: string | null
  placeholder: string | null
  text: string | null
  element_id: string | null
  name: string | null
  input_type: string | null
  href: string | null
  selector_candidates: Record<string, unknown> | null
  is_sensitive: boolean
  attributes: Record<string, unknown> | null
}

export interface PageDetail extends PageSummary {
  normalized_url: string
  content_type: string | null
  text_summary: string | null
  screenshot_url: string | null
  dom_url: string | null
  elements: PageElement[]
}

export interface PageRelation {
  id: number
  from_page_id: number
  to_page_id: number | null
  target_url: string | null
  relation_type: string
  source: string
  confidence: number
  evidence: Record<string, unknown> | null
  created_at: string
}

export interface Requirement {
  id: number
  project_id: number
  title: string
  content: string
  related_page_ids: number[] | null
  generation_config: Record<string, unknown> | null
  status: string
  created_by: number | null
  created_at: string
  updated_at: string
}

export interface WorkflowStep {
  step_no: number
  page_id?: number | null
  action: string
  target: string
  value?: string | null
  description?: string | null
}

export interface Workflow {
  id: number
  project_id: number
  requirement_id: number | null
  name: string
  description: string | null
  steps: WorkflowStep[]
  involved_page_ids: number[] | null
  uncertainty: string | null
  status: string
  source: string
  generation_record_id: number | null
  created_at: string
  updated_at: string
}

export interface CaseStep {
  step_no: number
  page_reference?: string | null
  action: string
  target: string
  value?: string | null
  description?: string | null
}

export interface CaseAssertion {
  assertion_type: string
  target: string
  expected: unknown
  source: string
  confidence: number
}

export interface TestCase {
  id: number
  project_id: number
  requirement_id: number | null
  case_code: string
  title: string
  module: string | null
  priority: string
  preconditions: unknown[] | null
  related_page_ids: number[] | null
  steps: CaseStep[]
  test_data: Record<string, unknown> | null
  expected_result: string | null
  assertions: CaseAssertion[]
  assumptions: unknown[] | null
  status: string
  generation_source: string
  generation_record_id: number | null
  created_at: string
  updated_at: string
}

export interface ScriptSummary {
  id: number
  project_id: number
  test_case_id: number
  version: number
  filename: string
  content_hash: string
  status: string
  validation_report: Record<string, unknown> | null
  generation_source: string
  generation_record_id: number | null
  created_at: string
  updated_at: string
}

export interface ScriptDetail extends ScriptSummary {
  content: string
}

export interface Execution {
  id: number
  project_id: number
  task_id: string | null
  status: string
  mode: string
  timeout_seconds: number
  total: number
  passed: number
  failed: number
  skipped: number
  errors: number
  started_at: string | null
  finished_at: string | null
  report_url: string | null
  log_url: string | null
  error_message: string | null
  created_at: string
}

export interface TestResult {
  id: number
  execution_id: number
  script_id: number | null
  test_case_id: number | null
  node_id: string | null
  test_name: string
  status: string
  duration_ms: number | null
  failure_message: string | null
  traceback: string | null
  screenshot_url: string | null
  failure_analysis: Record<string, unknown> | null
  created_at: string
}

export interface LLMConfig {
  project_id: number
  provider: string
  base_url: string | null
  model: string
  configured: boolean
  key_hint: string | null
  temperature: number
  timeout_seconds: number
  max_retries: number
  is_mock: boolean
  updated_at: string | null
}

export interface LLMTestResult {
  ok: boolean
  is_mock: boolean
  provider: string
  model: string
  latency_ms: number
  message: string
}

export interface ExecutionCreated {
  execution_id: number
  task_id: string
}

export interface GenerationRecord {
  id: number
  project_id: number
  task_type: string
  prompt_version: string
  provider: string
  model: string
  is_mock: boolean
  input_summary: string | null
  output_summary: string | null
  prompt_tokens: number | null
  completion_tokens: number | null
  duration_ms: number | null
  status: string
  error: string | null
  created_at: string
}
