import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Scan, Sparkles, ChevronDown, ChevronRight, Play, Search,
  Users, Car, TreePine, Zap, Building, Droplets, Construction,
  Flame, TrafficCone, Sun, CircleDot, Fence, Brain, MessageSquare
} from 'lucide-react'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'

const standardCategories = [
  { id: 'people', label: 'People', icon: Users, count: 5, color: '#06b6d4' },
  { id: 'vehicles', label: 'Vehicles', icon: Car, count: 13, color: '#22c55e' },
  { id: 'plants', label: 'Plants & Trees', icon: TreePine, count: 6, color: '#84cc16' },
  { id: 'buildings', label: 'Buildings', icon: Building, count: 4, color: '#a855f7' },
  { id: 'roads', label: 'Roads & Potholes', icon: TrafficCone, count: 5, color: '#f97316' },
  { id: 'water', label: 'Water Bodies', icon: Droplets, count: 3, color: '#3b82f6' },
  { id: 'electric', label: 'Electric & Poles', icon: Zap, count: 3, color: '#eab308' },
  { id: 'construction', label: 'Construction', icon: Construction, count: 4, color: '#ef4444' },
  { id: 'fire', label: 'Fire & Smoke', icon: Flame, count: 2, color: '#ef4444' },
  { id: 'solar', label: 'Solar Panels', icon: Sun, count: 2, color: '#f59e0b' },
  { id: 'agriculture', label: 'Agricultural Land', icon: Fence, count: 3, color: '#65a30d' },
  { id: 'parking', label: 'Parking Areas', icon: CircleDot, count: 2, color: '#64748b' },
]

const characteristicsMap = {
  vehicles: [
    { id: 'light', label: 'Light Vehicle' },
    { id: 'heavy', label: 'Heavy Vehicle' },
    { id: '2w', label: '2 Wheeler' },
    { id: '3w', label: '3 Wheeler' },
    { id: '4w', label: '4 Wheeler' },
    { id: 'bike', label: 'Bike' },
    { id: 'car', label: 'Car' },
    { id: 'bus', label: 'Bus' },
    { id: 'truck', label: 'Truck' },
    { id: 'ambulance', label: 'Ambulance' },
    { id: 'police', label: 'Police Vehicle' },
    { id: 'moving', label: 'Moving' },
    { id: 'stationary', label: 'Stationary' },
  ],
  people: [
    { id: 'male', label: 'Male' },
    { id: 'female', label: 'Female' },
    { id: 'child', label: 'Child' },
    { id: 'elderly', label: 'Elderly' },
    { id: 'worker', label: 'Worker' },
    { id: 'helmet', label: 'Helmet Detection' },
    { id: 'safety', label: 'Safety Jacket' },
    { id: 'crowd', label: 'Crowd Density' },
  ],
  plants: [
    { id: 'potted', label: 'Potted Plants' },
    { id: 'small', label: 'Small Plants' },
    { id: 'medium', label: 'Medium Plants' },
    { id: 'large', label: 'Large Trees' },
    { id: 'dry', label: 'Dry Trees' },
    { id: 'dense', label: 'Dense Vegetation' },
  ],
  roads: [
    { id: 'pothole', label: 'Pothole Detection' },
    { id: 'severity', label: 'Damage Severity' },
    { id: 'water-fill', label: 'Water-Filled Pothole' },
    { id: 'priority', label: 'Maintenance Priority' },
    { id: 'blockage', label: 'Road Blockage' },
  ],
}

const nlqExamples = [
  'Count all traffic lights in the footage',
  'Detect damaged buildings near water',
  'Find red vehicles on main road',
  'Count solar panels on rooftops',
  'Detect empty parking spaces',
  'Find flooded road sections',
]

export default function AnalysisConfigPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('standard') // 'standard' | 'custom' | 'nlq'
  const [selectedCategories, setSelectedCategories] = useState(new Set())
  const [expandedCategory, setExpandedCategory] = useState(null)
  const [selectedCharacteristics, setSelectedCharacteristics] = useState(new Set())
  const [customQuery, setCustomQuery] = useState('')
  const [nlQuery, setNlQuery] = useState('')

  const toggleCategory = (id) => {
    const next = new Set(selectedCategories)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setSelectedCategories(next)
  }

  const toggleCharacteristic = (id) => {
    const next = new Set(selectedCharacteristics)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedCharacteristics(next)
  }

  const handleStartAnalysis = () => {
    navigate('/analysis/results/demo-001')
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-1">Configure Analysis</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Select detection mode and categories for AI analysis
        </p>
      </div>

      {/* Detection Mode Selector */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { id: 'standard', icon: Scan, title: 'Standard Detection', desc: 'Predefined AI categories', color: '#22c55e' },
          { id: 'custom', icon: Sparkles, title: 'Custom AI Detection', desc: 'Open vocabulary detection', color: '#06b6d4' },
          { id: 'nlq', icon: MessageSquare, title: 'Natural Language', desc: 'Ask AI in plain English', color: '#a855f7' },
        ].map((m) => (
          <motion.div
            key={m.id}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setMode(m.id)}
            className={`
              glass-card p-5 cursor-pointer transition-all duration-300
              ${mode === m.id 
                ? 'border-opacity-100' 
                : 'border-opacity-30 opacity-60 hover:opacity-80'
              }
            `}
            style={{ 
              borderColor: mode === m.id ? m.color : undefined,
              boxShadow: mode === m.id ? `0 0 30px ${m.color}15` : undefined,
            }}
          >
            <div 
              className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
              style={{ background: `${m.color}15`, border: `1px solid ${m.color}20` }}
            >
              <m.icon size={20} style={{ color: m.color }} />
            </div>
            <h3 className="text-sm font-semibold mb-0.5">{m.title}</h3>
            <p className="text-xs text-[var(--text-muted)]">{m.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* Standard Detection Categories */}
      <AnimatePresence mode="wait">
        {mode === 'standard' && (
          <motion.div
            key="standard"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <GlassCard hover={false}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold">Detection Categories</h3>
                <button 
                  onClick={() => {
                    if (selectedCategories.size === standardCategories.length) {
                      setSelectedCategories(new Set())
                    } else {
                      setSelectedCategories(new Set(standardCategories.map(c => c.id)))
                    }
                  }}
                  className="text-xs text-green-400 hover:text-green-300 transition-colors"
                >
                  {selectedCategories.size === standardCategories.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {standardCategories.map((cat) => (
                  <div key={cat.id}>
                    <motion.div
                      whileTap={{ scale: 0.97 }}
                      onClick={() => toggleCategory(cat.id)}
                      className={`
                        relative flex items-center gap-2.5 p-3 rounded-xl cursor-pointer
                        transition-all duration-200 border
                        ${selectedCategories.has(cat.id)
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-white/[0.01] border-white/5 hover:border-white/10'
                        }
                      `}
                    >
                      <div 
                        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ background: `${cat.color}10` }}
                      >
                        <cat.icon size={14} style={{ color: cat.color }} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium truncate">{cat.label}</p>
                        <p className="text-[0.6rem] text-[var(--text-muted)]">{cat.count} sub-types</p>
                      </div>
                      {/* Checkbox */}
                      <div className={`
                        absolute top-2 right-2 w-4 h-4 rounded border flex items-center justify-center
                        transition-all duration-200
                        ${selectedCategories.has(cat.id)
                          ? 'bg-green-500 border-green-500'
                          : 'border-white/20'
                        }
                      `}>
                        {selectedCategories.has(cat.id) && (
                          <motion.svg
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            width="10" height="10" viewBox="0 0 10 10"
                          >
                            <path d="M2 5 L4 7 L8 3" stroke="white" strokeWidth="1.5" fill="none" />
                          </motion.svg>
                        )}
                      </div>
                    </motion.div>

                    {/* Expandable characteristics */}
                    {selectedCategories.has(cat.id) && characteristicsMap[cat.id] && (
                      <div className="mt-1">
                        <button
                          onClick={() => setExpandedCategory(expandedCategory === cat.id ? null : cat.id)}
                          className="flex items-center gap-1 text-[0.65rem] text-green-400 hover:text-green-300 px-3 py-1"
                        >
                          {expandedCategory === cat.id ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                          Characteristics
                        </button>
                        <AnimatePresence>
                          {expandedCategory === cat.id && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="p-2 space-y-1">
                                {characteristicsMap[cat.id].map((ch) => (
                                  <label
                                    key={ch.id}
                                    className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-white/[0.02] cursor-pointer text-xs text-[var(--text-secondary)]"
                                  >
                                    <input
                                      type="checkbox"
                                      checked={selectedCharacteristics.has(ch.id)}
                                      onChange={() => toggleCharacteristic(ch.id)}
                                      className="accent-green-500 w-3 h-3"
                                    />
                                    {ch.label}
                                  </label>
                                ))}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {mode === 'custom' && (
          <motion.div
            key="custom"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <GlassCard hover={false}>
              <div className="flex items-center gap-2 mb-4">
                <Brain size={16} className="text-cyan-400" />
                <h3 className="text-sm font-semibold">Open Vocabulary Detection</h3>
              </div>
              <p className="text-xs text-[var(--text-muted)] mb-4">
                Type any object you want the AI to detect. Uses YOLO-World for zero-shot detection.
              </p>
              <textarea
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                placeholder="Enter objects to detect (one per line):&#10;traffic lights&#10;solar panels&#10;damaged roofs&#10;mobile towers&#10;parking slots"
                className="glass-input w-full h-40 resize-none font-mono text-sm"
              />
              <div className="flex flex-wrap gap-2 mt-3">
                {['solar panels', 'mobile towers', 'school buildings', 'temples', 'boats', 'pipelines'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setCustomQuery((prev) => prev ? prev + '\n' + s : s)}
                    className="px-2.5 py-1 rounded-lg text-xs bg-cyan-500/5 border border-cyan-500/10 
                               text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                  >
                    + {s}
                  </button>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {mode === 'nlq' && (
          <motion.div
            key="nlq"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <GlassCard hover={false}>
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare size={16} className="text-purple-400" />
                <h3 className="text-sm font-semibold">Natural Language Query</h3>
              </div>
              <p className="text-xs text-[var(--text-muted)] mb-4">
                Ask the AI what you want to find using natural language.
              </p>
              <div className="relative">
                <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  type="text"
                  value={nlQuery}
                  onChange={(e) => setNlQuery(e.target.value)}
                  placeholder="e.g., Count all red vehicles on the highway..."
                  className="glass-input w-full pl-11 py-3 text-sm"
                />
              </div>
              <div className="mt-3">
                <p className="text-[0.65rem] text-[var(--text-muted)] mb-2 uppercase tracking-wider">Try these:</p>
                <div className="flex flex-wrap gap-2">
                  {nlqExamples.map((ex) => (
                    <button
                      key={ex}
                      onClick={() => setNlQuery(ex)}
                      className="px-3 py-1.5 rounded-lg text-xs bg-purple-500/5 border border-purple-500/10 
                                 text-purple-300 hover:bg-purple-500/10 transition-colors text-left"
                    >
                      "{ex}"
                    </button>
                  ))}
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Start Analysis Button */}
      <div className="flex justify-end pt-2">
        <NeonButton 
          variant="primary" 
          size="lg" 
          icon={Play}
          onClick={handleStartAnalysis}
        >
          Start Analysis
        </NeonButton>
      </div>
    </div>
  )
}
