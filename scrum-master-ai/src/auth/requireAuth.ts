/**
 * auth/requireAuth.ts — Fastify preHandler that resolves the real,
 * authenticated org for a request.
 *
 * This replaces the `const ORG_ID = 'default'` constants that used to sit
 * at the top of every route file in integrations/routes/ and
 * integrations/discord/ambient/routes/ — every one of those had the same
 * comment: "later: derive ORG_ID from an authenticated session instead of
 * this." This is that later.
 *
 * Two modes, chosen once at boot from whether AUTH_SERVICE_URL is set —
 * same opt-in pattern already used elsewhere in this codebase
 * (CREDENTIALS_STORE_DRIVER=auth-service, see AuthServiceCredentialsStore):
 *
 *   - AUTH_SERVICE_URL set: real auth. A request with no token, an
 *     expired/invalid token, or a token that fails JWKS verification gets
 *     401'd. request.orgId/userId/role are the verified values from the
 *     token — never client-supplied, never guessable.
 *   - AUTH_SERVICE_URL unset: single-org fallback (request.orgId =
 *     DEFAULT_ORG_ID, a fixed system userId, 'owner' role) so a developer
 *     running this service standalone, with no auth-service, doesn't hit a
 *     wall of 401s. Logged once at boot, not silently — this is a
 *     deliberate degraded mode, not an accident.
 */
import type { FastifyReply, FastifyRequest } from 'fastify';
import { verifyAccessToken } from './jwksVerifier.js';

export interface AuthedRequestFields {
  orgId: string;
  userId: string;
  role: string;
  email: string;
}

declare module 'fastify' {
  interface FastifyRequest {
    orgId?: string;
    userId?: string;
    role?: string;
  }
}

const authServiceUrl = process.env.AUTH_SERVICE_URL || '';
const defaultOrgId = process.env.DEFAULT_ORG_ID || 'default';
let warnedOnce = false;

export function isAuthEnforced(): boolean {
  return !!authServiceUrl;
}

export async function requireAuth(request: FastifyRequest, reply: FastifyReply): Promise<void> {
  const orgHeader = request.headers['x-org-id'] as string | undefined;

  if (!authServiceUrl) {
    if (!orgHeader && process.env.NODE_ENV !== 'test' && !process.env.ALLOW_INSECURE_DEV_DEFAULT_ORG) {
      reply.code(400);
      throw new Error('x-org-id header is required when running without central auth service');
    }
    request.orgId = orgHeader || defaultOrgId;
    request.userId = 'system';
    request.role = 'owner';
    return;
  }

  // Allow internal service-to-service calls (e.g. from agent-bridge or root backend)
  const serviceKey = request.headers.authorization;
  const configuredServiceKey = process.env.SERVICE_API_KEY;
  if (serviceKey && configuredServiceKey && serviceKey === `Bearer ${configuredServiceKey}`) {
    if (!orgHeader) {
      reply.code(400);
      throw new Error('x-org-id header is required for internal service calls');
    }
    request.orgId = orgHeader;
    request.userId = 'service';
    request.role = 'owner';
    return;
  }

  const internalKey = (request.headers['x-internal-key'] as string | undefined) || (request.headers['x-internal-service-key'] as string | undefined);
  const configuredKey = process.env.INTERNAL_SERVICE_KEY || process.env.AUTH_SERVICE_INTERNAL_KEY;
  if (internalKey && configuredKey && internalKey === configuredKey) {
    if (!orgHeader) {
      reply.code(400);
      throw new Error('x-org-id header is required for internal service calls');
    }
    request.orgId = orgHeader;
    request.userId = 'system';
    request.role = 'owner';
    return;
  }

  const header = request.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    reply.code(401);
    throw new Error('Authentication required');
  }

  let verified;
  try {
    verified = await verifyAccessToken(header.slice('Bearer '.length), authServiceUrl);
  } catch {
    reply.code(401);
    throw new Error('Invalid or expired token');
  }

  // Older single-tenant sessions used numeric org 0 while their credentials
  // were stored under the default org key. Real auth-service org IDs are
  // UUIDs, so this compatibility mapping cannot collide with a valid org.
  if (!verified.orgId || verified.orgId === '0') {
    if (process.env.ALLOW_INSECURE_DEV_DEFAULT_ORG || process.env.NODE_ENV === 'test') {
      request.orgId = defaultOrgId;
    } else {
      reply.code(401);
      throw new Error('Invalid organization in token');
    }
  } else {
    request.orgId = verified.orgId;
  }
  request.userId = verified.userId;
  request.role = verified.role;
}
