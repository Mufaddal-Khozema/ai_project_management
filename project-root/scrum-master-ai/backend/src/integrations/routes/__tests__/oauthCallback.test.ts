import { describe, expect, it, vi } from 'vitest';
import Fastify from 'fastify';
import registerIntegrationRoutes from '../integrations.js';

describe('OAuth Callback Routes', () => {
  it('handles org-scoped /integrations/:orgId/:provider/callback route', async () => {
    const app = Fastify();
    const mockOAuth = {
      handleCallback: vi.fn().mockResolvedValue({ redirectTo: 'http://localhost:5173/?integration=discord&status=connected' }),
    } as any;
    const mockStore = {} as any;
    const mockCreds = {} as any;

    registerIntegrationRoutes(app, {
      oauth: mockOAuth,
      store: mockStore,
      credentialsStore: mockCreds,
    });

    const response = await app.inject({
      method: 'GET',
      url: '/integrations/org-456/discord/callback?code=test-code&state=signed-state',
    });

    expect(response.statusCode).toBe(302);
    expect(response.headers.location).toBe('http://localhost:5173/?integration=discord&status=connected');
    expect(mockOAuth.handleCallback).toHaveBeenCalledWith(
      expect.any(String),
      'discord',
      'test-code',
      'signed-state',
      'org-456'
    );
  });

  it('handles legacy /integrations/:provider/callback route', async () => {
    const app = Fastify();
    const mockOAuth = {
      handleCallback: vi.fn().mockResolvedValue({ redirectTo: 'http://localhost:5173/?integration=discord&status=connected' }),
    } as any;

    registerIntegrationRoutes(app, {
      oauth: mockOAuth,
      store: {} as any,
      credentialsStore: {} as any,
    });

    const response = await app.inject({
      method: 'GET',
      url: '/integrations/discord/callback?code=test-code&state=signed-state',
    });

    expect(response.statusCode).toBe(302);
    expect(mockOAuth.handleCallback).toHaveBeenCalledWith(
      expect.any(String),
      'discord',
      'test-code',
      'signed-state',
      undefined
    );
  });
});
