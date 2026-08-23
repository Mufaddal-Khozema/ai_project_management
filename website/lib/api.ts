"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  apiAuthEmailSendOtpSendOtpHandlerMutation,
  apiAuthEmailVerifyOtpVerifyOtpHandlerMutation,
  apiIntegrationsListIntegrationsOptions,
  apiIntegrationsProviderAuthInitiateAuthMutation,
  apiIntegrationsProviderDisconnectDisconnectMutation,
  apiIntegrationsProviderRefreshRefreshMutation,
  apiIntegrationsProviderMembersListMembersOptions,
  apiIntegrationsProviderProjectsListProjectsOptions,
  apiIntegrationsProviderProjectsProjectIdMembersListProjectMembersOptions,
  apiIntegrationsProviderChannelsListChannelsOptions,
  apiIntegrationsProviderChannelsChannelIdMembersListChannelMembersOptions,
  apiOnboardingSubmitOnboardingMutation,
  apiPaymentsSetupIntentSetupIntentHandlerMutation,
  apiPaymentsCurrentCurrentSubscriptionHandlerOptions,
  apiPaymentsCancelCancelSubscriptionHandlerMutation,
  apiPaymentsInvoicesListInvoicesHandlerOptions,
  apiUsersMeGetCurrentUserOptions,
  apiUsersMeUpdateCurrentUserMutation,
} from "./api/@tanstack/react-query.gen";
import { client } from "./api/client.gen";
import type { IntegrationResponse } from "./api/types.gen";
import { StorageKeys } from "@/constants";

// ---------- 401 refresh + retry ----------

let refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/refresh", { method: "POST" });
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
  // Normalise to (url, requestInit) so the retry never reuses a consumed Request object.
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
  auth: () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(StorageKeys.TOKEN) ?? undefined;
    }
    return undefined;
  },
  fetch: authFetch,
});

export { client as sdk };
export { apiHealthHealthCheck as healthCheck } from "./api/sdk.gen";
export { apiAuthEmailSendOtpSendOtpHandler as sendOtp } from "./api/sdk.gen";
export { apiAuthEmailVerifyOtpVerifyOtpHandler as verifyOtp } from "./api/sdk.gen";
export { apiAuthRefreshRefreshHandler as refreshToken } from "./api/sdk.gen";
export { apiPaymentsSetupIntentSetupIntentHandler as setupIntent } from "./api/sdk.gen";
export { apiPaymentsCurrentCurrentSubscriptionHandler as getCurrentSubscription } from "./api/sdk.gen";
export { apiPaymentsCancelCancelSubscriptionHandler as cancelSubscription } from "./api/sdk.gen";
export { apiPaymentsInvoicesListInvoicesHandler as getInvoices } from "./api/sdk.gen";
export { apiUsersMeGetCurrentUser as getCurrentUser } from "./api/sdk.gen";
export { apiUsersMeUpdateCurrentUser as updateCurrentUser } from "./api/sdk.gen";
export { apiOnboardingSubmitOnboarding as submitOnboarding } from "./api/sdk.gen";
export { apiIntegrationsListIntegrations as listIntegrations } from "./api/sdk.gen";
export { apiIntegrationsProviderAuthInitiateAuth as initiateIntegrationAuth } from "./api/sdk.gen";
export { apiIntegrationsProviderDisconnectDisconnect as disconnectIntegration } from "./api/sdk.gen";
export { apiIntegrationsProviderRefreshRefresh as refreshIntegration } from "./api/sdk.gen";

export interface TaigaConnectRequest {
  username: string;
  password: string;
}

export async function connectTaiga(
  username: string,
  password: string,
): Promise<IntegrationResponse> {
  const { data, error } = await client.post({
    url: "/api/integrations/taiga/connect",
    body: { username, password },
  });
  if (error || !data) throw error;
  return data as IntegrationResponse;
}

export { apiAuthEmailSendOtpSendOtpHandlerMutation as sendOtpMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiAuthEmailVerifyOtpVerifyOtpHandlerMutation as verifyOtpMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiPaymentsSetupIntentSetupIntentHandlerMutation as setupIntentMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiPaymentsCurrentCurrentSubscriptionHandlerOptions as currentSubscriptionOptions } from "./api/@tanstack/react-query.gen";
export { apiPaymentsCurrentCurrentSubscriptionHandlerQueryKey as currentSubscriptionQueryKey } from "./api/@tanstack/react-query.gen";
export { apiPaymentsCancelCancelSubscriptionHandlerMutation as cancelSubscriptionMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiPaymentsInvoicesListInvoicesHandlerOptions as invoicesOptions } from "./api/@tanstack/react-query.gen";
export { apiOnboardingSubmitOnboardingMutation as submitOnboardingMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiUsersMeGetCurrentUserOptions as getCurrentUserOptions } from "./api/@tanstack/react-query.gen";
export { apiUsersMeUpdateCurrentUserMutation as updateCurrentUserMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsListIntegrationsOptions as listIntegrationsOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderAuthInitiateAuthMutation as initiateIntegrationAuthMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderDisconnectDisconnectMutation as disconnectIntegrationMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderRefreshRefreshMutation as refreshIntegrationMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsListIntegrationsQueryKey as listIntegrationsQueryKey } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderProjectsListProjectsOptions as listProjectsOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderProjectsProjectIdMembersListProjectMembersOptions as listProjectMembersOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderChannelsListChannelsOptions as listChannelsOptions } from "./api/@tanstack/react-query.gen";
export { apiIntegrationsProviderChannelsChannelIdMembersListChannelMembersOptions as listChannelMembersOptions } from "./api/@tanstack/react-query.gen";

export function useSendOtpMutation() {
  return useMutation(apiAuthEmailSendOtpSendOtpHandlerMutation());
}

export function useVerifyOtpMutation() {
  return useMutation(apiAuthEmailVerifyOtpVerifyOtpHandlerMutation());
}

export function useCurrentUser() {
  return useQuery(apiUsersMeGetCurrentUserOptions());
}

export function useCurrentSubscription() {
  return useQuery(apiPaymentsCurrentCurrentSubscriptionHandlerOptions());
}

export function useInvoices() {
  return useQuery(apiPaymentsInvoicesListInvoicesHandlerOptions());
}

export function useCancelSubscriptionMutation() {
  return useMutation(apiPaymentsCancelCancelSubscriptionHandlerMutation());
}

export function useUpdateProfileMutation() {
  return useMutation(apiUsersMeUpdateCurrentUserMutation());
}

export function useSubmitOnboardingMutation() {
  return useMutation(apiOnboardingSubmitOnboardingMutation());
}

export function useIntegrations() {
  return useQuery(apiIntegrationsListIntegrationsOptions());
}

export function useInitiateIntegrationAuthMutation() {
  return useMutation(apiIntegrationsProviderAuthInitiateAuthMutation());
}

export function useDisconnectIntegrationMutation() {
  return useMutation(apiIntegrationsProviderDisconnectDisconnectMutation());
}

export function useRefreshIntegrationMutation() {
  return useMutation(apiIntegrationsProviderRefreshRefreshMutation());
}

export function useTaigaConnectMutation() {
  return useMutation({
    mutationFn: ({ username, password }: TaigaConnectRequest) =>
      connectTaiga(username, password),
  });
}

export function useListMembers(provider: string, enabled = true) {
  return useQuery({
    ...apiIntegrationsProviderMembersListMembersOptions({
      path: { provider },
    }),
    enabled: enabled && provider.length > 0,
  });
}

export function useListProjects(provider: string, enabled = true) {
  return useQuery({
    ...apiIntegrationsProviderProjectsListProjectsOptions({
      path: { provider },
    }),
    enabled: enabled && provider.length > 0,
  });
}

export function useListProjectMembers(
  provider: string,
  projectId: string,
  enabled = true,
) {
  return useQuery({
    ...apiIntegrationsProviderProjectsProjectIdMembersListProjectMembersOptions({
      path: { provider, project_id: projectId },
    }),
    enabled: enabled && provider.length > 0 && projectId.length > 0,
  });
}

export function useListChannels(provider: string, enabled = true) {
  return useQuery({
    ...apiIntegrationsProviderChannelsListChannelsOptions({
      path: { provider },
    }),
    enabled: enabled && provider.length > 0,
  });
}

export function useListChannelMembers(
  provider: string,
  channelId: string,
  enabled = true,
) {
  return useQuery({
    ...apiIntegrationsProviderChannelsChannelIdMembersListChannelMembersOptions({
      path: { provider, channel_id: channelId },
    }),
    enabled: enabled && provider.length > 0 && channelId.length > 0,
  });
}

export type { SendOtpRequest, SendOtpResponse, VerifyOtpRequest, SetupIntentRequest, SetupIntentResponse } from "./api/types.gen";
export type { ApiAuthEmailSendOtpSendOtpHandlerData as SendOtpData } from "./api/types.gen";
export type { ApiAuthEmailVerifyOtpVerifyOtpHandlerData as VerifyOtpData } from "./api/types.gen";
export type { ApiPaymentsSetupIntentSetupIntentHandlerData as SetupIntentData } from "./api/types.gen";
export type { ApiAuthEmailSendOtpSendOtpHandlerResponse as SendOtpResponseType } from "./api/types.gen";
export type { ApiAuthEmailVerifyOtpVerifyOtpHandlerResponse as VerifyOtpResponseType } from "./api/types.gen";
export type { ApiPaymentsSetupIntentSetupIntentHandlerResponse as SetupIntentResponseType } from "./api/types.gen";
export type { UserResponse as CurrentUser, UpdateProfileRequest } from "./api/types.gen";
export type { SubscriptionResponse, CancelSubscriptionResponse, InvoiceResponse, InvoicesResponse } from "./api/types.gen";
export type { OnboardingRequest, WorkspaceResponse, MatchItem } from "./api/types.gen";
export type { IntegrationResponse, IntegrationsListResponse, InitiateAuthRequest, InitiateAuthResponse, DisconnectResponse, IntegrationMember, IntegrationMembersResponse, IntegrationScope, IntegrationScopesResponse } from "./api/types.gen";
export type { ApiIntegrationsListIntegrationsData as ListIntegrationsData } from "./api/types.gen";
export type { ApiIntegrationsProviderAuthInitiateAuthData as InitiateIntegrationAuthData } from "./api/types.gen";
export type { ApiIntegrationsProviderDisconnectDisconnectData as DisconnectIntegrationData } from "./api/types.gen";
export type { ApiIntegrationsProviderRefreshRefreshData as RefreshIntegrationData } from "./api/types.gen";
