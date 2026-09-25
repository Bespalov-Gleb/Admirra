import { test } from 'node:test'
import assert from 'node:assert/strict'
import { pollSyncJobsUntilDone } from '../src/utils/syncJobPolling.js'

const failure = (status) => Object.assign(new Error('network'), status ? { response: { status } } : {})
function harness(sequence, options = {}) {
  let clock = 0
  const calls = [], ticks = [], delays = []
  return {
    calls, ticks, delays,
    run: () => pollSyncJobsUntilDone(['a', 'a', null], {
      now: () => clock,
      sleep: async (ms) => { clock += ms; delays.push(ms) },
      getJob: async (id, config) => {
        calls.push({ id, config })
        const value = sequence.shift()
        if (value instanceof Error) throw value
        return value || { status: 'RUNNING' }
      },
      onTick: (s) => ticks.push(s), ...options,
    }),
  }
}

for (const status of [undefined, 408, 429, 500, 502, 503, 504]) {
  test(`transient ${status} retains RUNNING, then succeeds without a false FAILED`, async () => {
    const h = harness([{ status: 'RUNNING', progress: 42 }, failure(status), { status: 'SUCCESS' }])
    const r = await h.run()
    assert.deepEqual(r.failed, [])
    assert.deepEqual(r.finished, ['a'])
    assert.equal(h.ticks[1].a.progress, 42)
    assert.equal(h.calls.length, 3)
    assert.deepEqual(h.delays, [4000, 8000])
  })
}
test('initial transport failure is unknown, not FAILED', async () => {
  const h = harness([failure(502), { status: 'SUCCESS' }])
  await h.run()
  assert.deepEqual(h.ticks[0], {})
})
test('only confirmed job failure/cancellation counts as failed', async () => {
  for (const status of ['FAILED', 'CANCELLED']) {
    const r = await harness([{ status, error: 'provider rejected' }]).run()
    assert.deepEqual(r.failed, ['a'])
  }
})
test('persistent outage is bounded with capped backoff', async () => {
  const h = harness(Array.from({ length: 10 }, () => failure(502)))
  await assert.rejects(h.run(), /не означает, что она остановилась/)
  assert.equal(h.calls.length, 6)
  assert.ok(h.delays.every((ms) => ms <= 15000))
})
test('permission/not found responses stop without claiming worker failure', async () => {
  for (const status of [401, 403, 404]) {
    const h = harness([failure(status)])
    await assert.rejects(h.run(), /проверить статус/)
    assert.equal(h.calls.length, 1)
  }
})
test('deadline returns pending, not failed/success; request and delay bounded', async () => {
  const h = harness([], { timeoutMs: 5000 })
  const r = await h.run()
  assert.equal(r.timedOut, true)
  assert.deepEqual(r.failed, [])
  assert.deepEqual(r.finished, [])
  assert.deepEqual(r.pending, ['a'])
  assert.deepEqual(h.delays, [4000, 1000])
  assert.deepEqual(h.calls.map(c => c.config.timeout), [5000, 1000])
})
test('terminal jobs are not polled again while another job is pending', async () => {
  const calls = []
  const r = await pollSyncJobsUntilDone(['a', 'b'], {
    sleep: async () => {},
    getJob: async (id) => {
      calls.push(id)
      return { status: id === 'a' || calls.length > 2 ? 'SUCCESS' : 'RUNNING' }
    },
  })
  assert.deepEqual(calls, ['a', 'b', 'b'])
  assert.deepEqual(r.finished, ['a', 'b'])
})
test('unmount cancellation prevents callbacks after an in-flight response', async () => {
  const controller = new AbortController()
  let ticked = false
  await assert.rejects(pollSyncJobsUntilDone(['a'], {
    signal: controller.signal,
    getJob: async () => { controller.abort(); return { status: 'SUCCESS' } },
    onTick: () => { ticked = true },
  }), /отменено/)
  assert.equal(ticked, false)
})
