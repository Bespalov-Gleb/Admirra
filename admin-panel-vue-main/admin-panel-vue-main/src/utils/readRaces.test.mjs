import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createLatestRequest } from './latestRequest.js'

const tick = () => new Promise(resolve => setImmediate(resolve))
const ref = value => ({ value })
async function compile(path, start, end, bindings, result) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8')
  const a = source.indexOf(start), b = source.indexOf(end, a)
  assert.ok(a >= 0 && b > a, `source boundaries: ${path}`)
  return Function(...Object.keys(bindings), source.slice(a, b) + `\nreturn ${result}`)(...Object.values(bindings))
}
function transport() {
  const calls = []
  return { calls, api: { get(path, config) { return new Promise((resolve, reject) => calls.push({ path, config, resolve, reject })) } } }
}

test('Dynamics ignores previous project success/error and aborts on unmount', async () => {
  const t = transport(), cleanup = []
  const b = { api: t.api, props: { clientId: 'old', channel: 'all' }, periods: ref([]), goals: ref([]), meta: ref({}),
    loading: ref(false), granularity: ref('week'), userTouchedGranularity: ref(true),
    horizonDates: () => ({ start: '2026-08-01', end: '2026-09-20' }), onUnmounted: fn => cleanup.push(fn) }
  const fetch = await compile('../views/GeneralStats3/components/DynamicsView.vue', 'let seriesRequestId =', 'const setGranularity =', b, 'fetchSeries')
  const old = fetch()
  b.props.clientId = 'new'
  const current = fetch()
  assert.ok(t.calls[0].config.signal.aborted)
  t.calls[0].reject(new Error('late old error'))
  await old
  assert.equal(b.loading.value, true)
  t.calls[1].resolve({ data: { periods: [{ value: 42 }] } })
  await current
  assert.equal(b.periods.value[0].value, 42)
  const pending = fetch()
  cleanup.forEach(fn => fn())
  assert.ok(t.calls[2].config.signal.aborted)
  t.calls[2].resolve({ data: { periods: [{ value: 999 }] } })
  await pending
  assert.equal(b.periods.value[0].value, 42)
})

test('Reports publishes available history even when the queue is slow or fails', async () => {
  const t = transport(), cleanup = [], errors = []
  const b = { api: t.api, pending: ref([]), history: ref([]), loading: ref(false), createLatestRequest,
    onUnmounted: fn => cleanup.push(fn), refreshReportsQueue() {}, toaster: { error: e => errors.push(e) } }
  const load = await compile('../views/Reports/Reports.vue', 'const reportRequests =', 'const CHANNEL_META =', b, 'load')
  const run = load()
  assert.equal(run, load())
  await tick()
  assert.equal(t.calls.length, 2)
  t.calls.find(c => c.config.params.status === 'history').resolve({ data: [{ id: 'report-1' }] })
  await tick()
  assert.equal(b.history.value[0].id, 'report-1')
  t.calls.find(c => c.config.params.status === 'pending').reject(new Error('queue unavailable'))
  await run
  assert.equal(b.history.value[0].id, 'report-1')
  assert.equal(errors.length, 1)
  assert.equal(b.loading.value, false)
  cleanup.forEach(fn => fn())
})

test('Detector does not show an old project response after switching or clearing scope', async () => {
  const t = transport()
  const b = { api: t.api, summary: ref(null), loading: ref(false), DEMO_MODE: false,
    getCurrentScope: () => false, onScopeDispose() {} }
  const fetch = await compile('../composables/useDetector.js', '  let summaryRequestId =', '  // Детектор ит.4:', b, 'fetchSummary')
  const old = fetch('old'), current = fetch('new')
  t.calls[1].resolve({ data: { project: 'new' } })
  await current
  t.calls[0].resolve({ data: { project: 'old' } })
  await old
  assert.equal(b.summary.value.project, 'new')
  const pending = fetch('third')
  await fetch(null)
  t.calls[2].resolve({ data: { project: 'third' } })
  await pending
  assert.equal(b.summary.value, null)
})
