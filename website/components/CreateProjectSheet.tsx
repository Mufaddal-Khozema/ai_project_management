"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import {
  useIntegrations,
  listProjectsOptions,
  listChannelsOptions,
  listProjectsQueryKey,
} from "@/lib/api/@tanstack/react-query.gen";
import { client } from "@/lib/api/client.gen";
import { Check, Loader2, Sparkles, AlertCircle } from "lucide-react";

export interface UpsertProjectInput {
  pm_provider: "jira" | "taiga";
  project_id: string;
  comm_provider: "slack" | "discord";
  channel_id: string;
  active: boolean;
}

export interface ProjectMappingItem {
  uuid: string;
  pm_provider: string;
  project_id: string;
  project_name?: string | null;
  comm_provider: string;
  channel_id: string;
  active: boolean;
}

interface CreateProjectSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (projectName: string, channelName: string) => void;
}

export function CreateProjectSheet({
  open,
  onOpenChange,
  onCreated,
}: CreateProjectSheetProps) {
  const queryClient = useQueryClient();

  // Selected state
  const [pmProvider, setPmProvider] = useState<"jira" | "taiga">("jira");
  const [commProvider, setCommProvider] = useState<"slack" | "discord">("slack");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedProjectName, setSelectedProjectName] = useState<string>("");
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);
  const [selectedChannelName, setSelectedChannelName] = useState<string>("");
  const [activeSync, setActiveSync] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Drag wire state
  const boardRef = useRef<HTMLDivElement>(null);
  const pjRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const chRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [wirePath, setWirePath] = useState<string | null>(null);
  const [dragWire, setDragWire] = useState<{ start: [number, number]; current: [number, number] } | null>(null);

  // Integrations query
  const { data: integrationsData } = useIntegrations();

  const connectedProviders = useMemo(() => {
    const connected = (integrationsData?.integrations ?? []).filter(
      (i) => i.status === "connected"
    );
    return new Set(connected.map((i) => i.provider));
  }, [integrationsData]);

  // Existing project mappings from Litestar backend
  const { data: mappingsData } = useQuery<ProjectMappingItem[]>({
    queryKey: ["projectMappings"],
    queryFn: async () => {
      const response = await client.get({
        url: "/api/projects",
      });
      return (response.data as ProjectMappingItem[]) ?? [];
    },
    enabled: open,
  });

  const existingProjectIds = useMemo(() => {
    const list = Array.isArray(mappingsData) ? mappingsData : [];
    return new Set(
      list
        .filter((m) => m.pm_provider === pmProvider)
        .map((m) => m.project_id)
    );
  }, [mappingsData, pmProvider]);

  // Projects from PM Provider
  const {
    data: projectsData,
    isLoading: isProjectsLoading,
    isError: isProjectsError,
  } = useQuery({
    ...listProjectsOptions({
      path: { provider: pmProvider },
    }),
    enabled: open && connectedProviders.has(pmProvider),
  });

  // Channels from Comm Provider
  const {
    data: channelsData,
    isLoading: isChannelsLoading,
    isError: isChannelsError,
  } = useQuery({
    ...listChannelsOptions({
      path: { provider: commProvider },
    }),
    enabled: open && connectedProviders.has(commProvider),
  });

  const projectsList = useMemo(() => projectsData?.scopes ?? [], [projectsData?.scopes]);
  const channelsList = useMemo(() => channelsData?.scopes ?? [], [channelsData?.scopes]);

  // Reset or initialize on open
  useEffect(() => {
    if (open) {
      setErrorMsg(null);
      if (connectedProviders.has("taiga") && !connectedProviders.has("jira")) {
        setPmProvider("taiga");
      }
      if (connectedProviders.has("discord") && !connectedProviders.has("slack")) {
        setCommProvider("discord");
      }
    } else {
      setSelectedProjectId(null);
      setSelectedProjectName("");
      setSelectedChannelId(null);
      setSelectedChannelName("");
      setWirePath(null);
      setDragWire(null);
    }
  }, [open, connectedProviders]);

  // Reset selected project when pm provider changes
  const handlePmChange = (provider: "jira" | "taiga") => {
    setPmProvider(provider);
    setSelectedProjectId(null);
    setSelectedProjectName("");
    setErrorMsg(null);
  };

  // Reset selected channel when comm provider changes
  const handleCommChange = (provider: "slack" | "discord") => {
    setCommProvider(provider);
    setSelectedChannelId(null);
    setSelectedChannelName("");
    setErrorMsg(null);
  };

  // Calculate SVG Wire between selected project socket and channel socket
  const updateWire = () => {
    if (!selectedProjectId || !selectedChannelId || !boardRef.current) {
      setWirePath(null);
      return;
    }
    const pjEl = pjRefs.current.get(selectedProjectId);
    const chEl = chRefs.current.get(selectedChannelId);
    if (!pjEl || !chEl) {
      setWirePath(null);
      return;
    }

    const boardRect = boardRef.current.getBoundingClientRect();
    const pjSock = pjEl.querySelector(".socket-dot");
    const chSock = chEl.querySelector(".socket-dot");

    const pjRect = (pjSock || pjEl).getBoundingClientRect();
    const chRect = (chSock || chEl).getBoundingClientRect();

    const x1 = pjRect.left + pjRect.width / 2 - boardRect.left;
    const y1 = pjRect.top + pjRect.height / 2 - boardRect.top;
    const x2 = chRect.left + chRect.width / 2 - boardRect.left;
    const y2 = chRect.top + chRect.height / 2 - boardRect.top;

    const dx = Math.abs(x2 - x1) * 0.5;
    setWirePath(`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
  };

  useEffect(() => {
    updateWire();
  }, [selectedProjectId, selectedChannelId, projectsList, channelsList]);

  // Mutation to save project mapping directly to Litestar backend
  const upsertMutation = useMutation({
    mutationFn: async (payload: UpsertProjectInput) => {
      const response = await client.put({
        url: "/api/projects",
        body: payload,
      });
      return response.data as ProjectMappingItem;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ["projectMappings"],
      });
      queryClient.invalidateQueries({
        queryKey: listProjectsQueryKey({ path: { provider: pmProvider } }),
      });
      if (onCreated) {
        onCreated(selectedProjectName || data?.project_name || "Project", selectedChannelName || "Channel");
      }
      onOpenChange(false);
    },
    onError: (err: any) => {
      const msg = err?.detail || err?.message || "Failed to plug in project";
      setErrorMsg(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const handleSave = () => {
    if (!selectedProjectId || !selectedChannelId) return;
    setErrorMsg(null);
    upsertMutation.mutate({
      pm_provider: pmProvider,
      project_id: selectedProjectId,
      comm_provider: commProvider,
      channel_id: selectedChannelId,
      active: activeSync,
    });
  };

  // Drag wiring support
  const handlePointerDownProject = (id: string, name: string, e: React.PointerEvent) => {
    if (existingProjectIds.has(id)) return;
    setSelectedProjectId(id);
    setSelectedProjectName(name);

    if (!boardRef.current) return;
    const boardRect = boardRef.current.getBoundingClientRect();
    const pjEl = pjRefs.current.get(id);
    const sock = pjEl?.querySelector(".socket-dot") || pjEl;
    if (!sock) return;
    const sockRect = sock.getBoundingClientRect();

    const startX = sockRect.left + sockRect.width / 2 - boardRect.left;
    const startY = sockRect.top + sockRect.height / 2 - boardRect.top;
    const currX = e.clientX - boardRect.left;
    const currY = e.clientY - boardRect.top;

    setDragWire({ start: [startX, startY], current: [currX, currY] });

    const handlePointerMove = (ev: PointerEvent) => {
      if (!boardRef.current) return;
      const bRect = boardRef.current.getBoundingClientRect();
      setDragWire((prev) =>
        prev
          ? {
              start: prev.start,
              current: [ev.clientX - bRect.left, ev.clientY - bRect.top],
            }
          : null
      );
    };

    const handlePointerUp = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      setDragWire(null);

      // Check drop target under pointer
      const target = document.elementFromPoint(ev.clientX, ev.clientY)?.closest("[data-channel-id]") as HTMLElement | null;
      if (target) {
        const cId = target.dataset.channelId;
        const cName = target.dataset.channelName || "";
        if (cId) {
          setSelectedChannelId(cId);
          setSelectedChannelName(cName);
        }
      }
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  };

  const payloadPreview = {
    pm_provider: pmProvider,
    project_id: selectedProjectId ?? "...",
    comm_provider: commProvider,
    channel_id: selectedChannelId ?? "...",
    active: activeSync,
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl md:max-w-2xl lg:max-w-3xl flex flex-col p-6 sm:p-8 bg-canvas text-ink overflow-y-auto"
      >
        <SheetHeader className="p-0 space-y-2">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-2xl bg-gradient-to-tr from-[#7352f0] to-[#3f6df0] text-white flex items-center justify-center shadow-soft">
              <Sparkles className="size-5" />
            </div>
            <div>
              <SheetTitle className="text-xl font-bold tracking-tight text-ink font-display">
                Plug in a project
              </SheetTitle>
              <SheetDescription className="text-xs text-ink-muted">
                Wire an active project from Jira or Taiga directly to your Slack or Discord channel.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        {/* Board */}
        <div
          ref={boardRef}
          className="relative mt-6 rounded-3xl p-5 bg-canvas shadow-press border border-hairline select-none"
        >
          {/* Dynamic SVG Wires */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none z-10 overflow-visible"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="wireGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#ff5fa2" />
                <stop offset="50%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#4f7cff" />
              </linearGradient>
            </defs>

            {/* Confirmed Wire */}
            {wirePath && (
              <path
                d={wirePath}
                fill="none"
                stroke="url(#wireGradient)"
                strokeWidth="4"
                strokeLinecap="round"
                className="drop-shadow-md animate-in fade-in duration-300"
              />
            )}

            {/* Dragging Wire */}
            {dragWire && (
              <path
                d={`M ${dragWire.start[0]} ${dragWire.start[1]} C ${
                  dragWire.start[0] + 60
                } ${dragWire.start[1]}, ${dragWire.current[0] - 60} ${
                  dragWire.current[1]
                }, ${dragWire.current[0]} ${dragWire.current[1]}`}
                fill="none"
                stroke="url(#wireGradient)"
                strokeWidth="4"
                strokeDasharray="4 6"
                strokeLinecap="round"
                className="opacity-80"
              />
            )}
          </svg>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-0">
            {/* Project Source (Left) */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink">Project source</h3>
                <div className="flex rounded-full bg-canvas p-0.5 shadow-press">
                  <button
                    type="button"
                    onClick={() => handlePmChange("jira")}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                      pmProvider === "jira"
                        ? "bg-gradient-to-r from-[#7352f0] to-[#3f6df0] text-white shadow-soft"
                        : "text-ink-muted hover:text-ink"
                    }`}
                  >
                    Jira
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePmChange("taiga")}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                      pmProvider === "taiga"
                        ? "bg-gradient-to-r from-[#7352f0] to-[#3f6df0] text-white shadow-soft"
                        : "text-ink-muted hover:text-ink"
                    }`}
                  >
                    Taiga
                  </button>
                </div>
              </div>

              <div className="text-[11px] font-mono text-ink-muted">
                GET /api/integrations/{pmProvider}/projects
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {isProjectsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-14 rounded-2xl bg-canvas shadow-press animate-pulse"
                      />
                    ))}
                  </div>
                ) : !connectedProviders.has(pmProvider) ? (
                  <div className="p-4 rounded-2xl bg-canvas shadow-press text-center space-y-2">
                    <p className="text-xs text-ink-muted">
                      {pmProvider === "jira" ? "Jira" : "Taiga"} is not connected yet.
                    </p>
                    <a
                      href="/admin/settings"
                      className="inline-block text-xs font-semibold text-[#4f7cff] hover:underline"
                    >
                      Connect in Settings →
                    </a>
                  </div>
                ) : isProjectsError ? (
                  <div className="p-4 rounded-2xl bg-canvas shadow-press text-center text-xs text-[var(--color-danger)]">
                    Failed to fetch projects from {pmProvider}.
                  </div>
                ) : projectsList.length === 0 ? (
                  <div className="p-4 rounded-2xl bg-canvas shadow-press text-center text-xs text-ink-muted">
                    No projects found on this {pmProvider} workspace.
                  </div>
                ) : (
                  projectsList.map((p) => {
                    const isAlreadyPlugged = existingProjectIds.has(p.id);
                    const isSelected = selectedProjectId === p.id;
                    return (
                      <button
                        key={p.id}
                        ref={(el) => {
                          if (el) pjRefs.current.set(p.id, el);
                          else pjRefs.current.delete(p.id);
                        }}
                        type="button"
                        disabled={isAlreadyPlugged}
                        onPointerDown={(e) => handlePointerDownProject(p.id, p.name, e)}
                        onClick={() => {
                          if (!isAlreadyPlugged) {
                            setSelectedProjectId(isSelected ? null : p.id);
                            setSelectedProjectName(isSelected ? "" : p.name);
                          }
                        }}
                        className={`w-full text-left flex items-center justify-between p-3 rounded-2xl transition duration-150 cursor-grab active:cursor-grabbing ${
                          isAlreadyPlugged
                            ? "opacity-50 cursor-not-allowed bg-canvas shadow-press"
                            : isSelected
                            ? "bg-canvas shadow-press ring-2 ring-[#7352f0]"
                            : "bg-canvas shadow-soft hover:shadow-press"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="size-6 rounded-full bg-gradient-to-r from-[#7352f0] to-[#3f6df0] text-white text-[11px] font-bold flex items-center justify-center shrink-0">
                            {pmProvider === "jira" ? "J" : "T"}
                          </span>
                          <div className="truncate">
                            <p className="text-xs font-bold text-ink truncate">
                              {p.name}
                            </p>
                            <p className="text-[10px] text-ink-muted">
                              {isAlreadyPlugged ? "Already plugged in" : `id: ${p.id}`}
                            </p>
                          </div>
                        </div>
                        <span
                          className={`socket-dot size-5 rounded-full shrink-0 border-2 transition ${
                            isSelected
                              ? "bg-gradient-to-tr from-[#ff5fa2] to-[#7352f0] border-transparent shadow-sm"
                              : "border-hairline bg-canvas shadow-press"
                          }`}
                        />
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Chat Channel (Right) */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink">Chat channel</h3>
                <div className="flex rounded-full bg-canvas p-0.5 shadow-press">
                  <button
                    type="button"
                    onClick={() => handleCommChange("slack")}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                      commProvider === "slack"
                        ? "bg-gradient-to-r from-[#7352f0] to-[#3f6df0] text-white shadow-soft"
                        : "text-ink-muted hover:text-ink"
                    }`}
                  >
                    Slack
                  </button>
                  <button
                    type="button"
                    onClick={() => handleCommChange("discord")}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                      commProvider === "discord"
                        ? "bg-gradient-to-r from-[#7352f0] to-[#3f6df0] text-white shadow-soft"
                        : "text-ink-muted hover:text-ink"
                    }`}
                  >
                    Discord
                  </button>
                </div>
              </div>

              <div className="text-[11px] text-ink-muted">
                Alerts, sprint progress and health updates land here.
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {isChannelsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-14 rounded-2xl bg-canvas shadow-press animate-pulse"
                      />
                    ))}
                  </div>
                ) : !connectedProviders.has(commProvider) ? (
                  <div className="p-4 rounded-2xl bg-canvas shadow-press text-center space-y-2">
                    <p className="text-xs text-ink-muted">
                      {commProvider === "slack" ? "Slack" : "Discord"} is not connected yet.
                    </p>
                    <a
                      href="/admin/settings"
                      className="inline-block text-xs font-semibold text-[#4f7cff] hover:underline"
                    >
                      Connect in Settings →
                    </a>
                  </div>
                ) : isChannelsError ? (
                  <div className="p-4 rounded-2xl bg-canvas shadow-press text-center text-xs text-[var(--color-danger)]">
                    Failed to fetch channels from {commProvider}.
                  </div>
                ) : channelsList.length === 0 ? (
                  <div className="p-4 rounded-2xl bg-canvas shadow-press text-center text-xs text-ink-muted">
                    No channels found on this {commProvider} workspace.
                  </div>
                ) : (
                  channelsList.map((c) => {
                    const isSelected = selectedChannelId === c.id;
                    return (
                      <button
                        key={c.id}
                        ref={(el) => {
                          if (el) chRefs.current.set(c.id, el);
                          else chRefs.current.delete(c.id);
                        }}
                        type="button"
                        data-channel-id={c.id}
                        data-channel-name={c.name}
                        onClick={() => {
                          setSelectedChannelId(isSelected ? null : c.id);
                          setSelectedChannelName(isSelected ? "" : c.name);
                        }}
                        className={`w-full text-left flex items-center justify-between p-3 rounded-2xl transition duration-150 ${
                          isSelected
                            ? "bg-canvas shadow-press ring-2 ring-[#4f7cff]"
                            : "bg-canvas shadow-soft hover:shadow-press"
                        }`}
                      >
                        <span
                          className={`socket-dot size-5 rounded-full shrink-0 border-2 transition mr-2.5 ${
                            isSelected
                              ? "bg-gradient-to-tr from-[#8b5cf6] to-[#4f7cff] border-transparent shadow-sm"
                              : "border-hairline bg-canvas shadow-press"
                          }`}
                        />
                        <div className="flex-1 truncate">
                          <p className="text-xs font-bold text-ink truncate">
                            {c.name.startsWith("#") ? c.name : `#${c.name}`}
                          </p>
                          <p className="text-[10px] text-ink-muted truncate">
                            id: {c.id}
                          </p>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Live helper status */}
        <div className="mt-4 rounded-2xl bg-canvas shadow-press p-3 text-xs text-ink-muted flex items-center gap-2">
          <div
            className={`size-2 rounded-full shrink-0 ${
              selectedProjectId && selectedChannelId
                ? "bg-[var(--color-success)] animate-pulse"
                : "bg-ink-muted"
            }`}
          />
          <p className="truncate">
            {selectedProjectId && selectedChannelId
              ? `Wired "${selectedProjectName || selectedProjectId}" to "${
                  selectedChannelName || selectedChannelId
                }". Ready to save mapping.`
              : selectedProjectId
              ? `Selected project. Pick a chat channel or drag across to connect.`
              : "Pick a project from Jira/Taiga and connect it to a Slack/Discord channel."}
          </p>
        </div>

        {errorMsg && (
          <div className="mt-3 p-3 rounded-2xl bg-red-500/10 border border-red-500/20 text-xs text-[var(--color-danger)] flex items-center gap-2">
            <AlertCircle className="size-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Foot: Payload preview & Action */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
          <div className="rounded-2xl bg-canvas shadow-press p-3 font-mono text-[11px] text-ink leading-tight overflow-x-auto">
            <span className="text-[#8b5cf6] font-bold">PUT</span> /projects
            <pre className="mt-1 text-ink-muted">
              {JSON.stringify(payloadPreview, null, 2)}
            </pre>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-2xl bg-canvas shadow-soft p-3">
              <div>
                <p className="text-xs font-semibold text-ink">
                  Start syncing right away
                </p>
                <p className="text-[11px] text-ink-muted">
                  Issues, sprints, members and health
                </p>
              </div>
              <input
                type="checkbox"
                checked={activeSync}
                onChange={(e) => setActiveSync(e.target.checked)}
                className="size-4 accent-[#7352f0] cursor-pointer"
              />
            </div>

            <Button
              type="button"
              className="w-full"
              disabled={!selectedProjectId || !selectedChannelId || upsertMutation.isPending}
              onClick={handleSave}
            >
              {upsertMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin mr-2" />
                  Saving mapping…
                </>
              ) : (
                <>
                  <Check className="size-4 mr-1.5" />
                  Save mapping
                </>
              )}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
