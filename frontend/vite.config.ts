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
          if (
            id.includes("node_modules/react-dom") ||
            id.includes("node_modules/react/") ||
            id.includes("node_modules/scheduler")
          ) {
            return "vendor-react";
          }
          if (
            id.includes("/src/api/") ||
            id.includes("/src/workspace/uiLanguage") ||
            id.includes("/src/workspace/motion") ||
            (id.includes("/src/workspace/ui/") && !id.includes("CommandPalette"))
          ) {
            return "workspace-core";
          }
          if (
            id.includes("/src/workspace/WorkspaceAiWidgets") ||
            id.includes("/src/workspace/Research") ||
            id.includes("/src/workspace/KnowledgeDelta")
          ) {
            return "workspace-ai-hub";
          }
          if (
            /\/src\/workspace\/(CreatorFollowing|BilibiliImport|LocalImport|NativeLocalImport|LocalTranscription|TrackedContentRetry|ModelSettings|BigModelSettings|CloudSpendingSettings|LocalIntelligenceSetup|TranscriptionSetup|AddEntry|Onboarding|captionClean)(\.tsx?|$)/.test(
              id,
            )
          ) {
            return "workspace-sources-models";
          }
          return undefined;
        }
      }
    }
  },
  test: { environment: "jsdom", globals: true }
});
