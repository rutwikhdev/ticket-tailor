<script setup lang="ts">
const props = defineProps<{
  page: number
  total: number
  pageSize: number
}>()

const emit = defineEmits<{
  'update:page': [value: number]
}>()

const resultStart = computed(() => props.total ? ((props.page - 1) * props.pageSize) + 1 : 0)
const resultEnd = computed(() => Math.min(props.page * props.pageSize, props.total))
</script>

<template>
  <footer
    v-if="total > 0"
    class="flex flex-col gap-4 border-t border-default px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
  >
    <p class="financial-number text-xs text-muted">
      Showing {{ resultStart }}-{{ resultEnd }} of {{ total }}
    </p>
    <UPagination
      :page="page"
      :total="total"
      :items-per-page="pageSize"
      :sibling-count="1"
      size="sm"
      @update:page="emit('update:page', $event)"
    />
  </footer>
</template>
