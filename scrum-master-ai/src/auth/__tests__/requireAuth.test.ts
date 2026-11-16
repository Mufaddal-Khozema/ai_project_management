import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../jwksVerifier.js', () => ({
  verifyAccessToken: vi.fn(),
}));

function fakeReply() {
  return { code: vi.fn().mockReturnThis() } as any;
}

describe('requireAuth', () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    process.env = { ...originalEnv };
    vi.resetModules();
    vi.restoreAllMocks();
  });

  describe('AUTH_SERVICE_URL unset â€” single-org fallback mode', () => {
    beforeEach(() => {
      delete process.env.AUTH_SERVICE_URL;
    });

    it('sets orgId to "default" without requiring a token', async () => {
      const { requireAuth } = await import('../requireAuth.js');
      const request: any = { headers: {} };
      await requireAuth(request, fakeReply());

      expect(request.orgId).toBe('default');
      expect(request.role).toBe('owner');
    });

    it('isAuthEnforced() reports false', async () => {
      const { isAuthEnforced } = await import('../requireAuth.js');
      expect(isAuthEnforced()).toBe(false);
    });
  });

  describe('AUTH_SERVICE_URL set â€” real auth enforced', () => {
    beforeEach(() => {
      process.env.AUTH_SERVICE_URL = 'http://auth-service:4000';
    });

    it('rejects a request with no Authorization header', async () => {
      const { requireAuth } = await import('../requireAuth.js');
      const reply = fakeReply();
      const request: any = { headers: {} };

      await expect(requireAuth(request, reply)).rejects.toThrow(/Authentication required/);
      expect(reply.code).toHaveBeenCalledWith(401);
    });

    it('rejects a malformed Authorization header (not Bearer)', async () => {
      const { requireAuth } = await import('../requireAuth.js');
      const reply = fakeReply();
      const request: any = { headers: { authorization: 'Basic abc123' } };

      await expect(requireAuth(request, reply)).rejects.toThrow(/Authentication required/);
    });

    it('rejects a token that fails verification', async () => {
      const { verifyAccessToken } = await import('../jwksVerifier.js');
      vi.mocked(verifyAccessToken).mockRejectedValue(new Error('signature invalid'));

      const { requireAuth } = await import('../requireAuth.js');
      const reply = fakeReply();
      const request: any = { headers: { authorization: 'Bearer bad-token' } };

      await expect(requireAuth(request, reply)).rejects.toThrow(/Invalid or expired token/);
      expect(reply.code).toHaveBeenCalledWith(401);
    });

    it('sets orgId/userId/role from a valid token â€” never from client input', async () => {
      const { verifyAccessToken } = await import('../jwksVerifier.js');
      vi.mocked(verifyAccessToken).mockResolvedValue({
        orgId: 'org-abc', userId: 'user-123', role: 'admin', email: 'a@b.test',
      });

      const { requireAuth } = await import('../requireAuth.js');
      const request: any = { headers: { authorization: 'Bearer valid-token' } };
      await requireAuth(request, fakeReply());

      expect(request.orgId).toBe('org-abc');
      expect(request.userId).toBe('user-123');
      expect(request.role).toBe('admin');
    });

    it('maps the legacy org 0 session to the configured default org', async () => {
      process.env.DEFAULT_ORG_ID = 'default-org';
      const { verifyAccessToken } = await import('../jwksVerifier.js');
      vi.mocked(verifyAccessToken).mockResolvedValue({
        orgId: '0', userId: 'user-123', role: 'admin', email: 'a@b.test',
      });

      const { requireAuth } = await import('../requireAuth.js');
      const request: any = { headers: { authorization: 'Bearer token' } };
      await requireAuth(request, fakeReply());

      expect(request.orgId).toBe('default-org');
    });

    it('handles service-to-service calls with SERVICE_API_KEY and x-org-id', async () => {
      process.env.SERVICE_API_KEY = 'secret-svc-key';
      const { requireAuth } = await import('../requireAuth.js');
      const request: any = {
        headers: {
          authorization: 'Bearer secret-svc-key',
          'x-org-id': 'tenant-uuid-123',
        },
      };
      await requireAuth(request, fakeReply());

      expect(request.orgId).toBe('tenant-uuid-123');
      expect(request.userId).toBe('service');
      expect(request.role).toBe('owner');
    });

    it('rejects service-to-service calls with missing x-org-id', async () => {
      process.env.SERVICE_API_KEY = 'secret-svc-key';
      const { requireAuth } = await import('../requireAuth.js');
      const reply = fakeReply();
      const request: any = {
        headers: {
          authorization: 'Bearer secret-svc-key',
        },
      };

      await expect(requireAuth(request, reply)).rejects.toThrow(/x-org-id header is required/);
      expect(reply.code).toHaveBeenCalledWith(400);
    });

    it('handles internal key authentication with x-org-id', async () => {
      process.env.INTERNAL_SERVICE_KEY = 'internal-secret';
      const { requireAuth } = await import('../requireAuth.js');
      const request: any = {
        headers: {
          'x-internal-key': 'internal-secret',
          'x-org-id': 'tenant-internal-456',
        },
      };
      await requireAuth(request, fakeReply());

      expect(request.orgId).toBe('tenant-internal-456');
      expect(request.userId).toBe('system');
      expect(request.role).toBe('owner');
    });

    it('rejects internal key authentication with missing x-org-id', async () => {
      process.env.INTERNAL_SERVICE_KEY = 'internal-secret';
      const { requireAuth } = await import('../requireAuth.js');
      const reply = fakeReply();
      const request: any = {
        headers: {
          'x-internal-key': 'internal-secret',
        },
      };

      await expect(requireAuth(request, reply)).rejects.toThrow(/x-org-id header is required/);
      expect(reply.code).toHaveBeenCalledWith(400);
    });

    it('isAuthEnforced() reports true', async () => {
      const { isAuthEnforced } = await import('../requireAuth.js');
      expect(isAuthEnforced()).toBe(true);
    });
  });
});
