import { test } from 'node:test'
import assert from 'node:assert/strict'
import { reportExportError } from './reportExportError.js'

test('shows JSON 409 detail from an Axios blob', async () => {
  const data = new Blob([JSON.stringify({ detail: 'Данные ещё не готовы' })], { type: 'application/json' })
  assert.equal(await reportExportError({ response: { data } }, 'Ошибка'), 'Данные ещё не готовы')
})
test('plain JSON detail is preserved', async () => {
  assert.equal(await reportExportError({ response: { data: { detail: 'Нет доступа' } } }, 'Ошибка'), 'Нет доступа')
})
test('network, HTML, large body and non-text details use fallback', async () => {
  for (const data of [null, new Blob(['<html>bad gateway</html>']), new Blob(['x'.repeat(20000)]), { detail: [] }]) {
    assert.equal(await reportExportError({ response: { data } }, 'Ошибка'), 'Ошибка')
  }
  assert.equal(await reportExportError({}, 'Ошибка'), 'Ошибка')
})
