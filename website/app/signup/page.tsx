"use client";

import { useState, useRef, useEffect } from "react";
import { Elements } from "@stripe/react-stripe-js";
import { useMutation } from "@tanstack/react-query";
import { useSendOtpMutation, useVerifyOtpMutation, setupIntentMutationOptions } from "@/lib/api";
import { getStripe } from "@/lib/stripe";
import { PaymentForm } from "@/components/PaymentForm";
import { StorageKeys } from "@/constants";

const btnCls =
  "w-full h-[38px] bg-indigo-600 border-none rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-semibold tracking-[-0.01em] cursor-pointer flex items-center justify-center gap-2 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none";
const socialBtnCls =
  "h-12 bg-zinc-900 border border-zinc-800 rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-sm font-medium cursor-pointer flex items-center justify-center gap-[10px] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-zinc-800 hover:border-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed w-full";
const inputCls =
  "w-full h-[38px] px-4 bg-zinc-800 border rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-normal outline-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] placeholder:text-zinc-500 hover:border-zinc-700 focus:border-indigo-500 focus:shadow-[0_0_0_3px_rgba(99,102,241,0.1),0_0_20px_rgba(99,102,241,0.3)]";

const platforms = {
  comm: [
    { id: "slack", name: "Slack", color: "#4A154B", glyph: "#" },
    { id: "teams", name: "Teams", color: "#6264A7", glyph: "T" },
    { id: "discord", name: "Discord", color: "#5865F2", glyph: "D" },
    { id: "google-chat", name: "Google Chat", color: "#34A853", glyph: "G" },
    { id: "telegram", name: "Telegram", color: "#0088CC", glyph: "T" },
    { id: "other-comm", name: "Other", color: "#52525B", glyph: "..." },
  ],
  pm: [
    { id: "jira", name: "Jira", color: "#0052CC", glyph: "J" },
    { id: "asana", name: "Asana", color: "#F06A6A", glyph: "A" },
    { id: "linear", name: "Linear", color: "#5E6AD2", glyph: "L" },
    { id: "trello", name: "Trello", color: "#0079BF", glyph: "T" },
    { id: "notion", name: "Notion", color: "#000000", glyph: "N" },
    { id: "other-pm", name: "Other", color: "#52525B", glyph: "..." },
  ],
};

export default function SignupPage() {
  const [step, setStep] = useState(1);
  const [authMode, setAuthMode] = useState<"social" | "otp">("social");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [emailLoading, setEmailLoading] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, boolean>>({});

  const sendOtpMutation = useSendOtpMutation();
  const verifyOtpMutation = useVerifyOtpMutation();
  const setupIntentMutation = useMutation(setupIntentMutationOptions());

  const [paymentName, setPaymentName] = useState("");
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  const [showDialog, setShowDialog] = useState(false);
  const [dialogStep, setDialogStep] = useState<"survey" | "comm" | "pm">("survey");
  const [surveyCompany, setSurveyCompany] = useState("");
  const [surveyRole, setSurveyRole] = useState("");
  const [surveyTeam, setSurveyTeam] = useState("");
  const [surveySource, setSurveySource] = useState("");
  const [selectedComm, setSelectedComm] = useState("");
  const [selectedPm, setSelectedPm] = useState("");
  const [completed, setCompleted] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);

  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get(StorageKeys.TOKEN);
    const stepParam = params.get("step");
    const error = params.get("error");

    if (error) {
      setOauthError(error === "oauth" ? "Google or GitHub" : error);
      return;
    }

    if (token) {
      setOauthLoading(true);
      localStorage.setItem(StorageKeys.TOKEN, token);
      if (localStorage.getItem(StorageKeys.SELECTED_PLAN)) {
        window.history.replaceState(null, "", "/signup");
        setShowDialog(true);
        localStorage.removeItem(StorageKeys.SELECTED_PLAN);
        setTimeout(() => setOauthLoading(false), 500);
      } else {
        window.history.replaceState(null, "", "/signup?step=payment");
        setStep(2);
        setTimeout(() => setOauthLoading(false), 500);
      }
      return;
    }

    if (stepParam === "payment") {
      if (!localStorage.getItem(StorageKeys.TOKEN)) {
        window.history.replaceState(null, "", "/signup");
        setStep(1);
        return;
      }
      setStep(2);
      window.history.replaceState(null, "", "/signup?step=payment");
    }
  }, []);

  useEffect(() => {
    if (authMode === "otp") {
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    }
  }, [authMode]);

  const clearError = (field: string) =>
    setErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });

  const handleEmailSubmit = () => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setErrors({ email: true });
      return;
    }
    setEmailLoading(true);
    sendOtpMutation.mutate(
      { body: { email: email.trim() } },
      {
        onSuccess: () => {
          setEmailLoading(false);
          setAuthMode("otp");
          setErrors({});
        },
        onError: () => {
          setEmailLoading(false);
          setErrors({ email: true });
        },
      }
    );
  };

  const handleOtpChange = (i: number, val: string) => {
    if (val.length > 1) return;
    const next = [...otp];
    next[i] = val;
    setOtp(next);
    setErrors({});
    if (val && i < 5) otpRefs.current[i + 1]?.focus();
    if (i === 5 && val) {
      setOtpLoading(true);
      verifyOtpMutation.mutate(
        { body: { email: email.trim(), otp: [...otp.slice(0, 5), val].join("") } },
        {
          onSuccess: () => {
            setOtpLoading(false);
            if (localStorage.getItem(StorageKeys.SELECTED_PLAN)) {
              localStorage.removeItem(StorageKeys.SELECTED_PLAN);
              setShowDialog(true);
            } else {
              setStep(2);
            }
          },
          onError: () => {
            setOtpLoading(false);
            setErrors({ otp: true });
          },
        }
      );
    }
  };

  const handleOtpKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) otpRefs.current[i - 1]?.focus();
  };

  const handleSkipToPayment = () => setStep(2);

  const handlePaymentSubmit = () => {
    if (!paymentName.trim()) return;
    setSetupLoading(true);
    setSetupError(null);
    const priceId =
      billingPeriod === "monthly"
        ? process.env.NEXT_PUBLIC_STRIPE_PRICE_MONTHLY!
        : process.env.NEXT_PUBLIC_STRIPE_PRICE_YEARLY!;
    setupIntentMutation.mutate(
      { body: { name: paymentName.trim(), email: email.trim(), price_id: priceId } },
      {
        onSuccess: (data) => {
          setClientSecret(data.client_secret);
          setSetupLoading(false);
        },
        onError: (err) => {
          setSetupError(err instanceof Error ? err.message : "Something went wrong");
          setSetupLoading(false);
        },
      },
    );
  };

  const handleSkipPayment = () => setShowDialog(true);

  const handleDialogPrev = () => {
    if (dialogStep === "comm") setDialogStep("survey");
    else if (dialogStep === "pm") setDialogStep("comm");
  };

  const handleDialogNext = () => {
    if (dialogStep === "survey") setDialogStep("comm");
    else if (dialogStep === "comm") setDialogStep("pm");
    else {
      setCompleted(true);
      setShowDialog(false);
    }
  };

  const handleDialogSkip = () => {
    if (dialogStep === "survey") setDialogStep("comm");
    else if (dialogStep === "comm") setDialogStep("pm");
    else {
      setCompleted(true);
      setShowDialog(false);
    }
  };

  const progressLabels = ["Auth", "Payment"];

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap"
        rel="stylesheet"
      />

      <div id="signup-root" className="relative">
        <div className="mesh-bg fixed inset-0 z-0 overflow-hidden pointer-events-none" />

        <div className="relative z-[2] min-h-screen flex max-[900px]:flex-col">
          {/* Left: Visual Panel */}
          <div className="flex-1 min-h-screen relative flex flex-col justify-end p-12 overflow-hidden max-[900px]:min-h-[280px] max-[900px]:p-8 max-[480px]:min-h-[220px] max-[480px]:p-6 before:absolute before:inset-0 before:bg-gradient-to-b before:from-transparent before:via-[rgba(9,9,11,0.3)] before:to-[rgba(9,9,11,0.85)] before:z-[1]">
            <img
              src="/signup.png"
              alt=""
              className="absolute inset-0 w-full h-full object-cover saturate-[0.7] contrast-[1.1] max-[900px]:opacity-40"
            />
            <div className="relative z-[2] max-w-[480px]">
              <div className="font-['JetBrains_Mono',monospace] text-[11px] font-medium tracking-[0.15em] uppercase text-indigo-500 mb-5 inline-flex items-center gap-2">
                <span className="size-[6px] rounded-full bg-indigo-500 animate-pulse" />
                Onboarding
              </div>
              <h1 className="text-3xl md:text-4xl lg:text-5xl xl:text-[42px] font-semibold leading-[1.15] tracking-[-0.02em] mb-4 bg-gradient-to-br from-white to-white/70 bg-clip-text text-transparent">
                Where projects find their rhythm.
              </h1>
              <p className="text-[15px] leading-[1.7] text-zinc-400 max-w-[400px]">
                Join the teams who have replaced status meetings with intelligent coordination.
              </p>
              <div className="flex gap-8 mt-8 pt-6 border-t border-zinc-800 max-[900px]:gap-5 max-[480px]:hidden">
                <div className="flex flex-col gap-1">
                  <span className="font-['JetBrains_Mono',monospace] text-2xl font-medium text-white max-[900px]:text-xl">12K+</span>
                  <span className="text-xs text-zinc-500 tracking-[0.05em]">Teams synced</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="font-['JetBrains_Mono',monospace] text-2xl font-medium text-white max-[900px]:text-xl">4.2M</span>
                  <span className="text-xs text-zinc-500 tracking-[0.05em]">Tasks routed</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="font-['JetBrains_Mono',monospace] text-2xl font-medium text-white max-[900px]:text-xl">98.7%</span>
                  <span className="text-xs text-zinc-500 tracking-[0.05em]">Uptime</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Form Panel */}
          <div className="w-full max-w-[460px] min-h-screen flex flex-col justify-center p-10 relative bg-[rgb(9,9,11)] backdrop-blur-2xl backdrop-saturate-150 border-l border-zinc-800 max-[900px]:max-w-full max-[900px]:p-8 max-[900px]:border-l-0 max-[900px]:border-t border-zinc-800 max-[480px]:p-6">
            {!completed && !showDialog && (
              <>
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
                  <h2 className="text-lg font-semibold tracking-[-0.02em] leading-[1.2] mb-2">Join the network</h2>
                  <p className="text-xs text-zinc-400 leading-[1.6]">Fast setup. Start coordinating in minutes.</p>
                </div>

                {/* Progress Steps */}
                <div className="flex items-center gap-2 mb-10">
                  {progressLabels.map((label, i) => {
                    const idx = i + 1;
                    return (
                      <div key={label} className="flex items-center gap-2 flex-1 last:flex-none">
                        <button
                          type="button"
                          onClick={() => {
                            if (idx === 1) setStep(1);
                            else if (idx === 2) handleSkipToPayment();
                          }}
                          className={`flex items-center gap-2 text-xs font-medium transition-colors duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer hover:opacity-80 ${
                            step === idx ? "text-white" : step > idx ? "text-indigo-500" : "text-zinc-500"
                          }`}
                        >
                          <span
                            className={`size-7 rounded-full border flex items-center justify-center font-['JetBrains_Mono',monospace] text-[11px] font-medium transition-all duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
                              step > idx
                                ? "border-indigo-500 bg-indigo-500 text-white"
                                : step === idx
                                ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                                : "border-zinc-800"
                            }`}
                          >
                            {idx}
                          </span>
                          <span className="max-[400px]:hidden">{label}</span>
                        </button>
                        {i < progressLabels.length - 1 && (
                          <div
                            className={`flex-1 h-px bg-zinc-800 relative overflow-hidden after:absolute after:inset-0 after:bg-indigo-500 after:-translate-x-full after:transition-transform after:duration-[600ms] after:ease-[cubic-bezier(0.16,1,0.3,1)] ${
                              step > idx ? "after:translate-x-0" : ""
                            }`}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Step 1: Auth */}
                {step === 1 && (
                  <div
                    style={{
                      opacity: 1,
                      transform: "translateY(0)",
                      transition: "all 0.5s cubic-bezier(0.16,1,0.3,1)",
                    }}
                  >
                    {authMode === "social" ? (
                      <>
                        {oauthError && (
                          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center gap-2">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                              <circle cx="12" cy="12" r="10" />
                              <line x1="12" y1="8" x2="12" y2="12" />
                              <line x1="12" y1="16" x2="12.01" y2="16" />
                            </svg>
                            <span>Sign in with {oauthError} failed. Try again or use email.</span>
                          </div>
                        )}
                        <div className="flex flex-col gap-2.5 mb-4">
                          <button type="button" className={socialBtnCls} onClick={() => { window.location.href = "/auth/google/login"; }} disabled={oauthLoading}>
                            {oauthLoading ? (
                              <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                              <svg width="18" height="18" viewBox="0 0 24 24">
                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                              </svg>
                            )}
                            Continue with Google
                          </button>
                          <button type="button" className={socialBtnCls} onClick={() => { window.location.href = "/auth/github/login"; }} disabled={oauthLoading}>
                            {oauthLoading ? (
                              <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                              </svg>
                            )}
                            Continue with GitHub
                          </button>
                        </div>

                        <div className="flex items-center gap-4 my-4 text-zinc-500 text-xs font-medium before:flex-1 before:h-px before:bg-zinc-800 after:flex-1 after:h-px after:bg-zinc-800">
                          or with email
                        </div>

                        <div className="relative">
                          <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]" htmlFor="email">
                            Work email
                          </label>
                          <div className="relative">
                            <input
                              type="email"
                              id="email"
                              className={`peer ${inputCls} ${errors.email ? "!border-[#ef4444] !shadow-[0_0_0_3px_rgba(239,68,68,0.1)]" : "border-zinc-800"}`}
                              placeholder="alex@company.com"
                              autoComplete="email"
                              value={email}
                              onChange={(e) => {
                                setEmail(e.target.value);
                                clearError("email");
                              }}
                              onKeyDown={(e) => e.key === "Enter" && handleEmailSubmit()}
                            />
                            <svg
                              className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] peer-focus:text-indigo-500"
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <rect x="2" y="4" width="20" height="16" rx="2" />
                              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                            </svg>
                          </div>
                          <div
                            className={`text-xs text-red-500 mt-1.5 flex items-center gap-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                              errors.email ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"
                            }`}
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <circle cx="12" cy="12" r="10" />
                              <line x1="12" y1="8" x2="12" y2="12" />
                              <line x1="12" y1="16" x2="12.01" y2="16" />
                            </svg>
                            Please enter a valid email address
                          </div>
                        </div>

                        <button type="button" className={`${btnCls} mt-4`} onClick={handleEmailSubmit} disabled={emailLoading}>
                          <span>Continue with email</span>
                          {emailLoading && (
                            <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          )}
                          {!emailLoading && (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M5 12h14" />
                              <path d="m12 5 7 7-7 7" />
                            </svg>
                          )}
                        </button>

                        <div className="text-center mt-6 text-xs text-zinc-400">
                          Already have an account?{" "}
                          <a href="#" className="text-white no-underline font-semibold transition-colors duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-indigo-500">
                            Sign in
                          </a>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="mb-4">
                          <p className="text-xs text-zinc-400 mb-1">
                            Code sent to <span className="text-white font-medium">{email}</span>
                          </p>
                          <button
                            type="button"
                            className="text-xs text-indigo-500 bg-transparent border-none cursor-pointer hover:opacity-80 p-0"
                            onClick={() => {
                              setAuthMode("social");
                              setOtp(["", "", "", "", "", ""]);
                            }}
                          >
                            Change email
                          </button>
                        </div>

                        <label className="block text-[13px] font-medium text-zinc-400 mb-3 tracking-[0.01em]">Enter verification code</label>
                        <div className="flex gap-2 mb-4 justify-between">
                          {otp.map((digit, i) => (
                            <input
                              key={i}
                              ref={(el) => { otpRefs.current[i] = el; }}
                              type="text"
                              inputMode="numeric"
                              maxLength={1}
                              value={digit}
                              onChange={(e) => handleOtpChange(i, e.target.value)}
                              onKeyDown={(e) => handleOtpKeyDown(i, e)}
                              className={`w-12 h-12 text-center bg-zinc-800 border rounded-xl text-white font-['JetBrains_Mono',monospace] text-lg font-medium outline-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-zinc-700 focus:border-indigo-500 focus:shadow-[0_0_0_3px_rgba(99,102,241,0.1),0_0_20px_rgba(99,102,241,0.3)] ${
                                errors.otp ? "!border-[#ef4444]" : "border-zinc-800"
                              }`}
                            />
                          ))}
                        </div>

                        <button type="button" className={`${btnCls} mt-2`} disabled={otpLoading || otp.some((d) => !d)} onClick={() => {
                              setOtpLoading(true);
                              verifyOtpMutation.mutate(
                                { body: { email: email.trim(), otp: otp.join("") } },
                                {
                                  onSuccess: () => {
                                    setOtpLoading(false);
                                    if (localStorage.getItem(StorageKeys.SELECTED_PLAN)) {
                                      localStorage.removeItem(StorageKeys.SELECTED_PLAN);
                                      setShowDialog(true);
                                    } else {
                                      setStep(2);
                                    }
                                  },
                                  onError: () => {
                                    setOtpLoading(false);
                                    setErrors({ otp: true });
                                  },
                                }
                              );
                            }}>
                          <span>Verify & continue</span>
                          {otpLoading && <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                        </button>

                        <div className="text-center mt-4">
                          <button
                            type="button"
                            className="text-xs text-zinc-500 bg-transparent border-none cursor-pointer hover:text-zinc-300 p-0"
                          >
                            Resend code
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* Step 2: Payment */}
                {step === 2 && (
                  <div
                    style={{
                      opacity: 1,
                      transform: "translateY(0)",
                      transition: "all 0.5s cubic-bezier(0.16,1,0.3,1)",
                    }}
                  >
                    <p className="text-xs text-zinc-400 leading-[1.6] mb-5">
                      Start your 14-day free trial. No charge today.
                    </p>

                    <div className="relative mb-3">
                      <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]">
                        Plan
                      </label>
                      <div className="flex gap-2 p-1 bg-zinc-800/50 rounded-xl">
                        <button
                          type="button"
                          className={`flex-1 h-[38px] rounded-[10px] text-[13px] font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer ${
                            billingPeriod === "monthly"
                              ? "bg-indigo-600 text-white shadow-sm"
                              : "text-zinc-400 hover:text-zinc-300"
                          }`}
                          onClick={() => setBillingPeriod("monthly")}
                        >
                          Monthly
                        </button>
                        <button
                          type="button"
                          className={`flex-1 h-[38px] rounded-[10px] text-[13px] font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer flex items-center justify-center gap-1.5 ${
                            billingPeriod === "yearly"
                              ? "bg-indigo-600 text-white shadow-sm"
                              : "text-zinc-400 hover:text-zinc-300"
                          }`}
                          onClick={() => setBillingPeriod("yearly")}
                        >
                          Yearly
                        </button>
                      </div>
                    </div>

                    <div className="relative mb-3">
                      <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]" htmlFor="cardName">
                        Name on card
                      </label>
                      <input
                        type="text"
                        id="cardName"
                        className={`${inputCls} border-zinc-800`}
                        placeholder="Alex Chen"
                        value={paymentName}
                        onChange={(e) => setPaymentName(e.target.value)}
                      />
                    </div>

                    {clientSecret ? (
                      <Elements stripe={getStripe()} options={{ clientSecret }}>
                        <PaymentForm onSuccess={() => {
                          localStorage.removeItem(StorageKeys.SELECTED_PLAN);
                          setShowDialog(true);
                        }} />
                      </Elements>
                    ) : (
                      <>
                        <div className="relative mb-3">
                          <div className="h-[38px] px-4 bg-zinc-800 border border-zinc-800 rounded-xl flex items-center text-zinc-500 text-[13px] gap-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <rect x="1" y="6" width="22" height="12" rx="2" />
                              <line x1="6" y1="12" x2="10" y2="12" />
                              <line x1="13" y1="12" x2="18" y2="12" />
                            </svg>
                            Secure card details powered by Stripe
                          </div>
                        </div>

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

                        <button
                          type="button"
                          className={`${btnCls} mt-4`}
                          onClick={handlePaymentSubmit}
                          disabled={setupLoading || !paymentName.trim()}
                        >
                          <span>{setupLoading ? "Setting up…" : "Start free trial"}</span>
                          {setupLoading && (
                            <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          )}
                          {!setupLoading && (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M5 12h14" />
                              <path d="m12 5 7 7-7 7" />
                            </svg>
                          )}
                        </button>
                      </>
                    )}

                    <button
                      type="button"
                      className="w-full mt-2.5 bg-transparent border-none text-zinc-500 text-xs cursor-pointer hover:text-zinc-300 transition-colors p-1"
                      onClick={handleSkipPayment}
                    >
                      Skip for now →
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Success after dialog complete */}
            {completed && (
              <div className="text-center py-10">
                <div className="size-20 rounded-full bg-indigo-600 flex items-center justify-center mx-auto mb-6 relative before:absolute before:-inset-1 before:rounded-full before:bg-indigo-500/30 before:animate-ring-pulse">
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="relative z-[1]"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <h3 className="text-2xl font-semibold mb-2">You are all set</h3>
                <p className="text-[15px] text-zinc-400 leading-[1.6] mb-6">
                  Your workspace is ready. We are redirecting you to the dashboard.
                </p>
                <button type="button" className={btnCls} onClick={() => window.location.reload()}>
                  <span>Go to dashboard</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Onboarding Dialog (Survey + Platform Selection) */}
        {showDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => {}}
            />
            <div className="relative w-full max-w-lg bg-[rgb(9,9,11)] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden animate-fade-slide-up">
              {/* Dialog header */}
              <div className="flex items-center justify-between px-6 pt-6 pb-2">
                <div className="flex items-center gap-2">
                  <div className="size-5 rounded-lg bg-indigo-600 flex items-center justify-center">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="size-3">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <span className="text-sm font-semibold text-white">Quick setup</span>
                </div>
                <div className="flex gap-1">
                  {["survey", "comm", "pm"].map((s, i) => (
                    <div
                      key={s}
                      className={`size-2 rounded-full transition-colors duration-300 ${
                        ["survey", "comm", "pm"].indexOf(dialogStep) >= i ? "bg-indigo-500" : "bg-zinc-800"
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Survey */}
              {dialogStep === "survey" && (
                <div className="px-6 py-4">
                  <h3 className="text-base font-semibold text-white mb-1">Tell us about your team</h3>
                  <p className="text-xs text-zinc-400 mb-5">This helps us tailor the experience.</p>

                  <div className="relative mb-3">
                    <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]" htmlFor="surveyCompany">
                      Company name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      id="surveyCompany"
                      className={`${inputCls} ${errors.surveyCompany ? "!border-[#ef4444]" : "border-zinc-800"}`}
                      placeholder="Acme Industries"
                      value={surveyCompany}
                      onChange={(e) => {
                        setSurveyCompany(e.target.value);
                        clearError("surveyCompany");
                      }}
                    />
                    {errors.surveyCompany && (
                      <div className="text-xs text-red-500 mt-1.5 flex items-center gap-1">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        Company name is required
                      </div>
                    )}
                  </div>

                  <div className="relative mb-3">
                    <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]" htmlFor="surveyRole">
                      Your role
                    </label>
                    <select
                      id="surveyRole"
                      className={`${inputCls} border-zinc-800 appearance-none cursor-pointer`}
                      value={surveyRole}
                      onChange={(e) => setSurveyRole(e.target.value)}
                    >
                      <option value="" disabled>Select your role</option>
                      <option value="engineer">Engineer / Developer</option>
                      <option value="designer">Designer / Creative</option>
                      <option value="pm">Product Manager / Owner</option>
                      <option value="founder">Founder / CXO</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div className="relative mb-3">
                    <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]" htmlFor="surveyTeam">
                      Team size
                    </label>
                    <select
                      id="surveyTeam"
                      className={`${inputCls} border-zinc-800 appearance-none cursor-pointer`}
                      value={surveyTeam}
                      onChange={(e) => setSurveyTeam(e.target.value)}
                    >
                      <option value="" disabled>Select team size</option>
                      <option value="1-5">1–5 people</option>
                      <option value="6-20">6–20 people</option>
                      <option value="21-50">21–50 people</option>
                      <option value="50+">50+ people</option>
                    </select>
                  </div>

                  <div className="relative mb-4">
                    <label className="block text-[13px] font-medium text-zinc-400 mb-2 tracking-[0.01em]" htmlFor="surveySource">
                      How did you find us?
                    </label>
                    <select
                      id="surveySource"
                      className={`${inputCls} border-zinc-800 appearance-none cursor-pointer`}
                      value={surveySource}
                      onChange={(e) => setSurveySource(e.target.value)}
                    >
                      <option value="" disabled>Select one</option>
                      <option value="google">Google search</option>
                      <option value="social">Social media</option>
                      <option value="friend">Friend or colleague</option>
                      <option value="blog">Article / Blog</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div className={`flex gap-2 mt-2 ${errors.surveyCompany ? "animate-shake" : ""}`}>
                    <button type="button" className={`${btnCls} flex-1`} onClick={() => {
                      if (!surveyCompany.trim()) {
                        setErrors({ surveyCompany: true });
                        setTimeout(() => setErrors((p) => { const n = { ...p }; delete n.surveyCompany; return n; }), 400);
                        return;
                      }
                      setDialogStep("comm");
                    }}>
                      <span>Next</span>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M5 12h14" />
                        <path d="m12 5 7 7-7 7" />
                      </svg>
                    </button>
                    <button type="button" className="bg-transparent border border-zinc-800 text-zinc-500 h-[38px] px-4 rounded-xl text-xs font-medium cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-zinc-800 hover:text-zinc-300" onClick={() => setDialogStep("comm")}>
                      Skip
                    </button>
                  </div>
                </div>
              )}

              {/* Communication Platform */}
              {dialogStep === "comm" && (
                <div className="px-6 py-4">
                  <h3 className="text-base font-semibold text-white mb-1">Choose your Team Link</h3>
                  <p className="text-xs text-zinc-400 mb-5">Select your primary communication platform.</p>

                  <div className="grid grid-cols-3 gap-3 mb-5">
                    {platforms.comm.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        className={`flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer hover:scale-[1.03] ${
                          selectedComm === p.id
                            ? "border-indigo-500 bg-indigo-500/10 shadow-[0_0_0_3px_rgba(99,102,241,0.15)]"
                            : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 hover:bg-zinc-800/50"
                        }`}
                        onClick={() => setSelectedComm(p.id)}
                      >
                        <div
                          className="size-16 rounded-full flex items-center justify-center text-white text-xl font-bold font-['JetBrains_Mono',monospace] shadow-lg"
                          style={{ backgroundColor: p.color }}
                        >
                          {p.glyph}
                        </div>
                        <span className="text-[11px] font-medium text-zinc-300 leading-tight text-center">{p.name}</span>
                      </button>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <button type="button" className={`${btnCls} flex-1`} onClick={() => setDialogStep("pm")}>
                      <span>Next</span>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M5 12h14" />
                        <path d="m12 5 7 7-7 7" />
                      </svg>
                    </button>
                    <button type="button" className="bg-transparent border border-zinc-800 text-zinc-500 h-[38px] px-4 rounded-xl text-xs font-medium cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-zinc-800 hover:text-zinc-300" onClick={() => setDialogStep("pm")}>
                      Skip
                    </button>
                  </div>
                </div>
              )}

              {/* Project Management Platform */}
              {dialogStep === "pm" && (
                <div className="px-6 py-4">
                  <h3 className="text-base font-semibold text-white mb-1">Choose your Project Hub</h3>
                  <p className="text-xs text-zinc-400 mb-5">Select your primary project management platform.</p>

                  <div className="grid grid-cols-3 gap-3 mb-5">
                    {platforms.pm.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        className={`flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer hover:scale-[1.03] ${
                          selectedPm === p.id
                            ? "border-indigo-500 bg-indigo-500/10 shadow-[0_0_0_3px_rgba(99,102,241,0.15)]"
                            : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 hover:bg-zinc-800/50"
                        }`}
                        onClick={() => setSelectedPm(p.id)}
                      >
                        <div
                          className="size-16 rounded-full flex items-center justify-center text-white text-xl font-bold font-['JetBrains_Mono',monospace] shadow-lg"
                          style={{ backgroundColor: p.color }}
                        >
                          {p.glyph}
                        </div>
                        <span className="text-[11px] font-medium text-zinc-300 leading-tight text-center">{p.name}</span>
                      </button>
                    ))}
                  </div>

                  <button type="button" className={`${btnCls}`} onClick={handleDialogSkip}>
                    <span>Finish setup</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
