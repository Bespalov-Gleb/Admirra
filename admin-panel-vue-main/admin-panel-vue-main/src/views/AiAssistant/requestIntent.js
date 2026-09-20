// Keep the request identity across a dropped SSE/refresh, not the prompt text.
const KEY = 'admirra-assistant-request-v1'
let memory = null
function read() {
  try { return JSON.parse(sessionStorage.getItem(KEY)) || memory } catch { return memory }
}
function write(value) {
  memory = value
  try { value ? sessionStorage.setItem(KEY, JSON.stringify(value)) : sessionStorage.removeItem(KEY) } catch { /* private mode */ }
}
export async function identifyRequest(body, accountKey) {
  // JWT subject is a dedupe namespace only; the server validates authentication.
  try { accountKey = JSON.parse(atob(accountKey.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub || accountKey } catch { /* cookie auth */ }
  const { conversation_id, ...content } = body
  const bytes = new TextEncoder().encode(JSON.stringify({ accountKey, ...content }))
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('')
  let record = read()
  if (!record || record.hash !== hash || ![record.conversationId, record.replyConversationId].includes(conversation_id || null)) {
    record = { hash, id: crypto.randomUUID(), conversationId: conversation_id || null, replyConversationId: null }
    write(record)
  }
  return { ...body, conversation_id: record.conversationId || undefined, request_id: record.id }
}
export function rememberConversation(id) {
  const record = read()
  if (record) write({ ...record, replyConversationId: id })
}
export function completeRequest() { write(null) }
