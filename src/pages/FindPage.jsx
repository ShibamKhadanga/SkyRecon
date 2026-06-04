import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search, Video, X, Clock, Upload,
  AlertCircle, CheckCircle, Loader2, Image as ImageIcon,
  Target, ZoomIn, Download, ScanLine, Wifi, WifiOff, RefreshCw,
  Usb, ChevronDown, StopCircle
} from 'lucide-react'
import WeatherBar from '../components/ui/WeatherBar'

function formatTime(sec) {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// ── Drop zone for file upload ─────────────────────────────────────────────────
function DropZone({ accept, label, subLabel, icon: Icon, onFile, preview, onClear, disabled }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  const handleDrop = useCallback(e => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }, [onFile])

  return (
    <div
      className={`relative flex flex-col h-full rounded-xl border-2 border-dashed transition-all duration-200 overflow-hidden
        ${dragging ? 'border-green-400/60 bg-green-500/5' : 'border-white/10 bg-white/[0.02] hover:border-white/20'}
        ${disabled ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
      `}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !preview && inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept={accept} className="hidden"
        onChange={e => e.target.files[0] && onFile(e.target.files[0])} />

      {preview ? (
        <>
          {accept.startsWith('image')
            ? <img src={preview} alt="target" className="w-full h-full object-contain p-2" />
            : <video src={preview} className="w-full h-full object-contain" controls />
          }
          <button
            onClick={e => { e.stopPropagation(); onClear() }}
            className="absolute top-2 right-2 w-6 h-6 rounded-full bg-black/60 border border-white/20 flex items-center justify-center text-[var(--text-muted)] hover:text-white transition-colors"
          >
            <X size={11} />
          </button>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 p-4 h-full text-center">
          <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
            <Icon size={22} className="text-[var(--text-muted)]" />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-secondary)]">{label}</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">{subLabel}</p>
          </div>
          <button
            onClick={e => { e.stopPropagation(); inputRef.current?.click() }}
            className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-[var(--text-secondary)] hover:bg-white/10 transition-colors"
          >
            Browse Files
          </button>
        </div>
      )}
    </div>
  )
}

// ── Live / USB panel ──────────────────────────────────────────────────────────
const NET_PROTOCOLS = [
  { label: 'MJPEG',        value: 'mjpeg',  placeholder: 'http://192.168.1.6:8080/video' },
  { label: 'HLS (.m3u8)', value: 'hls',    placeholder: 'http://192.168.1.1/live/stream.m3u8' },
  { label: 'Direct (MP4)', value: 'direct', placeholder: 'http://192.168.1.1/stream.mp4' },
  { label: 'RTSP',         value: 'rtsp',   placeholder: 'rtsp://192.168.1.1:554/live' },
]

function LivePanel({ mode, onStreamReady, videoRef: externalVideoRef }) {
  const imgRef        = useRef()
  const internalVideoRef = useRef()
  const videoRef      = externalVideoRef || internalVideoRef
  const streamRef     = useRef(null)

  const [url, setUrl]               = useState('')
  const [protocol, setProtocol]     = useState('mjpeg')
  const [connected, setConnected]   = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [err, setErr]               = useState('')
  const [videoDevices, setVideoDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState('')

  const selectedProto = NET_PROTOCOLS.find(p => p.value === protocol)

  // Enumerate USB devices when in USB mode
  useEffect(() => {
    if (mode !== 'usb') return
    navigator.mediaDevices?.enumerateDevices()
      .then(devs => {
        const vids = devs.filter(d => d.kind === 'videoinput')
        setVideoDevices(vids)
        const ewrf = vids.find(d =>
          d.label.toLowerCase().includes('ewrf') ||
          d.label.toLowerCase().includes('capture') ||
          d.label.toLowerCase().includes('usb video') ||
          d.label.toLowerCase().includes('fpv')
        )
        setSelectedDevice(ewrf?.deviceId || vids[0]?.deviceId || '')
      })
  }, [mode])

  const refreshDevices = () => {
    navigator.mediaDevices?.getUserMedia({ video: true })
      .then(s => { s.getTracks().forEach(t => t.stop()); return navigator.mediaDevices.enumerateDevices() })
      .then(devs => {
        const vids = devs.filter(d => d.kind === 'videoinput')
        setVideoDevices(vids)
        const ewrf = vids.find(d =>
          d.label.toLowerCase().includes('ewrf') ||
          d.label.toLowerCase().includes('capture') ||
          d.label.toLowerCase().includes('usb video') ||
          d.label.toLowerCase().includes('fpv')
        )
        setSelectedDevice(ewrf?.deviceId || vids[0]?.deviceId || '')
      }).catch(() => {})
  }

  const disconnect = () => {
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null }
    if (videoRef.current)  { videoRef.current.srcObject = null; videoRef.current.src = ''; videoRef.current.load() }
    setConnected(false); onStreamReady(null); setErr('')
  }

  const connectUsb = async () => {
    setErr(''); setConnecting(true)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: selectedDevice ? { deviceId: { exact: selectedDevice } } : true,
        audio: false,
      })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      setConnected(true); setConnecting(false)
      onStreamReady('usb://' + selectedDevice)
    } catch (e) {
      setErr(e.name === 'NotFoundError'
        ? 'No capture device found. Plug in EWRF receiver and click Refresh.'
        : e.name === 'NotAllowedError'
          ? 'Camera permission denied. Allow in browser settings.'
          : `Failed: ${e.message}`)
      setConnecting(false)
    }
  }

  const connectNet = async () => {
    if (!url.trim()) return
    setErr(''); setConnecting(true)
    try {
      if (protocol === 'mjpeg') {
        setConnected(true); setConnecting(false); onStreamReady(url)
      } else if (protocol === 'hls') {
        const video = videoRef.current
        if (window.Hls?.isSupported()) {
          const hls = new window.Hls()
          hls.loadSource(url); hls.attachMedia(video)
          hls.on(window.Hls.Events.MANIFEST_PARSED, () => { video.play(); setConnected(true); setConnecting(false); onStreamReady(url) })
          hls.on(window.Hls.Events.ERROR, () => { setErr('HLS failed.'); setConnecting(false) })
        } else { setErr('HLS not supported.'); setConnecting(false) }
      } else if (protocol === 'direct') {
        videoRef.current.src = url
        videoRef.current.play()
          .then(() => { setConnected(true); setConnecting(false); onStreamReady(url) })
          .catch(() => { setErr('Stream failed. Check URL.'); setConnecting(false) })
      } else if (protocol === 'rtsp') {
        setErr('RTSP cannot play in browsers. Convert to HLS via FFmpeg first.')
        setConnecting(false)
      }
    } catch (e) { setErr(`Failed: ${e.message}`); setConnecting(false) }
  }

  // Reset on mode switch
  useEffect(() => { disconnect(); setErr('') }, [mode])

  const isUsb = mode === 'usb'

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Stream view — video always mounted so srcObject works before connected */}
      <div className={`relative rounded-xl overflow-hidden bg-black border border-white/5 min-h-0 ${connected ? 'flex-1' : 'hidden'}`}>
        {protocol === 'mjpeg' && !isUsb && connected && (
          <img ref={imgRef} src={url} alt="live" className="w-full h-full object-contain" />
        )}
        <video ref={videoRef} autoPlay playsInline muted
          className="w-full h-full object-contain"
          style={{ display: connected && !(protocol === 'mjpeg' && !isUsb) ? 'block' : 'none' }}
        />
        <div className="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/60 border border-green-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
          <span className="text-[10px] font-mono text-red-400">LIVE</span>
          {isUsb && <span className="text-[10px] font-mono text-purple-400 border-l border-white/10 pl-1.5">FPV</span>}
        </div>
        <button onClick={disconnect}
          className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-lg bg-black/60 border border-red-500/20 text-red-400 text-[10px] hover:bg-red-500/10 transition-colors">
          <WifiOff size={10} /> Disconnect
        </button>
      </div>

      {/* Placeholder when not connected */}
      {!connected && (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.02]">
          {isUsb ? <Usb size={24} className="text-[var(--text-muted)]" /> : <Video size={24} className="text-[var(--text-muted)]" />}
          <p className="text-[11px] text-[var(--text-muted)] font-mono text-center px-4">
            {isUsb ? 'Plug in EWRF receiver, select device below' : 'Enter stream URL and connect'}
          </p>
        </div>
      )}

      {/* Controls */}
      {!connected && (
        <div className="flex-shrink-0 space-y-2">
          {isUsb ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-[var(--text-muted)]">CAPTURE DEVICE</span>
                <button onClick={refreshDevices} className="text-[10px] font-mono text-purple-400 hover:text-purple-300 flex items-center gap-1">
                  <RefreshCw size={9} /> Refresh
                </button>
              </div>
              {videoDevices.length === 0 ? (
                <div className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-[10px] text-[var(--text-muted)] font-mono">No devices — click Refresh</div>
              ) : (
                <div className="relative">
                  <select value={selectedDevice} onChange={e => setSelectedDevice(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white focus:outline-none focus:border-purple-500/40 font-mono appearance-none pr-8">
                    {videoDevices.map(d => (
                      <option key={d.deviceId} value={d.deviceId} style={{ background: '#0a0a0a' }}>
                        {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none" />
                </div>
              )}
              <button onClick={connectUsb} disabled={connecting}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-semibold hover:bg-purple-500/20 transition-colors disabled:opacity-50">
                {connecting ? <RefreshCw size={12} className="animate-spin" /> : <Usb size={12} />}
                Connect FPV Receiver
              </button>
            </>
          ) : (
            <>
              <div className="flex gap-1">
                {NET_PROTOCOLS.map(p => (
                  <button key={p.value} onClick={() => { setProtocol(p.value); setErr('') }}
                    className={`flex-1 py-1 rounded-lg text-[10px] font-mono transition-colors border ${
                      protocol === p.value
                        ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400'
                        : 'bg-white/[0.02] border-white/5 text-[var(--text-muted)] hover:bg-white/5'
                    }`}>{p.label}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input type="text" value={url} onChange={e => { setUrl(e.target.value); setErr('') }}
                  onKeyDown={e => e.key === 'Enter' && connectNet()}
                  placeholder={selectedProto?.placeholder}
                  className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-cyan-500/40 font-mono" />
                <button onClick={connectNet} disabled={connecting || !url.trim()}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold hover:bg-cyan-500/20 transition-colors disabled:opacity-50">
                  {connecting ? <RefreshCw size={12} className="animate-spin" /> : <Wifi size={12} />}
                  Connect
                </button>
              </div>
            </>
          )}
          {err && <p className="text-[10px] text-orange-400 font-mono leading-relaxed">{err}</p>}
        </div>
      )}
    </div>
  )
}

// ── Capture a frame from a video element or file at a given time ─────────────
function captureFrame(videoEl) {
  try {
    const canvas = document.createElement('canvas')
    canvas.width  = videoEl.videoWidth  || 640
    canvas.height = videoEl.videoHeight || 360
    canvas.getContext('2d').drawImage(videoEl, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.8)
  } catch { return null }
}

async function captureFrameFromFile(file, timeSec) {
  return new Promise(resolve => {
    const video = document.createElement('video')
    video.src = URL.createObjectURL(file)
    video.muted = true
    video.currentTime = timeSec
    video.addEventListener('seeked', () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width  = video.videoWidth  || 640
        canvas.height = video.videoHeight || 360
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/jpeg', 0.8))
      } catch { resolve(null) }
    }, { once: true })
    video.addEventListener('error', () => resolve(null), { once: true })
  })
}
// ── Match card ────────────────────────────────────────────────────────────────
function MatchCard({ match, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-green-500/20 hover:bg-green-500/[0.02] transition-all group"
    >
      <div className="relative flex-shrink-0">
        <img src={match.thumbnail} alt={`Match at ${formatTime(match.timestamp)}`}
          className="w-20 h-14 object-cover rounded-lg border border-white/10" />
        <div className="absolute inset-0 rounded-lg border border-green-500/30" />
        <div className="absolute -top-1 -right-1 px-1.5 py-0.5 rounded-md bg-green-500 text-[9px] font-bold text-black">
          {Math.round(match.confidence * 100)}%
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-1">
          <Clock size={10} className="text-green-400 flex-shrink-0" />
          <span className="text-xs font-mono font-semibold text-green-400">{formatTime(match.timestamp)}</span>
        </div>
        <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed line-clamp-2">{match.description}</p>
        <div className="flex items-center gap-2 mt-1.5">
          <div className="h-1 flex-1 rounded-full bg-white/5 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${match.confidence * 100}%` }}
              transition={{ delay: index * 0.08 + 0.2, duration: 0.5 }}
              className="h-full rounded-full bg-green-400"
            />
          </div>
          <span className="text-[9px] font-mono text-[var(--text-muted)]">CONF</span>
        </div>
      </div>
      <button className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-[var(--text-muted)] hover:text-white opacity-0 group-hover:opacity-100 transition-all flex-shrink-0">
        <ZoomIn size={11} />
      </button>
    </motion.div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function FindPage() {
  const [targetFile, setTargetFile]   = useState(null)
  const [targetPreview, setTargetPreview] = useState(null)
  const [videoFile, setVideoFile]     = useState(null)
  const [videoPreview, setVideoPreview] = useState(null)
  const [videoMode, setVideoMode]     = useState('upload') // 'upload' | 'live' | 'usb'
  const [liveUrl, setLiveUrl]         = useState(null)
  const [searching, setSearching]     = useState(false)
  const [progress, setProgress]       = useState(0)
  const [progressMsg, setProgressMsg] = useState('')
  const [matches, setMatches]         = useState([])
  const [searchDone, setSearchDone]   = useState(false)
  const [error, setError]             = useState('')
  const [processingLog, setProcessingLog] = useState([])
  const abortRef = useRef(null)
  const liveVideoRef = useRef(null) // ref passed to LivePanel to capture frames

  const handleTargetFile = file => {
    setTargetFile(file)
    setTargetPreview(URL.createObjectURL(file))
    setMatches([]); setSearchDone(false); setError('')
  }
  const handleVideoFile = file => {
    setVideoFile(file)
    setVideoPreview(URL.createObjectURL(file))
    setMatches([]); setSearchDone(false); setError('')
  }
  const clearTarget = () => { setTargetFile(null); setTargetPreview(null) }
  const clearVideo  = () => { setVideoFile(null);  setVideoPreview(null)  }
  const addLog = msg => setProcessingLog(prev => [...prev, { time: new Date().toLocaleTimeString(), msg }])

  const canSearch = (videoMode === 'upload' ? (targetFile && videoFile) : (targetFile && liveUrl)) && !searching

  const startSearch = async () => {
    if (!targetFile) { setError('Upload a target image first.'); return }
    if (videoMode === 'upload' && !videoFile) { setError('Upload a drone video or switch to Live mode.'); return }
    if ((videoMode === 'live' || videoMode === 'usb') && !liveUrl) { setError('Connect to a live stream first.'); return }

    setError(''); setSearching(true); setSearchDone(false)
    setMatches([]); setProcessingLog([]); setProgress(0)

    abortRef.current = new AbortController()

    // Animate progress while backend processes
    let fakeP = 0
    const timer = setInterval(() => {
      fakeP = Math.min(fakeP + 1, 88)
      setProgress(fakeP)
      if (fakeP < 15) setProgressMsg('Loading models...')
      else if (fakeP < 30) setProgressMsg('Encoding target object...')
      else if (fakeP < 60) setProgressMsg('Scanning video frames...')
      else setProgressMsg('Comparing features...')
    }, 600)

    try {
      addLog('Initializing AI search engine...')
      addLog('Extracting target features with CLIP...')
      addLog(videoMode === 'upload' ? 'Scanning video frames...' : 'Scanning live frames...')
      addLog('Sending to backend AI pipeline...')

      const formData = new FormData()
      formData.append('target_image', targetFile)
      if (videoMode === 'upload') formData.append('video', videoFile)
      else formData.append('live_url', liveUrl)

      let backendOk = false
      try {
        const res = await fetch('/api/v1/analysis/find-object', { method: 'POST', body: formData, signal: abortRef.current?.signal })
        clearInterval(timer)
        if (res.ok) {
          const data = await res.json()
          setProgress(95); setProgressMsg('Finalizing results...')
          const count = data.matches?.length || 0
          addLog(`Scanned ${data.total_scanned || 0} frames — found ${count} match${count !== 1 ? 'es' : ''}`)
          if (count === 0) addLog('Object not detected in this footage.')
          await new Promise(r => setTimeout(r, 300))
          setProgress(100); setProgressMsg(count > 0 ? 'Search complete' : 'No matches found')
          setMatches(data.matches || [])
          setSearchDone(true)
          backendOk = true
        }
      } catch (_) { clearInterval(timer) }

      if (!backendOk) {
        clearInterval(timer)
        if (abortRef.current?.signal.aborted) {
          addLog('Search cancelled by user.')
          setProgress(0); setProgressMsg('')
        } else {
          addLog('Backend not available — start with: uvicorn app.main:app --reload')
          setProgress(100); setProgressMsg('Backend not available')
          setSearchDone(true)
        }
      }

    } catch (e) {
      clearInterval(timer)
      if (e.name !== 'AbortError') {
        setError(`Search failed: ${e.message}`)
        addLog(`Error: ${e.message}`)
      }
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="space-y-3 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1 flex items-center gap-2">
            <Target size={22} className="text-green-400" /> Object Finder
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            Upload a target image — AI finds every appearance in uploaded or live drone footage
          </p>
        </div>
        {canSearch && (
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={startSearch}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm font-semibold hover:bg-green-500/20 transition-colors">
            <Search size={15} /> Start Search
          </motion.button>
        )}
        {searching && (
          <button
            onClick={() => abortRef.current?.abort()}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-semibold hover:bg-red-500/20 transition-colors">
            <StopCircle size={15} /> Cancel
          </button>
        )}
      </div>

      {/* Weather Bar */}
      <WeatherBar />

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-3 p-3 rounded-xl bg-red-500/5 border border-red-500/20">
            <AlertCircle size={14} className="text-red-400 flex-shrink-0" />
            <p className="text-xs text-red-300">{error}</p>
            <button onClick={() => setError('')} className="ml-auto text-red-400/60 hover:text-red-400"><X size={12} /></button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 4-Quadrant Grid */}
      <div className="grid grid-cols-2 grid-rows-2 gap-3" style={{ height: 'calc(100vh - 240px)', minHeight: 480 }}>

        {/* TOP LEFT — Target Image */}
        <div className="flex flex-col rounded-2xl border border-white/5 bg-white/[0.01] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 flex-shrink-0">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span className="text-xs font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Target Object</span>
            {targetFile && (
              <span className="ml-auto text-[10px] font-mono text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                {targetFile.name.slice(0, 20)}
              </span>
            )}
          </div>
          <div className="flex-1 p-3 min-h-0">
            <DropZone accept="image/*" label="Upload Target Photo"
              subLabel="Person, vehicle, or any object to find"
              icon={ImageIcon} onFile={handleTargetFile}
              preview={targetPreview} onClear={clearTarget} disabled={searching} />
          </div>
        </div>

        {/* TOP RIGHT — Drone Video (Upload or Live toggle) */}
        <div className="flex flex-col rounded-2xl border border-white/5 bg-white/[0.01] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 flex-shrink-0">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            <span className="text-xs font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Drone Video</span>
            {/* Toggle: Upload / Live / USB */}
            <div className="ml-auto flex items-center gap-1 p-0.5 rounded-lg bg-white/5 border border-white/10">
              {[
                { mode: 'upload', icon: Upload, label: 'Upload' },
                { mode: 'live',   icon: Wifi,   label: 'Live'   },
                { mode: 'usb',    icon: Usb,    label: 'FPV'    },
              ].map(({ mode, icon: Icon, label }) => (
                <button key={mode}
                  onClick={() => { setVideoMode(mode); setMatches([]); setSearchDone(false) }}
                  className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-semibold transition-colors ${
                    videoMode === mode
                      ? mode === 'usb'
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/20'
                        : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/20'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                  }`}>
                  <Icon size={10} /> {label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 p-3 min-h-0">
            {videoMode === 'upload' ? (
              <DropZone accept="video/*" label="Upload Drone Video"
                subLabel="MP4, MOV, AVI"
                icon={Video} onFile={handleVideoFile}
                preview={videoPreview} onClear={clearVideo} disabled={searching} />
            ) : (
              <LivePanel mode={videoMode} onStreamReady={setLiveUrl} videoRef={liveVideoRef} />
            )}
          </div>
        </div>

        {/* BOTTOM LEFT — Processing */}
        <div className="flex flex-col rounded-2xl border border-white/5 bg-white/[0.01] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 flex-shrink-0">
            <div className={`w-1.5 h-1.5 rounded-full ${searching ? 'bg-yellow-400 animate-pulse' : searchDone ? 'bg-green-400' : 'bg-white/20'}`} />
            <span className="text-xs font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Processing</span>
            {searching && <span className="ml-auto text-[10px] font-mono text-yellow-400">{progress}%</span>}
            {searchDone && (
              <span className="ml-auto flex items-center gap-1 text-[10px] font-mono text-green-400">
                <CheckCircle size={10} /> Done
              </span>
            )}
          </div>
          <div className="flex-1 p-4 flex flex-col min-h-0 overflow-hidden">
            {!searching && !searchDone && !processingLog.length ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
                <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                  <ScanLine size={22} className="text-[var(--text-muted)]" />
                </div>
                <p className="text-xs text-[var(--text-muted)] font-mono">
                  Upload target + video<br />then click Start Search
                </p>
              </div>
            ) : (
              <div className="flex-1 flex flex-col gap-3 min-h-0">
                {(searching || searchDone) && (
                  <div className="space-y-1.5 flex-shrink-0">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-mono text-[var(--text-muted)]">{progressMsg}</span>
                      <span className="text-[10px] font-mono text-green-400">{progress}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <motion.div animate={{ width: `${progress}%` }} transition={{ duration: 0.4 }}
                        className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400" />
                    </div>
                  </div>
                )}
                {searching && (
                  <div className="flex items-center justify-center gap-3 py-2 flex-shrink-0">
                    <Loader2 size={16} className="text-green-400 animate-spin" />
                    <span className="text-xs text-green-400 font-mono animate-pulse">AI SCANNING FRAMES...</span>
                  </div>
                )}
                <div className="flex-1 overflow-y-auto space-y-1.5 min-h-0">
                  {processingLog.map((log, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="flex items-start gap-2">
                      <span className="text-[9px] font-mono text-[var(--text-muted)] flex-shrink-0 mt-0.5">{log.time}</span>
                      <span className="text-[11px] text-[var(--text-secondary)]">{log.msg}</span>
                    </motion.div>
                  ))}
                </div>
                {searchDone && (
                  <div className="grid grid-cols-2 gap-2 flex-shrink-0 pt-2 border-t border-white/5">
                    {[
                      { label: 'Matches',    value: matches.length, color: 'text-green-400' },
                      { label: 'Confidence', value: matches.length > 0 ? `${Math.round(matches[0].confidence * 100)}%` : '—', color: 'text-cyan-400' },
                    ].map(s => (
                      <div key={s.label} className="p-2 rounded-xl bg-white/[0.02] border border-white/5 text-center">
                        <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
                        <p className="text-[9px] font-mono text-[var(--text-muted)]">{s.label}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* BOTTOM RIGHT — Results */}
        <div className="flex flex-col rounded-2xl border border-white/5 bg-white/[0.01] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 flex-shrink-0">
            <div className={`w-1.5 h-1.5 rounded-full ${matches.length > 0 ? 'bg-green-400' : 'bg-white/20'}`} />
            <span className="text-xs font-mono font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Match Results</span>
            {matches.length > 0 && (
              <span className="ml-auto text-[10px] font-mono text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                {matches.length} found
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3 min-h-0">
            {matches.length === 0 && !searchDone ? (
              <div className="h-full flex flex-col items-center justify-center gap-3 text-center">
                <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                  <Target size={22} className="text-[var(--text-muted)]" />
                </div>
                <p className="text-xs text-[var(--text-muted)] font-mono">Timestamps and screenshots<br />will appear here after search</p>
              </div>
            ) : matches.length === 0 && searchDone ? (
              <div className="h-full flex flex-col items-center justify-center gap-3 text-center px-4">
                <AlertCircle size={28} className={progressMsg === 'No matches found' ? 'text-yellow-400' : 'text-[var(--text-muted)]'} />
                <p className="text-xs font-semibold text-[var(--text-secondary)]">
                  {progressMsg === 'No matches found' ? 'Object not found in footage' : 'Backend not available'}
                </p>
                <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                  {progressMsg === 'No matches found'
                    ? 'The target object was not detected in any frame. Try a clearer target photo or different footage.'
                    : 'Start the FastAPI backend to enable real AI object detection.'}
                </p>
                {progressMsg !== 'No matches found' && (
                  <div className="px-3 py-2 rounded-xl bg-orange-500/5 border border-orange-500/20">
                    <p className="text-[10px] font-mono text-orange-300">uvicorn app.main:app --reload</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {matches.map((match, i) => <MatchCard key={i} match={match} index={i} />)}
              </div>
            )}
          </div>
          {matches.length > 0 && (
            <div className="px-3 pb-3 flex-shrink-0">
              <button className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-[var(--text-secondary)] hover:bg-white/10 transition-colors">
                <Download size={12} /> Export Results ({matches.length} matches)
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
