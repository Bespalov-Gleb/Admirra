import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { parse } from '@vue/compiler-sfc'

const { descriptor } = parse(await readFile(new URL('./BillingOperationNotice.vue', import.meta.url), 'utf8'))
function fixture(get) {
  const timers = new Map(), events = []
  let mount, unmount, counter = 0
  const bindings = {
    ref: value => ({ value }), api: { get }, defineEmits: () => (...args) => events.push(args),
    defineExpose() {}, onMounted: fn => { mount = fn }, onBeforeUnmount: fn => { unmount = fn },
    setTimeout: (fn, ms) => { assert.equal(ms, 10000); timers.set(++counter, fn); return counter },
    clearTimeout: id => timers.delete(id),
  }
  const body = descriptor.scriptSetup.content.replace(/^import .*$/gm, '')
  const state = Function(...Object.keys(bindings), body + '\nreturn { operation, error, refresh, check }')(...Object.values(bindings))
  return { ...state, events, timers, mount: () => mount(), unmount: () => unmount() }
}
test('checks status only, polls boundedly, and never resends payment', async () => {
  let calls = 0
  const f = fixture(async url => { assert.equal(url, 'billing/provider-operation'); calls++; return { data: { operation: { status: 'queued' } } } })
  await f.mount()
  for (let i = 1; i < 30; i++) await [...f.timers.values()][0]()
  assert.equal(calls, 30)
  assert.equal(f.timers.size, 0)
  assert.match(f.error.value, /повторно отправлять запрос не нужно/)
})
test('unknown outcome stops polling without claiming success', async () => {
  const f = fixture(async () => ({ data: { operation: { status: 'uncertain' } } }))
  await f.mount()
  assert.equal(f.timers.size, 0)
  assert.equal(f.events.filter(([name]) => name === 'settled').length, 0)
})
test('confirmation refreshes subscription once', async () => {
  let operation = { status: 'dispatching' }
  const f = fixture(async () => ({ data: { operation } }))
  await f.mount()
  operation = null
  await f.check()
  await f.check()
  assert.equal(f.events.filter(([name]) => name === 'settled').length, 1)
  assert.equal(f.timers.size, 0)
})
test('late response after unmount does not restart polling', async () => {
  let resolve
  const f = fixture(() => new Promise(r => { resolve = r }))
  const running = f.mount()
  f.unmount()
  resolve({ data: { operation: { status: 'queued' } } })
  await running
  assert.equal(f.timers.size, 0)
  assert.equal(f.operation.value, null)
})
test('network failure retains operation and permits read-only check', async () => {
  let fail = false
  const f = fixture(async () => { if (fail) throw Error('synthetic'); return { data: { operation: { status: 'queued' } } } })
  await f.mount()
  fail = true
  await f.check()
  assert.equal(f.operation.value.status, 'queued')
  assert.equal(f.timers.size, 0)
  assert.match(f.error.value, /сам запрос не повторится/)
  fail = false
  await f.refresh()
  assert.equal(f.error.value, '')
})
