import { test } from 'node:test'
import assert from 'node:assert/strict'
import { discountStripKey, isDiscountStripHidden, hideDiscountStrip } from './discountStrip.js'

const offer = { eligible: true, active: false, expires_at: '2026-09-29T09:29:10Z' }
const storage = () => {
  const items = new Map()
  return { getItem: key => items.get(key), setItem: (key, value) => items.set(key, value) }
}
test('dismissal persists, does not mutate the offer, and stays account-scoped', () => {
  const store = storage(), before = { ...offer }, key = discountStripKey('account-a', offer)
  assert.equal(isDiscountStripHidden(store, key), false)
  hideDiscountStrip(store, key)
  assert.equal(isDiscountStripHidden(store, discountStripKey('account-a', offer)), true)
  assert.equal(isDiscountStripHidden(store, discountStripKey('account-b', offer)), false)
  assert.deepEqual(offer, before)
})
test('a granted discount reappears; a new offer does not inherit dismissal', () => {
  const store = storage(), key = discountStripKey('account-a', offer)
  hideDiscountStrip(store, key)
  const granted = discountStripKey('account-a', { ...offer, active: true })
  assert.equal(isDiscountStripHidden(store, granted), false)
  hideDiscountStrip(store, granted)
  assert.equal(isDiscountStripHidden(store, granted), true)
  assert.equal(isDiscountStripHidden(store, discountStripKey('account-a', { ...offer, expires_at: '2026-10-01' })), false)
})
test('missing identity, ineligible offers and blocked storage are safe', () => {
  assert.equal(discountStripKey(null, offer), null)
  assert.equal(discountStripKey('account-a', {}), null)
  assert.equal(discountStripKey('account-a', { ...offer, eligible: false }), null)
  const blocked = { getItem() { throw Error('blocked') }, setItem() { throw Error('blocked') } }
  for (const store of [null, blocked]) {
    assert.equal(isDiscountStripHidden(store, 'key'), false)
    assert.doesNotThrow(() => hideDiscountStrip(store, 'key'))
  }
})
