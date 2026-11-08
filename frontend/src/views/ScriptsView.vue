<script setup lang="ts">
import { AlertTriangle, CheckCircle2, Download, FileCode2, RefreshCw, ShieldCheck, Sparkles } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Modal from '@/components/ui/Modal.vue'
import TaskProgress from '@/components/TaskProgress.vue'
import Textarea from '@/components/ui/Textarea.vue'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { toast } from 'vue-sonner'
import type { ScriptDetail, ScriptSummary, TestCase } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const cases = ref<TestCase[]>([])
const scripts = ref<ScriptSummary[]>([])
const selectedCaseIds = ref<number[]>([])

function toggleCase(caseId: number, checked: boolean | 'indeterminate') {
  const next = new Set(selectedCaseIds.value)
  if (checked === true) next.add(caseId)
  else next.delete(caseId)
  selectedCaseIds.value = [...next]
}
const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const generating = ref(false)
const saving = ref(false)
const selectedScript = ref<ScriptDetail | null>(null)
const editContent = ref('')
const poll = useTaskPolling()
const { task: taskState, error: taskError, start: startPoll } = poll

const validationIssues = computed(() => {
  const report = selectedScript.value?.validation_report as { issues?: Array<Record<string, unknown>> } | null
  return report?.issues || []
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const [caseResult, scriptResult] = await Promise.all([
      api.listTestCases(projectId.value),
      api.listScripts(projectId.value),
    ])
    cases.value = caseResult.items
    scripts.value = scriptResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '脚本加载失败'
  } finally {
    loading.value = false
  }
}

async function generate() {
  if (!selectedCaseIds.value.length) {
    error.value = '请选择至少一条测试用例'
    return
  }
  generating.value = true
  error.value = null
  notice.value = null
  try {
    const created = await api.generateScripts(projectId.value, selectedCaseIds.value)
    await startPoll(created.task_id, (task) => {
      if (task.status === 'succeeded') toast.success('脚本生成完成')
      selectedCaseIds.value = []
      void load()
    })
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '脚本生成任务创建失败'
  } finally {
    generating.value = false
  }
}

async function openScript(script: ScriptSummary) {
  try {
    selectedScript.value = await api.getScript(script.id)
    editContent.value = selectedScript.value.content
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '脚本加载失败'
  }
}

async function saveScript() {
  if (!selectedScript.value) return
  saving.value = true
  try {
    const updated = await api.updateScript(selectedScript.value.id, editContent.value)
    selectedScript.value = updated
    editContent.value = updated.content
    notice.value = `已保存新版本 ${updated.filename}（${updated.status}）`
    toast.success('脚本已保存新版本')
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function validateSelected() {
  if (!selectedScript.value) return
  try {
    const updated = await api.validateScript(selectedScript.value.id)
    selectedScript.value = updated
    notice.value = updated.status === 'validated' ? '校验通过' : '校验未通过，请查看问题'
    if (updated.status === 'validated') toast.success('脚本校验通过')
    else toast.error('脚本校验未通过')
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '校验失败'
  }
}

function download(script: ScriptSummary) {
  window.open(`/api/v1/test-scripts/${script.id}/download`, '_blank')
}

function statusVariant(status: string) {
  if (status === 'validated') return 'success'
  if (status === 'rejected') return 'destructive'
  if (status === 'archived') return 'muted'
  return 'warning'
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">测试脚本</h3>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          生成 Pytest + Playwright 脚本，并通过 AST/安全校验。只有 validated 脚本允许执行。
        </p>
      </div>
      <Button variant="outline" @click="load"><RefreshCw class="h-4 w-4" />刷新</Button>
    </section>

    <Card class="p-5">
      <div class="flex items-center gap-2 text-sm font-medium"><FileCode2 class="h-4 w-4 text-primary" />从用例生成脚本</div>
      <div v-if="!cases.length" class="mt-2 text-xs text-muted-foreground">还没有测试用例，请先在「测试用例」生成。</div>
      <div v-else class="mt-3 max-h-40 space-y-1 overflow-y-auto rounded-md border border-border p-2">
        <label v-for="item in cases" :key="item.id" class="flex items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-muted">
          <Checkbox :model-value="selectedCaseIds.includes(item.id)" @update:model-value="(checked) => toggleCase(item.id, checked)" />
          <span class="font-mono-ui text-muted-foreground">{{ item.case_code }}</span>
          <span class="truncate">{{ item.title }}</span>
        </label>
      </div>
      <div class="mt-3 flex justify-end">
        <Button :disabled="generating" @click="generate">
          <Sparkles class="h-4 w-4" />{{ generating ? '提交中…' : '生成脚本' }}
        </Button>
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
      v-else-if="!scripts.length"
      title="还没有测试脚本"
      description="选择用例后生成脚本。Mock 模式会按用例步骤产出可执行的 Playwright 脚本。"
    >
      <template #icon><FileCode2 class="h-5 w-5" /></template>
    </EmptyState>

    <Card v-else class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow class="bg-muted/40 hover:bg-muted/40">
            <TableHead class="px-4">脚本</TableHead>
            <TableHead class="px-4">版本</TableHead>
            <TableHead class="px-4">状态</TableHead>
            <TableHead class="px-4">来源</TableHead>
            <TableHead class="px-4">校验</TableHead>
            <TableHead class="px-4 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="script in scripts" :key="script.id">
            <TableCell class="whitespace-normal px-4 py-3 font-mono-ui text-xs">{{ script.filename }}</TableCell>
            <TableCell class="px-4 py-3 text-muted-foreground">v{{ script.version }}</TableCell>
            <TableCell class="px-4 py-3"><Badge :variant="statusVariant(script.status)">{{ script.status }}</Badge></TableCell>
            <TableCell class="px-4 py-3"><Badge :variant="script.generation_source === 'mock' ? 'warning' : 'default'">{{ script.generation_source }}</Badge></TableCell>
            <TableCell class="px-4 py-3 text-xs text-muted-foreground">{{ script.validation_report?.ok ? '通过' : '未通过' }}</TableCell>
            <TableCell class="px-4 py-3">
              <div class="flex justify-end gap-1">
                <Button variant="outline" size="sm" @click="openScript(script)">预览/编辑</Button>
                <Button variant="ghost" size="icon" title="下载" @click="download(script)"><Download class="h-4 w-4" /></Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <Modal :open="!!selectedScript" :title="selectedScript?.filename || '脚本'" @close="selectedScript = null">
      <div v-if="selectedScript" class="space-y-3">
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <Badge :variant="statusVariant(selectedScript.status)">{{ selectedScript.status }}</Badge>
          <Badge variant="muted">v{{ selectedScript.version }}</Badge>
          <Badge :variant="selectedScript.generation_source === 'mock' ? 'warning' : 'default'">{{ selectedScript.generation_source }}</Badge>
        </div>
        <div v-if="validationIssues.length" class="rounded-md border border-destructive/20 bg-destructive/5 p-3">
          <div class="text-xs font-medium text-destructive">校验问题</div>
          <ul class="mt-1 list-disc pl-5 text-xs text-destructive">
            <li v-for="(issue, index) in validationIssues" :key="index">
              {{ issue.code }}: {{ issue.message }}
            </li>
          </ul>
        </div>
        <Textarea
          v-model="editContent"
          :rows="20"
          class="min-h-80 bg-slate-950 font-mono-ui text-xs leading-relaxed text-slate-100"
          spellcheck="false"
        />
        <p class="text-[11px] text-muted-foreground">
          保存会创建新版本并重新校验；不会覆盖旧版本。脚本内容来自 LLM/Mock，不可信，执行前仍然需要人工复核。
        </p>
      </div>
      <template #footer>
        <Button variant="outline" @click="selectedScript = null">关闭</Button>
        <Button variant="outline" @click="validateSelected"><ShieldCheck class="h-4 w-4" />重新校验</Button>
        <Button :disabled="saving" @click="saveScript">{{ saving ? '保存中…' : '保存新版本' }}</Button>
      </template>
    </Modal>
  </div>
</template>
