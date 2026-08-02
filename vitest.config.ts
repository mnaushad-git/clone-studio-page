// Standalone from vite.config.ts on purpose: that file is managed by
// @lovable.dev/vite-tanstack-config and its own comment warns against adding plugins
// manually. Vitest doesn't need any of that (TanStack Start SSR, nitro, sandbox
// detection) — a minimal config with just the `@` alias and jsdom is enough for unit
// tests of lib/ and components/.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
