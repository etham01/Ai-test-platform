<script setup lang="ts">
import { Textarea as ShadcnTextarea } from './textarea'

defineOptions({ inheritAttrs: false })
</script>

<template>
  <ShadcnTextarea v-bind="$attrs" />
</template>
