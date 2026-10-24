/**
 * integrations/identity/IdentityServiceClient.ts
 *
 * Client for root backend's identity & authorization resolution API:
 *   POST /api/identity/resolve
 *
 * Authenticates with a service-to-service key (Authorization: Bearer svc_...)
 * to resolve Discord voice speakers/participants to their real workspace user profiles.
 */

export interface IdentityUser {
  uuid: string;
  email: string | null;
  status: string;
  name: string | null;
  avatar: string | null;
}

export interface IdentityWorkspace {
  uuid: string;
  company_name: string;
}

export interface IdentityEntitlements {
  has_subscription: boolean;
  onboarding_completed: boolean;
}

export interface IdentityIntegration {
  provider: string;
  account_name: string | null;
  status: string;
  token_encrypted: string;
}

export interface ResolveIdentityResponse {
  linked: boolean;
  user?: IdentityUser;
  workspace?: IdentityWorkspace | null;
  entitlements?: IdentityEntitlements;
  integrations?: IdentityIntegration[];
  detail?: string;
}

export class IdentityServiceClient {
  private cache = new Map<string, { data: ResolveIdentityResponse; expiresAt: number }>();

  constructor(
    private backendUrl: string = process.env.BACKEND_URL || 'http://127.0.0.1:8000',
    private serviceApiKey: string = process.env.SERVICE_API_KEY || '',
    private cacheTtlMs: number = 30_000
  ) {}

  isConfigured(): boolean {
    return Boolean(this.backendUrl && this.serviceApiKey);
  }

  async resolveDiscordIdentity(
    externalId: string,
    guildId?: string,
    channelId?: string
  ): Promise<ResolveIdentityResponse> {
    const cacheKey = `discord:${externalId}`;
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.data;
    }

    const url = `${this.backendUrl.replace(/\/$/, '')}/api/identity/resolve`;
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.serviceApiKey}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          provider: 'discord',
          external_id: String(externalId),
          guild_id: guildId ? String(guildId) : null,
          channel_id: channelId ? String(channelId) : null,
        }),
      });

      if (res.status === 200) {
        const data = (await res.json()) as ResolveIdentityResponse;
        this.cache.set(cacheKey, { data, expiresAt: Date.now() + this.cacheTtlMs });
        return data;
      }

      if (res.status === 404) {
        const err = await res.json().catch(() => ({ detail: 'Identity not linked.' })) as any;
        const data: ResolveIdentityResponse = {
          linked: false,
          detail: err.detail || 'Identity not linked.',
        };
        this.cache.set(cacheKey, { data, expiresAt: Date.now() + this.cacheTtlMs });
        return data;
      }

      console.warn(`[IdentityServiceClient] Identity resolve returned ${res.status}: ${res.statusText}`);
      return { linked: false, detail: `Status ${res.status}` };
    } catch (err: any) {
      console.warn(`[IdentityServiceClient] Backend unreachable: ${err.message}`);
      return { linked: false, detail: err.message };
    }
  }
}
