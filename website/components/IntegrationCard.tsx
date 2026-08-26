"use client";

import { Button } from "@/components/ui/button";
import { TaigaConnectForm } from "@/components/TaigaConnectForm";
import type { IntegrationResponse } from "@/lib/api";
import type { IntegrationProvider } from "@/lib/integrations";
import { formatExpiry } from "@/lib/integrations";

interface Props {
  provider: IntegrationProvider;
  integration?: IntegrationResponse;
  onConnect: () => void;
  onDisconnect: () => void;
  connecting: boolean;
  onConnectWithCredentials?: (username: string, password: string) => Promise<void>;
}

export function IntegrationCard({
  provider,
  integration,
  onConnect,
  onDisconnect,
  connecting,
  onConnectWithCredentials,
}: Props) {
  const status = integration?.status;
  const expiresText = formatExpiry(integration?.expires_at ?? null);
  const expired = status === "expired" || expiresText === "Token expired";
  const needsReauth =
    status === "error" ||
    expired ||
    (status === "connected" && Boolean(expiresText) && !provider.refreshable);

  const credentialConnect =
    provider.id === "taiga" && onConnectWithCredentials !== undefined;
  const showCredentialForm =
    credentialConnect && (!integration || needsReauth);

  let detail = "Not connected";
  let warn = false;
  if (status === "error") {
    detail = "Connection failed. Please try again.";
  } else if (expired) {
    detail = "Token expired — reauthorize";
    warn = true;
  } else if (integration) {
    if (expiresText && !provider.refreshable) {
      detail = expiresText;
      warn = true;
    } else {
      detail = integration.account_name
        ? `Connected to ${integration.account_name}`
        : "Connected";
    }
  }

  const buttonLabel = !integration
    ? "Connect"
    : status === "error"
      ? "Retry"
      : needsReauth
        ? "Reconnect"
        : "Disconnect";

  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-3 transition-colors hover:border-border/50">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-md bg-card text-xs font-medium text-muted-foreground">
          <img src={provider.logo} alt={provider.name} className="size-6 object-contain" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-card-foreground">
            {provider.name}
          </p>
          <p
            className={`truncate text-xs ${
              warn ? "text-[var(--color-warning)]" : "text-muted-foreground"
            }`}
          >
            {detail}
          </p>
        </div>
      </div>

      {showCredentialForm ? (
        <TaigaConnectForm
          onConnect={onConnectWithCredentials}
          connecting={connecting}
        />
      ) : (
        <Button
          size="sm"
          variant={!needsReauth && integration ? "outline" : "default"}
          onClick={needsReauth || !integration ? onConnect : onDisconnect}
          disabled={connecting}
        >
          {connecting ? (
            <>
              <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Connecting…
            </>
          ) : (
            buttonLabel
          )}
        </Button>
      )}
    </div>
  );
}