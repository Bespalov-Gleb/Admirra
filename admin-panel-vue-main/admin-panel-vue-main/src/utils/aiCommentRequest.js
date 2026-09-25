import { consumerReadiness } from './consumerReadiness.js'
import { isTransientSyncPollError } from './syncJobPolling.js'

const abortError = () => Object.assign(new Error('Отменено'), { name: 'AbortError' })
const preparationError = () => new Error('Не удалось подготовить данные для анализа. Проверьте подключение и попробуйте ещё раз.')
const sleepWithSignal = (ms, signal) => new Promise((resolve, reject) => {
  const abort = () => { clearTimeout(timer); reject(abortError()) }
  const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve() }, ms)
  signal.addEventListener('abort', abort, { once: true })
  if (signal.aborted) abort()
})

// One explicit user intent, at most ONE generation POST. All automatic retries
// precede it and only read preparation status. Never replay an ambiguous LLM call.
export function createAiCommentRequest({ api, onPhase = () => {}, now = Date.now, sleep = sleepWithSignal, pollMs = 10000 }) {
  let active = null
  const cancel = () => {
    const previous = active
    active = null
    previous?.controller.abort()
    onPhase('idle')
  }
  const run = (payload) => {
    if (active) return active.promise
    const request = { controller: new AbortController() }
    active = request
    const { signal } = request.controller
    const check = () => { if (signal.aborted || active !== request) throw abortError() }
    const phase = (value) => { check(); onPhase(value) }
    const get = async (url, params) => {
      for (let attempt = 0; ; attempt++) {
        check()
        try {
          const response = await api.get(url, { params, signal, timeout: 20000 })
          check()
          return response.data
        } catch (error) {
          check()
          if (!isTransientSyncPollError(error) || attempt >= 2) throw error
          await sleep(1000 * 2 ** attempt, signal)
        }
      }
    }
    request.promise = (async () => {
      try {
        phase('preparing')
        // GET performs coverage preflight, but never calls the model. Background
        // page loading/old ready notices cannot create this explicit intent.
        if (payload.client_id) {
          const data = await get('ai/comment', {
            client_id: payload.client_id, start_date: payload.start_date, end_date: payload.end_date,
          })
          let state = consumerReadiness(data?.data_readiness, now())
          if (data?.data_readiness && data.data_readiness !== 'regenerate' && !state) throw preparationError()
          if (state?.status === 'held' && state.can_retry && state.id) {
            // One explicit retry of an old preparation, not of AI generation.
            const response = await api.post(`data-refresh/${encodeURIComponent(state.id)}/retry`, null, { signal, timeout: 20000 })
            check()
            state = consumerReadiness(response.data, now())
            if (!state) throw preparationError()
          }
          const deadline = now() + 10 * 60 * 1000
          while (state?.status === 'waiting') {
            check()
            const remaining = Math.min(deadline, Date.parse(state.deadline)) - now()
            if (remaining <= 0) throw preparationError()
            await sleep(Math.min(pollMs, remaining), signal)
            check()
            if (now() >= deadline || now() >= Date.parse(state.deadline)) throw preparationError()
            state = consumerReadiness(await get(`data-refresh/${encodeURIComponent(state.id)}`), now())
            if (!state) throw preparationError()
          }
          if (state && state.status !== 'ready') throw preparationError()
        }
        phase('generating')
        const response = await api.post('ai/generate-report', { ...payload, report_type: 'dashboard_comment' }, { signal, timeout: 180000 })
        check()
        return response.data
      } finally {
        if (active === request) { active = null; onPhase('idle') }
      }
    })()
    return request.promise
  }
  return { run, cancel }
}

export function aiCommentError(error) {
  if (error?.name === 'AbortError' || error?.code === 'ERR_CANCELED') return ''
  const detail = error?.response?.data?.detail
  if (detail?.data_readiness || error?.response?.status === 409) {
    return 'Данные изменились во время подготовки. Нажмите «Повторить», чтобы получить актуальный комментарий.'
  }
  if (typeof detail === 'string') return detail
  if (error?.response?.status >= 500 || error?.code === 'ECONNABORTED' || error?.code === 'ERR_NETWORK') {
    return 'Не удалось получить ответ. Автоматически повторять запрос не будем. Проверьте соединение и попробуйте позже.'
  }
  return error?.message || 'Не удалось получить комментарий. Попробуйте ещё раз.'
}
