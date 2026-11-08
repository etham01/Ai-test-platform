import { onUnmounted, ref } from 'vue'

import { api } from '@/api/client'
import type { Task } from '@/types/api'

const TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

export function useTaskPolling() {
  const task = ref<Task | null>(null)
  const error = ref<string | null>(null)
  let timer: number | undefined
  let stopped = false

  function stop() {
    stopped = true
    if (timer) {
      window.clearTimeout(timer)
      timer = undefined
    }
  }

  async function start(taskId: string, onDone?: (task: Task) => void) {
    stop()
    stopped = false
    error.value = null

    const tick = async () => {
      if (stopped) return
      try {
        const current = await api.getTask(taskId)
        task.value = current
        if (TERMINAL.has(current.status)) {
          stop()
          onDone?.(current)
          return
        }
      } catch (caught) {
        error.value = caught instanceof Error ? caught.message : '任务状态查询失败'
        stop()
        return
      }
      timer = window.setTimeout(tick, 1500)
    }

    await tick()
  }

  onUnmounted(stop)

  return { task, error, start, stop }
}
