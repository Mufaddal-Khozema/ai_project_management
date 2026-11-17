"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import { StorageKeys } from "@/constants";

export type Theme = "light" | "dark";
export type ThemePreference = Theme | "system";

const DARK_QUERY = "(prefers-color-scheme: dark)";
const THEME_CHANGE_EVENT = "coordina-theme-change";

export function getStoredThemePreference(): ThemePreference {
  if (typeof window === "undefined") return "system";

  try {
    const stored = localStorage.getItem(StorageKeys.THEME);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    // ignore storage failures
  }

  return "system";
}

export function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "light";

  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

export function resolveTheme(preference: ThemePreference): Theme {
  return preference === "system" ? getSystemTheme() : preference;
}

function applyTheme(preference: ThemePreference, resolved: Theme) {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  root.dataset.theme = resolved;
  root.dataset.themePreference = preference;
  root.style.colorScheme = resolved;
}

export function applyThemePreference(preference: ThemePreference) {
  applyTheme(preference, resolveTheme(preference));
}

function subscribePreference(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(THEME_CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(THEME_CHANGE_EVENT, onStoreChange);
  };
}

function subscribeSystem(onStoreChange: () => void) {
  const media = window.matchMedia(DARK_QUERY);
  media.addEventListener("change", onStoreChange);
  return () => media.removeEventListener("change", onStoreChange);
}

const getServerPreference = (): ThemePreference => "system";
const getServerSystemTheme = (): Theme => "light";

type ThemeContextValue = {
  theme: Theme;
  preference: ThemePreference;
  setThemePreference: (preference: ThemePreference) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const preference = useSyncExternalStore(
    subscribePreference,
    getStoredThemePreference,
    getServerPreference,
  );
  const systemTheme = useSyncExternalStore(
    subscribeSystem,
    getSystemTheme,
    getServerSystemTheme,
  );

  const theme: Theme = preference === "system" ? systemTheme : preference;

  useEffect(() => {
    applyThemePreference(getStoredThemePreference());
  }, [preference, theme]);

  const setThemePreference = useCallback((next: ThemePreference) => {
    try {
      localStorage.setItem(StorageKeys.THEME, next);
    } catch {
      // ignore storage failures
    }
    window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
  }, []);

  const toggleTheme = useCallback(() => {
    setThemePreference(theme === "dark" ? "light" : "dark");
  }, [setThemePreference, theme]);

  const value = useMemo(
    () => ({ theme, preference, setThemePreference, toggleTheme }),
    [preference, setThemePreference, theme, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}

export const useLandingTheme = useTheme;
