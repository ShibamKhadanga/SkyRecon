// Simple recordings store using localStorage + custom events for cross-component sync

const KEY = 'skyrecon_recordings'

export function getRecordings() {
  try { return JSON.parse(localStorage.getItem(KEY) || '[]') }
  catch { return [] }
}

export function saveRecording(rec) {
  const list = getRecordings()
  list.unshift(rec) // newest first
  localStorage.setItem(KEY, JSON.stringify(list))
  window.dispatchEvent(new Event('skyrecon-recordings-updated'))
}

export function deleteRecording(id) {
  const list = getRecordings().filter(r => r.id !== id)
  localStorage.setItem(KEY, JSON.stringify(list))
  window.dispatchEvent(new Event('skyrecon-recordings-updated'))
}

export function clearRecordings() {
  localStorage.removeItem(KEY)
  window.dispatchEvent(new Event('skyrecon-recordings-updated'))
}
