"use client";

import * as React from "react";
import { useState, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { client } from "@/lib/api";
import {
  useIntegrations,
  listProjectsOptions,
} from "@/lib/api/@tanstack/react-query.gen";
import {
  Volume2,
  Lock,
  Bot,
  MessageSquare,
  FolderGit2,
  AlertCircle,
} from "lucide-react";

interface ProjectMappingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface ChannelsApiResponse {
  scopes?: Array<{ id: string; name: string }>;
}

export function ProjectMappingDialog({
  open,
  onOpenChange,
  onSuccess,
}: ProjectMappingDialogProps) {
  const queryClient = useQueryClient();
  const { data: integrationsData } = useIntegrations();

  const voiceFeatureEnabled =
    typeof process !== "undefined"
      ? process.env.NEXT_PUBLIC_VOICE_FEATURE_ENABLED !== "false"
      : true;

  // Discover connected providers
  const connectedIntegrations = useMemo(() => {
    return (integrationsData?.integrations ?? []).filter(
      (i) => i.status === "connected"
    );
  }, [integrationsData]);

  const pmProviders = useMemo(() => {
    return connectedIntegrations
      .filter((i) => i.provider === "taiga" || i.provider === "jira")
      .map((i) => i.provider);
  }, [connectedIntegrations]);

  const commProviders = useMemo(() => {
    return connectedIntegrations
      .filter((i) => i.provider === "discord" || i.provider === "slack")
      .map((i) => i.provider);
  }, [connectedIntegrations]);

  const [selectedPm, setSelectedPm] = useState<string>("");
  const [selectedComm, setSelectedComm] = useState<string>("");
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedTextChannel, setSelectedTextChannel] = useState<string>("");
  const [selectedVoiceChannel, setSelectedVoiceChannel] = useState<string>("");
  const [ambientEnabled, setAmbientEnabled] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Set default providers when dialog opens or data loads
  useEffect(() => {
    if (open) {
      if (pmProviders.length > 0 && !selectedPm) {
        setSelectedPm(pmProviders[0]);
      }
      if (commProviders.length > 0 && !selectedComm) {
        setSelectedComm(commProviders[0]);
      }
    }
  }, [open, pmProviders, commProviders, selectedPm, selectedComm]);

  // Reset voice settings if comm provider changes to slack
  useEffect(() => {
    if (selectedComm === "slack") {
      setSelectedVoiceChannel("");
      setAmbientEnabled(false);
    }
  }, [selectedComm]);

  // Query PM Projects
  const { data: projectsData, isLoading: isLoadingProjects } = useQuery({
    ...listProjectsOptions({
      path: { provider: selectedPm || "jira" },
    }),
    enabled: Boolean(selectedPm),
  });

  // Query Text Channels
  const { data: textChannelsData, isLoading: isLoadingTextChannels } =
    useQuery<ChannelsApiResponse>({
      queryKey: ["channels", selectedComm, "text"],
      queryFn: async () => {
        const res = await client.get<ChannelsApiResponse>({
          url: "/api/integrations/{provider}/channels",
          path: { provider: selectedComm },
          query: { type: "text" },
        });
        if (res.error) {
          throw new Error((res.error as any)?.detail || "Failed to fetch text channels");
        }
        return res.data ?? { scopes: [] };
      },
      enabled: Boolean(selectedComm),
    });

  // Query Voice Channels (Discord only)
  const { data: voiceChannelsData, isLoading: isLoadingVoiceChannels } =
    useQuery<ChannelsApiResponse>({
      queryKey: ["channels", selectedComm, "voice"],
      queryFn: async () => {
        const res = await client.get<ChannelsApiResponse>({
          url: "/api/integrations/{provider}/channels",
          path: { provider: selectedComm },
          query: { type: "voice" },
        });
        if (res.error) {
          throw new Error((res.error as any)?.detail || "Failed to fetch voice channels");
        }
        return res.data ?? { scopes: [] };
      },
      enabled: selectedComm === "discord" && voiceFeatureEnabled,
    });

  const textChannels = useMemo(() => {
    return textChannelsData?.scopes ?? [];
  }, [textChannelsData]);

  const voiceChannels = useMemo(() => {
    return voiceChannelsData?.scopes ?? [];
  }, [voiceChannelsData]);

  const projectScopes = useMemo(() => {
    return (projectsData?.scopes ?? []) as Array<{ id: string; name: string }>;
  }, [projectsData]);

  // Save Mapping Mutation
  const saveMappingMutation = useMutation({
    mutationFn: async () => {
      setErrorMsg(null);
      const payload = {
        pm_provider: selectedPm,
        project_id: selectedProject,
        comm_provider: selectedComm,
        channel_id: selectedTextChannel,
        voice_channel_id:
          selectedComm === "discord" ? selectedVoiceChannel || null : null,
        ambient_enabled:
          selectedComm === "discord" && selectedVoiceChannel
            ? ambientEnabled
            : false,
        active: true,
      };

      const res = await client.put({
        url: "/api/projects",
        body: payload,
      });

      if (res.error) {
        throw new Error((res.error as any)?.detail || "Failed to save project mapping");
      }
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-mappings"] });
      onSuccess?.();
      onOpenChange(false);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || "An error occurred");
    },
  });

  const canSubmit =
    Boolean(selectedPm) &&
    Boolean(selectedComm) &&
    Boolean(selectedProject) &&
    Boolean(selectedTextChannel) &&
    !saveMappingMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg rounded-2xl bg-canvas p-6 shadow-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500">
              <FolderGit2 size={18} />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-ink">
                Configure Project Mapping
              </DialogTitle>
              <DialogDescription className="text-xs text-ink-muted">
                Link your project management board to team communication channels.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {errorMsg && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-500">
            <AlertCircle size={14} className="shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="space-y-4 py-2">
          {/* Provider Selection */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-ink-muted">
                Project Tracker
              </label>
              <div className="mt-1 flex gap-2">
                {pmProviders.length === 0 ? (
                  <p className="text-xs text-ink-muted">No PM connected</p>
                ) : (
                  pmProviders.map((pm) => (
                    <button
                      key={pm}
                      type="button"
                      onClick={() => {
                        setSelectedPm(pm);
                        setSelectedProject("");
                      }}
                      className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium capitalize transition-all ${
                        selectedPm === pm
                          ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                          : "border-hairline bg-canvas text-ink hover:border-zinc-700"
                      }`}
                    >
                      {pm}
                    </button>
                  ))
                )}
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-ink-muted">
                Communication Tool
              </label>
              <div className="mt-1 flex gap-2">
                {commProviders.length === 0 ? (
                  <p className="text-xs text-ink-muted">No chat connected</p>
                ) : (
                  commProviders.map((comm) => (
                    <button
                      key={comm}
                      type="button"
                      onClick={() => {
                        setSelectedComm(comm);
                        setSelectedTextChannel("");
                      }}
                      className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium capitalize transition-all ${
                        selectedComm === comm
                          ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                          : "border-hairline bg-canvas text-ink hover:border-zinc-700"
                      }`}
                    >
                      {comm}
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Project Selection Dropdown */}
          <div>
            <label className="text-xs font-semibold text-ink-muted">
              Select {selectedPm ? selectedPm.toUpperCase() : "PM"} Project
            </label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              disabled={isLoadingProjects || projectScopes.length === 0}
              className="mt-1 w-full rounded-lg border border-hairline bg-canvas px-3 py-2 text-xs text-ink focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            >
              <option value="">
                {isLoadingProjects
                  ? "Loading projects..."
                  : projectScopes.length === 0
                  ? "No projects found"
                  : "-- Choose Project --"}
              </option>
              {projectScopes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Primary Text Channel Selection */}
          <div>
            <label className="text-xs font-semibold text-ink-muted flex items-center gap-1">
              <MessageSquare size={12} />
              <span>Primary Text Channel (Updates & Summaries)</span>
            </label>
            <select
              value={selectedTextChannel}
              onChange={(e) => setSelectedTextChannel(e.target.value)}
              disabled={isLoadingTextChannels || textChannels.length === 0}
              className="mt-1 w-full rounded-lg border border-hairline bg-canvas px-3 py-2 text-xs text-ink focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            >
              <option value="">
                {isLoadingTextChannels
                  ? "Loading text channels..."
                  : textChannels.length === 0
                  ? "No text channels found"
                  : "-- Choose Text Channel --"}
              </option>
              {textChannels.map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Voice & Ambient Section */}
          <div className="pt-2">
            {selectedComm === "discord" ? (
              <div className="rounded-xl border border-hairline bg-canvas/50 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Volume2 size={16} className="text-indigo-400" />
                    <span className="text-xs font-semibold text-ink">
                      AI Voice & Daily Standups
                    </span>
                  </div>
                  {voiceFeatureEnabled ? (
                    <Badge variant="outline" className="border-indigo-500/30 text-indigo-400 text-[10px]">
                      Discord Voice
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-zinc-500 text-[10px]">
                      Feature Disabled
                    </Badge>
                  )}
                </div>

                {voiceFeatureEnabled ? (
                  <>
                    <div>
                      <label className="text-[11px] text-ink-muted">
                        Standup Voice Channel (Optional)
                      </label>
                      <select
                        value={selectedVoiceChannel}
                        onChange={(e) => {
                          setSelectedVoiceChannel(e.target.value);
                          if (!e.target.value) setAmbientEnabled(false);
                        }}
                        disabled={isLoadingVoiceChannels}
                        className="mt-1 w-full rounded-lg border border-hairline bg-canvas px-3 py-1.5 text-xs text-ink focus:border-indigo-500 focus:outline-none disabled:opacity-50"
                      >
                        <option value="">-- No Voice Channel (Text Only) --</option>
                        {voiceChannels.map((c) => (
                          <option key={c.id} value={c.id}>
                            🔊 {c.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex items-start gap-2 pt-1">
                      <input
                        type="checkbox"
                        id="ambient_toggle"
                        checked={ambientEnabled}
                        disabled={!selectedVoiceChannel}
                        onChange={(e) => setAmbientEnabled(e.target.checked)}
                        className="mt-1 h-3.5 w-3.5 rounded border-hairline bg-canvas accent-indigo-600 disabled:opacity-40"
                      />
                      <label
                        htmlFor="ambient_toggle"
                        className={`text-xs select-none ${
                          !selectedVoiceChannel
                            ? "cursor-not-allowed text-ink-muted/50"
                            : "cursor-pointer text-ink"
                        }`}
                      >
                        <span className="font-medium flex items-center gap-1.5">
                          <Bot size={13} className="text-indigo-400" />
                          Always-On Ambient Voice Assistant
                        </span>
                        <p className="mt-0.5 text-[11px] text-ink-muted">
                          The AI bot resides in this voice channel to detect tasks and lead Daily Scrums.
                        </p>
                      </label>
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-ink-muted">
                    Voice features are currently turned off via system configuration.
                  </p>
                )}
              </div>
            ) : selectedComm === "slack" ? (
              /* Slack Voice Locked Placeholder Card */
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-zinc-400">
                    <Lock size={14} className="text-amber-500" />
                    <span className="text-xs font-semibold text-zinc-300">
                      AI Voice Standups (Zoom)
                    </span>
                  </div>
                  <Badge variant="outline" className="border-amber-500/30 text-amber-400 text-[10px]">
                    Coming Soon
                  </Badge>
                </div>
                <p className="text-[11px] leading-relaxed text-zinc-400">
                  Live audio standups for Slack workspaces will be enabled with our upcoming Zoom integration. Voice is turned off for now.
                </p>
              </div>
            ) : null}
          </div>
        </div>

        <DialogFooter className="mt-4 flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={saveMappingMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => saveMappingMutation.mutate()}
            disabled={!canSubmit}
            className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5"
          >
            {saveMappingMutation.isPending ? "Saving..." : "Save Mapping"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

