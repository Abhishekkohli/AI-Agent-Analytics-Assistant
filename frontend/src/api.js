const TOKEN_KEY = 'analytics.token'

export function getToken() {
  return window.localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) window.localStorage.setItem(TOKEN_KEY, token)
  else window.localStorage.removeItem(TOKEN_KEY)
}

async function parseError(res) {
  try {
    const data = await res.json()
    return data.detail || data.message || res.statusText
  } catch {
    return res.statusText || 'Request failed'
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = auth ? getToken() : ''
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!res.ok) {
    const error = new Error(await parseError(res))
    error.status = res.status
    throw error
  }
  return res.status === 204 ? null : res.json()
}

// ── Auth ───────────────────────────────────────────────────────────

export function signup(name, email, password) {
  return request('/api/auth/signup', {
    method: 'POST',
    body: { name, email, password },
    auth: false,
  })
}

export function login(email, password) {
  return request('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
}

export function logout() {
  return request('/api/auth/logout', { method: 'POST' })
}

export function fetchMe() {
  return request('/api/auth/me')
}

// ── App data ───────────────────────────────────────────────────────

export function askQuestion(question) {
  return request('/api/ask', { method: 'POST', body: { question } })
}

export function fetchExamples() {
  return request('/api/examples')
}

export function fetchHealth() {
  return request('/api/health', { auth: false })
}

export function fetchSchema() {
  return request('/api/schema')
}

export function fetchHistory() {
  return request('/api/history')
}

export function clearHistory() {
  return request('/api/history', { method: 'DELETE' })
}
