export type IntegrationCategory = "comm" | "pm";

export type IntegrationProviderId =
  | "slack"
  | "teams"
  | "discord"
  | "jira"
  | "clickup"
  | "taiga";

export interface IntegrationProvider {
  id: IntegrationProviderId;
  name: string;
  category: IntegrationCategory;
  logo: string;
  refreshable: boolean;
}

export const integrationProviders: IntegrationProvider[] = [
  {
    id: "slack",
    name: "Slack",
    category: "comm",
    logo: "https://images.icon-icons.com/2699/PNG/512/slack_logo_icon_170727.png",
    refreshable: false,
  },
  {
    id: "teams",
    name: "Teams",
    category: "comm",
    logo: "https://images.icon-icons.com/2397/PNG/512/microsoft_office_teams_logo_icon_145726.png",
    refreshable: true,
  },
  {
    id: "discord",
    name: "Discord",
    category: "comm",
    logo: "https://images.icon-icons.com/3132/PNG/512/discord_social_network_communication_interaction_message_icon_192260.png",
    refreshable: true,
  },
  {
    id: "jira",
    name: "Jira",
    category: "pm",
    logo: "https://images.icon-icons.com/2429/PNG/512/jira_logo_icon_147274.png",
    refreshable: true,
  },
  {
    id: "clickup",
    name: "ClickUp",
    category: "pm",
    logo: "https://images.seeklogo.com/logo-png/38/1/clickup-symbol-logo-png_seeklogo-389754.png",
    refreshable: true,
  },
  {
    id: "taiga",
    name: "Taiga",
    category: "pm",
    logo: "https://docs.taiga.io/images/logo-taiga.png",
    refreshable: true,
  },
];

export const integrationProviderById: Record<string, IntegrationProvider> =
  Object.fromEntries(
    integrationProviders.map((p) => [p.id, p]),
  );

export const INTEGRATION_OAUTH_MESSAGE = "coordinaai:integration-oauth" as const;

export function formatExpiry(expires_at: string | null): string {
  if (!expires_at) return "";
  const expiresAt = new Date(expires_at);
  if (Number.isNaN(expiresAt.getTime())) return "";
  const ms = expiresAt.getTime() - Date.now();
  if (ms <= 0) return "Token expired";
  const days = Math.ceil(ms / (1000 * 60 * 60 * 24));
  return `Token expires in ${days}d`;
}