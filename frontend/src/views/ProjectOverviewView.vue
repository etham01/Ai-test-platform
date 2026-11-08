<script setup lang="ts">
import { ArrowRight, FileCode2, FlaskConical, GitBranch, Globe2, ListChecks, PlayCircle, Sparkles } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import type { Execution, LLMConfig } from '@/types/api'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const loading = ref(true)
const error = ref<string | null>(null)
const llm = ref<LLMConfig | null>(null)
const executions = ref<Execution[]>([])
const counts = ref({ pages: 0, relations: 0, workflows: 0, requirements: 0, cases: 0, scripts: 0, executions: 0 })

async function load() {
  loading.value = true
  error.value = null
  try {
    const [pages, relations, workflows, requirements, cases, scripts, execs, llmConfig] =
      await Promise.all([
        api.listPages(projectId.value, { page_size: 1 }),
        api.listRelations(projectId.value),
        api.listWorkflows(projectId.value),
        api.listRequirements(projectId.value),
        api.listTestCases(projectId.value),
        api.listScripts(projectId.value),
        api.listExecutions(projectId.value),
        api.getLLMConfig(projectId.value),
      ])
    counts.value = {
      pages: pages.total,
      relations: relations.total,
      workflows: workflows.total,
      requirements: requirements.total,
      cases: cases.total,
      scripts: scripts.total,
      executions: execs.total,
    }
    llm.value = llmConfig
    executions.value = execs.items.slice(0, 3)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '概览加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <Card v-if="llm?.is_mock" class="border-warning/20 bg-warning/5 p-4">
      <div class="flex items-start gap-3">
        <Sparkles class="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <div>
          <div class="text-sm font-medium text-foreground">当前使用 Mock LLM（演示模式）</div>
          <p class="mt-0.5 text-xs text-muted-foreground">
            生成结果来自确定性模板，用于验证流程，不代表真实大模型的生成质量。可在「设置」中切换真实 OpenAI 兼容配置。
          </p>
        </div>
      </div>
    </Card>

    <div v-if="loading" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Card v-for="index in 8" :key="index" class="h-24 animate-pulse p-4">
        <div class="h-3 w-1/3 rounded bg-muted" />
        <div class="mt-3 h-6 w-1/2 rounded bg-muted" />
      </Card>
    </div>

    <Card v-else-if="error" class="p-5 text-sm text-destructive">{{ error }}</Card>

    <template v-else>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card class="p-4">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><Globe2 class="h-3.5 w-3.5" />页面</div>
          <div class="mt-1 text-2xl font-semibold">{{ counts.pages }}</div>
          <div class="text-[11px] text-muted-foreground">{{ counts.relations }} 条关系</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><GitBranch class="h-3.5 w-3.5" />业务流程</div>
          <div class="mt-1 text-2xl font-semibold">{{ counts.workflows }}</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><ListChecks class="h-3.5 w-3.5" />测试需求</div>
          <div class="mt-1 text-2xl font-semibold">{{ counts.requirements }}</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><FlaskConical class="h-3.5 w-3.5" />测试用例</div>
          <div class="mt-1 text-2xl font-semibold">{{ counts.cases }}</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><FileCode2 class="h-3.5 w-3.5" />脚本版本</div>
          <div class="mt-1 text-2xl font-semibold">{{ counts.scripts }}</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><PlayCircle class="h-3.5 w-3.5" />执行</div>
          <div class="mt-1 text-2xl font-semibold">{{ counts.executions }}</div>
        </Card>
        <Card class="p-4 sm:col-span-2">
          <div class="text-xs text-muted-foreground">LLM 状态</div>
          <div class="mt-1 flex items-center gap-2 text-sm font-medium">
            {{ llm?.is_mock ? 'Mock 演示模式' : `${llm?.provider} / ${llm?.model}` }}
            <Badge :variant="llm?.is_mock ? 'warning' : 'success'">{{ llm?.is_mock ? 'Mock' : '真实模型' }}</Badge>
          </div>
          <div class="mt-1 text-[11px] text-muted-foreground">Key：{{ llm?.key_hint || (llm?.is_mock ? '不需要 Key' : '未配置') }}</div>
        </Card>
      </div>

      <Card class="p-5">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-sm font-semibold">端到端流程</h3>
          <Badge variant="muted">按顺序执行</Badge>
        </div>
        <div class="mt-4 grid gap-2 md:grid-cols-3">
          <RouterLink :to="`/projects/${projectId}/pages`" class="group rounded-lg border border-border p-3 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]">
            <div class="text-sm font-medium">1. 采集页面</div>
            <p class="mt-1 text-xs text-muted-foreground">Playwright 同源 BFS，提取元素与关系。</p>
          </RouterLink>
          <RouterLink :to="`/projects/${projectId}/requirements`" class="group rounded-lg border border-border p-3 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]">
            <div class="text-sm font-medium">2. 编写需求</div>
            <p class="mt-1 text-xs text-muted-foreground">把业务预期与关联页面记录下来。</p>
          </RouterLink>
          <RouterLink :to="`/projects/${projectId}/workflows`" class="group rounded-lg border border-border p-3 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]">
            <div class="text-sm font-medium">3. 分析流程</div>
            <p class="mt-1 text-xs text-muted-foreground">生成候选流程并人工确认。</p>
          </RouterLink>
          <RouterLink :to="`/projects/${projectId}/cases`" class="group rounded-lg border border-border p-3 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]">
            <div class="text-sm font-medium">4. 生成用例</div>
            <p class="mt-1 text-xs text-muted-foreground">结构化步骤、断言与待确认假设。</p>
          </RouterLink>
          <RouterLink :to="`/projects/${projectId}/scripts`" class="group rounded-lg border border-border p-3 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]">
            <div class="text-sm font-medium">5. 生成脚本</div>
            <p class="mt-1 text-xs text-muted-foreground">Pytest + Playwright，AST/安全校验。</p>
          </RouterLink>
          <RouterLink :to="`/projects/${projectId}/executions`" class="group rounded-lg border border-border p-3 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]">
            <div class="text-sm font-medium">6. 执行与报告</div>
            <p class="mt-1 text-xs text-muted-foreground">结果、截图、日志、HTML 报告与失败分析。</p>
          </RouterLink>
        </div>
      </Card>

      <Card class="p-5">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-sm font-semibold">最近执行</h3>
          <RouterLink :to="`/projects/${projectId}/executions`" class="text-xs text-primary hover:underline">查看全部</RouterLink>
        </div>
        <div v-if="!executions.length" class="mt-3 text-sm text-muted-foreground">还没有执行记录。</div>
        <div v-else class="mt-3 divide-y divide-border">
          <RouterLink
            v-for="execution in executions"
            :key="execution.id"
            :to="`/projects/${projectId}/executions/${execution.id}`"
            class="flex items-center justify-between gap-3 py-3 text-sm hover:bg-muted/40"
          >
            <div class="flex items-center gap-2">
              <span class="font-mono-ui text-xs text-muted-foreground">#{{ execution.id }}</span>
              <Badge :variant="execution.status === 'passed' ? 'success' : execution.status === 'failed' ? 'destructive' : 'muted'">
                {{ execution.status }}
              </Badge>
              <span>{{ execution.passed }} passed / {{ execution.failed }} failed</span>
            </div>
            <ArrowRight class="h-4 w-4 text-muted-foreground" />
          </RouterLink>
        </div>
      </Card>
    </template>
  </div>
</template>
