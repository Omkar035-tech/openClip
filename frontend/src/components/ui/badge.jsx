import React from "react"
import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold font-mono transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-accent-soft-var text-accent-var border border-accent-var/30",
        secondary:
          "border-transparent bg-surface-elevated text-muted-var border border-studio",
        destructive:
          "border-transparent bg-rose-500/10 text-rose-400 border border-rose-500/20",
        success:
          "border-transparent bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
        outline: "text-primary-var border-studio",
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
