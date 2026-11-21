import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent text-sm font-semibold whitespace-nowrap outline-none select-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "rounded-[28px] bg-brand border-[5px] border-[#e1e1f5] dark:border-[#2a3266] text-white shadow-[inset_0_-1px_3px_0px_rgba(0,0,0,0.35)] dark:shadow-[inset_0_-1px_3px_0px_rgba(0,0,0,0.6)] font-display font-bold transition-all duration-400 ease-[cubic-bezier(0.68,-0.55,0.27,2.5)] hover:scale-105 hover:bg-brand hover:border-[#ebebfa] dark:hover:border-[#374185] hover:shadow-[inset_0_-2px_4px_0px_rgba(0,0,0,0.35)] dark:hover:shadow-[inset_0_-2px_4px_0px_rgba(0,0,0,0.7)] active:scale-95 active:shadow-[inset_0_3px_6px_0px_rgba(0,0,0,0.5)] dark:active:shadow-[inset_0_3px_6px_0px_rgba(0,0,0,0.8)] active:border-[#d6d6f0] dark:active:border-[#202752]",
        gradient:
          "bg-gradient-to-br from-violet-600 to-blue-600 text-white shadow-soft hover:brightness-105 active:shadow-press transition-all active:not-aria-[haspopup]:translate-y-px",
        outline:
          "bg-canvas text-ink shadow-soft hover:text-ink aria-expanded:shadow-press active:shadow-press transition-all active:not-aria-[haspopup]:translate-y-px",
        secondary:
          "bg-canvas text-ink shadow-soft aria-expanded:shadow-press active:shadow-press transition-all active:not-aria-[haspopup]:translate-y-px",
        ghost:
          "text-ink-muted hover:bg-hairline hover:text-ink aria-expanded:bg-hairline aria-expanded:text-ink transition-all active:not-aria-[haspopup]:translate-y-px",
        destructive:
          "bg-canvas text-[var(--color-danger)] shadow-soft hover:bg-[var(--color-danger-bg)] active:shadow-press transition-all active:not-aria-[haspopup]:translate-y-px",
        link: "text-[var(--color-primary)] underline-offset-4 hover:underline transition-all",
      },
      size: {
        default:
          "h-9 gap-1.5 px-4 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        xs: "h-7 gap-1 px-3 text-xs border-[2px] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1 px-3 text-[0.8rem] border-[2.5px] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-10 gap-1.5 px-5 has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4",
        icon: "size-9",
        "icon-xs":
          "size-7 border-[2px] [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8 border-[2.5px]",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
