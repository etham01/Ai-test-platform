<script setup lang="ts">
import { AlertTriangle, ArrowLeft, Download, ExternalLink, RefreshCw } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { PageDetail, PageRelation } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const pageId = computed(() => Number(route.params.pageId))
const detail = ref<PageDetail | null>(null)
const relations = ref<PageRelation[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const pageRelations = computed(() =>
  relations.value.filter(
    (item) => item.from_page_id === pageId.value || item.to_page_id === pageId.value,
  ),
)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [page, relationResult] = await Promise.all([
      api.getPage(projectId.value, pageId.value),
      api.listRelations(projectId.value),
    ])
    detail.value = page
    relations.value = relationResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '页面加载失败'
  } finally {
    loading.value = false
  }
}

function selectorText(value: Record<string, unknown> | null) {
  if (!value) return '—'
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${typeof item === 'object' ? JSON.stringify(item) : String(item)}`)
    .join(' · ')
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <RouterLink
      :to="`/projects/${projectId}/pages`"
      class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft class="h-4 w-4" />返回页面列表
    </RouterLink>

    <Card v-if="loading" class="p-5">
      <div class="h-6 w-1/3 animate-pulse rounded bg-muted" />
      <div class="mt-3 h-4 w-2/3 animate-pulse rounded bg-muted" />
    </Card>

    <Card v-else-if="error" class="p-5">
      <div class="flex items-start gap-2 text-sm text-destructive"><AlertTriangle class="h-4 w-4" />{{ error }}</div>
      <Button variant="outline" class="mt-3" @click="load"><RefreshCw class="h-4 w-4" />重试</Button>
    </Card>

    <template v-else-if="detail">
      <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="text-xl font-semibold tracking-tight">{{ detail.title || '(无标题)' }}</h3>
            <Badge :variant="detail.status === 'parsed' ? 'success' : detail.status === 'failed' ? 'destructive' : 'warning'">
              {{ detail.status }}
            </Badge>
            <Badge variant="muted">depth {{ detail.depth }}</Badge>
          </div>
          <a :href="detail.url" target="_blank" class="mt-1 inline-flex items-center gap-1 break-all font-mono-ui text-xs text-primary hover:underline">
            {{ detail.url }}<ExternalLink class="h-3 w-3" />
          </a>
        </div>
        <div class="flex flex-wrap gap-2">
          <a v-if="detail.dom_url" :href="detail.dom_url" target="_blank">
            <Button variant="outline" size="sm"><Download class="h-3.5 w-3.5" />DOM 快照</Button>
          </a>
          <a v-if="detail.screenshot_url" :href="detail.screenshot_url" target="_blank">
            <Button variant="outline" size="sm">查看截图</Button>
          </a>
        </div>
      </section>

      <div class="grid gap-4 lg:grid-cols-3">
        <Card class="p-5 lg:col-span-2">
          <h4 class="text-sm font-semibold">页面文本摘要</h4>
          <pre class="mt-3 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-md border border-border bg-muted/30 p-3 text-xs leading-relaxed text-muted-foreground">{{ detail.text_summary || '无文本摘要' }}</pre>
          <div class="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <div>HTTP：{{ detail.http_status ?? '—' }}</div>
            <div>Content-Type：{{ detail.content_type || '—' }}</div>
            <div>元素数：{{ detail.elements.length }}</div>
            <div>关系数：{{ pageRelations.length }}</div>
          </div>
        </Card>
        <Card class="p-5">
          <h4 class="text-sm font-semibold">截图</h4>
          <img
            v-if="detail.screenshot_url"
            :src="detail.screenshot_url"
            alt="页面截图"
            class="mt-3 max-h-80 w-full rounded-md border border-border object-contain"
          />
          <div v-else class="mt-3 text-xs text-muted-foreground">无截图</div>
        </Card>
      </div>

      <Card class="overflow-hidden">
        <div class="border-b border-border px-4 py-3 text-sm font-semibold">交互元素（{{ detail.elements.length }}）</div>
        <Table class="text-xs">
          <TableHeader>
            <TableRow class="bg-muted/40 hover:bg-muted/40">
              <TableHead class="px-3">类型</TableHead>
              <TableHead class="px-3">Role</TableHead>
              <TableHead class="px-3">可访问名 / Label</TableHead>
              <TableHead class="px-3">Placeholder</TableHead>
              <TableHead class="px-3">定位候选</TableHead>
              <TableHead class="px-3">敏感</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="element in detail.elements" :key="element.id">
              <TableCell class="px-3 py-2 font-mono-ui">{{ element.element_type }}</TableCell>
              <TableCell class="px-3 py-2">{{ element.role || '—' }}</TableCell>
              <TableCell class="max-w-xs whitespace-normal px-3 py-2">
                <div class="truncate">{{ element.accessible_name || element.label || '—' }}</div>
                <div class="truncate text-[10px] text-muted-foreground">{{ element.tag }} {{ element.input_type || '' }}</div>
              </TableCell>
              <TableCell class="max-w-xs whitespace-normal px-3 py-2 text-muted-foreground">{{ element.placeholder || '—' }}</TableCell>
              <TableCell class="max-w-sm whitespace-normal px-3 py-2 font-mono-ui text-[10px] text-muted-foreground">{{ selectorText(element.selector_candidates) }}</TableCell>
              <TableCell class="px-3 py-2">
                <Badge v-if="element.is_sensitive" variant="warning">敏感</Badge>
                <span v-else class="text-muted-foreground">—</span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>

      <Card class="overflow-hidden">
        <div class="border-b border-border px-4 py-3 text-sm font-semibold">页面关系（{{ pageRelations.length }}）</div>
        <div v-if="!pageRelations.length" class="p-4 text-xs text-muted-foreground">暂无关系</div>
        <div v-else class="divide-y divide-border">
          <div v-for="relation in pageRelations" :key="relation.id" class="flex flex-wrap items-center gap-2 px-4 py-2.5 text-xs">
            <Badge variant="muted">{{ relation.relation_type }}</Badge>
            <span class="font-mono-ui">#{{ relation.from_page_id }} → #{{ relation.to_page_id ?? '?' }}</span>
            <span class="min-w-0 flex-1 truncate text-muted-foreground">{{ relation.target_url }}</span>
            <Badge :variant="relation.source === 'model_inferred' ? 'warning' : 'success'">{{ relation.source }}</Badge>
          </div>
        </div>
      </Card>
    </template>
  </div>
</template>
