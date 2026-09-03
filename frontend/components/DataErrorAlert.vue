<script setup lang="ts">
import type { ApiRequestError } from '~/lib/api'
import { getApiErrorTitle } from '~/lib/api'

defineProps<{
  error: ApiRequestError
  title?: string
}>()

const emit = defineEmits<{
  retry: []
}>()
</script>

<template>
  <UAlert
    v-if="error"
    role="alert"
    :title="title || getApiErrorTitle(error)"
    :description="error.message"
    icon="i-lucide-circle-alert"
    color="error"
    variant="subtle"
  >
    <template #actions>
      <UButton label="Retry" color="error" variant="soft" size="xs" @click="emit('retry')" />
    </template>
  </UAlert>
</template>
