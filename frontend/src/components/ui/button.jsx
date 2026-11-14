import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-xs font-semibold ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md hover:from-purple-500 hover:to-indigo-500 hover:shadow-lg shadow-purple-500/20",
        destructive:
          "bg-rose-500 text-white hover:bg-rose-600 shadow-sm",
        outline:
          "border border-[var(--color-line,#293244)] bg-[var(--color-card,#141821)] hover:bg-[var(--color-surface,#1D2430)] text-[var(--color-text,#F1F5F9)]",
        secondary:
          "bg-[var(--color-surface,#1D2430)] text-[var(--color-text,#F1F5F9)] hover:bg-[var(--color-card,#141821)] border border-[var(--color-line,#293244)]",
        ghost: "hover:bg-[var(--color-surface,#1D2430)] text-[var(--color-muted,#929BAA)] hover:text-[var(--color-text,#F1F5F9)]",
        link: "text-[var(--color-accent,#8B5CF6)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-lg px-3",
        lg: "h-11 rounded-2xl px-6 text-sm",
        icon: "h-8 w-8 rounded-xl",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props}
    />
  )
})
Button.displayName = "Button"

export { Button, buttonVariants }
