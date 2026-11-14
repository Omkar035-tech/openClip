import * as React from "react"
import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[var(--color-accent,#8B5CF6)] text-white shadow-xs",
        secondary:
          "border-transparent bg-[var(--color-surface,#1D2430)] text-[var(--color-text,#F1F5F9)] border border-[var(--color-line,#293244)]",
        destructive:
          "border-transparent bg-rose-500 text-white shadow-xs",
        outline: "text-[var(--color-text,#F1F5F9)] border-[var(--color-line,#293244)]",
        success: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400 font-mono",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({ className, variant, ...props }) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
