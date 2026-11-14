"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { Elements } from "@stripe/react-stripe-js";
import { useMutation } from "@tanstack/react-query";
import { withAuth } from "@/components/withAuth";
import { getStripe } from "@/lib/stripe";
import { PaymentForm } from "@/components/PaymentForm";
import { setupIntentMutation } from "@/lib/api/@tanstack/react-query.gen";
import type { PlanResponse } from "@/lib/api/types.gen";
import { getCurrentUser, listPlans } from "@/lib/api";
import { Orb } from "@/components/landing/orb";
import { Threads } from "@/components/landing/threads";
import { ThemeIcon } from "@/components/landing/icons";
import { useLandingTheme } from "@/components/landing/use-theme";

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
  const { theme, toggleTheme } = useLandingTheme();

  const setupStarted = useRef(false);

  useEffect(() => {
    if (!planId || !billing || (billing !== "monthly" && billing !== "yearly")) {
      router.replace("/plans");
      return;
    }

    listPlans({ throwOnError: true })
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

    getCurrentUser({ throwOnError: true })
      .then(({ data }) => {
        if (data) {
          setUserEmail(data.email);
          setUserName(data.name ?? null);
        }
      })
      .catch(() => {});
  }, [planId, billing, router]);

  const mutation = useMutation({
    ...setupIntentMutation(),
    onSuccess: (data) => {
      setClientSecret(data.client_secret);
    },
    onError: (err) => {
      setSetupError(err instanceof Error ? err.message : "Something went wrong");
    }
  });

  useEffect(() => {
    if (!plan || !userEmail || setupError || setupStarted.current) return;
    setupStarted.current = true;
    const priceId =
      billing === "monthly" ? plan.price_id_monthly : plan.price_id_yearly;
    mutation.mutate({ body: { name: userName ?? undefined, email: userEmail, price_id: priceId } });
  }, [plan, userEmail, setupError, billing, userName]);

  if (plansLoading) {
    return (
      <div
        className="landing relative isolate flex min-h-screen items-center justify-center bg-canvas font-body text-ink"
      >
        <Threads className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-60" />
        <div className="size-6 animate-spin rounded-full border-2 border-indigo-500/30 border-t-indigo-500" />
      </div>
    );
  }

  if (!plan) return null;

  const price = billing === "monthly" ? plan.price_monthly : plan.price_yearly;
  const isDark = theme === "dark";

  return (
    <div
      className="landing relative isolate min-h-screen bg-canvas font-body text-ink"
    >
      <Threads className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-60" />

      <div className="relative z-10 grid min-h-screen lg:grid-cols-5">
        <div className="relative flex min-h-72 flex-col justify-end overflow-hidden p-6 sm:p-8 lg:col-span-3 lg:min-h-screen lg:p-14">
          <Image
            src="/landing/a3.jpg"
            alt=""
            fill
            priority
            sizes="(min-width: 1024px) 60vw, 100vw"
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-950/40 via-indigo-950/60 to-indigo-950/90" />

          <div className="relative z-10 max-w-xl">
            <div className="mb-5 inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-indigo-200 uppercase">
              <span className="size-1.5 rounded-full bg-indigo-300" />
              Checkout
            </div>
            <h1 className="font-display text-3xl font-extrabold leading-none tracking-tight text-white sm:text-4xl lg:text-5xl">
              Secure your workspace.
            </h1>
            <p className="mt-4 max-w-md text-indigo-100/80">
              You’re subscribing to{" "}
              <span className="font-medium text-white">{plan.name}</span> billed{" "}
              {billing}ly. No charges until your 14-day trial ends.
            </p>

            <div className="mt-8 grid max-w-sm gap-4 rounded-2xl bg-canvas p-6 shadow-raise">
              <div className="flex items-center justify-between text-sm">
                <span className="text-ink-muted">Plan</span>
                <span className="font-medium">{plan.name}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-ink-muted">Billing</span>
                <span className="font-medium capitalize">{billing}</span>
              </div>
              <div className="h-px bg-hairline" />
              <div className="flex items-center justify-between">
                <span className="text-sm text-ink-muted">Total today</span>
                <span className="font-display text-lg font-extrabold">
                  ${price / 100}
                  <span className="font-body text-sm font-normal text-ink-muted">
                    /{billing === "monthly" ? "mo" : "yr"}
                  </span>
                </span>
              </div>
              <div className="text-xs text-ink-muted">
                14-day free trial · Cancel anytime
              </div>
            </div>

            {plan.features.length > 0 && (
              <div className="mt-6 max-w-sm">
                <p className="mb-3 text-xs font-semibold tracking-wider text-indigo-200/70 uppercase">
                  What’s included
                </p>
                <ul className="grid gap-2">
                  {plan.features.slice(0, 5).map((feature, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 text-sm text-indigo-100/80"
                    >
                      <span className="mt-0.5 shrink-0 font-extrabold text-indigo-300">
                        ✓
                      </span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-center border-t border-hairline bg-canvas p-6 sm:p-10 lg:col-span-2 lg:border-t-0 lg:border-l">
          <div className="w-full max-w-md">
            <div className="mb-7 flex items-center gap-2.5">
              <Orb />
              <span className="font-display text-lg font-extrabold">
                CoordinaAI
              </span>
              <span className="flex-1" />
              <button
                type="button"
                aria-label="Switch light or dark theme"
                onClick={toggleTheme}
                className="inline-flex size-11 items-center justify-center rounded-xl bg-canvas text-ink shadow-soft active:shadow-press"
              >
                <ThemeIcon />
              </button>
            </div>

            <h2 className="font-display text-2xl font-extrabold tracking-tight">
              Complete payment
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              Start your 14-day free trial. No charge today.
            </p>

            <div className="mt-6">
              {clientSecret ? (
                <Elements
                  stripe={getStripe()}
                  options={{
                    clientSecret,
                    appearance: {
                      theme: isDark ? "night" : "stripe",
                      variables: {
                        fontFamily: "'Figtree', -apple-system, BlinkMacSystemFont, sans-serif",
                        colorPrimary: "#4f46e5",
                        colorBackground: isDark ? "#0f172a" : "#ffffff",
                        colorText: isDark ? "#f1f5f9" : "#1e293b",
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
                  {mutation.isPending && (
                    <div className="flex h-12 items-center gap-2 rounded-xl bg-canvas px-4 text-sm text-ink-muted shadow-press">
                      <span className="size-4 animate-spin rounded-full border-2 border-hairline border-t-indigo-500" />
                      Loading secure payment…
                    </div>
                  )}

                  {setupError && (
                    <div className="flex items-center gap-1 text-xs text-red-500">
                      <svg
                        className="size-3.5"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
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
                      className="mt-4 inline-flex h-12 w-full items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 text-sm font-semibold text-white shadow-soft active:shadow-press"
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
      </div>
    </div>
  );
}

export default withAuth(PaymentPage);
