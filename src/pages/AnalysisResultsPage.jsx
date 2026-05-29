import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Camera, Download, Filter, Layers, BarChart3, MapPin,
  Eye, Grid, List, Maximize, ZoomIn, Clock
} from 'lucide-react'
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'
import DetectionCard from '../components/ui/DetectionCard'
import ConfidenceBar from '../components/ui/ConfidenceBar'

const mockDetections = [
  { label: 'Car (Red)', category: 'Vehicles', confidence: 96, timestamp: '00:12', location: '28.6°N, 77.2°E', thumbnailColor: '#22c55e' },
  { label: 'Truck', category: 'Vehicles', confidence: 91, timestamp: '00:15', location: '28.6°N, 77.2°E', thumbnailColor: '#22c55e' },
  { label: 'Person (Standing)', category: 'People', confidence: 88, timestamp: '00:18', location: '28.6°N, 77.2°E', thumbnailColor: '#06b6d4' },
  { label: 'Building', category: 'Buildings', confidence: 94, timestamp: '00:22', location: '28.5°N, 77.1°E', thumbnailColor: '#a855f7' },
  { label: 'Pothole (Severe)', category: 'Roads', confidence: 82, timestamp: '00:30', location: '28.5°N, 77.1°E', thumbnailColor: '#f97316' },
  { label: 'Tree (Large)', category: 'Trees', confidence: 97, timestamp: '00:35', location: '28.5°N, 77.1°E', thumbnailColor: '#84cc16' },
  { label: 'Electric Pole', category: 'Infrastructure', confidence: 90, timestamp: '00:41', location: '28.4°N, 77.0°E', thumbnailColor: '#eab308' },
  { label: 'Bike', category: 'Vehicles', confidence: 85, timestamp: '00:48', location: '28.4°N, 77.0°E', thumbnailColor: '#22c55e' },
  { label: 'Crowd Cluster', category: 'People', confidence: 79, timestamp: '00:55', location: '28.4°N, 77.0°E', thumbnailColor: '#06b6d4' },
  { label: 'Solar Panel', category: 'Infrastructure', confidence: 93, timestamp: '01:02', location: '28.3°N, 77.0°E', thumbnailColor: '#f59e0b' },
]

const summaryData = [
  { name: 'Vehicles', count: 42, color: '#22c55e' },
  { name: 'People', count: 28, color: '#06b6d4' },
  { name: 'Buildings', count: 15, color: '#a855f7' },
  { name: 'Trees', count: 67, color: '#84cc16' },
  { name: 'Roads', count: 8, color: '#f97316' },
  { name: 'Infra', count: 12, color: '#eab308' },
]

export default function AnalysisResultsPage() {
  const { id } = useParams()
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [filterCategory, setFilterCategory] = useState('all')

  const filteredDetections = filterCategory === 'all' 
    ? mockDetections 
    : mockDetections.filter(d => d.category === filterCategory)

  const categories = ['all', ...new Set(mockDetections.map(d => d.category))]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">Analysis Results</h1>
          <p className="text-sm text-[var(--text-muted)] font-mono">ID: {id} • 172 objects detected</p>
        </div>
        <div className="flex items-center gap-3">
          <NeonButton variant="secondary" icon={Camera} size="sm">
            Screenshot
          </NeonButton>
          <NeonButton variant="primary" icon={Download}>
            Generate Report
          </NeonButton>
        </div>
      </div>

      {/* Main content: Video + Detections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Video Panel */}
        <div className="lg:col-span-2 space-y-4">
          <GlassCard hover={false} className="p-0 overflow-hidden">
            {/* Video player area */}
            <div className="relative aspect-video bg-gradient-to-br from-gray-900 to-black flex items-center justify-center">
              {/* Mock video with detection boxes */}
              <div className="absolute inset-0 bg-grid opacity-20" />
              
              {/* Simulated detection boxes */}
              <motion.div
                className="absolute border-2 border-green-400 rounded"
                style={{ top: '20%', left: '15%', width: '12%', height: '18%' }}
                animate={{ borderColor: ['rgba(34,197,94,0.8)', 'rgba(34,197,94,0.3)', 'rgba(34,197,94,0.8)'] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <span className="absolute -top-5 left-0 text-[0.6rem] bg-green-500/80 text-white px-1.5 py-0.5 rounded font-mono">
                  Car 96%
                </span>
              </motion.div>

              <motion.div
                className="absolute border-2 border-cyan-400 rounded"
                style={{ top: '35%', left: '55%', width: '8%', height: '22%' }}
                animate={{ borderColor: ['rgba(6,182,212,0.8)', 'rgba(6,182,212,0.3)', 'rgba(6,182,212,0.8)'] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
              >
                <span className="absolute -top-5 left-0 text-[0.6rem] bg-cyan-500/80 text-white px-1.5 py-0.5 rounded font-mono">
                  Person 88%
                </span>
              </motion.div>

              <motion.div
                className="absolute border-2 border-purple-400 rounded"
                style={{ top: '10%', left: '65%', width: '20%', height: '35%' }}
                animate={{ borderColor: ['rgba(168,85,247,0.8)', 'rgba(168,85,247,0.3)', 'rgba(168,85,247,0.8)'] }}
                transition={{ duration: 2, repeat: Infinity, delay: 1 }}
              >
                <span className="absolute -top-5 left-0 text-[0.6rem] bg-purple-500/80 text-white px-1.5 py-0.5 rounded font-mono">
                  Building 94%
                </span>
              </motion.div>

              <motion.div
                className="absolute border-2 border-orange-400 rounded"
                style={{ top: '75%', left: '35%', width: '6%', height: '6%' }}
                animate={{ borderColor: ['rgba(249,115,22,0.8)', 'rgba(249,115,22,0.3)', 'rgba(249,115,22,0.8)'] }}
                transition={{ duration: 2, repeat: Infinity, delay: 0.7 }}
              >
                <span className="absolute -top-5 left-0 text-[0.6rem] bg-orange-500/80 text-white px-1.5 py-0.5 rounded font-mono">
                  Pothole 82%
                </span>
              </motion.div>

              {/* Heatmap overlay */}
              {showHeatmap && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.4 }}
                  className="absolute inset-0"
                  style={{
                    background: 'radial-gradient(circle at 30% 40%, rgba(239,68,68,0.4) 0%, transparent 40%), radial-gradient(circle at 60% 50%, rgba(249,115,22,0.3) 0%, transparent 35%), radial-gradient(circle at 75% 30%, rgba(234,179,8,0.2) 0%, transparent 30%)',
                  }}
                />
              )}

              {/* Center play icon */}
              <div className="text-white/10">
                <Eye size={48} />
              </div>
            </div>

            {/* Controls bar */}
            <div className="p-3 flex items-center justify-between border-t border-white/5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-[var(--text-muted)]">
                  <Clock size={10} className="inline mr-1" />
                  01:23 / 05:45
                </span>
              </div>
              <div className="flex items-center gap-1">
                <NeonButton 
                  variant={showHeatmap ? 'primary' : 'ghost'} 
                  size="sm"
                  onClick={() => setShowHeatmap(!showHeatmap)}
                >
                  <Layers size={14} /> Heatmap
                </NeonButton>
                <NeonButton variant="ghost" size="sm">
                  <Maximize size={14} />
                </NeonButton>
              </div>
            </div>
          </GlassCard>

          {/* Summary Bar Chart */}
          <GlassCard hover={false}>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <BarChart3 size={14} className="text-green-400" />
              Detection Summary
            </h3>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={summaryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip 
                  contentStyle={{ 
                    background: 'rgba(17,24,39,0.9)', 
                    border: '1px solid rgba(57,255,20,0.1)',
                    borderRadius: 10,
                    color: '#f0fdf4',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {summaryData.map((entry, i) => (
                    <motion.rect key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </div>

        {/* Detection Sidebar */}
        <div className="space-y-4">
          {/* Filters */}
          <GlassCard hover={false} className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Filter size={14} className="text-green-400" />
              <h3 className="text-sm font-semibold">Filter</h3>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setFilterCategory(cat)}
                  className={`
                    px-2.5 py-1 rounded-lg text-xs font-medium transition-all
                    ${filterCategory === cat
                      ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                      : 'bg-white/5 text-[var(--text-muted)] border border-transparent hover:bg-white/10'
                    }
                  `}
                >
                  {cat === 'all' ? 'All' : cat}
                </button>
              ))}
            </div>
          </GlassCard>

          {/* Detection list */}
          <GlassCard hover={false} className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">{filteredDetections.length} Detections</h3>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded-lg bg-white/5 text-[var(--text-muted)]"><List size={12} /></button>
                <button className="p-1.5 rounded-lg bg-white/5 text-[var(--text-muted)]"><Grid size={12} /></button>
              </div>
            </div>
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {filteredDetections.map((det, i) => (
                <DetectionCard key={i} {...det} delay={i * 0.03} />
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
