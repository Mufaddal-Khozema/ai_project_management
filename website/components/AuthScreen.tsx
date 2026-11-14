"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSendOtpMutation, useVerifyOtpMutation } from "@/lib/api/@tanstack/react-query.gen";
import { getCurrentUser } from "@/lib/api/sdk.gen";
import { establishSession } from "@/lib/api";
import { API_URL, StorageKeys } from "@/constants";
import { Orb } from "@/components/landing/orb";
import { Threads } from "@/components/landing/threads";
import { ThemeIcon } from "@/components/landing/icons";
import { useLandingTheme } from "@/components/landing/use-theme";

type AuthScreenMode = "signup" | "signin";

type ApiProblem = {
  status?: number;
  detail?: string;
};

const btnCls =
  "inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 text-sm font-semibold text-white shadow-soft transition-all active:shadow-press disabled:cursor-not-allowed disabled:opacity-50";
const socialBtnCls =
  "inline-flex h-12 w-full items-center justify-center gap-2.5 rounded-xl bg-canvas text-sm font-medium text-ink shadow-soft transition-all hover:shadow-raise active:shadow-press disabled:cursor-not-allowed disabled:opacity-50";
const inputCls =
  "h-12 w-full rounded-xl bg-canvas px-4 text-base text-ink shadow-press outline-none transition-all placeholder:text-ink-muted focus:outline-2 focus:outline-blue-500";

const STATS = [
  { value: "12K+", label: "Teams synced" },
  { value: "4.2M", label: "Tasks routed" },
  { value: "98.7%", label: "Uptime" },
];

function asProblem(error: unknown): ApiProblem {
  return typeof error === "object" && error !== null ? (error as ApiProblem) : {};
}

export default function AuthScreen({ mode }: { mode: AuthScreenMode }) {
  const router = useRouter();
  const isSignin = mode === "signin";
  const { toggleTheme } = useLandingTheme();
  const [authMode, setAuthMode] = useState<"social" | "otp">("social");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [emailLoading, setEmailLoading] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [created, setCreated] = useState(false);

  const sendOtpMutation = useSendOtpMutation();
  const verifyOtpMutation = useVerifyOtpMutation();
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  const getPostAuthPath = async () => {
    try {
      const { data } = await getCurrentUser();
      return data?.has_subscription ? "/admin?onboarding=1" : "/plans";
    } catch {
      return "/plans";
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get(StorageKeys.TOKEN);
    const error = params.get("error");

    if (!error && !token) {
      // Only check auth state if we have an existing token (e.g. from a prior OAuth flow).
      // Don't redirect new signups if no token exists.
      if (localStorage.getItem(StorageKeys.TOKEN)) {
        getPostAuthPath().then((dest) => router.replace(dest));
      }
      return;
    }

    const timer = setTimeout(() => {
      if (error) {
        setOauthError(error === "oauth" ? "Google or GitHub" : error);
        return;
      }

      if (!token) return;
      setOauthLoading(true);
      localStorage.setItem(StorageKeys.TOKEN, token);
      void establishSession(token);
      window.history.replaceState(null, "", isSignin ? "/signin" : "/signup");
      setTimeout(() => {
        setOauthLoading(false);
        setCreated(true);
      }, 600);
    }, 0);

    return () => clearTimeout(timer);
  }, [router, isSignin]);

  useEffect(() => {
    if (authMode === "otp") {
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    }
  }, [authMode]);

  useEffect(() => {
    if (created) {
      const t = setTimeout(async () => {
        const dest = await getPostAuthPath();
        router.push(dest);
      }, 2000);
      return () => clearTimeout(t);
    }
  }, [created, router]);

  const handleEmailSubmit = () => {
    if (emailLoading) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setEmailError("Please enter a valid email address");
      return;
    }
    setEmailError(null);
    setEmailLoading(true);
    sendOtpMutation.mutate(
      { body: { email: email.trim(), purpose: mode } },
      {
        onSuccess: () => {
          setEmailLoading(false);
          setAuthMode("otp");
          setOtpError(null);
        },
        onError: (error) => {
          setEmailLoading(false);
          const { status } = asProblem(error);
          if (isSignin && status === 404) {
            setEmailError("No account found for this email. Create an account instead.");
          } else if (!isSignin && status === 409) {
            setEmailError("This email is already registered. Sign in instead.");
          } else {
            setEmailError("Something went wrong. Please try again.");
          }
        },
      }
    );
  };

  const verifyOtp = (code: string) => {
    setOtpLoading(true);
    verifyOtpMutation.mutate(
      { body: { email: email.trim(), otp: code } },
      {
        onSuccess: (data) => {
          const body = data as { token?: string; access_token?: string };
          const accessToken = body.token ?? body.access_token;
          if (accessToken) {
            localStorage.setItem(StorageKeys.TOKEN, accessToken);
            void establishSession(accessToken);
          }
          setOtpLoading(false);
          setCreated(true);
        },
        onError: () => {
          setOtpLoading(false);
          setOtpError("Invalid or expired code. Try again.");
        },
      }
    );
  };

  const handleOtpChange = (i: number, val: string) => {
    if (val.length > 1) return;
    const next = [...otp];
    next[i] = val;
    setOtp(next);
    setOtpError(null);
    if (val && i < 5) otpRefs.current[i + 1]?.focus();
    if (i === 5 && val) verifyOtp([...otp.slice(0, 5), val].join(""));
  };

  const handleOtpKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) otpRefs.current[i - 1]?.focus();
  };

  if (created) {
    return (
      <div
        className="landing relative isolate flex min-h-screen items-center justify-center bg-canvas px-6 font-body text-ink"
      >
        <Threads className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-60" />
        <div className="text-center">
          <div className="mx-auto mb-6 grid size-20 place-items-center rounded-full bg-canvas shadow-raise">
            <span className="grid size-14 place-items-center rounded-full bg-gradient-to-br from-indigo-600 to-blue-600 text-white shadow-soft">
              <svg
                className="size-7"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
          </div>
          <h3 className="font-display text-2xl font-extrabold tracking-tight">
            {isSignin ? "Welcome back" : "Workspace created"}
          </h3>
          <p className="mt-2 text-sm text-ink-muted">
            {isSignin
              ? "Signing you in…"
              : "Welcome to Coordina. Choosing your plan…"}
          </p>
          <div className="mx-auto mt-5 size-5 animate-spin rounded-full border-2 border-indigo-500/30 border-t-indigo-500" />
        </div>
      </div>
    );
  }

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
              {isSignin ? "Sign in" : "Onboarding"}
            </div>
            <h1 className="font-display text-3xl font-extrabold leading-none tracking-tight text-white sm:text-4xl lg:text-5xl">
              Where projects find their rhythm.
            </h1>
            <p className="mt-4 max-w-md text-indigo-100/80">
              {isSignin
                ? "Welcome back. Pick up exactly where your team left off."
                : "Join the teams who have replaced status meetings with intelligent coordination."}
            </p>
            <div className="mt-8 hidden grid-cols-3 gap-6 border-t border-white/20 pt-6 sm:grid">
              {STATS.map((stat) => (
                <div key={stat.label} className="flex flex-col gap-1">
                  <span className="font-display text-2xl font-extrabold text-white">
                    {stat.value}
                  </span>
                  <span className="text-xs tracking-wide text-indigo-200/70">
                    {stat.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center border-t border-hairline bg-canvas p-6 sm:p-10 lg:col-span-2 lg:border-t-0 lg:border-l">
          <div className="w-full max-w-md">
            <div className="mb-7 flex items-center gap-2.5">
              <Link href="/" className="flex items-center gap-2.5">
                <Orb />
                <span className="font-display text-lg font-extrabold">
                  CoordinaAI
                </span>
              </Link>
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
              {isSignin ? "Welcome back" : "Join the network"}
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              {isSignin
                ? "Sign in to your workspace and keep things moving."
                : "Fast setup. Start coordinating in minutes."}
            </p>

            {oauthError && (
              <div className="mt-5 flex items-center gap-2 rounded-xl bg-red-500/10 p-3 text-xs text-red-500">
                <svg
                  className="size-4 shrink-0"
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
                <span>
                  Sign in with {oauthError} failed. Try again or use email.
                </span>
              </div>
            )}

            {authMode === "social" ? (
              <>
                <div className="mt-6 flex flex-col gap-2.5">
                  <button
                    type="button"
                    className={socialBtnCls}
                    onClick={() => {
                      window.location.href = `${API_URL}/api/auth/google/login`;
                    }}
                    disabled={oauthLoading}
                  >
                    {oauthLoading ? (
                      <span className="size-5 animate-spin rounded-full border-2 border-ink/30 border-t-ink" />
                    ) : (
                      <svg className="size-5" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                      </svg>
                    )}
                    Continue with Google
                  </button>

                  <button
                    type="button"
                    className={socialBtnCls}
                    onClick={() => {
                      window.location.href = `${API_URL}/api/auth/github/login`;
                    }}
                    disabled={oauthLoading}
                  >
                    {oauthLoading ? (
                      <span className="size-5 animate-spin rounded-full border-2 border-ink/30 border-t-ink" />
                    ) : (
                      <svg className="size-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                      </svg>
                    )}
                    Continue with GitHub
                  </button>
                </div>

                <div className="my-4 flex items-center gap-4 text-xs font-medium text-ink-muted before:h-px before:flex-1 before:bg-hairline after:h-px after:flex-1 after:bg-hairline">
                  or with email
                </div>

                <div>
                  <label
                    htmlFor="email"
                    className="mb-2 block text-sm font-medium text-ink-muted"
                  >
                    Work email
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      id="email"
                      className={`peer ${inputCls} pr-12 ${
                        emailError ? "outline-2 outline-red-500" : ""
                      }`}
                      placeholder="alex@company.com"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setEmailError(null);
                      }}
                      onKeyDown={(e) => e.key === "Enter" && handleEmailSubmit()}
                    />
                    <svg
                      className="pointer-events-none absolute top-1/2 right-4 size-5 -translate-y-1/2 text-ink-muted peer-focus:text-indigo-500"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </div>
                  <div
                    className={`mt-1.5 flex items-center gap-1 text-xs text-red-500 transition-all ${
                      emailError
                        ? "translate-y-0 opacity-100"
                        : "-translate-y-1 opacity-0"
                    }`}
                  >
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
                    {emailError ?? "Please enter a valid email address"}
                  </div>
                </div>

                <button
                  type="button"
                  className={`${btnCls} mt-4`}
                  onClick={handleEmailSubmit}
                  disabled={emailLoading}
                >
                  <span>Continue with email</span>
                  {emailLoading && (
                    <span className="size-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  )}
                  {!emailLoading && (
                    <svg
                      className="size-5"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M5 12h14" />
                      <path d="m12 5 7 7-7 7" />
                    </svg>
                  )}
                </button>

                <div className="mt-6 text-center text-xs text-ink-muted">
                  {isSignin ? "Don't have an account? " : "Already have an account? "}
                  <Link
                    href={isSignin ? "/signup" : "/signin"}
                    className="font-semibold text-ink no-underline transition-colors hover:text-indigo-500"
                  >
                    {isSignin ? "Sign up" : "Sign in"}
                  </Link>
                </div>

                <div className="mt-8 flex items-center justify-center gap-5 border-t border-hairline pt-6 text-xs text-ink-muted">
                  <Link href="/terms" className="transition-colors hover:text-ink">
                    Terms
                  </Link>
                  <span aria-hidden="true">•</span>
                  <Link href="/privacy" className="transition-colors hover:text-ink">
                    Privacy
                  </Link>
                </div>
              </>
            ) : (
              <>
                <div className="mt-6 mb-4">
                  <p className="mb-1 text-xs text-ink-muted">
                    Code sent to{" "}
                    <span className="font-medium text-ink">{email}</span>
                  </p>
                  <button
                    type="button"
                    className="cursor-pointer border-none bg-transparent p-0 text-xs font-semibold text-indigo-500 hover:opacity-80"
                    onClick={() => {
                      setAuthMode("social");
                      setOtp(["", "", "", "", "", ""]);
                      setOtpError(null);
                    }}
                  >
                    Change email
                  </button>
                </div>

                <label className="mb-3 block text-sm font-medium text-ink-muted">
                  Enter verification code
                </label>
                <div className="mb-2 flex justify-between gap-2">
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
                      className={`h-12 w-11 rounded-xl bg-canvas text-center font-mono text-lg font-medium text-ink shadow-press outline-none transition-all focus:outline-2 focus:outline-blue-500 sm:w-12 ${
                        otpError ? "outline-2 outline-red-500" : ""
                      }`}
                    />
                  ))}
                </div>
                <div
                  className={`mb-3 flex items-center gap-1 text-xs text-red-500 transition-all ${
                    otpError
                      ? "translate-y-0 opacity-100"
                      : "-translate-y-1 opacity-0"
                  }`}
                >
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
                  {otpError ?? "Invalid or expired code. Try again."}
                </div>

                <button
                  type="button"
                  className={`${btnCls} mt-2`}
                  disabled={otpLoading || otp.some((d) => !d)}
                  onClick={() => verifyOtp(otp.join(""))}
                >
                  <span>Verify &amp; continue</span>
                  {otpLoading && (
                    <span className="size-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  )}
                </button>

                <div className="mt-4 text-center">
                  <button
                    type="button"
                    className="cursor-pointer border-none bg-transparent p-0 text-xs text-ink-muted hover:text-ink"
                  >
                    Resend code
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
