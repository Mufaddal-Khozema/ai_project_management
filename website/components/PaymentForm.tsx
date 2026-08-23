"use client";

import { useState } from "react";
import Link from "next/link";
import {
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";

const btnCls =
  "w-full h-[38px] bg-indigo-600 border-none rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-semibold tracking-[-0.01em] cursor-pointer flex items-center justify-center gap-2 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none";

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
        <div className="text-xs text-red-500 mb-3 flex items-center gap-1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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
          className="appearance-none mt-[1px] h-5 w-5 min-w-5 relative cursor-pointer rounded-[6px] border border-white/5 bg-[#1a1a1f] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] checked:border-indigo-500 checked:bg-indigo-500 after:absolute after:left-[6px] after:top-[2px] after:h-[10px] after:w-[5px] after:rotate-45 after:border-b-2 after:border-r-2 after:border-white after:opacity-0 checked:after:opacity-100"
        />
        <span className="text-[13px] leading-[1.6] text-[#8e8e93]">
          I agree to the{" "}
          <Link href="/terms" className="text-indigo-500 no-underline font-medium transition-opacity duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:opacity-80">
            Terms of Service
          </Link>
          {" "}and{" "}
          <Link href="/privacy" className="text-indigo-500 no-underline font-medium transition-opacity duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:opacity-80">
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
          <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full animate-spin" />
        )}
        {!loading && (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        )}
      </button>
    </form>
  );
}
