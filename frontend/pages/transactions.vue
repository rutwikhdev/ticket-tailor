<script setup lang="ts">
import type { ReportPeriod, TransactionKind } from '~/lib/api'
import { useApi, VALID_KINDS, VALID_PERIODS } from '~/lib/api'
import { queryPage, queryValue } from '~/utils/query'

useSeoMeta({ title: 'Transactions' })

const route = useRoute()
const api = useApi()
const pageSize = 20

const period = computed<ReportPeriod>({
  get() {
    const value = queryValue(route.query.period) as ReportPeriod | undefined
    return value && VALID_PERIODS.includes(value) ? value : 'all_time'
  },
  set(value) {
    void navigateTo({ path: route.path, query: { ...route.query, period: value === 'all_time' ? undefined : value, page: undefined } })
  },
})

const kind = computed<TransactionKind>({
  get() {
    const value = queryValue(route.query.type) as TransactionKind | undefined
    return value && VALID_KINDS.includes(value) ? value : 'sale'
  },
  set(value) {
    void navigateTo({ path: route.path, query: { ...route.query, type: value === 'sale' ? undefined : value, page: undefined } })
  },
})

const page = computed<number>({
  get: () => queryPage(route.query.page),
  set(value) {
    void navigateTo({ path: route.path, query: { ...route.query, page: value === 1 ? undefined : String(value) } })
  },
})

const timezone = ref(import.meta.client ? Intl.DateTimeFormat().resolvedOptions().timeZone : '')
const transactions = useClientData(
  () => api.getTransactions({ kind: kind.value, period: period.value, timezone: timezone.value, page: page.value, page_size: pageSize }),
  [kind, period, page, timezone],
)

const tabs = [
  { label: 'Sales', value: 'sale' },
  { label: 'Refunds', value: 'refund' },
] satisfies { label: string; value: TransactionKind }[]

watch(() => transactions.data.value?.page_count, (pageCount) => {
  if (pageCount && page.value > pageCount) page.value = pageCount
})
</script>

<template>
  <div class="flex h-[calc(100dvh-3rem)] min-h-[480px] flex-col gap-6">
    <header class="border-b border-default pb-4">
      <div class="flex items-center gap-2">
        <h1 class="text-xl font-semibold text-highlighted">Transactions</h1>
        <UBadge v-if="transactions.pending.value && transactions.data.value" label="Refreshing" color="neutral" variant="subtle" size="sm" />
      </div>
      <p class="mt-2 max-w-2xl text-sm text-muted">Review sales, refunds, fees, and the amount included in financial reporting.</p>
    </header>

    <section aria-label="Transaction filters" class="flex flex-col gap-4 border-b border-default pb-4 sm:flex-row sm:items-center sm:justify-between">
      <UTabs
        :model-value="kind"
        :items="tabs"
        :content="false"
        color="neutral"
        class="w-full sm:w-64"
        @update:model-value="kind = $event as TransactionKind"
      />
      <PeriodFilter v-model="period" />
    </section>

    <UAlert
      v-if="transactions.error.value"
      role="alert"
      title="Transactions could not be refreshed"
      :description="transactions.error.value"
      icon="i-lucide-circle-alert"
      color="error"
      variant="subtle"
    >
      <template #actions>
        <UButton label="Retry" color="error" variant="soft" size="xs" @click="transactions.refresh" />
      </template>
    </UAlert>

    <section aria-label="Transaction results" class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div class="min-h-0 flex-1">
        <TransactionTable
          v-if="transactions.data.value"
          :items="transactions.data.value.items"
          :pending="transactions.pending.value"
        />

        <div v-else-if="transactions.pending.value" class="p-4">
          <USkeleton class="h-10 w-full" />
          <USkeleton v-for="index in 8" :key="index" class="mt-3 h-13 w-full" />
        </div>
      </div>

      <PaginationFooter
        v-if="transactions.data.value"
        :page="page"
        :total="transactions.data.value.total"
        :page-size="transactions.data.value.page_size"
        @update:page="page = $event"
      />
    </section>
  </div>
</template>
