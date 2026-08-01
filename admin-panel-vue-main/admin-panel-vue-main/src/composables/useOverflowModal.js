import { reactive } from 'vue'

// Глобальное состояние модалки превышения лимита проектов (§8.5 ТЗ экономики).
// Одна модалка на приложение, монтируется в MainLayout; любой поток создания
// проекта вызывает requestOverflowConfirm / openOverflowInfo.
const state = reactive({
  open: false,
  mode: 'confirm', // 'confirm' — можно добавить в запас; 'info' — только апгрейд
  detail: null,
  _resolve: null,
})

function close(result = false) {
  state.open = false
  const resolve = state._resolve
  state._resolve = null
  state.detail = null
  if (resolve) resolve(result)
}

// Показать модалку «добавить в запас» и дождаться решения пользователя.
// true — согласился добавить сверх лимита, false — отменил / ушёл в тарифы.
function requestOverflowConfirm(detail) {
  return new Promise((resolve) => {
    state.detail = detail || {}
    state.mode = 'confirm'
    state.open = true
    state._resolve = resolve
  })
}

// Показать модалку без «добавить пока так» (запас исчерпан / блок) — только
// предложение перейти на старший тариф.
function openOverflowInfo(detail) {
  return new Promise((resolve) => {
    state.detail = detail || {}
    state.mode = 'info'
    state.open = true
    state._resolve = resolve
  })
}

export function useOverflowModal() {
  return { state, close, requestOverflowConfirm, openOverflowInfo }
}
