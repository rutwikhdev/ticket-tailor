const moneyFormatters = new Map<string, Intl.NumberFormat>()

export function formatMoney(minorUnits: number, currency = 'GBP'): string {
  let formatter = moneyFormatters.get(currency)

  if (!formatter) {
    formatter = new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
    moneyFormatters.set(currency, formatter)
  }

  return formatter.format(minorUnits / 100)
}

export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return 'Not scheduled'

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return value

  const [, year, month, day] = match
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)))

  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

export function formatStatus(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase())
}
