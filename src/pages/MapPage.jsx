import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MapPin, Layers, Navigation, Search, Crosshair, X, AlertTriangle, Zap, Trees, Car, Building2, Flame } from 'lucide-react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'
import SeverityBadge from '../components/ui/SeverityBadge'

// Fix Leaflet default icon
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const customIcon = (color, pulse = false) => new L.DivIcon({
  html: `<div style="
    background:${color};
    width:14px; height:14px;
    border-radius:50%;
    border:2.5px solid rgba(255,255,255,0.9);
    box-shadow: 0 0 ${pulse ? 18 : 10}px ${color}90, 0 0 4px ${color};
    ${pulse ? 'animation: pulse-ring 2s infinite;' : ''}
  "></div>`,
  className: '',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

const userLocationIcon = () => new L.DivIcon({
  html: `<div style="
    background:#22c55e;
    width:18px; height:18px;
    border-radius:50%;
    border:3px solid white;
    box-shadow: 0 0 20px #22c55e, 0 0 40px rgba(34,197,94,0.4);
  "></div><div style="
    position:absolute;
    top:50%; left:50%;
    transform:translate(-50%,-50%);
    width:40px; height:40px;
    border-radius:50%;
    border:2px solid rgba(34,197,94,0.3);
    animation: pulse-ring 2s infinite;
  "></div>`,
  className: '',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

// No hardcoded mock markers — only real DB data is shown

const tileLayers = {
  terrain: { url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', name: 'Terrain', icon: '🏔️' },
  satellite: { url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', name: 'Satellite', icon: '🛰️' },
  street: { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', name: 'Streets', icon: '🗺️' },
}

const typeConfig = {
  traffic: { icon: Car, color: '#f97316', label: 'Traffic' },
  building: { icon: Building2, color: '#a855f7', label: 'Buildings' },
  disaster: { icon: AlertTriangle, color: '#ef4444', label: 'Disaster' },
  vegetation: { icon: Trees, color: '#84cc16', label: 'Vegetation' },
  infrastructure: { icon: Zap, color: '#22c55e', label: 'Infrastructure' },
}

// Component to control the map programmatically
function MapController({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    if (center) {
      map.flyTo(center, zoom || 13, { duration: 1.8, easeLinearity: 0.3 })
    }
  }, [center, zoom, map])
  return null
}

// Locate Me control inside map
function LocateMeControl({ onLocate }) {
  const map = useMap()
  const handleLocate = () => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const latlng = [pos.coords.latitude, pos.coords.longitude]
        onLocate(latlng)
        map.flyTo(latlng, 14, { duration: 1.8 })
      },
      () => alert('Location access denied. Please enable GPS permissions.')
    )
  }
  return (
    <div className="leaflet-bottom leaflet-right" style={{ marginBottom: 28, marginRight: 10 }}>
      <div className="leaflet-control">
        <button
          onClick={handleLocate}
          title="Fly to my location"
          style={{
            background: 'rgba(11,15,25,0.95)',
            border: '1px solid rgba(34,197,94,0.4)',
            borderRadius: 10,
            width: 38, height: 38,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#22c55e',
            boxShadow: '0 0 15px rgba(34,197,94,0.2)',
          }}
        >
          <Navigation size={16} />
        </button>
      </div>
    </div>
  )
}

export default function MapPage() {
  const [activeLayer, setActiveLayer] = useState('terrain')
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [selectedMarker, setSelectedMarker] = useState(null)
  const [center, setCenter] = useState([22.5, 82.5])
  const [zoom, setZoom] = useState(5)
  const [userLocation, setUserLocation] = useState(null)
  const [locating, setLocating] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [markers, setMarkers] = useState([])
  const [usingRealData, setUsingRealData] = useState(false)
  const [weather, setWeather] = useState(null)
  const [weatherGrid, setWeatherGrid] = useState([]) // grid of points for map overlays
  const [activeOverlay, setActiveOverlay] = useState(null) // 'temp' | 'pressure' | 'wind' | null
  const [aircraft, setAircraft] = useState([])
  const [satellites, setSatellites] = useState([])
  const [showAircraft, setShowAircraft] = useState(false)
  const [showSatellites, setShowSatellites] = useState(false)
  const [trafficLoading, setTrafficLoading] = useState(false)

  // Auto-detect user location on mount + fetch weather
  useEffect(() => {
    if (navigator.geolocation) {
      setLocating(true)
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const latlng = [pos.coords.latitude, pos.coords.longitude]
          setUserLocation(latlng)
          setCenter(latlng)
          setZoom(12)
          setLocating(false)
          // Fetch real-time weather from Open-Meteo (free, no API key)
          fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latlng[0]}&longitude=${latlng[1]}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature&wind_speed_unit=kmh&timezone=auto`)
            .then(r => r.json())
            .then(d => {
              const c = d.current
              const wmoDesc = (code) => {
                if (code === 0) return { label: 'Clear Sky', icon: '☀️' }
                if (code <= 3) return { label: 'Partly Cloudy', icon: '⛅' }
                if (code <= 49) return { label: 'Foggy', icon: '🌫️' }
                if (code <= 67) return { label: 'Rainy', icon: '🌧️' }
                if (code <= 77) return { label: 'Snowy', icon: '❄️' }
                if (code <= 82) return { label: 'Rain Showers', icon: '🌦️' }
                if (code <= 99) return { label: 'Thunderstorm', icon: '⛈️' }
                return { label: 'Unknown', icon: '🌡️' }
              }
              const { label, icon } = wmoDesc(c.weather_code)
              setWeather({
                temp: Math.round(c.temperature_2m),
                feels: Math.round(c.apparent_temperature),
                humidity: c.relative_humidity_2m,
                wind: Math.round(c.wind_speed_10m),
                label,
                icon,
              })
              // Fetch a 4x4 grid of points around user for map overlay
              const offsets = [-1.5, -0.5, 0.5, 1.5]
              const gridPoints = []
              for (const dlat of offsets) {
                for (const dlon of offsets) {
                  gridPoints.push({ lat: latlng[0] + dlat, lon: latlng[1] + dlon })
                }
              }
              const latList = gridPoints.map(p => p.lat).join(',')
              const lonList = gridPoints.map(p => p.lon).join(',')
              fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latList}&longitude=${lonList}&current=temperature_2m,surface_pressure,wind_speed_10m&wind_speed_unit=kmh&timezone=auto`)
                .then(r => r.json())
                .then(arr => {
                  const results = Array.isArray(arr) ? arr : [arr]
                  const grid = results.map((item, i) => ({
                    lat: gridPoints[i]?.lat,
                    lon: gridPoints[i]?.lon,
                    temp: Math.round(item.current?.temperature_2m ?? 0),
                    pressure: Math.round(item.current?.surface_pressure ?? 1013),
                    wind: Math.round(item.current?.wind_speed_10m ?? 0),
                  }))
                  setWeatherGrid(grid)
                })
                .catch(() => {})
            })
            .catch(() => {})
        },
        () => {
          setCenter([20.5937, 78.9629])
          setZoom(5)
          setLocating(false)
        },
        { timeout: 5000 }
      )
    }
  }, [])

  // Fetch live markers from DB
  useEffect(() => {
    fetch('/api/v1/dashboard/map-markers')
      .then((res) => { if (!res.ok) throw new Error(); return res.json() })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          const parsed = data
            .filter(m => m.lat && m.lon && !String(m.id).startsWith('mock') && !String(m.label).includes('Mock'))
            .map((m) => ({
              id: m.id,
              position: [m.lat, m.lon],
              label: m.label,
              city: `${m.lat.toFixed(3)}°N, ${m.lon.toFixed(3)}°E`,
              type: m.type || 'infrastructure',
              severity: m.severity || 1,
              color: m.color || '#22c55e',
              detections: m.detections || 1,
              desc: m.label,
            }))
          if (parsed.length > 0) {
            setMarkers(parsed)
            setUsingRealData(true)
          }
        }
      })
      .catch(() => {})
  }, [])

  const handleLocateMe = () => {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const latlng = [pos.coords.latitude, pos.coords.longitude]
        setUserLocation(latlng)
        setCenter(latlng)
        setZoom(14)
        setLocating(false)
      },
      () => setLocating(false),
      { timeout: 8000 }
    )
  }

  const fetchAircraft = async () => {
    const loc = userLocation || [20.5937, 78.9629]
    setTrafficLoading(true)
    try {
      const res = await fetch(`/api/v1/dashboard/live-aircraft?lat=${loc[0]}&lon=${loc[1]}&radius=8`)
      const data = await res.json()
      setAircraft(data.aircraft || [])
    } catch { setAircraft([]) }
    setTrafficLoading(false)
  }

  const fetchSatellites = async () => {
    setTrafficLoading(true)
    try {
      const res = await fetch('/api/v1/dashboard/live-satellites')
      const data = await res.json()
      setSatellites(data.satellites || [])
    } catch { setSatellites([]) }
    setTrafficLoading(false)
  }

  const handleToggleAircraft = () => {
    if (!showAircraft && aircraft.length === 0) fetchAircraft()
    setShowAircraft(v => !v)
  }

  const handleToggleSatellites = () => {
    if (!showSatellites && satellites.length === 0) fetchSatellites()
    setShowSatellites(v => !v)
  }

  const filteredMarkers = markers.filter((m) => {
    const matchType = filterType === 'all' || m.type === filterType
    const matchSearch = searchQuery === '' ||
      m.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.city.toLowerCase().includes(searchQuery.toLowerCase())
    return matchType && matchSearch
  })

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold mb-1">GIS Intelligence Map</h1>
          <p className="text-sm text-[var(--text-muted)]">
            Live geospatial drone reconnaissance — India-wide coverage
            {locating && <span className="ml-2 text-green-400 animate-pulse font-mono text-xs">🛰 Acquiring GPS...</span>}
            {userLocation && !locating && (
              <span className="ml-2 text-green-400 font-mono text-xs">
                📍 {userLocation[0].toFixed(4)}°N, {userLocation[1].toFixed(4)}°E
              </span>
            )}
            {usingRealData && (
              <span className="ml-2 text-green-400/70 font-mono text-xs">· {markers.length} live detection sites</span>
            )}
          </p>
        </div>

        {/* Layer switcher */}
        <div className="flex items-center gap-2">
          {Object.entries(tileLayers).map(([key, layer]) => (
            <button
              key={key}
              onClick={() => setActiveLayer(key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono font-semibold border transition-all cursor-pointer ${
                activeLayer === key
                  ? 'bg-green-500/15 text-green-400 border-green-500/30 shadow-[0_0_12px_rgba(34,197,94,0.15)]'
                  : 'bg-white/[0.02] text-[var(--text-muted)] border-white/5 hover:border-white/10'
              }`}
            >
              {layer.icon} {layer.name}
            </button>
          ))}
          <button
            onClick={handleLocateMe}
            disabled={locating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold border border-green-500/30 bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-all cursor-pointer disabled:opacity-50"
          >
            <Navigation size={13} className={locating ? 'animate-spin' : ''} />
            {locating ? 'Locating...' : 'Locate Me'}
          </button>
        </div>
      </div>

      {/* Main Layout: Map + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4" style={{ height: 'calc(100vh - 210px)' }}>

        {/* Interactive Map - 3 cols */}
        <div className="lg:col-span-3 rounded-2xl overflow-hidden border border-white/10 shadow-[0_0_30px_rgba(0,0,0,0.5)] relative">
          <MapContainer
            center={center}
            zoom={zoom}
            style={{ height: '100%', width: '100%', background: '#0b0f19' }}
            zoomControl={false}
          >
            <TileLayer url={tileLayers[activeLayer].url} attribution="&copy; SkyRecon AI" />
            <MapController center={center} zoom={zoom} />

            {/* User location marker */}
            {userLocation && (
              <Marker position={userLocation} icon={userLocationIcon()}>
                <Popup>
                  <div className="text-xs font-mono">
                    <p className="font-bold text-green-600">📍 Your Location</p>
                    <p>{userLocation[0].toFixed(4)}°N, {userLocation[1].toFixed(4)}°E</p>
                  </div>
                </Popup>
              </Marker>
            )}

            {/* Detection markers */}
            {filteredMarkers.map((marker) => (
              <Marker
                key={marker.id}
                position={marker.position}
                icon={customIcon(marker.color, marker.severity >= 4)}
                eventHandlers={{
                  click: () => {
                    setSelectedMarker(marker)
                    setCenter(marker.position)
                    setZoom(13)
                  },
                }}
              >
                <Popup>
                  <div style={{ fontFamily: 'monospace', minWidth: 160 }}>
                    <p style={{ fontWeight: 'bold', marginBottom: 4 }}>{marker.label}</p>
                    <p style={{ fontSize: 11, color: '#666' }}>{marker.city}</p>
                    <p style={{ fontSize: 11 }}>{marker.detections} detections</p>
                  </div>
                </Popup>
              </Marker>
            ))}

            {/* Heatmap circles */}
            {showHeatmap && filteredMarkers.map((marker) => (
              <Circle
                key={`heat-${marker.id}`}
                center={marker.position}
                radius={marker.detections * 40}
                pathOptions={{
                  fillColor: marker.color,
                  fillOpacity: 0.15,
                  stroke: true,
                  color: marker.color,
                  weight: 1,
                  opacity: 0.25,
                }}
              />
            ))}

            {/* Aircraft markers */}
            {showAircraft && aircraft.map((ac) => (
              <Marker
                key={ac.icao}
                position={[ac.lat, ac.lon]}
                icon={new L.DivIcon({
                  html: `<div style="font-size:18px;transform:rotate(${ac.heading}deg);filter:drop-shadow(0 0 4px #06b6d4)" title="${ac.callsign}">✈️</div>`,
                  className: '', iconSize: [20, 20], iconAnchor: [10, 10],
                })}
              >
                <Popup>
                  <div style={{ fontFamily: 'monospace', fontSize: 11 }}>
                    <b>✈️ {ac.callsign}</b><br />
                    Country: {ac.country}<br />
                    Alt: {ac.altitude}m &nbsp; Speed: {ac.speed} m/s<br />
                    Heading: {ac.heading}°<br />
                    {ac.on_ground ? '🟡 On Ground' : '🟢 Airborne'}
                  </div>
                </Popup>
              </Marker>
            ))}

            {/* Satellite markers */}
            {showSatellites && satellites.map((sat, i) => (
              <Marker
                key={i}
                position={[sat.lat, sat.lon]}
                icon={new L.DivIcon({
                  html: `<div style="font-size:16px;filter:drop-shadow(0 0 5px #a855f7)" title="${sat.name}">🛰️</div>`,
                  className: '', iconSize: [18, 18], iconAnchor: [9, 9],
                })}
              >
                <Popup>
                  <div style={{ fontFamily: 'monospace', fontSize: 11 }}>
                    <b>🛰️ {sat.name}</b><br />
                    Alt: ~{sat.altitude_km} km<br />
                    Inclination: {sat.inclination}°<br />
                    Period: {sat.period_min} min
                  </div>
                </Popup>
              </Marker>
            ))}
            {activeOverlay && weatherGrid.map((pt, i) => {
              if (!pt.lat || !pt.lon) return null
              let color = '#06b6d4'
              let value = ''
              if (activeOverlay === 'temp') {
                const t = pt.temp
                color = t > 35 ? '#ef4444' : t > 28 ? '#f97316' : t > 20 ? '#eab308' : t > 10 ? '#22c55e' : '#60a5fa'
                value = `${t}°C`
              } else if (activeOverlay === 'pressure') {
                const p = pt.pressure
                color = p < 1005 ? '#3b82f6' : p < 1013 ? '#06b6d4' : p < 1020 ? '#22c55e' : '#f97316'
                value = `${p} hPa`
              } else if (activeOverlay === 'wind') {
                const w = pt.wind
                color = w > 40 ? '#ef4444' : w > 25 ? '#f97316' : w > 15 ? '#eab308' : '#22c55e'
                value = `${w} km/h`
              }
              return (
                <Circle
                  key={`wx-${i}`}
                  center={[pt.lat, pt.lon]}
                  radius={80000}
                  pathOptions={{ fillColor: color, fillOpacity: 0.18, stroke: true, color, weight: 1, opacity: 0.35 }}
                >
                  <Popup>
                    <div style={{ fontFamily: 'monospace', fontSize: 11 }}>
                      <b>{activeOverlay.toUpperCase()}</b>: {value}<br />
                      {pt.lat.toFixed(2)}°N {pt.lon.toFixed(2)}°E
                    </div>
                  </Popup>
                </Circle>
              )
            })}
          </MapContainer>

          {/* Map overlay stats */}
          <div className="absolute bottom-4 left-4 flex items-center gap-2 z-[1000] pointer-events-none">
            <div className="bg-black/80 backdrop-blur-sm border border-green-500/20 rounded-xl px-3 py-2 text-[10px] font-mono">
              <span className="text-green-400">{filteredMarkers.length}</span>
              <span className="text-[var(--text-muted)] ml-1">sites mapped</span>
            </div>
            <div className="bg-black/80 backdrop-blur-sm border border-red-500/20 rounded-xl px-3 py-2 text-[10px] font-mono">
              <span className="text-red-400">{filteredMarkers.filter(m => m.severity >= 4).length}</span>
              <span className="text-[var(--text-muted)] ml-1">critical alerts</span>
            </div>
          </div>
        </div>

        {/* Sidebar - 1 col */}
        <div className="space-y-3 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 210px)' }}>

          {/* Weather Card */}
          {weather && (
            <GlassCard hover={false} className="p-3 border-cyan-500/10">
              <p className="text-[9px] font-mono text-cyan-400 uppercase tracking-widest mb-2">Live Weather · Your Location</p>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{weather.icon}</span>
                  <div>
                    <p className="text-lg font-bold text-white">{weather.temp}°C</p>
                    <p className="text-[10px] text-[var(--text-muted)]">{weather.label}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-[var(--text-muted)] font-mono">Feels {weather.feels}°C</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <div className="bg-white/[0.02] rounded-lg p-2 text-center">
                  <p className="text-xs font-bold text-cyan-400">{weather.humidity}%</p>
                  <p className="text-[9px] text-[var(--text-muted)] font-mono">Humidity</p>
                </div>
                <div className="bg-white/[0.02] rounded-lg p-2 text-center">
                  <p className="text-xs font-bold text-cyan-400">{weather.wind} km/h</p>
                  <p className="text-[9px] text-[var(--text-muted)] font-mono">Wind</p>
                </div>
              </div>
              <p className="text-[8px] text-[var(--text-muted)] font-mono mt-2 text-center">Open-Meteo · No API key · Live data</p>
              {weatherGrid.length > 0 && (
                <div className="mt-3 pt-2 border-t border-white/5">
                  <p className="text-[9px] font-mono text-[var(--text-muted)] mb-1.5">MAP OVERLAY</p>
                  <div className="grid grid-cols-3 gap-1">
                    {[
                      { key: 'temp', label: 'Temp', color: 'text-orange-400' },
                      { key: 'pressure', label: 'Pressure', color: 'text-blue-400' },
                      { key: 'wind', label: 'Wind', color: 'text-green-400' },
                    ].map(o => (
                      <button
                        key={o.key}
                        onClick={() => setActiveOverlay(activeOverlay === o.key ? null : o.key)}
                        className={`py-1 rounded-lg text-[9px] font-mono font-bold border transition-all cursor-pointer ${
                          activeOverlay === o.key
                            ? `${o.color} bg-white/10 border-white/20`
                            : 'text-[var(--text-muted)] border-white/5 hover:border-white/10'
                        }`}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                  <div className="mt-1.5 flex gap-1 text-[8px] font-mono text-[var(--text-muted)] justify-between">
                    {activeOverlay === 'temp' && <><span className="text-blue-400">■ Cold</span><span className="text-green-400">■ Mild</span><span className="text-orange-400">■ Hot</span><span className="text-red-400">■ Very Hot</span></>}
                    {activeOverlay === 'pressure' && <><span className="text-blue-400">■ Low</span><span className="text-cyan-400">■ Normal</span><span className="text-orange-400">■ High</span></>}
                    {activeOverlay === 'wind' && <><span className="text-green-400">■ Calm</span><span className="text-yellow-400">■ Moderate</span><span className="text-red-400">■ Strong</span></>}
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {/* Air Traffic & Satellite Card */}
          <GlassCard hover={false} className="p-3 border-purple-500/10">
            <p className="text-[9px] font-mono text-purple-400 uppercase tracking-widest mb-2">Live Traffic Layers</p>
            <div className="space-y-2">
              <button
                onClick={handleToggleAircraft}
                disabled={trafficLoading}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl border text-xs font-mono font-semibold transition-all cursor-pointer disabled:opacity-50 ${
                  showAircraft
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                    : 'bg-white/[0.02] border-white/5 text-[var(--text-muted)] hover:border-white/10'
                }`}
              >
                <span>✈️ Air Traffic</span>
                <span className="text-[9px]">
                  {showAircraft ? `${aircraft.length} aircraft` : 'OFF'}
                </span>
              </button>
              <button
                onClick={handleToggleSatellites}
                disabled={trafficLoading}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl border text-xs font-mono font-semibold transition-all cursor-pointer disabled:opacity-50 ${
                  showSatellites
                    ? 'bg-purple-500/10 border-purple-500/30 text-purple-400'
                    : 'bg-white/[0.02] border-white/5 text-[var(--text-muted)] hover:border-white/10'
                }`}
              >
                <span>🛰️ Satellites</span>
                <span className="text-[9px]">
                  {showSatellites ? `${satellites.length} tracked` : 'OFF'}
                </span>
              </button>
              {trafficLoading && (
                <p className="text-[9px] text-[var(--text-muted)] font-mono text-center animate-pulse">Fetching live data...</p>
              )}
              {showAircraft && aircraft.length === 0 && !trafficLoading && (
                <p className="text-[9px] text-yellow-400/70 font-mono text-center">No aircraft in range (OpenSky may rate-limit anonymous requests)</p>
              )}
            </div>
            <p className="text-[8px] text-[var(--text-muted)] font-mono mt-2 text-center">OpenSky Network · Celestrak · Free APIs</p>
          </GlassCard>

          {/* Search */}
          <GlassCard hover={false} className="p-3">
            <div className="flex items-center gap-2 glass-input py-2 px-3 mb-3">
              <Search size={13} className="text-[var(--text-muted)] flex-shrink-0" />
              <input
                type="text"
                placeholder="Search sites..."
                className="bg-transparent outline-none text-xs w-full text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Type filter chips */}
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setFilterType('all')}
                className={`px-2 py-0.5 rounded text-[10px] font-mono border cursor-pointer transition-all ${
                  filterType === 'all' ? 'bg-white/10 text-white border-white/20' : 'text-[var(--text-muted)] border-white/5 hover:border-white/10'
                }`}
              >ALL</button>
              {Object.entries(typeConfig).map(([type, cfg]) => (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  style={filterType === type ? { borderColor: cfg.color + '60', backgroundColor: cfg.color + '15', color: cfg.color } : {}}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono border cursor-pointer transition-all ${
                    filterType !== type ? 'text-[var(--text-muted)] border-white/5 hover:border-white/10' : ''
                  }`}
                >
                  {cfg.label.toUpperCase()} ({markers.filter(m => m.type === type).length})
                </button>
              ))}
            </div>

            {/* Heatmap toggle */}
            <label className="flex items-center gap-2 mt-3 cursor-pointer">
              <div
                onClick={() => setShowHeatmap(!showHeatmap)}
                className={`w-8 h-4 rounded-full transition-all cursor-pointer relative ${showHeatmap ? 'bg-green-500' : 'bg-white/10'}`}
              >
                <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all ${showHeatmap ? 'right-0.5' : 'left-0.5'}`} />
              </div>
              <span className="text-xs text-[var(--text-secondary)]">Show Heatmap</span>
            </label>
          </GlassCard>

          {/* Markers list */}
          <GlassCard hover={false} className="p-3">
            <h3 className="text-xs font-semibold mb-2.5 flex items-center gap-2 text-[var(--text-secondary)] font-mono uppercase tracking-wider">
              <MapPin size={13} className="text-green-400" />
              Recon Sites ({filteredMarkers.length})
            </h3>
            {!usingRealData ? (
              <div className="py-6 flex flex-col items-center gap-2 text-center">
                <MapPin size={22} className="text-[var(--text-muted)]" />
                <p className="text-[10px] text-[var(--text-muted)] font-mono leading-relaxed">
                  No recon sites yet.<br />Run an analysis to plot<br />real detection markers here.
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
              {filteredMarkers.map((marker) => {
                const TypeIcon = typeConfig[marker.type]?.icon || MapPin
                return (
                  <motion.button
                    key={marker.id}
                    whileHover={{ x: 2 }}
                    onClick={() => {
                      setSelectedMarker(marker)
                      setCenter(marker.position)
                      setZoom(13)
                    }}
                    className={`w-full flex items-center gap-2.5 p-2.5 rounded-xl text-left transition-all cursor-pointer ${
                      selectedMarker?.id === marker.id
                        ? 'bg-green-500/10 border border-green-500/20'
                        : 'hover:bg-white/[0.03] border border-transparent'
                    }`}
                  >
                    <div
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: marker.color, boxShadow: `0 0 6px ${marker.color}80` }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-medium truncate text-white">{marker.label}</p>
                      <p className="text-[9px] text-[var(--text-muted)] truncate">{marker.city}</p>
                    </div>
                    <SeverityBadge level={marker.severity} size="sm" showLabel={false} />
                  </motion.button>
                )
              })}
              </div>
            )}
          </GlassCard>
          <AnimatePresence>
            {selectedMarker && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}>
                <GlassCard hover={false} className="p-4 border-white/10">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0 pr-2">
                      <p className="text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider">{selectedMarker.city}</p>
                      <h3 className="text-sm font-bold text-white mt-0.5 leading-tight">{selectedMarker.label}</h3>
                    </div>
                    <button
                      onClick={() => setSelectedMarker(null)}
                      className="text-[var(--text-muted)] hover:text-white p-0.5 cursor-pointer flex-shrink-0"
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed mb-3">{selectedMarker.desc}</p>

                  <div className="space-y-1.5 text-[11px]">
                    <div className="flex justify-between items-center py-1 border-b border-white/5">
                      <span className="text-[var(--text-muted)] font-mono">GPS</span>
                      <span className="font-mono text-green-400">{selectedMarker.position[0].toFixed(4)}°N, {selectedMarker.position[1].toFixed(4)}°E</span>
                    </div>
                    <div className="flex justify-between items-center py-1 border-b border-white/5">
                      <span className="text-[var(--text-muted)] font-mono">Detections</span>
                      <span className="font-mono text-white font-semibold">{selectedMarker.detections}</span>
                    </div>
                    <div className="flex justify-between items-center py-1 border-b border-white/5">
                      <span className="text-[var(--text-muted)] font-mono">Type</span>
                      <span className="text-white capitalize">{typeConfig[selectedMarker.type]?.label}</span>
                    </div>
                    <div className="flex justify-between items-center pt-1">
                      <span className="text-[var(--text-muted)] font-mono">Severity</span>
                      <SeverityBadge level={selectedMarker.severity} size="sm" />
                    </div>
                  </div>

                  <button
                    onClick={() => { setCenter(selectedMarker.position); setZoom(15) }}
                    className="mt-3 w-full py-1.5 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-[11px] font-mono hover:bg-green-500/20 transition-all cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <Crosshair size={12} />
                    ZOOM INTO SITE
                  </button>
                </GlassCard>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
