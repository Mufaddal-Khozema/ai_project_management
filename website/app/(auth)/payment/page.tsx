"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Elements } from "@stripe/react-stripe-js";
import { useMutation } from "@tanstack/react-query";
import { withAuth } from "@/components/withAuth";
import { getStripe } from "@/lib/stripe";
import { PaymentForm } from "@/components/PaymentForm";
import { setupIntentMutationOptions, getCurrentUser } from "@/lib/api";
import { sdk } from "@/lib/api";
import { apiPaymentsPlansPlansHandler } from "@/lib/api/sdk.gen";
import type { PlanResponse } from "@/lib/api/types.gen";

function PaymentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const planId = searchParams.get("plan");
  const billing = searchParams.get("billing") as "monthly" | "yearly" | null;

  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [plansLoading, setPlansLoading] = useState(true);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState("");
  const [userName, setUserName] = useState<string | null>(null);

  const setupIntentMutation = useMutation(setupIntentMutationOptions());
  const setupStarted = useRef(false);

  useEffect(() => {
    if (!planId || !billing || (billing !== "monthly" && billing !== "yearly")) {
      router.replace("/plans");
      return;
    }

    apiPaymentsPlansPlansHandler({ client: sdk, throwOnError: true })
      .then(({ data }) => {
        const found = data.plans.find((p) => p.id === planId);
        if (!found) {
          router.replace("/plans");
        } else {
          setPlan(found);
        }
      })
      .catch(() => router.replace("/plans"))
      .finally(() => setPlansLoading(false));

    getCurrentUser({ client: sdk })
      .then(({ data }) => {
        if (data) {
          setUserEmail(data.email);
          setUserName(data.name ?? null);
        }
      })
      .catch(() => {});
  }, [planId, billing, router]);

  useEffect(() => {
    if (!plan || !userEmail || clientSecret || setupError || setupStarted.current) return;
    setupStarted.current = true;
    const priceId =
      billing === "monthly" ? plan.price_id_monthly : plan.price_id_yearly;
    setupIntentMutation.mutate(
      { body: { name: userName ?? undefined, email: userEmail, price_id: priceId } },
      {
        onSuccess: (data) => {
          setClientSecret(data.client_secret);
        },
        onError: (err) => {
          setSetupError(err instanceof Error ? err.message : "Something went wrong");
        },
      }
    );
  }, [plan, userEmail, clientSecret, setupError, billing, userName]);

  if (plansLoading) {
    return (
      <div className="min-h-screen bg-[rgb(9,9,11)] flex items-center justify-center">
        <div className="size-6 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!plan) return null;

  const price = billing === "monthly" ? plan.price_monthly : plan.price_yearly;

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap"
        rel="stylesheet"
      />

      <div className="relative min-h-screen bg-[rgb(9,9,11)]">
        <div className="mesh-bg fixed inset-0 z-0 overflow-hidden pointer-events-none" />
        <div className="relative z-[2] min-h-screen flex max-[900px]:flex-col">
          {/* Left: Order Summary */}
          <div className="flex-1 min-h-screen relative flex flex-col justify-end p-12 overflow-hidden max-[900px]:min-h-[280px] max-[900px]:p-8 max-[480px]:min-h-[220px] max-[480px]:p-6 before:absolute before:inset-0 before:bg-gradient-to-b before:from-transparent before:via-[rgba(9,9,11,0.3)] before:to-[rgba(9,9,11,0.85)] before:z-[1]">
            <img
              src="/signup.png"
              alt=""
              className="absolute inset-0 w-full h-full object-cover saturate-[0.7] contrast-[1.1] max-[900px]:opacity-40"
            />
            <div className="relative z-[2] max-w-[480px]">
              <div className="font-['JetBrains_Mono',monospace] text-[11px] font-medium tracking-[0.15em] uppercase text-indigo-500 mb-5 inline-flex items-center gap-2">
                <span className="size-[6px] rounded-full bg-indigo-500 animate-pulse" />
                Checkout
              </div>
              <h1 className="text-3xl md:text-4xl lg:text-5xl xl:text-[42px] font-semibold leading-[1.15] tracking-[-0.02em] mb-4 bg-gradient-to-br from-white to-white/70 bg-clip-text text-transparent">
                Secure your workspace.
              </h1>
              <p className="text-[15px] leading-[1.7] text-zinc-400 max-w-[400px]">
                You're subscribing to{" "}
                <span className="text-white font-medium">{plan.name}</span> billed{" "}
                {billing}ly. No charges until your 14-day trial ends.
              </p>

              <div className="mt-10 p-6 bg-zinc-900/60 backdrop-blur-xl border border-zinc-800 rounded-2xl space-y-4 max-w-sm">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-zinc-400">Plan</span>
                  <span className="text-white font-medium">{plan.name}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-zinc-400">Billing</span>
                  <span className="text-white font-medium capitalize">{billing}</span>
                </div>
                <div className="h-px bg-zinc-800" />
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400 text-sm">Total today</span>
                  <span className="text-white font-semibold text-lg">
                    ${price / 100}
                    <span className="text-zinc-500 text-sm font-normal">
                      /{billing === "monthly" ? "mo" : "yr"}
                    </span>
                  </span>
                </div>
                <div className="text-xs text-zinc-500">14-day free trial &bull; Cancel anytime</div>
              </div>

              {plan.features.length > 0 && (
                <div className="mt-6 max-w-sm">
                  <p className="text-xs text-zinc-500 mb-3 font-medium uppercase tracking-wider">What's included</p>
                  <ul className="space-y-2">
                    {plan.features.slice(0, 5).map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-zinc-400">
                        <svg className="shrink-0 mt-0.5 text-indigo-500" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Right: Payment Form */}
          <div className="w-full max-w-[460px] min-h-screen flex flex-col justify-center p-10 relative bg-[rgb(9,9,11)] backdrop-blur-2xl backdrop-saturate-150 border-l border-zinc-800 max-[900px]:max-w-full max-[900px]:p-8 max-[900px]:border-l-0 max-[900px]:border-t border-zinc-800 max-[480px]:p-6">
            <div className="mb-5">
              <div className="flex items-center gap-[10px] mb-8">
                <div className="size-6 rounded-lg bg-indigo-600 flex items-center justify-center">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="relative z-[1] size-4">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
                <span className="text-base font-semibold tracking-[-0.03em] text-white">Coordina</span>
              </div>
              <h2 className="text-lg font-semibold tracking-[-0.02em] leading-[1.2] mb-2">Complete payment</h2>
              <p className="text-xs text-zinc-400 leading-[1.6]">Start your 14-day free trial. No charge today.</p>
            </div>

            {clientSecret ? (
              <Elements
                stripe={getStripe()}
                options={{
                  clientSecret,
                  appearance: {
                    theme: "night",
                    variables: {
                      fontFamily: "'Inter Tight', -apple-system, BlinkMacSystemFont, sans-serif",
                      colorPrimary: "#6366f1",
                      colorBackground: "#27272a",
                      colorText: "#f4f4f5",
                      colorDanger: "#ef4444",
                      borderRadius: "12px",
                    },
                  },
                }}
              >
		<PaymentForm
                  onSuccess={() => {
                    router.push("/admin?onboarding=1");
                  }}
                  returnUrl={`${window.location.origin}/payment?plan=${planId}&billing=${billing}`}
                  name={userName ?? undefined}
                  email={userEmail || undefined}
                />
              </Elements>
            ) : (
              <>
                {setupIntentMutation.isPending && (
                  <div className="h-[38px] px-4 bg-zinc-800 border border-zinc-800 rounded-xl flex items-center text-zinc-500 text-[13px] gap-2">
                    <span className="size-[16px] border-2 border-zinc-600 border-t-indigo-500 rounded-full animate-spin" />
                    Loading secure payment…
                  </div>
                )}

                {setupError && (
                  <div className="text-xs text-red-500 mb-3 flex items-center gap-1">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    {setupError}
                  </div>
                )}

                {setupError && (
                  <button
                    type="button"
                    className="w-full h-[38px] bg-indigo-600 border-none rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-semibold tracking-[-0.01em] cursor-pointer flex items-center justify-center gap-2 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none mt-4"
                    onClick={() => {
                      setupStarted.current = false;
                      setSetupError(null);
                    }}
                  >
                    Try again
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default withAuth(PaymentPage);
