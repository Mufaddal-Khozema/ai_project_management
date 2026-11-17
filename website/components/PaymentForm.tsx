"use client";

import { useState } from "react";
import Link from "next/link";
import {
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";

const btnCls =
  "inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 text-sm font-semibold text-white shadow-soft transition-all active:shadow-press disabled:cursor-not-allowed disabled:opacity-50";

export function PaymentForm({
  onSuccess,
  returnUrl,
  name,
  email,
}: {
  onSuccess: () => void;
  returnUrl?: string;
  name?: string;
  email?: string;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [agreementError, setAgreementError] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!agreed) {
      setAgreementError(true);
      setError("You must agree to the Terms of Service and Privacy Policy to continue.");
      return;
    }

    if (!stripe || !elements) return;

    setLoading(true);
    setError(null);

    const { error: confirmError } = await stripe.confirmSetup({
      elements,
      confirmParams: {
        return_url: returnUrl || `${window.location.origin}/signup/success`,
        ...(name || email ? {
          payment_method_data: {
            billing_details: {
              ...(name ? { name } : {}),
              ...(email ? { email } : {}),
            },
          },
        } : {}),
      },
      redirect: "if_required",
    });

    if (confirmError) {
      setError(confirmError.message ?? "Payment setup failed");
      setLoading(false);
      return;
    }

    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="relative mb-3">
        <PaymentElement
          options={{
            layout: "tabs",
            fields: {
              billingDetails: {
                name: "auto",
                email: "never",
                phone: "auto",
                address: "auto",
              },
            },
            wallets: { applePay: "never", googlePay: "never" },
          }}
        />
      </div>

      {error && (
        <div className="mb-3 flex items-center gap-1 text-xs text-red-500">
          <svg className="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      <label
        className={`my-6 flex cursor-pointer items-start gap-3 ${agreementError ? "animate-shake" : ""}`}
      >
        <input
          type="checkbox"
          id="agreement"
          checked={agreed}
          onChange={(e) => {
            setAgreed(e.target.checked);
            if (e.target.checked) setAgreementError(false);
          }}
          className="relative mt-0.5 size-5 shrink-0 cursor-pointer appearance-none rounded-md border border-hairline bg-canvas shadow-press transition-all after:absolute after:top-0.5 after:left-1.5 after:h-2.5 after:w-1.5 after:rotate-45 after:border-r-2 after:border-b-2 after:border-white after:opacity-0 checked:border-indigo-600 checked:bg-indigo-600 checked:after:opacity-100"
        />
        <span className="text-sm leading-relaxed text-ink-muted">
          I agree to the{" "}
          <Link href="/terms" className="font-medium text-indigo-500 no-underline transition-opacity hover:opacity-80">
            Terms of Service
          </Link>
          {" "}and{" "}
          <Link href="/privacy" className="font-medium text-indigo-500 no-underline transition-opacity hover:opacity-80">
            Privacy Policy
          </Link>
          .
        </span>
      </label>

      <button
        type="submit"
        className={`${btnCls} mt-1`}
        disabled={!stripe || !elements || loading}
      >
        <span>{loading ? "Processing…" : "Start free trial"}</span>
        {loading && (
          <span className="size-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        )}
        {!loading && (
          <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        )}
      </button>
    </form>
  );
}
