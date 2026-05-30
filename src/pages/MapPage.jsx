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

// India-wide mock markers across real cities
const mockMarkers = [
  { id: 1, position: [22.2531, 84.9011], label: 'NIT Rourkela Campus', city: 'Rourkela, Odisha', type: 'infrastructure', severity: 1, color: '#22c55e', detections: 67, desc: 'Campus surveillance — 67 infrastructure elements mapped.' },
  { id: 2, position: [20.2961, 85.8245], label: 'Flood Zone — Mahanadi', city: 'Cuttack, Odisha', type: 'disaster', severity: 5, color: '#ef4444', detections: 18, desc: 'Severe flooding. 4.5ft water depth. Evacuation required.' },
  { id: 3, position: [28.6139, 77.2090], label: 'Delhi Traffic Corridor', city: 'New Delhi', type: 'traffic', severity: 3, color: '#f97316', detections: 450, desc: 'Heavy traffic on NH-48. 450 vehicles detected, density: high.' },
  { id: 4, position: [19.0760, 72.8777], label: 'Mumbai Coastal Scan', city: 'Mumbai, Maharashtra', type: 'vegetation', severity: 1, color: '#84cc16', detections: 120, desc: 'Coastal vegetation & mangrove cover analysis completed.' },
  { id: 5, position: [12.9716, 77.5946], label: 'Bangalore Tech Park', city: 'Bengaluru, Karnataka', type: 'building', severity: 1, color: '#a855f7', detections: 89, desc: 'Tech corridor infrastructure scan. 89 structures mapped.' },
  { id: 6, position: [17.3850, 78.4867], label: 'Hyderabad Fire Alert', city: 'Hyderabad, Telangana', type: 'disaster', severity: 4, color: '#f97316', detections: 6, desc: 'Active fire & smoke in industrial block. Level 4 alert.' },
  { id: 7, position: [22.5726, 88.3639], label: 'Kolkata Road Survey', city: 'Kolkata, West Bengal', type: 'infrastructure', severity: 2, color: '#eab308', detections: 230, desc: 'Pothole & road damage survey. 230 defects mapped.' },
  { id: 8, position: [26.9124, 75.7873], label: 'Jaipur Land Mapping', city: 'Jaipur, Rajasthan', type: 'vegetation', severity: 1, color: '#06b6d4', detections: 155, desc: 'Agricultural land use and vegetation health analysis.' },
  { id: 9, position: [21.1458, 79.0882], label: 'Nagpur Plantation Zone', city: 'Nagpur, Maharashtra', type: 'vegetation', severity: 1, color: '#4ade80', detections: 320, desc: 'Orange orchard & plantation health monitoring complete.' },
  { id: 10, position: [13.0827, 80.2707], label: 'Chennai Flood Monitor', city: 'Chennai, Tamil Nadu', type: 'disaster', severity: 3, color: '#60a5fa', detections: 14, desc: 'Moderate waterlogging in residential zones. Monitoring active.' },
]

const tileLayers = {
  dark: { url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', name: 'Dark', icon: '🌑' },
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
  const [activeLayer, setActiveLayer] = useState('dark')
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [selectedMarker, setSelectedMarker] = useState(null)
  const [center, setCenter] = useState([22.5, 82.5]) // India geographic center
  const [zoom, setZoom] = useState(5)
  const [userLocation, setUserLocation] = useState(null)
  const [locating, setLocating] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [markers, setMarkers] = useState(mockMarkers)
  const [usingRealData, setUsingRealData] = useState(false)

  // Auto-detect user location on mount
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
        },
        () => {
          // On denial, default to India center
          setCenter([20.5937, 78.9629])
          setZoom(5)
          setLocating(false)
        },
        { timeout: 5000 }
      )
    }
  }, [])

  // Fetch active database markers
  useEffect(() => {
    fetch('/api/v1/dashboard/map-markers')
      .then((res) => {
        if (!res.ok) throw new Error('API error')
        return res.json()
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          const parsed = data.map((m) => ({
            id: m.id,
            position: [m.lat, m.lon],
            label: m.label,
            city: m.lat > 28 ? 'North India Region' : 'Central/South India',
            type: m.type,
            severity: m.severity,
            color: m.color || '#22c55e',
            detections: m.detections || 1,
            desc: `Detection marker from database (lat: ${m.lat.toFixed(4)}, lon: ${m.lon.toFixed(4)}).`
          }))
          setMarkers(parsed)
          setUsingRealData(true)
        }
      })
      .catch((err) => console.log('Using demo GIS markers:', err))
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
            {!usingRealData && (
              <span className="ml-2 text-yellow-400/70 font-mono text-xs">· Demo markers (run an analysis to see real data)</span>
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

          {/* Search */}
          <GlassCard hover={false} className="p-3">
            <div className="relative mb-3">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Search cities, sites..."
                className="glass-input w-full pl-8 py-2 text-xs"
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
          </GlassCard>

          {/* Selected detail card */}
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
