import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": process.cwd(),
    },
  },
  test: {
    environment: "happy-dom",
    globals: true,
    include: ["app/**/*.test.{ts,tsx}", "components/**/*.test.{ts,tsx}", "lib/**/*.test.{ts,tsx}"],
  },
});