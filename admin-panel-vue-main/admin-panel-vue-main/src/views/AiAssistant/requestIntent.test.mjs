import assert from 'node:assert/strict'
import { test } from 'node:test'
import { identifyRequest, rememberConversation, completeRequest } from './requestIntent.js'

const data = new Map()
globalThis.sessionStorage = { getItem: key => data.get(key), setItem: (key, val) => data.set(key, val), removeItem: key => data.delete(key) }
const jwt = (sub, exp) => `header.${Buffer.from(JSON.stringify({ sub, exp })).toString('base64url')}.signature`

test('network retry keeps identity after meta and access-token renewal', async () => {
  completeRequest()
  const body = { message: 'Analyse', attachment_ids: [], effort: 'medium' }
  const first = await identifyRequest(body, jwt('owner', 1))
  rememberConversation('conversation-1')
  const retry = await identifyRequest({ ...body, conversation_id: 'conversation-1' }, jwt('owner', 2))
  assert.equal(first.request_id, retry.request_id)
  assert.equal(retry.conversation_id, undefined)
  assert.ok(![...data.values()].join('').includes('Analyse'))
  const changed = await identifyRequest({ ...body, message: 'Different' }, jwt('owner', 2))
  assert.notEqual(changed.request_id, first.request_id)
})

test('successful completion or another user creates a new intent', async () => {
  completeRequest()
  const body = { message: 'Hello' }
  const first = await identifyRequest(body, jwt('owner', 1))
  const other = await identifyRequest(body, jwt('other', 1))
  assert.notEqual(first.request_id, other.request_id)
  completeRequest()
  const next = await identifyRequest(body, jwt('other', 1))
  assert.notEqual(next.request_id, other.request_id)
})
