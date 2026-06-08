const API_BASE = import.meta.env.VITE_API_URL || ''

function buildUrl(path) {
  if (typeof path !== 'string') return path
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE}${path}`
}

export async function fetchJson(path, options) {
  const res = await fetch(buildUrl(path), options)
  const text = await res.text()
  const contentType = (res.headers.get('content-type') || '').toLowerCase()

  let parsed = null
  if (contentType.includes('application/json')) {
    try {
      parsed = JSON.parse(text)
    } catch {
      parsed = null
    }
  }

  if (!res.ok) {
    const message = parsed?.detail || parsed?.message || text || res.statusText || `HTTP ${res.status}`
    throw new Error(message)
  }

  if (contentType.includes('application/json')) {
    return parsed
  }

  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export function getApiBase() {
  return API_BASE
}
