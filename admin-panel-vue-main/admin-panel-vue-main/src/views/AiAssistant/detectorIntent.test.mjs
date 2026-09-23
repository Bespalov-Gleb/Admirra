import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createDetectorIntent, consumeDetectorIntent, detectorQuestion } from './detectorIntent.js'

const data = new Map()
globalThis.sessionStorage = { getItem: key => data.get(key), setItem: (key, val) => data.set(key, val), removeItem: key => data.delete(key) }
const token = sub => `header.${Buffer.from(JSON.stringify({ sub })).toString('base64url')}.signature`

test('detector prompt contains exact project, period, metric and hypothesis', () => {
  const message = detectorQuestion({ projectId: 'id-1', projectName: 'VK project', startDate: '2026-09-01', endDate: '2026-09-07', campaignName: 'Campaign', alert: { metric: 'cpa', deviation_pct: 35, hypothesis_text: 'Test hypothesis' } })
  for (const text of ['id-1', 'VK project', '2026-09-01', '2026-09-07', 'Campaign', 'CPL', '+35%', 'Test hypothesis', 'инструментов']) assert.ok(message.includes(text))
  assert.ok(!detectorQuestion({ projectId: 'id', alert: {} }).includes('0%'))
})

test('private prompt is not in URL; one intent sends once, never on refresh', () => {
  const route = createDetectorIntent('private detector data', token('owner'))
  assert.equal(route.path, '/ai')
  assert.ok(!JSON.stringify(route).includes('private'))
  assert.ok(![...data.values()].join('').includes(token('owner')))
  assert.equal(consumeDetectorIntent('arbitrary-url-id', token('owner')), null)
  assert.equal(consumeDetectorIntent(route.query.detector, token('owner')), 'private detector data')
  assert.equal(consumeDetectorIntent(route.query.detector, token('owner')), null)
})

test('another account and expired intents cannot auto-send', () => {
  const route = createDetectorIntent('test', token('owner'))
  assert.equal(consumeDetectorIntent(route.query.detector, token('other')), null)
  const expired = createDetectorIntent('test', token('owner'))
  const saved = JSON.parse(data.get('admirra-detector-intent-v1'))
  saved.createdAt -= 6 * 60 * 1000
  data.set('admirra-detector-intent-v1', JSON.stringify(saved))
  assert.equal(consumeDetectorIntent(expired.query.detector, token('owner')), null)
})

test('blocked sessionStorage has a same-tab memory fallback', () => {
  const storage = globalThis.sessionStorage
  globalThis.sessionStorage = { getItem() { throw Error() }, setItem() { throw Error() }, removeItem() { throw Error() } }
  try {
    const route = createDetectorIntent('test', token('owner'))
    assert.equal(consumeDetectorIntent(route.query.detector, token('owner')), 'test')
    assert.equal(consumeDetectorIntent(route.query.detector, token('owner')), null)
  } finally { globalThis.sessionStorage = storage }
})
