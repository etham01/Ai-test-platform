<script setup lang="ts">
import { Card as ShadcnCard } from './card'

defineOptions({ inheritAttrs: false })
</script>

<template>
  <ShadcnCard v-bind="$attrs">
    <slot />
  </ShadcnCard>
</template>
