"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogHeader,
  DialogFooter,
} from "@/components/ui/dialog";
import { useState, useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCurrentUser,
  useUpdateProfileMutation,
  useIntegrations,
  useTaigaConnectMutation,
  useInitiateIntegrationAuthMutation,
  useDisconnectIntegrationMutation,
  listIntegrationsQueryKey,
  type IntegrationResponse,
} from "@/lib/api";
import { IntegrationCard } from "@/components/IntegrationCard";
import { BillingTab } from "@/components/BillingTab";
import {
  integrationProviders,
  integrationProviderById,
  INTEGRATION_OAUTH_MESSAGE,
  type IntegrationProviderId,
} from "@/lib/integrations";
import {
  Building2,
  UserCircle,
  CreditCard,
  Bell,
  Shield,
  Trash2,
  AlertTriangle,
  Check,
  Mail,
  KeyRound,
  Palette,
} from "lucide-react";

export default function SettingsPage() {
  const { data: user, isLoading } = useCurrentUser();
  const updateProfile = useUpdateProfileMutation();
  const queryClient = useQueryClient();

  const { data: integrationsData, isLoading: integrationsLoading, isError: integrationsError } =
    useIntegrations();
  const initiateAuth = useInitiateIntegrationAuthMutation();
  const disconnectMutation = useDisconnectIntegrationMutation();
  const taigaConnect = useTaigaConnectMutation();

  const integrationsById = useMemo(() => {
    const map: Record<string, IntegrationResponse> = {};
    for (const integration of integrationsData?.integrations ?? []) {
      map[integration.provider] = integration;
    }
    return map;
  }, [integrationsData]);

  const [connectingProvider, setConnectingProvider] = useState<IntegrationProviderId | null>(null);
  const [disconnectProvider, setDisconnectProvider] = useState<IntegrationProviderId | null>(null);

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

  const handleConnect = async (providerId: IntegrationProviderId) => {
    setConnectingProvider(providerId);
    try {
      const { authorization_url } = await initiateAuth.mutateAsync({
        path: { provider: providerId },
        body: { redirect_source: "settings" },
      });
      const popup = window.open(authorization_url, "_blank", "width=600,height=700");
      if (!popup) {
        window.location.assign(authorization_url);
      }
    } catch {
      setConnectingProvider(null);
    }
  };

  const handleDisconnect = async () => {
    if (!disconnectProvider) return;
    try {
      await disconnectMutation.mutateAsync({ path: { provider: disconnectProvider } });
      queryClient.invalidateQueries({ queryKey: listIntegrationsQueryKey() });
    } finally {
      setDisconnectProvider(null);
    }
  };

  const handleTaigaConnect = async (username: string, password: string) => {
    setConnectingProvider("taiga");
    try {
      await taigaConnect.mutateAsync({ username, password });
      queryClient.invalidateQueries({ queryKey: listIntegrationsQueryKey() });
    } finally {
      setConnectingProvider(null);
    }
  };

  const [prevUser, setPrevUser] = useState(user);
  const [displayName, setDisplayName] = useState(user?.name ?? "");
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar ?? "");

  if (user !== prevUser) {
    setPrevUser(user);
    setDisplayName(user?.name ?? "");
    setAvatarUrl(user?.avatar ?? "");
  }

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [saved, setSaved] = useState(false);

  const handleSaveProfile = async () => {
    try {
      await updateProfile.mutateAsync({
        body: {
          name: displayName || null,
          avatar: avatarUrl || null,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  return (
      <>
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-card-foreground">
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage workspace, account, and billing preferences
        </p>
      </div>

      <Tabs defaultValue="workspace" data-horizontal="true">
        <TabsList className="mb-2">
          <TabsTrigger value="workspace">
            <Building2 size={13} className="mr-1.5" />
            Workspace
          </TabsTrigger>
          <TabsTrigger value="profile">
            <UserCircle size={13} className="mr-1.5" />
            User profile
          </TabsTrigger>
          <TabsTrigger value="billing">
            <CreditCard size={13} className="mr-1.5" />
            Billing
          </TabsTrigger>
        </TabsList>

        <TabsContent value="workspace" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>General</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Workspace name
                  </label>
                  <Input defaultValue="Acme Engineering" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Slug
                  </label>
                  <Input defaultValue="acme-eng" />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">
                  Description
                </label>
                <Input defaultValue="Internal coordination dashboard for Platform, Mobile, and QA teams." />
              </div>

              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Timezone
                  </label>
                  <Select defaultValue="utc">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="utc">
                        UTC (Coordinated Universal Time)
                      </SelectItem>
                      <SelectItem value="est">
                        America/New_York (EST/EDT)
                      </SelectItem>
                      <SelectItem value="pst">
                        America/Los_Angeles (PST/PDT)
                      </SelectItem>
                      <SelectItem value="gmt">
                        Europe/London (GMT/BST)
                      </SelectItem>
                      <SelectItem value="cet">
                        Europe/Berlin (CET/CEST)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Week starts on
                  </label>
                  <Select defaultValue="mon">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mon">Monday</SelectItem>
                      <SelectItem value="sun">Sunday</SelectItem>
                      <SelectItem value="sat">Saturday</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-4">
                <div className="flex items-center gap-3">
                  <Bell size={16} className="text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      Digest emails
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Weekly summary every Monday
                    </p>
                  </div>
                </div>
                <div className="flex h-6 w-11 cursor-pointer items-center rounded-full bg-primary px-0.5 transition-colors">
                  <div className="h-5 w-5 translate-x-5 rounded-full bg-white shadow-sm" />
                </div>
              </div>

              <div className="flex justify-end">
                <Button size="sm" onClick={() => { setSaved(true); setTimeout(() => setSaved(false), 2000); }}>
                  {saved ? (
                    <>
                      <Check size={14} className="mr-1" /> Saved
                    </>
                  ) : (
                    "Save changes"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Integrations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {integrationsLoading ? (
                <>
                  {integrationProviders.map((p) => (
                    <div
                      key={p.id}
                      className="flex animate-pulse items-center justify-between rounded-lg border border-border bg-muted p-3"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-md bg-card" />
                        <div className="space-y-1.5">
                          <div className="h-3.5 w-24 rounded bg-card" />
                          <div className="h-3 w-32 rounded bg-card/60" />
                        </div>
                      </div>
                      <div className="h-7 w-20 rounded-lg bg-card" />
                    </div>
                  ))}
                </>
              ) : integrationsError ? (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                  Failed to load integrations. Please try again.
                </div>
              ) : (
                <>
                  {integrationProviders.map((provider) => (
                    <IntegrationCard
                      key={provider.id}
                      provider={provider}
                      integration={integrationsById[provider.id]}
                      connecting={connectingProvider === provider.id}
                      onConnect={() => handleConnect(provider.id)}
                      onDisconnect={() => setDisconnectProvider(provider.id)}
                      onConnectWithCredentials={
                        provider.id === "taiga" ? handleTaigaConnect : undefined
                      }
                    />
                  ))}
                  {(integrationsData?.integrations.length ?? 0) === 0 && (
                    <p className="pt-1 text-xs text-muted-foreground">
                      Connect your communication and project tools to start coordinating.
                    </p>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card className="border-destructive/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle size={14} />
                Danger zone
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    Delete workspace
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Permanently remove all data, projects, and history. This
                    cannot be undone.
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 size={13} className="mr-1" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Public profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {isLoading ? (
                <div className="space-y-4">
                  <div className="h-16 w-16 rounded-full bg-muted animate-pulse" />
                  <div className="h-10 rounded-lg bg-muted animate-pulse" />
                  <div className="h-10 rounded-lg bg-muted animate-pulse" />
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-4">
                    <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-primary to-[#4f46e5] text-lg font-semibold text-primary-foreground">
                      {avatarUrl ? (
                        <img src={avatarUrl} alt="" className="size-full object-cover" />
                      ) : (
                        user?.name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? "?"
                      )}
                    </div>
                    <div>
                      <Button variant="outline" size="sm">
                        Change avatar
                      </Button>
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Paste an image URL below
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">
                      Avatar URL
                    </label>
                    <Input
                      value={avatarUrl}
                      onChange={(e) => setAvatarUrl(e.target.value)}
                      placeholder="https://example.com/avatar.jpg"
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        Display name
                      </label>
                      <Input
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        placeholder="Your name"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        Email
                      </label>
                      <div className="relative">
                        <Mail
                          size={14}
                          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                        />
                        <Input value={user?.email ?? ""} className="pl-9" disabled />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      onClick={handleSaveProfile}
                      disabled={updateProfile.isPending}
                    >
                      {updateProfile.isPending ? (
                        <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      ) : saved ? (
                        <>
                          <Check size={14} className="mr-1" /> Saved
                        </>
                      ) : (
                        "Save profile"
                      )}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Security</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-4">
                <div className="flex items-center gap-3">
                  <KeyRound size={16} className="text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      Password
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Last changed 3 months ago
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Change
                </Button>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-4">
                <div className="flex items-center gap-3">
                  <Shield size={16} className="text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      Two-factor auth
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Enabled via authenticator app
                    </p>
                  </div>
                </div>
                <Badge variant="outline">Active</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Palette size={16} className="text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      Theme
                    </p>
                    <p className="text-xs text-muted-foreground">
                      System preference
                    </p>
                  </div>
                </div>
                <Select defaultValue="system">
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="system">System</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bell size={16} className="text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      Notifications
                    </p>
                    <p className="text-xs text-muted-foreground">
                      In-app and push
                    </p>
                  </div>
                </div>
                <div className="flex h-6 w-11 cursor-pointer items-center rounded-full bg-primary px-0.5 transition-colors">
                  <div className="h-5 w-5 translate-x-5 rounded-full bg-white shadow-sm" />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="billing" className="space-y-4">
          <BillingTab />
        </TabsContent>
      </Tabs>

      <Dialog
        open={disconnectProvider !== null}
        onOpenChange={(open) => !open && setDisconnectProvider(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Disconnect{" "}
              {disconnectProvider
                ? integrationProviderById[disconnectProvider]?.name
                : ""}
              ?
            </DialogTitle>
            <DialogDescription>
              Coordination from this workspace will pause. You can reconnect at
              any time.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDisconnectProvider(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={disconnectMutation.isPending}
              onClick={handleDisconnect}
            >
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete workspace</DialogTitle>
            <DialogDescription>
              This action is irreversible. All projects, data, and history will
              be permanently erased.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Type <b className="text-card-foreground">acme-eng</b> to confirm:
            </p>
            <Input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="acme-eng"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" size="sm" onClick={() => setDeleteOpen(false)}>
              Never mind
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={confirmText !== "acme-eng"}
              onClick={() => {
                setDeleteOpen(false);
                setConfirmText("");
              }}
            >
              Permanently delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
