import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { Check, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

const SelectRoot = SelectPrimitive.Root
const SelectGroup = SelectPrimitive.Group
const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-9 w-full items-center justify-between rounded-xl border border-[var(--color-line,#293244)] bg-[var(--color-surface,#1D2430)] px-3 py-1.5 text-xs text-[var(--color-text,#F1F5F9)] shadow-xs ring-offset-background placeholder:text-[var(--color-muted,#929BAA)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent,#8B5CF6)] disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1 cursor-pointer",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectScrollUpButton = React.forwardRef(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollUpButton
    ref={ref}
    className={cn("flex cursor-default items-center justify-center py-1", className)}
    {...props}
  >
    <ChevronUp className="h-4 w-4" />
  </SelectPrimitive.ScrollUpButton>
))
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName

const SelectScrollDownButton = React.forwardRef(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollDownButton
    ref={ref}
    className={cn("flex cursor-default items-center justify-center py-1", className)}
    {...props}
  >
    <ChevronDown className="h-4 w-4" />
  </SelectPrimitive.ScrollDownButton>
))
SelectScrollDownButton.displayName = SelectPrimitive.ScrollDownButton.displayName

const SelectContent = React.forwardRef(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        "relative z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-xl border border-[var(--color-line,#293244)] bg-[var(--color-card,#141821)] text-[var(--color-text,#F1F5F9)] shadow-2xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        position === "popper" &&
          "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
        className
      )}
      position={position}
      {...props}
    >
      <SelectScrollUpButton />
      <SelectPrimitive.Viewport
        className={cn(
          "p-1",
          position === "popper" &&
            "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
      <SelectScrollDownButton />
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
))
SelectContent.displayName = SelectPrimitive.Content.displayName

const SelectLabel = React.forwardRef(({ className, ...props }, ref) => (
  <SelectPrimitive.Label
    ref={ref}
    className={cn("px-2 py-1.5 text-[10px] font-semibold text-[var(--color-muted,#929BAA)] uppercase", className)}
    {...props}
  />
))
SelectLabel.displayName = SelectPrimitive.Label.displayName

const SelectItem = React.forwardRef(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-pointer select-none items-center rounded-lg py-1.5 pl-2 pr-8 text-xs outline-none focus:bg-[var(--color-surface,#1D2430)] focus:text-[var(--color-text,#F1F5F9)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4 text-[var(--color-accent,#8B5CF6)]" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

const SelectSeparator = React.forwardRef(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator
    ref={ref}
    className={cn("-mx-1 my-1 h-px bg-[var(--color-line,#293244)]", className)}
    {...props}
  />
))
SelectSeparator.displayName = SelectPrimitive.Separator.displayName

/**
 * Universal Select: works both as a direct wrapper around native options
 * AND as official Shadcn Radix compound components.
 */
function Select({ value, onChange, onValueChange, className, children, disabled, ...props }) {
  // If children are standard HTML <option> tags, render styled Select with seamless event binding
  const isOptionChildren = React.Children.toArray(children).every(
    child => React.isValidElement(child) && child.type === 'option'
  )

  if (isOptionChildren) {
    return (
      <div className="relative">
        <select
          value={value}
          disabled={disabled}
          onChange={(e) => {
            if (onChange) onChange(e)
            if (onValueChange) onValueChange(e.target.value)
          }}
          className={cn(
            "flex h-9 w-full appearance-none items-center rounded-xl border border-[var(--color-line,#293244)] bg-[var(--color-surface,#1D2430)] px-3 py-1.5 text-xs text-[var(--color-text,#F1F5F9)] shadow-xs transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--color-accent,#8B5CF6)] disabled:cursor-not-allowed disabled:opacity-50 pr-8 cursor-pointer",
            className
          )}
          {...props}
        >
          {children}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-2.5 flex items-center">
          <ChevronDown className="h-3.5 w-3.5 text-[var(--color-muted,#929BAA)] opacity-70" />
        </div>
      </div>
    )
  }

  // Otherwise, use Radix Select Root
  return (
    <SelectRoot
      value={value}
      onValueChange={(val) => {
        if (onValueChange) onValueChange(val)
        if (onChange) onChange({ target: { value: val } })
      }}
      disabled={disabled}
      {...props}
    >
      {children}
    </SelectRoot>
  )
}

export {
  Select,
  SelectRoot,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
}
