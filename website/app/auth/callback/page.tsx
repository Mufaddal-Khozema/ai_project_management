"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { StorageKeys } from "@/constants";

const SIGNUP_URL = "/signup";
const DASHBOARD_URL = "/dashboard";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"processing" | "error">("processing");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const error = params.get("error");

    if (error) {
      setStatus("error");
      const reason = params.get("reason") ?? error;
      setTimeout(() => router.replace(`${SIGNUP_URL}?error=${encodeURIComponent(reason)}`), 2000);
      return;
    }

    if (token) {
      localStorage.setItem(StorageKeys.TOKEN, token);
      router.replace(SIGNUP_URL);
      return;
    }

    // Cookie-based session approach: try to verify session
    // This requires a `/api/auth/me` endpoint to exist on the backend
    fetch("/api/auth/me", { credentials: "include" })
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error("not authenticated");
      })
      .then(() => {
        router.replace(SIGNUP_URL);
      })
      .catch(() => {
        // No token and no session — still go to signup
        router.replace(SIGNUP_URL);
      });
  }, [router]);

  if (status === "error") {
    return (
      <div className="min-h-screen bg-[rgb(9,9,11)] flex items-center justify-center">
        <div className="text-center">
          <div className="size-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">Authentication failed</h2>
          <p className="text-sm text-zinc-400">Redirecting you back to sign in…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[rgb(9,9,11)] flex items-center justify-center">
      <div className="text-center">
        <div className="size-16 rounded-full bg-indigo-600/20 flex items-center justify-center mx-auto mb-4">
          <div className="size-6 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">Signing you in</h2>
        <p className="text-sm text-zinc-400">Please wait…</p>
      </div>
    </div>
  );
}
