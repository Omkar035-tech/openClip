import * as React from "react"
import { Header } from "@/components/Header"
import { Sidebar } from "@/components/Sidebar"
import { ShortsStudio } from "@/components/ShortsStudio"
import { LongFormStudio } from "@/components/LongFormStudio"
import { 
  NewProjectModal, 
  CaptionPlaygroundModal, 
  LocalVideosModal, 
  YouTubeModal, 
  SettingsSidebar 
} from "@/components/Modals"

export default function App() {
  // Theme state
  const [colorTheme, setColorTheme] = React.useState(
    localStorage.getItem('openclip_color_theme') || 'midnight'
  )
  const [themeMode, setThemeMode] = React.useState(
    localStorage.getItem('openclip_mode') || 'dark'
  )

  // Navigation tab
  const [activeTab, setActiveTab] = React.useState('shorts') // 'shorts', 'longform', 'dashboard', etc.
  const [searchQuery, setSearchQuery] = React.useState('')

  // Engine Architecture
  const [engineArch, setEngineArch] = React.useState('openclip_standard')

  // Shorts Configuration State
  const [videoPath, setVideoPath] = React.useState('')
  const [sourceFileName, setSourceFileName] = React.useState('')
  const [aspectRatio, setAspectRatio] = React.useState('9:16')
  const [clipCount, setClipCount] = React.useState(5)
  const [maxDuration, setMaxDuration] = React.useState(60)
  const [fallbackLayout, setFallbackLayout] = React.useState('face_centered')
  const [webcamSplit, setWebcamSplit] = React.useState(false)
  const [camPlacement, setCamPlacement] = React.useState('top')
  const [streamerMode, setStreamerMode] = React.useState('auto')
  const [manualCamBox, setManualCamBox] = React.useState([0, 60, 380, 260])

  // Caption Styling State
  const [fontFamily, setFontFamily] = React.useState('Montserrat')
  const [fontSize, setFontSize] = React.useState(68)
  const [primaryColor, setPrimaryColor] = React.useState('#FFFFFF')
  const [activeColor, setActiveColor] = React.useState('#FFD400')
  const [emphasisColor, setEmphasisColor] = React.useState('#00FFCC')
  const [strokeColor, setStrokeColor] = React.useState('#000000')
  const [rotationAngle, setRotationAngle] = React.useState(0)
  const [randomFlip, setRandomFlip] = React.useState(false)
  const [bgMode, setBgMode] = React.useState('none')
  const [strokeWidth, setStrokeWidth] = React.useState('2')
  const [autoEmphasis, setAutoEmphasis] = React.useState(true)

  // Music & Effects
  const [ostSelect, setOstSelect] = React.useState('electronic')
  const [musicLevel, setMusicLevel] = React.useState(-18)
  const [fxFlash, setFxFlash] = React.useState(true)
  const [fxProgress, setFxProgress] = React.useState(true)
  const [fxZoom, setFxZoom] = React.useState(true)

  // Engine Pipeline & Generation State
  const [generationState, setGenerationState] = React.useState({
    status: 'idle',
    stage: 'Ready for input',
    progress: 0,
    logs: []
  })

  // Gallery State
  const [galleryProjects, setGalleryProjects] = React.useState([])
  const [activeProjectIdx, setActiveProjectIdx] = React.useState(0)
  const [activeClip, setActiveClip] = React.useState(null)

  // Modal open states
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false)
  const [isNewProjectOpen, setIsNewProjectOpen] = React.useState(false)
  const [isCaptionPlaygroundOpen, setIsCaptionPlaygroundOpen] = React.useState(false)
  const [isLocalVideosOpen, setIsLocalVideosOpen] = React.useState(false)
  const [isYouTubeOpen, setIsYouTubeOpen] = React.useState(false)

  // Sync colorTheme and themeMode to documentElement
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', colorTheme)
    localStorage.setItem('openclip_color_theme', colorTheme)
  }, [colorTheme])

  React.useEffect(() => {
    if (themeMode === 'dark') {
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    } else {
      document.documentElement.classList.remove('dark')
      document.documentElement.classList.add('light')
    }
    localStorage.setItem('openclip_mode', themeMode)
  }, [themeMode])

  // Load gallery folders on mount
  const loadGallery = async () => {
    try {
      const res = await fetch('/api/gallery')
      const data = await res.json()
      const projects = data.projects || []
      setGalleryProjects(projects)
      if (projects.length > 0 && projects[0].clips && projects[0].clips.length > 0) {
        setActiveClip(projects[0].clips[0])
      }
    } catch (e) {
      console.error(e)
    }
  }

  // Load latest source video if available
  const loadDefaultVideo = async () => {
    try {
      const res = await fetch('/api/local-videos')
      const data = await res.json()
      if (data.videos && data.videos.length > 0) {
        const v = data.videos[0]
        setVideoPath(v.path)
        setSourceFileName(v.name)
      }
    } catch (e) {
      console.error(e)
    }
  }

  React.useEffect(() => {
    loadGallery()
    loadDefaultVideo()
  }, [])

  // Start Generation Dispatcher
  const triggerClipping = async (isShuffle = false) => {
    if (!videoPath) {
      alert("Please select or upload a source video first.")
      return
    }

    setGenerationState(prev => ({
      ...prev,
      status: 'processing',
      stage: 'Dispatching generation...',
      progress: 5
    }))

    const payload = {
      video_path: videoPath,
      shuffle: isShuffle,
      layout: webcamSplit ? 'streamer_split' : fallbackLayout,
      aspect_ratio: aspectRatio,
      streamer_layout_enabled: webcamSplit,
      cam_placement: camPlacement,
      streamer_mode: streamerMode,
      manual_cam_box: streamerMode === 'manual' ? manualCamBox : null,
      engine_architecture: engineArch,
      n_clips: clipCount,
      max_duration: maxDuration,
      font_file: fontFamily,
      font_size: fontSize,
      primary_color: primaryColor,
      active_color: activeColor,
      emphasis_color: emphasisColor,
      stroke_color: strokeColor,
      rotation_angle: rotationAngle,
      random_flip: randomFlip,
      bg_mode: bgMode,
      auto_detect_emphasis: autoEmphasis,
      selected_track_id: ostSelect,
      music_level_db: musicLevel,
      effects_flash: fxFlash,
      effects_progress: fxProgress,
      hook_zoom: fxZoom ? 1.12 : 1.0
    }

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      await res.json()
      pollStatus()
    } catch (err) {
      alert("Failed to start generation: " + err)
      setGenerationState(prev => ({ ...prev, status: 'error', stage: 'Failed to start' }))
    }
  }

  // Status Poller
  const pollStatus = () => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/status')
        const status = await res.json()

        setGenerationState({
          status: status.status,
          stage: status.stage,
          progress: status.progress,
          logs: status.logs || []
        })

        if (status.status === 'completed' || status.status === 'error') {
          clearInterval(interval)
          if (status.status === 'completed') {
            loadGallery()
          }
        }
      } catch (e) {
        console.error(e)
      }
    }, 1000)
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)] font-sans">
      {/* Fixed Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenCaptionPlayground={() => setIsCaptionPlaygroundOpen(true)}
        onOpenOstModal={() => alert("Background OST library ready.")}
        onOpenYouTubeModal={() => setIsYouTubeOpen(true)}
        onOpenProjectsModal={() => setIsNewProjectOpen(true)}
      />

      {/* Main Workspace Column */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Compact Top Navigation Header */}
        <Header
          colorTheme={colorTheme}
          setColorTheme={setColorTheme}
          themeMode={themeMode}
          setThemeMode={setThemeMode}
          engineArch={engineArch}
          onOpenSettings={() => setIsSettingsOpen(true)}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
        />

        {/* Studio Body: Shorts Studio or Long-Form Studio */}
        {activeTab === 'longform' ? (
          <LongFormStudio
            onOpenNewProject={() => setIsNewProjectOpen(true)}
            onOpenCaptionPlayground={() => setIsCaptionPlaygroundOpen(true)}
          />
        ) : (
          <ShortsStudio
            videoPath={videoPath}
            setVideoPath={setVideoPath}
            sourceFileName={sourceFileName}
            setSourceFileName={setSourceFileName}
            onOpenLocalVideos={() => setIsLocalVideosOpen(true)}
            aspectRatio={aspectRatio}
            setAspectRatio={setAspectRatio}
            clipCount={clipCount}
            setClipCount={setClipCount}
            maxDuration={maxDuration}
            setMaxDuration={setMaxDuration}
            fallbackLayout={fallbackLayout}
            setFallbackLayout={setFallbackLayout}
            webcamSplit={webcamSplit}
            setWebcamSplit={setWebcamSplit}
            camPlacement={camPlacement}
            setCamPlacement={setCamPlacement}
            streamerMode={streamerMode}
            setStreamerMode={setStreamerMode}
            manualCamBox={manualCamBox}
            setManualCamBox={setManualCamBox}
            fontFamily={fontFamily}
            setFontFamily={setFontFamily}
            fontSize={fontSize}
            setFontSize={setFontSize}
            primaryColor={primaryColor}
            setPrimaryColor={setPrimaryColor}
            activeColor={activeColor}
            setActiveColor={setActiveColor}
            emphasisColor={emphasisColor}
            setEmphasisColor={setEmphasisColor}
            strokeColor={strokeColor}
            setStrokeColor={setStrokeColor}
            rotationAngle={rotationAngle}
            setRotationAngle={setRotationAngle}
            randomFlip={randomFlip}
            setRandomFlip={setRandomFlip}
            bgMode={bgMode}
            setBgMode={setBgMode}
            strokeWidth={strokeWidth}
            setStrokeWidth={setStrokeWidth}
            autoEmphasis={autoEmphasis}
            setAutoEmphasis={setAutoEmphasis}
            ostSelect={ostSelect}
            setOstSelect={setOstSelect}
            musicLevel={musicLevel}
            setMusicLevel={setMusicLevel}
            fxFlash={fxFlash}
            setFxFlash={setFxFlash}
            fxProgress={fxProgress}
            setFxProgress={setFxProgress}
            fxZoom={fxZoom}
            setFxZoom={setFxZoom}
            onTriggerClipping={triggerClipping}
            generationState={generationState}
            onOpenCaptionPlayground={() => setIsCaptionPlaygroundOpen(true)}
            onOpenOstModal={() => alert("Background OST selection ready.")}
            onOpenYouTubeModal={() => setIsYouTubeOpen(true)}
            galleryProjects={galleryProjects}
            activeProjectIdx={activeProjectIdx}
            setActiveProjectIdx={setActiveProjectIdx}
            activeClip={activeClip}
            setActiveClip={setActiveClip}
            onRefreshGallery={loadGallery}
          />
        )}
      </div>

      {/* Slide-Over and Dialog Modals */}
      <SettingsSidebar
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        engineArch={engineArch}
        setEngineArch={setEngineArch}
      />

      <NewProjectModal
        open={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
        onSubmitSuccess={() => setActiveTab('longform')}
      />

      <CaptionPlaygroundModal
        open={isCaptionPlaygroundOpen}
        onClose={() => setIsCaptionPlaygroundOpen(false)}
        currentStyle={{
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
        }}
        onApplyStyle={(style) => {
          setFontFamily(style.fontFamily)
          setFontSize(style.fontSize)
          setRotationAngle(style.rotationAngle)
          if (style.randomFlip !== undefined) setRandomFlip(style.randomFlip)
          setPrimaryColor(style.primaryColor)
          setActiveColor(style.activeColor)
          setEmphasisColor(style.emphasisColor)
          setStrokeColor(style.strokeColor)
          setStrokeWidth(style.strokeWidth)
          setBgMode(style.bgMode)
        }}
      />

      <LocalVideosModal
        open={isLocalVideosOpen}
        onClose={() => setIsLocalVideosOpen(false)}
        onSelectVideo={(path, name) => {
          setVideoPath(path)
          setSourceFileName(name)
        }}
      />

      <YouTubeModal
        open={isYouTubeOpen}
        onClose={() => setIsYouTubeOpen(false)}
        clip={activeClip}
      />
    </div>
  )
}
