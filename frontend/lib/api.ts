export type ReportPeriod =
  | 'today'
  | 'yesterday'
  | 'this_week'
  | 'last_week'
  | 'this_month'
  | 'last_month'
  | 'all_time'

export type TransactionKind = 'sale' | 'refund'
export type PayoutStatusFilter = 'all' | 'paid' | 'unpaid' | 'processing'
export type PayoutStatus = Exclude<PayoutStatusFilter, 'all'>

export const VALID_PERIODS: ReportPeriod[] = ['today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month', 'all_time']
export const VALID_KINDS: TransactionKind[] = ['sale', 'refund']

export interface ReportPeriodDetails {
  key: ReportPeriod
  timezone: string
  start_date: string | null
  end_date_exclusive: string | null
}

export interface RevenueSummary {
  net_revenue: number
  payouts_completed: number
  available_to_payout: number
  pending: number
}

export interface RevenueBreakdown {
  gross_sales: number
  refunds: number
  ticket_tailor_fees: number
  stripe_fees: number
  net_revenue: number
}

export interface PayoutScheduleItem {
  id: string
  amount: number
  currency: string
  status: PayoutStatus
  arrival_date: string
}

export interface OverviewResponse {
  currency: string
  period: ReportPeriodDetails
  summary: RevenueSummary
  revenue_breakdown: RevenueBreakdown
  payout_schedule: PayoutScheduleItem[]
  excluded_unreconciled_count: number
}

export interface Transaction {
  id: string
  type: TransactionKind
  order_reference: string | null
  related_charge_id: string | null
  currency: string
  amount: number
  stripe_fee: number
  ticket_tailor_fee: number
  net: number
  status: string | null
  available_on: string
  reconciled: boolean
  included_in_reporting: boolean
}

export interface Payout {
  id: string
  currency: string
  amount: number
  status: PayoutStatus
  arrival_date: string
  transaction_count: number
  reconciled: boolean
  included_in_reporting: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  page_count: number
}

export type TransactionsResponse = PaginatedResponse<Transaction>
export type PayoutsResponse = PaginatedResponse<Payout>

type QueryValue = string | number | boolean | null | undefined

export class ApiRequestError extends Error {
  statusCode?: number

  constructor(message: string, statusCode?: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.statusCode = statusCode
  }
}

function normalizeError(error: unknown): ApiRequestError {
  if (error instanceof ApiRequestError) return error

  const fetchError = error as {
    data?: string | { detail?: string; message?: string }
    statusCode?: number
    statusMessage?: string
    message?: string
  }
  const payload = fetchError?.data
  const payloadMessage = typeof payload === 'string' ? payload : payload?.detail || payload?.message
  const message = payloadMessage || fetchError?.statusMessage || fetchError?.message || 'The request could not be completed.'

  return new ApiRequestError(message, fetchError?.statusCode)
}

export function getApiErrorMessage(error: unknown, fallback = 'Unable to load data.'): string {
  const normalized = normalizeError(error)
  return normalized.message === 'The request could not be completed.' ? fallback : normalized.message
}

async function apiRequest<T>(baseURL: string, path: string, query?: Record<string, QueryValue>): Promise<T> {
  try {
    return await $fetch<T>(path, {
      baseURL,
      query,
    })
  } catch (error) {
    throw normalizeError(error)
  }
}

export function useApi() {
  const config = useRuntimeConfig()
  const baseURL = import.meta.server ? config.apiBaseUrl : config.public.apiBaseUrl

  return {
    getOverview: (params: { period: ReportPeriod; timezone: string }) =>
      apiRequest<OverviewResponse>(baseURL, '/api/reports/overview', params),
    getTransactions: (params: {
      kind: TransactionKind
      period: ReportPeriod
      timezone: string
      page: number
      page_size: number
    }) => apiRequest<TransactionsResponse>(baseURL, '/api/transactions', params),
    getPayouts: (params: {
      status: PayoutStatusFilter
      period: ReportPeriod
      timezone: string
      page: number
      page_size: number
    }) => apiRequest<PayoutsResponse>(baseURL, '/api/payouts', params),
  }
}
