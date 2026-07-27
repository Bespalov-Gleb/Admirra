import { reactive } from 'vue'

const state = reactive({ items: [] })
let id = 0

export function useToast() {
  const push = (message, type = 'success', timeout = 4200) => {
    const item = { id: ++id, message, type }
    state.items.push(item)
    window.setTimeout(() => remove(item.id), timeout)
  }
  const remove = (itemId) => {
    const index = state.items.findIndex((item) => item.id === itemId)
    if (index >= 0) state.items.splice(index, 1)
  }
  return {
    toasts: state.items,
    success: (message) => push(message, 'success'),
    error: (message) => push(message, 'error', 6500),
    info: (message) => push(message, 'info'),
    remove,
  }
}
