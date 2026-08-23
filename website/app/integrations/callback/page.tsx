"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { INTEGRATION_OAUTH_MESSAGE } from "@/lib/integrations";

function CallbackContent() {
  const searchParams = useSearchParams();
  const [popup] = useState(() => typeof window !== "undefined" && Boolean(window.opener));

  useEffect(() => {
    const provider = searchParams.get("provider") ?? "";
    const status = searchParams.get("status") ?? "";
    const source = searchParams.get("source") ?? "settings";

    if (popup) {
      window.opener?.postMessage(
        { type: INTEGRATION_OAUTH_MESSAGE, provider, status },
        window.location.origin,
      );
      window.close();
      return;
    }

    window.location.replace(
      source === "onboarding" ? "/admin?onboarding=1" : "/admin/settings",
    );
  }, [popup, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="size-8 animate-spin rounded-full border-2 border-zinc-700 border-t-zinc-200" />
        <p className="text-sm text-zinc-400">
          {popup
            ? "Connection complete — you can close this window."
            : "Connection complete — redirecting…"}
        </p>
      </div>
    </div>
  );
}

export default function IntegrationCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-zinc-950">
          <div className="size-8 animate-spin rounded-full border-2 border-zinc-700 border-t-zinc-200" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}