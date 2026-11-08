<script setup lang="ts">
import { AlertTriangle, ArrowRight, GitBranch, Globe2, RefreshCw, Search } from '@lucide/vue'
import { computed, onMounted, reactive, ref, toRefs } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api } from '@/api/client'
import { Alert, AlertDescription } from '@/components/ui/alert'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Input from '@/components/ui/Input.vue'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import TaskProgress from '@/components/TaskProgress.vue'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { toast } from 'vue-sonner'
import type { PageRelation, PageSummary } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const pages = ref<PageSummary[]>([])
const relations = ref<PageRelation[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const exploring = ref(false)
const form = reactive({
  start_url: '',
  max_pages: 8,
  max_depth: 2,
  timeout_seconds: 15,
  wait_after_load_ms: 500,
})
const { start_url, max_pages, max_depth, timeout_seconds, wait_after_load_ms } = toRefs(form)
const poll = useTaskPolling()
const { task: exploreTask, error: taskError, start: startExplorePoll } = poll

async function load() {
  loading.value = true
  error.value = null
  try {
    const [pageResult, relationResult] = await Promise.all([
      api.listPages(projectId.value, { page_size: 100 }),
      api.listRelations(projectId.value),
    ])
    pages.value = pageResult.items
    relations.value = relationResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '页面加载失败'
  } finally {
    loading.value = false
  }
}

async function explore() {
  exploring.value = true
  error.value = null
  try {
    const created = await api.explorePages(projectId.value, {
      start_url: form.start_url.trim() || undefined,
      max_pages: Number(form.max_pages) || 8,
      max_depth: Number(form.max_depth) || 0,
      timeout_seconds: Number(form.timeout_seconds) || 15,
      wait_after_load_ms: Number(form.wait_after_load_ms) || 0,
    })
    await startExplorePoll(created.task_id, (task) => {
      if (task.status === 'succeeded') toast.success('页面探索完成')
      void load()
    })
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '探索任务创建失败'
  } finally {
    exploring.value = false
  }
}

const statusVariant = (status: string) => {
  if (status === 'parsed') return 'success'
  if (status === 'failed') return 'destructive'
  if (status === 'blocked') return 'warning'
  return 'muted'
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">页面采集</h3>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          从项目 Base URL 开始做同源有限深度 BFS。默认不提交表单、不跟随外域/登出/下载链接。
        </p>
      </div>
      <Button variant="outline" @click="load">
        <RefreshCw class="h-4 w-4" />
        刷新
      </Button>
    </section>

    <Card class="p-5">
      <div class="flex items-center gap-2 text-sm font-medium">
        <Search class="h-4 w-4 text-primary" />
        探索配置
      </div>
      <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <label class="space-y-1.5 sm:col-span-2">
          <span class="text-xs text-muted-foreground">起始 URL（留空使用项目 Base URL）</span>
          <Input v-model="start_url" placeholder="http://127.0.0.1:8001/" />
        </label>
        <label class="space-y-1.5">
          <span class="text-xs text-muted-foreground">最大页面数</span>
          <Input v-model="max_pages" type="number" min="1" max="50" />
        </label>
        <label class="space-y-1.5">
          <span class="text-xs text-muted-foreground">最大深度</span>
          <Input v-model="max_depth" type="number" min="0" max="5" />
        </label>
        <div class="flex items-end">
          <Button class="w-full" :disabled="exploring || !!exploreTask && ['queued','running'].includes(exploreTask.status)" @click="explore">
            <Globe2 class="h-4 w-4" />
            {{ exploring ? '提交中…' : '开始探索' }}
          </Button>
        </div>
      </div>
      <p class="mt-3 text-[11px] text-muted-foreground">
        单页超时 {{ timeout_seconds }}s · 加载后等待 {{ wait_after_load_ms }}ms · 非授权源与云元数据地址会被拒绝
      </p>
    </Card>

    <TaskProgress :task="exploreTask" :error="taskError" />

    <Alert v-if="error" variant="destructive">
      <AlertTriangle class="h-4 w-4" />
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <div class="grid gap-3 sm:grid-cols-3">
      <Card class="p-4">
        <div class="text-xs text-muted-foreground">已采集页面</div>
        <div class="mt-1 text-2xl font-semibold">{{ pages.length }}</div>
      </Card>
      <Card class="p-4">
        <div class="flex items-center gap-2 text-xs text-muted-foreground"><GitBranch class="h-3.5 w-3.5" />页面关系</div>
        <div class="mt-1 text-2xl font-semibold">{{ relations.length }}</div>
      </Card>
      <Card class="p-4">
        <div class="text-xs text-muted-foreground">已解析页面</div>
        <div class="mt-1 text-2xl font-semibold">{{ pages.filter((p) => p.status === 'parsed').length }}</div>
      </Card>
    </div>

    <Card v-if="loading" class="p-5">
      <div class="space-y-3">
        <div v-for="index in 6" :key="index" class="h-10 animate-pulse rounded bg-muted" />
      </div>
    </Card>

    <EmptyState
      v-else-if="!pages.length"
      title="还没有页面"
      description="填写起始 URL 后点击「开始探索」。本地演示可使用 DemoShop 的 http://127.0.0.1:8001/。"
    >
      <template #icon><Globe2 class="h-5 w-5" /></template>
      <template #action>
        <Button @click="explore">
          <Globe2 class="h-4 w-4" />
          探索站点
        </Button>
      </template>
    </EmptyState>

    <Card v-else class="overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow class="bg-muted/40 hover:bg-muted/40">
            <TableHead class="px-4">页面</TableHead>
            <TableHead class="px-4">状态</TableHead>
            <TableHead class="px-4">深度</TableHead>
            <TableHead class="px-4">元素</TableHead>
            <TableHead class="px-4">HTTP</TableHead>
            <TableHead class="px-4 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="page in pages" :key="page.id" class="align-top">
            <TableCell class="max-w-md whitespace-normal px-4 py-3">
              <div class="truncate font-medium">{{ page.title || '(无标题)' }}</div>
              <div class="mt-0.5 truncate font-mono-ui text-[11px] text-muted-foreground">{{ page.url }}</div>
              <div v-if="page.error_message" class="mt-1 text-[11px] text-destructive">{{ page.error_message }}</div>
            </TableCell>
            <TableCell class="px-4 py-3"><Badge :variant="statusVariant(page.status)">{{ page.status }}</Badge></TableCell>
            <TableCell class="px-4 py-3 text-muted-foreground">{{ page.depth }}</TableCell>
            <TableCell class="px-4 py-3 text-muted-foreground">{{ page.element_count }}</TableCell>
            <TableCell class="px-4 py-3 text-muted-foreground">{{ page.http_status ?? '—' }}</TableCell>
            <TableCell class="px-4 py-3 text-right">
              <RouterLink :to="`/projects/${projectId}/pages/${page.id}`">
                <Button variant="outline" size="sm">
                  查看
                  <ArrowRight class="h-3.5 w-3.5" />
                </Button>
              </RouterLink>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>
