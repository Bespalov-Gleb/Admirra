import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import { requiredProjectSlots } from '../src/utils/projectSlots.js'
import { FALLBACK_PLANS, perProjectLine } from '../src/utils/pricingPlans.js'

async function moduleWithMocks(path, bindings, exports) {
  const source = (await readFile(new URL(path, import.meta.url), 'utf8'))
    .replace(/^import .*$/gm, '').replace(/^export /gm, '')
  return new Function(...Object.keys(bindings), source + '\nreturn {' + exports.join(',') + '}')(...Object.values(bindings))
}

test('number of places includes existing overflow', () => {
  assert.equal(requiredProjectSlots({ current: 3, limit: 3 }), 1)
  assert.equal(requiredProjectSlots({ current: 4, limit: 3 }), 2)
  assert.equal(requiredProjectSlots({ current: 12, limit: 10 }), 3)
  assert.equal(requiredProjectSlots({ current: 12, limit: 10, requested_total: 15 }), 5)
})

test('catalog prices and per-project amounts', () => {
  assert.deepEqual(['start', 'agency', 'pro'].map(k => FALLBACK_PLANS[k].price_rub), [2900, 6900, 13900])
  assert.deepEqual(['start', 'agency', 'pro'].map(k => FALLBACK_PLANS[k].extra_project_price_month), [1100, 800, 650])
  assert.match(perProjectLine(2900, 3), /^967 ₽/)
  assert.match(perProjectLine(6900, 10), /^690 ₽/)
  assert.match(perProjectLine(13900, 25), /^556 ₽/)
})

for (const reason of ['confirmation_required', 'overflow_limit_reached', 'overflow_hard_blocked']) {
  for (const status of ['success', 'cancelled']) {
    test(reason + ': payment ' + status, async () => {
      const calls = []
      let createCount = 0
      const api = { post: async (path, payload) => {
        calls.push(path)
        if (++createCount === 1) throw { response: { status: 409, data: { detail: { reason, current: 4, limit: 3 } } } }
        return { data: { id: 'created' } }
      } }
      const { createProjectWithOverflow } = await moduleWithMocks('../src/utils/createProject.js', {
        api, requiredProjectSlots,
        useOverflowModal: () => ({ requestOverflowConfirm: async () => 'buy', openOverflowInfo: async () => 'buy' }),
        purchaseSlots: async count => { assert.equal(count, 2); return { status } },
      }, ['createProjectWithOverflow'])
      const result = await createProjectWithOverflow({ name: 'Test' })
      assert.equal(calls.length, status === 'success' ? 2 : 1)
      assert.equal(result?.data?.id ?? null, status === 'success' ? 'created' : null)
    })
  }
}

test('cancel and temporary overflow never start payment', async () => {
  for (const choice of [false, 'confirm']) {
    const calls = []
    const api = { post: async (...args) => {
      calls.push(args)
      if (calls.length === 1) throw { response: { status: 409, data: { detail: { reason: 'confirmation_required' } } } }
      return { data: { id: 'created' } }
    } }
    const { createProjectWithOverflow } = await moduleWithMocks('../src/utils/createProject.js', {
      api, requiredProjectSlots,
      useOverflowModal: () => ({ requestOverflowConfirm: async () => choice }),
      purchaseSlots: async () => assert.fail('payment must not run'),
    }, ['createProjectWithOverflow'])
    await createProjectWithOverflow({})
    if (choice === 'confirm') assert.deepEqual(calls[1][2], { params: { confirm_overflow: true } })
    else assert.equal(calls[1][0], 'billing/overflow/decline')
  }
})

test('payment is single-flight and waits for server confirmation', async () => {
  let finish
  let eventCount = 0
  const { purchaseSlots } = await moduleWithMocks('../src/utils/purchaseSlots.js', {
    api: {
      post: async () => ({ data: { expected_purchased_slots: 2 } }),
      get: async () => ({ data: { purchased_slots: 2 } }),
    },
    payWithCloudPayments: () => new Promise(resolve => { finish = resolve }),
    window: { dispatchEvent: () => eventCount++ }, Event,
  }, ['purchaseSlots'])
  const first = purchaseSlots(2)
  await Promise.resolve()
  await assert.rejects(purchaseSlots(2), /уже выполняется/)
  finish({ status: 'success' })
  assert.equal((await first).confirmed, true)
  assert.equal(eventCount, 1)
})

test('opening a new modal settles the previous pending request', async () => {
  const { useOverflowModal } = await moduleWithMocks('../src/composables/useOverflowModal.js', {
    reactive: value => value,
  }, ['useOverflowModal'])
  const { requestOverflowConfirm, openOverflowInfo, close } = useOverflowModal()
  const first = requestOverflowConfirm({})
  const second = openOverflowInfo({})
  assert.equal(await first, false)
  close('buy')
  assert.equal(await second, 'buy')
})
