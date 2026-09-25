import { ref } from 'vue'
import api from '@/api/axios'
const state = ref({})
let pending, loadedAt = 0, generation = 0
export function useOnboarding() {
  function reset() { generation++; pending = null; loadedAt = 0; state.value = {} }
  async function refresh(force = false) {
    if (pending && !force) return pending
    if (!force && Date.now() - loadedAt < 15000) return state.value
    const revision = ++generation
    const request = api.get('billing/signup-discount').then(({ data }) => {
      if (revision === generation) { state.value = data; loadedAt = Date.now() }
      return data
    }).catch(() => { if (revision === generation) state.value = {}; return null }).finally(() => { if (pending === request) pending = null })
    pending = request
    return request
  }
  return { state, refresh, reset }
}
