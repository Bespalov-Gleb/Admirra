import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { diagnosticError } from './diagnosticError.js'

test('quota uses bounded retry time; upstream details never reach UI', () => {
  assert.match(diagnosticError({ response: { status: 429, headers: { 'retry-after': '61' } } }), /2 мин/)
  assert.match(diagnosticError({ response: { status: 429, headers: { 'retry-after': '86400' } } }), /1440 мин/)
  assert.match(diagnosticError({ response: { status: 429, headers: { 'retry-after': 'invalid' } } }), /позже/)
  for (const status of [0, 401, 403, 404, 422, 429, 500, 503]) {
    assert.ok(!diagnosticError({ message: 'SECRET', response: { status, data: { detail: 'SECRET' } } }).includes('SECRET'))
  }
  assert.match(diagnosticError({ response: { status: 503 } }), /временно недоступен/)
})

test('component compiles and distinguishes a failed request from a rejected lead', () => {
  const filename = new URL('./PhoneAPI.vue', import.meta.url)
  const source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source, { filename: filename.pathname })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'phone-api-test' })
  const template = compileTemplate({ source: descriptor.template.content, id: 'phone-api-test',
    filename: filename.pathname, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  assert.match(source, /if \(loading.value\) return/)
  assert.match(source, /const diagnostic = testMode.value/)
  assert.match(source, /Проверка не выполнена/)
  assert.match(source, /заявка не сохранена/)
  assert.ok(!source.includes("console.error('Validation error:'"))
})
