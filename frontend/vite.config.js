import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => ({
  server: {
    proxy: {
      "/api": loadEnv(mode, process.cwd(), "").VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8001",
    },
  },
  test: { environment: "node" },
}));
