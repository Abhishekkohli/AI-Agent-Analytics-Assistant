async function parseError(res) {
  try {
    const data = await res.json()
    return data.detail || data.message || res.statusText
  } catch {
    return res.statusText || 'Request failed'
  }
}

export async function askQuestion(question) {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    throw new Error(await parseError(res))
  }
  return res.json()
}

export async function fetchExamples() {
  const res = await fetch('/api/examples')
  if (!res.ok) {
    throw new Error(await parseError(res))
  }
  return res.json()
}

export async function fetchHealth() {
  const res = await fetch('/api/health')
  if (!res.ok) {
    throw new Error(await parseError(res))
  }
  return res.json()
}

export async function fetchSchema() {
  const res = await fetch('/api/schema')
  if (!res.ok) {
    throw new Error(await parseError(res))
  }
  return res.json()
}
