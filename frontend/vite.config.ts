import { defineConfig } from "vite";
import { apiProxyTarget } from "./src/api/proxy";

export default defineConfig({
  server: {
    host: "127.0.0.1",
    proxy: { "/api": apiProxyTarget(process.env.YIA_API_BASE) }
  },
  test: { environment: "jsdom", globals: true }
});
