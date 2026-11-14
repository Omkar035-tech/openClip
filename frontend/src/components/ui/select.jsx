import * as React from "react"
import { cn } from "@/lib/utils"

function Select({ className, children, ...props }) {
  return (
    <select
      data-slot="select"
      className={cn(
        "flex h-9 w-full rounded-xl border border-[var(--color-line,#293244)] bg-[var(--color-surface,#1D2430)] px-3 py-1.5 text-xs text-[var(--color-text,#F1F5F9)] shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent,#8B5CF6)] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </select>
  )
}

export { Select }
