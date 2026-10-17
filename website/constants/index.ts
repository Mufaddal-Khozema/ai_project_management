export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const StorageKeys = {
  TOKEN: "token",
  SELECTED_PLAN: "selectedPlan",
} as const;
