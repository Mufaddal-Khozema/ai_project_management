"use client";

import { useMutation } from "@tanstack/react-query";
import {
  apiAuthEmailSendOtpSendOtpHandlerMutation,
  apiAuthEmailVerifyOtpVerifyOtpHandlerMutation,
  apiPaymentsSetupIntentSetupIntentHandlerMutation,
} from "./api/@tanstack/react-query.gen";
import { client } from "./api/client.gen";
import { StorageKeys } from "@/constants";

client.setConfig({
  auth: () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(StorageKeys.TOKEN) ?? undefined;
    }
    return undefined;
  },
});

export { client as sdk };
export { apiHealthHealthCheck as healthCheck } from "./api/sdk.gen";
export { apiAuthEmailSendOtpSendOtpHandler as sendOtp } from "./api/sdk.gen";
export { apiAuthEmailVerifyOtpVerifyOtpHandler as verifyOtp } from "./api/sdk.gen";
export { apiPaymentsSetupIntentSetupIntentHandler as setupIntent } from "./api/sdk.gen";

export { apiAuthEmailSendOtpSendOtpHandlerMutation as sendOtpMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiAuthEmailVerifyOtpVerifyOtpHandlerMutation as verifyOtpMutationOptions } from "./api/@tanstack/react-query.gen";
export { apiPaymentsSetupIntentSetupIntentHandlerMutation as setupIntentMutationOptions } from "./api/@tanstack/react-query.gen";

export function useSendOtpMutation() {
  return useMutation(apiAuthEmailSendOtpSendOtpHandlerMutation());
}

export function useVerifyOtpMutation() {
  return useMutation(apiAuthEmailVerifyOtpVerifyOtpHandlerMutation());
}

export type { SendOtpRequest, SendOtpResponse, VerifyOtpRequest, SetupIntentRequest, SetupIntentResponse } from "./api/types.gen";
export type { ApiAuthEmailSendOtpSendOtpHandlerData as SendOtpData } from "./api/types.gen";
export type { ApiAuthEmailVerifyOtpVerifyOtpHandlerData as VerifyOtpData } from "./api/types.gen";
export type { ApiPaymentsSetupIntentSetupIntentHandlerData as SetupIntentData } from "./api/types.gen";
export type { ApiAuthEmailSendOtpSendOtpHandlerResponse as SendOtpResponseType } from "./api/types.gen";
export type { ApiAuthEmailVerifyOtpVerifyOtpHandlerResponse as VerifyOtpResponseType } from "./api/types.gen";
export type { ApiPaymentsSetupIntentSetupIntentHandlerResponse as SetupIntentResponseType } from "./api/types.gen";
