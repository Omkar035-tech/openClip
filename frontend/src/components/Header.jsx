import * as React from "react"
import { Search, Sun, Moon, Sparkles, MessageSquare, HelpCircle, Settings as SettingsIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"

export function Header({
  colorTheme,
  setColorTheme,
  themeMode,
  setThemeMode,
  engineArch,
  onOpenSettings,
  searchQuery,
  setSearchQuery
}) {
  return (
    <header className="h-14 border-b border-[var(--color-line)] bg-[var(--color-sidebar)] px-4 flex items-center justify-between gap-4 z-20 shrink-0">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3 min-w-[200px]">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-purple-500/20">
          <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
            <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11z" />
          </svg>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-extrabold text-sm tracking-tight text-[var(--color-text)]">openClip</span>
            <Badge variant="outline" className="text-[9px] font-mono py-0 px-1 border-[var(--color-line)] text-[var(--color-accent)] bg-[var(--color-accent-soft)]">
              {engineArch === 'wayin_2_0' ? '2.0 Beta' : '1.0 Standard'}
            </Badge>
          </div>
          <span className="text-[10px] text-[var(--color-muted)] font-medium block -mt-0.5">AI Video Clipping Studio</span>
        </div>
      </div>

      {/* Global Search Input */}
      <div className="flex-1 max-w-md hidden md:flex items-center relative">
        <Search className="w-3.5 h-3.5 absolute left-3 text-[var(--color-muted)] pointer-events-none" />
        <Input
          type="text"
          placeholder="Search projects, videos... (Ctrl + K)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 h-8 text-xs bg-[var(--color-surface)] border-[var(--color-line)] text-[var(--color-text)] focus-visible:ring-1 focus-visible:ring-[var(--color-accent)] rounded-xl"
        />
      </div>

      {/* Right Controls: Theme Toggle, Palette Selector, Discord, Settings */}
      <div className="flex items-center gap-2">
        {/* Palette Selector */}
        <div className="hidden sm:flex items-center gap-1 bg-[var(--color-surface)] p-0.5 rounded-xl border border-[var(--color-line)]">
          <Select
            value={colorTheme}
            onChange={(e) => setColorTheme(e.target.value)}
            className="h-7 text-[11px] font-medium border-0 bg-transparent py-0 pl-2 pr-6"
          >
            <option value="midnight">Midnight Studio</option>
            <option value="obsidian">Obsidian Cyan</option>
            <option value="graphite">Graphite Orange</option>
          </Select>
        </div>

        {/* Light / Dark Mode Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
          className="h-8 w-8 rounded-xl text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]"
          title="Toggle light/dark mode"
        >
          {themeMode === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
        </Button>

        {/* Join Discord */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.open('https://discord.gg', '_blank')}
          className="h-8 px-2.5 rounded-xl text-xs font-medium border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-text)] hover:border-[var(--color-accent)] hidden lg:flex items-center gap-1.5"
        >
          <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
          <span>Join Discord</span>
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-xl text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]"
          title="Help & Shortcuts"
        >
          <HelpCircle className="w-4 h-4" />
        </Button>

        {/* Settings Slide-Over Trigger */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenSettings}
          className="h-8 w-8 rounded-xl text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]"
          title="Engine & Hardware Settings"
        >
          <SettingsIcon className="w-4 h-4 text-[var(--color-accent)]" />
        </Button>

        {/* User Avatar */}
        <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shadow">
          O
        </div>
      </div>
    </header>
  )
}
