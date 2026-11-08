<script setup lang="ts">
import { Button as ShadcnButton } from './button'

defineOptions({ inheritAttrs: false })
</script>

<template>
  <ShadcnButton v-bind="{ type: 'button', ...$attrs }">
    <slot />
  </ShadcnButton>
</template>
