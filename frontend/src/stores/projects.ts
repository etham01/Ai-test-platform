import { defineStore } from 'pinia'
import { ref } from 'vue'

import { ApiError, api } from '@/api/client'
import type { Project, ProjectCreate } from '@/types/api'

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return '未知错误'
}

export const useProjectsStore = defineStore('projects', () => {
  const items = ref<Project[]>([])
  const total = ref(0)
  const loading = ref(false)
  const creating = ref(false)
  const error = ref<string | null>(null)
  const notice = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const page = await api.listProjects({ page: 1, page_size: 50 })
      items.value = page.items
      total.value = page.total
    } catch (caught) {
      error.value = errorMessage(caught)
    } finally {
      loading.value = false
    }
  }

  async function create(payload: ProjectCreate): Promise<Project> {
    creating.value = true
    error.value = null
    try {
      const project = await api.createProject(payload)
      items.value = [project, ...items.value]
      total.value += 1
      notice.value = `项目「${project.name}」已创建`
      return project
    } catch (caught) {
      error.value = errorMessage(caught)
      throw caught
    } finally {
      creating.value = false
    }
  }

  async function remove(projectId: number) {
    error.value = null
    try {
      await api.deleteProject(projectId)
      items.value = items.value.filter((item) => item.id !== projectId)
      total.value = Math.max(0, total.value - 1)
      notice.value = '项目已删除（软删除，执行历史仍保留在数据库中）'
    } catch (caught) {
      error.value = errorMessage(caught)
      throw caught
    }
  }

  function clearNotice() {
    notice.value = null
  }

  return {
    items,
    total,
    loading,
    creating,
    error,
    notice,
    load,
    create,
    remove,
    clearNotice,
  }
})
