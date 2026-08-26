"use client";

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
  AlertTriangle,
} from "lucide-react";
import { OnboardingDialog } from "@/components/OnboardingDialog";
import { useCurrentUser, useSubmitOnboardingMutation, useIntegrations } from "@/lib/api";
import { integrationProviders, formatExpiry } from "@/lib/integrations";
import { useState, useMemo } from "react";

const adoptionData = weeks.map((w, i) => ({ week: w, value: adoption[i] }));
const gaugeData = [{ value: 78 }, { value: 22 }];

export default function DashboardPage() {
  const { data: user, isPending: userLoading } = useCurrentUser();
  const { data: integrationsData } = useIntegrations();
  const [onboarding, setOnboarding] = useState(true);
  const onboardingMutation = useSubmitOnboardingMutation();

  const integrationsById = useMemo(() => {
    const map: Record<string, { status: string; expires_at: string | null }> = {};
    for (const integration of integrationsData?.integrations ?? []) {
      map[integration.provider] = integration;
    }
    return map;
  }, [integrationsData]);
  return (
    <>
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Home</span>
            <span>&rsaquo;</span>
            <span>Coordination</span>
            <span>&rsaquo;</span>
            <span className="text-card-foreground">Dashboard</span>
          </div>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-card-foreground">
            Acme Engineering
          </h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            May 12 – Jun 10, 2026
          </Button>
          <Button size="sm">Generate report</Button>
        </div>
      </div>

      <div className="flex items-start gap-4 rounded-xl border border-border bg-card p-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-success-bg)]">
          <ShieldCheck size={18} className="text-[var(--color-success)]" />
        </div>
        <div>
          <p className="text-sm font-medium text-card-foreground">
            Team&apos;s on pace this week — adoption is climbing and two
            integrations need attention.
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Priya is carrying 4 active workstreams. MS Teams token expires in 3
            days.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <span className="text-xs text-muted-foreground">
                Hours saved
              </span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent">
                <Clock size={14} className="text-accent-foreground" />
              </div>
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-tight text-card-foreground">
              146
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                /mo
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1 text-xs text-[var(--color-success)]">
              <span>↑</span> 18% vs last month
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <span className="text-xs text-muted-foreground">Trust rate</span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-success-bg)]">
                <ShieldCheck size={14} className="text-[var(--color-success)]" />
              </div>
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-tight text-card-foreground">
              82%
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              confirmed without edits
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <span className="text-xs text-muted-foreground">
                Bot-led sprints closed
              </span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent">
                <Activity size={14} className="text-accent-foreground" />
              </div>
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-tight text-card-foreground">
              27
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                /31
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1 text-xs text-[var(--color-success)]">
              <span>↑</span> 87% on-time close rate
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <span className="text-xs text-muted-foreground">
                Active projects
              </span>
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-warning-bg)]">
                <FolderOpen size={14} className="text-[var(--color-warning)]" />
              </div>
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-tight text-card-foreground">
              11
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                /13
              </span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              2 not yet connected
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1.6fr_1fr] gap-4">
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
                        stopColor="#6366f1"
                        stopOpacity={0.25}
                      />
                      <stop
                        offset="100%"
                        stopColor="#6366f1"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke="rgba(255,255,255,0.04)"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="week"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#636366", fontSize: 11 }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#636366", fontSize: 11 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a1f",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "#f5f5f7",
                    }}
                    formatter={(v) => [`${v}% adoption`, ""]}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#6366f1"
                    strokeWidth={2}
                    fill="url(#adoptionGrad)"
                    dot={false}
                    activeDot={{
                      r: 5,
                      fill: "#6366f1",
                      stroke: "#09090b",
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
                    <Cell fill="#6366f1" />
                    <Cell fill="#1a1a1f" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-semibold text-card-foreground">
                  78
                </span>
                <span className="text-xs text-muted-foreground">strong</span>
              </div>
            </div>
            <p className="mt-3 text-center text-xs leading-relaxed text-muted-foreground">
              Composite of cycle time, rework rate, and on-time delivery across
              all active projects.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Organization capacity</CardTitle>
            <Badge variant="outline">86% allocated</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            {capacity.map((c) => (
              <div key={c.team}>
                <div className="mb-1.5 flex justify-between text-xs">
                  <span className="text-card-foreground">{c.team}</span>
                  <span className="text-muted-foreground">{c.percent}%</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${c.percent}%`, background: c.color }}
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
          <CardContent className="divide-y divide-border">
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
                    : "text-muted-foreground";
              const dotClass =
                tone === "ok"
                  ? "bg-[var(--color-success)]"
                  : tone === "warn"
                    ? "bg-[var(--color-warning)]"
                    : "bg-muted-foreground/50";

              return (
                <div
                  key={provider.id}
                  className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-3 text-sm text-card-foreground">
                    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-muted text-xs text-muted-foreground">
                      {provider.name[0]}
                    </div>
                    {provider.name}
                  </div>
                  <div className={`flex items-center gap-2 text-xs ${toneClass}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
                    {detail}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Live feed</CardTitle>
          <div className="flex items-center gap-2 text-xs text-[var(--color-success)]">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-success)]" />
            Live
          </div>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {feed.map((item) => (
            <div
              key={item.id}
              className="flex gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-[10px] font-medium text-muted-foreground">
                {item.isBot ? "🤖" : item.initials}
              </div>
              <div>
                <p className="text-sm text-card-foreground">
                  <span className="font-medium">{item.actor}</span> {item.text}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {item.time}
                </p>
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
        <CardContent className="divide-y divide-border">
          {projects
            .filter((p) => p.status === "at-risk")
            .map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
              >
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    {p.name}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Lead by {p.lead} · {p.tasksDone}/{p.tasksTotal} tasks
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <AvatarGroup>
                    {p.team.map((t) => (
                      <Avatar key={t} size="sm">
                        <AvatarFallback className="text-[10px]">{t}</AvatarFallback>
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
