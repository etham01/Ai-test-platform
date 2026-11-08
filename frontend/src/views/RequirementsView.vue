<script setup lang="ts">
import { AlertTriangle, CheckCircle2, ListChecks, Plus, RefreshCw, Trash2 } from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import Badge from '@/components/ui/Badge.vue'
import { Checkbox } from '@/components/ui/checkbox'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import type { PageSummary, Requirement } from '@/types/api'
import { toast } from 'vue-sonner'

const route = useRoute()
const projectId = computed(() => Number(route.params.projectId))
const requirements = ref<Requirement[]>([])
const pages = ref<PageSummary[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const saving = ref(false)
const editingId = ref<number | null>(null)
const pendingDelete = ref<Requirement | null>(null)

function toggleRelatedPage(pageId: number, checked: boolean | 'indeterminate') {
  const next = new Set(form.related_page_ids)
  if (checked === true) next.add(pageId)
  else next.delete(pageId)
  form.related_page_ids = [...next]
}
const form = reactive({
  title: '',
  content: '',
  related_page_ids: [] as number[],
  max_cases: 5,
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const [requirementResult, pageResult] = await Promise.all([
      api.listRequirements(projectId.value),
      api.listPages(projectId.value, { page_size: 100 }),
    ])
    requirements.value = requirementResult.items
    pages.value = pageResult.items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '需求加载失败'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = null
  form.title = ''
  form.content = ''
  form.related_page_ids = []
  form.max_cases = 5
}

function edit(requirement: Requirement) {
  editingId.value = requirement.id
  form.title = requirement.title
  form.content = requirement.content
  form.related_page_ids = [...(requirement.related_page_ids || [])]
  form.max_cases = Number(requirement.generation_config?.max_cases || 5)
}

async function submit() {
  if (!form.title.trim() || !form.content.trim()) {
    error.value = '请填写需求标题和内容'
    return
  }
  saving.value = true
  error.value = null
  notice.value = null
  const payload = {
    title: form.title.trim(),
    content: form.content.trim(),
    related_page_ids: form.related_page_ids,
    generation_config: { max_cases: Number(form.max_cases) || 5 },
  }
  try {
    if (editingId.value) {
      await api.updateRequirement(editingId.value, payload)
      notice.value = '需求已更新'
      toast.success('需求已更新')
    } else {
      const created = await api.createRequirement(projectId.value, payload)
      requirements.value = [created, ...requirements.value]
      notice.value = '需求已创建'
      toast.success('需求已创建')
    }
    resetForm()
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '保存失败'
  } finally {
    saving.value = false
  }
}

function remove(requirement: Requirement) {
  pendingDelete.value = requirement
}

async function confirmDeleteRequirement() {
  const requirement = pendingDelete.value
  if (!requirement) return
  try {
    await api.deleteRequirement(requirement.id)
    requirements.value = requirements.value.filter((item) => item.id !== requirement.id)
    notice.value = '需求已删除'
    toast.success('需求已删除')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '删除失败'
  } finally {
    pendingDelete.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <h3 class="text-lg font-semibold tracking-tight">测试需求</h3>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          记录业务预期与关联页面；后续流程分析和用例生成都会引用它。
        </p>
      </div>
      <Button variant="outline" @click="load"><RefreshCw class="h-4 w-4" />刷新</Button>
    </section>

    <Alert v-if="notice" class="border-success/20 bg-success/5 text-success">
      <CheckCircle2 class="h-4 w-4" />
      <AlertDescription class="text-success">{{ notice }}</AlertDescription>
    </Alert>
    <Alert v-if="error" variant="destructive">
      <AlertTriangle class="h-4 w-4" />
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <Card class="p-5">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 text-sm font-medium">
          <ListChecks class="h-4 w-4 text-primary" />
          {{ editingId ? '编辑需求' : '新建需求' }}
        </div>
        <Button v-if="editingId" variant="ghost" size="sm" @click="resetForm">取消编辑</Button>
      </div>
      <div class="mt-4 space-y-3">
        <label class="block space-y-1.5">
          <span class="text-xs text-muted-foreground">需求标题</span>
          <Input v-model="form.title" placeholder="例如：登录、浏览商品并加入购物车" maxlength="256" />
        </label>
        <label class="block space-y-1.5">
          <span class="text-xs text-muted-foreground">需求内容</span>
          <Textarea v-model="form.content" rows="4" placeholder="描述业务预期、边界条件与失败路径；不要把未确认的推断写成事实。" />
        </label>
        <div class="grid gap-3 sm:grid-cols-[1fr_140px]">
          <div>
            <span class="text-xs text-muted-foreground">关联页面</span>
            <div v-if="!pages.length" class="mt-1 text-xs text-muted-foreground">先采集页面后再关联。</div>
            <div v-else class="mt-2 grid max-h-32 gap-1 overflow-y-auto rounded-md border border-border p-2 sm:grid-cols-2">
              <label v-for="page in pages" :key="page.id" class="flex items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-muted">
                <Checkbox :model-value="form.related_page_ids.includes(page.id)" @update:model-value="(checked) => toggleRelatedPage(page.id, checked)" />
                <span class="truncate">{{ page.title || page.url }}</span>
              </label>
            </div>
          </div>
          <label class="space-y-1.5">
            <span class="text-xs text-muted-foreground">生成用例上限</span>
            <Input v-model="form.max_cases" type="number" min="1" max="10" />
          </label>
        </div>
        <div class="flex justify-end">
          <Button :disabled="saving" @click="submit">
            <Plus v-if="!editingId" class="h-4 w-4" />
            {{ saving ? '保存中…' : editingId ? '保存修改' : '创建需求' }}
          </Button>
        </div>
      </div>
    </Card>

    <Card v-if="loading" class="p-5">
      <div v-for="index in 3" :key="index" class="mb-3 h-16 animate-pulse rounded bg-muted" />
    </Card>

    <EmptyState
      v-else-if="!requirements.length"
      title="还没有测试需求"
      description="先写一条需求，例如“正确密码登录成功并跳转商品列表；错误密码应提示错误”。"
    >
      <template #icon><ListChecks class="h-5 w-5" /></template>
    </EmptyState>

    <div v-else class="space-y-3">
      <Card v-for="requirement in requirements" :key="requirement.id" class="p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h4 class="text-base font-semibold">{{ requirement.title }}</h4>
              <Badge variant="muted">{{ requirement.status }}</Badge>
              <Badge variant="default">{{ (requirement.related_page_ids || []).length }} 个页面</Badge>
            </div>
            <p class="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{{ requirement.content }}</p>
          </div>
          <div class="flex shrink-0 gap-1">
            <Button variant="outline" size="sm" @click="edit(requirement)">编辑</Button>
            <Button variant="ghost" size="icon" class="text-muted-foreground hover:text-destructive" @click="remove(requirement)">
              <Trash2 class="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>

    <ConfirmDialog
      :open="!!pendingDelete"
      title="删除测试需求"
      :description="pendingDelete ? `确认删除「${pendingDelete.title}」？` : ''"
      confirm-text="确认删除"
      destructive
      @confirm="confirmDeleteRequirement"
      @close="pendingDelete = null"
    />
  </div>
</template>
