import { test } from 'node:test'
import assert from 'node:assert/strict'
import { consumerReadiness, createReadinessCompletion, readinessKey, readinessMessage, detectorReadinessTitle } from './consumerReadiness.js'

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
test('completion is once per preparation, including retries with a new deadline', () => {
  const notify = createReadinessCompletion()
  const state = { id: 'a', deadline: 'later', status: 'waiting' }
  assert.equal(notify(state), false)
  assert.equal(notify({ ...state, status: 'held' }), false)
  assert.equal(notify({ ...state, status: 'ready' }), true)
  assert.equal(notify({ ...state, status: 'ready' }), false)
  assert.equal(notify({ ...state, status: 'ready', deadline: 'new deadline' }), true)
  assert.equal(notify({ status: 'ready' }), false)
  assert.notEqual(readinessKey(state), readinessKey({ ...state, id: 'b' }))
})
test('detector describes history, not missing dashboard statistics', () => {
  const value = { status: 'waiting', message: 'Обновляем недостающие данные. Повторите действие после завершения.' }
  assert.equal(readinessMessage(value, 'detector'), 'Анализируем данные…')
  assert.doesNotMatch(readinessMessage(value, 'detector'), /Повторите действие/)
  assert.equal(readinessMessage(value), value.message)
  assert.match(readinessMessage(value, 'detector', true), /Не удалось проверить/)
})
test('titles distinguish preparation, held, ready and unknown history', () => {
  assert.equal(detectorReadinessTitle([{ status: 'waiting' }]), 'Анализируем данные…')
  assert.equal(detectorReadinessTitle([{ status: 'held' }]), 'Подготовка истории приостановлена')
  assert.equal(detectorReadinessTitle([{ status: 'ready' }]), 'История для детектора готова')
  assert.equal(detectorReadinessTitle([null]), 'Проверяем полноту данных для детектора')
  assert.notEqual(detectorReadinessTitle([{ status: 'ready' }, null]), 'История для детектора готова')
  assert.equal(detectorReadinessTitle([{ status: 'waiting' }, { status: 'held' }]), 'Подготовка истории приостановлена')
  assert.equal(detectorReadinessTitle([{ status: 'waiting', poll_error: true }]), 'Не удалось проверить данные')
})
