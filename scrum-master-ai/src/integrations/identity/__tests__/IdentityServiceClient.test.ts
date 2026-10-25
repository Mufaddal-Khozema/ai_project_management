import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { IdentityServiceClient } from '../IdentityServiceClient.js';

describe('IdentityServiceClient', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('reports isConfigured when backendUrl and serviceApiKey are present', () => {
    const client = new IdentityServiceClient('http://localhost:8000', 'svc_123');
    expect(client.isConfigured()).toBe(true);

    const unconfigured = new IdentityServiceClient('', '');
    expect(unconfigured.isConfigured()).toBe(false);
  });

  it('resolves Discord identity successfully on 200 response', async () => {
    const mockResponse = {
      linked: true,
      user: {
        uuid: '00000000-0000-0000-0000-000000000001',
        email: 'alice@example.com',
        name: 'Alice Smith',
        status: 'email_verified',
        avatar: null,
      },
      workspace: {
        uuid: '00000000-0000-0000-0000-000000000002',
        company_name: 'Acme Corp',
      },
      entitlements: {
        has_subscription: true,
        onboarding_completed: true,
      },
      integrations: [
        {
          provider: 'taiga',
          account_name: 'alice_taiga',
          status: 'connected',
          token_encrypted: 'encrypted_blob',
        },
      ],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => mockResponse,
    } as any);

    const client = new IdentityServiceClient('http://mock-backend:8000', 'svc_test_key');
    const result = await client.resolveDiscordIdentity('1319579537012424797', '1489127884319625276', '1489127884319625279');

    expect(result.linked).toBe(true);
    expect(result.user?.name).toBe('Alice Smith');
    expect(result.workspace?.company_name).toBe('Acme Corp');
    expect(result.entitlements?.has_subscription).toBe(true);
    expect(result.integrations?.length).toBe(1);

    // Verify cache hit
    const cachedResult = await client.resolveDiscordIdentity('1319579537012424797');
    expect(cachedResult.user?.name).toBe('Alice Smith');
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('handles 404 unlinked identity cleanly without throwing', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 404,
      json: async () => ({ detail: 'Identity not linked.' }),
    } as any);

    const client = new IdentityServiceClient('http://mock-backend:8000', 'svc_test_key');
    const result = await client.resolveDiscordIdentity('999999999999');

    expect(result.linked).toBe(false);
    expect(result.detail).toBe('Identity not linked.');
  });
});
