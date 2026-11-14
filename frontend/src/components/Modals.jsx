import * as React from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { 
  Sparkles, 
  X, 
  Check, 
  Copy, 
  Share2, 
  Palette, 
  Film, 
  Folder, 
  Settings as SettingsIcon, 
  Zap, 
  Cpu, 
  Shuffle,
  Play,
  Pause,
  RotateCcw
} from "lucide-react"
import { Badge } from "@/components/ui/badge"

// 1. New Long-Form Project Modal
export function NewProjectModal({ open, onClose, onSubmitSuccess }) {
  const [localVideos, setLocalVideos] = React.useState([])
  const [selectedVideo, setSelectedVideo] = React.useState("")
  const [projectTitle, setProjectTitle] = React.useState("")
  const [contentType, setContentType] = React.useState("general")
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    if (open) {
      fetch('/api/local-videos')
        .then(res => res.json())
        .then(data => {
          setLocalVideos(data.videos || [])
          if (data.videos && data.videos.length > 0) {
            setSelectedVideo(data.videos[0].path)
          }
        })
        .catch(console.error)
    }
  }, [open])

  const handleCreate = async () => {
    if (!selectedVideo) return
    setLoading(true)
    try {
      const res = await fetch('/api/long-form/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: selectedVideo,
          title: projectTitle || undefined,
          content_type: contentType
        })
      })
      const data = await res.json()
      if (data.project) {
        onClose()
        if (onSubmitSuccess) onSubmitSuccess(data.project)
      }
    } catch (e) {
      alert("Failed to create project: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            <Film className="w-5 h-5 text-[var(--color-accent)] inline mr-2" />
            <span>Create Long-Form Studio Project</span>
          </DialogTitle>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 rounded-lg">
            <X className="w-4 h-4" />
          </Button>
        </DialogHeader>

        <div className="space-y-3 py-3 text-xs">
          <div>
            <label className="text-[var(--color-muted)] block mb-1 font-semibold">Select Local Video</label>
            <Select
              value={selectedVideo}
              onChange={(e) => setSelectedVideo(e.target.value)}
              className="h-9"
            >
              {localVideos.map((v) => (
                <option key={v.path} value={v.path}>
                  {v.name} ({v.size_mb} MB)
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="text-[var(--color-muted)] block mb-1 font-semibold">Project Title</label>
            <Input
              placeholder="e.g. Full Stream Edit Episode 12"
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
              className="h-9"
            />
          </div>

          <div>
            <label className="text-[var(--color-muted)] block mb-1 font-semibold">Content Style Profile</label>
            <Select
              value={contentType}
              onChange={(e) => setContentType(e.target.value)}
              className="h-9"
            >
              <option value="general">General Video (Balanced)</option>
              <option value="gaming">Gaming Stream (Fast Action / Keep Suspense)</option>
              <option value="podcast">Podcast & Interview (Speech Clarity / Remove Dead Air)</option>
              <option value="tutorial">Tutorial / Educational (Preserve Complete Steps)</option>
              <option value="vlog">Vlog (Casual Storytelling)</option>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose} className="h-8">Cancel</Button>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={loading}
            className="h-8 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold"
          >
            {loading ? "Creating..." : "Initialize Project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// 2. Caption Playground Modal (Full Captions Studio)
export function CaptionPlaygroundModal({ open, onClose, currentStyle, onApplyStyle }) {
  const [fontFamily, setFontFamily] = React.useState(currentStyle?.fontFamily || "Montserrat")
  const [fontSize, setFontSize] = React.useState(currentStyle?.fontSize || 68)
  const [rotationAngle, setRotationAngle] = React.useState(currentStyle?.rotationAngle || 0)
  const [randomFlip, setRandomFlip] = React.useState(currentStyle?.randomFlip || false)
  const [primaryColor, setPrimaryColor] = React.useState(currentStyle?.primaryColor || "#FFFFFF")
  const [activeColor, setActiveColor] = React.useState(currentStyle?.activeColor || "#FFD400")
  const [emphasisColor, setEmphasisColor] = React.useState(currentStyle?.emphasisColor || "#00FFCC")
  const [strokeColor, setStrokeColor] = React.useState(currentStyle?.strokeColor || "#000000")
  const [strokeWidth, setStrokeWidth] = React.useState(currentStyle?.strokeWidth || "2")
  const [bgMode, setBgMode] = React.useState(currentStyle?.bgMode || "none")
  
  // Multi-phrase / sentence playback support (e.g. "I live in city // but I always love my village")
  const [previewText, setPreviewText] = React.useState("I LIVE IN CITY // BUT I ALWAYS LOVE MY {{VILLAGE}}")
  const [activePhraseIndex, setActivePhraseIndex] = React.useState(0)
  const [activeWordIndex, setActiveWordIndex] = React.useState(0)
  const [isPlaying, setIsPlaying] = React.useState(true)
  const [playbackSpeed, setPlaybackSpeed] = React.useState(400) // ms per word
  const [previewFlipState, setPreviewFlipState] = React.useState(false)

  // Style Presets definition
  const PRESETS = {
    mrbeast: {
      name: "MrBeast Tilt",
      font: "Montserrat",
      size: 68,
      primary: "#FFFFFF",
      active: "#FFD400",
      emphasis: "#00FFCC",
      stroke: "#000000",
      strokeWidth: "4",
      rotation: -4,
      bgMode: "emphasis"
    },
    cyberpunk: {
      name: "Cyberpunk Glow",
      font: "Anton",
      size: 72,
      primary: "#00F0FF",
      active: "#FFE600",
      emphasis: "#FF0055",
      stroke: "#000000",
      strokeWidth: "4",
      rotation: 0,
      bgMode: "word"
    },
    hormozi: {
      name: "Hormozi Yellow",
      font: "Montserrat",
      size: 68,
      primary: "#FFFFFF",
      active: "#22C55E",
      emphasis: "#22C55E",
      stroke: "#000000",
      strokeWidth: "4",
      rotation: 0,
      bgMode: "word"
    },
    cleanbox: {
      name: "Clean Box",
      font: "Montserrat",
      size: 60,
      primary: "#FFFFFF",
      active: "#38BDF8",
      emphasis: "#38BDF8",
      stroke: "#000000",
      strokeWidth: "2",
      rotation: 0,
      bgMode: "phrase"
    },
    hotred: {
      name: "Red Punch",
      font: "The Bold Font",
      size: 70,
      primary: "#FFFFFF",
      active: "#EF4444",
      emphasis: "#F97316",
      stroke: "#000000",
      strokeWidth: "4",
      rotation: -5,
      bgMode: "emphasis"
    },
    goldpop: {
      name: "Gold Pop",
      font: "Bebas Neue",
      size: 74,
      primary: "#FFFFFF",
      active: "#F59E0B",
      emphasis: "#FCD34D",
      stroke: "#000000",
      strokeWidth: "4",
      rotation: 2,
      bgMode: "word"
    }
  }

  // Parse phrases separated by // or newlines
  const phrases = React.useMemo(() => {
    const rawPhrases = previewText
      .split(/\/\/|\n+/)
      .map(p => p.trim())
      .filter(Boolean)
    return rawPhrases.length > 0 ? rawPhrases : ["I LIVE IN CITY", "BUT I ALWAYS LOVE MY {{VILLAGE}}"]
  }, [previewText])

  // Parse tokens for current phrase
  const currentTokens = React.useMemo(() => {
    const phrase = phrases[activePhraseIndex] || phrases[0] || ""
    const tokens = []
    const parts = phrase.split(/(\{\{[^}]+\}\})/g)
    for (const part of parts) {
      if (!part) continue
      if (part.startsWith('{{') && part.endsWith('}}')) {
        const inner = part.slice(2, -2).trim()
        const words = inner.split(/\s+/)
        for (const w of words) {
          if (w) tokens.push({ word: w, isEmphasis: true })
        }
      } else {
        const words = part.split(/\s+/)
        for (const w of words) {
          if (w) tokens.push({ word: w, isEmphasis: false })
        }
      }
    }
    return tokens
  }, [phrases, activePhraseIndex])

  // Sync incoming currentStyle on open
  React.useEffect(() => {
    if (open && currentStyle) {
      if (currentStyle.fontFamily) setFontFamily(currentStyle.fontFamily)
      if (currentStyle.fontSize) setFontSize(currentStyle.fontSize)
      if (currentStyle.rotationAngle !== undefined) setRotationAngle(currentStyle.rotationAngle)
      if (currentStyle.randomFlip !== undefined) setRandomFlip(currentStyle.randomFlip)
      if (currentStyle.primaryColor) setPrimaryColor(currentStyle.primaryColor)
      if (currentStyle.activeColor) setActiveColor(currentStyle.activeColor)
      if (currentStyle.emphasisColor) setEmphasisColor(currentStyle.emphasisColor)
      if (currentStyle.strokeColor) setStrokeColor(currentStyle.strokeColor)
      if (currentStyle.strokeWidth) setStrokeWidth(currentStyle.strokeWidth)
      if (currentStyle.bgMode) setBgMode(currentStyle.bgMode)
    }
  }, [open, currentStyle])

  // Karaoke playback timer across words & phrases
  React.useEffect(() => {
    if (!open || !isPlaying) return

    const timer = setInterval(() => {
      setActiveWordIndex(prevWordIdx => {
        if (prevWordIdx + 1 < currentTokens.length) {
          return prevWordIdx + 1
        } else {
          // Move to next phrase after a brief pause
          setActivePhraseIndex(prevPhraseIdx => {
            const nextPhraseIdx = (prevPhraseIdx + 1) % phrases.length
            // Toggle flip state per phrase if randomFlip is enabled
            if (randomFlip) {
              setPreviewFlipState(nextPhraseIdx % 2 === 1)
            }
            return nextPhraseIdx
          })
          return 0
        }
      })
    }, playbackSpeed)

    return () => clearInterval(timer)
  }, [open, isPlaying, currentTokens.length, phrases.length, playbackSpeed, randomFlip])

  // When randomFlip changes, sync state
  React.useEffect(() => {
    if (!randomFlip) {
      setPreviewFlipState(false)
    }
  }, [randomFlip])

  const effectiveAngle = randomFlip ? (previewFlipState ? -rotationAngle : rotationAngle) : rotationAngle

  const applyPreset = (key) => {
    const p = PRESETS[key]
    if (!p) return
    setFontFamily(p.font)
    setFontSize(p.size)
    setPrimaryColor(p.primary)
    setActiveColor(p.active)
    setEmphasisColor(p.emphasis)
    setStrokeColor(p.stroke)
    setStrokeWidth(p.strokeWidth)
    setRotationAngle(p.rotation)
    setBgMode(p.bgMode)
  }

  const handleApply = () => {
    if (onApplyStyle) {
      onApplyStyle({
        fontFamily,
        fontSize,
        rotationAngle,
        randomFlip,
        primaryColor,
        activeColor,
        emphasisColor,
        strokeColor,
        strokeWidth,
        bgMode
      })
    }
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <div className="flex items-center justify-between w-full">
            <DialogTitle className="flex items-center gap-2">
              <Palette className="w-5 h-5 text-[var(--color-accent)]" />
              <span>Caption Style Studio & Playground</span>
              <Badge variant="outline" className="text-[10px] text-[var(--color-accent)] border-[var(--color-accent)]/30">
                Full Studio
              </Badge>
            </DialogTitle>
            <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 rounded-lg">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 py-2">
          {/* Controls Left Column */}
          <div className="lg:col-span-7 space-y-3.5">
            {/* Style Presets Palette with Visual Previews */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[10px] font-bold text-[var(--color-muted)] uppercase tracking-wider">
                  Style Presets
                </label>
                <span className="text-[10px] text-[var(--color-muted)]">Click preset to load styles</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(PRESETS).map(([key, p]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => applyPreset(key)}
                    className="p-2 rounded-xl bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-[var(--color-accent)] transition text-left group flex flex-col justify-between h-20 shadow-sm"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[11px] font-bold text-[var(--color-text)] truncate">{p.name}</span>
                      <span className="text-[9px] font-mono text-[var(--color-muted)]">{p.rotation !== 0 ? `${p.rotation}°` : 'Flat'}</span>
                    </div>
                    {/* Live Miniature Style Badge Preview */}
                    <div className="w-full flex items-center justify-center py-1">
                      <span
                        className="text-xs font-black uppercase tracking-wider px-2 py-0.5 rounded transition-transform group-hover:scale-105"
                        style={{
                          color: p.active,
                          fontFamily: p.font,
                          transform: `rotate(${p.rotation}deg)`,
                          backgroundColor: p.bgMode === 'word' || p.bgMode === 'emphasis' ? '#000000e6' : (p.bgMode === 'phrase' ? '#000000b0' : 'transparent'),
                          border: p.bgMode !== 'none' ? `1px solid ${p.active}66` : 'none',
                          textShadow: `-${p.strokeWidth}px -${p.strokeWidth}px 0 ${p.stroke}, ${p.strokeWidth}px -${p.strokeWidth}px 0 ${p.stroke}, -${p.strokeWidth}px ${p.strokeWidth}px 0 ${p.stroke}, ${p.strokeWidth}px ${p.strokeWidth}px 0 ${p.stroke}`
                        }}
                      >
                        Sample
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Typography Controls */}
            <div className="grid grid-cols-3 gap-2.5">
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Font Family</label>
                <Select value={fontFamily} onChange={(e) => setFontFamily(e.target.value)} className="h-8 text-xs font-semibold">
                  <option value="Montserrat">Montserrat ExtraBold</option>
                  <option value="Anton">Anton Impact</option>
                  <option value="Bebas Neue">Bebas Neue Bold</option>
                  <option value="Poppins">Poppins Heavy</option>
                  <option value="Inter">Inter Black</option>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Font Size: {fontSize}px</label>
                <Slider min={36} max={96} step={2} value={fontSize} onValueChange={setFontSize} className="py-2" />
              </div>
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Tilt Angle: {rotationAngle}°</label>
                <Slider min={-15} max={15} step={1} value={rotationAngle} onValueChange={setRotationAngle} className="py-2" />
              </div>
            </div>

            {/* Random Flip Option */}
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)]">
              <div className="flex items-center gap-2">
                <Shuffle className="w-4 h-4 text-[var(--color-accent)]" />
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text)] block">Random Flip Angle</span>
                  <span className="text-[9px] text-[var(--color-muted)]">Flips tilt sign between phrases (+{Math.abs(rotationAngle)}° ⇄ -{Math.abs(rotationAngle)}°)</span>
                </div>
              </div>
              <Switch checked={randomFlip} onCheckedChange={setRandomFlip} />
            </div>

            {/* Color Palette Grid */}
            <div className="grid grid-cols-4 gap-2">
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Text Color</label>
                <div className="flex items-center gap-1.5 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="w-5 h-5 rounded cursor-pointer bg-transparent border-0" />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{primaryColor}</span>
                </div>
              </div>
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Active Pop</label>
                <div className="flex items-center gap-1.5 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input type="color" value={activeColor} onChange={(e) => setActiveColor(e.target.value)} className="w-5 h-5 rounded cursor-pointer bg-transparent border-0" />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{activeColor}</span>
                </div>
              </div>
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Emphasis Tag</label>
                <div className="flex items-center gap-1.5 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input type="color" value={emphasisColor} onChange={(e) => setEmphasisColor(e.target.value)} className="w-5 h-5 rounded cursor-pointer bg-transparent border-0" />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{emphasisColor}</span>
                </div>
              </div>
              <div>
                <label className="text-[10px] text-[var(--color-muted)] block mb-1">Stroke Outline</label>
                <div className="flex items-center gap-1.5 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input type="color" value={strokeColor} onChange={(e) => setStrokeColor(e.target.value)} className="w-5 h-5 rounded cursor-pointer bg-transparent border-0" />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{strokeColor}</span>
                </div>
              </div>
            </div>

            {/* Background Style and Stroke Width */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--color-muted)] block mb-1">Background Style</label>
                <Select value={bgMode} onChange={(e) => setBgMode(e.target.value)} className="h-8 text-xs">
                  <option value="none">None (Transparent)</option>
                  <option value="word">Active Word Pill</option>
                  <option value="emphasis">Emphasis Tag Pill</option>
                  <option value="phrase">Full Box Pill</option>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--color-muted)] block mb-1">Stroke Width</label>
                <Select value={strokeWidth} onChange={(e) => setStrokeWidth(e.target.value)} className="h-8 text-xs">
                  <option value="0">None (0px)</option>
                  <option value="2">2px Outline</option>
                  <option value="4">4px Heavy Outline</option>
                </Select>
              </div>
            </div>

            {/* Preview Sentence with Multi-line / Phrase Split Support */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-[var(--color-muted)]">
                  Speech Text (Use <code className="text-[var(--color-accent)] font-mono text-[10px] font-bold">{'//'}</code> to split lines, <code className="text-emerald-400 font-mono text-[10px] font-bold">{'{{word}}'}</code> for emphasis)
                </label>
                <span className="text-[9px] text-[var(--color-muted)]">{phrases.length} phrase(s)</span>
              </div>
              <Input
                value={previewText}
                onChange={(e) => {
                  setPreviewText(e.target.value)
                  setActivePhraseIndex(0)
                  setActiveWordIndex(0)
                }}
                placeholder="e.g. I live in city // but I always love my village"
                className="h-8 text-xs font-mono"
              />
              <p className="text-[10px] text-[var(--color-muted)]">
                Example: <span className="text-[var(--color-text)]">I live in city // but I always love my village</span> &rarr; First phrase displays, then sequentially transitions to the second phrase.
              </p>
            </div>
          </div>

          {/* Right Monitor Preview */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-3">
            <div className="aspect-[9/16] max-h-[360px] mx-auto w-full bg-black rounded-3xl border border-[var(--color-line)] flex flex-col items-center justify-between p-4 relative overflow-hidden shadow-2xl">
              {/* Top Status in Monitor */}
              <div className="w-full flex items-center justify-between text-[10px] text-gray-400 font-mono z-10">
                <span className="flex items-center gap-1 text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  KARAOKE
                </span>
                <span>Phrase {activePhraseIndex + 1}/{phrases.length}</span>
              </div>

              {/* Central Dynamic Caption Stage */}
              <div
                className={`text-center font-black uppercase tracking-wider transition-all duration-200 ${
                  bgMode === 'phrase' ? 'bg-black/80 px-4 py-2 rounded-2xl border border-white/20 backdrop-blur-sm' : ''
                }`}
                style={{
                  transform: `rotate(${effectiveAngle}deg)`,
                  fontFamily,
                  fontSize: `${Math.max(18, Math.round(fontSize * 0.32))}px`,
                  color: primaryColor,
                  textShadow: strokeWidth > 0 ? `
                    -${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},
                    -${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},
                     0px 4px 8px rgba(0,0,0,0.9)
                  ` : '0px 2px 4px rgba(0,0,0,0.8)'
                }}
              >
                {currentTokens.map((t, idx) => {
                  const isActive = idx === activeWordIndex
                  let wordColor = primaryColor
                  let badgeStyle = {}
                  let scaleClass = 'scale-100'

                  if (t.isEmphasis) {
                    wordColor = emphasisColor
                    if (bgMode === 'emphasis') {
                      badgeStyle = {
                        backgroundColor: '#000000e6',
                        border: `1px solid ${emphasisColor}66`,
                        boxShadow: `0 0 10px ${emphasisColor}40`,
                        borderRadius: '8px',
                        padding: '1px 6px'
                      }
                      scaleClass = 'scale-110 font-black'
                    }
                  }

                  if (isActive) {
                    wordColor = activeColor
                    if (bgMode === 'word') {
                      badgeStyle = {
                        backgroundColor: '#000000e6',
                        border: `1px solid ${activeColor}80`,
                        boxShadow: `0 0 12px ${activeColor}60`,
                        borderRadius: '8px',
                        padding: '1px 6px'
                      }
                    }
                    scaleClass = 'scale-125 font-black z-10'
                  }

                  return (
                    <span
                      key={idx}
                      className={`inline-block mx-1 my-0.5 transition-all duration-150 transform ${scaleClass}`}
                      style={{ color: wordColor, ...badgeStyle }}
                    >
                      {t.word}
                    </span>
                  )
                })}
              </div>

              {/* Bottom Playback Scrubber */}
              <div className="w-full space-y-1.5 z-10">
                <div className="flex items-center justify-between text-[9px] text-gray-400 font-mono">
                  <span>Speed: {playbackSpeed}ms</span>
                  <span>{effectiveAngle}° {randomFlip ? '(Random)' : ''}</span>
                </div>
                <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[var(--color-accent)] h-full transition-all duration-200"
                    style={{
                      width: `${Math.round(((activeWordIndex + 1) / Math.max(1, currentTokens.length)) * 100)}%`
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Playback Controls and Speed Selector */}
            <div className="flex items-center justify-between gap-2 px-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsPlaying(!isPlaying)}
                className="h-8 text-xs flex items-center gap-1.5 flex-1"
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5 text-amber-400" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
                <span>{isPlaying ? 'Pause' : 'Play Karaoke'}</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActivePhraseIndex(0)
                  setActiveWordIndex(0)
                }}
                className="h-8 text-xs flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset</span>
              </Button>
              <Select
                value={String(playbackSpeed)}
                onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                className="h-8 text-xs w-24"
              >
                <option value="600">0.7x Slow</option>
                <option value="400">1.0x Normal</option>
                <option value="250">1.5x Fast</option>
              </Select>
            </div>

            <Button
              onClick={handleApply}
              className="w-full h-10 rounded-2xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-bold shadow hover:from-purple-500 hover:to-indigo-500"
            >
              Save & Apply Style to Active Studio
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// 3. Local Videos Library Modal
export function LocalVideosModal({ open, onClose, onSelectVideo }) {
  const [videos, setVideos] = React.useState([])
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    if (open) {
      setLoading(true)
      fetch('/api/local-videos')
        .then(r => r.json())
        .then(d => {
          setVideos(d.videos || [])
        })
        .finally(() => setLoading(false))
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            <Folder className="w-5 h-5 text-[var(--color-accent)] inline mr-2" />
            <span>Local Video Library</span>
          </DialogTitle>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 rounded-lg">
            <X className="w-4 h-4" />
          </Button>
        </DialogHeader>

        <p className="text-xs text-[var(--color-muted)] py-1">Available videos detected in your project directories:</p>
        
        <div className="max-h-72 overflow-y-auto custom-scrollbar space-y-2 pr-1 text-xs">
          {loading ? (
            <div className="text-[var(--color-muted)] py-4 text-center italic">Scanning directories...</div>
          ) : videos.length === 0 ? (
            <div className="text-[var(--color-muted)] py-4 text-center">No video files found. Use the upload button to upload one.</div>
          ) : (
            videos.map((v) => (
              <div
                key={v.path}
                onClick={() => {
                  onSelectVideo(v.path, v.name)
                  onClose()
                }}
                className="group p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)] hover:border-[var(--color-accent)] cursor-pointer transition flex items-center justify-between"
              >
                <div className="space-y-0.5 overflow-hidden pr-2">
                  <div className="text-xs font-semibold text-[var(--color-text)] group-hover:text-[var(--color-accent)] truncate">
                    {v.name}
                  </div>
                  <div className="text-[10px] text-[var(--color-muted)] font-mono truncate">{v.path}</div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] font-mono text-[var(--color-muted)]">{v.size_mb} MB</span>
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-[var(--color-card)] text-[var(--color-text)] font-bold">
                    {v.source}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose} className="h-8">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// 4. YouTube Post Modal
export function YouTubeModal({ open, onClose, clip }) {
  const [title, setTitle] = React.useState(clip ? `${clip.title} #shorts` : "")
  const [desc, setDesc] = React.useState(clip ? `${clip.excerpt}\n\nSoundtrack: ${clip.music}\n\n#shorts #podcast #viral` : "")

  React.useEffect(() => {
    if (clip) {
      setTitle(`${clip.title} #shorts`)
      setDesc(`${clip.excerpt}\n\nSoundtrack: ${clip.music}\n\n#shorts #podcast #viral`)
    }
  }, [clip])

  const copyAndOpen = () => {
    const text = `${title}\n\n${desc}`
    navigator.clipboard.writeText(text)
    alert("Copied Title & Description to clipboard! Opening YouTube Studio upload...")
    window.open("https://studio.youtube.com/channel/UC/videos/upload?d=ud", "_blank")
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-red-500">
            <Share2 className="w-4 h-4 fill-current inline mr-2" />
            <span>YouTube Shorts Automation</span>
          </DialogTitle>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 rounded-lg">
            <X className="w-4 h-4" />
          </Button>
        </DialogHeader>

        <div className="space-y-3 py-3 text-xs">
          <div>
            <label className="text-[var(--color-muted)] block mb-1 font-semibold">Video Title</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} className="h-9 font-medium" />
          </div>
          <div>
            <label className="text-[var(--color-muted)] block mb-1 font-semibold">Description & Hashtags</label>
            <textarea
              rows={4}
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full text-xs px-2.5 py-1.5 font-mono rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)] text-[var(--color-text)]"
            />
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-col gap-2">
          <Button
            onClick={copyAndOpen}
            className="w-full h-9 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold flex items-center justify-center gap-1.5"
          >
            <Copy className="w-3.5 h-3.5" />
            <span>Copy Metadata &amp; Open YouTube Studio</span>
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              navigator.clipboard.writeText(`${title}\n\n${desc}`)
              alert("Metadata copied!")
            }}
            className="w-full h-8"
          >
            Copy Only
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// 5. Settings Slide-Over Sidebar
export function SettingsSidebar({ open, onClose, engineArch, setEngineArch }) {
  const [groqKey, setGroqKey] = React.useState(localStorage.getItem('openclip_groq_api_key') || "")
  const [groqModel, setGroqModel] = React.useState(localStorage.getItem('openclip_groq_model') || "llama-3.3-70b-versatile")
  const [whisperHw, setWhisperHw] = React.useState("auto")
  const [renderHw, setRenderHw] = React.useState("auto")

  const handleSave = () => {
    localStorage.setItem('openclip_groq_api_key', groqKey)
    localStorage.setItem('openclip_groq_model', groqModel)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-y-0 right-0 max-w-sm w-full bg-[var(--color-sidebar)] border-l border-[var(--color-line)] shadow-2xl z-50 flex flex-col justify-between animate-in slide-in-from-right duration-200">
      <div className="p-5 space-y-5 overflow-y-auto custom-scrollbar">
        <div className="flex items-center justify-between border-b border-[var(--color-line)] pb-3">
          <div className="flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-[var(--color-accent)]" />
            <h2 className="text-sm font-bold text-[var(--color-text)]">Studio & Hardware Settings</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 rounded-lg">
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Engine Architecture */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider">Engine Architecture</h3>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-[var(--color-surface)] text-[var(--color-text)]">
              {engineArch}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <label
              onClick={() => setEngineArch('openclip_standard')}
              className={`p-2.5 rounded-xl border bg-[var(--color-card)] cursor-pointer transition ${
                engineArch === 'openclip_standard' ? "border-[var(--color-accent)]" : "border-[var(--color-line)]"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-[var(--color-text)]">1.0 Standard</span>
                <input type="radio" checked={engineArch === 'openclip_standard'} readOnly className="accent-[var(--color-accent)]" />
              </div>
              <p className="text-[9px] text-[var(--color-muted)]">Acoustic RMS + local heuristic.</p>
            </label>

            <label
              onClick={() => setEngineArch('wayin_2_0')}
              className={`p-2.5 rounded-xl border bg-[var(--color-card)] cursor-pointer transition ${
                engineArch === 'wayin_2_0' ? "border-[var(--color-accent)]" : "border-[var(--color-line)]"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-[var(--color-accent)]">2.0 Beta</span>
                <input type="radio" checked={engineArch === 'wayin_2_0'} readOnly className="accent-[var(--color-accent)]" />
              </div>
              <p className="text-[9px] text-[var(--color-muted)]">Groq LPU + 62-tag virality.</p>
            </label>
          </div>

          {engineArch === 'wayin_2_0' && (
            <div className="space-y-2.5 pt-2 border-t border-[var(--color-line)] text-xs">
              <div>
                <label className="text-[11px] text-[var(--color-muted)] block mb-1">GroqCloud Model</label>
                <Select value={groqModel} onChange={(e) => setGroqModel(e.target.value)} className="h-8 text-xs font-mono">
                  <option value="llama-3.3-70b-versatile">Llama 3.3 70B Versatile (280 T/s)</option>
                  <option value="llama-3.1-8b-instant">Llama 3.1 8B Instant (560 T/s)</option>
                </Select>
              </div>

              <div>
                <label className="text-[11px] text-[var(--color-muted)] block mb-1">Groq API Key</label>
                <Input
                  type="password"
                  value={groqKey}
                  onChange={(e) => setGroqKey(e.target.value)}
                  placeholder="gsk_..."
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>
          )}
        </div>

        {/* Hardware Settings */}
        <div className="space-y-3 pt-3 border-t border-[var(--color-line)] text-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider">Hardware & Performance</h3>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
              GPU / CUDA
            </span>
          </div>

          <div>
            <label className="text-[11px] text-[var(--color-muted)] block mb-1">Whisper Speech AI</label>
            <Select value={whisperHw} onChange={(e) => setWhisperHw(e.target.value)} className="h-8 text-xs">
              <option value="auto">Auto (Fastest GPU / Metal)</option>
              <option value="gpu">GPU (CUDA / Float16)</option>
              <option value="cpu">CPU (INT8 Multi-Thread)</option>
            </Select>
          </div>

          <div>
            <label className="text-[11px] text-[var(--color-muted)] block mb-1">Video Encoder</label>
            <Select value={renderHw} onChange={(e) => setRenderHw(e.target.value)} className="h-8 text-xs">
              <option value="auto">Auto (NVENC / VideoToolbox)</option>
              <option value="gpu">Hardware GPU (NVENC)</option>
              <option value="cpu">Software CPU (libx264)</option>
            </Select>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-[var(--color-line)] bg-[var(--color-card)] flex items-center justify-between">
        <span className="text-[10px] text-[var(--color-muted)]">Settings auto-saved</span>
        <Button size="sm" onClick={handleSave} className="h-8 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-bold">
          Done
        </Button>
      </div>
    </div>
  )
}
