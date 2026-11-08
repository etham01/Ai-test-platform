<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/60 px-6 py-14 text-center">
    <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
      <slot name="icon" />
    </div>
    <h3 class="text-base font-semibold text-foreground">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-md text-sm text-muted-foreground">{{ description }}</p>
    <div v-if="$slots.action" class="mt-5">
      <slot name="action" />
    </div>
  </div>
</template>
