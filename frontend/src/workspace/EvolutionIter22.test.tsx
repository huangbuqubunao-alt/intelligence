import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 22 — Actionable Following attention filter & inline source recovery guidance", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  it("filters unhealthy sources via digest pill, keeps recovery hint outside button, and navigates to Settings without auto-retries", async () => {
    location.hash = "#Following";
    const user = userEvent.setup();
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === "/api/v1/sources/check-stale") {
        return jsonResponse({ checks: [] });
      }
      if (path === "/api/v1/sources") {
        return jsonResponse({
          sources: [
            {
              source_id: "srcHealthy1",
              source_type: "CHANNEL",
              provider: "YOUTUBE",
              display_name: "Healthy Engineering Channel",
              canonical_url: "https://www.youtube.com/@healthy",
              enabled: true,
              insight_count: 3,
              tracking: {
                health: "UP_TO_DATE",
                coverage: "RECENT",
                update_count: 1,
                pending_count: 0,
                processing_count: 0,
                unavailable_count: 0,
                checking: false,
              },
            },
            {
              source_id: "srcBroken1",
              source_type: "CHANNEL",
              provider: "YOUTUBE",
              display_name: "Rate Limited Channel",
              canonical_url: "https://www.youtube.com/@broken",
              enabled: true,
              insight_count: 0,
              last_error: { code: "PROVIDER_AUTH_ERROR", message: "Auth expired" },
              tracking: {
                health: "PROVIDER_ERROR",
                coverage: "PARTIAL",
                update_count: 0,
                pending_count: 0,
                processing_count: 0,
                unavailable_count: 0,
                checking: false,
              },
            },
          ],
          ai_signal_by_source: {},
        });
      }
      if (path.startsWith("/api/v1/capability")) {
        return jsonResponse({ available: false });
      }
      if (path.startsWith("/api/v1/settings")) {
        return new Promise<Response>(() => {});
      }
      if (path.startsWith("/api/v1/workspace-ai/")) {
        return jsonResponse({ ready: false, sessions: [] });
      }
      return jsonResponse({ init_method: init?.method ?? "GET" });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Healthy Engineering Channel")).toBeTruthy();
    expect(screen.getByText("Rate Limited Channel")).toBeTruthy();

    const attentionBtn = await screen.findByRole("button", { name: "需处理异常信源 (1)" });
    await user.click(attentionBtn);

    expect(attentionBtn.getAttribute("aria-pressed")).toBe("true");
    expect(screen.queryByText("Healthy Engineering Channel")).toBeNull();
    expect(screen.getByText("Rate Limited Channel")).toBeTruthy();

    const recoveryNote = document.querySelector(".source-recovery-hint");
    expect(recoveryNote).not.toBeNull();
    expect(recoveryNote?.closest("button.source-select")).toBeNull();

    const retryCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("/check"),
    ).length;
    expect(retryCalls).toBe(1); // Only initial check-stale visibility check, zero automatic per-source /sources/:id/check retries

    await user.click(screen.getByRole("button", { name: "前往设置" }));
    await waitFor(() => {
      expect(location.hash).toBe("#Settings");
    });
  });
});
