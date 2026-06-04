import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Video, Wifi, WifiOff, Maximize2,
  Circle, Square, RefreshCw, AlertTriangle, Camera,
  Signal, Battery, Thermometer, Wind, RotateCw, RotateCcw,
  Usb, ChevronDown
} from 'lucide-react'
import GlassCard from '../components/ui/GlassCard'
import WeatherBar from '../components/ui/WeatherBar'
import { saveRecording } from '../hooks/useRecordingsStore'

const STREAM_PROTOCOLS = [
  { label: 'FPV Receiver (USB)', value: 'fpv',    placeholder: null },
  { label: 'MJPEG',              value: 'mjpeg',  placeholder: 'http://192.168.1.1:8080/video' },
  { label: 'HLS (.m3u8)',        value: 'hls',    placeholder: 'http://192.168.1.1/live/stream.m3u8' },
  { label: 'Direct URL (MP4)',   value: 'direct', placeholder: 'http://192.168.1.1/stream.mp4' },
  { label: 'RTSP (via proxy)',   value: 'rtsp',   placeholder: 'rtsp://192.168.1.1:554/live' },
]

function useTelemetry(connected) {
  const [tele, setTele] = useState({ altitude: 0, speed: 0, battery: 0, signal: 0, temp: 0 })
  useEffect(() => {
    if (!connected) return
    const iv = setInterval(() => {
      setTele({
        altitude: (85 + Math.random() * 10).toFixed(1),
        speed:    (12 + Math.random() * 5).toFixed(1),
        battery:  (78 - Math.random()).toFixed(0),
        signal:   (92 + Math.random() * 6).toFixed(0),
        temp:     (32 + Math.random() * 3).toFixed(1),
      })
    }, 1500)
    return () => clearInterval(iv)
  }, [connected])
  return tele
}

export default function LiveFeedPage() {
  const videoRef  = useRef(null)
  const imgRef    = useRef(null)
  const streamRef = useRef(null) // holds MediaStream for FPV
  const mediaRecorderRef = useRef(null)
  const recordedChunksRef = useRef([])
  const recordStartRef = useRef(null)

  const [protocol, setProtocol]       = useState('fpv')
  const [streamUrl, setStreamUrl]     = useState('')
  const [connected, setConnected]     = useState(false)
  const [connecting, setConnecting]   = useState(false)
  const [error, setError]             = useState('')
  const [fullscreen, setFullscreen]   = useState(false)
  const [recording, setRecording]     = useState(false)
  const [isMjpeg, setIsMjpeg]         = useState(false)
  const [mjpegSrc, setMjpegSrc]       = useState('')
  const [rotation, setRotation]       = useState(0)

  // FPV device list
  const [videoDevices, setVideoDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState('')

  const tele = useTelemetry(connected)

  const rotateLeft  = () => setRotation(r => (r - 90 + 360) % 360)
  const rotateRight = () => setRotation(r => (r + 90) % 360)

  const toggleRecording = () => {
    if (!recording) {
      // Start recording
      try {
        // Get the stream to record — FPV has MediaStream, others use captureStream()
        const stream = streamRef.current || videoRef.current?.captureStream?.()
        if (!stream) { setError('Cannot record: no active stream.'); return }

        const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
          ? 'video/webm;codecs=vp9'
          : MediaRecorder.isTypeSupported('video/webm') ? 'video/webm' : 'video/mp4'

        const mr = new MediaRecorder(stream, { mimeType })
        recordedChunksRef.current = []
        recordStartRef.current = Date.now()

        mr.ondataavailable = e => { if (e.data.size > 0) recordedChunksRef.current.push(e.data) }
        mr.onstop = () => {
          const blob = new Blob(recordedChunksRef.current, { type: mimeType })
          const url  = URL.createObjectURL(blob)
          const duration = Date.now() - recordStartRef.current
          const ext  = mimeType.includes('mp4') ? 'mp4' : 'webm'
          const name = `SkyRecon_${new Date().toISOString().slice(0,19).replace(/[:T]/g, '-')}.${ext}`

          // Auto-download to disk so the file is not lost when browser closes
          const a = document.createElement('a')
          a.href = url
          a.download = name
          a.click()

          saveRecording({
            id:       Date.now().toString(),
            name,
            url,
            size:     blob.size,
            duration,
            date:     new Date().toLocaleString(),
            source:   protocol === 'fpv' ? 'FPV' : protocol.toUpperCase(),
          })
        }

        mr.start(1000) // collect chunks every 1s
        mediaRecorderRef.current = mr
        setRecording(true)
      } catch (e) {
        setError(`Recording failed: ${e.message}`)
      }
    } else {
      // Stop recording
      mediaRecorderRef.current?.stop()
      mediaRecorderRef.current = null
      setRecording(false)
    }
  }

  // Enumerate video input devices when FPV protocol selected
  useEffect(() => {
    if (protocol !== 'fpv') return
    navigator.mediaDevices?.enumerateDevices()
      .then(devices => {
        const vids = devices.filter(d => d.kind === 'videoinput')
        setVideoDevices(vids)
        // auto-select EWRF / capture card if found, else first device
        const ewrf = vids.find(d =>
          d.label.toLowerCase().includes('ewrf') ||
          d.label.toLowerCase().includes('capture') ||
          d.label.toLowerCase().includes('usb video') ||
          d.label.toLowerCase().includes('fpv')
        )
        setSelectedDevice(ewrf?.deviceId || vids[0]?.deviceId || '')
      })
      .catch(() => setVideoDevices([]))
  }, [protocol])

  // Re-enumerate after permission granted (labels appear only after permission)
  const refreshDevices = () => {
    navigator.mediaDevices?.getUserMedia({ video: true })
      .then(s => {
        s.getTracks().forEach(t => t.stop())
        return navigator.mediaDevices.enumerateDevices()
      })
      .then(devices => {
        const vids = devices.filter(d => d.kind === 'videoinput')
        setVideoDevices(vids)
        const ewrf = vids.find(d =>
          d.label.toLowerCase().includes('ewrf') ||
          d.label.toLowerCase().includes('capture') ||
          d.label.toLowerCase().includes('usb video') ||
          d.label.toLowerCase().includes('fpv')
        )
        setSelectedDevice(ewrf?.deviceId || vids[0]?.deviceId || '')
      })
      .catch(() => {})
  }

  const connectFpv = async () => {
    setError('')
    setConnecting(true)
    setIsMjpeg(false)
    try {
      const constraints = {
        video: selectedDevice
          ? { deviceId: { exact: selectedDevice }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      // videoRef.current is always mounted, safe to assign
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setConnected(true)
      setConnecting(false)
    } catch (e) {
      if (e.name === 'NotFoundError')
        setError('No video capture device found. Plug in the EWRF receiver and click Refresh Devices.')
      else if (e.name === 'NotAllowedError')
        setError('Camera permission denied. Allow camera access in browser settings.')
      else
        setError(`FPV connection failed: ${e.message}`)
      setConnecting(false)
    }
  }

  const connect = async () => {
    setError('')
    setConnecting(true)

    try {
      if (protocol === 'fpv') {
        await connectFpv()
        return
      }

      if (!streamUrl.trim()) { setError('Enter a stream URL first.'); setConnecting(false); return }

      if (protocol === 'mjpeg') {
        setMjpegSrc(streamUrl)
        setIsMjpeg(true)
        setConnected(true)
        setConnecting(false)
      } else if (protocol === 'hls') {
        setIsMjpeg(false)
        const video = videoRef.current
        if (window.Hls && window.Hls.isSupported()) {
          const hls = new window.Hls()
          hls.loadSource(streamUrl)
          hls.attachMedia(video)
          hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
            video.play(); setConnected(true); setConnecting(false)
          })
          hls.on(window.Hls.Events.ERROR, () => {
            setError('HLS stream failed.'); setConnecting(false)
          })
        } else {
          setError('HLS not supported in this browser. Try Chrome.')
          setConnecting(false)
        }
      } else if (protocol === 'direct') {
        setIsMjpeg(false)
        const video = videoRef.current
        video.src = streamUrl
        video.play()
          .then(() => { setConnected(true); setConnecting(false) })
          .catch(() => { setError('Stream failed. Check the URL.'); setConnecting(false) })
      } else if (protocol === 'rtsp') {
        setError('RTSP cannot play in browsers. Convert to HLS via FFmpeg first.')
        setConnecting(false)
      }
    } catch (e) {
      setError(`Connection failed: ${e.message}`)
      setConnecting(false)
    }
  }

  const disconnect = () => {
    // Stop recording if active
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
    }
    // Stop FPV MediaStream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
      videoRef.current.src = ''
      videoRef.current.load()
    }
    setMjpegSrc('')
    setConnected(false)
    setIsMjpeg(false)
    setRecording(false)
    setRotation(0)
    setError('')
  }

  const toggleFullscreen = () => {
    const el = isMjpeg ? imgRef.current : videoRef.current
    if (!fullscreen) el?.requestFullscreen?.()
    else document.exitFullscreen?.()
    setFullscreen(!fullscreen)
  }

  const selectedProto = STREAM_PROTOCOLS.find(p => p.value === protocol)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1">Live Drone Feed</h1>
          <p className="text-sm text-[var(--text-muted)]">Real-time drone camera stream with telemetry overlay</p>
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-full border ${
          connected
            ? 'text-green-400 border-green-500/20 bg-green-500/5'
            : 'text-[var(--text-muted)] border-white/10 bg-white/5'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          {connected ? 'STREAMING' : 'DISCONNECTED'}
        </span>
      </div>

      {/* Weather Bar */}
      <WeatherBar />

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">

        {/* Video Feed */}
        <div className="xl:col-span-3 space-y-4">
          <div className="relative rounded-2xl overflow-hidden bg-black border border-white/5"
               style={{ aspectRatio: '16/9' }}>

            {/* MJPEG */}
            {isMjpeg && mjpegSrc && (
              <img ref={imgRef} src={mjpegSrc} alt="live"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ transform: `rotate(${rotation}deg)`, transition: 'transform 0.3s' }}
              />
            )}

            {/* HLS / Direct / FPV USB — all use <video> */}
            <video ref={videoRef}
              className="absolute inset-0 w-full h-full object-contain"
              autoPlay playsInline muted
              style={{
                display: connected && !isMjpeg ? 'block' : 'none',
                transform: `rotate(${rotation}deg)`,
                transition: 'transform 0.3s',
              }}
            />

            {/* Placeholder */}
            {!connected && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                <motion.div
                  animate={{ opacity: [0.3, 0.7, 0.3] }}
                  transition={{ duration: 3, repeat: Infinity }}
                  className="w-20 h-20 rounded-full border-2 border-green-500/20 flex items-center justify-center"
                >
                  {protocol === 'fpv'
                    ? <Usb size={36} className="text-green-500/40" />
                    : <Camera size={36} className="text-green-500/40" />
                  }
                </motion.div>
                <p className="text-sm text-[var(--text-muted)] font-mono">
                  {connecting ? 'Connecting to stream...' : 'No stream connected'}
                </p>
                {connecting && (
                  <motion.div className="w-32 h-0.5 bg-white/5 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-green-400 rounded-full"
                      animate={{ x: ['-100%', '200%'] }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                    />
                  </motion.div>
                )}
              </div>
            )}

            {/* Scan line */}
            {connected && (
              <motion.div
                className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-green-400/20 to-transparent pointer-events-none"
                animate={{ top: ['0%', '100%'] }}
                transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
              />
            )}

            {/* Corner brackets */}
            {['top-2 left-2', 'top-2 right-2', 'bottom-2 left-2', 'bottom-2 right-2'].map((pos, i) => (
              <div key={i} className={`absolute ${pos} w-4 h-4 border-green-500/30 pointer-events-none`}
                style={{
                  borderTopWidth: i < 2 ? 1 : 0, borderBottomWidth: i >= 2 ? 1 : 0,
                  borderLeftWidth: i % 2 === 0 ? 1 : 0, borderRightWidth: i % 2 === 1 ? 1 : 0,
                }}
              />
            ))}

            {/* HUD */}
            {connected && (
              <>
                <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/60 border border-green-500/20">
                  <Circle size={6} className="text-red-400 fill-red-400 animate-pulse" />
                  <span className="text-[10px] font-mono text-red-400">{recording ? 'REC' : 'LIVE'}</span>
                  {protocol === 'fpv' && (
                    <span className="ml-1 text-[10px] font-mono text-purple-400 border-l border-white/10 pl-1.5">FPV</span>
                  )}
                </div>
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                  <button onClick={rotateLeft} title="Rotate Left"
                    className="p-1.5 rounded-lg bg-black/60 border border-white/10 text-[var(--text-muted)] hover:text-white transition-colors">
                    <RotateCcw size={12} />
                  </button>
                  <button onClick={rotateRight} title="Rotate Right"
                    className="p-1.5 rounded-lg bg-black/60 border border-white/10 text-[var(--text-muted)] hover:text-white transition-colors">
                    <RotateCw size={12} />
                  </button>
                  {rotation !== 0 && (
                    <button onClick={() => setRotation(0)}
                      className="px-2 py-1 rounded-lg bg-black/60 border border-green-500/20 text-green-400 text-[10px] font-mono hover:bg-green-500/10 transition-colors">
                      {rotation}°
                    </button>
                  )}
                  <button onClick={toggleFullscreen}
                    className="p-1.5 rounded-lg bg-black/60 border border-white/10 text-[var(--text-muted)] hover:text-white transition-colors">
                    <Maximize2 size={12} />
                  </button>
                </div>
                <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {[
                      { icon: Wind,   label: `${tele.altitude}m`, title: 'Altitude' },
                      { icon: Signal, label: `${tele.speed}m/s`,  title: 'Speed' },
                    ].map(({ icon: Icon, label, title }) => (
                      <div key={title} title={title}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg bg-black/60 border border-white/10">
                        <Icon size={10} className="text-green-400" />
                        <span className="text-[10px] font-mono text-white">{label}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    {[
                      { icon: Battery,     label: `${tele.battery}%`, title: 'Battery' },
                      { icon: Wifi,        label: `${tele.signal}%`,  title: 'Signal' },
                    ].map(({ icon: Icon, label, title }) => (
                      <div key={title} title={title}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg bg-black/60 border border-white/10">
                        <Icon size={10} className="text-cyan-400" />
                        <span className="text-[10px] font-mono text-white">{label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Controls Bar */}
          <div className="flex items-center gap-3 flex-wrap">
            {!connected ? (
              <button onClick={connect} disabled={connecting}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm font-semibold hover:bg-green-500/20 transition-colors disabled:opacity-50">
                {connecting
                  ? <><RefreshCw size={14} className="animate-spin" /> Connecting...</>
                  : protocol === 'fpv'
                    ? <><Usb size={14} /> Connect FPV Receiver</>
                    : <><Wifi size={14} /> Connect Stream</>
                }
              </button>
            ) : (
              <>
                <button onClick={disconnect}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-semibold hover:bg-red-500/20 transition-colors">
                  <WifiOff size={14} /> Disconnect
                </button>
                <button onClick={toggleRecording}
                  className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors border ${
                    recording
                      ? 'bg-red-500/10 border-red-500/20 text-red-400 hover:bg-red-500/20'
                      : 'bg-white/5 border-white/10 text-[var(--text-secondary)] hover:bg-white/10'
                  }`}>
                  {recording ? <><Square size={14} /> Stop Recording</> : <><Circle size={14} /> Record</>}
                </button>
              </>
            )}
          </div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className="flex items-start gap-3 p-3 rounded-xl bg-orange-500/5 border border-orange-500/20">
                <AlertTriangle size={15} className="text-orange-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-orange-300 leading-relaxed">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right Panel */}
        <div className="space-y-4">
          <GlassCard hover={false}>
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Video size={14} className="text-green-400" /> Stream Setup
            </h3>

            {/* Protocol selector */}
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[var(--text-muted)] font-mono mb-1.5 block">SOURCE</label>
                <div className="grid grid-cols-1 gap-1">
                  {STREAM_PROTOCOLS.map(p => (
                    <button key={p.value}
                      onClick={() => { setProtocol(p.value); setStreamUrl(''); setError('') }}
                      className={`px-3 py-2 rounded-lg text-xs font-mono text-left transition-colors border flex items-center gap-2 ${
                        protocol === p.value
                          ? 'bg-green-500/10 border-green-500/20 text-green-400'
                          : 'bg-white/[0.02] border-white/5 text-[var(--text-muted)] hover:bg-white/5'
                      }`}>
                      {p.value === 'fpv' && <Usb size={11} />}
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* FPV device picker */}
              {protocol === 'fpv' && (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs text-[var(--text-muted)] font-mono">CAPTURE DEVICE</label>
                    <button onClick={refreshDevices}
                      className="text-[10px] font-mono text-green-400 hover:text-green-300 flex items-center gap-1">
                      <RefreshCw size={9} /> Refresh
                    </button>
                  </div>
                  {videoDevices.length === 0 ? (
                    <div className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-[var(--text-muted)] font-mono">
                      No devices found — click Refresh
                    </div>
                  ) : (
                    <div className="relative">
                      <select
                        value={selectedDevice}
                        onChange={e => setSelectedDevice(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white focus:outline-none focus:border-green-500/40 font-mono appearance-none pr-8"
                      >
                        {videoDevices.map(d => (
                          <option key={d.deviceId} value={d.deviceId}
                            style={{ background: '#0a0a0a' }}>
                            {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none" />
                    </div>
                  )}
                </div>
              )}

              {/* URL input for non-FPV protocols */}
              {protocol !== 'fpv' && (
                <div>
                  <label className="text-xs text-[var(--text-muted)] font-mono mb-1.5 block">STREAM URL</label>
                  <input type="text" value={streamUrl}
                    onChange={e => { setStreamUrl(e.target.value); setError('') }}
                    placeholder={selectedProto?.placeholder}
                    className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-green-500/40 font-mono"
                    onKeyDown={e => e.key === 'Enter' && connect()}
                  />
                </div>
              )}
            </div>

            {/* Hint box */}
            <div className="mt-4 p-3 rounded-xl bg-blue-500/5 border border-blue-500/10">
              <p className="text-[10px] font-mono text-blue-300 leading-relaxed">
                {protocol === 'fpv'    && '✓ Plug EWRF 5.8G OTG receiver into USB, click Refresh Devices, select it from the list, then Connect FPV Receiver.'}
                {protocol === 'mjpeg'  && '✓ Same WiFi: use phone IP shown in IP Webcam app. Phone hotspot: use http://192.168.43.1:8080/video'}
                {protocol === 'hls'    && "✓ Run mediamtx or FFmpeg on companion PC to output HLS."}
                {protocol === 'direct' && '✓ Any browser-compatible video URL on the local network.'}
                {protocol === 'rtsp'   && '⚠ Convert to HLS via FFmpeg first — RTSP cannot play in browsers.'}
              </p>
            </div>
          </GlassCard>

          {/* Telemetry */}
          <GlassCard hover={false}>
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Signal size={14} className="text-cyan-400" /> Telemetry
              {!connected && <span className="ml-auto text-[10px] font-mono text-[var(--text-muted)]">OFFLINE</span>}
            </h3>
            <div className="space-y-3">
              {[
                { icon: Wind,        label: 'Altitude', value: connected ? `${tele.altitude} m` : '—', color: 'text-green-400' },
                { icon: Signal,      label: 'Speed',    value: connected ? `${tele.speed} m/s`  : '—', color: 'text-cyan-400' },
                { icon: Battery,     label: 'Battery',  value: connected ? `${tele.battery}%`   : '—', color: Number(tele.battery) < 30 ? 'text-red-400' : 'text-yellow-400' },
                { icon: Wifi,        label: 'Signal',   value: connected ? `${tele.signal}%`    : '—', color: 'text-purple-400' },
                { icon: Thermometer, label: 'Temp',     value: connected ? `${tele.temp}°C`     : '—', color: 'text-orange-400' },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon size={13} className={color} />
                    <span className="text-xs text-[var(--text-secondary)]">{label}</span>
                  </div>
                  <span className={`text-xs font-mono font-semibold ${connected ? color : 'text-[var(--text-muted)]'}`}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* FPV Setup Guide */}
          <GlassCard hover={false}>
            <h3 className="text-xs font-semibold text-[var(--text-muted)] mb-3 font-mono uppercase tracking-wider">
              FPV Setup Guide
            </h3>
            <ol className="space-y-2">
              {[
                'Power on drone & VTX (Sologood 5.8G)',
                'Plug EWRF OTG receiver into laptop USB',
                'Select "FPV Receiver (USB)" source',
                'Click Refresh Devices',
                'Select EWRF from the dropdown',
                'Click Connect FPV Receiver',
              ].map((step, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-[9px] font-mono flex items-center justify-center flex-shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-[11px] text-[var(--text-secondary)] leading-relaxed">{step}</span>
                </li>
              ))}
            </ol>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
