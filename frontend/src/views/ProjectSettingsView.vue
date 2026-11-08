<script setup lang="ts">
import { AlertTriangle, CheckCircle2, KeyRound, RefreshCw, Save, Sparkles } from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { LLMConfig, Project } from '@/types/api'
import { toast } from 'vue-sonner'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const project = ref<Project | null>(null)
const config = ref<LLMConfig | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const savingProject = ref(false)
const savingLLM = ref(false)
const testing = ref(false)
const testMessage = ref<string | null>(null)
const apiKey = ref('')
const clearKey = ref(false)

const projectForm = reactive({
  name: '',
  description: '',
  base_url: '',
  browser_type: 'chromium',
})
const llmForm = reactive({
  provider: 'mock',
  base_url: '',
  model: '',
  temperature: 0.2,
  timeout_seconds: 60,
  max_retries: 2,
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const [p, c] = await Promise.all([api.getProject(projectId.value), api.getLLMConfig(projectId.value)])
    project.value = p
    config.value = c
    projectForm.name = p.name
    projectForm.description = p.description || ''
    projectForm.base_url = p.base_url
    projectForm.browser_type = p.browser_type
    llmForm.provider = c.provider
    llmForm.base_url = c.base_url || ''
    llmForm.model = c.model
    llmForm.temperature = c.temperature
    llmForm.timeout_seconds = c.timeout_seconds
    llmForm.max_retries = c.max_retries
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '设置加载失败'
  } finally {
    loading.value = false
  }
}

async function saveProject() {
  savingProject.value = true
  error.value = null
  notice.value = null
  try {
    project.value = await api.updateProject(projectId.value, {
      name: projectForm.name,
      description: projectForm.description || null,
      base_url: projectForm.base_url,
      browser_type: projectForm.browser_type,
    })
    notice.value = '项目配置已保存'
    toast.success('项目配置已保存')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '项目保存失败'
  } finally {
    savingProject.value = false
  }
}

async function saveLLM() {
  savingLLM.value = true
  error.value = null
  notice.value = null
  try {
    const payload: Record<string, unknown> = {
      provider: llmForm.provider,
      temperature: Number(llmForm.temperature),
      timeout_seconds: Number(llmForm.timeout_seconds),
      max_retries: Number(llmForm.max_retries),
    }
    if (llmForm.provider === 'openai_compatible') {
      payload.base_url = llmForm.base_url
      payload.model = llmForm.model
      if (apiKey.value) payload.api_key = apiKey.value
      if (clearKey.value) payload.clear_api_key = true
    }
    config.value = await api.updateLLMConfig(projectId.value, payload)
    apiKey.value = ''
    clearKey.value = false
    notice.value = 'LLM 配置已保存'
    toast.success('LLM 配置已保存')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'LLM 配置保存失败'
  } finally {
    savingLLM.value = false
  }
}

async function testLLM() {
  testing.value = true
  testMessage.value = null
  try {
    const result = await api.testLLM(projectId.value)
    testMessage.value = `${result.ok ? '成功' : '失败'} · ${result.provider} / ${result.model} · ${result.latency_ms}ms · ${result.message}`
    if (result.ok) toast.success('LLM 连接成功')
    else toast.error('LLM 连接失败')
  } catch (caught) {
    testMessage.value = caught instanceof Error ? caught.message : '连接测试失败'
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex items-center justify-between gap-3">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">项目设置</h3>
        <p class="mt-1 text-sm text-muted-foreground">项目基础信息与 LLM 配置。API Key 永不返回前端明文。</p>
      </div>
      <Button variant="outline" @click="load"><RefreshCw class="h-4 w-4" />刷新</Button>
    </section>

    <div v-if="notice" class="flex items-center gap-2 rounded-lg border border-success/20 bg-success/5 px-4 py-2.5 text-sm text-success">
      <CheckCircle2 class="h-4 w-4" />{{ notice }}
    </div>
    <div v-if="error" class="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
      <AlertTriangle class="h-4 w-4" />{{ error }}
    </div>

    <Card v-if="loading" class="p-5"><div class="h-48 animate-pulse rounded bg-muted" /></Card>

    <template v-else-if="project">
      <Card class="p-5">
        <div class="text-sm font-semibold">项目信息</div>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">项目名称</span>
            <Input v-model="projectForm.name" maxlength="128" />
          </label>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">起始 URL</span>
            <Input v-model="projectForm.base_url" />
          </label>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">浏览器</span>
            <Select v-model="projectForm.browser_type">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择浏览器" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="chromium">Chromium（Playwright）</SelectItem>
                <SelectItem value="chrome">系统 Chrome</SelectItem>
                <SelectItem value="msedge">系统 Edge</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label class="space-y-1.5 sm:col-span-2">
            <span class="text-xs text-muted-foreground">描述</span>
            <Textarea v-model="projectForm.description" rows="2" maxlength="5000" />
          </label>
        </div>
        <div class="mt-4 flex justify-end">
          <Button :disabled="savingProject" @click="saveProject"><Save class="h-4 w-4" />{{ savingProject ? '保存中…' : '保存项目' }}</Button>
        </div>
      </Card>

      <Card class="p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2 text-sm font-semibold"><KeyRound class="h-4 w-4 text-primary" />LLM 配置</div>
          <div class="flex items-center gap-2">
            <Badge :variant="config?.is_mock ? 'warning' : config?.configured ? 'success' : 'destructive'">
              {{ config?.is_mock ? 'Mock 演示模式' : config?.configured ? '真实模型' : '未配置 Key' }}
            </Badge>
            <Button variant="outline" size="sm" :disabled="testing" @click="testLLM">
              {{ testing ? '测试中…' : '测试连接' }}
            </Button>
          </div>
        </div>

        <div v-if="config?.is_mock" class="mt-3 rounded-md border border-warning/20 bg-warning/5 px-3 py-2 text-xs text-warning">
          <Sparkles class="mr-1 inline h-3.5 w-3.5" />
          Mock 模式不会调用真实模型；生成结果来自确定性模板，仅用于完整流程演示。
        </div>

        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">Provider</span>
            <Select v-model="llmForm.provider">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择 Provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mock">Mock（演示）</SelectItem>
                <SelectItem value="openai_compatible">OpenAI 兼容</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">模型名</span>
            <Input v-model="llmForm.model" placeholder="mock-v1 或真实模型名" />
          </label>
          <label class="space-y-1.5 sm:col-span-2">
            <span class="text-xs text-muted-foreground">Base URL（OpenAI 兼容，建议包含 /v1）</span>
            <Input v-model="llmForm.base_url" placeholder="https://api.example.com/v1" />
          </label>
          <label class="space-y-1.5 sm:col-span-2">
            <span class="text-xs text-muted-foreground">API Key（只写；留空保留现有 Key）</span>
            <Input v-model="apiKey" type="password" placeholder="sk-..." autocomplete="off" />
            <div class="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
              <span>已保存 Key：{{ config?.key_hint || '无' }}</span>
              <label class="flex items-center gap-1">
                <Checkbox :model-value="clearKey" @update:model-value="(value) => (clearKey = value === true)" />清除现有 Key
              </label>
            </div>
          </label>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">Temperature</span>
            <Input v-model="llmForm.temperature" type="number" min="0" max="2" step="0.1" />
          </label>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">超时（秒）</span>
            <Input v-model="llmForm.timeout_seconds" type="number" min="5" max="300" />
          </label>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">最大重试</span>
            <Input v-model="llmForm.max_retries" type="number" min="0" max="5" />
          </label>
        </div>

        <div v-if="testMessage" class="mt-3 rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">{{ testMessage }}</div>

        <div class="mt-4 flex justify-end">
          <Button :disabled="savingLLM" @click="saveLLM"><Save class="h-4 w-4" />{{ savingLLM ? '保存中…' : '保存 LLM 配置' }}</Button>
        </div>
      </Card>
    </template>
  </div>
</template>
