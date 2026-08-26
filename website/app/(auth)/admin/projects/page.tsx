"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarGroup } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { projects } from "@/lib/data";
import {
  Search,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Filter,
} from "lucide-react";
import { useState } from "react";

export default function ProjectsPage() {
  const [search, setSearch] = useState("");

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  const statusBadge = (status: string) => {
    switch (status) {
      case "on-track":
        return <Badge variant="outline">On track</Badge>;
      case "at-risk":
        return <Badge variant="destructive">At risk</Badge>;
      case "completed":
        return (
          <Badge variant="outline" className="text-muted-foreground">
            Completed
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const velocityIcon = (v: string) => {
    if (v.startsWith("↑"))
      return (
        <ArrowUpRight size={12} className="text-[var(--color-success)]" />
      );
    if (v.startsWith("↓"))
      return (
        <ArrowDownRight size={12} className="text-[var(--color-danger)]" />
      );
    return <Minus size={12} className="text-muted-foreground" />;
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-card-foreground">
            Projects
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {projects.length} total ·{" "}
            {projects.filter((p) => p.status === "at-risk").length} at risk
          </p>
        </div>
        <Button size="sm">New project</Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="outline" size="sm" className="gap-2">
          <Filter size={14} />
          Filter
        </Button>
      </div>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Health</TableHead>
              <TableHead>Sprint</TableHead>
              <TableHead>Progress</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Velocity</TableHead>
              <TableHead>Last activity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((p) => (
              <TableRow key={p.id} className="cursor-pointer">
                <TableCell>
                  <div>
                    <p className="font-medium text-card-foreground">
                      {p.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Lead: {p.lead}
                    </p>
                  </div>
                </TableCell>
                <TableCell>{statusBadge(p.status)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
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
                    <span className="text-xs text-muted-foreground">
                      {p.health}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {p.sprint}
                </TableCell>
                <TableCell>
                  <span className="text-xs text-muted-foreground">
                    {p.tasksDone}/{p.tasksTotal}
                  </span>
                </TableCell>
                <TableCell>
                  <AvatarGroup>
                    {p.team.map((t) => (
                      <Avatar key={t} size="sm">
                        <AvatarFallback className="text-[10px]">{t}</AvatarFallback>
                      </Avatar>
                    ))}
                  </AvatarGroup>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 text-xs">
                    {velocityIcon(p.velocity)}
                    <span
                      className={
                        p.velocity.startsWith("↑")
                          ? "text-[var(--color-success)]"
                          : p.velocity.startsWith("↓")
                          ? "text-[var(--color-danger)]"
                          : "text-muted-foreground"
                      }
                    >
                      {p.velocity}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {p.lastActivity}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {filtered.slice(0, 3).map((p) => (
          <Card
            key={p.id}
            className="group cursor-pointer transition-colors hover:border-border/50"
          >
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    {p.name}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {p.sprint}
                  </p>
                </div>
                {statusBadge(p.status)}
              </div>

              <div className="mt-4 space-y-3">
                <div>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-muted-foreground">Tasks</span>
                    <span className="text-card-foreground">
                      {p.tasksDone}/{p.tasksTotal}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{
                        width: `${(p.tasksDone / p.tasksTotal) * 100}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <AvatarGroup>
                    {p.team.map((t) => (
                      <Avatar key={t} size="sm">
                        <AvatarFallback className="text-[10px]">{t}</AvatarFallback>
                      </Avatar>
                    ))}
                  </AvatarGroup>
                  <span className="text-xs text-muted-foreground">
                    {p.lastActivity}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
