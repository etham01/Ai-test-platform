import type {
  ApiResponse,
  Execution,
  ExecutionCreated,
  GenerationRecord,
  HealthResponse,
  LLMConfig,
  LLMTestResult,
  PageDetail,
  PageRelation,
  PageSummary,
  Paginated,
  Project,
  ProjectCreate,
  ProjectUpdate,
  Requirement,
  ScriptDetail,
  ScriptSummary,
  Task,
  TaskCreated,
  TaskLog,
  TestCase,
  TestResult,
  Workflow,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export class ApiError extends Error {
  code: string
  status: number
  details?: unknown

  constructor(message: string, code: string, status: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError('无法连接后端服务，请确认 FastAPI 已启动', 'NETWORK_ERROR', 0)
  }

  const body = await readBody(response)

  if (!response.ok) {
    const envelope = body as Partial<ApiResponse<unknown>> | null
    throw new ApiError(
      envelope?.error?.message ?? `请求失败（HTTP ${response.status}）`,
      envelope?.error?.code ?? 'HTTP_ERROR',
      response.status,
      envelope?.error?.details,
    )
  }

  if (body && typeof body === 'object' && 'success' in body) {
    const envelope = body as ApiResponse<T>
    if (!envelope.success) {
      throw new ApiError(
        envelope.error?.message ?? '请求失败',
        envelope.error?.code ?? 'API_ERROR',
        response.status,
        envelope.error?.details,
      )
    }
    return envelope.data as T
  }

  return body as T
}

export const api = {
  async health(): Promise<HealthResponse> {
    let response: Response
    try {
      response = await fetch('/health')
    } catch {
      throw new ApiError('无法连接后端服务', 'NETWORK_ERROR', 0)
    }
    if (!response.ok) {
      throw new ApiError(`健康检查失败（HTTP ${response.status}）`, 'HEALTH_ERROR', response.status)
    }
    return (await response.json()) as HealthResponse
  },

  listProjects(params: { page?: number; page_size?: number; status?: string } = {}) {
    const query = new URLSearchParams()
    if (params.page) query.set('page', String(params.page))
    if (params.page_size) query.set('page_size', String(params.page_size))
    if (params.status) query.set('status', params.status)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request<Paginated<Project>>(`/projects${suffix}`)
  },

  createProject(payload: ProjectCreate) {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  getProject(projectId: number) {
    return request<Project>(`/projects/${projectId}`)
  },

  updateProject(projectId: number, payload: ProjectUpdate) {
    return request<Project>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  async deleteProject(projectId: number): Promise<void> {
    await request<null>(`/projects/${projectId}`, { method: 'DELETE' })
  },

  getTask(taskId: string) {
    return request<Task>(`/tasks/${taskId}`)
  },

  getTaskLogs(taskId: string) {
    return request<{ items: TaskLog[]; total: number }>(`/tasks/${taskId}/logs`)
  },

  cancelTask(taskId: string) {
    return request<{ task_id: string; status: string; cancel_requested: boolean }>(
      `/tasks/${taskId}/cancel`,
      { method: 'POST' },
    )
  },

  explorePages(projectId: number, payload: Record<string, unknown>) {
    return request<TaskCreated>(`/projects/${projectId}/pages/explore`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listPages(projectId: number, params: { page?: number; page_size?: number } = {}) {
    const query = new URLSearchParams()
    if (params.page) query.set('page', String(params.page))
    if (params.page_size) query.set('page_size', String(params.page_size))
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request<Paginated<PageSummary>>(`/projects/${projectId}/pages${suffix}`)
  },

  getPage(projectId: number, pageId: number) {
    return request<PageDetail>(`/projects/${projectId}/pages/${pageId}`)
  },

  listRelations(projectId: number) {
    return request<{ items: PageRelation[]; total: number }>(
      `/projects/${projectId}/relations`,
    )
  },

  listRequirements(projectId: number) {
    return request<Paginated<Requirement>>(
      `/projects/${projectId}/requirements?page_size=100`,
    )
  },

  createRequirement(
    projectId: number,
    payload: {
      title: string
      content: string
      related_page_ids: number[]
      generation_config?: Record<string, unknown> | null
    },
  ) {
    return request<Requirement>(`/projects/${projectId}/requirements`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateRequirement(requirementId: number, payload: Record<string, unknown>) {
    return request<Requirement>(`/requirements/${requirementId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteRequirement(requirementId: number) {
    return request<null>(`/requirements/${requirementId}`, { method: 'DELETE' })
  },

  analyzeWorkflows(projectId: number, payload: Record<string, unknown>) {
    return request<TaskCreated>(`/projects/${projectId}/workflows/analyze`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listWorkflows(projectId: number) {
    return request<Paginated<Workflow>>(
      `/projects/${projectId}/workflows?page_size=100`,
    )
  },

  getWorkflow(workflowId: number) {
    return request<Workflow>(`/workflows/${workflowId}`)
  },

  updateWorkflow(workflowId: number, payload: Record<string, unknown>) {
    return request<Workflow>(`/workflows/${workflowId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  listTestCases(projectId: number, params: { requirement_id?: number } = {}) {
    const query = new URLSearchParams({ page_size: '100' })
    if (params.requirement_id) query.set('requirement_id', String(params.requirement_id))
    return request<Paginated<TestCase>>(`/projects/${projectId}/test-cases?${query.toString()}`)
  },

  getTestCase(caseId: number) {
    return request<TestCase>(`/test-cases/${caseId}`)
  },

  updateTestCase(caseId: number, payload: Record<string, unknown>) {
    return request<TestCase>(`/test-cases/${caseId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteTestCase(caseId: number) {
    return request<null>(`/test-cases/${caseId}`, { method: 'DELETE' })
  },

  generateCases(projectId: number, payload: Record<string, unknown>) {
    return request<TaskCreated>(`/projects/${projectId}/ai/generate-cases`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listGenerationRecords(projectId: number) {
    return request<GenerationRecord[]>(
      `/projects/${projectId}/ai/generation-records?limit=50`,
    )
  },

  generateScripts(projectId: number, testCaseIds: number[]) {
    return request<TaskCreated>(`/projects/${projectId}/ai/generate-scripts`, {
      method: 'POST',
      body: JSON.stringify({ test_case_ids: testCaseIds }),
    })
  },

  listScripts(projectId: number, params: { test_case_id?: number } = {}) {
    const query = new URLSearchParams({ page_size: '100' })
    if (params.test_case_id) query.set('test_case_id', String(params.test_case_id))
    return request<Paginated<ScriptSummary>>(
      `/projects/${projectId}/test-scripts?${query.toString()}`,
    )
  },

  getScript(scriptId: number) {
    return request<ScriptDetail>(`/test-scripts/${scriptId}`)
  },

  updateScript(scriptId: number, content: string) {
    return request<ScriptDetail>(`/test-scripts/${scriptId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    })
  },

  validateScript(scriptId: number) {
    return request<ScriptDetail>(`/test-scripts/${scriptId}/validate`, {
      method: 'POST',
    })
  },

  createExecution(
    projectId: number,
    payload: { script_ids: number[]; timeout_seconds: number; mode: 'local' | 'docker' },
  ) {
    return request<ExecutionCreated>(`/projects/${projectId}/executions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listExecutions(projectId: number) {
    return request<Paginated<Execution>>(
      `/projects/${projectId}/executions?page_size=100`,
    )
  },

  getExecution(executionId: number) {
    return request<Execution>(`/executions/${executionId}`)
  },

  getExecutionResults(executionId: number) {
    return request<{ items: TestResult[]; total: number }>(
      `/executions/${executionId}/results`,
    )
  },

  cancelExecution(executionId: number) {
    return request<{
      execution_id: number
      task_id: string | null
      status: string
      cancel_requested: boolean
    }>(`/executions/${executionId}/cancel`, { method: 'POST' })
  },

  analyzeFailure(projectId: number, executionId: number, resultId: number) {
    return request<TaskCreated>(`/projects/${projectId}/ai/analyze-failure`, {
      method: 'POST',
      body: JSON.stringify({ execution_id: executionId, result_id: resultId }),
    })
  },

  getLLMConfig(projectId: number) {
    return request<LLMConfig>(`/projects/${projectId}/llm-config`)
  },

  updateLLMConfig(projectId: number, payload: Record<string, unknown>) {
    return request<LLMConfig>(`/projects/${projectId}/llm-config`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  testLLM(projectId: number, payload: Record<string, unknown> = {}) {
    return request<LLMTestResult>(`/projects/${projectId}/llm-config/test`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
