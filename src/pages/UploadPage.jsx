import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Upload, ArrowRight, Film, Satellite } from 'lucide-react'
import FileDropzone from '../components/ui/FileDropzone'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'

export default function UploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [metadata, setMetadata] = useState({
    projectName: '',
    location: '',
    droneModel: '',
    description: '',
  })

  const handleDetectLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords
          setMetadata(prev => ({
            ...prev,
            location: `${latitude.toFixed(6)}°N, ${longitude.toFixed(6)}°E`
          }))
        },
        () => {
          // Fallback to NIT Rourkela coordinates for testing
          setMetadata(prev => ({
            ...prev,
            location: '22.2531°N, 84.9011°E (NIT Rourkela)'
          }))
        }
      )
    } else {
      setMetadata(prev => ({
        ...prev,
        location: '22.2531°N, 84.9011°E (NIT Rourkela)'
      }))
    }
  }

  const handleFillMockData = () => {
    setMetadata({
      projectName: 'NIT Rourkela Campus Survey',
      location: '22.2531°N, 84.9011°E',
      droneModel: 'DJI Mavic 3 Pro',
      description: 'Aerial monitoring of campus green cover, vehicle tracking, and road condition scanning.',
    })
  }

  const handleProceed = () => {
    // Store file reference and navigate to config
    navigate('/analysis/config')
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-1">Upload Drone Footage</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Upload your drone video to begin AI-powered analysis
        </p>
      </div>

      {/* Upload Zone */}
      <FileDropzone onFileSelect={setFile} />

      {/* Video preview */}
      {file && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <GlassCard hover={false}>
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Film size={16} className="text-green-400" />
              Video Preview
            </h3>
            <div className="rounded-xl overflow-hidden bg-black/40 aspect-video flex items-center justify-center">
              <video
                src={URL.createObjectURL(file)}
                controls
                className="w-full h-full object-contain"
              />
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Project Metadata */}
      <GlassCard hover={false} delay={0.1}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Satellite size={16} className="text-cyan-400" />
            Project Information
          </h3>
          <button 
            type="button"
            onClick={handleFillMockData}
            className="text-xs text-green-400 hover:text-green-300 font-mono flex items-center gap-1 bg-green-500/5 hover:bg-green-500/10 border border-green-500/10 px-2 py-1 rounded-lg transition-colors cursor-pointer"
          >
            Auto-Fill Test Data
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1.5 block">Project Name</label>
            <input
              type="text"
              placeholder="e.g., Highway Survey NH-48"
              className="glass-input w-full"
              value={metadata.projectName}
              onChange={(e) => setMetadata({ ...metadata, projectName: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1.5 block">Location</label>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g., 28.6139°N, 77.2090°E"
                className="glass-input w-full pr-24"
                value={metadata.location}
                onChange={(e) => setMetadata({ ...metadata, location: e.target.value })}
              />
              <button
                type="button"
                onClick={handleDetectLocation}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-1.5 rounded-lg hover:bg-cyan-500 hover:text-black font-mono transition-all duration-300 cursor-pointer"
              >
                Auto-Detect
              </button>
            </div>
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1.5 block">Drone Model</label>
            <input
              type="text"
              placeholder="e.g., DJI Mavic 3"
              className="glass-input w-full"
              value={metadata.droneModel}
              onChange={(e) => setMetadata({ ...metadata, droneModel: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-[var(--text-muted)] mb-1.5 block">Description</label>
            <input
              type="text"
              placeholder="Brief description of the survey"
              className="glass-input w-full"
              value={metadata.description}
              onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
            />
          </div>
        </div>
      </GlassCard>

      {/* Action */}
      <div className="flex justify-end">
        <NeonButton 
          variant="primary" 
          size="lg" 
          icon={ArrowRight}
          onClick={handleProceed}
          disabled={!file}
          className={!file ? 'opacity-50 cursor-not-allowed' : ''}
        >
          Configure Analysis
        </NeonButton>
      </div>
    </div>
  )
}
