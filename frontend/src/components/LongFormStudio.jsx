import * as React from "react"
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Scissors, 
  Bookmark, 
  Star, 
  Type, 
  Sliders, 
  Download, 
  Folder, 
  Save, 
  ZoomIn, 
  MousePointer, 
  Hand, 
  Ruler, 
  Check, 
  Sparkles,
  RefreshCw
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"

export function LongFormStudio({
  onOpenNewProject,
  onOpenCaptionPlayground
}) {
  const [projects, setProjects] = React.useState([])
  const [currentProjectId, setCurrentProjectId] = React.useState(null)
  const [activeProject, setActiveProject] = React.useState(null)
  const [timelineSegments, setTimelineSegments] = React.useState([])
  const [selectedSegment, setSelectedSegment] = React.useState(null)
  const [inspectorTab, setInspectorTab] = React.useState("controls") // controls, chapters, export
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [currentTimecode, setCurrentTimecode] = React.useState("12:34 / 42:15")
  const [timelineZoom, setTimelineZoom] = React.useState(1)
  const [timelineTool, setTimelineTool] = React.useState("select")
  const [thresholdDb, setThresholdDb] = React.useState(-28.0)
  const [marginSec, setMarginSec] = React.useState(0.2)
  const [mincutSec, setMincutSec] = React.useState(0.2)
  const [exportProgress, setExportProgress] = React.useState({ show: false, pct: 0, stage: "" })

  const playerRef = React.useRef(null)
  const canvasRef = React.useRef(null)

  // Fetch long-form projects on mount
  const loadProjects = async () => {
    try {
      const res = await fetch('/api/long-form/projects')
      const data = await res.json()
      setProjects(data.projects || [])
      if (data.projects && data.projects.length > 0 && !currentProjectId) {
        selectProject(data.projects[0].id)
      }
    } catch (e) {
      console.error(e)
    }
  }

  React.useEffect(() => {
    loadProjects()
  }, [])

  const selectProject = async (id) => {
    setCurrentProjectId(id)
    try {
      const res = await fetch(`/api/long-form/projects/${id}`)
      const data = await res.json()
      setActiveProject(data.project)
      if (playerRef.current) {
        playerRef.current.src = `/api/long-form/projects/${id}/video`
        playerRef.current.load()
      }
      loadTimeline(id)
    } catch (e) {
      console.error(e)
    }
  }

  const loadTimeline = async (id) => {
    try {
      const res = await fetch(`/api/long-form/projects/${id}/timeline`)
      const data = await res.json()
      setTimelineSegments(data.segments || [])
    } catch (e) {
      console.error(e)
    }
  }

  // Draw multi-track timeline canvas
  React.useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const w = canvas.width = canvas.parentElement.clientWidth || 800
    const h = canvas.height = canvas.parentElement.clientHeight || 110

    const rulerH = 20
    const videoTrackH = 32
    const audioTrackH = h - rulerH - videoTrackH
    const videoTrackY = rulerH
    const audioTrackY = rulerH + videoTrackH
    const totalDuration = activeProject?.metadata?.duration || 2535

    // Background
    ctx.fillStyle = '#0B0D12'
    ctx.fillRect(0, 0, w, h)

    // Ruler
    ctx.fillStyle = '#111722'
    ctx.fillRect(0, 0, w, rulerH)
    ctx.strokeStyle = '#293244'
    ctx.beginPath()
    ctx.moveTo(0, rulerH)
    ctx.lineTo(w, rulerH)
    ctx.stroke()

    // Ruler ticks
    ctx.fillStyle = '#929BAA'
    ctx.font = '9px monospace'
    for (let i = 0; i <= 10; i++) {
      const tx = (i / 10) * w
      const tSec = (i / 10) * totalDuration
      const m = Math.floor(tSec / 60)
      const s = Math.floor(tSec % 60)
      ctx.fillText(`${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`, tx + 2, 14)
    }

    // Video Track
    ctx.fillStyle = '#141821'
    ctx.fillRect(0, videoTrackY, w, videoTrackH)
    ctx.strokeStyle = '#293244'
    ctx.beginPath()
    ctx.moveTo(0, audioTrackY)
    ctx.lineTo(w, audioTrackY)
    ctx.stroke()

    // Audio Track
    ctx.fillStyle = '#0F131A'
    ctx.fillRect(0, audioTrackY, w, audioTrackH)

    // Render segments or simulated blocks
    const segmentsToRender = timelineSegments.length > 0 ? timelineSegments : [
      { id: 1, source_start: 0, source_end: totalDuration * 0.35, action: 'KEEP' },
      { id: 2, source_start: totalDuration * 0.35, source_end: totalDuration * 0.40, action: 'CUT' },
      { id: 3, source_start: totalDuration * 0.40, source_end: totalDuration * 0.85, action: 'KEEP' },
      { id: 4, source_start: totalDuration * 0.85, source_end: totalDuration, action: 'CUT' },
    ]

    segmentsToRender.forEach((seg, idx) => {
      const sx = (seg.source_start / totalDuration) * w
      const sw = Math.max(2, ((seg.source_end - seg.source_start) / totalDuration) * w)

      if (seg.action === 'KEEP') {
        // Video
        ctx.fillStyle = '#92400e'
        ctx.fillRect(sx, videoTrackY + 2, sw, videoTrackH - 4)
        ctx.strokeStyle = '#b45309'
        ctx.strokeRect(sx, videoTrackY + 2, sw, videoTrackH - 4)

        // Audio
        ctx.fillStyle = '#0284c7'
        ctx.fillRect(sx, audioTrackY + 2, sw, audioTrackH - 4)

        // Waveform lines
        ctx.strokeStyle = '#bae6fd'
        ctx.lineWidth = 1
        ctx.beginPath()
        const midA = audioTrackY + audioTrackH / 2
        for (let x = sx; x < sx + sw; x += 4) {
          const amp = (Math.sin(x * 0.1) * 0.5 + 0.5) * (audioTrackH * 0.35)
          ctx.moveTo(x, midA - amp)
          ctx.lineTo(x, midA + amp)
        }
        ctx.stroke()
      } else {
        // Cut region
        ctx.fillStyle = '#e11d48'
        ctx.fillRect(sx, audioTrackY + 2, sw, audioTrackH - 4)
      }
    })

    // Red playhead line
    if (playerRef.current) {
      const cur = playerRef.current.currentTime || 0
      const px = (cur / totalDuration) * w
      ctx.strokeStyle = '#ef4444'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(px, 0)
      ctx.lineTo(px, h)
      ctx.stroke()
    }
  }, [timelineSegments, activeProject, timelineZoom])

  const togglePlay = () => {
    if (!playerRef.current) return
    if (playerRef.current.paused) {
      playerRef.current.play()
      setIsPlaying(true)
    } else {
      playerRef.current.pause()
      setIsPlaying(false)
    }
  }

  const triggerAnalyze = async () => {
    if (!currentProjectId) return
    try {
      await fetch(`/api/long-form/projects/${currentProjectId}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engine_mode: 'auto_editor',
          threshold_percent: 4.0,
          margin_sec: marginSec
        })
      })
      alert("Auto-Editor dead-air analysis dispatched!")
    } catch (e) {
      alert("Error: " + e.message)
    }
  }

  const triggerExport = async () => {
    if (!currentProjectId) return
    setExportProgress({ show: true, pct: 15, stage: "Rendering master export..." })
    try {
      await fetch(`/api/long-form/projects/${currentProjectId}/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_codec: 'libx264',
          output_filename: 'altered_master.mp4',
          include_transitions: true
        })
      })
    } catch (e) {
      alert("Export failed: " + e.message)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-4 space-y-4">
      {/* Long-Form Header Bar (Matching Image 2) */}
      <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm shrink-0">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎬</span>
            <h1 className="text-base font-bold text-[var(--color-text)]">Long-Form Studio</h1>
            <Badge variant="outline" className="text-[10px] font-mono font-bold border-[var(--color-line)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
              Pro NLE
            </Badge>
          </div>
          <p className="text-xs text-[var(--color-muted)]">
            Edit, enhance and create engaging long-form content with AI dead-air excision.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenNewProject}
            className="h-8 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-medium"
          >
            <Folder className="w-3.5 h-3.5 mr-1.5" />
            <span>Load Project</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={loadProjects}
            className="h-8 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-medium"
          >
            <Save className="w-3.5 h-3.5 mr-1.5" />
            <span>Save Project</span>
          </Button>
          <Button
            size="sm"
            onClick={triggerExport}
            className="h-8 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow"
          >
            <span>Export Video ↗</span>
          </Button>
        </div>
      </div>

      {/* Main 3-Column NLE Workspace Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-y-auto custom-scrollbar min-h-0">
        
        {/* LEFT COLUMN: Project Setup & Editing Tools (3 cols) */}
        <div className="lg:col-span-3 space-y-3.5 flex flex-col justify-start">
          {/* Project Setup Card */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--color-text)]">Project Setup</span>
              <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
                READY
              </span>
            </div>

            {/* Video File Snippet */}
            <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)] flex items-center gap-3">
              <div className="w-12 h-10 rounded-lg bg-black/60 flex items-center justify-center text-[var(--color-accent)] shrink-0 overflow-hidden">
                <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                  <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-[var(--color-text)] truncate">
                  {activeProject ? activeProject.title : "podcast_full.mp4"}
                </div>
                <div className="text-[10px] text-[var(--color-muted)] font-mono truncate">
                  1920x1080 • 42:15
                </div>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={onOpenNewProject}
              className="w-full h-8 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-medium"
            >
              <span>Change Video</span>
            </Button>
          </div>

          {/* Editing Tools Accordion */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-2 shadow-sm">
            <div className="text-xs font-bold text-[var(--color-text)] mb-2">Editing Tools</div>

            {[
              { id: 'trim', title: 'Trim & Cut', desc: 'Remove unwanted parts and dead-air', icon: Scissors, action: () => setInspectorTab('controls') },
              { id: 'chapters', title: 'Auto Chapters', badge: 'Beta', desc: 'Generate YouTube chapters', icon: Bookmark, action: () => setInspectorTab('chapters') },
              { id: 'highlights', title: 'AI Highlights', desc: 'Find key viral moments', icon: Star, action: triggerAnalyze },
              { id: 'captions', title: 'Add Captions', desc: 'Auto or custom burned captions', icon: Type, action: onOpenCaptionPlayground },
              { id: 'audio', title: 'Audio Enhancement', desc: 'Clean and enhance speech', icon: Sliders, action: () => setInspectorTab('controls') },
            ].map((tool) => {
              const Icon = tool.icon
              return (
                <div
                  key={tool.id}
                  onClick={tool.action}
                  className="p-2.5 rounded-xl bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] cursor-pointer transition flex items-center justify-between"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4 text-[var(--color-accent)] shrink-0" />
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-[var(--color-text)]">{tool.title}</span>
                        {tool.badge && (
                          <span className="text-[9px] font-mono px-1 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold">
                            {tool.badge}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-[var(--color-muted)]">{tool.desc}</span>
                    </div>
                  </div>
                  <span className="text-[var(--color-muted)] text-xs">›</span>
                </div>
              )
            })}
          </div>

          <Button
            size="sm"
            onClick={triggerAnalyze}
            className="w-full h-10 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            <span>Re-Analyze Dead Air (Auto-Editor)</span>
          </Button>
        </div>

        {/* CENTER COLUMN: 16:9 Widescreen Monitor (6 cols) */}
        <div className="lg:col-span-6 flex flex-col justify-between space-y-3 min-h-[460px]">
          {/* Header */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[var(--color-text)] font-mono truncate max-w-[280px]">
                {activeProject ? activeProject.title : "Preview Monitor"}
              </span>
              <span className="px-2 py-0.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-[10px] font-mono text-[var(--color-text)]">
                1080p
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2 py-0.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-[var(--color-muted)] font-medium">
                Fit 100%
              </span>
              <span className="font-mono text-[var(--color-muted)]">{currentTimecode}</span>
            </div>
          </div>

          {/* 16:9 Monitor Centerpiece */}
          <div className="flex-1 bg-black rounded-3xl border-2 border-[var(--color-line)] overflow-hidden relative shadow-2xl flex items-center justify-center min-h-[380px] max-h-[560px]">
            <video
              ref={playerRef}
              playsInline
              className="w-full h-full object-contain"
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />

            {/* Play Button Overlay */}
            <button
              onClick={togglePlay}
              className="absolute w-14 h-14 rounded-full bg-black/60 hover:bg-black/80 border border-white/20 text-white flex items-center justify-center text-xl transition shadow-xl"
            >
              {isPlaying ? "❚❚" : "▶"}
            </button>

            {/* Subtitle Dialogue Overlay */}
            <div className="absolute bottom-6 inset-x-6 pointer-events-none flex justify-center text-center">
              <div className="px-4 py-1.5 rounded-xl bg-black/60 backdrop-blur-sm border border-white/10 text-white font-semibold text-sm drop-shadow">
                <span>This is going to be amazing!</span>
              </div>
            </div>
          </div>

          {/* Transport Controls */}
          <div className="p-3 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] flex items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (playerRef.current) playerRef.current.currentTime -= 5
                }}
                className="h-8 px-2.5 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs"
              >
                ⏪ -5s
              </Button>
              <Button
                size="sm"
                onClick={togglePlay}
                className="h-8 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold"
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                <span>{isPlaying ? "Pause" : "Play"}</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (playerRef.current) playerRef.current.currentTime += 5
                }}
                className="h-8 px-2.5 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs"
              >
                +5s ⏩
              </Button>
            </div>

            <div className="flex items-center gap-3 text-xs">
              <label className="flex items-center gap-1.5 text-[var(--color-muted)] cursor-pointer hover:text-[var(--color-text)]">
                <input type="checkbox" className="accent-[var(--color-accent)] w-3.5 h-3.5 rounded" />
                <span>Skip Dead Air</span>
              </label>
              <span className="font-mono text-[var(--color-muted)] text-xs">-29:41</span>
              <Select className="h-7 w-20 text-xs border-0 bg-transparent">
                <option value="1">1.0x</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
                <option value="2">2.0x</option>
              </Select>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Inspector & Chapters (3 cols) */}
        <div className="lg:col-span-3 space-y-3.5 flex flex-col justify-start">
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-4 shadow-sm flex-1 flex flex-col">
            {/* Tab Selector */}
            <div className="flex items-center bg-[var(--color-surface)] border border-[var(--color-line)] p-1 rounded-xl">
              <button
                onClick={() => setInspectorTab('controls')}
                className={`flex-1 py-1 rounded-lg text-xs font-bold transition ${
                  inspectorTab === 'controls'
                    ? "bg-[var(--color-card)] text-[var(--color-accent)] shadow"
                    : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                Inspector
              </button>
              <button
                onClick={() => setInspectorTab('chapters')}
                className={`flex-1 py-1 rounded-lg text-xs font-semibold transition ${
                  inspectorTab === 'chapters'
                    ? "bg-[var(--color-card)] text-[var(--color-accent)] shadow"
                    : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                Chapters
              </button>
              <button
                onClick={() => setInspectorTab('export')}
                className={`flex-1 py-1 rounded-lg text-xs font-semibold transition ${
                  inspectorTab === 'export'
                    ? "bg-[var(--color-card)] text-[var(--color-accent)] shadow"
                    : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                Export
              </button>
            </div>

            {/* Inspector Tab */}
            {inspectorTab === 'controls' && (
              <div className="space-y-3.5 text-xs flex-1">
                <div>
                  <span className="text-xs font-bold text-[var(--color-text)] block mb-2">Video Settings</span>
                  <label className="text-[10px] text-[var(--color-muted)] block mb-1">Aspect Ratio</label>
                  <div className="grid grid-cols-5 gap-1 text-[10px] font-mono text-center">
                    <button className="py-1 rounded-lg bg-[var(--color-accent-soft)] border border-[var(--color-accent)] text-[var(--color-accent)] font-bold">16:9</button>
                    <button className="py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-[var(--color-muted)]">9:16</button>
                    <button className="py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-[var(--color-muted)]">1:1</button>
                    <button className="py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-[var(--color-muted)]">4:5</button>
                    <button className="py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-[var(--color-muted)]">2:3</button>
                  </div>
                </div>

                <div>
                  <label className="text-[10px] text-[var(--color-muted)] block mb-1">Resolution</label>
                  <Select className="h-8 text-xs">
                    <option>1080p (Full HD)</option>
                    <option>1440p (2K)</option>
                    <option>2160p (4K UHD)</option>
                  </Select>
                </div>

                <div>
                  <label className="text-[10px] text-[var(--color-muted)] block mb-1">Quality Profile</label>
                  <Select className="h-8 text-xs">
                    <option>High (Visually Lossless)</option>
                    <option>Medium (Balanced Size)</option>
                    <option>Draft (Fast)</option>
                  </Select>
                </div>

                {/* Chapters Section */}
                <div className="pt-2 border-t border-[var(--color-line)] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--color-text)]">Chapters</span>
                    <Switch checked={true} />
                  </div>
                  <div className="space-y-1.5 text-xs max-h-32 overflow-y-auto custom-scrollbar pr-1">
                    {[
                      { time: "00:00", title: "Introduction" },
                      { time: "02:15", title: "Main Topic" },
                      { time: "08:30", title: "Key Insights" },
                      { time: "14:20", title: "Conclusion" },
                    ].map((ch) => (
                      <div key={ch.time} className="flex items-center justify-between p-1.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)]">
                        <span className="font-mono text-[var(--color-accent)] text-[10px]">{ch.time}</span>
                        <span className="text-[var(--color-text)] font-medium truncate flex-1 mx-2">{ch.title}</span>
                        <span className="text-[var(--color-muted)] hover:text-rose-400 cursor-pointer">🗑</span>
                      </div>
                    ))}
                  </div>
                </div>

                <Button
                  size="sm"
                  onClick={triggerAnalyze}
                  className="w-full h-9 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow"
                >
                  <Check className="w-3.5 h-3.5 mr-1" />
                  <span>Apply Changes</span>
                </Button>
              </div>
            )}

            {/* Export Tab */}
            {inspectorTab === 'export' && (
              <div className="space-y-3 text-xs flex-1">
                <div>
                  <label className="text-[10px] text-[var(--color-muted)] block mb-1">Output Name</label>
                  <Input defaultValue="podcast_master.mp4" className="h-8 text-xs font-mono" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-[var(--color-muted)] block mb-1">Export As</label>
                    <Select className="h-8 text-xs">
                      <option>Media File</option>
                      <option>NLE Timeline</option>
                    </Select>
                  </div>
                  <div>
                    <label className="text-[10px] text-[var(--color-muted)] block mb-1">Format</label>
                    <Select className="h-8 text-xs">
                      <option>mp4</option>
                      <option>mkv</option>
                      <option>mov</option>
                    </Select>
                  </div>
                </div>

                <Button
                  size="sm"
                  onClick={triggerExport}
                  className="w-full h-9 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow"
                >
                  Start Export
                </Button>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* BOTTOM MULTI-TRACK NLE TIMELINE (Matching Image 2) */}
      <div className="h-44 bg-[var(--color-card)] border border-[var(--color-line)] rounded-2xl p-3 flex flex-col justify-between shadow-sm shrink-0">
        {/* Timeline Header */}
        <div className="flex items-center justify-between pb-2 border-b border-[var(--color-line)]">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[var(--color-text)]">Timeline</span>
            <span className="text-[10px] font-mono text-[var(--color-muted)] px-2 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-line)]">
              {activeProject ? activeProject.title : "podcast_full.mp4"}
            </span>
            <span className="text-[10px] font-mono text-[var(--color-muted)]">1080p • 60fps</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Tools */}
            <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-line)] rounded-xl p-0.5">
              <button
                onClick={() => setTimelineTool('select')}
                className={`p-1 rounded ${timelineTool === 'select' ? 'text-[var(--color-accent)] font-bold' : 'text-[var(--color-muted)]'}`}
              >
                <MousePointer className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setTimelineTool('hand')}
                className={`p-1 rounded ${timelineTool === 'hand' ? 'text-[var(--color-accent)] font-bold' : 'text-[var(--color-muted)]'}`}
              >
                <Hand className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setTimelineTool('cut')}
                className={`p-1 rounded ${timelineTool === 'cut' ? 'text-[var(--color-accent)] font-bold' : 'text-[var(--color-muted)]'}`}
              >
                <Scissors className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setTimelineTool('ruler')}
                className={`p-1 rounded ${timelineTool === 'ruler' ? 'text-[var(--color-accent)] font-bold' : 'text-[var(--color-muted)]'}`}
              >
                <Ruler className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Zoom Slider */}
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-[var(--color-muted)]">Zoom</span>
              <Slider
                min={1}
                max={5}
                step={0.5}
                value={timelineZoom}
                onValueChange={(val) => setTimelineZoom(val)}
                className="w-16"
              />
              <span className="font-mono text-[var(--color-muted)] text-[10px]">{timelineZoom}x</span>
            </div>

            <Button
              size="sm"
              className="h-7 px-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow"
            >
              + Add to Timeline
            </Button>
          </div>
        </div>

        {/* Tracks Canvas Area */}
        <div className="flex-1 flex gap-2 pt-2 overflow-hidden">
          {/* Track Headers */}
          <div className="w-24 flex flex-col justify-around text-[10px] font-medium text-[var(--color-muted)] shrink-0 pr-2 border-r border-[var(--color-line)] select-none">
            <div className="flex items-center justify-between">
              <span>📹 Video</span>
              <span>👁</span>
            </div>
            <div className="flex items-center justify-between">
              <span>🔤 Captions</span>
              <span>👁</span>
            </div>
            <div className="flex items-center justify-between">
              <span>🔊 Audio</span>
              <span>👁</span>
            </div>
          </div>

          {/* Canvas */}
          <div className="w-full flex-1 relative bg-black/60 rounded-xl overflow-hidden border border-[var(--color-line)] cursor-pointer">
            <canvas ref={canvasRef} className="w-full h-full block" />
          </div>
        </div>

        {/* Summary Footer */}
        <div className="flex items-center justify-between text-[10px] font-mono text-[var(--color-muted)] pt-1 border-t border-[var(--color-line)]">
          <div className="flex items-center gap-3">
            <span>Cuts Made: <strong className="text-[var(--color-accent)]">14</strong></span>
            <span>Time Cut Out: <strong className="text-rose-400">12.5 min</strong></span>
            <span>Time Saved: <strong className="text-emerald-400">1.2 h</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-cyan-400 font-bold">Kept: 29.6 min</span>
            <span className="text-rose-400 font-bold">Dead Air: 12.5 min</span>
          </div>
        </div>
      </div>
    </div>
  )
}
