"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

const TABS = [
  {
    label: "Ask it",
    heading: "Manage work by chatting.",
    lines: [
      "List, search and summarise items.",
      "Create, assign and close them.",
      "Start a standup from chat.",
    ],
  },
  {
    label: "Talk to it",
    heading: "It runs the standup out loud.",
    lines: [
      "No push-to-talk. Interrupt any time.",
      "Everyone gets a turn, late joiners too.",
      "Wraps up at five minutes and posts a summary.",
    ],
  },
  {
    label: "It remembers",
    heading: "Decisions outlive the meeting.",
    lines: [
      "Every meeting saved with its transcript.",
      "Decisions, actions and blockers pulled out.",
      "Changed facts are replaced, never erased.",
    ],
  },
];

const BARS = [
  { day: "M", value: "70%" },
  { day: "T", value: "90%" },
  { day: "W", value: "100%" },
  { day: "T", value: "80%" },
  { day: "F", value: "95%" },
];

export function Features() {
  const [active, setActive] = useState(0);

  return (
    <>
      <div
        role="tablist"
        aria-label="Product features"
        className="mt-5 inline-flex max-w-full gap-1.5 overflow-x-auto rounded-xl p-1.5 shadow-press"
      >
        {TABS.map((tab, index) => (
          <button
            key={tab.label}
            type="button"
            role="tab"
            aria-selected={active === index}
            onClick={() => setActive(index)}
            className={cn(
              "rounded-lg px-4 py-2.5 text-sm font-semibold whitespace-nowrap text-ink-muted",
              active === index && "bg-canvas text-ink shadow-soft",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6 grid overflow-hidden rounded-2xl border border-hairline lg:grid-cols-2">
        <div className="grid content-start gap-3 p-6 lg:p-9">
          <h3 className="font-display text-xl font-extrabold">
            {TABS[active].heading}
          </h3>
          {TABS[active].lines.map((line) => (
            <div
              key={line}
              className="border-t border-hairline py-3.5 text-sm font-semibold"
            >
              {line}
            </div>
          ))}
        </div>

        <div className="relative grid min-h-96 place-items-center p-6 lg:p-9">
          <Image
            src="/landing/a2.jpg"
            alt=""
            fill
            className="object-cover"
            sizes="(min-width: 1024px) 50vw, 100vw"
          />

          <div
            hidden={active !== 0}
            className="relative grid w-full max-w-sm gap-2.5 rounded-2xl bg-canvas p-4 shadow-raise"
          >
            <div className="max-w-sm justify-self-end rounded-xl px-3.5 py-2.5 text-sm shadow-press">
              Create a task to retry failed charges
            </div>
            <div className="max-w-sm rounded-xl px-3.5 py-2.5 text-sm shadow-soft">
              Created PAY-42 in Jira and assigned it to you. The board is
              updated.
              <div className="mt-2 flex justify-between gap-2.5 rounded-lg px-2.5 py-2 text-sm shadow-press">
                <b className="font-semibold">PAY-42 Retry failed charges</b>
                <span className="text-ink-muted">You · To do</span>
              </div>
            </div>
          </div>

          <div
            hidden={active !== 1}
            className="relative grid w-full max-w-sm gap-2.5 rounded-2xl bg-canvas p-4 shadow-raise"
          >
            <div className="flex items-center gap-4">
              <div className="size-28 shrink-0 rounded-full bg-gradient-to-br from-pink-500 via-violet-500 to-blue-500 p-2.5 shadow-press">
                <div className="grid size-full place-items-center rounded-full bg-canvas font-display text-2xl font-extrabold shadow-soft">
                  3:12
                </div>
              </div>
              <div
                role="img"
                aria-label="Standup completeness this week"
                className="flex h-24 flex-1 items-end gap-2.5"
              >
                {BARS.map((bar, index) => (
                  <div
                    key={`${bar.day}-${index}`}
                    className="flex h-full flex-1 flex-col items-center justify-end gap-1"
                  >
                    <i
                      style={{ height: bar.value }}
                      className="block w-full rounded-md bg-gradient-to-t from-indigo-600 to-blue-500"
                    />
                    <small className="text-xs text-ink-muted">{bar.day}</small>
                  </div>
                ))}
              </div>
            </div>
            <b className="font-semibold">Diego is speaking</b>
            <span className="text-sm text-ink-muted">
              Yesterday and today are in. Coordi is asking about blockers.
            </span>
          </div>

          <div
            hidden={active !== 2}
            className="relative grid w-full max-w-sm gap-2.5 rounded-2xl bg-canvas p-4 shadow-raise"
          >
            <div className="rounded-xl px-3.5 py-2.5 text-ink-muted shadow-press">
              deploys
            </div>
            <div>
              We freeze deploys on Fridays.
              <br />
              <span className="text-ink-muted">
                Remembered by Amina · 2 Nov
              </span>
            </div>
            <div className="text-ink-muted line-through">
              Deploys freeze at 3 pm on Fridays.
            </div>
            <span className="inline-block w-fit rounded-md px-2.5 py-0.5 text-sm font-semibold shadow-press">
              Replaced, kept in history
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
