<script setup lang="ts">
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FolderKanban,
  Plus,
  RefreshCw,
  Server,
  Trash2,
} from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import ConfirmDialog from '@/components/ConfirmDialog.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Input from '@/components/ui/Input.vue'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import Textarea from '@/components/ui/Textarea.vue'
import { formatDate } from '@/lib/utils'
import { useProjectsStore } from '@/stores/projects'
import type { Project, ProjectCreate } from '@/types/api'

const store = useProjectsStore()
const { items, total, loading, creating, error, notice } = storeToRefs(store)
const router = useRouter()

const showForm = ref(false)
const pendingDelete = ref<Project | null>(null)
const formError = ref<string | null>(null)
const form = reactive({
  name: '',
  description: '',
  base_url: 'http://127.0.0.1:8001',
  browser_type: 'chromium',
  max_pages: 8,
  max_depth: 2,
})

const activeCount = computed(() => items.value.filter((item) => item.status === 'active').length)

function resetForm() {
  form.name = ''
  form.description = ''
  form.base_url = 'http://127.0.0.1:8001'
  form.browser_type = 'chromium'
  form.max_pages = 8
  form.max_depth = 2
  formError.value = null
}

function openCreate() {
  resetForm()
  showForm.value = true
}

async function submit() {
  formError.value = null
  if (!form.name.trim()) {
    formError.value = '请输入项目名称'
    return
  }
  if (!form.base_url.trim()) {
    formError.value = '请输入目标站点起始 URL'
    return
  }

  const payload: ProjectCreate = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    base_url: form.base_url.trim(),
    browser_type: form.browser_type,
    scan_config: {
      max_pages: Number(form.max_pages) || 8,
      max_depth: Number(form.max_depth) || 2,
    },
  }

  try {
    await store.create(payload)
    toast.success('项目已创建')
    showForm.value = false
    resetForm()
  } catch (caught) {
    formError.value = caught instanceof Error ? caught.message : '创建失败'
  }
}

function openProject(project: Project) {
  void router.push(`/projects/${project.id}/overview`)
}

function removeProject(project: Project) {
  pendingDelete.value = project
}

async function confirmDeleteProject() {
  const project = pendingDelete.value
  if (!project) return
  try {
    await store.remove(project.id)
    toast.success('项目已删除')
  } catch {
    // store.error already contains a user-facing message
  } finally {
    pendingDelete.value = null
  }
}


onMounted(() => {
  void store.load()
})
</script>

<template>
  <div class="space-y-6">
    <section class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <div class="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <FolderKanban class="h-3.5 w-3.5" />
          工作台
        </div>
        <h2 class="mt-1 text-2xl font-semibold tracking-tight">项目</h2>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          每个项目绑定一个授权起始 URL，后续的页面采集、测试需求、用例与执行记录都归属于项目。
        </p>
      </div>
      <Button @click="openCreate">
        <Plus class="h-4 w-4" />
        新建项目
      </Button>
    </section>

    <div class="grid gap-3 sm:grid-cols-3">
      <Card class="p-4">
        <div class="text-xs text-muted-foreground">项目总数</div>
        <div class="mt-1 text-2xl font-semibold">{{ total }}</div>
      </Card>
      <Card class="p-4">
        <div class="text-xs text-muted-foreground">活跃项目</div>
        <div class="mt-1 text-2xl font-semibold">{{ activeCount }}</div>
      </Card>
      <Card class="p-4">
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
          <Server class="h-3.5 w-3.5" />
          端到端 MVP
        </div>
        <div class="mt-1 flex items-center gap-2 text-sm font-medium">
          采集 → 流程 → 用例 → 脚本 → 执行
          <Badge variant="success">已验证</Badge>
        </div>
      </Card>
    </div>

    <div
      v-if="notice"
      class="flex items-start gap-3 rounded-lg border border-success/20 bg-success/5 px-4 py-3 text-sm text-success"
    >
      <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0" />
      <div class="flex-1">{{ notice }}</div>
      <button class="text-xs underline underline-offset-2" @click="store.clearNotice()">关闭</button>
    </div>

    <div
      v-if="error"
      class="flex items-start gap-3 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
    >
      <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
      <div class="flex-1">{{ error }}</div>
      <Button variant="ghost" size="sm" @click="store.load()">
        <RefreshCw class="h-3.5 w-3.5" />
        重试
      </Button>
    </div>

    <Card v-if="showForm" class="overflow-hidden">
      <div class="border-b border-border px-5 py-4">
        <h3 class="text-sm font-semibold">新建测试项目</h3>
        <p class="mt-0.5 text-xs text-muted-foreground">
          本地演示可填写 DemoShop 地址 <code class="font-mono-ui rounded bg-muted px-1.5 py-0.5">http://127.0.0.1:8001</code>
        </p>
      </div>
      <form class="space-y-4 p-5" @submit.prevent="submit">
        <div class="grid gap-4 md:grid-cols-2">
          <label class="space-y-1.5">
            <span class="text-xs font-medium text-foreground">项目名称 <span class="text-destructive">*</span></span>
            <Input v-model="form.name" placeholder="例如：DemoShop 登录与购物流程" maxlength="128" />
          </label>
          <label class="space-y-1.5">
            <span class="text-xs font-medium text-foreground">起始 URL <span class="text-destructive">*</span></span>
            <Input v-model="form.base_url" placeholder="http://127.0.0.1:8001" maxlength="2048" />
          </label>
        </div>

        <label class="block space-y-1.5">
          <span class="text-xs font-medium text-foreground">项目描述</span>
          <Textarea v-model="form.description" placeholder="说明测试目标、业务范围与已知限制（可选）" rows="2" maxlength="5000" />
        </label>

        <div class="grid gap-4 sm:grid-cols-3">
          <label class="space-y-1.5">
            <span class="text-xs font-medium text-foreground">浏览器</span>
            <Select v-model="form.browser_type">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择浏览器" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="chromium">Chromium</SelectItem>
                <SelectItem value="chrome">系统 Chrome</SelectItem>
                <SelectItem value="msedge">系统 Edge</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label class="space-y-1.5">
            <span class="text-xs font-medium text-foreground">最大页面数</span>
            <Input v-model="form.max_pages" type="number" min="1" max="50" />
          </label>
          <label class="space-y-1.5">
            <span class="text-xs font-medium text-foreground">最大深度</span>
            <Input v-model="form.max_depth" type="number" min="0" max="5" />
          </label>
        </div>

        <div
          v-if="formError"
          class="flex items-center gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive"
        >
          <AlertTriangle class="h-3.5 w-3.5" />
          {{ formError }}
        </div>

        <div class="flex items-center justify-end gap-2 border-t border-border pt-4">
          <Button variant="ghost" type="button" @click="showForm = false">取消</Button>
          <Button type="submit" :disabled="creating">
            <span v-if="creating">创建中…</span>
            <span v-else>创建项目</span>
          </Button>
        </div>
      </form>
    </Card>

    <div v-if="loading" class="grid gap-4 md:grid-cols-2">
      <Card v-for="index in 4" :key="index" class="h-44 animate-pulse p-5">
        <div class="h-4 w-1/3 rounded bg-muted" />
        <div class="mt-3 h-3 w-4/5 rounded bg-muted" />
        <div class="mt-2 h-3 w-2/3 rounded bg-muted" />
      </Card>
    </div>

    <EmptyState
      v-else-if="!items.length"
      title="还没有测试项目"
      description="创建一个项目，绑定本地 demo 站点或你已获授权的目标站点。项目创建后即可进入后续的页面采集与 AI 生成流程。"
    >
      <template #icon>
        <FolderKanban class="h-5 w-5" />
      </template>
      <template #action>
        <Button @click="openCreate">
          <Plus class="h-4 w-4" />
          创建第一个项目
        </Button>
      </template>
    </EmptyState>

    <div v-else class="grid gap-4 md:grid-cols-2">
      <Card v-for="project in items" :key="project.id" class="flex flex-col p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <h3 class="truncate text-base font-semibold">{{ project.name }}</h3>
              <Badge :variant="project.status === 'active' ? 'success' : 'muted'">
                {{ project.status === 'active' ? '进行中' : '已归档' }}
              </Badge>
            </div>
            <p class="mt-1 line-clamp-2 min-h-10 text-sm text-muted-foreground">
              {{ project.description || '暂无描述' }}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            class="shrink-0 text-muted-foreground hover:text-destructive"
            title="删除项目"
            @click="removeProject(project)"
          >
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>

        <div class="mt-4 rounded-md border border-border bg-muted/40 px-3 py-2">
          <div class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Base URL</div>
          <div class="mt-0.5 truncate font-mono-ui text-xs">{{ project.base_url }}</div>
        </div>

        <div class="mt-4 flex items-center justify-between gap-3 border-t border-border pt-4">
          <div class="text-[11px] text-muted-foreground">
            创建于 {{ formatDate(project.created_at) }} · {{ project.browser_type }}
          </div>
          <Button variant="outline" size="sm" @click="openProject(project)">
            查看
            <ArrowRight class="h-3.5 w-3.5" />
          </Button>
        </div>
      </Card>
    </div>

    <p class="text-center text-[11px] text-muted-foreground">
      所有项目数据持久化在 MySQL；删除为软删除，避免丢失后续执行历史。
    </p>

    <ConfirmDialog
      :open="!!pendingDelete"
      title="删除项目"
      :description="pendingDelete ? `确认删除「${pendingDelete.name}」？这是软删除，执行历史仍保留在数据库中。` : ''"
      confirm-text="确认删除"
      destructive
      @confirm="confirmDeleteProject"
      @close="pendingDelete = null"
    />
  </div>
</template>
