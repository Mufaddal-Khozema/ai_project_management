"use client";

import Link from "next/link";
import type { ComponentType, CSSProperties } from "react";
import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarGroup } from "@/components/ui/avatar";
import {
  weeks,
  adoption,
  projects,
  feed,
  capacity,
} from "@/lib/data";
import {
  Activity,
  Clock,
  ShieldCheck,
  FolderOpen,
  FolderKanban,
  Users as UsersIcon,
  BarChart3,
  AlertTriangle,
  ArrowUpRight,
} from "lucide-react";
import { OnboardingDialog } from "@/components/OnboardingDialog";
import {
  useCurrentUser,
  useSubmitOnboardingMutation,
  useIntegrations,
} from "@/lib/api/@tanstack/react-query.gen";
import { integrationProviders, formatExpiry } from "@/lib/integrations";
import { Orb } from "@/components/landing/orb";
import { Threads } from "@/components/landing/threads";
import { cn } from "@/lib/utils";

const adoptionData = weeks.map((w, i) => ({ week: w, value: adoption[i] }));
const gaugeData = [{ value: 78 }, { value: 22 }];

const chartTooltip: CSSProperties = {
  background: "var(--ca-bg)",
  border: "1px solid var(--ca-line)",
  borderRadius: 16,
  fontSize: 12,
  color: "var(--ca-ink)",
  boxShadow: "4px 4px 9px var(--ca-lo), -4px -4px 9px var(--ca-hi)",
};

const focusCards = [
  {
    href: "/admin/projects",
    icon: FolderKanban,
    title: "Track projects",
    detail: "See health, scope changes and what needs attention.",
  },
  {
    href: "/admin/users",
    icon: UsersIcon,
    title: "Team capacity",
    detail: "Workload, velocity and trust across every teammate.",
  },
  {
    href: "/admin/reports",
    icon: BarChart3,
    title: "Read reports",
    detail: "Adoption, delivery and contribution analytics.",
  },
];

function StatCard({
  icon: Icon,
  label,
  value,
  suffix,
  detail,
  tone = "accent",
}: {
  icon: ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: string;
  suffix?: string;
  detail: string;
  tone?: "accent" | "success" | "warning";
}) {
  const toneClass =
    tone === "success"
      ? "text-[var(--color-success)]"
      : tone === "warning"
        ? "text-[var(--color-warning)]"
        : "text-[#6d5ef0]";
  const detailClass =
    tone === "success" ? "text-[var(--color-success)]" : "text-ink-muted";

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-start justify-between">
          <span className="text-xs font-semibold text-ink-muted">{label}</span>
          <div className="grid size-8 place-items-center rounded-xl bg-canvas shadow-press">
            <Icon size={14} className={toneClass} />
          </div>
        </div>
        <div className="mt-3 font-display text-3xl font-extrabold tracking-tight">
          {value}
          {suffix && (
            <span className="ml-1 font-body text-sm font-normal text-ink-muted">
              {suffix}
            </span>
          )}
        </div>
        <div className={cn("mt-1 text-xs font-semibold", detailClass)}>
          {detail}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: user, isPending: userLoading } = useCurrentUser();
  const { data: integrationsData } = useIntegrations();
  const [onboarding, setOnboarding] = useState(true);
  const onboardingMutation = useSubmitOnboardingMutation();

  const firstName = user?.name?.split(" ")[0] ?? "there";

  const integrationsById = useMemo(() => {
    const map: Record<string, { status: string; expires_at: string | null }> = {};
    for (const integration of integrationsData?.integrations ?? []) {
      map[integration.provider] = integration;
    }
    return map;
  }, [integrationsData]);

  return (
    <>
      {/* Hero */}
      <section
        className="relative overflow-hidden rounded-[36px] p-6 text-white shadow-raise sm:p-9"
        style={{
          background:
            "linear-gradient(120deg,#4b2fd0 0%,#b0389f 48%,#ee5a45 82%,#f59a2d 100%)",
        }}
      >
        <Threads
          tone="mono"
          className="pointer-events-none absolute inset-0 h-full w-full opacity-50"
        />
        <div className="relative grid items-center gap-6 lg:grid-cols-[1fr_auto]">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-white/70">
              <span>Home</span>
              <span>&rsaquo;</span>
              <span>Coordination</span>
              <span>&rsaquo;</span>
              <span className="text-white">Dashboard</span>
            </div>
            <h1 className="mt-3 max-w-[18ch] font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
              Good morning, {firstName}.{" "}
              <span className="text-white/80">
                Team&apos;s on pace this week.
              </span>
            </h1>
            <p className="mt-3 max-w-xl text-sm text-white/80">
              Adoption is climbing and two integrations need attention. Priya
              is carrying 4 active workstreams. The MS Teams token expires in 3
              days.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              {integrationProviders.map((provider) => {
                const integration = integrationsById[provider.id];
                const connected = integration?.status === "connected";
                const expired =
                  integration?.status === "expired" ||
                  integration?.status === "error";
                return (
                  <span
                    key={provider.id}
                    className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[13px] font-semibold text-white"
                  >
                    <span
                      className={cn(
                        "size-2 rounded-full",
                        connected
                          ? "bg-[#9bffd3]"
                          : expired
                            ? "bg-[#ffe08a]"
                            : "bg-white/50",
                      )}
                    />
                    {provider.name}
                    {expired ? " expired" : ""}
                  </span>
                );
              })}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-2">
              <Button variant="secondary" size="sm">
                May 12 – Jun 10, 2026
              </Button>
              <Button
                size="sm"
                className="bg-none bg-white text-[#27305a] hover:bg-white"
              >
                Generate report
              </Button>
            </div>
          </div>

          <Orb size="xl" className="hidden justify-self-center sm:grid" />
        </div>
      </section>

      {/* Focus cards */}
      <div className="grid gap-5 md:grid-cols-3">
        {focusCards.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.href}
              href={card.href}
              className="group grid gap-2.5 rounded-[28px] bg-canvas p-6 shadow-raise transition-shadow hover:shadow-press"
            >
              <span className="grid size-12 place-items-center rounded-2xl bg-canvas text-[#8b5cf6] shadow-press">
                <Icon size={22} />
              </span>
              <h3 className="font-display text-lg font-extrabold tracking-tight">
                {card.title}
              </h3>
              <p className="text-sm text-ink-muted">{card.detail}</p>
              <span className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-[#6d5ef0]">
                Open <ArrowUpRight size={12} />
              </span>
            </Link>
          );
        })}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          icon={Clock}
          label="Hours saved"
          value="146"
          suffix="/mo"
          detail="↑ 18% vs last month"
          tone="success"
        />
        <StatCard
          icon={ShieldCheck}
          label="Trust rate"
          value="82%"
          detail="confirmed without edits"
          tone="success"
        />
        <StatCard
          icon={Activity}
          label="Bot-led sprints closed"
          value="27"
          suffix="/31"
          detail="↑ 87% on-time close rate"
          tone="success"
        />
        <StatCard
          icon={FolderOpen}
          label="Active projects"
          value="11"
          suffix="/13"
          detail="2 not yet connected"
          tone="warning"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.6fr_1fr]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Adoption rate over time</CardTitle>
            <Badge variant="outline">% of work routed via bot</Badge>
          </CardHeader>
          <CardContent className="pb-4">
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={adoptionData}>
                  <defs>
                    <linearGradient
                      id="adoptionGrad"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="#8b5cf6"
                        stopOpacity={0.35}
                      />
                      <stop
                        offset="100%"
                        stopColor="#8b5cf6"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke="var(--ca-line)"
                    strokeOpacity={0.45}
                    vertical={false}
                  />
                  <XAxis
                    dataKey="week"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "var(--ca-mute)", fontSize: 11 }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "var(--ca-mute)", fontSize: 11 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={chartTooltip}
                    formatter={(v) => [`${v}% adoption`, ""]}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    fill="url(#adoptionGrad)"
                    dot={false}
                    activeDot={{
                      r: 5,
                      fill: "#8b5cf6",
                      stroke: "var(--ca-bg)",
                      strokeWidth: 2,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Organizational efficiency</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center pb-5">
            <div className="relative h-[160px] w-[160px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={gaugeData}
                    startAngle={225}
                    endAngle={-45}
                    innerRadius="78%"
                    outerRadius="100%"
                    cornerRadius={4}
                    paddingAngle={0}
                    dataKey="value"
                    stroke="none"
                  >
                    <Cell fill="#8b5cf6" />
                    <Cell fill="var(--ca-line)" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-display text-3xl font-extrabold">
                  78
                </span>
                <span className="text-xs text-ink-muted">strong</span>
              </div>
            </div>
            <p className="mt-3 max-w-xs text-center text-xs leading-relaxed text-ink-muted">
              Composite of cycle time, rework rate, and on-time delivery across
              all active projects.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Capacity + integrations */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Organization capacity</CardTitle>
            <Badge variant="outline">86% allocated</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            {capacity.map((c) => (
              <div key={c.team}>
                <div className="mb-1.5 flex justify-between text-xs">
                  <span className="font-medium text-ink">{c.team}</span>
                  <span className="text-ink-muted">{c.percent}%</span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full shadow-press">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#ff5fa2] via-[#8b5cf6] to-[#4f7cff]"
                    style={{ width: `${c.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Integration health</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-hairline">
            {integrationProviders.map((provider) => {
              const integration = integrationsById[provider.id];
              const expiresText = integration
                ? formatExpiry(integration.expires_at)
                : "";
              const expired =
                integration?.status === "expired" ||
                expiresText === "Token expired";
              const isError = integration?.status === "error";

              let detail = "Not connected";
              let tone: "muted" | "ok" | "warn" = "muted";
              if (expired) {
                detail = "Token expired — reauthorize";
                tone = "warn";
              } else if (isError) {
                detail = "Connection error";
                tone = "warn";
              } else if (expiresText && !provider.refreshable) {
                detail = expiresText;
                tone = "warn";
              } else if (integration) {
                detail = "Synced …";
                tone = "ok";
              }

              const toneClass =
                tone === "ok"
                  ? "text-[var(--color-success)]"
                  : tone === "warn"
                    ? "text-[var(--color-warning)]"
                    : "text-ink-muted";
              const dotClass =
                tone === "ok"
                  ? "bg-[var(--color-success)]"
                  : tone === "warn"
                    ? "bg-[var(--color-warning)]"
                    : "bg-ink-muted/50";

              return (
                <div
                  key={provider.id}
                  className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-3 text-sm font-medium text-ink">
                    <div className="grid size-7 place-items-center rounded-lg bg-canvas text-xs text-ink-muted shadow-press">
                      {provider.name[0]}
                    </div>
                    {provider.name}
                  </div>
                  <span
                    className={cn(
                      "inline-flex items-center gap-2 rounded-full bg-canvas px-3 py-1 text-xs font-semibold shadow-press",
                      toneClass,
                    )}
                  >
                    <span className={cn("size-2 rounded-full", dotClass)} />
                    {detail}
                  </span>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Feed + projects needing attention */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Live feed</CardTitle>
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--color-success)]">
              <span className="size-2 animate-pulse rounded-full bg-[var(--color-success)]" />
              Live
            </div>
          </CardHeader>
          <CardContent className="divide-y divide-hairline">
            {feed.map((item) => (
              <div
                key={item.id}
                className="flex gap-3 py-3 first:pt-0 last:pb-0"
              >
                {item.isBot ? (
                  <Orb size="sm" className="size-8" />
                ) : (
                  <div className="grid size-8 shrink-0 place-items-center rounded-full bg-canvas text-[10px] font-semibold text-ink-muted shadow-soft">
                    {item.initials}
                  </div>
                )}
                <div>
                  <p className="text-sm text-ink">
                    <span className="font-semibold">{item.actor}</span>{" "}
                    {item.text}
                  </p>
                  <p className="mt-0.5 text-xs text-ink-muted">{item.time}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Projects needing attention</CardTitle>
            <Badge variant="destructive">2 at risk</Badge>
          </CardHeader>
          <CardContent className="divide-y divide-hairline">
            {projects
              .filter((p) => p.status === "at-risk")
              .map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink">
                      {p.name}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-muted">
                      Lead by {p.lead} · {p.tasksDone}/{p.tasksTotal} tasks
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <AvatarGroup>
                      {p.team.map((t) => (
                        <Avatar key={t} size="sm">
                          <AvatarFallback className="text-[10px]">
                            {t}
                          </AvatarFallback>
                        </Avatar>
                      ))}
                    </AvatarGroup>
                    <Badge
                      variant="outline"
                      className="flex items-center gap-1 text-[var(--color-warning)]"
                    >
                      <AlertTriangle size={10} />
                      {p.scopeChange}
                    </Badge>
                  </div>
                </div>
              ))}
          </CardContent>
        </Card>
      </div>

      <OnboardingDialog
        open={!userLoading && onboarding && !user?.onboarding_completed}
        onComplete={(data) => {
          onboardingMutation.mutate({ body: data });
          setOnboarding(false);
        }}
      />
    </>
  );
}
