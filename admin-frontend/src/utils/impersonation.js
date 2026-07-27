export async function openImpersonatedCabinet(requestToken) {
  // Окно создаётся синхронно в обработчике клика, иначе браузер может
  // заблокировать его как popup, пока мы ждём ответ API.
  const target = window.open('about:blank', '_blank')
  try {
    const token = await requestToken()
    const url = new URL('/signin', window.location.origin.replace('admin.', ''))
    // JWT передаётся во fragment: он не попадает в access-логи nginx.
    url.hash = `impersonation_token=${encodeURIComponent(token)}`
    if (target) {
      target.opener = null
      target.location.replace(url.toString())
    } else {
      window.location.assign(url.toString())
    }
  } catch (error) {
    target?.close()
    throw error
  }
}
