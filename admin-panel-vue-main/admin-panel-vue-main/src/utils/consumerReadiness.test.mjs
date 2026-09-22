import { test } from 'node:test'
import assert from 'node:assert/strict'
import { consumerReadiness } from './consumerReadiness.js'

test('old API waiting state is finite, unknown states are hidden', () => {
  assert.equal(consumerReadiness('waiting_data').status, 'held')
  assert.equal(consumerReadiness('regenerate'), null)
  assert.equal(consumerReadiness(null), null)
})
test('waiting requires an identifier and a finite future deadline', () => {
  const value = { id: 'request', status: 'waiting', deadline: '2026-09-22T12:00:00Z' }
  assert.equal(consumerReadiness(value, Date.parse('2026-09-22T11:59:00Z')).status, 'waiting')
  assert.equal(consumerReadiness(value, Date.parse(value.deadline)).status, 'held')
  assert.equal(consumerReadiness({ ...value, deadline: 'broken' }).status, 'held')
  assert.equal(value.status, 'waiting')
})
test('ready is not a command to run a paid action', () => {
  assert.deepEqual(consumerReadiness({ status: 'ready', id: 'request' }), { status: 'ready', id: 'request' })
})
test('held retry stays controlled by the server', () => {
  assert.equal(consumerReadiness({ status: 'held', can_retry: false }).can_retry, false)
})
