import * as React from "react"
import { 
  Film, 
  Video, 
  LayoutDashboard, 
  FolderKanban, 
  Type, 
  Music, 
  Share2, 
  Settings as SettingsIcon,
  Zap
} from "lucide-react"
import { Button } from "@/components/ui/button"

export function Sidebar({
  activeTab,
  setActiveTab,
  onOpenSettings,
  onOpenCaptionPlayground,
  onOpenOstModal,
  onOpenYouTubeModal,
  onOpenProjectsModal
}) {
  const navItems = [
    { id: 'shorts', label: 'Shorts Studio', icon: Film, primary: true },
    { id: 'longform', label: 'Long-Form Studio', icon: Video, primary: true },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects', label: 'Projects', icon: FolderKanban, action: onOpenProjectsModal },
    { id: 'captions', label: 'Captions Studio', icon: Type, action: onOpenCaptionPlayground },
    { id: 'audio', label: 'Audio', icon: Music, action: onOpenOstModal },
    { id: 'export', label: 'Export Center', icon: Share2, action: onOpenYouTubeModal },
    { id: 'settings', label: 'Settings', icon: SettingsIcon, action: onOpenSettings },
  ]

  return (
    <aside className="w-56 border-r border-[var(--color-line)] bg-[var(--color-sidebar)] flex flex-col justify-between p-3 shrink-0 select-none z-10">
      <div className="space-y-4">
        {/* Navigation list */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                onClick={() => {
                  if (item.action) {
                    item.action()
                  } else {
                    setActiveTab(item.id)
                  }
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition text-left ${
                  isActive
                    ? "bg-[var(--color-accent)] text-white shadow-md shadow-[var(--color-accent-glow)] font-bold"
                    : "text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]"
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : ""}`} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Bottom Engine Status & Upgrade Card */}
      <div className="space-y-3 pt-3 border-t border-[var(--color-line)]">
        {/* Engine Status Waveform */}
        <div className="p-3 rounded-2xl bg-[var(--color-card)] border border-[var(--color-line)] space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[11px] font-semibold text-[var(--color-text)]">Engine Status</span>
            </div>
            <span className="text-[9px] font-mono text-emerald-400 font-bold">ONLINE</span>
          </div>
          <p className="text-[10px] text-[var(--color-muted)]">Ready for generation</p>
          <div className="h-5 flex items-end gap-0.5 overflow-hidden">
            <span className="flex-1 bg-emerald-500/40 rounded-t h-2 animate-pulse"></span>
            <span className="flex-1 bg-emerald-500/60 rounded-t h-4"></span>
            <span className="flex-1 bg-emerald-500/80 rounded-t h-3 animate-pulse"></span>
            <span className="flex-1 bg-emerald-500 rounded-t h-5"></span>
            <span className="flex-1 bg-emerald-500/70 rounded-t h-2"></span>
            <span className="flex-1 bg-emerald-500/90 rounded-t h-4 animate-pulse"></span>
            <span className="flex-1 bg-emerald-500/50 rounded-t h-3"></span>
            <span className="flex-1 bg-emerald-500/70 rounded-t h-1"></span>
          </div>
        </div>

        {/* Pro Features Upgrade Card */}
        <div className="p-3 rounded-2xl bg-gradient-to-br from-purple-950/40 to-indigo-950/30 border border-purple-500/30 space-y-2 shadow-sm">
          <div className="flex items-center gap-1.5 text-[var(--color-accent)] text-xs font-bold">
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>Pro Features</span>
          </div>
          <p className="text-[10px] text-[var(--color-muted)] leading-snug">
            Unlock 4K exports, unlimited AI virality detection & batch processing.
          </p>
          <Button
            size="sm"
            onClick={onOpenSettings}
            className="w-full h-7 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow"
          >
            Upgrade
          </Button>
        </div>

        <div className="text-[9px] text-[var(--color-muted)] text-center font-mono">
          v1.0.0 • openClip Studio
        </div>
      </div>
    </aside>
  )
}
