<script setup lang="ts">
import { Input as ShadcnInput } from './input'

defineOptions({ inheritAttrs: false })
</script>

<template>
  <ShadcnInput v-bind="$attrs" />
</template>
