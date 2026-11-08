<script setup lang="ts">
import { AlertTriangle, ArrowLeft, FileText, RefreshCw, Sparkles, Square, Terminal } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Modal from '@/components/ui/Modal.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import { useTaskPolling } from '@/composables/useTaskPolling'
import type { Execution, TestResult } from '@/types/api'

interface InferredCause {
  cause: string
  evidence: string
  confidence: number
}

interface FailureAnalysis {
  observed_error?: string
  inferred_causes?: InferredCause[]
  suggestions?: string[]
  needs_more_info?: boolean
  provider?: string
  model?: string
  is_mock?: boolean
}

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const executionId = computed(() => Number(route.params.executionId))
const execution = ref<Execution | null>(null)
const results = ref<TestResult[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const selectedResult = ref<TestResult | null>(null)
const executionPoll = useTaskPolling()
const analysisPoll = useTaskPolling()
const { task: executionTask, error: executionTaskError, start: startExecutionPolling } = executionPoll
const { task: analysisTask, error: analysisTaskError, start: startAnalysisPolling } = analysisPoll

const analysis = computed(() => (selectedResult.value?.failure_analysis as FailureAnalysis | null) || null)
const isActive = computed(() => !!execution.value && ['pending', 'running'].includes(execution.value.status))

async function load() {
  loading.value = true
  error.value = null
  try {
    const [exec, result] = await Promise.all([
      api.getExecution(executionId.value),
      api.getExecutionResults(executionId.value),
    ])
    execution.value = exec
    results.value = result.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '执行详情加载失败'
  } finally {
    loading.value = false
  }
}

async function refreshAfterRun() {
  await load()
}

async function beginExecutionPoll() {
  const taskId = execution.value?.task_id
  if (taskId && isActive.value) {
    await startExecutionPolling(taskId, refreshAfterRun)
  }
}

async function cancelExecution() {
  try {
    await api.cancelExecution(executionId.value)
    notice.value = '已请求取消，runner 会在下一次检查时终止进程树'
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '取消失败'
  }
}

async function analyze(result: TestResult) {
  selectedResult.value = result
  if (result.failure_analysis) return
  try {
    const created = await api.analyzeFailure(projectId.value, executionId.value, result.id)
    await startAnalysisPolling(created.task_id, async () => {
      const refreshed = await api.getExecutionResults(executionId.value)
      results.value = refreshed.items
      selectedResult.value = refreshed.items.find((item) => item.id === result.id) || null
    })
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '失败分析创建失败'
  }
}

function openUrl(url: string | null) {
  if (url) window.open(url, '_blank')
}

function statusVariant(status: string) {
  if (status === 'passed') return 'success'
  if (status === 'failed') return 'destructive'
  if (status === 'error' || status === 'timeout') return 'warning'
  if (status === 'running') return 'default'
  return 'muted'
}

onMounted(async () => {
  await load()
  await beginExecutionPoll()
})
</script>

<template>
  <div class="space-y-5">
    <RouterLink
      :to="`/projects/${projectId}/executions`"
      class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft class="h-4 w-4" />返回执行列表
    </RouterLink>

    <Card v-if="loading" class="p-5"><div class="h-48 animate-pulse rounded bg-muted" /></Card>
    <Card v-else-if="error" class="p-5 text-sm text-destructive">{{ error }}</Card>

    <template v-else-if="execution">
      <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="text-xl font-semibold tracking-tight">执行 #{{ execution.id }}</h3>
            <Badge :variant="statusVariant(execution.status)">{{ execution.status }}</Badge>
            <Badge variant="muted">{{ execution.mode }}</Badge>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">
            开始：{{ execution.started_at || '—' }} · 结束：{{ execution.finished_at || '—' }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button v-if="execution.report_url" variant="outline" size="sm" @click="openUrl(execution.report_url)">
            <FileText class="h-3.5 w-3.5" />HTML 报告
          </Button>
          <Button v-if="execution.log_url" variant="outline" size="sm" @click="openUrl(execution.log_url)">
            <Terminal class="h-3.5 w-3.5" />执行日志
          </Button>
          <Button v-if="isActive" variant="destructive" size="sm" @click="cancelExecution">
            <Square class="h-3.5 w-3.5" />取消
          </Button>
          <Button variant="outline" size="sm" @click="load"><RefreshCw class="h-3.5 w-3.5" />刷新</Button>
        </div>
      </section>

      <TaskProgress v-if="executionTask" :task="executionTask" :error="executionTaskError" />

      <div v-if="notice" class="rounded-lg border border-success/20 bg-success/5 px-4 py-2.5 text-sm text-success">{{ notice }}</div>
      <div v-if="execution.error_message" class="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">{{ execution.error_message }}</div>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Card class="p-4"><div class="text-xs text-muted-foreground">总计</div><div class="mt-1 text-2xl font-semibold">{{ execution.total }}</div></Card>
        <Card class="p-4"><div class="text-xs text-muted-foreground">通过</div><div class="mt-1 text-2xl font-semibold text-success">{{ execution.passed }}</div></Card>
        <Card class="p-4"><div class="text-xs text-muted-foreground">失败</div><div class="mt-1 text-2xl font-semibold text-destructive">{{ execution.failed }}</div></Card>
        <Card class="p-4"><div class="text-xs text-muted-foreground">错误</div><div class="mt-1 text-2xl font-semibold text-warning">{{ execution.errors }}</div></Card>
        <Card class="p-4"><div class="text-xs text-muted-foreground">跳过</div><div class="mt-1 text-2xl font-semibold">{{ execution.skipped }}</div></Card>
      </div>

      <Card class="overflow-hidden">
        <div class="border-b border-border px-4 py-3 text-sm font-semibold">逐条结果（{{ results.length }}）</div>
        <div v-if="!results.length" class="p-4 text-sm text-muted-foreground">暂无结果（可能仍在运行或 pytest 收集失败）。</div>
        <div v-else class="divide-y divide-border">
          <div v-for="result in results" :key="result.id" class="px-4 py-3">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <Badge :variant="statusVariant(result.status)">{{ result.status }}</Badge>
                  <span class="font-mono-ui text-xs">{{ result.test_name }}</span>
                  <span class="text-[11px] text-muted-foreground">{{ result.duration_ms ?? 0 }} ms</span>
                </div>
                <p v-if="result.failure_message" class="mt-1 line-clamp-2 text-xs text-destructive">{{ result.failure_message }}</p>
              </div>
              <div class="flex shrink-0 flex-wrap gap-1">
                <Button v-if="result.screenshot_url" variant="outline" size="sm" @click="openUrl(result.screenshot_url)">截图</Button>
                <Button v-if="result.status === 'failed' || result.status === 'error'" variant="outline" size="sm" @click="analyze(result)">
                  <Sparkles class="h-3.5 w-3.5" />失败分析
                </Button>
              </div>
            </div>
            <details v-if="result.traceback" class="mt-2">
              <summary class="cursor-pointer text-xs text-muted-foreground">查看 traceback</summary>
              <pre class="mt-2 max-h-64 overflow-auto rounded-md border border-border bg-muted/30 p-3 text-[11px] leading-relaxed">{{ result.traceback }}</pre>
            </details>
            <div v-if="result.failure_analysis" class="mt-2 rounded-md border border-warning/20 bg-warning/5 p-3 text-xs">
              <div class="font-medium text-warning">已有失败分析（{{ (result.failure_analysis as FailureAnalysis).is_mock ? 'Mock' : 'LLM' }}）</div>
              <div class="mt-1 text-muted-foreground">{{ (result.failure_analysis as FailureAnalysis).observed_error }}</div>
              <Button variant="ghost" size="sm" class="mt-1 h-7 px-2" @click="selectedResult = result">查看详情</Button>
            </div>
          </div>
        </div>
      </Card>
    </template>

    <Modal :open="!!selectedResult" title="失败分析" @close="selectedResult = null">
      <div v-if="selectedResult" class="space-y-4 text-sm">
        <div class="flex flex-wrap items-center gap-2">
          <Badge variant="destructive">{{ selectedResult.status }}</Badge>
          <span class="font-mono-ui text-xs">{{ selectedResult.test_name }}</span>
          <Badge v-if="analysis?.is_mock" variant="warning">Mock</Badge>
          <Badge v-else-if="analysis" variant="success">{{ analysis.provider }} / {{ analysis.model }}</Badge>
        </div>
        <TaskProgress v-if="analysisTask" :task="analysisTask" :error="analysisTaskError" />
        <div v-if="!analysis && analysisTask" class="text-xs text-muted-foreground">正在分析失败原因…</div>
        <template v-else-if="analysis">
          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Observed error（事实）</h4>
            <pre class="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-muted/30 p-3 text-xs">{{ analysis.observed_error }}</pre>
          </div>
          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Inferred causes（推测）</h4>
            <div class="mt-2 space-y-2">
              <div v-for="(cause, index) in analysis.inferred_causes || []" :key="index" class="rounded-md border border-border p-3">
                <div class="flex items-center justify-between gap-2">
                  <span class="font-medium">{{ cause.cause }}</span>
                  <Badge variant="muted">confidence {{ cause.confidence }}</Badge>
                </div>
                <p class="mt-1 text-xs text-muted-foreground">{{ cause.evidence }}</p>
              </div>
            </div>
          </div>
          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">建议</h4>
            <ul class="mt-1 list-disc pl-5 text-xs text-muted-foreground">
              <li v-for="(suggestion, index) in analysis.suggestions || []" :key="index">{{ suggestion }}</li>
            </ul>
          </div>
          <p v-if="analysis.needs_more_info" class="flex items-center gap-1 text-xs text-warning">
            <AlertTriangle class="h-3.5 w-3.5" />信息不足，需要更多日志/上下文。
          </p>
        </template>
      </div>
      <template #footer>
        <Button variant="outline" @click="selectedResult = null">关闭</Button>
      </template>
    </Modal>
  </div>
</template>
