import { defineConfig } from "vite";
import { apiProxyTarget } from "./src/api/proxy";

export default defineConfig({
  server: {
    host: "127.0.0.1",
    proxy: { "/api": apiProxyTarget(process.env.YIA_API_BASE) }
  },
  preview: {
    host: "127.0.0.1",
    proxy: { "/api": apiProxyTarget(process.env.YIA_API_BASE) }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react-dom") || id.includes("node_modules/react/")) {
            return "vendor-react";
          }
          return undefined;
        }
      }
    }
  },
  test: { environment: "jsdom", globals: true }
});
