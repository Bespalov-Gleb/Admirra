import test from 'node:test'
import assert from 'node:assert/strict'
import { createLatestRequest } from './latestRequest.js'

test('same in-flight key is deduplicated; a new key aborts and fences old results', async () => {
  const loader = createLatestRequest()
  const contexts = []
  const pending = []
  const work = ctx => { contexts.push(ctx); return new Promise(resolve => pending.push(resolve)) }
  const first = loader.run('old', work)
  assert.equal(loader.run('old', work), first)
  await Promise.resolve()
  const second = loader.run('new', work)
  await Promise.resolve()
  assert.equal(contexts[0].signal.aborted, true)
  assert.equal(contexts[0].isCurrent(), false)
  assert.equal(contexts[1].isCurrent(), true)
  pending[0]()
  await first
  assert.equal(loader.run('new', work), second)
  loader.cancel()
  assert.equal(contexts[1].isCurrent(), false)
  pending[1]()
  await second
})

test('unmounted or superseded work does not even start before its microtask', async () => {
  const loader = createLatestRequest()
  const pending = loader.run('period', () => assert.fail('obsolete request started'))
  loader.cancel()
  await pending
})
