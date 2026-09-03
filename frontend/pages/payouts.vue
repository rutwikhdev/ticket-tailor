<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Payout, PayoutStatusFilter, ReportPeriod } from '~/lib/api'
import { useApi, VALID_PERIODS } from '~/lib/api'
import { formatDateOnly, formatMoney, formatStatus, reportingLabel } from '~/utils/formatters'
import { queryPage, queryValue } from '~/utils/query'

useSeoMeta({ title: 'Payouts' })

const route = useRoute()
const api = useApi()
const pageSize = 20
const validStatuses: PayoutStatusFilter[] = ['all', 'paid', 'unpaid', 'processing']

const period = computed<ReportPeriod>({
  get() {
    const value = queryValue(route.query.period) as ReportPeriod | undefined
    return value && VALID_PERIODS.includes(value) ? value : 'all_time'
  },
  set(value) {
    void navigateTo({ path: route.path, query: { ...route.query, period: value === 'all_time' ? undefined : value, page: undefined } })
  },
})

const status = computed<PayoutStatusFilter>({
  get() {
    const value = queryValue(route.query.status) as PayoutStatusFilter | undefined
    return value && validStatuses.includes(value) ? value : 'all'
  },
  set(value) {
    void navigateTo({ path: route.path, query: { ...route.query, status: value === 'all' ? undefined : value, page: undefined } })
  },
})

const page = computed<number>({
  get: () => queryPage(route.query.page),
  set(value) {
    void navigateTo({ path: route.path, query: { ...route.query, page: value === 1 ? undefined : String(value) } })
  },
})

const timezone = ref(import.meta.client ? Intl.DateTimeFormat().resolvedOptions().timeZone : '')
const payouts = useClientData(
  () => api.getPayouts({ status: status.value, period: period.value, timezone: timezone.value, page: page.value, page_size: pageSize }),
  [status, period, page, timezone],
)

const statusItems = [
  { label: 'All statuses', value: 'all' },
  { label: 'Paid', value: 'paid' },
  { label: 'Unpaid', value: 'unpaid' },
  { label: 'Processing', value: 'processing' },
] satisfies { label: string; value: PayoutStatusFilter }[]

const columns: TableColumn<Payout>[] = [
  { accessorKey: 'id', header: 'Payout' },
  { accessorKey: 'amount', header: 'Amount' },
  { accessorKey: 'status', header: 'Status' },
  { accessorKey: 'arrival_date', header: 'Arrival date' },
  { accessorKey: 'transaction_count', header: 'Transactions' },
  { accessorKey: 'included_in_reporting', header: 'Reporting' },
]

watch(() => payouts.data.value?.page_count, (pageCount) => {
  if (pageCount && page.value > pageCount) page.value = pageCount
})
</script>

<template>
  <div class="flex h-[calc(100dvh-3rem)] min-h-[480px] flex-col gap-6">
    <header class="border-b border-default pb-4">
      <div class="flex items-center gap-2">
        <h1 class="text-xl font-semibold text-highlighted">Payouts</h1>
        <UBadge v-if="payouts.pending.value && payouts.data.value" label="Refreshing" color="neutral" variant="subtle" size="sm" />
      </div>
      <p class="mt-2 max-w-2xl text-sm text-muted">Track payout status, expected arrival, and the transactions included in each transfer.</p>
    </header>

    <section aria-label="Payout filters" class="grid gap-4 border-b border-default pb-4 sm:flex sm:items-center sm:justify-end">
      <label class="w-full sm:w-auto">
        <span class="sr-only">Status</span>
        <USelect
          :model-value="status"
          :items="statusItems"
          value-key="value"
          size="md"
          variant="ghost"
          class="w-full data-[state=open]:bg-elevated sm:w-40"
          @update:model-value="status = $event"
        />
      </label>
      <PeriodFilter v-model="period" />
    </section>

    <UAlert
      v-if="payouts.error.value"
      role="alert"
      title="Payouts could not be refreshed"
      :description="payouts.error.value"
      icon="i-lucide-circle-alert"
      color="error"
      variant="subtle"
    >
      <template #actions>
        <UButton label="Retry" color="error" variant="soft" size="xs" @click="payouts.refresh" />
      </template>
    </UAlert>

    <section aria-label="Payout results" class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div class="min-h-0 flex-1">
        <UTable
          v-if="payouts.data.value"
          :data="payouts.data.value.items"
          :columns="columns"
          :loading="payouts.pending.value"
          loading-color="primary"
          sticky
          :ui="{
            root: 'h-full w-full overflow-auto',
            base: 'w-full border-separate border-spacing-0',
            thead: '[&>tr]:bg-elevated/50',
            th: 'border-y border-default px-4 py-3 text-xs font-medium text-muted first:rounded-l-lg first:border-l last:rounded-r-lg last:border-r',
            td: 'border-b border-default px-4 py-3.5 text-sm text-default',
          }"
        >
        <template #id-cell="{ row }">
          <div class="flex items-start gap-3">
            <span class="mt-0.5 flex shrink-0 rounded-full bg-elevated p-2 ring ring-inset ring-default">
              <UIcon name="i-lucide-ticket" class="size-4 text-muted" />
            </span>
            <div class="min-w-0">
              <p class="truncate font-medium text-highlighted">Payout</p>
              <p class="mt-0.5 max-w-52 truncate font-mono text-[11px] text-dimmed">{{ row.original.id }}</p>
            </div>
          </div>
        </template>

        <template #amount-cell="{ row }">
          <span class="financial-number font-semibold text-highlighted">{{ formatMoney(row.original.amount, row.original.currency) }}</span>
        </template>

        <template #status-cell="{ row }">
          <UBadge
            :label="formatStatus(row.original.status)"
            :color="row.original.status === 'paid' ? 'success' : 'neutral'"
            variant="subtle"
            size="sm"
          />
        </template>

        <template #arrival_date-cell="{ row }">
          <span>{{ formatDateOnly(row.original.arrival_date) }}</span>
        </template>

        <template #transaction_count-cell="{ row }">
          <span class="financial-number">{{ row.original.transaction_count }}</span>
        </template>

        <template #included_in_reporting-cell="{ row }">
          <UBadge
            :label="reportingLabel(row.original)"
            :color="row.original.included_in_reporting ? 'success' : 'neutral'"
            variant="subtle"
            size="sm"
          />
        </template>

        <template #empty>
          <div class="flex flex-col items-center px-4 py-10 text-center">
            <UIcon name="i-lucide-landmark" class="mb-3 size-5 text-dimmed" />
            <p class="text-sm font-medium text-highlighted">No payouts</p>
            <p class="mt-1 text-sm text-muted">There are no payouts for the selected filters.</p>
          </div>
        </template>
      </UTable>

      <div v-else-if="payouts.pending.value" class="p-4">
        <USkeleton class="h-10 w-full" />
        <USkeleton v-for="index in 8" :key="index" class="mt-3 h-13 w-full" />
      </div>
      </div>

      <PaginationFooter
        v-if="payouts.data.value"
        :page="page"
        :total="payouts.data.value.total"
        :page-size="payouts.data.value.page_size"
        @update:page="page = $event"
      />
    </section>
  </div>
</template>
