"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const TIERS = [
  { name: "Admin", allowed: [true, true, true] },
  { name: "Write", allowed: [true, true, false] },
  { name: "Read", allowed: [true, false, false] },
  { name: "None", allowed: [false, false, false] },
];

const ACTIONS = ["Look things up", "Create, update and close", "Delete"];

export function Access() {
  const [tier, setTier] = useState(1);
  const [days, setDays] = useState(2);

  return (
    <div className="grid content-center gap-4 p-6 sm:p-8 lg:border-l lg:border-hairline lg:p-14">
      <div
        role="radiogroup"
        aria-label="Access tier"
        className="flex gap-1.5 rounded-xl bg-canvas p-1.5 shadow-press"
      >
        {TIERS.map((item, index) => (
          <button
            key={item.name}
            type="button"
            role="radio"
            aria-checked={tier === index}
            onClick={() => setTier(index)}
            className={cn(
              "flex-1 rounded-lg px-2.5 py-2.5 text-sm font-semibold text-ink-muted",
              tier === index && "bg-canvas text-ink shadow-soft",
            )}
          >
            {item.name}
          </button>
        ))}
      </div>

      <div className="rounded-2xl bg-canvas px-4 py-1.5 shadow-raise">
        {ACTIONS.map((action, index) => (
          <div
            key={action}
            className={cn(
              "flex items-center gap-3 py-2.5",
              index > 0 && "border-t border-hairline",
            )}
          >
            <span
              className={cn(
                "grid size-6 shrink-0 place-items-center rounded-md text-sm shadow-press",
                TIERS[tier].allowed[index] &&
                  "bg-gradient-to-br from-indigo-600 to-blue-600 text-white shadow-none",
              )}
            >
              {TIERS[tier].allowed[index] ? "✓" : ""}
            </span>
            {action}
          </div>
        ))}
      </div>

      <div className="rounded-2xl bg-canvas px-4 py-4 shadow-raise">
        <label htmlFor="nudges" className="font-semibold">
          Deadline nudges
        </label>
        <input
          id="nudges"
          type="range"
          min={1}
          max={7}
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
          aria-describedby="nudges-value"
          className="mt-3 mb-2 w-full accent-violet-500"
        />
        <div id="nudges-value" className="text-sm text-ink-muted">
          Owners are nudged {days} {days === 1 ? "day" : "days"} before a
          deadline. One reminder per item per day.
        </div>
      </div>
    </div>
  );
}
