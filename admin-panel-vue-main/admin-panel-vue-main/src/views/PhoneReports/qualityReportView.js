export function rejectionRows(value) {
  if (!value || typeof value !== 'object') return []
  const rows = Array.isArray(value) ? value : Object.entries(value).map(([reason, count]) => ({ reason, count }))
  return rows.filter(row => row && typeof row.reason === 'string' && Number.isFinite(Number(row.count)))
    .map(row => ({ reason: row.reason, count: Number(row.count) }))
}
