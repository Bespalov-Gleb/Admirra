import { test } from 'node:test'
import assert from 'node:assert/strict'
import { reportReadiness } from './reportReadiness.js'

test('legacy and verified reports retain the usual approval UI', () => {
  assert.equal(reportReadiness({}), null)
  assert.equal(reportReadiness({ data_readiness: { status: 'ready' } }), null)
})
test('waiting never offers send or restart', () => {
  const view = reportReadiness({ data_readiness: { status: 'waiting', can_retry: true } })
  assert.equal(view.title, 'Ожидаем данные')
  assert.equal(view.canRetry, false)
})
test('held retry requires explicit server permission', () => {
  const state = { status: 'held', reason: 'deadline_expired' }
  assert.equal(reportReadiness({ data_readiness: state }).canRetry, false)
  assert.equal(reportReadiness({ data_readiness: { ...state, can_retry: true } }).canRetry, true)
})
test('unknown internal reasons are not reflected to the user', () => {
  assert.equal(reportReadiness({ data_readiness: { status: 'held', reason: '<secret>' } }).detail.includes('<secret>'), false)
})
