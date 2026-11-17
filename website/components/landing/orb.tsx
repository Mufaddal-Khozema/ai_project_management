import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";

const sizes = {
  sm: { box: "size-10", radius: "3px" },
  md: { box: "size-11", radius: "3px" },
  lg: { box: "size-16", radius: "5px" },
  xl: { box: "size-28", radius: "8px" },
  "2xl": { box: "size-36", radius: "11px" },
} as const;

type OrbSize = keyof typeof sizes;

export function Orb({
  size = "md",
  className,
}: {
  size?: OrbSize;
  className?: string;
}) {
  const { box, radius } = sizes[size];

  return (
    <div
      className={cn(
        "grid shrink-0 place-items-center rounded-full bg-canvas shadow-raise",
        box,
        className,
      )}
      style={{ "--r": radius } as CSSProperties}
    >
      <span className="relative block aspect-square w-4/5 rounded-full bg-gradient-to-br from-pink-200 via-pink-500 to-violet-500 shadow-inner">
        <span
          className="absolute inset-0 flex items-center justify-center gap-2"
          style={{
            transform:
              "translate(calc(var(--ex, 0) * var(--r)), calc(var(--ey, 0) * var(--r)))",
          }}
        >
          <span className="h-1/4 w-1/6 rounded-full bg-white animate-orb-blink" />
          <span className="h-1/4 w-1/6 rounded-full bg-white animate-orb-blink" />
        </span>
      </span>
    </div>
  );
}
