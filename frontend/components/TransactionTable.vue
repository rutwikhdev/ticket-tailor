<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Transaction } from '~/lib/api'
import { formatDateOnly, formatMoney, formatStatus, statusColor } from '~/utils/formatters'

const props = withDefaults(defineProps<{
  items?: Transaction[]
  pending?: boolean
  compact?: boolean
}>(), {
  items: () => [],
  pending: false,
  compact: false,
})

const columns: TableColumn<Transaction>[] = [
  { accessorKey: 'order_reference', header: 'Order' },
  { accessorKey: 'type', header: 'Type' },
  { accessorKey: 'amount', header: 'Amount' },
  { accessorKey: 'stripe_fee', header: 'Stripe fee' },
  { accessorKey: 'ticket_tailor_fee', header: 'TT fee' },
  { accessorKey: 'net', header: 'Net' },
  { accessorKey: 'available_on', header: 'Available' },
  { accessorKey: 'status', header: 'Status' },
]

const visibleColumns = computed(() => props.compact
  ? columns.filter(column => !('accessorKey' in column) || !['stripe_fee', 'ticket_tailor_fee'].includes(String(column.accessorKey)))
  : columns,
)

function formatFee(value: number, currency: string): string {
  return formatMoney(value === 0 ? 0 : -value, currency)
}
</script>

<template>
  <UTable
    :data="items"
    :columns="visibleColumns"
    :loading="pending && items.length > 0"
    loading-color="primary"
    sticky
    empty="No transactions found for these filters."
    :ui="{
      root: 'h-full w-full overflow-auto',
      base: 'w-full border-separate border-spacing-0',
      thead: '[&>tr]:bg-elevated/50',
      th: 'border-y border-default px-4 py-3 text-xs font-medium text-muted first:rounded-l-lg first:border-l last:rounded-r-lg last:border-r',
      td: 'border-b border-default px-4 py-3.5 text-sm text-default',
    }"
  >
    <template #order_reference-cell="{ row }">
      <div class="flex items-start gap-3">
        <span class="mt-0.5 flex shrink-0 rounded-full bg-elevated p-2 ring ring-inset ring-default">
          <UIcon name="i-lucide-ticket" class="size-4 text-muted" />
        </span>
        <div class="min-w-0">
          <p class="truncate font-medium text-highlighted">{{ row.original.order_reference || 'No order reference' }}</p>
          <p class="mt-0.5 max-w-48 truncate font-mono text-[11px] text-dimmed">{{ row.original.id }}</p>
          <p v-if="row.original.related_charge_id" class="mt-0.5 max-w-48 truncate font-mono text-[11px] text-dimmed">
            Charge {{ row.original.related_charge_id }}
          </p>
        </div>
      </div>
    </template>

    <template #type-cell="{ row }">
      <UBadge
        :label="formatStatus(row.original.type)"
        color="neutral"
        variant="subtle"
        size="sm"
      />
    </template>

    <template #amount-cell="{ row }">
      <span class="financial-number font-medium text-highlighted">{{ formatMoney(row.original.amount, row.original.currency) }}</span>
    </template>

    <template #stripe_fee-cell="{ row }">
      <span class="financial-number text-muted">{{ formatFee(row.original.stripe_fee, row.original.currency) }}</span>
    </template>

    <template #ticket_tailor_fee-cell="{ row }">
      <span class="financial-number text-muted">{{ formatFee(row.original.ticket_tailor_fee, row.original.currency) }}</span>
    </template>

    <template #net-cell="{ row }">
      <span class="financial-number font-semibold text-highlighted">{{ formatMoney(row.original.net, row.original.currency) }}</span>
    </template>

    <template #available_on-cell="{ row }">
      <span>{{ formatDateOnly(row.original.available_on) }}</span>
    </template>

    <template #status-cell="{ row }">
      <UBadge
        v-if="row.original.status"
        :label="formatStatus(row.original.status)"
        :color="statusColor(row.original.status)"
        variant="subtle"
        size="sm"
      />
      <span v-else class="text-muted">Not applicable</span>
    </template>

    <template #empty>
      <div class="flex flex-col items-center px-4 py-10 text-center">
        <UIcon name="i-lucide-receipt" class="mb-3 size-5 text-dimmed" />
        <p class="text-sm font-medium text-highlighted">No transactions</p>
        <p class="mt-1 text-sm text-muted">There are no records for the selected filters.</p>
      </div>
    </template>
  </UTable>
</template>
