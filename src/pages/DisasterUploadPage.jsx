import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertTriangle, Upload, ArrowRight, Flame, Droplets, Wind, Building, Zap } from 'lucide-react'
import FileDropzone from '../components/ui/FileDropzone'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'

const disasterTypes = [
  { id: 'flood', label: 'Flood', icon: Droplets, color: '#3b82f6' },
  { id: 'fire', label: 'Fire & Smoke', icon: Flame, color: '#ef4444' },
  { id: 'structural', label: 'Structural Damage', icon: Building, color: '#f97316' },
  { id: 'cyclone', label: 'Cyclone / Storm', icon: Wind, color: '#06b6d4' },
  { id: 'landslide', label: 'Landslide', icon: AlertTriangle, color: '#eab308' },
  { id: 'electrical', label: 'Electrical Damage', icon: Zap, color: '#a855f7' },
]

export default function DisasterUploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [selectedType, setSelectedType] = useState(null)

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header with warning accent */}
      <div className="flex items-start gap-3">
        <div className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20 flex-shrink-0 mt-1">
          <AlertTriangle size={20} className="text-orange-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold mb-1">Disaster Analysis</h1>
          <p className="text-sm text-[var(--text-muted)]">
            Upload drone footage from disaster-affected areas for AI-powered damage assessment
          </p>
        </div>
      </div>

      {/* Disaster Type Selection */}
      <GlassCard hover={false} className="border-orange-500/10">
        <h3 className="text-sm font-semibold mb-4">Select Disaster Type</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {disasterTypes.map((type) => (
            <motion.button
              key={type.id}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setSelectedType(type.id)}
              className={`
                flex items-center gap-3 p-4 rounded-xl border transition-all duration-300 text-left
                ${selectedType === type.id
                  ? 'border-opacity-100 bg-opacity-10'
                  : 'border-white/5 bg-white/[0.01] hover:border-white/10'
                }
              `}
              style={{
                borderColor: selectedType === type.id ? type.color : undefined,
                backgroundColor: selectedType === type.id ? `${type.color}08` : undefined,
              }}
            >
              <div
                className="p-2 rounded-lg flex-shrink-0"
                style={{ background: `${type.color}15` }}
              >
                <type.icon size={18} style={{ color: type.color }} />
              </div>
              <span className="text-sm font-medium">{type.label}</span>
            </motion.button>
          ))}
        </div>
      </GlassCard>

      {/* Upload Zone */}
      <FileDropzone onFileSelect={setFile} />

      {/* Action */}
      <div className="flex justify-end">
        <NeonButton
          variant="danger"
          size="lg"
          icon={ArrowRight}
          onClick={() => navigate('/disaster/results/demo-001')}
          disabled={!file || !selectedType}
          className={!file || !selectedType ? 'opacity-50 cursor-not-allowed' : ''}
        >
          Start Disaster Analysis
        </NeonButton>
      </div>
    </div>
  )
}
