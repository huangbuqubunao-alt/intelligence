import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import { buildStarterSampleNote, STARTER_SAMPLE_FILENAME } from "./starterSample";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("buildStarterSampleNote creates valid bilingual UTF-8 Markdown files", async () => {
  const zhFile = buildStarterSampleNote("zh-CN");
  expect(zhFile.name).toBe(STARTER_SAMPLE_FILENAME);
  expect(zhFile.type).toContain("text/markdown");
  expect(zhFile.size).toBeGreaterThan(200);

  const enFile = buildStarterSampleNote("en");
  expect(enFile.name).toBe(STARTER_SAMPLE_FILENAME);
  expect(enFile.size).toBeGreaterThan(200);
});

test("Empty Home imports the built-in starter sample note via /local/imports and opens the reader", async () => {
  location.hash = "#Home";
  let imported = false;
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.startsWith("/api/v1/local/imports?") && init?.method === "POST") {
      imported = true;
      expect(url).toContain(encodeURIComponent(STARTER_SAMPLE_FILENAME));
      return {
        ok: true,
        json: async () => ({
          import: {
            content_id: "starter-note-001",
            filename: STARTER_SAMPLE_FILENAME,
            status: "READY",
            duplicate: false,
          },
        }),
      };
    }
    if (url.startsWith("/api/v1/dashboard")) {
      return {
        ok: true,
        json: async () => ({
          intelligence: [],
          pinned_topics: [],
          weekly_v1: [],
          needs_attention: [],
          operations: { source_count: imported ? 1 : 0 },
          demo_mode: false,
        }),
      };
    }
    if (url.startsWith("/api/v1/knowledge-delta")) {
      return {
        ok: true,
        json: async () => ({
          window_start: "2026-11-20T00:00:00Z",
          window_end: "2026-11-27T00:00:00Z",
          timezone: "Asia/Shanghai",
          changes: [],
        }),
      };
    }
    if (url === "/api/v1/videos" || url.startsWith("/api/v1/videos?")) {
      return {
        ok: true,
        json: async () => ({
          videos: imported
            ? [
                {
                  video_id: "starter-note-001",
                  title: STARTER_SAMPLE_FILENAME,
                  provider: "LOCAL",
                  media_kind: "TEXT",
                  format: "md",
                  processing_status: "READY",
                  channel_name: "Local library",
                },
              ]
            : [],
        }),
      };
    }
    if (url === "/api/v1/videos/starter-note-001") {
      return {
        ok: true,
        json: async () => ({
          video: {
            video_id: "starter-note-001",
            title: STARTER_SAMPLE_FILENAME,
            provider: "LOCAL",
            media_kind: "TEXT",
            format: "md",
            processing_status: "READY",
            channel_name: "Local library",
          },
          transcript: { status: "AVAILABLE", text: "Local-First starter note body." },
          note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
          intelligence_result: { status: "NOT_PROCESSED" },
          history: [],
        }),
      };
    }
    if (url.endsWith("/evidence")) {
      return { ok: true, json: async () => ({ evidence: [] }) };
    }
    if (url.endsWith("/deep-analysis")) {
      return {
        ok: true,
        json: async () => ({
          deep_analysis: {
            status: {
              availability: "NOT_QUALIFIED",
              reason_code: "NO_QUALIFIED_MODEL",
              qualified: false,
              production_eligible: false,
              consent_required: false,
              routes: [],
            },
            result: null,
          },
        }),
      };
    }
    return { ok: true, json: async () => ({}) };
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  const sampleBtn = await screen.findByRole("button", { name: "一键导入示例笔记体验" });
  fireEvent.click(sampleBtn);

  await waitFor(() => {
    expect(location.hash).toBe("#Content/starter-note-001");
  });
  expect(await screen.findByRole("heading", { name: STARTER_SAMPLE_FILENAME })).toBeTruthy();
  const importCalls = fetchMock.mock.calls.filter(([u]) => String(u).includes("/api/v1/local/imports"));
  expect(importCalls).toHaveLength(1);
});

test("Empty Content handles starter sample import errors cleanly and Empty Following keeps dual Add Source hierarchy", async () => {
  location.hash = "#Content";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.startsWith("/api/v1/local/imports") && init?.method === "POST") {
        return {
          ok: false,
          json: async () => ({ error: { code: "LOCAL_DISK_SPACE_INSUFFICIENT", message: "Full" } }),
        };
      }
      if (url === "/api/v1/videos") {
        return { ok: true, json: async () => ({ videos: [] }) };
      }
      if (url === "/api/v1/capabilities/creator-following") {
        return { ok: true, json: async () => ({ available: false }) };
      }
      if (url === "/api/v1/sources/check-stale") {
        return { ok: true, json: async () => ({ checks: [] }) };
      }
      if (url === "/api/v1/sources") {
        return { ok: true, json: async () => ({ sources: [] }) };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  const sampleBtn = await screen.findByRole("button", { name: "一键导入示例笔记体验" });
  fireEvent.click(sampleBtn);

  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain("示例笔记未能导入");

  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  const addButtons = await screen.findAllByRole("button", { name: "添加关注" });
  expect(addButtons).toHaveLength(2);
  expect(addButtons[0].className).toContain("button-secondary");
  expect(addButtons[1].className).toContain("button-primary");
});
