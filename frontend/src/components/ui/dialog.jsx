import * as React from "react"
import { cn } from "@/lib/utils"

function Dialog({ open, onOpenChange, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in-0 duration-200">
      <div 
        className="fixed inset-0" 
        onClick={() => onOpenChange && onOpenChange(false)} 
      />
      <div className="relative z-10 w-full max-h-[92vh] overflow-y-auto">
        {children}
      </div>
    </div>
  )
}

function DialogContent({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "relative mx-auto rounded-3xl border border-[var(--color-line,#293244)] bg-[var(--color-card,#141821)] p-6 shadow-2xl text-[var(--color-text,#F1F5F9)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

function DialogHeader({ className, children, ...props }) {
  return (
    <div
      className={cn("flex items-center justify-between pb-3 border-b border-[var(--color-line,#293244)]", className)}
      {...props}
    >
      {children}
    </div>
  )
}

function DialogTitle({ className, children, ...props }) {
  return (
    <h3
      className={cn("text-base font-bold text-[var(--color-text,#F1F5F9)] flex items-center gap-2", className)}
      {...props}
    >
      {children}
    </h3>
  )
}

function DialogFooter({ className, children, ...props }) {
  return (
    <div
      className={cn("flex justify-end gap-2 pt-3 border-t border-[var(--color-line,#293244)]", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter }
