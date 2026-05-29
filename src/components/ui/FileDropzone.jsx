import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Film, Image, X, CheckCircle } from 'lucide-react'

export default function FileDropzone({ 
  onFileSelect, 
  accept = '.mp4,.mov,.avi,.mkv,.webm,.jpg,.jpeg,.png,.webp',
  maxSizeMB = 500,
  className = '' 
}) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')

  const handleDrag = useCallback((e) => { e.preventDefault(); e.stopPropagation() }, [])
  const handleDragIn = useCallback((e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true) }, [])
  const handleDragOut = useCallback((e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false) }, [])

  const VALID_TYPES = [
    'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/avi',
    'video/x-matroska', 'video/webm',
    'image/jpeg', 'image/png', 'image/webp', 'image/bmp',
  ]

  const validateFile = (file) => {
    const extOk = accept.split(',').some(ext => file.name.toLowerCase().endsWith(ext.trim()))
    if (!VALID_TYPES.includes(file.type) && !extOk) {
      setError('Invalid format. Supported: MP4, MOV, AVI, MKV, WebM, JPG, PNG, WebP')
      return false
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File too large. Maximum: ${maxSizeMB}MB`)
      return false
    }
    setError('')
    return true
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false)
    const file = e.dataTransfer?.files?.[0]
    if (file && validateFile(file)) { setSelectedFile(file); onFileSelect?.(file) }
  }, [onFileSelect, maxSizeMB])

  const handleFileInput = (e) => {
    const file = e.target.files?.[0]
    if (file && validateFile(file)) { setSelectedFile(file); onFileSelect?.(file) }
  }

  const removeFile = () => { setSelectedFile(null); setError(''); onFileSelect?.(null) }

  const formatSize = (bytes) => {
    if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB'
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB'
    return (bytes / 1024).toFixed(1) + ' KB'
  }

  const isImage = selectedFile?.type?.startsWith('image/')

  return (
    <div className={className}>
      <AnimatePresence mode="wait">
        {!selectedFile ? (
          <motion.label
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onDragEnter={handleDragIn}
            onDragLeave={handleDragOut}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
              relative flex flex-col items-center justify-center 
              min-h-[220px] rounded-2xl border-2 border-dashed cursor-pointer
              transition-all duration-300
              ${isDragging 
                ? 'border-green-400 bg-green-500/5 shadow-[0_0_40px_rgba(57,255,20,0.1)]' 
                : 'border-white/10 bg-white/[0.02] hover:border-green-500/30 hover:bg-white/[0.03]'
              }
            `}
          >
            <input type="file" accept={accept} onChange={handleFileInput} className="hidden" />

            <motion.div
              animate={isDragging ? { y: [-5, 5, -5] } : { y: [0, -8, 0] }}
              transition={{ duration: isDragging ? 0.5 : 2, repeat: Infinity }}
              className="mb-4"
            >
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500/20 to-green-600/10 flex items-center justify-center">
                  <Upload size={28} className="text-green-400" />
                </div>
                {isDragging && (
                  <motion.div
                    className="absolute -inset-2 rounded-2xl border border-green-400/40"
                    animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}
              </div>
            </motion.div>

            <p className="text-base font-semibold text-[var(--text-primary)] mb-1">
              {isDragging ? 'Drop your file here' : 'Upload Drone Footage or Image'}
            </p>
            <p className="text-sm text-[var(--text-muted)] mb-3">Drag & drop or click to browse</p>
            <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-[var(--text-muted)]">
              {['MP4','MOV','AVI','MKV'].map(f => (
                <span key={f} className="px-2 py-1 rounded-md bg-white/5">{f}</span>
              ))}
              <span className="text-[var(--text-muted)]">|</span>
              {['JPG','PNG','WebP'].map(f => (
                <span key={f} className="px-2 py-1 rounded-md bg-cyan-500/10 text-cyan-400/70">{f}</span>
              ))}
              <span>Max {maxSizeMB}MB</span>
            </div>
          </motion.label>
        ) : (
          <motion.div
            key="file-preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="glass-card p-5"
          >
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 ${
                isImage ? 'bg-cyan-500/10' : 'bg-green-500/10'
              }`}>
                {isImage
                  ? <Image size={24} className="text-cyan-400" />
                  : <Film size={24} className="text-green-400" />
                }
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle size={14} className="text-green-400 flex-shrink-0" />
                  <p className="text-sm font-semibold truncate">{selectedFile.name}</p>
                </div>
                <p className="text-xs text-[var(--text-muted)]">
                  {formatSize(selectedFile.size)} • {isImage ? 'Image' : 'Video'} • {selectedFile.type}
                </p>
              </div>
              <button
                onClick={removeFile}
                className="p-2 rounded-lg hover:bg-red-500/10 text-[var(--text-muted)] hover:text-red-400 transition-colors"
              >
                <X size={18} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-sm text-red-400 mt-2 pl-1"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  )
}
