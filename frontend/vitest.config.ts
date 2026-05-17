import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss(), react()],
  test: {
    globals: true,
    environment: "jsdom",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["tests/e2e/**", "node_modules/**", "dist/**"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
