<script setup lang="ts">
import type { ReportPeriod } from '~/lib/api'

defineProps<{
  modelValue: ReportPeriod
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ReportPeriod]
}>()

const periods = [
  { label: 'Today', value: 'today' },
  { label: 'Yesterday', value: 'yesterday' },
  { label: 'This Week', value: 'this_week' },
  { label: 'Last Week', value: 'last_week' },
  { label: 'This Month', value: 'this_month' },
  { label: 'Last Month', value: 'last_month' },
  { label: 'All Time', value: 'all_time' },
] satisfies { label: string; value: ReportPeriod }[]
</script>

<template>
  <label class="w-full sm:w-auto">
    <span class="sr-only">Period</span>
    <USelect
      :model-value="modelValue"
      :items="periods"
      value-key="value"
      size="md"
      variant="ghost"
      class="w-full data-[state=open]:bg-elevated sm:w-44"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </label>
</template>
