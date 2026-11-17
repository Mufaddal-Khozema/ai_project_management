"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { withAuth } from "@/components/withAuth";
import { useListPlansQuery } from "@/lib/api/@tanstack/react-query.gen";
import type { PlanResponse } from "@/lib/api/types.gen";
import { Orb } from "@/components/landing/orb";
import { Threads } from "@/components/landing/threads";
import { ThemeIcon } from "@/components/landing/icons";
import { useLandingTheme } from "@/components/landing/use-theme";
import { cn } from "@/lib/utils";

function PlansPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentPlanId = searchParams.get("current");
  const { data: plansData, isPending } = useListPlansQuery();
  const plans = plansData?.plans ?? [];
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");
  const { toggleTheme } = useLandingTheme();

  const handleSelect = (planId: string) => {
    router.push(`/payment?plan=${planId}&billing=${billing}`);
  };

  const priceDisplay = (plan: PlanResponse) => {
    if (plan.price_monthly === 0) {
      return (
        <div className="font-display text-4xl font-extrabold tracking-tight">
          Let’s talk
        </div>
      );
    }

    const price =
      billing === "monthly" ? plan.price_monthly : plan.price_yearly;
    const monthlyEquiv =
      billing === "yearly" ? Math.round(plan.price_yearly / 12) : null;

    return (
      <div className="flex flex-col items-center gap-1">
        <div className="font-display text-4xl font-extrabold tracking-tight">
          ${price / 100}{" "}
          <small className="font-body text-sm font-medium text-ink-muted">
            {billing === "monthly" ? "a month" : "a year"}
          </small>
        </div>
        {monthlyEquiv !== null && (
          <span className="text-xs text-ink-muted">
            (${(monthlyEquiv / 100).toFixed(2)}/mo)
          </span>
        )}
      </div>
    );
  };

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossOrigin="anonymous"
      />
      <link
        rel="stylesheet"
        precedence="default"
        href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=Figtree:wght@400;500;600&display=swap"
      />

      <div
        className="landing relative isolate min-h-screen bg-canvas font-body text-ink"
      >
        <Threads className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-60" />

        <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
          <Link href="/" className="flex items-center gap-2.5">
            <Orb />
            <span className="font-display text-lg font-extrabold">
              CoordinaAI
            </span>
          </Link>
          <button
            type="button"
            aria-label="Switch light or dark theme"
            onClick={toggleTheme}
            className="inline-flex size-11 items-center justify-center rounded-xl bg-canvas text-ink shadow-soft active:shadow-press"
          >
            <ThemeIcon />
          </button>
        </header>

        <main className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
          <div className="mb-14 text-center">
            <div className="mb-4 inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-indigo-500 uppercase">
              <span className="size-1.5 rounded-full bg-indigo-500" />
              Pricing
            </div>
            <h1 className="font-display text-4xl font-extrabold tracking-tight sm:text-5xl">
              Choose your coordinates
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-ink-muted">
              Scale at the pace that matches your team’s velocity. No hidden
              fees.
            </p>
          </div>

          <div className="mb-12 flex justify-center">
            <div className="flex gap-1.5 rounded-xl p-1.5 shadow-press">
              <button
                type="button"
                onClick={() => setBilling("monthly")}
                className={cn(
                  "rounded-lg px-5 py-2.5 text-sm font-semibold text-ink-muted transition-all",
                  billing === "monthly" && "bg-canvas text-ink shadow-soft",
                )}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setBilling("yearly")}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold text-ink-muted transition-all",
                  billing === "yearly" && "bg-canvas text-ink shadow-soft",
                )}
              >
                Yearly
                <span className="rounded-md bg-canvas px-1.5 py-0.5 text-xs font-semibold text-ink-muted shadow-soft">
                  Save 20%
                </span>
              </button>
            </div>
          </div>

          {isPending ? (
            <div className="grid gap-5 md:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="grid content-start gap-5 rounded-2xl bg-canvas p-7 shadow-raise"
                >
                  <div className="mx-auto h-4 w-20 animate-pulse rounded bg-hairline" />
                  <div className="mx-auto h-9 w-28 animate-pulse rounded bg-hairline" />
                  <div className="mx-auto h-3 w-48 animate-pulse rounded bg-hairline" />
                  <div className="h-12 w-full animate-pulse rounded-xl bg-hairline" />
                  <div className="grid gap-3 border-t border-hairline pt-5">
                    <div className="h-3 w-full animate-pulse rounded bg-hairline" />
                    <div className="h-3 w-5/6 animate-pulse rounded bg-hairline" />
                    <div className="h-3 w-4/6 animate-pulse rounded bg-hairline" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid items-start gap-5 md:grid-cols-3">
              {plans.map((plan) => {
                const isCurrent = plan.id === currentPlanId;
                const isHighlighted = isCurrent || plan.highlighted;
                const isFree = plan.price_monthly === 0;

                const card = (
                  <div className="grid h-full content-start gap-5 rounded-2xl bg-canvas p-7">
                    <h3 className="text-xs font-semibold tracking-widest text-ink-muted uppercase">
                      {plan.name}
                    </h3>

                    {priceDisplay(plan)}

                    <p className="text-sm leading-relaxed text-ink-muted">
                      {plan.description}
                    </p>

                    <button
                      type="button"
                      disabled={isCurrent}
                      onClick={() => handleSelect(plan.id)}
                      className={cn(
                        "inline-flex h-12 w-full items-center justify-center rounded-xl text-sm font-semibold transition-all",
                        isCurrent
                          ? "cursor-not-allowed bg-hairline text-ink-muted"
                          : plan.highlighted
                            ? "bg-gradient-to-br from-indigo-600 to-blue-600 text-white shadow-soft active:shadow-press"
                            : "bg-canvas text-ink shadow-soft active:shadow-press",
                      )}
                    >
                      {isCurrent
                        ? "Current plan"
                        : isFree
                          ? "Contact Sales"
                          : "Select plan"}
                    </button>

                    <ul className="grid gap-3 border-t border-hairline pt-5">
                      {plan.features.map((feature, idx) => (
                        <li
                          key={idx}
                          className="flex items-start gap-2.5 text-sm"
                        >
                          <span className="mt-0.5 shrink-0 font-extrabold text-violet-500">
                            ✓
                          </span>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                );

                return (
                  <div
                    key={plan.id}
                    className={cn(
                      "relative rounded-2xl",
                      isHighlighted
                        ? "bg-gradient-to-br from-pink-500 via-violet-500 to-blue-500 p-0.5 shadow-raise"
                        : "bg-canvas p-0.5 shadow-raise",
                    )}
                  >
                    {(plan.badge || isCurrent) && (
                      <div className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-canvas px-3 py-1 text-xs font-semibold text-ink shadow-soft">
                        {isCurrent ? "Current plan" : plan.badge}
                      </div>
                    )}
                    {isHighlighted ? (
                      <div className="rounded-2xl bg-canvas">{card}</div>
                    ) : (
                      card
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </>
  );
}

export default withAuth(PlansPage);
