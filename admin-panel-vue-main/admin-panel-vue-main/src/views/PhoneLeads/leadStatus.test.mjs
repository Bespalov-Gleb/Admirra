import assert from 'node:assert/strict'
import { test } from 'node:test'
import { leadStatus } from './leadStatus.js'

test('an unfinished check is not a negative lead judgement', () => {
  assert.equal(leadStatus({ status: 'PENDING', is_accepted: false }).text, 'Проверяется')
  assert.equal(leadStatus({ validation_state: 'held', is_accepted: false }).text, 'Требует сверки')
  assert.equal(leadStatus({ validation_state: 'closed', status: 'PENDING' }).text, 'Закрыта без проверки')
})
test('legacy final result remains compatible', () => {
  assert.equal(leadStatus({ is_accepted: true }).text, 'Принят')
  assert.equal(leadStatus({ is_accepted: false }).text, 'Отклонён')
})
