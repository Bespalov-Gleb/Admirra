import test from 'node:test'
import assert from 'node:assert/strict'
import { loadProjectSummaries } from './projectSummaries.js'

const channels = () => Object.fromEntries(['all', 'yandex', 'vk', 'avito'].map(c => [c, { expenses: 1 }]))
test('bounded sequential pages preserve period and deduplicate projects', async () => {
  const calls = []
  const api = { async get(url, { params }) {
    calls.push({ url, params })
    return { data: Object.fromEntries(params.client_ids.map(id => [id, channels()])) }
  } }
  const ids = Array.from({ length: 130 }, (_, i) => `project-${i}`)
  const result = await loadProjectSummaries(api, [...ids, ids[0]], { period_preset: 'this_month' })
  assert.equal(Object.keys(result).length, 130)
  assert.deepEqual(calls.map(c => c.params.client_ids.length), [64, 64, 2])
  assert.ok(calls.every(c => c.url === 'dashboard/project-summaries' && c.params.period_preset === 'this_month'))
})
test('obsolete response is discarded and cannot start the next page', async () => {
  let current = true
  let calls = 0
  const api = { async get() { calls++; current = false; return { data: {} } } }
  assert.equal(await loadProjectSummaries(api, Array(130).fill(0).map((_, i) => `${i}`), {}, () => current), null)
  assert.equal(calls, 1)
})
test('errors and partial responses never become successful zero statistics', async () => {
  await assert.rejects(loadProjectSummaries({ get: async () => ({ data: {} }) }, ['one'], {}), /Incomplete/)
  await assert.rejects(loadProjectSummaries({ get: async () => { throw new Error('offline') } }, ['one'], {}), /offline/)
})
test('empty scope does not issue a request', async () => {
  assert.deepEqual(await loadProjectSummaries({ get: () => assert.fail('unexpected request') }, [], {}), {})
})
