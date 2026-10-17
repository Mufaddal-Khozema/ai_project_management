"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { client } from "@/lib/api";
import { StorageKeys } from "@/constants";

export function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function AuthenticatedRoute(props: P) {
    const router = useRouter();
    const [checking, setChecking] = useState(true);

    useEffect(() => {
      const token = localStorage.getItem(StorageKeys.TOKEN);
      if (token) {
        // Set token as cookie so backend JWT middleware can read it
        document.cookie = `${StorageKeys.TOKEN}=${token}; path=/; max-age=${60 * 60 * 24 * 365}; secure}`;
        // Also ensure the Hey API client auth config has the token for SDK requests
        client.setConfig({
          auth: () => localStorage.getItem(StorageKeys.TOKEN) ?? undefined,
        });
      } else {
        router.replace("/signup");
      }
      setChecking(false);
    }, [router]);

    if (checking) {
      return (
        <div className="min-h-screen bg-[rgb(9,9,11)] flex items-center justify-center">
          <div className="size-6 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        </div>
      );
    }

    return <Component {...props} />;
  };
}
