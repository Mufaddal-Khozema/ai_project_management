"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { StorageKeys } from "@/constants";

export function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function AuthenticatedRoute(props: P) {
    const router = useRouter();
    const [checking, setChecking] = useState(true);

    useEffect(() => {
      const token = localStorage.getItem(StorageKeys.TOKEN);
      if (!token) {
        router.replace("/signup");
      } else {
        setChecking(false);
      }
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
