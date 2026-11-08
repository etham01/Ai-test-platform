<script setup lang="ts">
import { computed } from 'vue'

import Badge from '@/components/ui/Badge.vue'
import type { Task } from '@/types/api'

const props = defineProps<{
  task: Task | null
  error?: string | null
}>()

const variant = computed(() => {
  const status = props.task?.status
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'destructive'
  if (status === 'cancelled') return 'muted'
  if (status === 'running') return 'default'
  return 'warning'
})

const label = computed(() => {
  const status = props.task?.status
  if (status === 'queued') return '排队中'
  if (status === 'running') return '运行中'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'cancelled') return '已取消'
  return '等待'
})
</script>

<template>
  <div v-if="task || error" class="rounded-lg border border-border bg-card p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <Badge :variant="variant">{{ label }}</Badge>
        <span class="text-sm text-muted-foreground">{{ task?.message || '处理中…' }}</span>
      </div>
      <span v-if="task" class="text-xs text-muted-foreground">{{ task.progress }}%</span>
    </div>
    <div v-if="task" class="mt-3 h-2 overflow-hidden rounded-full bg-muted">
      <div
        class="h-full rounded-full bg-primary transition-all"
        :style="{ width: `${Math.max(0, Math.min(100, task.progress))}%` }"
      />
    </div>
    <p v-if="task?.error" class="mt-2 text-xs text-destructive">{{ task.error }}</p>
    <p v-if="error" class="mt-2 text-xs text-destructive">{{ error }}</p>
  </div>
</template>
