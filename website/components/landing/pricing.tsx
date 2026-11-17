"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const PLANS = [
  {
    name: "Starter",
    month: "49",
    year: "490",
    features: ["Up to 5 teammates", "Daily standups", "1 project"],
    cta: "Start free trial",
  },
  {
    name: "Professional",
    month: "149",
    year: "1,490",
    features: ["Up to 25 teammates", "Weekly reports", "Unlimited projects"],
    cta: "Start free trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    custom: true,
    features: [
      "Unlimited teammates",
      "Custom setup",
      "Everything in Professional",
    ],
    cta: "Contact us",
  },
];

export function Pricing() {
  const [yearly, setYearly] = useState(false);

  return (
    <>
      <h2 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
        Pick a plan.{" "}
        <span className="text-ink-muted">The first 14 days are free.</span>
      </h2>

      <div className="mt-5 flex items-center gap-3">
        <span>Monthly</span>
        <button
          type="button"
          role="switch"
          aria-checked={yearly}
          aria-label="Bill yearly"
          onClick={() => setYearly((value) => !value)}
          className={cn(
            "relative h-7 w-14 rounded-lg shadow-press",
            yearly && "bg-gradient-to-br from-indigo-600 to-blue-600",
          )}
        >
          <span
            className={cn(
              "absolute top-1 left-1 size-5 rounded-md bg-canvas shadow-soft transition-transform",
              yearly && "translate-x-6",
            )}
          />
        </button>
        <span>Yearly, about ten months for twelve</span>
      </div>

      <div className="mt-7 grid gap-5 lg:grid-cols-3">
        {PLANS.map((plan) => {
          const content = (
            <div
              className={cn(
                "grid h-full content-start gap-3.5",
                plan.highlighted
                  ? "rounded-2xl bg-canvas p-6"
                  : "rounded-2xl bg-canvas p-6 shadow-raise",
              )}
            >
              <h3 className="font-display text-xl font-extrabold">
                {plan.name}
              </h3>
              <div className="font-display text-4xl font-extrabold tracking-tight">
                {plan.custom ? (
                  "Let’s talk"
                ) : (
                  <>
                    ${yearly ? plan.year : plan.month}{" "}
                    <small className="font-body text-sm font-medium text-ink-muted">
                      {yearly ? "a year" : "a month"}
                    </small>
                  </>
                )}
              </div>
              <ul className="grid list-none gap-2 p-0">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2.5">
                    <span className="font-extrabold text-violet-500">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>
              {plan.cta === "Contact us" ? (
                <a
                  href="#pricing"
                  className="inline-flex items-center justify-center rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-canvas"
                >
                  {plan.cta}
                </a>
              ) : (
                <Link
                  href="/signup"
                  className={cn(
                    "inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold",
                    plan.highlighted
                      ? "bg-gradient-to-br from-indigo-600 to-blue-600 text-white"
                      : "bg-canvas text-ink shadow-soft active:shadow-press",
                  )}
                >
                  {plan.cta}
                </Link>
              )}
            </div>
          );

          if (!plan.highlighted) {
            return <div key={plan.name}>{content}</div>;
          }

          return (
            <div
              key={plan.name}
              className="rounded-2xl bg-gradient-to-br from-pink-500 via-violet-500 to-blue-500 p-0.5 shadow-raise"
            >
              {content}
            </div>
          );
        })}
      </div>

      <p className="mt-5 text-ink-muted">
        Card on file, nothing charged today. Cancel any time.
      </p>
    </>
  );
}
