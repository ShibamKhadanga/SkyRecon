import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Settings, Users, Tag, Sliders, Shield, Plus, Pencil, 
  Trash2, X, Save, Database, Cpu, Eye
} from 'lucide-react'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'
import AnimatedCounter from '../components/ui/AnimatedCounter'

const mockCategories = [
  { id: 1, name: 'People', characteristics: 8, color: '#06b6d4', active: true },
  { id: 2, name: 'Vehicles', characteristics: 13, color: '#22c55e', active: true },
  { id: 3, name: 'Plants & Trees', characteristics: 6, color: '#84cc16', active: true },
  { id: 4, name: 'Buildings', characteristics: 4, color: '#a855f7', active: true },
  { id: 5, name: 'Roads & Potholes', characteristics: 5, color: '#f97316', active: true },
  { id: 6, name: 'Water Bodies', characteristics: 3, color: '#3b82f6', active: true },
  { id: 7, name: 'Electric Poles', characteristics: 3, color: '#eab308', active: false },
  { id: 8, name: 'Fire & Smoke', characteristics: 2, color: '#ef4444', active: true },
  { id: 9, name: 'Solar Panels', characteristics: 2, color: '#f59e0b', active: true },
  { id: 10, name: 'Construction', characteristics: 4, color: '#ef4444', active: true },
  { id: 11, name: 'Agricultural Land', characteristics: 3, color: '#65a30d', active: true },
  { id: 12, name: 'Parking Areas', characteristics: 2, color: '#64748b', active: true },
]

const tabs = [
  { id: 'categories', label: 'Categories', icon: Tag },
  { id: 'severity', label: 'Severity Rules', icon: Shield },
  { id: 'ai', label: 'AI Settings', icon: Cpu },
  { id: 'users', label: 'Users', icon: Users },
]

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('categories')
  const [categories, setCategories] = useState(mockCategories)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')

  const toggleCategory = (id) => {
    setCategories(prev => prev.map(c => c.id === id ? { ...c, active: !c.active } : c))
  }

  const deleteCategory = (id) => {
    setCategories(prev => prev.filter(c => c.id !== id))
  }

  const addCategory = () => {
    if (!newCategoryName.trim()) return
    const newCat = {
      id: Date.now(),
      name: newCategoryName,
      characteristics: 0,
      color: `hsl(${Math.random() * 360}, 70%, 50%)`,
      active: true,
    }
    setCategories(prev => [...prev, newCat])
    setNewCategoryName('')
    setShowAddModal(false)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-1 flex items-center gap-2">
          <Settings size={24} className="text-green-400" />
          Admin Panel
        </h1>
        <p className="text-sm text-[var(--text-muted)]">Manage categories, rules, AI settings, and users</p>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Categories', value: categories.length, icon: Tag, color: '#22c55e' },
          { label: 'Total Characteristics', value: categories.reduce((a, c) => a + c.characteristics, 0), icon: Sliders, color: '#06b6d4' },
          { label: 'Active Models', value: 3, icon: Cpu, color: '#a855f7' },
          { label: 'Total Users', value: 5, icon: Users, color: '#f97316' },
        ].map((stat, i) => (
          <GlassCard key={stat.label} className="p-4" delay={i * 0.05} hover={false}>
            <div className="flex items-center gap-2 mb-2">
              <stat.icon size={14} style={{ color: stat.color }} />
              <span className="text-xs text-[var(--text-muted)]">{stat.label}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: stat.color }}>
              <AnimatedCounter value={stat.value} />
            </p>
          </GlassCard>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 rounded-xl bg-white/[0.02] border border-white/5 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
              ${activeTab === tab.id 
                ? 'text-green-400' 
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
              }
            `}
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="admin-tab"
                className="absolute inset-0 bg-green-500/10 border border-green-500/20 rounded-lg"
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-2">
              <tab.icon size={14} />
              {tab.label}
            </span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'categories' && (
          <motion.div
            key="categories"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <GlassCard hover={false}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold">Detection Categories</h3>
                <NeonButton variant="primary" size="sm" icon={Plus} onClick={() => setShowAddModal(true)}>
                  Add Category
                </NeonButton>
              </div>

              <div className="space-y-2">
                {categories.map((cat, i) => (
                  <motion.div
                    key={cat.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/[0.02] transition-colors"
                  >
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: cat.color }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{cat.name}</p>
                      <p className="text-[0.65rem] text-[var(--text-muted)]">{cat.characteristics} characteristics</p>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <span className={`text-xs ${cat.active ? 'text-green-400' : 'text-[var(--text-muted)]'}`}>
                        {cat.active ? 'Active' : 'Inactive'}
                      </span>
                      <div
                        onClick={(e) => { e.preventDefault(); toggleCategory(cat.id) }}
                        className={`
                          w-9 h-5 rounded-full relative cursor-pointer transition-colors
                          ${cat.active ? 'bg-green-500' : 'bg-white/10'}
                        `}
                      >
                        <motion.div
                          className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow"
                          animate={{ left: cat.active ? 18 : 2 }}
                          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                        />
                      </div>
                    </label>
                    <NeonButton variant="ghost" size="sm"><Pencil size={12} /></NeonButton>
                    <NeonButton variant="ghost" size="sm" onClick={() => deleteCategory(cat.id)}>
                      <Trash2 size={12} className="text-red-400" />
                    </NeonButton>
                  </motion.div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {activeTab === 'severity' && (
          <motion.div key="severity" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard hover={false}>
              <h3 className="text-sm font-semibold mb-4">Severity Level Configuration</h3>
              <div className="space-y-3">
                {[
                  { level: 1, label: 'Minor', color: '#22c55e', desc: 'Low impact, routine monitoring' },
                  { level: 2, label: 'Low Urgency', color: '#84cc16', desc: 'Needs attention within 24 hours' },
                  { level: 3, label: 'Moderate', color: '#eab308', desc: 'Significant damage, action needed within hours' },
                  { level: 4, label: 'High Danger', color: '#f97316', desc: 'Severe situation, immediate response required' },
                  { level: 5, label: 'Critical Emergency', color: '#ef4444', desc: 'Life-threatening, evacuate & deploy resources' },
                ].map((sev) => (
                  <div key={sev.level} className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.01] border border-white/5">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold"
                      style={{ background: `${sev.color}15`, color: sev.color, border: `1px solid ${sev.color}30` }}
                    >
                      {sev.level}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold" style={{ color: sev.color }}>{sev.label}</p>
                      <p className="text-xs text-[var(--text-muted)]">{sev.desc}</p>
                    </div>
                    <NeonButton variant="ghost" size="sm"><Pencil size={12} /></NeonButton>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {activeTab === 'ai' && (
          <motion.div key="ai" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard hover={false}>
              <h3 className="text-sm font-semibold mb-4">AI Model Configuration</h3>
              <div className="space-y-3">
                {[
                  { name: 'YOLOv8', version: 'v8.2.0', status: 'online', desc: 'Standard object detection', color: '#22c55e' },
                  { name: 'YOLO-World', version: 'v1.0', status: 'online', desc: 'Open vocabulary detection', color: '#06b6d4' },
                  { name: 'SAM', version: 'v2.0', status: 'standby', desc: 'Segment Anything Model', color: '#a855f7' },
                ].map((model) => (
                  <div key={model.name} className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.01] border border-white/5">
                    <div 
                      className="p-2.5 rounded-xl"
                      style={{ background: `${model.color}10`, border: `1px solid ${model.color}20` }}
                    >
                      <Cpu size={18} style={{ color: model.color }} />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold">{model.name} <span className="text-xs text-[var(--text-muted)] font-mono">{model.version}</span></p>
                      <p className="text-xs text-[var(--text-muted)]">{model.desc}</p>
                    </div>
                    <span className={`text-xs font-mono px-2 py-1 rounded-lg ${
                      model.status === 'online' ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
                    }`}>
                      ● {model.status}
                    </span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {activeTab === 'users' && (
          <motion.div key="users" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard hover={false}>
              <h3 className="text-sm font-semibold mb-4">User Management</h3>
              <div className="space-y-2">
                {[
                  { name: 'Admin User', email: 'admin@skyrecon.ai', role: 'Admin', status: 'active' },
                  { name: 'Drone Operator', email: 'operator@skyrecon.ai', role: 'Operator', status: 'active' },
                  { name: 'Analyst', email: 'analyst@skyrecon.ai', role: 'Analyst', status: 'active' },
                  { name: 'Viewer', email: 'viewer@skyrecon.ai', role: 'Viewer', status: 'inactive' },
                ].map((user) => (
                  <div key={user.email} className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/[0.02] transition-colors">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-green-500/20 to-cyan-500/10 flex items-center justify-center text-sm font-bold text-green-400">
                      {user.name.charAt(0)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{user.name}</p>
                      <p className="text-xs text-[var(--text-muted)]">{user.email}</p>
                    </div>
                    <span className="text-xs px-2 py-1 rounded-lg bg-white/5 text-[var(--text-secondary)]">{user.role}</span>
                    <span className={`text-xs ${user.status === 'active' ? 'text-green-400' : 'text-[var(--text-muted)]'}`}>
                      ● {user.status}
                    </span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add Category Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setShowAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-card p-6 w-full max-w-md"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Add Category</h3>
                <button onClick={() => setShowAddModal(false)} className="p-1.5 rounded-lg hover:bg-white/5">
                  <X size={16} />
                </button>
              </div>
              <input
                type="text"
                placeholder="Category name..."
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                className="glass-input w-full mb-4"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && addCategory()}
              />
              <div className="flex justify-end gap-2">
                <NeonButton variant="secondary" onClick={() => setShowAddModal(false)}>Cancel</NeonButton>
                <NeonButton variant="primary" icon={Save} onClick={addCategory}>Save</NeonButton>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
