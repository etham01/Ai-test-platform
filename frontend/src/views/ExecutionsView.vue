<script setup lang="ts">
import { AlertTriangle, PlayCircle, RefreshCw, ShieldAlert } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import type { Execution, ScriptSummary } from '@/types/api'
import { toast } from 'vue-sonner'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.projectId))
const scripts = ref<ScriptSummary[]>([])
const executions = ref<Execution[]>([])
const selectedScriptIds = ref<number[]>([])

function toggleScript(scriptId: number, checked: boolean | 'indeterminate') {
  const next = new Set(selectedScriptIds.value)
  if (checked === true) next.add(scriptId)
  else next.delete(scriptId)
  selectedScriptIds.value = [...next]
}
const timeoutSeconds = ref(120)
const loading = ref(true)
const error = ref<string | null>(null)
const creating = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [scriptResult, executionResult] = await Promise.all([
      api.listScripts(projectId.value),
      api.listExecutions(projectId.value),
    ])
    scripts.value = scriptResult.items.filter((item) => item.status === 'validated')
    executions.value = executionResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '执行记录加载失败'
  } finally {
    loading.value = false
  }
}

async function createExecution() {
  if (!selectedScriptIds.value.length) {
    error.value = '请选择至少一个已校验脚本'
    return
  }
  creating.value = true
  error.value = null
  try {
    const created = await api.createExecution(projectId.value, {
      script_ids: selectedScriptIds.value,
      timeout_seconds: Number(timeoutSeconds.value) || 120,
      mode: 'local',
    })
    toast.success('执行任务已创建')
    await router.push(`/projects/${projectId.value}/executions/${created.execution_id}`)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '创建执行失败'
  } finally {
    creating.value = false
  }
}

function statusVariant(status: string) {
  if (status === 'passed') return 'success'
  if (status === 'failed') return 'destructive'
  if (status === 'running') return 'default'
  if (status === 'timeout' || status === 'error') return 'warning'
  return 'muted'
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">执行与报告</h3>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          在独立工作目录运行 Pytest + Playwright，保存逐条结果、日志、截图和 HTML 报告。
        </p>
      </div>
      <Button variant="outline" @click="load"><RefreshCw class="h-4 w-4" />刷新</Button>
    </section>

    <Card class="border-warning/20 bg-warning/5 p-4">
      <div class="flex items-start gap-2 text-xs text-warning">
        <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0" />
        当前为受限本地执行模式，不是安全沙箱。只对本地 demo 或受控站点使用；生产环境必须使用容器/沙箱隔离。
      </div>
    </Card>

    <Card class="p-5">
      <div class="flex items-center gap-2 text-sm font-medium"><PlayCircle class="h-4 w-4 text-primary" />创建执行</div>
      <div v-if="!scripts.length" class="mt-2 text-xs text-muted-foreground">没有已校验脚本，请先在「脚本」生成并通过校验。</div>
      <div v-else class="mt-3 max-h-40 space-y-1 overflow-y-auto rounded-md border border-border p-2">
        <label v-for="script in scripts" :key="script.id" class="flex items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-muted">
          <Checkbox :model-value="selectedScriptIds.includes(script.id)" @update:model-value="(checked) => toggleScript(script.id, checked)" />
          <span class="font-mono-ui text-muted-foreground">{{ script.filename }}</span>
          <Badge variant="success">validated</Badge>
        </label>
      </div>
      <div class="mt-3 flex flex-wrap items-end justify-between gap-3">
        <label class="space-y-1.5">
          <span class="text-xs text-muted-foreground">超时（秒）</span>
          <Input v-model="timeoutSeconds" type="number" min="10" max="600" class="w-32" />
        </label>
        <Button :disabled="creating || !scripts.length" @click="createExecution">
          <PlayCircle class="h-4 w-4" />{{ creating ? '创建中…' : '开始执行' }}
        </Button>
      </div>
    </Card>

    <div v-if="error" class="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
      <AlertTriangle class="h-4 w-4" />{{ error }}
    </div>

    <Card v-if="loading" class="p-5"><div class="h-40 animate-pulse rounded bg-muted" /></Card>

    <EmptyState
      v-else-if="!executions.length"
      title="还没有执行记录"
      description="选择已验证脚本并创建执行，结果会持久化到 MySQL。"
    >
      <template #icon><PlayCircle class="h-5 w-5" /></template>
    </EmptyState>

    <Card v-else class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow class="bg-muted/40 hover:bg-muted/40">
            <TableHead class="px-4">执行</TableHead>
            <TableHead class="px-4">状态</TableHead>
            <TableHead class="px-4">结果</TableHead>
            <TableHead class="px-4">模式</TableHead>
            <TableHead class="px-4">时间</TableHead>
            <TableHead class="px-4 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="execution in executions" :key="execution.id">
            <TableCell class="px-4 py-3 font-mono-ui text-xs">#{{ execution.id }}</TableCell>
            <TableCell class="px-4 py-3"><Badge :variant="statusVariant(execution.status)">{{ execution.status }}</Badge></TableCell>
            <TableCell class="px-4 py-3 text-xs text-muted-foreground">
              {{ execution.passed }} passed / {{ execution.failed }} failed / {{ execution.errors }} errors
            </TableCell>
            <TableCell class="px-4 py-3 text-xs text-muted-foreground">{{ execution.mode }}</TableCell>
            <TableCell class="px-4 py-3 text-xs text-muted-foreground">{{ execution.started_at || execution.created_at }}</TableCell>
            <TableCell class="px-4 py-3 text-right">
              <RouterLink :to="`/projects/${projectId}/executions/${execution.id}`">
                <Button variant="outline" size="sm">查看</Button>
              </RouterLink>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>
