export const AUTH_TOKEN_KEY = 'auth_token'
export const AUTH_PROVIDER_KEY = 'auth_provider'

let accessToken = sessionStorage.getItem(AUTH_TOKEN_KEY) || localStorage.getItem(AUTH_TOKEN_KEY) || ''

export function getAccessToken() {
  return accessToken || sessionStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAccessToken(token) {
  accessToken = token || ''
  if (accessToken) {
    sessionStorage.setItem(AUTH_TOKEN_KEY, accessToken)
    localStorage.removeItem(AUTH_TOKEN_KEY)
  } else {
    sessionStorage.removeItem(AUTH_TOKEN_KEY)
  }
}

export function clearAccessToken() {
  accessToken = ''
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function getAuthProvider() {
  return localStorage.getItem(AUTH_PROVIDER_KEY) || ''
}

export function setAuthProvider(provider) {
  if (provider) {
    localStorage.setItem(AUTH_PROVIDER_KEY, provider)
  } else {
    localStorage.removeItem(AUTH_PROVIDER_KEY)
  }
}

export function clearAuthProvider() {
  localStorage.removeItem(AUTH_PROVIDER_KEY)
}
