<script setup lang="ts">
import { AlertTriangle, CheckCircle2, GitBranch, RefreshCw, Sparkles } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { toast } from 'vue-sonner'
import type { PageSummary, Requirement, Workflow } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const workflows = ref<Workflow[]>([])
const requirements = ref<Requirement[]>([])
const pages = ref<PageSummary[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const requirementId = ref<number | ''>('')
const selectedPageIds = ref<number[]>([])
const analyzing = ref(false)
const poll = useTaskPolling()

function setRequirement(value: unknown) {
  const selected = String(value ?? 'none')
  requirementId.value = selected === 'none' ? '' : Number(selected)
}

function togglePage(pageId: number, checked: boolean | 'indeterminate') {
  const next = new Set(selectedPageIds.value)
  if (checked === true) next.add(pageId)
  else next.delete(pageId)
  selectedPageIds.value = [...next]
}
const { task: taskState, error: taskError, start: startPoll } = poll

async function load() {
  loading.value = true
  error.value = null
  try {
    const [workflowResult, requirementResult, pageResult] = await Promise.all([
      api.listWorkflows(projectId.value),
      api.listRequirements(projectId.value),
      api.listPages(projectId.value, { page_size: 100 }),
    ])
    workflows.value = workflowResult.items
    requirements.value = requirementResult.items
    pages.value = pageResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '流程加载失败'
  } finally {
    loading.value = false
  }
}

async function analyze() {
  analyzing.value = true
  error.value = null
  notice.value = null
  try {
    const created = await api.analyzeWorkflows(projectId.value, {
      requirement_id: requirementId.value || undefined,
      page_ids: selectedPageIds.value,
    })
    await startPoll(created.task_id, (task) => {
      if (task.status === 'succeeded') toast.success('流程分析完成')
      void load()
    })
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '流程分析任务创建失败'
  } finally {
    analyzing.value = false
  }
}

async function confirmWorkflow(workflow: Workflow) {
  try {
    const updated = await api.updateWorkflow(workflow.id, { status: 'confirmed' })
    workflows.value = workflows.value.map((item) => (item.id === updated.id ? updated : item))
    notice.value = `流程「${workflow.name}」已确认`
    toast.success('流程已确认')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '确认失败'
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">业务流程</h3>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          基于已采集页面、关系和需求生成候选流程。模型推断的内容必须人工确认，不能当作网站真实规则。
        </p>
      </div>
      <Button variant="outline" @click="load"><RefreshCw class="h-4 w-4" />刷新</Button>
    </section>

    <Card class="p-5">
      <div class="flex items-center gap-2 text-sm font-medium"><GitBranch class="h-4 w-4 text-primary" />分析配置</div>
      <div class="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <label class="space-y-1.5">
          <span class="text-xs text-muted-foreground">关联需求（可选）</span>
          <Select
            :model-value="requirementId === '' ? 'none' : String(requirementId)"
            @update:model-value="setRequirement"
          >
            <SelectTrigger class="w-full">
              <SelectValue placeholder="不关联需求" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">不关联需求</SelectItem>
              <SelectItem v-for="requirement in requirements" :key="requirement.id" :value="String(requirement.id)">
                {{ requirement.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </label>
        <div class="space-y-1.5">
          <span class="text-xs text-muted-foreground">页面范围（不选则使用全部已采集页面）</span>
          <div class="flex h-9 items-center overflow-x-auto gap-2 rounded-md border border-border px-2 text-xs">
            <label v-for="page in pages" :key="page.id" class="flex shrink-0 items-center gap-1">
              <Checkbox :model-value="selectedPageIds.includes(page.id)" @update:model-value="(checked) => togglePage(page.id, checked)" />
              {{ page.title || page.url }}
            </label>
            <span v-if="!pages.length" class="text-muted-foreground">暂无页面</span>
          </div>
        </div>
        <div class="flex items-end">
          <Button class="w-full" :disabled="analyzing" @click="analyze">
            <Sparkles class="h-4 w-4" />{{ analyzing ? '提交中…' : '分析流程' }}
          </Button>
        </div>
      </div>
    </Card>

    <TaskProgress :task="taskState" :error="taskError" />

    <div v-if="notice" class="flex items-center gap-2 rounded-lg border border-success/20 bg-success/5 px-4 py-2.5 text-sm text-success">
      <CheckCircle2 class="h-4 w-4" />{{ notice }}
    </div>
    <div v-if="error" class="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
      <AlertTriangle class="h-4 w-4" />{{ error }}
    </div>

    <Card v-if="loading" class="p-5"><div class="h-40 animate-pulse rounded bg-muted" /></Card>

    <EmptyState
      v-else-if="!workflows.length"
      title="还没有业务流程"
      description="选择需求/页面后点击「分析流程」。Mock 模式会基于已采集页面生成确定性候选流程。"
    >
      <template #icon><GitBranch class="h-5 w-5" /></template>
    </EmptyState>

    <div v-else class="space-y-4">
      <Card v-for="workflow in workflows" :key="workflow.id" class="p-5">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h4 class="text-base font-semibold">{{ workflow.name }}</h4>
              <Badge :variant="workflow.status === 'confirmed' ? 'success' : 'warning'">{{ workflow.status }}</Badge>
              <Badge variant="muted">{{ workflow.source }}</Badge>
              <Badge variant="default">{{ workflow.involved_page_ids?.length || 0 }} 个页面</Badge>
            </div>
            <p class="mt-1 text-sm text-muted-foreground">{{ workflow.description || '无描述' }}</p>
          </div>
          <Button
            v-if="workflow.status !== 'confirmed'"
            variant="outline"
            size="sm"
            @click="confirmWorkflow(workflow)"
          >
            <CheckCircle2 class="h-3.5 w-3.5" />确认流程
          </Button>
        </div>

        <div class="mt-4 overflow-hidden rounded-md border border-border">
          <Table class="text-xs">
            <TableHeader>
              <TableRow class="bg-muted/40 hover:bg-muted/40">
                <TableHead class="px-3">#</TableHead>
                <TableHead class="px-3">页面</TableHead>
                <TableHead class="px-3">动作</TableHead>
                <TableHead class="px-3">目标</TableHead>
                <TableHead class="px-3">值</TableHead>
                <TableHead class="px-3">说明</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="step in workflow.steps" :key="step.step_no">
                <TableCell class="px-3 py-2 text-muted-foreground">{{ step.step_no }}</TableCell>
                <TableCell class="px-3 py-2">#{{ step.page_id ?? '—' }}</TableCell>
                <TableCell class="px-3 py-2"><Badge variant="muted">{{ step.action }}</Badge></TableCell>
                <TableCell class="px-3 py-2 font-mono-ui">{{ step.target }}</TableCell>
                <TableCell class="px-3 py-2 text-muted-foreground">{{ step.value ?? '—' }}</TableCell>
                <TableCell class="whitespace-normal px-3 py-2 text-muted-foreground">{{ step.description || '—' }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div v-if="workflow.uncertainty" class="mt-3 rounded-md border border-warning/20 bg-warning/5 px-3 py-2 text-xs text-warning">
          不确定点：{{ workflow.uncertainty }}
        </div>
      </Card>
    </div>
  </div>
</template>
