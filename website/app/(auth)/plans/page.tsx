"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { withAuth } from "@/components/withAuth";
import { sdk } from "@/lib/api";
import { apiPaymentsPlansPlansHandler } from "@/lib/api/sdk.gen";
import type { PlanResponse } from "@/lib/api/types.gen";

function PlansPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentPlanId = searchParams.get("current");
  const [plans, setPlans] = useState<PlanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    apiPaymentsPlansPlansHandler({ client: sdk, throwOnError: true })
      .then(({ data }) => setPlans(data.plans))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSelect = (planId: string) => {
    router.push(`/payment?plan=${planId}&billing=${billing}`);
  };

  const priceDisplay = (plan: PlanResponse) => {
    if (plan.price_monthly === 0) return "Custom";
    const price = billing === "monthly" ? plan.price_monthly : plan.price_yearly;
    const monthlyEquiv = billing === "yearly" ? Math.round(plan.price_yearly / 12) : null;
    return (
      <div className="flex items-baseline justify-center gap-1">
        <span className="text-4xl font-medium text-white tracking-tight">${price / 100}</span>
        <span className="text-sm text-zinc-500 font-medium">
          {billing === "monthly" ? "/mo" : "/yr"}
        </span>
        {monthlyEquiv && (
          <span className="text-xs text-zinc-500 ml-2">(${(monthlyEquiv / 100).toFixed(2)}/mo)</span>
        )}
      </div>
    );
  };

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap"
        rel="stylesheet"
      />

      <div className="min-h-screen bg-[rgb(9,9,11)] relative overflow-hidden">
        <div className="mesh-bg fixed inset-0 z-0 overflow-hidden pointer-events-none" />
        <div className="fixed rounded-full blur-[80px] pointer-events-none z-0 opacity-40 w-[400px] h-[400px] bg-[radial-gradient(circle,rgba(99,102,241,0.3),transparent_70%)] top-[-100px] right-[-100px] animate-orb-float-1" />
        <div className="fixed rounded-full blur-[80px] pointer-events-none z-0 opacity-40 w-[300px] h-[300px] bg-[radial-gradient(circle,rgba(139,92,246,0.2),transparent_70%)] bottom-[10%] left-[5%] animate-orb-float-2" />

        <div className="relative z-10 max-w-6xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <div className="font-['JetBrains_Mono',monospace] text-[11px] font-medium tracking-[0.15em] uppercase text-indigo-500 mb-5 inline-flex items-center gap-2">
              <span className="size-[6px] rounded-full bg-indigo-500 animate-pulse" />
              Pricing
            </div>
            <h1 className="text-4xl md:text-5xl font-semibold text-white tracking-tight mb-4 bg-gradient-to-br from-white to-white/70 bg-clip-text text-transparent">
              Choose your coordinates
            </h1>
            <p className="text-zinc-400 text-lg max-w-xl mx-auto">
              Scale at the pace that matches your team's velocity. No hidden fees.
            </p>
          </div>

          {/* Billing toggle */}
          <div className="flex justify-center mb-12">
            <div className="flex gap-2 p-1 bg-zinc-800/50 rounded-xl border border-zinc-800">
              <button
                type="button"
                onClick={() => setBilling("monthly")}
                className={`h-[38px] px-5 rounded-[10px] text-[13px] font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer ${
                  billing === "monthly"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-300"
                }`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setBilling("yearly")}
                className={`h-[38px] px-5 rounded-[10px] text-[13px] font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer flex items-center gap-2 ${
                  billing === "yearly"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-300"
                }`}
              >
                Yearly
                <span className="text-[10px] bg-zinc-700 text-zinc-300 px-1.5 py-0.5 rounded-md font-medium">
                  Save 20%
                </span>
              </button>
            </div>
          </div>

          {loading ? (
            <div className="grid md:grid-cols-3 gap-8">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-8 text-center space-y-6 animate-pulse"
                >
                  <div className="h-4 bg-zinc-800 rounded w-20 mx-auto" />
                  <div className="h-8 bg-zinc-800 rounded w-24 mx-auto" />
                  <div className="h-3 bg-zinc-800 rounded w-48 mx-auto" />
                  <div className="h-10 bg-zinc-800 rounded-xl w-full" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid md:grid-cols-3 gap-8 items-start">
              {plans.map((plan) => {
                const isCurrent = plan.id === currentPlanId;
                const isHighlighted = isCurrent || plan.highlighted;
                return (
                  <div
                    key={plan.id}
                    className={`relative rounded-2xl border p-8 text-center space-y-6 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1 ${
                      isHighlighted
                        ? "bg-zinc-900 border-indigo-500/50 shadow-2xl shadow-indigo-900/10"
                        : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
                    }`}
                  >
                    {plan.badge && (
                      <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-indigo-500 text-white text-[10px] font-bold uppercase tracking-widest py-1 px-3 rounded-full">
                        {plan.badge}
                      </div>
                    )}

                    <h3
                      className={`text-sm font-semibold uppercase tracking-widest ${
                        isHighlighted ? "text-indigo-300" : "text-zinc-400"
                      }`}
                    >
                      {plan.name}
                    </h3>

                    <div>{priceDisplay(plan)}</div>

                    <button
                      type="button"
                      disabled={isCurrent}
                      onClick={() => handleSelect(plan.id)}
                      className={`w-full font-semibold py-3 rounded-xl transition text-sm cursor-pointer ${
                        isCurrent
                          ? "bg-zinc-800 text-zinc-400 cursor-not-allowed"
                          : isHighlighted
                            ? "bg-indigo-600 text-white hover:bg-indigo-500 hover:shadow-[0_8px_30px_rgba(99,102,241,0.35)]"
                            : "bg-zinc-800 text-white hover:bg-zinc-700"
                      }`}
                    >
                      {isCurrent
                        ? "Current plan"
                        : plan.price_monthly === 0
                          ? "Contact Sales"
                          : "Select plan"}
                    </button>

                    <p
                      className={`text-xs leading-relaxed ${
                        isHighlighted ? "text-indigo-200/70" : "text-zinc-500"
                      }`}
                    >
                      {plan.description}
                    </p>

                    <ul className="text-left space-y-3 pt-4 border-t border-zinc-800">
                      {plan.features.map((feature, idx) => (
                        <li
                          key={idx}
                          className="flex items-start gap-3 text-sm text-zinc-300"
                        >
                          <svg
                            className="shrink-0 mt-0.5 text-indigo-500"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default withAuth(PlansPage);
