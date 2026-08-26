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
  PanelLeft,
  ChevronLeft,
} from "lucide-react";
import { useState } from "react";
import { useCurrentUser } from "@/lib/api";
import { UserMenu } from "@/components/UserMenu";

const nav = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/projects", label: "Projects", icon: FolderKanban },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/reports", label: "Reports", icon: BarChart3 },
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

function SidebarUser({ collapsed }: { collapsed: boolean }) {
  const { data: user, isLoading } = useCurrentUser();
  const initials = user
    ? (user.name
        ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
        : user.email[0].toUpperCase())
    : "?";

  return (
    <div
      className={cn(
        "flex items-center gap-3",
        collapsed && "justify-center"
      )}
    >
      {user?.avatar ? (
        <img
          src={user.avatar}
          alt=""
          className="size-9 shrink-0 rounded-full object-cover"
        />
      ) : (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
          {isLoading ? (
            <div className="size-9 rounded-full bg-primary/50 animate-pulse" />
          ) : (
            initials
          )}
        </div>
      )}

      {!collapsed && (
        <div className="overflow-hidden">
          <p className="truncate text-sm font-medium text-card-foreground">
            {isLoading ? (
              <span className="inline-block h-4 w-24 rounded bg-muted animate-pulse" />
            ) : (
              user?.name ?? user?.email ?? "User"
            )}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {user?.email ?? ""}
          </p>
        </div>
      )}
    </div>
  );
}

  return (
    <div className="min-h-screen bg-background">

      {/* Overlay on mobile */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed z-40 flex flex-col",
          "left-4 top-4 bottom-4",
          "rounded-2xl border border-border bg-card shadow-xl",
          "transition-all duration-300 ease-in-out",

          // desktop
          collapsed ? "md:w-[72px]" : "md:w-[240px]",

          // mobile
          "w-[240px]",
          mobileOpen ? "translate-x-0" : "-translate-x-[120%]",

          // desktop always visible
          "md:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center px-5">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="h-7 w-7 shrink-0 rounded-lg bg-primary" />

            {!collapsed && (
              <span className="text-sm font-semibold tracking-tight text-card-foreground">
                Acme Eng
              </span>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-3">
          {nav.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/admin" &&
                pathname.startsWith(item.href));

            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  collapsed ? "justify-center" : "gap-3",

                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-card-foreground"
                )}
              >
                <Icon size={18} />

                {!collapsed && item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Content */}
      <main
        className={cn(
          "min-h-screen p-6 pt-7 transition-all duration-300",
          collapsed ? "md:ml-[104px]" : "md:ml-[272px]"
        )}
      >
        <div className="mx-auto max-w-6xl space-y-6">
          <div className="flex justify-between">
            {/* Floating toggle button */}
            <button
              onClick={() => {
                if (window.innerWidth < 768) {
                  setMobileOpen(!mobileOpen);
                } else {
                  setCollapsed(!collapsed);
                }
              }}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full",
                "border border-border bg-card shadow-md transition-all",
              )}
            >
              {collapsed || !mobileOpen ? (
                <PanelLeft size={18} />
              ) : (
                <ChevronLeft size={18} />
              )}
            </button>
            <UserMenu />
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
