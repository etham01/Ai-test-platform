<script setup lang="ts">
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    description?: string
    confirmText?: string
    cancelText?: string
    destructive?: boolean
  }>(),
  {
    description: '',
    confirmText: '确认',
    cancelText: '取消',
    destructive: false,
  },
)

const emit = defineEmits<{
  close: []
  confirm: []
}>()

function onOpenChange(value: boolean) {
  if (!value) emit('close')
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpenChange">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription v-if="description">{{ description }}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" @click="emit('close')">{{ cancelText }}</Button>
        <Button :variant="destructive ? 'destructive' : 'default'" @click="emit('confirm')">
          {{ confirmText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
