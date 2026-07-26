"use client";

import { useState } from "react";
import {
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";

const btnCls =
  "w-full h-[38px] bg-indigo-600 border-none rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-semibold tracking-[-0.01em] cursor-pointer flex items-center justify-center gap-2 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none";

export function PaymentForm({
  onSuccess,
}: {
  onSuccess: () => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) return;

    setLoading(true);
    setError(null);

    const { error: confirmError } = await stripe.confirmSetup({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/signup/success`,
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
            fields: { billingDetails: "never" },
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
