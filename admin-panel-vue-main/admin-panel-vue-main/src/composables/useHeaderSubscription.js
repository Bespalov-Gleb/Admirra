import { shallowRef, watch } from 'vue'
import api from '../api/axios'
import { useAuth } from './useAuth'
import { createAccountSnapshot } from '../utils/accountSnapshot'

const snapshot = shallowRef({ data: null, loading: false, error: false })
const store = createAccountSnapshot({
  load: async () => (await api.get('billing/subscription')).data,
  publish: (value) => { snapshot.value = value },
})
// Module-scoped: shared by MainLayout / MockupLayout headers. Reset synchronously
// at logout/account switch so a previous account's quota is never displayed.
const { user } = useAuth()
watch(() => user.value?.id, (id) => {
  store.setAccount(id)
  if (id) store.refresh()
}, { immediate: true, flush: 'sync' })

export function useHeaderSubscription() {
  return { subscriptionSnapshot: snapshot, loadSubscription: store.refresh }
}
