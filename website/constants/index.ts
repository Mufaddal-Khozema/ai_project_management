"use client"
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL;

export const StorageKeys = {
  TOKEN: "token",
  SELECTED_PLAN: "selectedPlan",
} as const;
