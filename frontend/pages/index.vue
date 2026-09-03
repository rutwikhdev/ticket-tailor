<script setup lang="ts">
import type { ReportPeriod, ReportPeriodDetails, TransactionKind } from '~/lib/api'
import { useApi, VALID_KINDS, VALID_PERIODS } from '~/lib/api'
import { formatDateOnly, formatMoney, formatStatus } from '~/utils/formatters'
import { queryValue } from '~/utils/query'

useSeoMeta({ title: 'Revenue overview' })

const route = useRoute()
const api = useApi()

const period = computed<ReportPeriod>({
  get() {
    const value = queryValue(route.query.period) as ReportPeriod | undefined
    return value && VALID_PERIODS.includes(value) ? value : 'all_time'
  },
  set(value) {
    void navigateTo({
      path: route.path,
      query: { ...route.query, period: value === 'all_time' ? undefined : value },
    })
  },
})

const recentKind = computed<TransactionKind>({
  get() {
    const value = queryValue(route.query.type) as TransactionKind | undefined
    return value && VALID_KINDS.includes(value) ? value : 'sale'
  },
  set(value) {
    void navigateTo({
      path: route.path,
      query: { ...route.query, type: value === 'sale' ? undefined : value },
    })
  },
})

const timezone = ref(import.meta.client ? Intl.DateTimeFormat().resolvedOptions().timeZone : '')

const overview = useClientData(
  () => api.getOverview({ period: period.value, timezone: timezone.value }),
  [period, timezone],
)

const recent = useClientData(
  () => api.getTransactions({
    kind: recentKind.value,
    period: period.value,
    timezone: timezone.value,
    page: 1,
    page_size: 8,
  }),
  [recentKind, period, timezone],
)

const recentTabs = [
  { label: 'Sales', value: 'sale' },
  { label: 'Refunds', value: 'refund' },
] satisfies { label: string; value: TransactionKind }[]

const scheduledPayouts = computed(() =>
  (overview.data.value?.payout_schedule || []).slice(0, 5),
)

function deduction(value: number, currency: string): string {
  return value === 0 ? formatMoney(0, currency) : `-${formatMoney(Math.abs(value), currency)}`
}

function feeDeduction(value: number, currency: string): string {
  return formatMoney(value === 0 ? 0 : -value, currency)
}

function periodRange(details: ReportPeriodDetails | undefined): string {
  if (!details) return 'Loading reporting period...'
  if (!details.start_date) return `All recorded activity in ${details.timezone}`
  if (!details.end_date_exclusive) return `From ${formatDateOnly(details.start_date)}`

  const end = new Date(`${details.end_date_exclusive}T00:00:00Z`)
  end.setUTCDate(end.getUTCDate() - 1)
  const inclusiveEnd = end.toISOString().slice(0, 10)
  return `${formatDateOnly(details.start_date)} to ${formatDateOnly(inclusiveEnd)} in ${details.timezone}`
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-col gap-4 border-b border-default pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-semibold text-highlighted">Overview</h1>
          <UBadge v-if="overview.pending.value && overview.data.value" label="Refreshing" color="neutral" variant="subtle" size="sm" />
        </div>
        <p class="mt-2 text-sm text-muted">{{ periodRange(overview.data.value?.period) }}</p>
      </div>
      <PeriodFilter v-model="period" />
    </header>

    <DataErrorAlert
      v-if="overview.error.value"
      :error="overview.error.value"
      title="Overview could not be refreshed"
      @retry="overview.refresh"
    />

    <template v-if="overview.data.value">
      <section aria-labelledby="summary-heading">
        <h2 id="summary-heading" class="sr-only">Revenue summary</h2>
        <div class="grid gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
          <UCard>
            <div class="flex items-start justify-between gap-3">
              <p class="text-xs font-normal uppercase text-muted">Net revenue</p>
              <span class="flex rounded-full bg-primary/10 p-2 text-primary ring ring-inset ring-primary/25">
                <UIcon name="i-lucide-circle-pound-sterling" class="size-4" />
              </span>
            </div>
            <p class="financial-number mt-2 text-2xl font-semibold text-highlighted">
              {{ formatMoney(overview.data.value.summary.net_revenue, overview.data.value.currency) }}
            </p>
            <p class="mt-2 text-xs text-muted">After refunds and fees</p>
          </UCard>
          <UCard>
            <div class="flex items-start justify-between gap-3">
              <p class="text-xs font-normal uppercase text-muted">Paid to You</p>
              <span class="flex rounded-full bg-primary/10 p-2 text-primary ring ring-inset ring-primary/25">
                <UIcon name="i-lucide-circle-check" class="size-4" />
              </span>
            </div>
            <p class="financial-number mt-2 text-2xl font-semibold text-highlighted">
              {{ formatMoney(overview.data.value.summary.payouts_completed, overview.data.value.currency) }}
            </p>
            <p class="mt-2 text-xs text-muted">Funds already sent</p>
          </UCard>
          <UCard>
            <div class="flex items-start justify-between gap-3">
              <p class="text-xs font-normal uppercase text-muted">Available Soon</p>
              <span class="flex rounded-full bg-primary/10 p-2 text-primary ring ring-inset ring-primary/25">
                <UIcon name="i-lucide-wallet-cards" class="size-4" />
              </span>
            </div>
            <p class="financial-number mt-2 text-2xl font-semibold text-highlighted">
              {{ formatMoney(overview.data.value.summary.available_to_payout, overview.data.value.currency) }}
            </p>
            <p class="mt-2 text-xs text-muted">Transferred on arrival date</p>
          </UCard>
          <UCard>
            <div class="flex items-start justify-between gap-3">
              <p class="text-xs font-normal uppercase text-muted">Pending</p>
              <span class="flex rounded-full bg-primary/10 p-2 text-primary ring ring-inset ring-primary/25">
                <UIcon name="i-lucide-clock-3" class="size-4" />
              </span>
            </div>
            <p class="financial-number mt-2 text-2xl font-semibold text-highlighted">
              {{ formatMoney(overview.data.value.summary.pending, overview.data.value.currency) }}
            </p>
            <p class="mt-2 text-xs text-muted">Not yet available</p>
          </UCard>
        </div>
      </section>

      <UAlert
        v-if="overview.data.value.excluded_unreconciled_count > 0"
        title="Some activity is excluded"
        :description="`${overview.data.value.excluded_unreconciled_count} unreconciled ${overview.data.value.excluded_unreconciled_count === 1 ? 'record is' : 'records are'} not included in these totals.`"
        icon="i-lucide-triangle-alert"
        color="warning"
        variant="subtle"
      />
    </template>

    <section v-if="overview.pending.value && !overview.data.value" aria-label="Loading revenue summary" class="grid gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-4">
      <div v-for="index in 4" :key="index" class="rounded-lg border border-default bg-elevated/25 p-5">
        <USkeleton class="h-4 w-28" />
        <USkeleton class="mt-4 h-8 w-36" />
        <USkeleton class="mt-3 h-3 w-24" />
      </div>
    </section>

    <div class="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="breakdown-heading">
          <div class="mb-4">
            <h2 id="breakdown-heading" class="text-base font-semibold text-highlighted">Revenue Breakdown</h2>
            <p class="mt-1 text-sm text-muted">How gross ticket sales become net revenue.</p>
          </div>

          <UCard v-if="overview.data.value" class="bg-elevated/25" :ui="{ body: 'p-0 sm:p-0' }">
            <dl class="divide-y divide-default">
              <div class="flex items-center justify-between gap-4 px-5 py-4">
                <dt class="text-sm text-muted">Gross ticket sales</dt>
                <dd class="financial-number text-sm font-semibold text-highlighted">{{ formatMoney(overview.data.value.revenue_breakdown.gross_sales, overview.data.value.currency) }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4 px-5 py-4">
                <dt class="text-sm text-muted">Refunds</dt>
                <dd class="financial-number text-sm font-medium text-default">{{ deduction(overview.data.value.revenue_breakdown.refunds, overview.data.value.currency) }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4 px-5 py-4">
                <dt class="text-sm text-muted">Ticket Tailor fees</dt>
                <dd class="financial-number text-sm font-medium text-default">{{ feeDeduction(overview.data.value.revenue_breakdown.ticket_tailor_fees, overview.data.value.currency) }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4 px-5 py-4">
                <dt class="text-sm text-muted">Stripe fees</dt>
                <dd class="financial-number text-sm font-medium text-default">{{ feeDeduction(overview.data.value.revenue_breakdown.stripe_fees, overview.data.value.currency) }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4 bg-secondary/5 px-5 py-4">
                <dt class="text-sm font-semibold text-highlighted">Net revenue</dt>
                <dd class="financial-number text-base font-semibold">{{ formatMoney(overview.data.value.revenue_breakdown.net_revenue, overview.data.value.currency) }}</dd>
              </div>
            </dl>
          </UCard>

          <div v-else-if="overview.pending.value" class="rounded-lg border border-default bg-elevated/25 p-5">
            <USkeleton v-for="row in 5" :key="row" class="mb-4 h-5 w-full last:mb-0" />
          </div>
        </section>

        <section aria-labelledby="schedule-heading" class="flex flex-col">
          <div class="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 id="schedule-heading" class="text-base font-semibold text-highlighted">Payout Schedule</h2>
              <p class="mt-1 text-sm text-muted">Unpaid and processing payouts in the selected period.</p>
            </div>
            <UButton
              v-if="overview.data.value"
              :to="{ path: '/payouts', query: period === 'all_time' ? {} : { period } }"
              label="View payouts"
              trailing-icon="i-lucide-arrow-right"
              color="neutral"
              variant="ghost"
              size="sm"
            />
          </div>

          <div v-if="scheduledPayouts.length" class="flex-1 divide-y divide-default overflow-hidden rounded-lg border border-default bg-default">
            <UCard
              v-for="payout in scheduledPayouts"
              :key="payout.id"
              :ui="{ root: 'rounded-none border-0', body: 'flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-4' }"
            >
              <div class="flex items-center gap-3">
                <span class="grid size-9 shrink-0 place-items-center rounded-md bg-secondary/5">
                  <UIcon name="i-lucide-banknote-arrow-down" class="size-4" />
                </span>
                <div>
                  <p class="financial-number font-semibold text-highlighted">{{ formatMoney(payout.amount, payout.currency) }}</p>
                  <p class="mt-0.5 font-mono text-[11px] text-dimmed">{{ payout.id }}</p>
                </div>
              </div>
              <div class="flex items-center justify-between gap-5 pl-12 sm:justify-end sm:pl-0">
                <div class="text-right">
                  <p class="text-xs text-muted">Arrival date</p>
                  <p class="mt-0.5 text-sm font-medium text-highlighted">{{ formatDateOnly(payout.arrival_date) }}</p>
                </div>
                <UBadge :label="formatStatus(payout.status)" color="neutral" variant="subtle" size="sm" />
              </div>
            </UCard>
          </div>

          <div v-else-if="overview.pending.value && !overview.data.value" class="space-y-px overflow-hidden rounded-lg border border-default">
            <div v-for="index in 3" :key="index" class="flex items-center justify-between bg-default p-5">
              <div class="flex items-center gap-3"><USkeleton class="size-9" /><USkeleton class="h-5 w-28" /></div>
              <USkeleton class="h-5 w-32" />
            </div>
          </div>

          <div v-else-if="overview.data.value" class="rounded-lg border border-dashed border-default px-5 py-10 text-center">
            <UIcon name="i-lucide-calendar-check" class="mx-auto size-5 text-dimmed" />
            <p class="mt-3 text-sm font-medium text-highlighted">No payouts scheduled</p>
            <p class="mt-1 text-sm text-muted">Upcoming unpaid payouts will appear here.</p>
          </div>
        </section>
      </div>

    <section aria-labelledby="recent-heading" class="border-t border-default pt-8">
      <div class="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="recent-heading" class="text-base font-semibold text-highlighted">Recent transactions</h2>
          <p class="mt-1 text-sm text-muted">Latest activity by availability date.</p>
        </div>
        <UTabs
          :model-value="recentKind"
          :items="recentTabs"
          value-key="value"
          :content="false"
          color="neutral"
          size="sm"
          class="w-full sm:w-56"
          @update:model-value="recentKind = $event as TransactionKind"
        />
      </div>

      <DataErrorAlert
        v-if="recent.error.value"
        :error="recent.error.value"
        title="Recent transactions could not be refreshed"
        class="mb-4"
        @retry="recent.refresh"
      />

      <div class="overflow-hidden">
        <TransactionTable
          v-if="recent.data.value"
          :items="recent.data.value.items"
          :pending="recent.pending.value"
          compact
        />
        <div v-else-if="recent.pending.value" class="p-4">
          <USkeleton class="h-9 w-full" />
          <USkeleton v-for="index in 5" :key="index" class="mt-3 h-12 w-full" />
        </div>
      </div>
    </section>
  </div>
</template>
