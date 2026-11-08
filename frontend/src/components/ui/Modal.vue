<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './dialog'

defineProps<{
  open: boolean
  title: string
}>()

const emit = defineEmits<{
  close: []
}>()

function onOpenChange(value: boolean) {
  if (!value) emit('close')
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpenChange">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-3xl">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription class="sr-only">对话框内容</DialogDescription>
      </DialogHeader>
      <slot />
      <DialogFooter v-if="$slots.footer">
        <slot name="footer" />
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
