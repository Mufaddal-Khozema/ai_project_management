"use client";

import { useTheme as useNextTheme, ThemeProvider as NextThemesProvider } from "next-themes";
import { useCallback, useMemo } from "react";
import { StorageKeys } from "@/constants";

export type Theme = "light" | "dark";
export type ThemePreference = Theme | "system";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme="system"
      enableSystem
      storageKey={StorageKeys.THEME}
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}

export function useTheme() {
  const { theme, resolvedTheme, setTheme } = useNextTheme();

  const currentTheme: Theme = (resolvedTheme === "dark" ? "dark" : "light");
  const preference: ThemePreference = (theme as ThemePreference) || "system";

  const setThemePreference = useCallback(
    (next: ThemePreference) => {
      setTheme(next);
    },
    [setTheme],
  );

  const toggleTheme = useCallback(() => {
    setTheme(currentTheme === "dark" ? "light" : "dark");
  }, [currentTheme, setTheme]);

  return useMemo(
    () => ({
      theme: currentTheme,
      preference,
      setThemePreference,
      toggleTheme,
    }),
    [currentTheme, preference, setThemePreference, toggleTheme],
  );
}

export const useLandingTheme = useTheme;
