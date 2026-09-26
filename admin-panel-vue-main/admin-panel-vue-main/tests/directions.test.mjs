import { test } from 'node:test'
import assert from 'node:assert/strict'
import { effectScope, reactive, nextTick } from 'vue'
import { useDirectionData } from '../src/composables/useDirectionData.js'

const flush = async () => { await nextTick(); await Promise.resolve(); await Promise.resolve() }
const row = (name = 'Газобетон') => ({ id: name, name, campaign_ids: ['campaign-1'], campaign_count: 1, masks: [{ mask: name }] })
function setup(t) {
  const filters = reactive({ client_id: 'p1', channel: 'yandex', start_date: '2026-09-01', end_date: '2026-09-07' })
  const requests = [], accepted = []
  const api = { get(url, config) { return new Promise((resolve, reject) => requests.push({ url, config, resolve: data => resolve({ data }), reject })) } }
  const scope = effectScope()
  const data = scope.run(() => useDirectionData(api, () => filters, stats => accepted.push(stats)))
  t.after(() => scope.stop())
  return { filters, requests, accepted, scope, ...data }
}
test('list renders before slow statistics; repeated opens reuse in-flight request', async t => {
  const h = setup(t)
  h.fetchDirections(); h.fetchDirections()
  await flush()
  assert.equal(h.requests.length, 2)
  assert.equal(h.directionsLoading.value, true)
  h.requests[0].resolve([row()]); await flush()
  assert.equal(h.directionOptions.value[0].name, 'Газобетон')
  assert.equal(h.directionStats.value.items.length, 0)
  assert.equal(h.directionsLoading.value, false)
  await h.fetchDirections()
  assert.equal(h.requests.length, 2)
})
test('date changes refetch only stats, not definitions', async t => {
  const h = setup(t); await flush()
  h.requests[0].resolve([row()]); await flush()
  h.filters.start_date = '2026-08-01'; h.filters.end_date = '2026-08-07'; await flush()
  assert.equal(h.requests.length, 3)
  assert.match(h.requests[2].url, /stats$/)
  assert.equal(h.directionOptions.value.length, 1)
  assert.equal(h.requests[1].config.signal.aborted, true)
})
test('project switch sends one pair, late old responses cannot leak rows or stats', async t => {
  const h = setup(t); await flush()
  h.filters.client_id = 'p2'; await flush()
  assert.equal(h.requests.length, 4)
  h.requests[0].resolve([row('old')]); h.requests[1].resolve({ items: [row('old')] }); await flush()
  assert.deepEqual(h.directionOptions.value, [])
  assert.equal(h.accepted.length, 0)
  h.requests[2].resolve([row('new')]); await flush()
  assert.equal(h.directionOptions.value[0].name, 'new')
})
test('channel change clears rows; same-scope statistics cannot replace definitions', async t => {
  const h = setup(t); await flush()
  h.requests[0].resolve([row()]); await flush()
  h.filters.channel = 'vk'; await flush()
  assert.deepEqual(h.directionOptions.value, [])
  h.requests[2].resolve([row('VK')]); h.requests[3].resolve({ items: [row('VK'), { id: 'unassigned', is_unassigned: true }] }); await flush()
  assert.equal(h.directionOptions.value.length, 2)
})
test('mutation refresh supersedes in-flight reads, then uses new matches', async t => {
  const h = setup(t); await flush()
  const refresh = h.refreshDirections(); await flush()
  assert.equal(h.requests.length, 4)
  h.requests[0].resolve([row('deleted')]); h.requests[1].resolve({ items: [row('deleted')] })
  h.requests[2].resolve([row('created')]); h.requests[3].resolve({ items: [row('created')] })
  await refresh
  assert.equal(h.directionOptions.value[0].name, 'created')
  assert.equal(h.accepted.length, 1)
})
test('stats failure does not hide definitions; list failure is not successful empty state', async t => {
  const h = setup(t); await flush()
  h.requests[0].reject(new Error('503')); h.requests[1].reject(new Error('502')); await flush()
  assert.equal(h.directionsLoading.value, false)
  assert.match(h.directionsError.value, /Не удалось/)
  const retry = h.fetchDirections(); await flush()
  h.requests[2].resolve([row()]); await retry
  assert.equal(h.directionsError.value, '')
  assert.equal(h.directionOptions.value.length, 1)
})
test('no client makes no requests and leaving the page cancels pending reads', async t => {
  const h = setup(t)
  h.filters.client_id = null; await flush()
  assert.equal(h.requests.length, 0)
  h.filters.client_id = 'p2'; await flush()
  h.scope.stop()
  for (const r of h.requests) { assert.equal(r.config.signal.aborted, true); r.resolve([row('late')]) }
  await flush()
  assert.deepEqual(h.directionOptions.value, [])
})
test('successful empty definitions are cached briefly; force refresh bypasses it', async t => {
  const h = setup(t); await flush()
  h.requests[0].resolve([]); await flush()
  await h.fetchDirections()
  assert.equal(h.requests.length, 2)
  h.fetchDirections({ force: true }); await flush()
  assert.equal(h.requests.length, 3)
})
