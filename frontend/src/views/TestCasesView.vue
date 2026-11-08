<script setup lang="ts">
import { AlertTriangle, CheckCircle2, FlaskConical, RefreshCw, Sparkles } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Input from '@/components/ui/Input.vue'
import Modal from '@/components/ui/Modal.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { toast } from 'vue-sonner'
import type { Requirement, TestCase } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const requirements = ref<Requirement[]>([])
const cases = ref<TestCase[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const generating = ref(false)
const requirementId = ref<number | ''>('')
const maxCases = ref(5)
const selectedCase = ref<TestCase | null>(null)
const poll = useTaskPolling()

function setRequirement(value: unknown) {
  const selected = String(value ?? 'none')
  requirementId.value = selected === 'none' ? '' : Number(selected)
}
const { task: taskState, error: taskError, start: startPoll } = poll

async function load() {
  loading.value = true
  error.value = null
  try {
    const [requirementResult, caseResult] = await Promise.all([
      api.listRequirements(projectId.value),
      api.listTestCases(projectId.value),
    ])
    requirements.value = requirementResult.items
    cases.value = caseResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '用例加载失败'
  } finally {
    loading.value = false
  }
}

async function generate() {
  if (!requirementId.value) {
    error.value = '请先选择测试需求'
    return
  }
  generating.value = true
  error.value = null
  notice.value = null
  try {
    const created = await api.generateCases(projectId.value, {
      requirement_id: Number(requirementId.value),
      max_cases: Number(maxCases.value) || 5,
    })
    await startPoll(created.task_id, (task) => {
      if (task.status === 'succeeded') toast.success('用例生成完成')
      void load()
    })
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '用例生成任务创建失败'
  } finally {
    generating.value = false
  }
}

async function confirmCase() {
  if (!selectedCase.value) return
  try {
    const updated = await api.updateTestCase(selectedCase.value.id, { status: 'confirmed' })
    cases.value = cases.value.map((item) => (item.id === updated.id ? updated : item))
    selectedCase.value = updated
    notice.value = `用例 ${updated.case_code} 已确认`
    toast.success('用例已确认')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '确认失败'
  }
}

function statusVariant(status: string) {
  if (status === 'confirmed') return 'success'
  if (status === 'needs_review') return 'warning'
  if (status === 'archived') return 'muted'
  return 'default'
}

function expectedText(value: unknown) {
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">测试用例</h3>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          从需求与页面上下文生成结构化用例。model_inference 的断言会标记为待确认，不会伪装成确定规则。
        </p>
      </div>
      <Button variant="outline" @click="load"><RefreshCw class="h-4 w-4" />刷新</Button>
    </section>

    <Card class="p-5">
      <div class="flex items-center gap-2 text-sm font-medium"><FlaskConical class="h-4 w-4 text-primary" />生成用例</div>
      <div class="mt-4 grid gap-3 sm:grid-cols-[1fr_160px_auto]">
        <label class="space-y-1.5">
          <span class="text-xs text-muted-foreground">测试需求</span>
          <Select
            :model-value="requirementId === '' ? 'none' : String(requirementId)"
            @update:model-value="setRequirement"
          >
            <SelectTrigger class="w-full">
              <SelectValue placeholder="请选择需求" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">请选择需求</SelectItem>
              <SelectItem v-for="requirement in requirements" :key="requirement.id" :value="String(requirement.id)">
                {{ requirement.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </label>
        <label class="space-y-1.5">
          <span class="text-xs text-muted-foreground">最多生成</span>
          <Input v-model="maxCases" type="number" min="1" max="10" />
        </label>
        <div class="flex items-end">
          <Button class="w-full" :disabled="generating" @click="generate">
            <Sparkles class="h-4 w-4" />{{ generating ? '提交中…' : '生成用例' }}
          </Button>
        </div>
      </div>
      <p v-if="!requirements.length" class="mt-2 text-xs text-warning">还没有需求，请先到「测试需求」创建。</p>
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
      v-else-if="!cases.length"
      title="还没有测试用例"
      description="选择一条需求并点击「生成用例」。Mock 模式会基于页面元素生成可执行的确定性用例。"
    >
      <template #icon><FlaskConical class="h-5 w-5" /></template>
    </EmptyState>

    <Card v-else class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow class="bg-muted/40 hover:bg-muted/40">
            <TableHead class="px-4">用例</TableHead>
            <TableHead class="px-4">优先级</TableHead>
            <TableHead class="px-4">步骤</TableHead>
            <TableHead class="px-4">状态</TableHead>
            <TableHead class="px-4">来源</TableHead>
            <TableHead class="px-4 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="item in cases" :key="item.id">
            <TableCell class="max-w-xl whitespace-normal px-4 py-3">
              <div class="flex items-center gap-2">
                <span class="font-mono-ui text-xs text-muted-foreground">{{ item.case_code }}</span>
                <span class="font-medium">{{ item.title }}</span>
              </div>
              <div class="mt-0.5 text-xs text-muted-foreground">{{ item.module || '未分类' }}</div>
            </TableCell>
            <TableCell class="px-4 py-3"><Badge variant="muted">{{ item.priority }}</Badge></TableCell>
            <TableCell class="px-4 py-3 text-muted-foreground">{{ item.steps.length }}</TableCell>
            <TableCell class="px-4 py-3"><Badge :variant="statusVariant(item.status)">{{ item.status }}</Badge></TableCell>
            <TableCell class="px-4 py-3"><Badge :variant="item.generation_source === 'mock' ? 'warning' : 'default'">{{ item.generation_source }}</Badge></TableCell>
            <TableCell class="px-4 py-3 text-right">
              <Button variant="outline" size="sm" @click="selectedCase = item">查看</Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <Modal :open="!!selectedCase" :title="selectedCase?.case_code || '用例详情'" @close="selectedCase = null">
      <div v-if="selectedCase" class="space-y-4">
        <div>
          <h3 class="text-lg font-semibold">{{ selectedCase.title }}</h3>
          <div class="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <Badge variant="muted">{{ selectedCase.priority }}</Badge>
            <Badge :variant="statusVariant(selectedCase.status)">{{ selectedCase.status }}</Badge>
            <Badge :variant="selectedCase.generation_source === 'mock' ? 'warning' : 'default'">{{ selectedCase.generation_source }}</Badge>
          </div>
        </div>
        <div>
          <h4 class="text-sm font-semibold">前置条件</h4>
          <ul class="mt-1 list-disc pl-5 text-xs text-muted-foreground">
            <li v-for="(item, index) in selectedCase.preconditions || []" :key="index">{{ item }}</li>
            <li v-if="!selectedCase.preconditions?.length">无</li>
          </ul>
        </div>
        <div>
          <h4 class="text-sm font-semibold">步骤</h4>
          <div class="mt-2 overflow-hidden rounded-md border border-border">
            <Table class="text-xs">
              <TableHeader>
                <TableRow class="bg-muted/40 hover:bg-muted/40">
                  <TableHead class="px-2">#</TableHead>
                  <TableHead class="px-2">页面</TableHead>
                  <TableHead class="px-2">动作</TableHead>
                  <TableHead class="px-2">目标</TableHead>
                  <TableHead class="px-2">值</TableHead>
                  <TableHead class="px-2">说明</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="step in selectedCase.steps" :key="step.step_no">
                  <TableCell class="px-2 py-2">{{ step.step_no }}</TableCell>
                  <TableCell class="px-2 py-2">{{ step.page_reference || '—' }}</TableCell>
                  <TableCell class="px-2 py-2">{{ step.action }}</TableCell>
                  <TableCell class="px-2 py-2 font-mono-ui">{{ step.target }}</TableCell>
                  <TableCell class="px-2 py-2">{{ step.value ?? '—' }}</TableCell>
                  <TableCell class="whitespace-normal px-2 py-2 text-muted-foreground">{{ step.description || '—' }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
        <div>
          <h4 class="text-sm font-semibold">断言</h4>
          <div class="mt-2 space-y-2">
            <div v-for="(assertion, index) in selectedCase.assertions" :key="index" class="rounded-md border border-border px-3 py-2 text-xs">
              <div class="flex flex-wrap items-center gap-2">
                <Badge variant="muted">{{ assertion.assertion_type }}</Badge>
                <span class="font-mono-ui">{{ assertion.target }}</span>
                <span class="text-muted-foreground">→ {{ expectedText(assertion.expected) }}</span>
                <Badge :variant="assertion.source === 'model_inference' ? 'warning' : 'success'">{{ assertion.source }}</Badge>
              </div>
            </div>
          </div>
        </div>
        <div v-if="selectedCase.assumptions?.length">
          <h4 class="text-sm font-semibold">假设 / 待确认</h4>
          <ul class="mt-1 list-disc pl-5 text-xs text-warning">
            <li v-for="(item, index) in selectedCase.assumptions" :key="index">{{ item }}</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <Button variant="outline" @click="selectedCase = null">关闭</Button>
        <Button v-if="selectedCase && selectedCase.status !== 'confirmed'" @click="confirmCase">确认用例</Button>
      </template>
    </Modal>
  </div>
</template>
