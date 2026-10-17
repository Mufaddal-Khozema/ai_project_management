"use client";

import { client } from "./api/client.gen";
import { API_URL, StorageKeys } from "@/constants";

// ---------- 401 refresh + retry ----------

let refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    const data = await res.json();
    const token: string | undefined = data.access_token;
    if (token) {
      localStorage.setItem(StorageKeys.TOKEN, token);
      return token;
    }
    return null;
  } catch {
    return null;
  }
}

function getRefreshToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  let url: RequestInfo | URL;
  let requestInit: RequestInit;

  if (input instanceof Request) {
    url = input.url;
    const headers = new Headers(input.headers);
    let body: BodyInit | null | undefined;
    if (input.method !== "GET" && input.method !== "HEAD") {
      body = await input.clone().text();
    }
    requestInit = { method: input.method, headers, body };
  } else {
    url = input;
    requestInit = init ?? {};
  }

  const response = await fetch(url, requestInit);

  if (response.status === 401) {
    const token = localStorage.getItem(StorageKeys.TOKEN);
    if (!token) return response;

    const newToken = await getRefreshToken();
    if (!newToken) {
      localStorage.removeItem(StorageKeys.TOKEN);
      window.location.href = "/signup";
      return new Promise<Response>(() => {});
    }

    const headers = new Headers(requestInit.headers ?? {});
    headers.set("Authorization", `Bearer ${newToken}`);
    return fetch(url, { ...requestInit, headers });
  }

  return response;
}

// ---------- client setup ----------

client.setConfig({
  baseUrl: API_URL,
  auth: () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(StorageKeys.TOKEN) ?? undefined;
    }
    return undefined;
  },
  fetch: authFetch,
});

export { client };

// Export SDK-generated API functions with proper types
export {
  healthCheck,
  sendOtp,
  verifyOtp,
  refreshToken,
  setupIntent,
  getCurrentSubscription,
  cancelSubscription,
  getInvoices,
  getCurrentUser,
  updateCurrentUser,
  listWorkspaceUsers,
  submitOnboarding,
  listIntegrations,
  initiateIntegrationAuth,
  disconnectIntegration,
  refreshIntegration,
  listMembers,
  listProjects,
  listProjectMembers,
  listChannels,
  listChannelMembers,
  listPlans,
  connectTaiga,
} from "./api/sdk.gen";
