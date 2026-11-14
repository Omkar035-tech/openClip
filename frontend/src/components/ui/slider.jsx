import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"
import { cn } from "@/lib/utils"

const Slider = React.forwardRef(({ className, min = 0, max = 100, step = 1, value, defaultValue, onValueChange, ...props }, ref) => {
  // Support both single number and array values for maximum compatibility
  const normalizedValue = React.useMemo(() => {
    if (value !== undefined) return Array.isArray(value) ? value : [value]
    if (defaultValue !== undefined) return Array.isArray(defaultValue) ? defaultValue : [defaultValue]
    return [min]
  }, [value, defaultValue, min])

  const handleValueChange = (vals) => {
    if (onValueChange) {
      // Pass single number if value passed was single number
      if (!Array.isArray(value) && !Array.isArray(defaultValue)) {
        onValueChange(vals[0])
      } else {
        onValueChange(vals)
      }
    }
  }

  return (
    <SliderPrimitive.Root
      ref={ref}
      min={min}
      max={max}
      step={step}
      value={normalizedValue}
      onValueChange={handleValueChange}
      className={cn("relative flex w-full touch-none select-none items-center py-1.5 cursor-pointer", className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-[var(--color-surface,#1D2430)] border border-[var(--color-line,#293244)]/40">
        <SliderPrimitive.Range className="absolute h-full bg-[var(--color-accent,#8B5CF6)]" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb className="block h-4 w-4 rounded-full border-2 border-[var(--color-accent,#8B5CF6)] bg-white shadow-md transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent,#8B5CF6)] disabled:pointer-events-none disabled:opacity-50" />
    </SliderPrimitive.Root>
  )
})
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }
