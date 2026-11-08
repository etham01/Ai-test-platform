<script setup lang="ts">
import { ArrowLeft, FileCode2, FlaskConical, GitBranch, Globe2, LayoutDashboard, ListChecks, PlayCircle, Settings } from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import type { Project } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const project = ref<Project | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const tabs = [
  { label: '概览', path: 'overview', icon: LayoutDashboard },
  { label: '页面', path: 'pages', icon: Globe2 },
  { label: '业务流程', path: 'workflows', icon: GitBranch },
  { label: '测试需求', path: 'requirements', icon: ListChecks },
  { label: '测试用例', path: 'cases', icon: FlaskConical },
  { label: '脚本', path: 'scripts', icon: FileCode2 },
  { label: '执行与报告', path: 'executions', icon: PlayCircle },
  { label: '设置', path: 'settings', icon: Settings },
]

const activePath = computed(() => route.path)

function tabActive(path: string) {
  return activePath.value === `/projects/${projectId.value}/${path}` ||
    activePath.value.startsWith(`/projects/${projectId.value}/${path}/`)
}

async function load() {
  loading.value = true
  error.value = null
  try {
    project.value = await api.getProject(projectId.value)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '项目加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(projectId, load)
</script>

<template>
  <div class="space-y-5">
    <RouterLink
      to="/projects"
      class="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft class="h-4 w-4" />
      返回项目列表
    </RouterLink>

    <Card v-if="loading" class="p-5">
      <div class="h-6 w-1/3 animate-pulse rounded bg-muted" />
      <div class="mt-3 h-4 w-2/3 animate-pulse rounded bg-muted" />
    </Card>

    <Card v-else-if="error" class="border-destructive/20 bg-destructive/5 p-5 text-sm text-destructive">
      {{ error }}
    </Card>

    <template v-else-if="project">
      <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-2xl font-semibold tracking-tight">{{ project.name }}</h2>
            <Badge :variant="project.status === 'active' ? 'success' : 'muted'">
              {{ project.status === 'active' ? '进行中' : '已归档' }}
            </Badge>
            <Badge variant="muted">#{{ project.id }}</Badge>
          </div>
          <p class="mt-1 max-w-3xl text-sm text-muted-foreground">
            {{ project.description || '暂无项目描述' }}
          </p>
          <p class="mt-2 break-all font-mono-ui text-xs text-muted-foreground">
            {{ project.base_url }}
          </p>
        </div>
      </section>

      <nav class="flex flex-wrap gap-1 rounded-xl border border-border bg-card p-1.5">
        <RouterLink
          v-for="tab in tabs"
          :key="tab.path"
          :to="`/projects/${projectId}/${tab.path}`"
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          :class="{ 'bg-primary/10 text-primary hover:bg-primary/10 hover:text-primary': tabActive(tab.path) }"
        >
          <component :is="tab.icon" class="h-3.5 w-3.5" />
          {{ tab.label }}
        </RouterLink>
      </nav>

      <RouterView />
    </template>
  </div>
</template>
