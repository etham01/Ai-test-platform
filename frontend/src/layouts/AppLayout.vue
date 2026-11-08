<script setup lang="ts">
import { FolderKanban, Server, Sparkles } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import { Toaster } from '@/components/ui/sonner'

const route = useRoute()
const currentPath = computed(() => route.path)
const healthState = ref<'checking' | 'online' | 'offline'>('checking')
const version = ref('')

const navItems = [
  { label: '项目', to: '/projects', icon: FolderKanban, enabled: true },
]

const pageTitle = computed(() => {
  return typeof route.meta.title === 'string' ? route.meta.title : '智能测试平台'
})

const healthLabel = computed(() => {
  if (healthState.value === 'online') return 'API 正常'
  if (healthState.value === 'offline') return 'API 未连接'
  return '检查中'
})

const healthDotClass = computed(() => {
  if (healthState.value === 'online') return 'bg-success'
  if (healthState.value === 'offline') return 'bg-destructive'
  return 'bg-warning'
})

let timer: number | undefined

async function checkHealth() {
  try {
    const result = await api.health()
    healthState.value = 'online'
    version.value = result.version
  } catch {
    healthState.value = 'offline'
  }
}

onMounted(() => {
  void checkHealth()
  timer = window.setInterval(() => void checkHealth(), 15_000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <Toaster position="top-right" />
    <div class="flex min-h-screen">
      <aside class="hidden w-64 shrink-0 border-r border-border bg-card lg:flex lg:flex-col">
        <div class="flex h-16 items-center gap-3 border-b border-border px-5">
          <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground shadow-sm">
            ST
          </div>
          <div>
            <div class="text-sm font-semibold tracking-tight">SmartTest</div>
            <div class="text-[11px] text-muted-foreground">智能多页面测试平台</div>
          </div>
        </div>

        <nav class="flex-1 space-y-1 px-3 py-4">
          <div class="px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            工作台
          </div>
          <template v-for="item in navItems" :key="item.label">
            <RouterLink
              v-if="item.enabled"
              :to="item.to"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              :class="{
                'bg-primary/10 font-medium text-primary hover:bg-primary/10 hover:text-primary':
                  currentPath.startsWith(item.to),
              }"
            >
              <component :is="item.icon" class="h-4 w-4" />
              <span>{{ item.label }}</span>
            </RouterLink>
            <div
              v-else
              class="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground/50"
              :title="`${item.label} 将在后续阶段接入`"
            >
              <component :is="item.icon" class="h-4 w-4" />
              <span>{{ item.label }}</span>
              <Badge variant="muted" class="ml-auto px-1.5 py-0 text-[10px]">P2+</Badge>
            </div>
          </template>
        </nav>

        <div class="m-3 rounded-lg border border-border bg-background p-3">
          <div class="flex items-center gap-2 text-xs font-medium">
            <Sparkles class="h-3.5 w-3.5 text-primary" />
            MVP · 端到端流程
          </div>
          <p class="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
            进入项目后使用顶部标签页完成页面采集、流程/用例/脚本生成与执行；所有主要操作均连接真实后端。
          </p>
        </div>
      </aside>

      <div class="flex min-w-0 flex-1 flex-col">
        <header class="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/85 px-4 backdrop-blur sm:px-6">
          <div class="flex min-w-0 items-center gap-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary lg:hidden">
              <Server class="h-4 w-4" />
            </div>
            <div class="min-w-0">
              <h1 class="truncate text-base font-semibold tracking-tight">{{ pageTitle }}</h1>
              <p class="hidden text-[11px] text-muted-foreground sm:block">
                面向 Web 应用的智能测试用例与脚本生成平台
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2 sm:gap-3">
            <div class="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground sm:flex">
              <span class="h-2 w-2 rounded-full" :class="healthDotClass" />
              <span>{{ healthLabel }}</span>
              <span v-if="version" class="text-muted-foreground/60">v{{ version }}</span>
            </div>
            <Badge variant="default">MVP</Badge>
          </div>
        </header>

        <main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <RouterView />
        </main>

        <footer class="border-t border-border px-6 py-4 text-center text-[11px] text-muted-foreground">
          SmartTest · 本科毕业设计项目 · 当前阶段功能均连接真实后端
        </footer>
      </div>
    </div>
  </div>
</template>
