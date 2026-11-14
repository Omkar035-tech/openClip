import * as React from "react"
import { 
  Sparkles, 
  Shuffle, 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize2, 
  Upload, 
  Folder, 
  Check, 
  ChevronRight,
  Music,
  Share2,
  Trash2,
  RotateCcw,
  Sliders,
  Crop,
  Zap
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"

export function ShortsStudio({
  videoPath,
  setVideoPath,
  sourceFileName,
  setSourceFileName,
  onOpenLocalVideos,
  aspectRatio,
  setAspectRatio,
  clipCount,
  setClipCount,
  maxDuration,
  setMaxDuration,
  fallbackLayout,
  setFallbackLayout,
  webcamSplit,
  setWebcamSplit,
  camPlacement,
  setCamPlacement,
  streamerMode,
  setStreamerMode,
  manualCamBox,
  setManualCamBox,
  fontFamily,
  setFontFamily,
  fontSize,
  setFontSize,
  primaryColor,
  setPrimaryColor,
  activeColor,
  setActiveColor,
  emphasisColor,
  setEmphasisColor,
  strokeColor,
  setStrokeColor,
  rotationAngle,
  setRotationAngle,
  randomFlip,
  setRandomFlip,
  bgMode,
  setBgMode,
  strokeWidth,
  setStrokeWidth,
  autoEmphasis,
  setAutoEmphasis,
  ostSelect,
  setOstSelect,
  musicLevel,
  setMusicLevel,
  fxFlash,
  setFxFlash,
  fxProgress,
  setFxProgress,
  fxZoom,
  setFxZoom,
  onTriggerClipping,
  generationState,
  onOpenCaptionPlayground,
  onOpenOstModal,
  onOpenYouTubeModal,
  galleryProjects,
  activeProjectIdx,
  setActiveProjectIdx,
  activeClip,
  setActiveClip,
  onRefreshGallery
}) {
  const fileInputRef = React.useRef(null)
  const videoPlayerRef = React.useRef(null)
  const cropWrapperRef = React.useRef(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [isMuted, setIsMuted] = React.useState(false)
  const [currentTimecode, setCurrentTimecode] = React.useState("00:32 / 01:15")
  const [uploadProgress, setUploadProgress] = React.useState({ show: false, pct: 0, status: "" })
  const [simulatedFlip, setSimulatedFlip] = React.useState(false)

  // In preview canvas, toggle flip every 1.5s when randomFlip is active
  React.useEffect(() => {
    if (!randomFlip) {
      setSimulatedFlip(false)
      return
    }
    const timer = setInterval(() => {
      setSimulatedFlip(prev => !prev)
    }, 1500)
    return () => clearInterval(timer)
  }, [randomFlip])

  const effectiveRotationAngle = randomFlip ? (simulatedFlip ? -rotationAngle : rotationAngle) : rotationAngle

  // Manual Crop Box State
  const [previewTimestamp, setPreviewTimestamp] = React.useState(2.0)
  const [previewFrameUrl, setPreviewFrameUrl] = React.useState(null)
  const [frameLoading, setFrameLoading] = React.useState(false)
  const [videoNaturalDims, setVideoNaturalDims] = React.useState({ width: 1920, height: 1080 })
  const [videoTotalDuration, setVideoTotalDuration] = React.useState(120.0)
  const [isDraggingCrop, setIsDraggingCrop] = React.useState(false)
  const [dragStart, setDragStart] = React.useState({ x: 0, y: 0, boxX: 0, boxY: 0 })

  // Style Presets definitions
  const PRESETS = {
    mrbeast: {
      font: "Montserrat",
      size: 68,
      primary: "#FFFFFF",
      active: "#FFD400",
      emphasis: "#00FFCC",
      stroke: "#000000",
      strokeWidth: "2",
      rotation: -4,
      bgMode: "emphasis"
    },
    cyberpunk: {
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

  const applyQuickPreset = (name) => {
    const p = PRESETS[name]
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

  // Load Video Frame for Manual Crop Preview
  const loadCropFrame = async (time = previewTimestamp, autoDetect = true) => {
    if (!videoPath) {
      alert("Please select or upload a video first to extract frames for cropping.")
      return
    }
    setFrameLoading(true)
    try {
      const res = await fetch(`/api/video/frame?path=${encodeURIComponent(videoPath)}&timestamp=${encodeURIComponent(time)}`)
      if (!res.ok) throw new Error("Could not extract frame")

      const w = parseInt(res.headers.get('X-Video-Width') || '1920')
      const h = parseInt(res.headers.get('X-Video-Height') || '1080')
      const dur = parseFloat(res.headers.get('X-Video-Duration') || '0')
      setVideoNaturalDims({ width: w, height: h })
      if (dur > 0) setVideoTotalDuration(dur)

      if (autoDetect) {
        const detectedHeader = res.headers.get('X-Detected-Cam-Box')
        if (detectedHeader && detectedHeader !== 'null') {
          try {
            const detected = JSON.parse(detectedHeader)
            setManualCamBox([
              Math.round(detected[0]),
              Math.round(detected[1]),
              Math.round(detected[2]),
              Math.round(detected[3])
            ])
          } catch (e) {}
        }
      }

      const blob = await res.blob()
      if (previewFrameUrl) URL.revokeObjectURL(previewFrameUrl)
      setPreviewFrameUrl(URL.createObjectURL(blob))
    } catch (err) {
      console.error("Frame extraction error:", err)
      alert("Failed to grab video frame: " + err.message)
    } finally {
      setFrameLoading(false)
    }
  }

  // Auto-fetch frame when switching to manual crop method
  React.useEffect(() => {
    if (webcamSplit && streamerMode === 'manual' && videoPath && !previewFrameUrl) {
      loadCropFrame(previewTimestamp, true)
    }
  }, [webcamSplit, streamerMode, videoPath])

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return

    setUploadProgress({ show: true, pct: 0, status: `Uploading ${file.name}...` })
    const formData = new FormData()
    formData.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/upload-video', true)

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        const pct = Math.round((ev.loaded / ev.total) * 100)
        setUploadProgress({ show: true, pct, status: `Uploading ${file.name} (${pct}%)` })
      }
    }

    xhr.onload = () => {
      if (xhr.status === 200) {
        try {
          const data = JSON.parse(xhr.responseText)
          if (data.success) {
            setUploadProgress({ show: true, pct: 100, status: `Uploaded ${data.filename} (${data.size_mb} MB)` })
            setVideoPath(data.path)
            setSourceFileName(data.filename)
            setTimeout(() => setUploadProgress({ show: false, pct: 0, status: "" }), 2500)
            if (webcamSplit && streamerMode === 'manual') {
              loadCropFrame(2.0, true)
            }
          }
        } catch (err) {
          setUploadProgress({ show: false, pct: 0, status: "" })
        }
      } else {
        setUploadProgress({ show: true, pct: 0, status: `Upload failed: ${xhr.statusText}` })
      }
    }

    xhr.onerror = () => {
      setUploadProgress({ show: true, pct: 0, status: "Network error during upload" })
    }

    xhr.send(formData)
  }

  const togglePlay = () => {
    if (!videoPlayerRef.current) return
    if (videoPlayerRef.current.paused) {
      videoPlayerRef.current.play()
      setIsPlaying(true)
    } else {
      videoPlayerRef.current.pause()
      setIsPlaying(false)
    }
  }

  const toggleMute = () => {
    if (!videoPlayerRef.current) return
    videoPlayerRef.current.muted = !videoPlayerRef.current.muted
    setIsMuted(videoPlayerRef.current.muted)
  }

  // Active word color resolution
  const resolvedActiveColor = autoEmphasis ? emphasisColor : activeColor

  // Calculate scaled manual crop box overlay coordinates inside wrapper
  const cropBox = manualCamBox || [0, 60, 380, 260]
  const [cbX, cbY, cbW, cbH] = cropBox

  // Mouse handlers for dragging manual crop box
  const handleCropMouseDown = (e) => {
    e.preventDefault()
    setIsDraggingCrop(true)
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      boxX: cbX,
      boxY: cbY
    })
  }

  const handleCropMouseMove = (e) => {
    if (!isDraggingCrop || !cropWrapperRef.current) return
    const dx = e.clientX - dragStart.x
    const dy = e.clientY - dragStart.y
    const wrapW = cropWrapperRef.current.clientWidth || 300
    const wrapH = cropWrapperRef.current.clientHeight || 170

    const scaleX = videoNaturalDims.width / wrapW
    const scaleY = videoNaturalDims.height / wrapH

    const newX = Math.max(0, Math.min(videoNaturalDims.width - cbW, dragStart.boxX + Math.round(dx * scaleX)))
    const newY = Math.max(0, Math.min(videoNaturalDims.height - cbH, dragStart.boxY + Math.round(dy * scaleY)))

    setManualCamBox([newX, newY, cbW, cbH])
  }

  const handleCropMouseUp = () => {
    if (isDraggingCrop) setIsDraggingCrop(false)
  }

  return (
    <div
      className="flex-1 flex flex-col overflow-hidden p-4 space-y-4"
      onMouseMove={handleCropMouseMove}
      onMouseUp={handleCropMouseUp}
    >
      {/* Top 3-Column Studio Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-y-auto custom-scrollbar min-h-0">
        
        {/* ========================================================
            LEFT COLUMN (3 cols): Source Video, Clip Config, Captions
            ======================================================== */}
        <div className="lg:col-span-3 space-y-3.5 flex flex-col justify-start">
          
          {/* 1. Source Video Card */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--color-text)] flex items-center gap-1.5">
                <span>1. Source Video</span>
              </span>
              <span className={`w-2 h-2 rounded-full ${videoPath ? "bg-emerald-400" : "bg-amber-400"}`}></span>
            </div>

            {/* Video Preview Info */}
            <div className="p-2.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)] flex items-center gap-3">
              <div className="w-12 h-10 rounded-lg bg-black/60 flex items-center justify-center text-[var(--color-accent)] shrink-0 overflow-hidden">
                <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                  <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-[var(--color-text)] truncate">
                  {sourceFileName || "Select a video"}
                </div>
                <div className="text-[10px] text-[var(--color-muted)] font-mono truncate">
                  {videoPath ? videoPath.split('\\').pop().split('/').pop() : "No video loaded"}
                </div>
              </div>
            </div>

            {/* Hidden Input & Upload Action Buttons */}
            <input
              type="file"
              ref={fileInputRef}
              accept=".mp4,.mkv,.mov,.webm,.avi"
              className="hidden"
              onChange={handleFileUpload}
            />
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onOpenLocalVideos}
                className="w-full h-8 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-medium"
              >
                <Folder className="w-3.5 h-3.5 mr-1 text-[var(--color-accent)]" />
                <span>Library</span>
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                className="w-full h-8 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-medium"
              >
                <Upload className="w-3.5 h-3.5 mr-1" />
                <span>Change Video</span>
              </Button>
            </div>

            {/* Video Path Manual Input */}
            <Input
              type="text"
              placeholder="Or enter local file path..."
              value={videoPath}
              onChange={(e) => setVideoPath(e.target.value)}
              className="h-8 text-xs font-mono bg-[var(--color-surface)] border-[var(--color-line)] text-[var(--color-text)] rounded-xl"
            />

            {/* Upload Progress Bar */}
            {uploadProgress.show && (
              <div className="p-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-accent)]/40 space-y-1">
                <div className="flex justify-between text-[10px]">
                  <span className="text-[var(--color-accent)] font-medium truncate">{uploadProgress.status}</span>
                  <span className="font-mono font-bold text-[var(--color-text)]">{uploadProgress.pct}%</span>
                </div>
                <div className="w-full bg-[var(--color-line)] h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[var(--color-accent)] h-full transition-all duration-150"
                    style={{ width: `${uploadProgress.pct}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* 2. Clip Configuration Card */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--color-text)]">2. Clip Configuration</span>
              <span className="text-[10px] text-[var(--color-muted)] cursor-pointer" title="Configure output aspect ratio, duration, and fallback crop">ⓘ</span>
            </div>

            {/* Aspect Ratio Buttons Group */}
            <div>
              <label className="text-[10px] font-semibold text-[var(--color-muted)] block mb-1.5 uppercase tracking-wider">
                Aspect Ratio
              </label>
              <div className="grid grid-cols-5 gap-1.5">
                {[
                  { ratio: "9:16", w: "w-3.5", h: "h-6", desc: "9:16 Vertical Reel: Smartphone format for Reels, TikTok & Shorts." },
                  { ratio: "4:5", w: "w-4", h: "h-5", desc: "4:5 Portrait: Ideal for Instagram portrait feeds." },
                  { ratio: "1:1", w: "w-4", h: "h-4", desc: "1:1 Square: Balanced square format for Instagram & LinkedIn." },
                  { ratio: "16:9", w: "w-6", h: "h-3.5", desc: "16:9 Widescreen: Standard landscape for YouTube." },
                  { ratio: "2:3", w: "w-4", h: "h-6", desc: "2:3 Classic: Traditional portrait ratio." },
                ].map((item) => {
                  const isSelected = aspectRatio === item.ratio
                  return (
                    <button
                      key={item.ratio}
                      type="button"
                      onClick={() => setAspectRatio(item.ratio)}
                      className={`py-2 px-1 text-center rounded-xl border text-xs font-bold flex flex-col items-center transition ${
                        isSelected
                          ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)] shadow-sm"
                          : "border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:border-[var(--color-accent)]"
                      }`}
                    >
                      <span className={`${item.w} ${item.h} rounded border border-current mb-1`}></span>
                      <span className="text-[9px]">{item.ratio}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Clip Count (1-10) & Max Clip Duration Slider */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div>
                <label className="text-[10px] font-semibold text-[var(--color-muted)] block mb-1">Clip Count</label>
                <Select
                  value={clipCount}
                  onChange={(e) => setClipCount(parseInt(e.target.value))}
                  className="h-8 text-xs font-semibold"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <option key={n} value={n}>{n} {n === 1 ? 'Clip' : 'Clips'}</option>
                  ))}
                </Select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-[10px] font-semibold text-[var(--color-muted)]">Max Duration</label>
                  <span className="text-[10px] text-[var(--color-accent)] font-mono font-bold">{maxDuration}s</span>
                </div>
                <Slider
                  min={20}
                  max={180}
                  step={5}
                  value={maxDuration}
                  onValueChange={(val) => setMaxDuration(val)}
                  className="mt-2"
                />
              </div>
            </div>

            {/* Fallback Layout Mode & Webcam Split Switch */}
            <div className="space-y-2 pt-1">
              <div>
                <label className="text-[10px] font-semibold text-[var(--color-muted)] block mb-1">Fallback Layout</label>
                <Select
                  value={fallbackLayout}
                  onChange={(e) => setFallbackLayout(e.target.value)}
                  className="h-8 text-xs"
                >
                  <option value="face_centered">Face Centered (Smart Centering)</option>
                  <option value="face_tight">Face Tight (Portrait Zoom)</option>
                  <option value="padded">Letterbox / Pillarbox (Keep Full 16:9)</option>
                  <option value="blurred_bg">Blurred Background Border</option>
                </Select>
              </div>

              {/* Webcam Split Toggle */}
              <div className="flex items-center justify-between p-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)]">
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text)] block">Webcam Split</span>
                  <span className="text-[9px] text-[var(--color-muted)]">Split facecam + gameplay view</span>
                </div>
                <Switch
                  checked={webcamSplit}
                  onCheckedChange={setWebcamSplit}
                />
              </div>

              {/* Webcam Split Options */}
              {webcamSplit && (
                <div className="space-y-2 pt-2 border-t border-[var(--color-line)]">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-[var(--color-muted)] block mb-1">Camera Position</label>
                      <Select
                        value={camPlacement}
                        onChange={(e) => setCamPlacement(e.target.value)}
                        className="h-7 text-xs"
                      >
                        <option value="top">Top Half</option>
                        <option value="bottom">Bottom Half</option>
                      </Select>
                    </div>
                    <div>
                      <label className="text-[10px] text-[var(--color-muted)] block mb-1">Crop Method</label>
                      <Select
                        value={streamerMode}
                        onChange={(e) => {
                          const newMode = e.target.value
                          setStreamerMode(newMode)
                          if (newMode === 'manual' && videoPath) {
                            loadCropFrame(previewTimestamp, true)
                          }
                        }}
                        className="h-7 text-xs font-semibold"
                      >
                        <option value="auto">Auto Face Detect</option>
                        <option value="manual">Manual Box (Interactive)</option>
                      </Select>
                    </div>
                  </div>

                  {/* Manual Crop Box Interactive Window */}
                  {streamerMode === 'manual' && (
                    <div className="p-2.5 rounded-xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-2 animate-in fade-in-0 duration-150">
                      <div className="flex justify-between items-center text-[10px]">
                        <div className="flex items-center gap-1.5 font-mono">
                          <Crop className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                          <span className="text-[var(--color-accent)] font-bold">{previewTimestamp.toFixed(1)}s</span>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={frameLoading}
                          onClick={() => loadCropFrame(previewTimestamp, false)}
                          className="h-6 px-2 text-[10px] rounded-lg border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)]"
                        >
                          {frameLoading ? "Grabbing..." : "Grab Frame"}
                        </Button>
                      </div>

                      {/* Frame seek slider */}
                      <Slider
                        min={0}
                        max={Math.ceil(videoTotalDuration)}
                        step={0.5}
                        value={previewTimestamp}
                        onValueChange={(val) => {
                          setPreviewTimestamp(val)
                        }}
                        onChange={() => {
                          // Debounced frame load on slider change
                          loadCropFrame(previewTimestamp, false)
                        }}
                      />

                      {/* Interactive Crop Canvas Wrapper */}
                      <div
                        ref={cropWrapperRef}
                        className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-[var(--color-line)] flex items-center justify-center select-none"
                      >
                        {previewFrameUrl ? (
                          <img
                            src={previewFrameUrl}
                            alt="Crop Preview Frame"
                            className="w-full h-full object-contain pointer-events-none"
                          />
                        ) : (
                          <div className="text-[10px] text-[var(--color-muted)] italic text-center p-2">
                            {frameLoading ? "Loading frame..." : "Click Grab Frame to preview webcam bounds"}
                          </div>
                        )}

                        {/* Draggable manual crop overlay rectangle */}
                        {cropWrapperRef.current && (
                          <div
                            onMouseDown={handleCropMouseDown}
                            className="absolute border-2 border-[var(--color-accent)] bg-[var(--color-accent-soft)] cursor-move transition-shadow hover:shadow-lg"
                            style={{
                              left: `${(cbX / videoNaturalDims.width) * (cropWrapperRef.current.clientWidth || 280)}px`,
                              top: `${(cbY / videoNaturalDims.height) * (cropWrapperRef.current.clientHeight || 160)}px`,
                              width: `${(cbW / videoNaturalDims.width) * (cropWrapperRef.current.clientWidth || 280)}px`,
                              height: `${(cbH / videoNaturalDims.height) * (cropWrapperRef.current.clientHeight || 160)}px`,
                            }}
                          >
                            <span className="absolute top-0.5 left-1 text-[8px] font-mono font-bold text-white bg-black/60 px-1 rounded pointer-events-none">
                              Cam Box
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Crop bounds numerical inputs */}
                      <div className="grid grid-cols-4 gap-1 text-[10px] font-mono">
                        <div>
                          <label className="text-[9px] text-[var(--color-muted)] block text-center">X</label>
                          <Input
                            type="number"
                            value={cbX}
                            onChange={(e) => setManualCamBox([parseInt(e.target.value) || 0, cbY, cbW, cbH])}
                            className="h-6 text-[10px] font-mono px-1 py-0 text-center"
                          />
                        </div>
                        <div>
                          <label className="text-[9px] text-[var(--color-muted)] block text-center">Y</label>
                          <Input
                            type="number"
                            value={cbY}
                            onChange={(e) => setManualCamBox([cbX, parseInt(e.target.value) || 0, cbW, cbH])}
                            className="h-6 text-[10px] font-mono px-1 py-0 text-center"
                          />
                        </div>
                        <div>
                          <label className="text-[9px] text-[var(--color-muted)] block text-center">Width</label>
                          <Input
                            type="number"
                            value={cbW}
                            onChange={(e) => setManualCamBox([cbX, cbY, parseInt(e.target.value) || 100, cbH])}
                            className="h-6 text-[10px] font-mono px-1 py-0 text-center"
                          />
                        </div>
                        <div>
                          <label className="text-[9px] text-[var(--color-muted)] block text-center">Height</label>
                          <Input
                            type="number"
                            value={cbH}
                            onChange={(e) => setManualCamBox([cbX, cbY, cbW, parseInt(e.target.value) || 100])}
                            className="h-6 text-[10px] font-mono px-1 py-0 text-center"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 3. Captions Style Card */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--color-text)] flex items-center gap-1.5">
                <span className="w-5 h-5 rounded-md bg-[var(--color-accent-soft)] text-[var(--color-accent)] flex items-center justify-center font-serif font-black text-xs">Aa</span>
                <span>3. Captions Style</span>
              </span>
              <button
                type="button"
                onClick={onOpenCaptionPlayground}
                className="text-[10px] font-semibold text-[var(--color-accent)] hover:underline"
              >
                Full Studio ↗
              </button>
            </div>

            {/* Quick Presets Bar (All 6 Pro Presets) */}
            <div>
              <label className="text-[9px] font-semibold text-[var(--color-muted)] block mb-1 uppercase tracking-wider">Style Presets</label>
              <div className="grid grid-cols-3 gap-1.5 text-[10px]">
                <button
                  type="button"
                  onClick={() => applyQuickPreset('mrbeast')}
                  className="py-1 px-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-[var(--color-accent)] text-[var(--color-text)] font-semibold truncate transition text-center flex items-center justify-center gap-1"
                >
                  <Zap className="w-3 h-3 text-amber-400 shrink-0" />
                  <span>MrBeast</span>
                </button>
                <button
                  type="button"
                  onClick={() => applyQuickPreset('cyberpunk')}
                  className="py-1 px-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-cyan-400 text-[var(--color-text)] font-semibold truncate transition text-center flex items-center justify-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-cyan-400 shrink-0" />
                  <span>Cyberpunk</span>
                </button>
                <button
                  type="button"
                  onClick={() => applyQuickPreset('hormozi')}
                  className="py-1 px-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-emerald-400 text-[var(--color-text)] font-semibold truncate transition text-center flex items-center justify-center gap-1"
                >
                  <Zap className="w-3 h-3 text-emerald-400 shrink-0" />
                  <span>Hormozi</span>
                </button>
                <button
                  type="button"
                  onClick={() => applyQuickPreset('cleanbox')}
                  className="py-1 px-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-blue-400 text-[var(--color-text)] font-semibold truncate transition text-center flex items-center justify-center gap-1"
                >
                  <Sliders className="w-3 h-3 text-blue-400 shrink-0" />
                  <span>Clean Box</span>
                </button>
                <button
                  type="button"
                  onClick={() => applyQuickPreset('hotred')}
                  className="py-1 px-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-red-400 text-[var(--color-text)] font-semibold truncate transition text-center flex items-center justify-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-red-400 shrink-0" />
                  <span>Red Punch</span>
                </button>
                <button
                  type="button"
                  onClick={() => applyQuickPreset('goldpop')}
                  className="py-1 px-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-card)] border border-[var(--color-line)] hover:border-amber-400 text-[var(--color-text)] font-semibold truncate transition text-center flex items-center justify-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
                  <span>Gold Pop</span>
                </button>
              </div>
            </div>

            {/* Font Family & Font Size */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-semibold text-[var(--color-muted)] block mb-1">Font Family</label>
                <Select
                  value={fontFamily}
                  onChange={(e) => setFontFamily(e.target.value)}
                  className="h-8 text-xs font-semibold"
                >
                  <option value="Montserrat">Montserrat ExtraBold</option>
                  <option value="Anton">Anton Impact</option>
                  <option value="Bebas Neue">Bebas Neue Bold</option>
                  <option value="Poppins">Poppins Heavy</option>
                  <option value="Inter">Inter Black</option>
                </Select>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-[10px] font-semibold text-[var(--color-muted)]">Font Size</label>
                  <span className="text-[10px] font-mono text-[var(--color-accent)] font-bold">{fontSize}px</span>
                </div>
                <Slider
                  min={40}
                  max={84}
                  step={2}
                  value={fontSize}
                  onValueChange={(val) => setFontSize(val)}
                  className="mt-2"
                />
              </div>
            </div>

            {/* 4 Live Color Palettes: Text Color, Active Pop, Emphasis Tag, Stroke Outline */}
            <div className="grid grid-cols-4 gap-1.5">
              <div>
                <label className="text-[9px] text-[var(--color-muted)] block mb-1 truncate">Text Color</label>
                <div className="flex items-center gap-1 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input
                    type="color"
                    value={primaryColor}
                    onChange={(e) => setPrimaryColor(e.target.value)}
                    className="w-4 h-4 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{primaryColor}</span>
                </div>
              </div>
              <div>
                <label className="text-[9px] text-[var(--color-muted)] block mb-1 truncate">Active Pop</label>
                <div className="flex items-center gap-1 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input
                    type="color"
                    value={activeColor}
                    onChange={(e) => setActiveColor(e.target.value)}
                    className="w-4 h-4 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{activeColor}</span>
                </div>
              </div>
              <div>
                <label className="text-[9px] text-[var(--color-muted)] block mb-1 truncate">Emphasis</label>
                <div className="flex items-center gap-1 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input
                    type="color"
                    value={emphasisColor}
                    onChange={(e) => setEmphasisColor(e.target.value)}
                    className="w-4 h-4 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{emphasisColor}</span>
                </div>
              </div>
              <div>
                <label className="text-[9px] text-[var(--color-muted)] block mb-1 truncate">Stroke</label>
                <div className="flex items-center gap-1 p-1 bg-[var(--color-surface)] rounded-lg border border-[var(--color-line)]">
                  <input
                    type="color"
                    value={strokeColor}
                    onChange={(e) => setStrokeColor(e.target.value)}
                    className="w-4 h-4 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="text-[9px] font-mono text-[var(--color-text)] uppercase">{strokeColor}</span>
                </div>
              </div>
            </div>

            {/* Tilt Angle & Background Style & Stroke Width */}
            <div className="grid grid-cols-3 gap-2">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-[9px] text-[var(--color-muted)]">Tilt</label>
                  <span className="text-[9px] font-mono text-[var(--color-accent)] font-bold">{rotationAngle}°</span>
                </div>
                <Slider
                  min={-12}
                  max={12}
                  step={1}
                  value={rotationAngle}
                  onValueChange={(val) => setRotationAngle(val)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-[9px] text-[var(--color-muted)] block mb-1">Background</label>
                <Select
                  value={bgMode}
                  onChange={(e) => setBgMode(e.target.value)}
                  className="h-7 text-xs px-1.5"
                >
                  <option value="none">None</option>
                  <option value="word">Active Word</option>
                  <option value="emphasis">Emphasis Pill</option>
                  <option value="phrase">Full Box</option>
                </Select>
              </div>
              <div>
                <label className="text-[9px] text-[var(--color-muted)] block mb-1">Stroke Width</label>
                <Select
                  value={strokeWidth}
                  onChange={(e) => setStrokeWidth(e.target.value)}
                  className="h-7 text-xs px-1.5"
                >
                  <option value="0">None</option>
                  <option value="2">2px Outline</option>
                  <option value="4">4px Heavy</option>
                </Select>
              </div>
            </div>

            {/* Random Flip Option */}
            <div className="flex items-center justify-between p-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)]">
              <div className="flex items-center gap-2">
                <Shuffle className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text)] block">Random Flip Angle</span>
                  <span className="text-[9px] text-[var(--color-muted)]">Randomly flips +{rotationAngle}° and -{rotationAngle}°</span>
                </div>
              </div>
              <Switch
                checked={randomFlip}
                onCheckedChange={setRandomFlip}
              />
            </div>

            {/* Auto-Detect Emphasis Toggle */}
            <div className="flex items-center justify-between p-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-line)]">
              <div>
                <span className="text-xs font-semibold text-[var(--color-text)] block">Auto-Detect Emphasis</span>
                <span className="text-[9px] text-[var(--color-muted)]">Color keywords & punchlines</span>
              </div>
              <Switch
                checked={autoEmphasis}
                onCheckedChange={setAutoEmphasis}
              />
            </div>

            {/* Interactive Subtitle Canvas Display Preview */}
            <div className="p-3 rounded-xl bg-black border border-[var(--color-line)] flex flex-col items-center justify-center overflow-hidden min-h-[90px] relative select-none">
              <span className="text-[9px] uppercase tracking-wider text-[var(--color-muted)] absolute top-1.5 left-2.5 font-mono">
                Interactive Subtitle Canvas
              </span>
              <div
                className={`text-base font-black tracking-wide uppercase transition-all duration-300 inline-block mt-2 ${
                  bgMode === 'phrase' ? 'bg-black/80 px-3 py-1.5 rounded-xl border border-white/20' : ''
                }`}
                style={{
                  fontFamily: fontFamily,
                  transform: `rotate(${effectiveRotationAngle}deg)`,
                  color: primaryColor,
                  textShadow: `
                    -${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},
                    -${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},
                     0px 3px 6px rgba(0,0,0,0.8)
                  `
                }}
              >
                <span>I WORKED AT </span>
                <span
                  className={`inline-block transform scale-105 px-1.5 py-0.5 rounded-lg ${
                    bgMode === 'word' || (bgMode === 'emphasis' && autoEmphasis)
                      ? 'bg-black/80 border border-white/25 shadow-lg'
                      : ''
                  }`}
                  style={{
                    color: resolvedActiveColor,
                    textShadow: `
                      -${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},
                      -${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},
                       0px 3px 6px rgba(0,0,0,0.9)
                    `
                  }}
                >
                  SEVEN 11
                </span>
                <span> TO SURVIVE</span>
              </div>
            </div>
          </div>

          {/* Background Music & FX */}
          <div className="p-3.5 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-2 shadow-sm text-xs">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-[var(--color-text)]">Background Music & FX</span>
              <span
                className="text-[10px] text-[var(--color-muted)] hover:text-[var(--color-accent)] cursor-pointer"
                onClick={onOpenOstModal}
              >
                + Add Music
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Select
                value={ostSelect}
                onChange={(e) => setOstSelect(e.target.value)}
                className="h-7 text-xs"
              >
                <option value="none">No Background OST</option>
                <option value="electronic">Viral Tech Phonk</option>
                <option value="lofi">Chill Lo-Fi Beat</option>
                <option value="suspense">Dark Suspense Tension</option>
              </Select>
              <Select
                value={musicLevel}
                onChange={(e) => setMusicLevel(parseFloat(e.target.value))}
                className="h-7 text-xs"
              >
                <option value="-18">Auto-Ducking (-18dB)</option>
                <option value="-24">Quiet Background (-24dB)</option>
                <option value="-12">High Energy (-12dB)</option>
              </Select>
            </div>
            <div className="flex items-center justify-between text-[10px] text-[var(--color-muted)] pt-1">
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fxFlash}
                  onChange={(e) => setFxFlash(e.target.checked)}
                  className="accent-[var(--color-accent)]"
                />
                <span>Flash Cut</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fxProgress}
                  onChange={(e) => setFxProgress(e.target.checked)}
                  className="accent-[var(--color-accent)]"
                />
                <span>Progress Bar</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fxZoom}
                  onChange={(e) => setFxZoom(e.target.checked)}
                  className="accent-[var(--color-accent)]"
                />
                <span>Hook Zoom</span>
              </label>
            </div>
          </div>

        </div>

        {/* ========================================================
            CENTER PREVIEW MONITOR (6 cols) - Visual Hero Centerpiece
            ======================================================== */}
        <div className="lg:col-span-6 flex flex-col justify-between space-y-3 min-h-[460px]">
          
          {/* Monitor Header */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <div className="px-2.5 py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-xs font-semibold text-[var(--color-text)] flex items-center gap-1">
                <span>{aspectRatio}</span>
                <span className="text-[9px] text-[var(--color-muted)]">Reel</span>
              </div>
              <div className="px-2.5 py-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-line)] text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Preview</span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-[var(--color-muted)]">
              <span>{currentTimecode}</span>
              <span className="px-1.5 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-line)] text-[10px] text-[var(--color-text)]">
                1080p
              </span>
            </div>
          </div>

          {/* Central Video Player (Visual Centerpiece matching Image 1) */}
          <div className="flex-1 bg-black rounded-3xl border-2 border-[var(--color-line)] overflow-hidden relative shadow-2xl flex items-center justify-center min-h-[380px] max-h-[560px]">
            {/* Aspect Ratio Container */}
            <div className="relative h-full aspect-[9/16] max-w-full bg-neutral-950 flex items-center justify-center overflow-hidden shadow-2xl">
              <video
                ref={videoPlayerRef}
                playsInline
                src={activeClip ? activeClip.file : (videoPath ? `/api/source-video-stream?path=${encodeURIComponent(videoPath)}` : undefined)}
                className="w-full h-full object-cover"
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onTimeUpdate={() => {
                  if (videoPlayerRef.current) {
                    const c = videoPlayerRef.current.currentTime
                    const d = videoPlayerRef.current.duration || 1
                    const cm = Math.floor(c / 60)
                    const cs = Math.floor(c % 60)
                    const dm = Math.floor(d / 60)
                    const ds = Math.floor(d % 60)
                    setCurrentTimecode(
                      `${String(cm).padStart(2, '0')}:${String(cs).padStart(2, '0')} / ${String(dm).padStart(2, '0')}:${String(ds).padStart(2, '0')}`
                    )
                  }
                }}
              />

              {/* Subtitle / Karaoke preview overlay synchronized with style */}
              <div className="absolute bottom-16 inset-x-4 pointer-events-none flex justify-center text-center">
                <div
                  className="px-4 py-1.5 rounded-2xl bg-black/60 backdrop-blur-sm border border-white/10 font-extrabold text-xl tracking-wide uppercase drop-shadow-[0_4px_8px_rgba(0,0,0,0.9)] transition-all duration-300"
                  style={{
                    fontFamily: fontFamily,
                    transform: `rotate(${effectiveRotationAngle}deg)`,
                    color: resolvedActiveColor,
                    textShadow: `
                      -${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px -${strokeWidth}px 0 ${strokeColor},
                      -${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},  ${strokeWidth}px  ${strokeWidth}px 0 ${strokeColor},
                       0px 4px 8px rgba(0,0,0,0.95)
                    `
                  }}
                >
                  <span>WHAT?!</span>
                </div>
              </div>
            </div>

            {/* Floating Viral Hook Score Badge */}
            <div className="absolute top-4 left-4 z-10">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-accent)] bg-[var(--color-accent-soft)] px-2.5 py-1 rounded-full border border-[var(--color-accent)]/40 backdrop-blur-md">
                Viral Score: {activeClip ? activeClip.score : "98.5"}
              </span>
            </div>
          </div>

          {/* Transport Control Bar */}
          <div className="p-3 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] flex items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (videoPlayerRef.current) videoPlayerRef.current.currentTime -= 5
                }}
                className="h-8 px-2.5 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs"
                title="Rewind 5s"
              >
                ⏪ -5s
              </Button>
              <Button
                size="sm"
                onClick={togglePlay}
                className="h-8 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 shadow"
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                <span>{isPlaying ? "Pause" : "Play"}</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (videoPlayerRef.current) videoPlayerRef.current.currentTime += 5
                }}
                className="h-8 px-2.5 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs"
                title="Forward 5s"
              >
                +5s ⏩
              </Button>
            </div>

            {/* Playhead Scrubber */}
            <div className="flex-1 mx-2">
              <Slider
                min={0}
                max={100}
                defaultValue={35}
                onValueChange={(val) => {
                  if (videoPlayerRef.current && videoPlayerRef.current.duration) {
                    videoPlayerRef.current.currentTime = (val / 100) * videoPlayerRef.current.duration
                  }
                }}
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleMute}
                className="h-8 w-8 rounded-xl text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]"
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  if (videoPlayerRef.current && videoPlayerRef.current.requestFullscreen) {
                    videoPlayerRef.current.requestFullscreen()
                  }
                }}
                className="h-8 w-8 rounded-xl text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]"
              >
                <Maximize2 className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Clip Info Card */}
          <div className="p-3 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] flex items-center justify-between text-xs">
            <div className="min-w-0 flex-1 pr-3">
              <h4 className="font-bold text-[var(--color-text)] truncate">
                {activeClip ? activeClip.title : "Select a clip to preview"}
              </h4>
              <p className="text-[11px] text-[var(--color-muted)] italic truncate mt-0.5">
                {activeClip ? `"${activeClip.excerpt}"` : "Viral excerpts and spoken hooks will appear here."}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[10px] font-mono text-[var(--color-muted)] hidden sm:inline">
                Track: {activeClip ? activeClip.music : "None"}
              </span>
              {activeClip && (
                <a
                  href={activeClip.file}
                  download={`${activeClip.clip_id}.mp4`}
                  className="px-3 py-1.5 rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] text-xs font-medium hover:border-[var(--color-accent)]"
                >
                  Download
                </a>
              )}
              <Button
                size="sm"
                onClick={onOpenYouTubeModal}
                className="h-7 px-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-medium text-xs flex items-center gap-1 shadow"
              >
                <Share2 className="w-3 h-3" />
                <span>Post</span>
              </Button>
            </div>
          </div>

        </div>

        {/* ========================================================
            RIGHT COLUMN (3 cols): Action Buttons, Progress, Engine Logs
            ======================================================== */}
        <div className="lg:col-span-3 space-y-3.5 flex flex-col justify-start">
          
          {/* Action Buttons: Generate & Shuffle */}
          <div className="space-y-2">
            <Button
              onClick={() => onTriggerClipping(false)}
              disabled={generationState.status === 'processing'}
              className="w-full h-12 rounded-2xl bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20"
            >
              <Sparkles className="w-4 h-4 fill-current" />
              <span>Generate {clipCount} Clips</span>
            </Button>

            <Button
              onClick={() => onTriggerClipping(true)}
              disabled={generationState.status === 'processing'}
              variant="outline"
              className="w-full h-9 rounded-2xl border-[var(--color-line)] bg-[var(--color-surface)] hover:bg-[var(--color-card)] text-[var(--color-text)] text-xs font-semibold flex items-center justify-center gap-1.5 transition"
            >
              <Shuffle className="w-3.5 h-3.5 text-[var(--color-accent)]" />
              <span>Shuffle &amp; Generate New Clips</span>
            </Button>
          </div>

          {/* Generation Progress Card */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-3.5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--color-text)]">Generation Progress</span>
              <span className="text-sm font-mono font-bold text-[var(--color-accent)]">{generationState.progress}%</span>
            </div>

            {/* Main gradient progress bar */}
            <div className="w-full bg-[var(--color-surface)] h-2.5 rounded-full overflow-hidden border border-[var(--color-line)]">
              <div
                className="bg-gradient-to-r from-purple-500 via-indigo-500 to-[var(--color-accent)] h-full transition-all duration-300"
                style={{ width: `${generationState.progress}%` }}
              />
            </div>

            <p className="text-xs font-medium text-[var(--color-muted)]">{generationState.stage}</p>

            {/* 5-Stage Stepper */}
            <div className="space-y-2 pt-1 border-t border-[var(--color-line)] text-xs">
              {[
                { stage: "Analyzing Video", threshold: 15 },
                { stage: "Transcribing Audio", threshold: 35 },
                { stage: "Detecting Moments", threshold: 60 },
                { stage: "Generating Clips", threshold: 85 },
                { stage: "Rendering & Finalizing", threshold: 100 },
              ].map((step, idx) => {
                const isDone = generationState.progress >= step.threshold
                const isCurrent = !isDone && (idx === 0 || generationState.progress >= [0, 15, 35, 60, 85][idx])
                return (
                  <div key={step.stage} className="flex items-center gap-2.5">
                    <span
                      className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        isDone
                          ? "bg-emerald-500/20 text-emerald-400"
                          : isCurrent
                          ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] animate-pulse"
                          : "bg-[var(--color-surface)] text-[var(--color-muted)]"
                      }`}
                    >
                      {isDone ? (
                        <Check className="w-3 h-3 text-emerald-400" />
                      ) : isCurrent ? (
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-muted)]/40" />
                      )}
                    </span>
                    <span
                      className={`${
                        isCurrent
                          ? "text-[var(--color-text)] font-semibold"
                          : "text-[var(--color-muted)]"
                      }`}
                    >
                      {step.stage}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Engine Logs Terminal */}
          <div className="p-4 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-2.5 shadow-sm flex-1 flex flex-col min-h-[160px]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-xs font-bold text-[var(--color-text)]">Engine Logs</span>
              </div>
              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                Live
              </span>
            </div>
            <div className="flex-1 bg-black/60 rounded-xl p-3 border border-[var(--color-line)] overflow-y-auto custom-scrollbar font-mono text-[11px] text-[var(--color-muted)] space-y-1 select-text">
              <div className="text-emerald-400 font-semibold">[Ready] openClip AI Engine initialized.</div>
              {generationState.logs && generationState.logs.length > 0 ? (
                generationState.logs.map((log, i) => (
                  <div key={i} className="leading-snug">{log}</div>
                ))
              ) : (
                <div>Awaiting media input...</div>
              )}
            </div>
          </div>

        </div>

      </div>

      {/* ========================================================
          BOTTOM PANEL: Generated Clips & Timeline Gallery
          ======================================================== */}
      <div className="h-44 bg-[var(--color-card)] border border-[var(--color-line)] rounded-2xl p-3 flex flex-col justify-between shadow-sm shrink-0">
        
        {/* Header Bar */}
        <div className="flex items-center justify-between pb-2 border-b border-[var(--color-line)]">
          <div className="flex items-center gap-3">
            <button className="text-xs font-bold text-[var(--color-text)] flex items-center gap-1.5 pb-0.5 border-b-2 border-[var(--color-accent)]">
              <span>Generated Clips</span>
              <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-bold">
                {galleryProjects[activeProjectIdx]?.clips?.length || 0}
              </span>
            </button>
            <span className="text-xs font-medium text-[var(--color-muted)] cursor-pointer hover:text-[var(--color-text)]">
              Timeline Mode
            </span>

            {/* Folder selection pills */}
            {galleryProjects.length > 0 && (
              <div className="hidden sm:flex items-center gap-1.5 pl-2 border-l border-[var(--color-line)] overflow-x-auto max-w-sm custom-scrollbar">
                {galleryProjects.map((p, idx) => (
                  <button
                    key={p.folder_name}
                    onClick={() => setActiveProjectIdx(idx)}
                    className={`px-2.5 py-1 rounded-xl text-[10px] font-medium border transition shrink-0 flex items-center gap-1.5 ${
                      idx === activeProjectIdx
                        ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)] font-bold shadow-xs"
                        : "bg-[var(--color-surface)] border-[var(--color-line)] text-[var(--color-muted)] hover:text-[var(--color-text)]"
                    }`}
                  >
                    <Folder className="w-3 h-3 text-[var(--color-accent)]" />
                    <span>{p.display_name} ({p.clip_count})</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Action buttons: Refresh, Export All */}
          <div className="flex items-center gap-2 text-xs">
            <Button
              variant="outline"
              size="sm"
              onClick={onRefreshGallery}
              className="h-7 px-2.5 rounded-xl border-[var(--color-line)] bg-[var(--color-surface)] text-xs text-[var(--color-muted)] hover:text-[var(--color-text)]"
              title="Refresh Gallery"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
            <Button
              size="sm"
              onClick={onOpenYouTubeModal}
              className="h-7 px-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow"
            >
              <span>Export All ↗</span>
            </Button>
          </div>
        </div>

        {/* Horizontal Strip of Generated Clips */}
        <div className="flex-1 flex items-center gap-3 overflow-x-auto pt-2 custom-scrollbar">
          {galleryProjects[activeProjectIdx]?.clips?.map((clip, cIdx) => {
            const isSelected = activeClip?.file === clip.file
            return (
              <div
                key={clip.id}
                onClick={() => setActiveClip(clip)}
                className={`shrink-0 w-40 h-28 rounded-xl bg-[var(--color-surface)] border p-2 flex flex-col justify-between cursor-pointer transition relative group overflow-hidden ${
                  isSelected
                    ? "border-[var(--color-accent)] ring-1 ring-[var(--color-accent)] shadow-md shadow-[var(--color-accent-glow)]"
                    : "border-[var(--color-line)] hover:border-[var(--color-accent)]/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-[var(--color-accent)]">Clip {clip.id}</span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-black/60 text-white">
                    {clip.duration}s
                  </span>
                </div>
                <div className="text-xs font-semibold text-[var(--color-text)] truncate">
                  {clip.title}
                </div>
                <div className="flex items-center justify-between text-[9px] text-[var(--color-muted)]">
                  <span>Score: {clip.score}</span>
                  <span className="text-emerald-400 font-semibold">1080p</span>
                </div>
              </div>
            )
          })}

          {/* Add to project card */}
          <div
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
            className="shrink-0 w-36 h-28 rounded-xl bg-[var(--color-surface)] border border-dashed border-[var(--color-line)] p-2 flex flex-col justify-center items-center text-center cursor-pointer hover:border-[var(--color-accent)] transition"
          >
            <span className="text-xl text-[var(--color-accent)] mb-1">+</span>
            <span className="text-xs font-semibold text-[var(--color-text)]">Add Video</span>
            <span className="text-[10px] text-[var(--color-muted)]">Upload source</span>
          </div>
        </div>

      </div>

    </div>
  )
}
