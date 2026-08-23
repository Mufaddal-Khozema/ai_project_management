"use client";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { reportData, weeks, adoption, projects, users } from "@/lib/data";
import {
  Download,
  ArrowUpRight,
  Users as UsersIcon,
  FolderKanban,
  Activity,
} from "lucide-react";
import { useState, useMemo } from "react";

const adoptionData = weeks.map((w, i) => ({ week: w, value: adoption[i] }));

const COLORS = [
  "#6366f1",
  "#34d399",
  "#fbbf24",
  "#f87171",
  "#a78bfa",
  "#22d3ee",
  "#fb923c",
];

export default function ReportsPage() {
  const [range, setRange] = useState("10w");
  const [project, setProject] = useState("all");

  const velocityData = useMemo(() => {
    if (range === "4w") return reportData.projectVelocity.slice(-4);
    return reportData.projectVelocity;
  }, [range]);

  const totalCommits = reportData.userContributions.reduce(
    (a, b) => a + b.commits,
    0
  );
  const totalReviews = reportData.userContributions.reduce(
    (a, b) => a + b.reviews,
    0
  );
  const avgVelocity =
    velocityData.reduce(
      (acc, v) => acc + v.platform + v.mobile + v.design + v.qa,
      0
    ) /
    (velocityData.length * 4);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-card-foreground">
            Reports
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Precision analytics across projects and team members
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={range} onValueChange={(v) => v && setRange(v)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="4w">4 weeks</SelectItem>
              <SelectItem value="10w">10 weeks</SelectItem>
              <SelectItem value="q">Quarter</SelectItem>
            </SelectContent>
          </Select>
          <Select value={project} onValueChange={(v) => v && setProject(v)}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All projects</SelectItem>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button size="sm" className="gap-2">
            <Download size={14} />
            Export
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-full w-1/2 bg-gradient-to-l from-primary/5 to-transparent" />
          <CardContent className="pt-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Activity size={13} className="text-primary" />
              Avg. team velocity
            </div>
            <div className="mt-2 text-2xl font-semibold text-card-foreground">
              {avgVelocity.toFixed(1)}
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                pts/wk
              </span>
            </div>
            <div className="mt-1 text-xs text-[var(--color-success)]">
              ↑ 6.2% vs prior period
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-full w-1/2 bg-gradient-to-l from-[var(--color-success)]/5 to-transparent" />
          <CardContent className="pt-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <UsersIcon size={13} className="text-[var(--color-success)]" />
              Total contributions
            </div>
            <div className="mt-2 text-2xl font-semibold text-card-foreground">
              {totalCommits}
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                commits
              </span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {totalReviews} code reviews
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-full w-1/2 bg-gradient-to-l from-[var(--color-warning)]/5 to-transparent" />
          <CardContent className="pt-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <FolderKanban
                size={13}
                className="text-[var(--color-warning)]"
              />
              Active scope
            </div>
            <div className="mt-2 text-2xl font-semibold text-card-foreground">
              {projects.filter((p) => p.status !== "completed").length}
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                projects
              </span>
            </div>
            <div className="mt-1 text-xs text-[var(--color-danger)]">
              {projects.filter((p) => p.status === "at-risk").length} flagged
              at risk
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" data-horizontal="true">
        <TabsList className="mb-2">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="projects">Project drill-down</TabsTrigger>
          <TabsTrigger value="users">User drill-down</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Velocity trends</CardTitle>
                <Badge variant="outline">Story points delivered</Badge>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={velocityData}>
                      <defs>
                        {["platform", "mobile", "design", "qa"].map(
                          (key, i) => (
                            <linearGradient
                              key={key}
                              id={`grad-${key}`}
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="0%"
                                stopColor={COLORS[i]}
                                stopOpacity={0.3}
                              />
                              <stop
                                offset="100%"
                                stopColor={COLORS[i]}
                                stopOpacity={0}
                              />
                            </linearGradient>
                          )
                        )}
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
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#111114",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 10,
                          fontSize: 12,
                          color: "#f5f5f7",
                        }}
                      />
                      <Legend
                        iconType="circle"
                        iconSize={6}
                        wrapperStyle={{ fontSize: 11, color: "#636366" }}
                      />
                      <Area
                        type="monotone"
                        dataKey="platform"
                        stackId="1"
                        stroke={COLORS[0]}
                        fill={`url(#grad-platform)`}
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="mobile"
                        stackId="1"
                        stroke={COLORS[1]}
                        fill={`url(#grad-mobile)`}
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="design"
                        stackId="1"
                        stroke={COLORS[2]}
                        fill={`url(#grad-design)`}
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="qa"
                        stackId="1"
                        stroke={COLORS[3]}
                        fill={`url(#grad-qa)`}
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Adoption curve</CardTitle>
                <Badge variant="outline">% bot-routed</Badge>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={adoptionData}>
                      <defs>
                        <linearGradient
                          id="adoptionGrad2"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#6366f1"
                            stopOpacity={0.35}
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
                          background: "#111114",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 10,
                          fontSize: 12,
                          color: "#f5f5f7",
                        }}
                        formatter={(v) => [`${v}%`, "Adoption"]}
                      />
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#6366f1"
                        strokeWidth={2}
                        fill="url(#adoptionGrad2)"
                        dot={false}
                        activeDot={{
                          r: 4,
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
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Team performance radar</CardTitle>
              <Badge variant="outline">Normalized scores</Badge>
            </CardHeader>
            <CardContent className="flex justify-center pb-6">
              <div className="h-[320px] w-full max-w-md">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart
                    cx="50%"
                    cy="50%"
                    outerRadius="75%"
                    data={[
                      {
                        subject: "Speed",
                        A: 92,
                        B: 78,
                        fullMark: 100,
                      },
                      {
                        subject: "Quality",
                        A: 85,
                        B: 88,
                        fullMark: 100,
                      },
                      {
                        subject: "Collaboration",
                        A: 76,
                        B: 94,
                        fullMark: 100,
                      },
                      {
                        subject: "Innovation",
                        A: 88,
                        B: 72,
                        fullMark: 100,
                      },
                      {
                        subject: "Stability",
                        A: 95,
                        B: 81,
                        fullMark: 100,
                      },
                      {
                        subject: "Scope Mgmt",
                        A: 70,
                        B: 90,
                        fullMark: 100,
                      },
                    ]}
                  >
                    <PolarGrid stroke="rgba(255,255,255,0.08)" />
                    <PolarAngleAxis
                      dataKey="subject"
                      tick={{ fill: "#8e8e93", fontSize: 11 }}
                    />
                    <PolarRadiusAxis
                      angle={30}
                      domain={[0, 100]}
                      tick={false}
                      axisLine={false}
                    />
                    <Radar
                      name="Platform"
                      dataKey="A"
                      stroke="#6366f1"
                      fill="#6366f1"
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                    <Radar
                      name="Mobile"
                      dataKey="B"
                      stroke="#34d399"
                      fill="#34d399"
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                    <Legend
                      iconType="circle"
                      iconSize={6}
                      wrapperStyle={{ fontSize: 11, color: "#636366" }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#111114",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 10,
                        fontSize: 12,
                        color: "#f5f5f7",
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="projects" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Scope change impact</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={projects.filter((p) => p.status !== "completed")}
                      layout="vertical"
                      margin={{ left: 20 }}
                    >
                      <CartesianGrid
                        stroke="rgba(255,255,255,0.04)"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 11 }}
                        tickFormatter={(v) => `${v}%`}
                      />
                      <YAxis
                        dataKey="name"
                        type="category"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#8e8e93", fontSize: 11 }}
                        width={140}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#111114",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 10,
                          fontSize: 12,
                          color: "#f5f5f7",
                        }}
                        formatter={(v) => [v, "Scope change"]}
                      />
                      <Bar
                        dataKey="health"
                        fill="#6366f1"
                        radius={[0, 4, 4, 0]}
                        barSize={16}
                        name="Health %"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Task completion rate</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={projects}>
                      <CartesianGrid
                        stroke="rgba(255,255,255,0.04)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="name"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 10 }}
                        interval={0}
                        angle={-15}
                        textAnchor="end"
                        height={50}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#111114",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 10,
                          fontSize: 12,
                          color: "#f5f5f7",
                        }}
                      />
                      <Bar
                        dataKey="tasksTotal"
                        stackId="a"
                        fill="rgba(255,255,255,0.06)"
                        radius={[4, 4, 0, 0]}
                        barSize={24}
                        name="Total"
                      />
                      <Bar
                        dataKey="tasksDone"
                        stackId="a"
                        fill="#6366f1"
                        radius={[4, 4, 0, 0]}
                        barSize={24}
                        name="Done"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Project health matrix</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {projects.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between py-4 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <p className="truncate text-sm font-medium text-card-foreground">
                        {p.name}
                      </p>
                      {p.status === "at-risk" ? (
                        <Badge variant="destructive">At risk</Badge>
                      ) : p.status === "completed" ? (
                        <Badge variant="outline">Done</Badge>
                      ) : (
                        <Badge variant="outline">On track</Badge>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Lead: {p.lead} · Sprint {p.sprint}
                    </p>
                  </div>
                  <div className="ml-4 flex items-center gap-6">
                    <div className="hidden sm:block">
                      <div className="mb-1 flex justify-between text-[10px] text-muted-foreground">
                        <span>Health</span>
                        <span>{p.health}%</span>
                      </div>
                      <div className="h-1 w-24 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${p.health}%`,
                            background:
                              p.health >= 80
                                ? "var(--color-success)"
                                : p.health >= 60
                                ? "var(--color-warning)"
                                : "var(--color-danger)",
                          }}
                        />
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-card-foreground">
                        {p.tasksDone}/{p.tasksTotal}
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        tasks
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="users" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Contribution breakdown</CardTitle>
                <Badge variant="outline">
                  Commits, reviews, bugs, features
                </Badge>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={reportData.userContributions}
                      margin={{ top: 10 }}
                    >
                      <CartesianGrid
                        stroke="rgba(255,255,255,0.04)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="name"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 11 }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#111114",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 10,
                          fontSize: 12,
                          color: "#f5f5f7",
                        }}
                      />
                      <Legend
                        iconType="circle"
                        iconSize={6}
                        wrapperStyle={{ fontSize: 11, color: "#636366" }}
                      />
                      <Bar
                        dataKey="commits"
                        stackId="a"
                        fill="#6366f1"
                        radius={[0, 0, 0, 0]}
                        barSize={20}
                      />
                      <Bar
                        dataKey="reviews"
                        stackId="a"
                        fill="#34d399"
                        radius={[0, 0, 0, 0]}
                        barSize={20}
                      />
                      <Bar
                        dataKey="bugs"
                        stackId="a"
                        fill="#f87171"
                        radius={[0, 0, 0, 0]}
                        barSize={20}
                      />
                      <Bar
                        dataKey="features"
                        stackId="a"
                        fill="#fbbf24"
                        radius={[4, 4, 0, 0]}
                        barSize={20}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Trust vs. Velocity</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={users}
                      layout="vertical"
                      margin={{ left: 10 }}
                    >
                      <CartesianGrid
                        stroke="rgba(255,255,255,0.04)"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#636366", fontSize: 11 }}
                      />
                      <YAxis
                        dataKey="initials"
                        type="category"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#8e8e93", fontSize: 11 }}
                        width={30}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#111114",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 10,
                          fontSize: 12,
                          color: "#f5f5f7",
                        }}
                      />
                      <Bar
                        dataKey="trustRate"
                        fill="#6366f1"
                        radius={[0, 4, 4, 0]}
                        barSize={12}
                        name="Trust %"
                      />
                      <Bar
                        dataKey="workload"
                        fill="rgba(255,255,255,0.08)"
                        radius={[0, 4, 4, 0]}
                        barSize={12}
                        name="Load %"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>User precision matrix</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {users.map((u) => {
                return (
                  <div
                    key={u.id}
                    className="flex items-center justify-between py-4 first:pt-0 last:pb-0"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium text-white"
                        style={{
                          background: `hsl(${u.name.length * 40}, 60%, 35%)`,
                        }}
                      >
                        {u.initials}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-card-foreground">
                          {u.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {u.role} · {u.team}
                        </p>
                      </div>
                    </div>
                    <div className="hidden gap-6 sm:flex">
                      <div className="text-center">
                        <p className="text-sm font-medium text-card-foreground">
                          {u.tasksClosedThisWeek}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          tasks/wk
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-medium text-card-foreground">
                          {u.hoursSaved}h
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          saved
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-medium text-card-foreground">
                          {u.trustRate}%
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          trust
                        </p>
                      </div>
                      <div className="text-center">
                        <p
                          className={`text-sm font-medium ${
                            u.velocityTrend.startsWith("+")
                              ? "text-[var(--color-success)]"
                              : "text-[var(--color-danger)]"
                          }`}
                        >
                          {u.velocityTrend}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          velocity
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
