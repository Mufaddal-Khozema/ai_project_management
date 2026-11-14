"use client";

import { useState } from "react";

export type Theme = "light" | "dark";

export function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";

  try {
    const stored = localStorage.getItem("ct");
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // ignore storage failures
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function useLandingTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  const toggleTheme = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem("ct", next);
    } catch {
      // ignore storage failures
    }
  };

  return { theme, toggleTheme };
}
