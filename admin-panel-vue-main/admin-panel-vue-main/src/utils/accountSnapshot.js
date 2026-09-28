// In-memory, account-scoped snapshot. No fabricated defaults or persistent cache.
export function createAccountSnapshot({ load, publish, now = Date.now, ttlMs = 30_000 }) {
  let account = null, generation = 0, flight = null, updatedAt = 0
  let state = { data: null, loading: false, error: false }
  const update = (patch) => { state = { ...state, ...patch }; publish(state) }

  function setAccount(id) {
    const next = id == null ? null : String(id)
    if (next === account) return
    account = next
    generation += 1
    flight = null
    updatedAt = 0
    update({ data: null, loading: false, error: false })
  }

  function refresh({ force = false } = {}) {
    if (!account) return Promise.resolve()
    if (flight) {
      // A usage-change event can arrive after the server read started. Read once
      // more afterwards; never let the earlier response undo the fresh balance.
      if (force) flight.again = true
      return flight.promise
    }
    if (!force && state.data && now() - updatedAt < ttlMs) return Promise.resolve()
    const request = { again: false, generation, promise: null }
    flight = request
    update({ loading: true, error: false })
    request.promise = (async () => {
      do {
        request.again = false
        try {
          const data = await load()
          if (request.generation !== generation) return
          if (!request.again) {
            updatedAt = now()
            update({ data, error: false })
          }
        } catch {
          if (request.generation !== generation) return
          if (!request.again) update({ error: true })
        }
      } while (request.again && request.generation === generation)
    })().finally(() => {
      if (flight === request) {
        flight = null
        update({ loading: false })
      }
    })
    return request.promise
  }

  return { setAccount, refresh }
}
