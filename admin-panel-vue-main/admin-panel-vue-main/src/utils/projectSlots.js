// Include projects already using the temporary overflow, not just the new one.
export function requiredProjectSlots(detail = {}) {
  const current = Number(detail.current || 0)
  const limit = Number(detail.limit || 0)
  const requested = Number(detail.requested_total ?? current + 1)
  return Math.max(1, Math.ceil(requested - limit))
}
