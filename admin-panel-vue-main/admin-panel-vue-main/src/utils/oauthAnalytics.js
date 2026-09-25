// Only the backend's explicit creation flag is authoritative. Never infer signup
// from account age: linking/login shortly after registration is not a conversion.
export function createOAuthTracker({ goal, identity, storage, decode = atob }) {
  const sent = new Set()
  return function track(data, provider) {
    if (!['yandex', 'vk', 'max'].includes(provider) || !data?.access_token) return
    // Bind to THIS response's token, not an older account in the browser.
    try { Promise.resolve(identity(data.access_token)).catch(() => {}) } catch {}
    if (data.is_new_user !== true) return
    let subject
    try {
      const segment = data.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
      subject = JSON.parse(decode(segment.padEnd(Math.ceil(segment.length / 4) * 4, '='))).sub
    } catch { return }
    if (!subject) return
    for (const event of ['signup_complete', 'signup', 'trial_start']) {
      const key = `admirra:oauth-goal:${provider}:${subject}:${event}`
      let stored = false
      try { stored = storage?.getItem(key) === '1' } catch {}
      if (sent.has(key) || stored) continue
      try {
        // false means there was no counter queue; do not mark unsent events.
        if (goal(event, { method: provider }) === false) continue
        sent.add(key)
        try { storage?.setItem(key, '1') } catch {}
      } catch { /* analytics must never break authentication */ }
    }
  }
}
