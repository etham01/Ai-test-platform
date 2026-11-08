<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, useAttrs } from 'vue'

import { cn } from '@/lib/utils'
import { Badge as ShadcnBadge } from './badge'

defineOptions({ inheritAttrs: false })

type LegacyVariant = 'default' | 'success' | 'warning' | 'muted' | 'destructive'

const props = withDefaults(defineProps<{ variant?: LegacyVariant }>(), {
  variant: 'default',
})

const attrs = useAttrs()

const mappedVariant = computed(() => {
  if (props.variant === 'muted') return 'secondary'
  if (props.variant === 'success' || props.variant === 'warning') return 'outline'
  return props.variant
})

const semanticClass = computed(() => {
  if (props.variant === 'success') return 'border-success/20 bg-success/10 text-success'
  if (props.variant === 'warning') return 'border-warning/20 bg-warning/10 text-warning'
  return undefined
})

const classes = computed(() =>
  cn(semanticClass.value, attrs.class as HTMLAttributes['class']),
)

const forwardedAttrs = computed(() => {
  const copy = { ...attrs }
  delete copy.class
  return copy
})
</script>

<template>
  <ShadcnBadge :variant="mappedVariant" :class="classes" v-bind="forwardedAttrs">
    <slot />
  </ShadcnBadge>
</template>
