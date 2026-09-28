/* First tagged visit, shared by the landing page and SPA. No analytics request. */
;(function () {
  var key = 'admirra_signup_utm'
  var ttl = 30 * 24 * 60 * 60 * 1000
  var fields = ['source', 'medium', 'campaign']
  function clean(value) {
    return typeof value === 'string' ? value.replace(/[\u0000-\u001f\u007f-\u009f]/g, ' ').trim().slice(0, 120) : ''
  }
  try {
    var now = Date.now()
    var existing = document.cookie.split('; ').find(function (part) { return part.indexOf(key + '=') === 0 })
    if (existing) {
      try {
        var saved = JSON.parse(decodeURIComponent(existing.slice(key.length + 1)))
        if (saved && typeof saved.expires === 'number' && saved.expires > now && saved.expires <= now + ttl &&
            fields.some(function (f) { return clean(saved['utm_' + f]) })) return
      } catch (_) { /* Replace invalid/expired metadata, never break signup. */ }
    }
    var params = new URL(window.location.href).searchParams
    var value = { expires: now + ttl }
    fields.forEach(function (f) { var text = clean(params.get('utm_' + f)); if (text) value['utm_' + f] = text })
    if (!fields.some(function (f) { return value['utm_' + f] })) return
    document.cookie = key + '=' + encodeURIComponent(JSON.stringify(value)) +
      '; Path=/; Max-Age=2592000; SameSite=Lax' + (window.location.protocol === 'https:' ? '; Secure' : '')
  } catch (_) { /* Blocked cookies or malformed URL must not block authorization. */ }
})()
