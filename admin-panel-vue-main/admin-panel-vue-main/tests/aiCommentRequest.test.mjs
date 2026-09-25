import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createAiCommentRequest, aiCommentError } from '../src/utils/aiCommentRequest.js'

const waiting = (clock = 0) => ({ status: 'waiting', id: 'r', deadline: new Date(clock + 600000).toISOString() })
const ready = { status: 'ready', id: 'r' }
const held = { status: 'held', id: 'r', can_retry: true }
function setup({ initial = null, statuses = [ready], generation, retry = ready } = {}) {
  let clock = 0
  const calls = [], phases = []
  const api = {
    async get(url) {
      calls.push(['GET', url])
      const data = url === 'ai/comment' ? { data_readiness: initial } : statuses.shift()
      if (data instanceof Error) throw data
      return { data }
    },
    async post(url) {
      calls.push(['POST', url])
      if (url.endsWith('/retry')) return { data: retry }
      if (generation instanceof Error) throw generation
      return { data: { text: 'done' } }
    },
  }
  const request = createAiCommentRequest({ api, now: () => clock, sleep: async ms => { clock += ms }, onPhase: p => phases.push(p) })
  const run = () => request.run({ client_id: 'p', start_date: '2026-09-01', end_date: '2026-09-07' })
  return { api, request, run, calls, phases }
}
test('no action on construction; ready data generates once', async () => {
  const h = setup()
  assert.deepEqual(h.calls, [])
  assert.equal((await h.run()).text, 'done')
  assert.deepEqual(h.calls, [['GET', 'ai/comment'], ['POST', 'ai/generate-report']])
})
test('one click waits, then sends exactly one generation without another click', async () => {
  const h = setup({ initial: waiting(), statuses: [waiting(), ready] })
  const one = h.run(), duplicate = h.run()
  assert.equal(one, duplicate)
  await one
  assert.deepEqual(h.calls.map(c => c[1]), ['ai/comment', 'data-refresh/r', 'data-refresh/r', 'ai/generate-report'])
  assert.deepEqual(h.phases, ['preparing', 'generating', 'idle'])
})
test('GET 502 retries before generation, not the generation itself', async () => {
  const error = Object.assign(new Error('502'), { response: { status: 502 } })
  const h = setup({ initial: waiting(), statuses: [error, ready] })
  await h.run()
  assert.equal(h.calls.filter(c => c[0] === 'POST').length, 1)
})
for (const status of [409, 429, 500, 502, 504, undefined]) {
  test(`generation ${status || 'disconnect'} is NEVER replayed`, async () => {
    const error = Object.assign(new Error('failed'), { response: status ? { status, data: {} } : undefined })
    const h = setup({ generation: error })
    await assert.rejects(h.run())
    assert.equal(h.calls.filter(c => c[0] === 'POST').length, 1)
  })
}
test('explicit new click can retry an OLD held preparation once', async () => {
  const h = setup({ initial: held, retry: waiting() })
  await h.run()
  assert.deepEqual(h.calls.filter(c => c[0] === 'POST').map(c => c[1]), ['data-refresh/r/retry', 'ai/generate-report'])
})
test('a failure during preparation stops, no automatic restart or model call', async () => {
  const h = setup({ initial: waiting(), statuses: [held] })
  await assert.rejects(h.run(), /подготовить данные/)
  assert.equal(h.calls.filter(c => c[0] === 'POST').length, 0)
})
test('legacy/invalid/unretryable readiness does not bypass protection', async () => {
  for (const initial of ['waiting_data', { status: 'unknown' }, { status: 'held' }]) {
    const h = setup({ initial })
    await assert.rejects(h.run())
    assert.equal(h.calls.filter(c => c[0] === 'POST').length, 0)
  }
})
test('deadline bounds wait without generation', async () => {
  const h = setup({ initial: { ...waiting(), deadline: new Date(1000).toISOString() } })
  await assert.rejects(h.run(), /подготовить данные/)
  assert.equal(h.calls.length, 1)
})
test('navigation/scope cancellation prevents later ready response from starting model', async () => {
  const h = setup()
  let resolve
  h.api.get = () => new Promise(r => { resolve = r })
  const pending = h.run()
  h.request.cancel()
  resolve({ data: { data_readiness: ready } })
  await assert.rejects(pending, { name: 'AbortError' })
  assert.equal(h.calls.length, 0)
})
test('cancelled old request cannot reset a newer request phase', async () => {
  const h = setup()
  const resolves = []
  h.api.get = () => new Promise(r => resolves.push(r))
  const old = h.run()
  h.request.cancel()
  const next = h.run()
  resolves[0]({ data: {} })
  await assert.rejects(old)
  assert.equal(h.phases.at(-1), 'preparing')
  resolves[1]({ data: {} })
  await next
  assert.equal(h.calls.length, 1)
})
test('user-facing cancellation is silent; post-generation 409 is explicit, not autostart', () => {
  assert.equal(aiCommentError({ name: 'AbortError' }), '')
  assert.match(aiCommentError({ response: { status: 409 } }), /Данные изменились/)
})
