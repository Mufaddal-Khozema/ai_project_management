"use client";

import { useRouter } from "next/navigation";
import type { PlanResponse } from "@/lib/api/types.gen";
import { StorageKeys } from "@/constants";

export default function PricingCards({ plans }: { plans: PlanResponse[] }) {
  const router = useRouter();

  const handleSelectPlan = (plan: PlanResponse) => {
    localStorage.setItem(StorageKeys.SELECTED_PLAN, JSON.stringify(plan));
    router.push("/signup");
  };

  const priceDisplay = (plan: PlanResponse) => {
    if (plan.price_monthly === 0) return "Custom";
    return `$${plan.price_monthly / 100}<span class="text-sm text-zinc-500 font-medium">/mo</span>`;
  };

  if (!plans || plans.length === 0) return null;

  return (
    <>
      {plans.map((plan) => {
        const isHighlighted = plan.highlighted;

        return (
          <div
            key={plan.id}
            className={`rounded-2xl border p-8 text-center space-y-6 ${
              isHighlighted
                ? "bg-zinc-900 border-indigo-500/50 relative transform shadow-2xl shadow-indigo-900/10"
                : "bg-zinc-900/40 border-zinc-800"
            }`}
          >
            {plan.badge && (
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-indigo-500 text-white text-[10px] font-bold uppercase tracking-widest py-1 px-3 rounded-full">
                {plan.badge}
              </div>
            )}

            <h3 className={`text-sm font-semibold uppercase tracking-widest ${
              isHighlighted ? "text-indigo-300" : "text-zinc-400"
            }`}>
              {plan.name}
            </h3>

            <div
              className="text-4xl font-medium text-white tracking-tight"
              dangerouslySetInnerHTML={{
                __html: priceDisplay(plan),
              }}
            />

            <button
              type="button"
              onClick={() => handleSelectPlan(plan)}
              className={`w-full font-semibold py-3 rounded-xl transition text-sm ${
                isHighlighted
                  ? "bg-indigo-600 text-white hover:bg-indigo-500"
                  : "bg-zinc-800 text-white hover:bg-zinc-700"
              }`}
            >
              {plan.name === "Enterprise" ? "Contact Sales" : "Start Trial"}
            </button>

            <p className={`text-xs leading-relaxed ${
              isHighlighted ? "text-indigo-200/70" : "text-zinc-500"
            }`}>
              {plan.description}
            </p>
          </div>
        );
      })}
    </>
  );
}
