"use client";

import { useState, useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { OnboardingRequest, IntegrationResponse, MatchItem } from "@/lib/api";
import {
  useIntegrations,
  useInitiateIntegrationAuthMutation,
  useTaigaConnectMutation,
  useListProjects,
  useListProjectMembers,
  useListChannels,
  useListChannelMembers,
  listIntegrationsQueryKey,
} from "@/lib/api";
import { TaigaConnectForm } from "@/components/TaigaConnectForm";
import {
  integrationProviders,
  INTEGRATION_OAUTH_MESSAGE,
  formatExpiry,
  type IntegrationProvider,
} from "@/lib/integrations";
import { Check, X } from "lucide-react";

const commProviders = integrationProviders.filter((p) => p.category === "comm");
const pmProviders = integrationProviders.filter((p) => p.category === "pm");

type Step = "survey" | "comm" | "pm" | "project" | "channel" | "match";

const PROJECT_PROVIDERS = new Set(["taiga"]);
const CHANNEL_PROVIDERS = new Set(["discord"]);

interface Props {
  open: boolean;
  onComplete?: (data: OnboardingRequest) => void;
}

interface MemberRow {
  id: string;
  name: string;
  username: string;
  email: string;
  avatar: string;
}

export function OnboardingDialog({
  open,
  onComplete,
}: Props) {
  const [step, setStep] = useState<Step>("survey");

  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [team, setTeam] = useState("");
  const [source, setSource] = useState("");

  const [selectedComm, setSelectedComm] = useState("");
  const [selectedPm, setSelectedPm] = useState("");

  const [selectedProject, setSelectedProject] = useState("");
  const [selectedChannel, setSelectedChannel] = useState("");

  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [pendingPm, setPendingPm] = useState<string | null>(null);
  const [pendingComm, setPendingComm] = useState<string | null>(null);

  const [error, setError] = useState(false);

  const queryClient = useQueryClient();
  const { data: integrationsData } = useIntegrations();
  const initiateAuth = useInitiateIntegrationAuthMutation();
  const taigaConnect = useTaigaConnectMutation();
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

  const isMatchStep = step === "match";

  const projectsQuery = useListProjects(
    selectedPm,
    step === "project" || step === "channel" || isMatchStep,
  );
  const projectMembersQuery = useListProjectMembers(
    selectedPm,
    selectedProject,
    isMatchStep && PROJECT_PROVIDERS.has(selectedPm),
  );
  const channelsQuery = useListChannels(
    selectedComm,
    step === "channel" || isMatchStep,
  );
  const channelMembersQuery = useListChannelMembers(
    selectedComm,
    selectedChannel,
    isMatchStep && CHANNEL_PROVIDERS.has(selectedComm),
  );

  const integrationsById = useMemo(() => {
    const map: Record<string, IntegrationResponse> = {};
    for (const integration of integrationsData?.integrations ?? []) {
      map[integration.provider] = integration;
    }
    return map;
  }, [integrationsData]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === INTEGRATION_OAUTH_MESSAGE) {
        setConnectingProvider(null);
        queryClient.invalidateQueries({ queryKey: listIntegrationsQueryKey() });
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [queryClient]);

  const handleConnect = async (providerId: string) => {
    setConnectingProvider(providerId);
    try {
      const { authorization_url } = await initiateAuth.mutateAsync({
        path: { provider: providerId },
        body: { redirect_source: "onboarding", company_name: company || null },
      });
      const popup = window.open(authorization_url, "_blank", "width=600,height=700");
      if (!popup) {
        window.location.assign(authorization_url);
      }
    } catch {
      setConnectingProvider(null);
    }
  };

  const selectProvider = (provider: IntegrationProvider, isConnected: boolean) => {
    if (step === "comm") {
      setSelectedComm(provider.id);
    } else {
      setSelectedPm(provider.id);
    }
    if (!isConnected) {
      void handleConnect(provider.id);
    }
  };

  const handleTaigaConnect = async (username: string, password: string) => {
    setConnectingProvider("taiga");
    try {
      await taigaConnect.mutateAsync({ username, password });
      setSelectedPm("taiga");
      queryClient.invalidateQueries({ queryKey: listIntegrationsQueryKey() });
    } finally {
      setConnectingProvider(null);
    }
  };

  const buildBody = (): OnboardingRequest => ({
    company_name: company.trim(),
    ...(role ? { role } : {}),
    ...(team ? { team_size: team } : {}),
    ...(source ? { acquisition_source: source } : {}),
    ...(selectedComm ? { comm_platform: selectedComm } : {}),
    ...(selectedPm ? { pm_platform: selectedPm } : {}),
    ...(selectedProject ? { project_id: selectedProject } : {}),
    ...(selectedChannel ? { channel_id: selectedChannel } : {}),
    ...(matches.length ? { matches } : {}),
  });

  const finish = () => {
    if (!company.trim()) {
      setStep("survey");
      setError(true);
      return;
    }
    onComplete?.(buildBody());
  };

  const nextStepAfter = (current: Step): Step => {
    if (current === "survey") return "comm";
    if (current === "comm") return "pm";
    if (current === "pm") {
      if (PROJECT_PROVIDERS.has(selectedPm)) return "project";
      if (CHANNEL_PROVIDERS.has(selectedComm)) return "channel";
      return "match";
    }
    if (current === "project") {
      if (CHANNEL_PROVIDERS.has(selectedComm)) return "channel";
      return "match";
    }
    if (current === "channel") return "match";
    return "match";
  };

  const next = () => {
    if (step === "survey") {
      if (!company.trim()) {
        setError(true);
        return;
      }
      setStep(nextStepAfter(step));
      return;
    }
    if (step === "pm" && !selectedPm) {
      return;
    }
    if (step === "comm" && !selectedComm) {
      return;
    }
    if (step === "project" && !selectedProject && PROJECT_PROVIDERS.has(selectedPm)) {
      return;
    }
    if (step === "channel" && !selectedChannel && CHANNEL_PROVIDERS.has(selectedComm)) {
      return;
    }
    if (step === "match") {
      finish();
      return;
    }
    setStep(nextStepAfter(step));
  };

  const skip = () => {
    if (step === "survey" && !company.trim()) {
      setStep("comm");
      return;
    }
    if (step === "match") {
      finish();
      return;
    }
    setStep(nextStepAfter(step));
  };

  const handlePmClick = (member: MemberRow) => {
    const alreadyMatched = matches.some((m) => m.pm_member_id === member.id);
    if (alreadyMatched) {
      setMatches((ms) =>
        ms.filter((m) => m.pm_member_id !== member.id && m.comm_member_id !== member.id),
      );
      return;
    }
    if (pendingComm) {
      setMatches((ms) => [...ms, { pm_member_id: member.id, comm_member_id: pendingComm }]);
      setPendingPm(null);
      setPendingComm(null);
      return;
    }
    setPendingComm(null);
    setPendingPm((prev) => (prev === member.id ? null : member.id));
  };

  const handleCommClick = (member: MemberRow) => {
    const alreadyMatched = matches.some((m) => m.comm_member_id === member.id);
    if (alreadyMatched) {
      setMatches((ms) =>
        ms.filter((m) => m.pm_member_id !== member.id && m.comm_member_id !== member.id),
      );
      return;
    }
    if (pendingPm) {
      setMatches((ms) => [...ms, { pm_member_id: pendingPm, comm_member_id: member.id }]);
      setPendingPm(null);
      setPendingComm(null);
      return;
    }
    setPendingPm(null);
    setPendingComm((prev) => (prev === member.id ? null : member.id));
  };

  const pmProvider = integrationProviders.find((i) => i.id === selectedPm);
  const commProvider = integrationProviders.find((i) => i.id === selectedComm);

  const matchedIds = useMemo(() => {
    const ids = new Set<string>();
    for (const m of matches) {
      ids.add(m.pm_member_id);
      ids.add(m.comm_member_id);
    }
    return ids;
  }, [matches]);

  const pmMembers = useMemo(
    () => (projectMembersQuery.data?.members ?? []) as MemberRow[],
    [projectMembersQuery.data],
  );
  const commMembers = useMemo(
    () => (channelMembersQuery.data?.members ?? []) as MemberRow[],
    [channelMembersQuery.data],
  );

  const memberById = useMemo(() => {
    const map = new Map<string, MemberRow>();
    for (const m of pmMembers) map.set(m.id, m);
    for (const m of commMembers) map.set(m.id, m);
    return map;
  }, [pmMembers, commMembers]);

  return (
    <Dialog open={open}>
      <DialogContent className="min-w-3xl max-w-lg bg-zinc-950 border-zinc-800 text-white rounded-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="size-5 rounded-md bg-indigo-600 flex items-center justify-center">
              <span className="text-xs">✦</span>
            </div>

            Quick setup
          </DialogTitle>

          <DialogDescription className="text-zinc-400">
            {step === "survey"
              ? "Tell us about your team"
              : step === "comm"
                ? "Choose your Team Link"
                : step === "pm"
                  ? "Choose your Project Hub"
                  : step === "project"
                    ? "Pick a project"
                    : step === "channel"
                      ? "Pick a channel"
                      : "Connect your team"}
          </DialogDescription>
        </DialogHeader>


        {step === "survey" && (
          <div className="space-y-4">

            <div>
              <Label>
                Company name <span className="text-red-500">*</span>
              </Label>

              <Input
                value={company}
                placeholder="Acme Industries"
                className={cn(
                  "mt-2 bg-zinc-900 border-zinc-800",
                  error && "border-red-500"
                )}
                onChange={(e) => {
                  setCompany(e.target.value);
                  setError(false);
                }}
              />

              {error && (
                <p className="text-xs text-red-500 mt-2">
                  Company name is required
                </p>
              )}
            </div>


            <Select value={role} onValueChange={(value) => setRole(value ?? "")}>
              <Label>Your role</Label>

              <SelectTrigger className="mt-2 bg-zinc-900 border-zinc-800">
                <SelectValue placeholder="Select your role" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="engineer">
                  Engineer / Developer
                </SelectItem>
                <SelectItem value="designer">
                  Designer / Creative
                </SelectItem>
                <SelectItem value="pm">
                  Product Manager / Owner
                </SelectItem>
                <SelectItem value="founder">
                  Founder / CXO
                </SelectItem>
                <SelectItem value="other">
                  Other
                </SelectItem>
              </SelectContent>
            </Select>


            <Select value={team} onValueChange={(value) => setTeam(value ?? "")}>
              <Label>Team size</Label>

              <SelectTrigger className="mt-2 bg-zinc-900 border-zinc-800">
                <SelectValue placeholder="Select team size" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="1-5">
                  1–5 people
                </SelectItem>
                <SelectItem value="6-20">
                  6–20 people
                </SelectItem>
                <SelectItem value="21-50">
                  21–50 people
                </SelectItem>
                <SelectItem value="50+">
                  50+ people
                </SelectItem>
              </SelectContent>
            </Select>


            <Select value={source} onValueChange={(value) => setSource(value ?? "")}>
              <Label>How did you find us?</Label>

              <SelectTrigger className="mt-2 bg-zinc-900 border-zinc-800">
                <SelectValue placeholder="Select one" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="google">
                  Google search
                </SelectItem>
                <SelectItem value="social">
                  Social media
                </SelectItem>
                <SelectItem value="friend">
                  Friend or colleague
                </SelectItem>
                <SelectItem value="blog">
                  Article / Blog
                </SelectItem>
                <SelectItem value="other">
                  Other
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}


        {(step === "comm" || step === "pm") && (
          <div className="grid grid-cols-3 gap-3">
            {(step === "comm" ? commProviders : pmProviders).map((p) => {
              const integration = integrationsById[p.id];
              const isConnected = integration?.status === "connected";
              const isExpired =
                integration?.status === "expired" ||
                formatExpiry(integration?.expires_at ?? null) === "Token expired";
              const isError = integration?.status === "error";
              const isConnecting = connectingProvider === p.id;
              const selected =
                step === "comm"
                  ? selectedComm === p.id
                  : selectedPm === p.id;

              if (p.id === "taiga") {
                return (
                  <div
                    key={p.id}
                    className={cn(
                      "rounded-xl border p-4 transition",
                      "bg-zinc-900 border-zinc-800",
                      selected && "border-indigo-500 bg-indigo-500/10"
                    )}
                  >
                    <div className="size-14 rounded-full bg-white mx-auto flex items-center justify-center overflow-hidden">
                      <img
                        src={p.logo}
                        alt={p.name}
                        className="size-8 object-contain"
                      />
                    </div>
                    <p className="mt-2 text-center text-xs text-zinc-300">
                      {p.name}
                    </p>
                    {isConnected ? (
                      <p className="mt-1 flex items-center justify-center gap-1 text-[10px] text-[var(--color-success)]">
                        <span className="size-1.5 rounded-full bg-current" />
                        Connected
                      </p>
                    ) : (
                      <div className="mt-2 flex justify-center">
                        <TaigaConnectForm
                          onConnect={handleTaigaConnect}
                          connecting={isConnecting}
                          dark
                        />
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <button
                  key={p.id}
                  disabled={isConnecting}
                  className={cn(
                    "rounded-xl border p-4 transition",
                    "bg-zinc-900 border-zinc-800",
                    selected &&
                      "border-indigo-500 bg-indigo-500/10",
                    isConnecting && "opacity-70"
                  )}
                  onClick={() => selectProvider(p, isConnected)}
                >
                  <div className="size-14 rounded-full bg-white mx-auto flex items-center justify-center overflow-hidden">
                    <img
                      src={p.logo}
                      alt={p.name}
                      className="size-8 object-contain"
                    />
                  </div>

                  <p className="mt-2 text-xs text-zinc-300">
                    {p.name}
                  </p>

                  {isConnecting ? (
                    <p className="mt-1 flex items-center justify-center gap-1 text-[10px] text-zinc-400">
                      <span className="size-2.5 animate-spin rounded-full border border-current border-t-transparent" />
                      Connecting…
                    </p>
                  ) : isConnected ? (
                    <p className="mt-1 flex items-center justify-center gap-1 text-[10px] text-[var(--color-success)]">
                      <span className="size-1.5 rounded-full bg-current" />
                      Connected
                    </p>
                  ) : isExpired ? (
                    <p className="mt-1 flex items-center justify-center gap-1 text-[10px] text-[var(--color-warning)]">
                      <span className="size-1.5 rounded-full bg-current" />
                      Token expired
                    </p>
                  ) : isError ? (
                    <p className="mt-1 text-center text-[10px] text-red-500">
                      Connection failed. Please try again.
                    </p>
                  ) : null}
                </button>
              );
            })}
          </div>
        )}


        {step === "project" && (
          <div className="space-y-3">
            <p className="text-xs text-zinc-400">
              Which {pmProvider?.name ?? "project"} would you like to sync from?
            </p>
            {projectsQuery.isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-11 animate-pulse rounded-lg bg-zinc-900" />
                ))}
              </div>
            ) : projectsQuery.isError ? (
              <p className="text-xs text-red-400">
                Couldn&apos;t load projects. Please reconnect in Settings.
              </p>
            ) : (projectsQuery.data?.scopes.length ?? 0) === 0 ? (
              <p className="text-xs text-zinc-500">No projects found.</p>
            ) : (
              <ul className="space-y-2">
                {projectsQuery.data?.scopes.map((scope) => (
                  <li key={scope.id}>
                    <button
                      className={cn(
                        "w-full rounded-lg border px-4 py-2.5 text-left text-sm transition",
                        "bg-zinc-900 border-zinc-800 text-white",
                        selectedProject === scope.id &&
                          "border-indigo-500 bg-indigo-500/10"
                      )}
                      onClick={() =>
                        setSelectedProject(scope.id === selectedProject ? "" : scope.id)
                      }
                    >
                      {scope.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}


        {step === "channel" && (
          <div className="space-y-3">
            <p className="text-xs text-zinc-400">
              Which {commProvider?.name ?? "channel"} would you like to sync from?
            </p>
            {channelsQuery.isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-11 animate-pulse rounded-lg bg-zinc-900" />
                ))}
              </div>
            ) : channelsQuery.isError ? (
              <p className="text-xs text-red-400">
                Couldn&apos;t load channels. Please reconnect in Settings.
              </p>
            ) : (channelsQuery.data?.scopes.length ?? 0) === 0 ? (
              <p className="text-xs text-zinc-500">No channels found.</p>
            ) : (
              <ul className="space-y-2">
                {channelsQuery.data?.scopes.map((scope) => (
                  <li key={scope.id}>
                    <button
                      className={cn(
                        "w-full rounded-lg border px-4 py-2.5 text-left text-sm transition",
                        "bg-zinc-900 border-zinc-800 text-white",
                        selectedChannel === scope.id &&
                          "border-indigo-500 bg-indigo-500/10"
                      )}
                      onClick={() =>
                        setSelectedChannel(scope.id === selectedChannel ? "" : scope.id)
                      }
                    >
                      {commProvider?.id === "discord" ? `#${scope.name}` : scope.name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}


        {step === "match" && (
          <div className="space-y-4">
            {!PROJECT_PROVIDERS.has(selectedPm) || !CHANNEL_PROVIDERS.has(selectedComm) ? (
              <p className="text-xs text-zinc-400">
                Member matching is available when syncing Taiga with Discord.
              </p>
            ) : (
              <>
                <p className="text-xs text-zinc-400">
                  Click a person on each side to link them — matched people move to
                  the top and are greyed out.
                </p>

                {matches.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                      Matched ({matches.length})
                    </p>
                    {matches.map((m) => {
                      const pm = memberById.get(m.pm_member_id);
                      const comm = memberById.get(m.comm_member_id);
                      return (
                        <div
                          key={`${m.pm_member_id}:${m.comm_member_id}`}
                          className="flex items-center gap-2 rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-3 py-2"
                        >
                          <span className="min-w-0 flex-1 truncate text-sm text-white">
                            {pm?.name || pm?.username || "Unknown"}
                          </span>
                          <span className="text-zinc-500">
                            <Check size={14} className="text-[var(--color-success)]" />
                          </span>
                          <span className="min-w-0 flex-1 truncate text-sm text-white">
                            {comm?.name || comm?.username || "Unknown"}
                          </span>
                          <button
                            className="text-zinc-500 hover:text-white"
                            onClick={() => {
                              setMatches((ms) =>
                                ms.filter(
                                  (x) =>
                                    x.pm_member_id !== m.pm_member_id ||
                                    x.comm_member_id !== m.comm_member_id,
                                ),
                              );
                            }}
                          >
                            <X size={14} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900">
                    <div className="flex items-center gap-2 border-b border-zinc-800 px-3 py-2.5">
                      <div className="size-6 rounded-full bg-white flex items-center justify-center overflow-hidden">
                        {pmProvider?.logo ? (
                          <img src={pmProvider.logo} alt="" className="size-4 object-contain" />
                        ) : null}
                      </div>
                      <p className="truncate text-xs font-medium text-white">
                        {pmProvider?.name ?? selectedPm}
                      </p>
                    </div>

                    <div className="max-h-56 overflow-y-auto p-2">
                      {projectMembersQuery.isLoading ? (
                        <div className="space-y-2 p-2">
                          {[0, 1, 2].map((i) => (
                            <div key={i} className="flex animate-pulse items-center gap-3">
                              <div className="size-8 rounded-full bg-zinc-800" />
                              <div className="space-y-1.5">
                                <div className="h-3 w-24 rounded bg-zinc-800" />
                                <div className="h-2.5 w-16 rounded bg-zinc-800/60" />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : projectMembersQuery.isError ? (
                        <p className="p-3 text-xs text-red-400">
                          Couldn&apos;t load members. Please reconnect in Settings.
                        </p>
                      ) : pmMembers.length === 0 ? (
                        <p className="p-3 text-xs text-zinc-500">No members found.</p>
                      ) : (
                        <ul className="divide-y divide-zinc-800">
                          {pmMembers.map((m) => {
                            const selected = pendingPm === m.id;
                            const matched = matchedIds.has(m.id);
                            return (
                              <li key={m.id}>
                                <button
                                  disabled={matched}
                                  className={cn(
                                    "flex w-full items-center gap-3 px-2 py-2 text-left transition",
                                    matched && "opacity-40",
                                    selected && "bg-indigo-500/15",
                                  )}
                                  onClick={() => handlePmClick(m)}
                                >
                                  {m.avatar ? (
                                    <img
                                      src={m.avatar}
                                      alt=""
                                      className="size-8 rounded-full object-cover"
                                    />
                                  ) : (
                                    <div className="flex size-8 items-center justify-center rounded-full bg-zinc-800 text-xs font-medium text-zinc-300">
                                      {(m.name || m.username || "?")[0]?.toUpperCase()}
                                    </div>
                                  )}
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm text-white">
                                      {m.name || m.username}
                                    </p>
                                    {m.email ? (
                                      <p className="truncate text-[11px] text-zinc-400">
                                        {m.email}
                                      </p>
                                    ) : m.username ? (
                                      <p className="truncate text-[11px] text-zinc-400">
                                        @{m.username}
                                      </p>
                                    ) : null}
                                  </div>
                                  {matched && (
                                    <Check size={14} className="text-[var(--color-success)]" />
                                  )}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-zinc-800 bg-zinc-900">
                    <div className="flex items-center gap-2 border-b border-zinc-800 px-3 py-2.5">
                      <div className="size-6 rounded-full bg-white flex items-center justify-center overflow-hidden">
                        {commProvider?.logo ? (
                          <img src={commProvider.logo} alt="" className="size-4 object-contain" />
                        ) : null}
                      </div>
                      <p className="truncate text-xs font-medium text-white">
                        {commProvider?.name ?? selectedComm}
                      </p>
                    </div>

                    <div className="max-h-56 overflow-y-auto p-2">
                      {channelMembersQuery.isLoading ? (
                        <div className="space-y-2 p-2">
                          {[0, 1, 2].map((i) => (
                            <div key={i} className="flex animate-pulse items-center gap-3">
                              <div className="size-8 rounded-full bg-zinc-800" />
                              <div className="space-y-1.5">
                                <div className="h-3 w-24 rounded bg-zinc-800" />
                                <div className="h-2.5 w-16 rounded bg-zinc-800/60" />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : channelMembersQuery.isError ? (
                        <p className="p-3 text-xs text-red-400">
                          Couldn&apos;t load members. Please reconnect in Settings.
                        </p>
                      ) : commMembers.length === 0 ? (
                        <p className="p-3 text-xs text-zinc-500">No members found.</p>
                      ) : (
                        <ul className="divide-y divide-zinc-800">
                          {commMembers.map((m) => {
                            const selected = pendingComm === m.id;
                            const matched = matchedIds.has(m.id);
                            return (
                              <li key={m.id}>
                                <button
                                  disabled={matched}
                                  className={cn(
                                    "flex w-full items-center gap-3 px-2 py-2 text-left transition",
                                    matched && "opacity-40",
                                    selected && "bg-indigo-500/15",
                                  )}
                                  onClick={() => handleCommClick(m)}
                                >
                                  {m.avatar ? (
                                    <img
                                      src={m.avatar}
                                      alt=""
                                      className="size-8 rounded-full object-cover"
                                    />
                                  ) : (
                                    <div className="flex size-8 items-center justify-center rounded-full bg-zinc-800 text-xs font-medium text-zinc-300">
                                      {(m.name || m.username || "?")[0]?.toUpperCase()}
                                    </div>
                                  )}
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm text-white">
                                      {m.name || m.username}
                                    </p>
                                    {m.email ? (
                                      <p className="truncate text-[11px] text-zinc-400">
                                        {m.email}
                                      </p>
                                    ) : m.username ? (
                                      <p className="truncate text-[11px] text-zinc-400">
                                        @{m.username}
                                      </p>
                                    ) : null}
                                  </div>
                                  {matched && (
                                    <Check size={14} className="text-[var(--color-success)]" />
                                  )}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}


        <div className="flex gap-2 pt-4">
          <Button
            className="flex-1 bg-indigo-600 hover:bg-indigo-500"
            onClick={next}
            disabled={
              (step === "comm" && !selectedComm) ||
              (step === "pm" && !selectedPm) ||
              (step === "project" && PROJECT_PROVIDERS.has(selectedPm) && !selectedProject) ||
              (step === "channel" && CHANNEL_PROVIDERS.has(selectedComm) && !selectedChannel)
            }
          >
            {step === "match" ? "Finish setup" : "Next"}
          </Button>

          <Button
            variant="outline"
            className="
              border-zinc-800
              bg-transparent
              text-zinc-400
            "
            onClick={skip}
          >
            Skip
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
