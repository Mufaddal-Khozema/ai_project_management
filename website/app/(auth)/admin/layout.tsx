"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderKanban,
  Users,
  BarChart3,
  Settings,
} from "lucide-react";
import { useEffect, useRef } from "react";
import { UserMenu } from "@/components/UserMenu";
import { Orb } from "@/components/landing/orb";
import { Threads } from "@/components/landing/threads";
import { ThemeIcon } from "@/components/landing/icons";
import { useTheme } from "@/components/landing/use-theme";
import { StorageKeys } from "@/constants";

const nav = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/projects", label: "Projects", icon: FolderKanban },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/reports", label: "Reports", icon: BarChart3 },
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, href: string) {
  return (
    pathname === href ||
    (href !== "/admin" && pathname.startsWith(href))
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const shellRef = useRef<HTMLDivElement>(null);
  const { toggleTheme, preference, setThemePreference } = useTheme();

  useEffect(() => {
    try {
      if (!localStorage.getItem(StorageKeys.THEME)) {
        setThemePreference("light");
      }
    } catch {
      // ignore storage failures
    }
  }, [setThemePreference, preference]);

  useEffect(() => {
    const element = shellRef.current;
    if (!element) return;

    const handleMove = (event: PointerEvent) => {
      element.style.setProperty(
        "--ex",
        ((event.clientX / window.innerWidth - 0.5) * 2).toFixed(2),
      );
      element.style.setProperty(
        "--ey",
        ((event.clientY / window.innerHeight - 0.5) * 2).toFixed(2),
      );
    };

    window.addEventListener("pointermove", handleMove);
    return () => window.removeEventListener("pointermove", handleMove);
  }, []);

  return (
    <div
      ref={shellRef}
      className="admin-app relative isolate min-h-screen bg-canvas font-body text-ink"
    >
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossOrigin="anonymous"
      />
      <link
        rel="stylesheet"
        precedence="default"
        href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=Figtree:wght@400;500;600&display=swap"
      />

      <Threads className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-60" />

      <div className="mx-auto flex max-w-[1320px] gap-6 px-4 pt-4 pb-28 md:gap-7 md:px-6 md:py-6 md:pb-6">
        {/* Desktop rail */}
        <nav
          aria-label="Main"
          className="sticky top-6 hidden h-[calc(100dvh-3rem)] w-[96px] shrink-0 flex-col items-center gap-2 rounded-[36px] bg-canvas p-4 shadow-raise md:flex"
        >
          {nav.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "grid w-[76px] justify-items-center gap-1 rounded-[22px] py-2.5 text-center text-xs font-semibold text-ink-muted transition-all hover:text-ink",
                  active && "text-ink shadow-press",
                )}
              >
                <Icon
                  size={22}
                  className={cn(active && "text-[#6d5ef0]")}
                />
                {item.label}
              </Link>
            );
          })}

          <div className="flex-1" />

          <button
            type="button"
            aria-label="Switch light or dark theme"
            onClick={toggleTheme}
            className="inline-flex size-11 items-center justify-center rounded-full bg-canvas text-ink shadow-soft active:shadow-press"
          >
            <ThemeIcon />
          </button>
        </nav>

        {/* Content */}
        <main className="min-w-0 flex-1">
          <header className="mb-6 flex flex-wrap items-center gap-3">
            <Orb size="sm" />
            <strong className="font-display text-xl font-extrabold tracking-tight">
              CoordinaAI
            </strong>
            <span className="flex-1" />
            <span className="inline-flex items-center gap-2 rounded-full bg-canvas px-3.5 py-1.5 text-[13px] font-semibold text-ink shadow-press">
              <span className="size-2 rounded-full bg-[#1f9d6b]" />
              Acme Eng · Pro trial
            </span>
            <button
              type="button"
              aria-label="Switch light or dark theme"
              onClick={toggleTheme}
              className="inline-flex size-11 items-center justify-center rounded-full bg-canvas text-ink shadow-soft active:shadow-press md:hidden"
            >
              <ThemeIcon />
            </button>
            <UserMenu />
          </header>

          <div className="space-y-5">{children}</div>
        </main>
      </div>

      {/* Mobile bottom rail */}
      <nav
        aria-label="Main"
        className="fixed inset-x-3 bottom-3 z-40 flex items-center justify-around rounded-[28px] bg-canvas p-1.5 shadow-raise md:hidden"
      >
        {nav.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "grid flex-1 justify-items-center gap-1 rounded-[22px] py-2 text-[11px] font-semibold text-ink-muted transition-all",
                active && "text-ink shadow-press",
              )}
            >
              <Icon
                size={20}
                className={cn(active && "text-[#6d5ef0]")}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
