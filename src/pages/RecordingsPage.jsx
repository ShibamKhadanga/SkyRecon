import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Video, Trash2, Download, Play, Clock, HardDrive, VideoOff, Trash } from 'lucide-react'
import { getRecordings, deleteRecording, clearRecordings } from '../hooks/useRecordingsStore'

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(ms) {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`
}

export default function RecordingsPage() {
  const [recordings, setRecordings] = useState(getRecordings())
  const [playing, setPlaying] = useState(null)

  // Sync when LiveFeedPage saves a new recording
  useEffect(() => {
    const sync = () => setRecordings(getRecordings())
    window.addEventListener('skyrecon-recordings-updated', sync)
    return () => window.removeEventListener('skyrecon-recordings-updated', sync)
  }, [])

  const handleDelete = (id) => {
    deleteRecording(id)
    setRecordings(getRecordings())
    if (playing === id) setPlaying(null)
  }

  const handleDownload = (rec) => {
    const a = document.createElement('a')
    a.href = rec.url
    a.download = rec.name
    a.click()
  }

  const handleClearAll = () => {
    // Revoke all blob URLs to free memory
    getRecordings().forEach(r => { try { URL.revokeObjectURL(r.url) } catch {} })
    clearRecordings()
    setRecordings([])
    setPlaying(null)
  }

  const totalSize = recordings.reduce((sum, r) => sum + (r.size || 0), 0)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1 flex items-center gap-2">
            <Video size={22} className="text-red-400" /> Recordings
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            All recordings captured from the Live Feed page
          </p>
        </div>
        {recordings.length > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-[var(--text-muted)] flex items-center gap-1.5">
              <HardDrive size={12} /> {recordings.length} recording{recordings.length !== 1 ? 's' : ''} · {formatSize(totalSize)}
            </span>
            <button onClick={handleClearAll}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-colors">
              <Trash size={12} /> Clear All
            </button>
          </div>
        )}
      </div>

      {/* Empty state */}
      {recordings.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
            <VideoOff size={28} className="text-[var(--text-muted)]" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-secondary)] mb-1">No recordings yet</p>
            <p className="text-xs text-[var(--text-muted)]">
              Go to Live Feed, connect a stream, then click the Record button
            </p>
          </div>
        </div>
      )}

      {/* Recordings grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <AnimatePresence>
          {recordings.map((rec, i) => (
            <motion.div
              key={rec.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ delay: i * 0.05 }}
              className="flex flex-col rounded-2xl border border-white/5 bg-white/[0.01] overflow-hidden"
            >
              {/* Video player */}
              <div className="relative bg-black" style={{ aspectRatio: '16/9' }}>
                {playing === rec.id ? (
                  <video
                    src={rec.url}
                    className="w-full h-full object-contain"
                    controls
                    autoPlay
                  />
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                    <motion.button
                      whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}
                      onClick={() => setPlaying(rec.id)}
                      className="w-14 h-14 rounded-full bg-white/10 border border-white/20 flex items-center justify-center hover:bg-white/20 transition-colors"
                    >
                      <Play size={22} className="text-white ml-1" />
                    </motion.button>
                    <span className="text-xs font-mono text-[var(--text-muted)]">Click to play</span>
                  </div>
                )}

                {/* Duration badge */}
                {rec.duration && (
                  <div className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-0.5 rounded-lg bg-black/70 border border-white/10">
                    <Clock size={9} className="text-[var(--text-muted)]" />
                    <span className="text-[10px] font-mono text-white">{formatDuration(rec.duration)}</span>
                  </div>
                )}
              </div>

              {/* Info + actions */}
              <div className="flex items-center gap-3 px-4 py-3 border-t border-white/5">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{rec.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">{rec.date}</span>
                    {rec.size > 0 && (
                      <span className="text-[10px] font-mono text-[var(--text-muted)]">· {formatSize(rec.size)}</span>
                    )}
                    {rec.source && (
                      <span className="text-[10px] font-mono text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded-md border border-purple-500/20">
                        {rec.source}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button onClick={() => handleDownload(rec)}
                    className="p-2 rounded-xl bg-white/5 border border-white/10 text-[var(--text-muted)] hover:text-white hover:bg-white/10 transition-colors"
                    title="Download">
                    <Download size={14} />
                  </button>
                  <button onClick={() => handleDelete(rec.id)}
                    className="p-2 rounded-xl bg-red-500/5 border border-red-500/10 text-red-400/60 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Delete">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
