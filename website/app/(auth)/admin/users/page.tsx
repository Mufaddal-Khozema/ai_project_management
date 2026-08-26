"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { users } from "@/lib/data";
import { Search, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useState } from "react";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [teamFilter, setTeamFilter] = useState("all");

  const teams = Array.from(new Set(users.map((u) => u.team)));
  const filtered = users.filter(
    (u) =>
      u.name.toLowerCase().includes(search.toLowerCase()) &&
      (teamFilter === "all" || u.team === teamFilter)
  );

  const statusDot = (status: string) => {
    const colors: Record<string, string> = {
      online: "bg-[var(--color-success)]",
      away: "bg-[var(--color-warning)]",
      offline: "bg-muted-foreground",
    };
    return (
      <span className="relative flex h-2 w-2">
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
            status === "online" ? "bg-[var(--color-success)]" : "hidden"
          }`}
        />
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${colors[status]}`}
        />
      </span>
    );
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-card-foreground">
            Team
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {users.length} members across {teams.length} teams
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            placeholder="Search by name or role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={teamFilter} onValueChange={(v) => v && setTeamFilter(v)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All teams" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All teams</SelectItem>
            {teams.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Member</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Active projects</TableHead>
              <TableHead>Tasks this week</TableHead>
              <TableHead>Velocity</TableHead>
              <TableHead>Trust rate</TableHead>
              <TableHead>Hours saved</TableHead>
              <TableHead>Workload</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((u) => (
              <TableRow key={u.id} className="cursor-pointer">
                <TableCell>
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
                      <p className="font-medium text-card-foreground">
                        {u.name}
                      </p>
                      <p className="text-xs text-muted-foreground">{u.role}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{u.team}</Badge>
                </TableCell>
                <TableCell className="text-card-foreground">
                  {u.activeProjects}
                </TableCell>
                <TableCell className="text-card-foreground">
                  {u.tasksClosedThisWeek}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    {u.velocityTrend.startsWith("+") ? (
                      <TrendingUp
                        size={12}
                        className="text-[var(--color-success)]"
                      />
                    ) : u.velocityTrend.startsWith("-") ? (
                      <TrendingDown
                        size={12}
                        className="text-[var(--color-danger)]"
                      />
                    ) : (
                      <Minus size={12} className="text-muted-foreground" />
                    )}
                    <span
                      className={
                        u.velocityTrend.startsWith("+")
                          ? "text-[var(--color-success)]"
                          : u.velocityTrend.startsWith("-")
                          ? "text-[var(--color-danger)]"
                          : "text-muted-foreground"
                      }
                    >
                      {u.velocityTrend}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${u.trustRate}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {u.trustRate}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-card-foreground">
                  {u.hoursSaved}h
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${u.workload}%`,
                          background:
                            u.workload > 90
                              ? "var(--color-danger)"
                              : u.workload > 70
                              ? "var(--color-warning)"
                              : "var(--color-success)",
                        }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {u.workload}%
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {statusDot(u.status)}
                    <span className="text-xs text-muted-foreground capitalize">
                      {u.status}
                    </span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {filtered.map((u) => (
          <Card
            key={u.id}
            className="group transition-colors hover:border-border/50"
          >
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-medium text-white"
                    style={{
                      background: `hsl(${u.name.length * 40}, 60%, 35%)`,
                    }}
                  >
                    {u.initials}
                  </div>
                  <div>
                    <p className="font-medium text-card-foreground">
                      {u.name}
                    </p>
                    <p className="text-xs text-muted-foreground">{u.role}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {statusDot(u.status)}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">Trust rate</p>
                  <p className="mt-1 text-lg font-semibold text-card-foreground">
                    {u.trustRate}%
                  </p>
                </div>
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">Hours saved</p>
                  <p className="mt-1 text-lg font-semibold text-card-foreground">
                    {u.hoursSaved}h
                  </p>
                </div>
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">Tasks closed</p>
                  <p className="mt-1 text-lg font-semibold text-card-foreground">
                    {u.tasksClosedThisWeek}
                  </p>
                </div>
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">Velocity</p>
                  <p
                    className={`mt-1 text-lg font-semibold ${
                      u.velocityTrend.startsWith("+")
                        ? "text-[var(--color-success)]"
                        : u.velocityTrend.startsWith("-")
                        ? "text-[var(--color-danger)]"
                        : "text-card-foreground"
                    }`}
                  >
                    {u.velocityTrend}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-muted-foreground">Workload</span>
                  <span
                    className={
                      u.workload > 90
                        ? "text-[var(--color-danger)]"
                        : u.workload > 70
                        ? "text-[var(--color-warning)]"
                        : "text-[var(--color-success)]"
                    }
                  >
                    {u.workload}%
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${u.workload}%`,
                      background:
                        u.workload > 90
                          ? "var(--color-danger)"
                          : u.workload > 70
                          ? "var(--color-warning)"
                          : "var(--color-success)",
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
