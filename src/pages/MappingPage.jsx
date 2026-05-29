import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Upload, ArrowRight, Film, Satellite, Play, Cpu, 
  BarChart3, Plus, ChevronRight, FileDown, Trees, Info, ShieldAlert,
  HelpCircle, Eye, Globe, Sliders, ToggleLeft, ToggleRight, Trash2, MapPin,
  CheckCircle, XCircle
} from 'lucide-react'
import FileDropzone from '../components/ui/FileDropzone'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'

// Dropdown configuration options - ALL 25 Predefined Categories from complete Master Prompt
const categoriesConfig = {
  vehicles: {
    label: 'Vehicles',
    characteristics: {
      type: {
        label: 'Vehicle Type',
        options: ['All', 'Light Vehicle (Sedan/SUV)', 'Heavy Vehicle (Truck/Bus)', '2-Wheeler', '3-Wheeler', '4-Wheeler', '6-Wheeler', 'Bike', 'Scooty', 'Car', 'Bus', 'Truck', 'Ambulance', 'Police Vehicle']
      },
      color: {
        label: 'Vehicle Color',
        options: ['All', 'White', 'Black', 'Grey', 'Red', 'Blue', 'Yellow', 'Silver']
      },
      status: {
        label: 'Movement State',
        options: ['All', 'Moving', 'Stationary']
      },
      damaged: {
        label: 'Structural Damage',
        options: ['All', 'Damaged', 'Undamaged']
      }
    }
  },
  people: {
    label: 'People',
    characteristics: {
      gender: {
        label: 'Gender / Age',
        options: ['All', 'Male', 'Female', 'Child', 'Elderly', 'Worker']
      },
      clothingColor: {
        label: 'Clothing Color',
        options: ['All', 'Black', 'White', 'Blue', 'Red', 'Green', 'Yellow', 'Grey']
      },
      safety: {
        label: 'Safety Equipment',
        options: ['All', 'Helmet Detected', 'Safety Jacket Detected', 'Both Detected', 'No Equipment']
      },
      activity: {
        label: 'Activity State',
        options: ['All', 'Standing', 'Sitting', 'Lying']
      },
      density: {
        label: 'Crowd Density',
        options: ['All', 'Low Density', 'Medium Density', 'High Crowd Alert']
      }
    }
  },
  plants: {
    label: 'Plants',
    characteristics: {
      type: {
        label: 'Plant Type',
        options: ['All', 'Potted plants', 'Small plants', 'Medium plants', 'Dense vegetation']
      },
      emptySoil: {
        label: 'Empty Soil Detection',
        options: ['All', 'Empty soil detected', 'Fully covered']
      },
      areaEstimate: {
        label: 'Plantation Area Size',
        options: ['All', 'Small plot (<50m²)', 'Medium field (50m²-500m²)', 'Large estate (>500m²)']
      }
    }
  },
  trees: {
    label: 'Trees',
    characteristics: {
      type: {
        label: 'Tree Size/State',
        options: ['All', 'Large trees', 'Dry trees', 'Dense forest canopy']
      },
      health: {
        label: 'Tree Health Index',
        options: ['All', 'Healthy Green', 'Diseased/Dry', 'Deactivated canopy']
      }
    }
  },
  poles: {
    label: 'Electric Poles',
    characteristics: {
      type: {
        label: 'Material & Class',
        options: ['All', 'Wooden Utility Pole', 'Metal Utility Pole', 'Reinforced Concrete Pole']
      },
      danger: {
        label: 'Threat State',
        options: ['All', 'Stable Vertical', 'Listing (Leaning >15°)', 'Severely Damaged / Snapped']
      }
    }
  },
  trafficlights: {
    label: 'Traffic Lights',
    characteristics: {
      state: {
        label: 'Active State',
        options: ['All', 'Active Operating', 'Inactive/Blank']
      },
      signalColor: {
        label: 'Active Signal Color',
        options: ['All', 'Red Signal', 'Yellow Signal', 'Green Signal']
      }
    }
  },
  roads: {
    label: 'Roads',
    characteristics: {
      type: {
        label: 'Surface Material',
        options: ['All', 'Asphalt Paved', 'Concrete Paved', 'Unpaved Dirt Road']
      },
      state: {
        label: 'Condition State',
        options: ['All', 'Excellent', 'Damaged surface', 'Severe blockages']
      }
    }
  },
  potholes: {
    label: 'Road Potholes',
    characteristics: {
      severity: {
        label: 'Depth Severity',
        options: ['All', 'Minor Crack', 'Moderate Pothole', 'Severe Pothole Crater']
      },
      moisture: {
        label: 'Water Logging',
        options: ['All', 'Dry Pothole', 'Water-filled Pothole']
      }
    }
  },
  waterbodies: {
    label: 'Water Bodies',
    characteristics: {
      type: {
        label: 'Water Accumulation',
        options: ['All', 'Puddle/Water Logging', 'Pond', 'Lake', 'Canal/Drainage']
      },
      spread: {
        label: 'Spread Area',
        options: ['All', 'Minor localized', 'Significant spread', 'Widespread overflow']
      }
    }
  },
  buildings: {
    label: 'Buildings',
    characteristics: {
      type: {
        label: 'Use Class',
        options: ['All', 'Residential Block', 'Commercial Block', 'Industrial Complex']
      },
      state: {
        label: 'Damage State',
        options: ['All', 'Undamaged Structure', 'Cracked Walls', 'Structural Collapse']
      }
    }
  },
  houses: {
    label: 'Houses',
    characteristics: {
      type: {
        label: 'Dwelling Type',
        options: ['All', 'Single Family Villa', 'Multi-family Apartment']
      },
      roof: {
        label: 'Roof Integrity',
        options: ['All', 'Intact Roof', 'Damaged roof', 'Tin roof collapsed']
      }
    }
  },
  parking: {
    label: 'Parking Areas',
    characteristics: {
      type: {
        label: 'Parking Structure',
        options: ['All', 'Open Surface Lot', 'Covered Parking Structure']
      },
      utilization: {
        label: 'Occupancy Rate',
        options: ['All', 'Empty slots (<10%)', 'Moderate (10%-70%)', 'Full slots (>70%)']
      }
    }
  },
  garbage: {
    label: 'Garbage Areas',
    characteristics: {
      state: {
        label: 'Overflow Severity',
        options: ['All', 'Under control', 'Overflowing Trash']
      },
      composition: {
        label: 'Waste Material',
        options: ['All', 'Organic waste', 'Recyclable materials', 'Hazardous debris']
      }
    }
  },
  construction: {
    label: 'Construction Zones',
    characteristics: {
      stage: {
        label: 'Work Phase',
        options: ['All', 'Excavation phase', 'Structural framing', 'Finishing work']
      },
      status: {
        label: 'Operational State',
        options: ['All', 'Active working', 'Inactive/Abandoned']
      }
    }
  },
  agriculture: {
    label: 'Agricultural Land',
    characteristics: {
      status: {
        label: 'Crop Cycle State',
        options: ['All', 'Planted/Green Crop fields', 'Fallow/Bare land', 'Harvested state']
      }
    }
  },
  animals: {
    label: 'Animals',
    characteristics: {
      type: {
        label: 'Classification',
        options: ['All', 'Livestock (Cows/Goats)', 'Wild animals', 'Stray dogs/cats']
      }
    }
  },
  solarpanels: {
    label: 'Solar Panels',
    characteristics: {
      type: {
        label: 'Mounting Style',
        options: ['All', 'Rooftop Mount', 'Ground Mount Grid']
      },
      state: {
        label: 'Panel Condition',
        options: ['All', 'Clean & Active', 'Dust covered', 'Damaged Panel']
      }
    }
  },
  bridges: {
    label: 'Bridges',
    characteristics: {
      type: {
        label: 'Engineering Style',
        options: ['All', 'Beam Bridge', 'Arch Bridge', 'Suspension Bridge']
      },
      integrity: {
        label: 'Structural Soundness',
        options: ['All', 'Intact Structure', 'Cracked Piers', 'Severely Damaged']
      }
    }
  },
  railway: {
    label: 'Railway Tracks',
    characteristics: {
      status: {
        label: 'Line Type',
        options: ['All', 'Active Main line', 'Sidings/Station Tracks']
      },
      obstruction: {
        label: 'Obstructions',
        options: ['All', 'Clear Track', 'Obstruction detected']
      }
    }
  },
  fire: {
    label: 'Fire & Smoke',
    characteristics: {
      intensity: {
        label: 'Combustion Level',
        options: ['All', 'Light smoke', 'Dense smoke', 'Active open fire', 'Severe wildfire']
      }
    }
  },
  flood: {
    label: 'Flood Water',
    characteristics: {
      level: {
        label: 'Water Depth Class',
        options: ['All', 'Minor puddle', 'Moderate overflow', 'Severe deep flood']
      },
      hazard: {
        label: 'Evacuation Urgency',
        options: ['All', 'Normal vigilance', 'Emergency evacuation required']
      }
    }
  },
  shops: {
    label: 'Shops',
    characteristics: {
      state: {
        label: 'Operational State',
        options: ['All', 'Open for business', 'Closed', 'Damaged facade']
      }
    }
  },
  warehouses: {
    label: 'Warehouses',
    characteristics: {
      state: {
        label: 'Status & Damage',
        options: ['All', 'Active facility', 'Inactive facility', 'Damaged roof']
      }
    }
  },
  pipelines: {
    label: 'Pipelines',
    characteristics: {
      type: {
        label: 'Layout Class',
        options: ['All', 'Above ground pipeline', 'Below ground pipeline']
      },
      safety: {
        label: 'Integrity Check',
        options: ['All', 'Secure/Intact', 'Leakage suspected']
      }
    }
  },
  streetlights: {
    label: 'Street Lights',
    characteristics: {
      state: {
        label: 'Lighting Operational',
        options: ['All', 'Active glowing', 'Inactive/Dark', 'Physically damaged']
      }
    }
  }
}

export default function MappingPage() {
  const [file, setFile] = useState(null)
  const [detectionMode, setDetectionMode] = useState('standard') // 'standard' or 'custom'
  const [selectedCategory, setSelectedCategory] = useState('vehicles')
  
  // Dynamic characteristics filter state
  const [characteristics, setCharacteristics] = useState({
    type: 'All',
    color: 'All',
    status: 'All',
    damaged: 'All',
    gender: 'All',
    clothingColor: 'All',
    safety: 'All',
    activity: 'All',
    density: 'All',
    emptySoil: 'All',
    areaEstimate: 'All',
    health: 'All',
    danger: 'All',
    state: 'All',
    signalColor: 'All',
    severity: 'All',
    moisture: 'All',
    spread: 'All',
    roof: 'All',
    utilization: 'All',
    composition: 'All',
    stage: 'All',
    intensity: 'All',
    level: 'All',
    hazard: 'All',
    integrity: 'All',
    obstruction: 'All',
    safetyCheck: 'All'
  })

  // Custom AI / Open Vocabulary options
  const [customPrompt, setCustomPrompt] = useState('')
  const [naturalLanguageQuery, setNaturalLanguageQuery] = useState('')
  const [activeAIModels, setActiveAIModels] = useState({
    yoloWorld: true,
    groundingDino: false,
    owlVit: true,
    sam: false
  })
  
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [terminalLogs, setTerminalLogs] = useState([])
  const [showReport, setShowReport] = useState(false)
  const [analysisId, setAnalysisId] = useState(null)
  const [realResults, setRealResults] = useState(null)
  const [apiError, setApiError] = useState(null)
  const pollRef = useRef(null)

  // Before/After comparison slider percentage
  const [sliderPosition, setSliderPosition] = useState(50)
  const sliderRef = useRef(null)

  // Autofill metadata
  const [metadata, setMetadata] = useState({
    projectName: 'NIT Rourkela Campus Survey',
    location: '22.2531°N, 84.9011°E',
    droneModel: 'DJI Mavic 3 Pro',
    description: 'Aerial monitoring of campus green cover, infrastructure & roadways.',
  })

  // Poll backend for real analysis status
  const startPolling = (aid) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/analysis/${aid}/status`)
        const data = await res.json()
        if (data.status === 'processing') {
          setAnalysisProgress(prev => Math.min(prev + 3, 90))
          setTerminalLogs(prev => [...prev, `[AI] ${data.total_objects} objects detected so far...`])
        } else if (data.status === 'completed') {
          clearInterval(pollRef.current)
          setAnalysisProgress(100)
          setTerminalLogs(prev => [...prev,
            `[SYSTEM] Analysis complete. ${data.total_objects} detections in ${data.processing_time?.toFixed(1)}s.`
          ])
          const sumRes = await fetch(`/api/v1/analysis/${aid}/summary`)
          const summary = await sumRes.json()
          setRealResults(summary)
          setAnalyzing(false)
          setShowReport(true)
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current)
          setApiError('Analysis failed on the server. Check backend logs.')
          setAnalyzing(false)
          setTerminalLogs(prev => [...prev, '[ERROR] Analysis pipeline failed.'])
        }
      } catch (e) {
        setTerminalLogs(prev => [...prev, `[WARN] Polling error: ${e.message}`])
      }
    }, 3000)
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const handleStartAnalysis = async () => {
    if (!file) return
    setAnalyzing(true)
    setShowReport(false)
    setRealResults(null)
    setApiError(null)
    setAnalysisProgress(5)
    setTerminalLogs([
      '[SYSTEM] Uploading drone footage to SkyRecon AI Engine...',
      `[SYSTEM] Category: ${categoriesConfig[selectedCategory]?.label} | Mode: ${detectionMode.toUpperCase()}`,
    ])
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('project_name', metadata.projectName)
      formData.append('location', metadata.location)
      formData.append('drone_model', metadata.droneModel)
      formData.append('description', metadata.description)
      formData.append('analysis_type', 'mapping')
      formData.append('detection_mode', detectionMode)
      formData.append('selected_category', categoriesConfig[selectedCategory]?.label || selectedCategory)
      formData.append('characteristics', JSON.stringify(characteristics))
      formData.append('custom_query', customPrompt)

      const res = await fetch('/api/v1/analysis/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
      const data = await res.json()
      setAnalysisId(data.id)
      setAnalysisProgress(15)
      setTerminalLogs(prev => [
        ...prev,
        `[SYSTEM] Job created (ID: ${data.id}). YOLOv8 pipeline starting...`,
        '[YOLOv8] Loading model weights, fusing Conv+BN layers...',
        '[AI] Extracting frames at 2fps for inference...',
      ])
      startPolling(data.id)
    } catch (e) {
      setApiError(e.message)
      setAnalyzing(false)
      setTerminalLogs(prev => [...prev, `[ERROR] ${e.message}`])
    }
  }

  const handleExportReal = async (fmt) => {
    if (!analysisId) return
    try {
      const res = await fetch(
        `/api/v1/analysis/${analysisId}/report?report_type=mapping&fmt=${fmt}`,
        { method: 'POST' }
      )
      const data = await res.json()
      const rid = data.report_id
      const poll = setInterval(async () => {
        const sr = await fetch(`/api/v1/analysis/report/${rid}/status`)
        const sd = await sr.json()
        if (sd.status === 'ready') {
          clearInterval(poll)
          window.open(`/api/v1/analysis/report/${rid}/download`, '_blank')
        }
      }, 2000)
    } catch (e) {
      alert(`Report generation failed: ${e.message}`)
    }
  }

  // Handle slide movement for Before/After preview
  const handleSliderMove = (clientX) => {
    if (!sliderRef.current) return
    const rect = sliderRef.current.getBoundingClientRect()
    const x = clientX - rect.left
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
    setSliderPosition(percentage)
  }

  const handleTouchMove = (e) => {
    if (!e.touches[0]) return
    handleSliderMove(e.touches[0].clientX)
  }

  const handleMouseMove = (e) => {
    if (e.buttons !== 1) return // only drag on mouse click
    handleSliderMove(e.clientX)
  }

  // GPS Fetching with proper state
  const handleGPSFetch = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setMetadata({
            ...metadata,
            location: `${pos.coords.latitude.toFixed(4)}°N, ${pos.coords.longitude.toFixed(4)}°E`
          })
        },
        () => {
          setMetadata({
            ...metadata,
            location: '22.2531°N, 84.9011°E'
          })
        }
      )
    }
  }

  // Report Export
  const handleExport = (format) => {
    const reportText = `SKYRECON MAPPING & LAND ASSESSMENT REPORT
===================================================
Project Name: ${metadata.projectName}
Location: ${metadata.location}
Drone Model: ${metadata.droneModel}
Description: ${metadata.description}
---------------------------------------------------
AI PIPELINE CONFIGURATION:
Detection Mode: ${detectionMode.toUpperCase()}
${detectionMode === 'standard' 
    ? `Target Category: ${categoriesConfig[selectedCategory].label}
Active Characteristics: ${JSON.stringify(characteristics)}`
    : `Custom Target Query: ${customPrompt || 'N/A'}
Natural Language Command: ${naturalLanguageQuery || 'N/A'}
Active Models: ${Object.entries(activeAIModels).filter(([_, v]) => v).map(([k]) => k).join(', ')}`
}
---------------------------------------------------
INTELLIGENT INSIGHTS SUMMARY:
Total Matches Found: ${detectionMode === 'standard' ? (selectedCategory === 'vehicles' ? 142 : selectedCategory === 'people' ? 84 : 450) : 194}
Vegetation/Area Density: ${selectedCategory === 'plants' || selectedCategory === 'trees' ? '28.4% (3,420 sq. meters)' : '14.5% (1,740 sq. meters)'}
Remaining Land Capacity: ${selectedCategory === 'plants' || selectedCategory === 'trees' ? '32.1% open soil remaining' : '85.5% free area'}
===================================================
Report generated by SkyRecon AI Drone Intelligence Software.`

    const blob = new Blob([reportText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `SkyRecon_Report_${metadata.projectName.replace(/\s+/g, '_')}.${format === 'docx' ? 'doc' : 'pdf'}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="w-full max-w-none space-y-6 px-1">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-1">Mapping & Land Survey Workspace</h1>
        <p className="text-sm text-[var(--text-muted)]">
          De-congested, fully adaptive, enterprise-grade AI Drone reconnaissance console
        </p>
      </div>

      {/* Main Grid: ADAPTIVE Breakpoints – Splits on xl (1280px), stacks vertically on lg/md (preventing congestion) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: Upload, Video Player, and Before/After Slider (Spans 7 columns on wide screens) */}
        <div className="xl:col-span-7 space-y-6 w-full">
          
          {/* File Upload Zone */}
          <FileDropzone onFileSelect={setFile} />

          {/* Video / Comparison Container */}
          {file && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 w-full">
              <GlassCard hover={false} className="p-4 border-white/5">
                <div className="flex items-center justify-between mb-3 border-b border-white/5 pb-2">
                  <span className="text-xs font-semibold flex items-center gap-1.5 text-green-400 font-mono">
                    <Film size={14} /> LIVE IMAGE & TELEMETRY SCOPE
                  </span>
                  <div className="flex items-center gap-1.5 bg-black/60 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-400">
                    GPS: {metadata.location}
                  </div>
                </div>

                <div className="rounded-xl overflow-hidden bg-black/40 aspect-video flex items-center justify-center relative">
                  <video src={URL.createObjectURL(file)} controls className="w-full h-full object-contain" />
                  <div className="absolute top-2 left-2 bg-black/80 px-2 py-1 rounded text-[10px] font-mono text-green-400 border border-green-500/20">
                    FEED RESOLVED • 60 FPS
                  </div>
                </div>
              </GlassCard>

              {/* Before vs After Comparison Slider (Master Prompt Section 23) */}
              <GlassCard hover={false} className="p-5 border-white/5">
                <div className="mb-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2 text-cyan-400 font-mono tracking-wider">
                    <Globe size={14} />
                    INTERACTIVE BEFORE VS AFTER COMPARISON
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Drag the vertical glowing handle to compare plain terrain (left) against active AI overlays (right)
                  </p>
                </div>

                <div 
                  ref={sliderRef}
                  onMouseMove={handleMouseMove}
                  onTouchMove={handleTouchMove}
                  className="relative aspect-video w-full rounded-xl overflow-hidden border border-white/10 cursor-ew-resize select-none shadow-[0_0_20px_rgba(0,0,0,0.5)]"
                >
                  {/* Left Frame: Before (Plain/Satellite) */}
                  <div className="absolute inset-0 bg-gradient-to-br from-green-950/20 to-emerald-950/40 flex items-center justify-center">
                    <div className="absolute inset-0 bg-grid opacity-25" />
                    <div className="text-center p-4 bg-black/70 rounded-xl border border-white/10">
                      <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase block tracking-widest">Before (Pre-Event)</span>
                      <p className="text-sm font-bold text-white mt-1">Plain Aerial Terrain View</p>
                    </div>
                  </div>

                  {/* Right Frame: After (AI Detection Heatmaps/Annotations) */}
                  <div 
                    className="absolute inset-y-0 right-0 overflow-hidden bg-gradient-to-br from-cyan-900/30 to-purple-950/40 flex items-center justify-center animate-shimmer"
                    style={{ left: `${sliderPosition}%` }}
                  >
                    <div 
                      className="absolute inset-y-0 left-0 bg-gradient-to-br from-cyan-900/30 to-purple-950/40 flex items-center justify-center"
                      style={{ 
                        width: `${sliderRef.current ? sliderRef.current.getBoundingClientRect().width : 800}px`, 
                        marginLeft: `-${sliderRef.current ? (sliderRef.current.getBoundingClientRect().width * sliderPosition) / 100 : 400}px` 
                      }}
                    >
                      <div className="absolute inset-0 bg-grid opacity-30 text-green-400" />
                      
                      {/* Bounding box representations */}
                      <div className="absolute top-1/4 left-1/4 w-32 h-20 border-2 border-green-500 rounded flex flex-col justify-between p-1 bg-green-500/15 shadow-[0_0_15px_rgba(34,197,94,0.2)]">
                        <span className="text-[8px] font-mono text-green-400 bg-black/90 px-1 rounded w-fit">VEHICLE: 98%</span>
                        <span className="text-[8px] font-mono text-[var(--text-muted)] self-end">ID: AN-01</span>
                      </div>
                      
                      <div className="absolute bottom-1/3 right-1/4 w-40 h-24 border-2 border-cyan-500 rounded flex flex-col justify-between p-1 bg-cyan-500/15 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
                        <span className="text-[8px] font-mono text-cyan-400 bg-black/90 px-1 rounded w-fit">VEGETATION COVER</span>
                        <span className="text-[8px] font-mono text-[var(--text-muted)] self-end">CANOPY DENSITY: 28.4%</span>
                      </div>

                      <div className="text-center p-4 bg-black/75 rounded-xl border border-cyan-500/30 shadow-lg">
                        <span className="text-[10px] font-mono text-cyan-400 uppercase block tracking-widest">After (AI Analysis)</span>
                        <p className="text-sm font-bold text-white mt-1">Real-Time Detections Locked</p>
                      </div>
                    </div>
                  </div>

                  {/* Vertical Handle Divider */}
                  <div 
                    className="absolute inset-y-0 w-0.5 bg-green-400 shadow-[0_0_10px_#22c55e] cursor-ew-resize flex items-center justify-center"
                    style={{ left: `${sliderPosition}%` }}
                  >
                    <div className="w-5 h-9 rounded-lg bg-green-400 text-black font-black text-xs flex items-center justify-center shadow-[0_0_15px_rgba(34,197,94,0.5)] border border-green-300">
                      ↔
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          )}
        </div>

        {/* RIGHT COLUMN: AI Command Control Panel (Spans 5 columns on wide screens) */}
        <div className="xl:col-span-5 space-y-6 w-full">
          <GlassCard hover={false} className="border-cyan-500/10 p-5 space-y-6">
            
            {/* Target Selection Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h3 className="text-sm font-bold flex items-center gap-2 text-white font-mono tracking-wider">
                <Satellite size={16} className="text-cyan-400 animate-pulse" />
                AI RECON CONTROLS
              </h3>
              <button 
                type="button" 
                onClick={() => {
                  setMetadata({
                    projectName: 'NIT Rourkela Campus Survey',
                    location: '22.2531°N, 84.9011°E',
                    droneModel: 'DJI Mavic 3 Pro',
                    description: 'Aerial monitoring of campus green cover, infrastructure & roadways.',
                  })
                }}
                className="text-[10px] text-green-400 hover:text-green-300 hover:underline font-mono cursor-pointer"
              >
                Autofill Campus Metadata
              </button>
            </div>

            {/* GROUP 1: Project Info Sub-card (Metadata Grouping) */}
            <div className="bg-black/30 border border-white/5 p-4 rounded-xl space-y-3">
              <div className="text-[10px] font-mono text-cyan-400 tracking-wider uppercase border-b border-white/5 pb-1 mb-2">
                PROJECT TARGET METADATA
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-[var(--text-secondary)] mb-1 block font-mono">PROJECT NAME</label>
                  <input 
                    type="text" 
                    className="glass-input w-full py-2 text-xs font-semibold" 
                    value={metadata.projectName}
                    onChange={(e) => setMetadata({...metadata, projectName: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-[10px] text-[var(--text-secondary)] mb-1 block font-mono">LOCATION COORDS</label>
                  {/* Nesting GPS button directly inside Location input as absolute overlay - SOLVES CLIPPING */}
                  <div className="relative flex items-center">
                    <input 
                      type="text" 
                      className="glass-input w-full pr-14 py-2 text-xs font-semibold font-mono" 
                      value={metadata.location}
                      onChange={(e) => setMetadata({...metadata, location: e.target.value})}
                    />
                    <button
                      type="button"
                      onClick={handleGPSFetch}
                      className="absolute right-2 px-2 py-1 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/30 text-[9px] font-mono font-bold transition-all cursor-pointer flex items-center gap-1 active:scale-95"
                      title="Fetch current coordinates from GPS API"
                    >
                      <MapPin size={10} />
                      GPS
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* GROUP 2: PIPELINE DETECTOR MODE SELECTOR (Segmented Premium Button Controls) */}
            <div className="bg-black/50 border border-white/10 p-3 rounded-2xl space-y-3 shadow-inner">
              <div className="flex items-center justify-between px-1">
                <span className="text-[10px] font-mono text-cyan-400 tracking-wider">PIPELINE ANALYSIS METHOD</span>
                <span className="text-[9px] font-mono text-green-400/80 bg-green-500/5 border border-green-500/10 px-1 rounded">HYBRID PIPELINE ACTIVE</span>
              </div>
              <div className="grid grid-cols-2 gap-2 bg-black/40 p-1.5 rounded-xl border border-white/5">
                <button
                  type="button"
                  onClick={() => setDetectionMode('standard')}
                  className={`py-2 px-3 rounded-lg text-xs font-bold tracking-widest font-mono transition-all duration-300 cursor-pointer ${
                    detectionMode === 'standard' 
                      ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-black shadow-[0_0_15px_rgba(34,197,94,0.3)] scale-[1.01]' 
                      : 'text-[var(--text-muted)] hover:text-white hover:bg-white/5'
                  }`}
                >
                  STANDARD PRESETS
                </button>
                <button
                  type="button"
                  onClick={() => setDetectionMode('custom')}
                  className={`py-2 px-3 rounded-lg text-xs font-bold tracking-widest font-mono transition-all duration-300 cursor-pointer ${
                    detectionMode === 'custom' 
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-black shadow-[0_0_15px_rgba(6,182,212,0.3)] scale-[1.01]' 
                      : 'text-[var(--text-muted)] hover:text-white hover:bg-white/5'
                  }`}
                >
                  CUSTOM AI VOCAB
                </button>
              </div>
            </div>

            {/* GROUP 3: PARAMETERS SELECTION SUB-CARD */}
            <div className="bg-black/30 border border-white/5 p-4 rounded-xl space-y-4">
              
              {/* DETECT MODE TAB 1: STANDARD PREDEFINED CATEGORIES (25 ITEMS) */}
              {detectionMode === 'standard' && (
                <div className="space-y-4">
                  {/* Category select block */}
                  <div>
                    <div className="border-b border-green-500/20 pb-1 mb-3 flex items-center justify-between">
                      <h4 className="text-xs font-bold text-green-400 font-mono tracking-widest uppercase flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                        1. SELECT TARGET CATEGORY
                      </h4>
                      <span className="text-[9px] text-[var(--text-muted)] font-mono">25 PRESETS</span>
                    </div>
                    <select 
                      className="glass-input w-full bg-[var(--bg-secondary)] border-green-500/20 focus:border-green-400 py-2.5 font-semibold text-xs text-white" 
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                    >
                      {Object.entries(categoriesConfig).map(([key, cfg]) => (
                        <option key={key} value={key} className="bg-[var(--bg-primary)]">
                          {cfg.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Characteristics Filters block */}
                  <div className="pt-2">
                    <div className="border-b border-green-500/20 pb-1 mb-3 flex items-center justify-between">
                      <h4 className="text-xs font-bold text-green-400 font-mono tracking-widest uppercase flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                        2. SET DYNAMIC FILTERS
                      </h4>
                      <span className="text-[9px] text-green-400/80 bg-green-500/10 px-1.5 py-0.5 rounded font-mono border border-green-500/10">ALL INCLUDED</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {Object.entries(categoriesConfig[selectedCategory].characteristics).map(([key, charCfg]) => (
                        <div key={key}>
                          <label className="text-[9px] text-[var(--text-secondary)] mb-1 block font-mono">{charCfg.label.toUpperCase()}</label>
                          <select 
                            className="glass-input w-full bg-[var(--bg-secondary)] py-1.5 text-xs font-medium text-white"
                            value={characteristics[key] || 'All'}
                            onChange={(e) => setCharacteristics({...characteristics, [key]: e.target.value})}
                          >
                            {charCfg.options.map(opt => (
                              <option key={opt} value={opt} className="bg-[var(--bg-primary)]">{opt}</option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* DETECT MODE TAB 2: CUSTOM AI & NLQ SYSTEM (YOLO-World, SAM, OWL-ViT) */}
              {detectionMode === 'custom' && (
                <div className="space-y-4">
                  {/* Custom Object Input (Open Vocabulary AI) */}
                  <div>
                    <div className="border-b border-cyan-500/20 pb-1 mb-3 flex items-center justify-between">
                      <h4 className="text-xs font-bold text-cyan-400 font-mono tracking-widest uppercase flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                        1. CUSTOM TARGET PROMPTS
                      </h4>
                      <span className="text-[9px] text-[var(--text-muted)] font-mono">OPEN VOCAB</span>
                    </div>
                    <input
                      type="text"
                      placeholder="e.g. traffic lights, solar panels, pipelines, school buildings"
                      className="glass-input w-full border-cyan-500/20 focus:border-cyan-400 py-2.5 text-xs text-white"
                      value={customPrompt}
                      onChange={(e) => setCustomPrompt(e.target.value)}
                    />
                    <span className="text-[9px] text-[var(--text-muted)] mt-1.5 block">
                      Our YOLO-World open-vocabulary engine dynamically resolves custom queries inside frame buffers without offline dataset training.
                    </span>
                  </div>

                  {/* Natural Language Query System */}
                  <div>
                    <div className="border-b border-cyan-500/20 pb-1 mb-3 flex items-center justify-between">
                      <h4 className="text-xs font-bold text-cyan-400 font-mono tracking-widest uppercase flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                        2. NATURAL LANGUAGE COMMAND
                      </h4>
                      <span className="text-[9px] text-[var(--text-muted)] font-mono">SEMANTIC COMMANDS</span>
                    </div>
                    <textarea
                      rows={2}
                      placeholder="e.g. Count red vehicles near warehouses, find empty parking spaces near structural cracked concrete."
                      className="glass-input w-full border-cyan-500/20 focus:border-cyan-400 resize-none py-2 text-xs text-white"
                      value={naturalLanguageQuery}
                      onChange={(e) => setNaturalLanguageQuery(e.target.value)}
                    />
                    <span className="text-[9px] text-[var(--text-muted)] mt-1 block">
                      Translates semantic inquiries to lock frames, count targets, and outline localized security hazards.
                    </span>
                  </div>

                  {/* Active AI Models check list */}
                  <div className="pt-2">
                    <div className="border-b border-cyan-500/20 pb-1 mb-3 flex items-center justify-between">
                      <h4 className="text-xs font-bold text-cyan-400 font-mono tracking-widest uppercase flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                        3. ACTIVE RECON ENGINES
                      </h4>
                      <span className="text-[9px] text-green-400 font-mono">MODEL COMPILING</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <label className="flex items-center gap-2 p-2 rounded bg-white/[0.01] border border-white/5 cursor-pointer hover:border-cyan-500/20 transition-colors">
                        <input 
                          type="checkbox" 
                          checked={activeAIModels.yoloWorld}
                          onChange={(e) => setActiveAIModels({...activeAIModels, yoloWorld: e.target.checked})}
                          className="accent-cyan-500 cursor-pointer" 
                        />
                        <span>YOLO-World (v1.0)</span>
                      </label>
                      <label className="flex items-center gap-2 p-2 rounded bg-white/[0.01] border border-white/5 cursor-pointer hover:border-cyan-500/20 transition-colors">
                        <input 
                          type="checkbox" 
                          checked={activeAIModels.groundingDino}
                          onChange={(e) => setActiveAIModels({...activeAIModels, groundingDino: e.target.checked})}
                          className="accent-cyan-500 cursor-pointer" 
                        />
                        <span>Grounding DINO</span>
                      </label>
                      <label className="flex items-center gap-2 p-2 rounded bg-white/[0.01] border border-white/5 cursor-pointer hover:border-cyan-500/20 transition-colors">
                        <input 
                          type="checkbox" 
                          checked={activeAIModels.owlVit}
                          onChange={(e) => setActiveAIModels({...activeAIModels, owlVit: e.target.checked})}
                          className="accent-cyan-500 cursor-pointer" 
                        />
                        <span>OWL-ViT</span>
                      </label>
                      <label className="flex items-center gap-2 p-2 rounded bg-white/[0.01] border border-white/5 cursor-pointer hover:border-cyan-500/20 transition-colors">
                        <input 
                          type="checkbox" 
                          checked={activeAIModels.sam}
                          onChange={(e) => setActiveAIModels({...activeAIModels, sam: e.target.checked})}
                          className="accent-cyan-500 cursor-pointer" 
                        />
                        <span>Segment (SAM v2)</span>
                      </label>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Run Analysis Button */}
            <div className="pt-2">
              <NeonButton 
                variant="primary" 
                className="w-full justify-center shadow-[0_0_20px_rgba(34,197,94,0.15)] hover:shadow-[0_0_25px_rgba(34,197,94,0.3)] transition-all py-3 font-bold uppercase tracking-widest text-xs" 
                icon={Play}
                onClick={handleStartAnalysis}
                disabled={!file || analyzing}
              >
                {analyzing ? 'Analyzing Video Stream...' : 'Execute Recon Sweep'}
              </NeonButton>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Analysis Terminal Logger (Spans full viewport width) */}
      <AnimatePresence>
        {analyzing && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
            <GlassCard hover={false} className="border-green-500/20 bg-black/60 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-green-500/10 pb-2 mb-3">
                <span className="text-green-400 font-bold flex items-center gap-2">
                  <Cpu size={14} className="animate-pulse" />
                  YOLOv8 + YOLO-WORLD HYBRID AI ENGINE
                </span>
                <span className="text-[var(--text-muted)]">{analysisProgress}%</span>
              </div>
              <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mb-3">
                <motion.div className="bg-green-400 h-full" animate={{ width: `${analysisProgress}%` }} />
              </div>
              <div className="space-y-1.5 max-h-40 overflow-y-auto text-[var(--text-secondary)]">
                {terminalLogs.map((log, i) => (
                  <div key={i} className={log.includes('SYSTEM') ? 'text-cyan-400' : log.includes('error') ? 'text-red-400' : ''}>
                    {log}
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Detailed Result Assessment Report (Spans full viewport width) */}
      <AnimatePresence>
        {showReport && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <GlassCard hover={false} className="border-green-500/20 shadow-2xl relative">
              
              {/* Top Download Actions */}
              <div className="absolute top-4 right-4 flex items-center gap-2">
                <button 
                  onClick={() => handleExportReal('docx')}
                  className="px-3 py-1.5 rounded-xl border border-white/5 hover:border-green-500/30 text-xs font-mono text-[var(--text-secondary)] hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer bg-white/[0.01]"
                >
                  <FileDown size={14} /> DOCX
                </button>
                <button 
                  onClick={() => handleExportReal('pdf')}
                  className="px-3 py-1.5 rounded-xl border border-white/5 hover:border-green-500/30 text-xs font-mono text-[var(--text-secondary)] hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer bg-white/[0.01]"
                >
                  <FileDown size={14} /> PDF
                </button>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <div className="p-2.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400">
                  <BarChart3 size={20} />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-[var(--text-muted)] tracking-wider">RUN COMPLETED — REAL AI RESULTS</span>
                  <h2 className="text-lg font-bold text-white">Land Survey Analysis Report</h2>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Detected Matches</span>
                    <h3 className="text-3xl font-bold text-white mt-1">{realResults?.total_detections ?? 0}</h3>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-4">
                    Objects detected by YOLOv8 matching [{categoriesConfig[selectedCategory]?.label || selectedCategory}] filters.
                  </p>
                </div>
                <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Area Covered</span>
                    <h3 className="text-3xl font-bold text-cyan-400 mt-1">{realResults?.coverage?.coverage_percent ?? 0}%</h3>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mt-4">
                    Approx. <span className="font-semibold text-white">{realResults?.coverage?.total_area_sqm ?? 0} m²</span> of surveyed zone.
                  </p>
                </div>
                <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Available Area</span>
                    <h3 className="text-3xl font-bold text-green-400 mt-1">
                      {realResults ? (100 - (realResults.coverage?.coverage_percent ?? 0)).toFixed(1) : 0}%
                    </h3>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mt-4">
                    {realResults?.coverage?.empty_area_sqm ?? 0} m² open area remaining.
                  </p>
                </div>
              </div>

              {realResults?.category_breakdown && Object.keys(realResults.category_breakdown).length > 0 && (
                <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {Object.entries(realResults.category_breakdown).map(([cat, count]) => (
                    <div key={cat} className="bg-white/[0.01] border border-white/5 rounded-xl p-3 text-center">
                      <p className="text-lg font-bold text-green-400">{count}</p>
                      <p className="text-[10px] text-[var(--text-muted)] font-mono mt-0.5">{cat}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-6 border-t border-white/5 pt-6 flex gap-4 items-start bg-green-500/[0.01] border-l-2 border-l-green-500 rounded-r-xl p-4">
                <Info size={20} className="text-green-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-white">AI Planning Recommendations</h4>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    Analysis detected <strong>{realResults?.total_detections ?? 0}</strong> objects across{' '}
                    <strong>{Object.keys(realResults?.category_breakdown ?? {}).length}</strong> categories.
                    Total covered area: <strong>{realResults?.coverage?.total_area_sqm ?? 0} m²</strong>{' '}
                    ({realResults?.coverage?.coverage_percent ?? 0}% of surveyed zone).
                    Available area: <strong>{realResults?.coverage?.empty_area_sqm ?? 0} m²</strong> remaining.
                    Processing time: <strong>{realResults?.processing_time?.toFixed(1) ?? '—'}s</strong>.
                  </p>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
