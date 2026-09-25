// Transport failures are not terminal SyncJob states. Never resubmit a sync
// from this read-only poller; keep the last confirmed status while reconnecting.
const terminal = new Set(['SUCCESS', 'FAILED', 'CANCELLED'])
const statusOf = (job) => String(job?.status || '').trim().toUpperCase()
export const isTransientSyncPollError = (error) => {
  const status = error?.response?.status
  return !status || status === 408 || status === 429 || status >= 500
}

export async function pollSyncJobsUntilDone(jobIds, {
  getJob, onTick, afterPoll, signal,
  intervalMs = 4000, timeoutMs = 20 * 60 * 1000,
  maxConsecutiveErrors = 6,
  now = Date.now,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
} = {}) {
  const ids = [...new Set((jobIds || []).filter(Boolean).map(String))]
  const statuses = {}
  const failures = {}
  const deadline = now() + timeoutMs
  const abort = () => {
    if (signal?.aborted) throw new Error('Ожидание статуса отменено.')
  }
  const result = (timedOut = false) => ({
    finished: ids.filter((id) => terminal.has(statusOf(statuses[id]))),
    failed: ids.filter((id) => ['FAILED', 'CANCELLED'].includes(statusOf(statuses[id]))),
    pending: ids.filter((id) => !terminal.has(statusOf(statuses[id]))),
    statuses, ...(timedOut ? { timedOut: true } : {}),
  })
  if (!ids.length) return result()
  while (now() < deadline) {
    abort()
    const pending = ids.filter((id) => !terminal.has(statusOf(statuses[id])))
    const responses = await Promise.allSettled(pending.map((id) => getJob(id, {
      timeout: Math.max(1, Math.min(10000, deadline - now())), signal,
    })))
    abort()
    let transportError = false
    for (let i = 0; i < responses.length; i++) {
      const response = responses[i]
      const id = pending[i]
      if (response.status === 'fulfilled') {
        statuses[id] = response.value || {}
        failures[id] = 0
      } else {
        transportError = true
        failures[id] = (failures[id] || 0) + 1
        if (!isTransientSyncPollError(response.reason) || failures[id] >= maxConsecutiveErrors) {
          // Deliberately not FAILED: the worker may still be running/succeeded.
          throw new Error('Не удалось проверить статус синхронизации. Это не означает, что она остановилась. Обновите страницу, чтобы проверить результат.')
        }
      }
    }
    if (afterPoll) await afterPoll()
    abort()
    if (onTick) onTick({ ...statuses })
    if (ids.every((id) => terminal.has(statusOf(statuses[id])))) return result()
    const streak = Math.max(0, ...Object.values(failures))
    const delay = transportError ? Math.min(15000, intervalMs * 2 ** streak) : intervalMs
    await sleep(Math.max(0, Math.min(delay, deadline - now())))
  }
  return result(true)
}
