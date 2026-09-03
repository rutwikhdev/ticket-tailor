export function queryValue(value: unknown): string | undefined {
  return Array.isArray(value) ? String(value[0]) : typeof value === 'string' ? value : undefined
}

export function queryPage(value: unknown): number {
  const parsed = Number(queryValue(value))
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1
}
