// One read generation per view/block. Cancellation is best-effort on the
// transport; the generation guard also rejects late responses from the server.
export function createLatestRequest() {
  let generation = 0
  let active = null
  const cancel = () => {
    generation += 1
    active?.controller.abort()
    active = null
  }
  const run = (key, work) => {
    if (active?.key === key) return active.promise
    cancel()
    const id = generation
    const controller = new AbortController()
    const context = {
      signal: controller.signal,
      isCurrent: () => id === generation && !controller.signal.aborted,
    }
    const promise = Promise.resolve().then(() => {
      if (context.isCurrent()) return work(context)
    }).finally(() => {
      if (active?.promise === promise) active = null
    })
    active = { key, controller, promise }
    return promise
  }
  return { run, cancel }
}
