import React from "react"
import { cn } from "@/lib/utils"

const Tabs = ({ value, onValueChange, className, children }) => {
  return (
    <div className={cn("flex flex-col", className)}>
      {React.Children.map(children, child => {
        if (!child) return null
        return React.cloneElement(child, { activeValue: value, onValueChange })
      })}
    </div>
  )
}

const TabsList = ({ className, activeValue, onValueChange, children }) => (
  <div
    className={cn(
      "inline-flex h-9 items-center justify-center rounded-xl bg-surface-elevated p-1 text-muted-var border border-studio",
      className
    )}
  >
    {React.Children.map(children, child => {
      if (!child) return null
      return React.cloneElement(child, {
        isActive: child.props.value === activeValue,
        onSelect: () => onValueChange && onValueChange(child.props.value),
      })
    })}
  </div>
)

const TabsTrigger = ({ className, value, isActive, onSelect, children }) => (
  <button
    type="button"
    onClick={onSelect}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-lg px-3 py-1 text-xs font-semibold ring-offset-background transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
      isActive
        ? "bg-card-panel text-accent-var shadow-sm"
        : "text-muted-var hover:text-primary-var",
      className
    )}
  >
    {children}
  </button>
)

const TabsContent = ({ value, activeValue, className, children }) => {
  if (value !== activeValue) return null
  return <div className={cn("mt-2 ring-offset-background", className)}>{children}</div>
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
