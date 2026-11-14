import * as React from "react"
import { cn } from "@/lib/utils"

function Slider({ min = 0, max = 100, step = 1, value, defaultValue, onValueChange, onChange, className, id, ...props }) {
  const currentVal = value !== undefined ? value : defaultValue
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      id={id}
      value={currentVal}
      onChange={(e) => {
        if (onChange) onChange(e)
        if (onValueChange) onValueChange(parseFloat(e.target.value))
      }}
      className={cn(
        "h-1.5 w-full cursor-pointer appearance-none rounded-full bg-[var(--color-surface,#1D2430)] accent-[var(--color-accent,#8B5CF6)] transition-all",
        className
      )}
      {...props}
    />
  )
}

export { Slider }
