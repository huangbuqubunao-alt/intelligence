import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });
it.each(["en", "zh-CN"])("refreshes Evidence and Deep Analysis after polled caption success without a reload in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/polled-caption";
  let detailReads = 0;
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    let body: object = {};
    if (path.endsWith("/videos/polled-caption")) {
      const succeeded = ++detailReads > 1;
      body = { video: { video_id: "polled-caption", provider: "YOUTUBE", title: "Polled captions", processing_status: succeeded ? "ORGANIZED" : "FAILED", tracked_content_retry: { retry_allowed: false, expected_job_id: null, request: { request_id: "tracked-content-retry:v1:current", video_id: "polled-caption", source_id: "source", expected_job_id: "old-job", target_job_id: "retry-job", state: succeeded ? "SUCCEEDED" : "FINALIZING", revision: succeeded ? 4 : 3, error_code: null, can_resume_local: false, can_close_local: false, can_cancel: false } } }, transcript: { status: succeeded ? "AVAILABLE" : "UNAVAILABLE", text: succeeded ? "Verified captured source text" : undefined }, note: { v2: { status: succeeded ? "AVAILABLE" : "UNAVAILABLE", summary: succeeded ? "A newly verified Summary" : undefined } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] };
    } else if (path.endsWith("/videos/another-content")) body = { video: { video_id: "another-content", provider: "YOUTUBE", title: "Another Content", processing_status: "FAILED", tracked_content_retry: { request: null, retry_allowed: false, expected_job_id: null } }, transcript: { status: "UNAVAILABLE" }, note: { v2: { status: "UNAVAILABLE" } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] };
    else if (path.endsWith("/videos/another-content/evidence")) body = { evidence: [] };
    else if (path.endsWith("/evidence")) body = { evidence: detailReads > 1 ? [{ evidence_id: "verified-after-retry", video_id: "polled-caption", source: "TRANSCRIPT", artifact_id: "canonical-after-retry", lineage_kind: "ORIGINAL_TRANSCRIPT", role: "PRIMARY_ORIGINAL", original_excerpt: "New canonical Evidence from completed retry", start_ms: 1000, end_ms: 3000, source_language: "en", translation_target_language: "en", translated_excerpt: null, translation_status: "UNAVAILABLE" }] : [] };
    else if (path.endsWith("/deep-analysis")) body = { deep_analysis: { status: { availability: "NOT_QUALIFIED", can_run: false }, result: null } };
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  const evidence = within((await screen.findByRole("heading", { name: language === "en" ? "Evidence · source transcript" : "证据 · 来源字幕" })).closest("section")!);
  await waitFor(() => expect(fetch.mock.calls.filter(([path]) => path.endsWith("/evidence"))).toHaveLength(1));
  expect(evidence.queryByText("New canonical Evidence from completed retry")).toBeNull();
  await screen.findByText("A newly verified Summary", {}, { timeout: 4000 });
  await evidence.findByText("New canonical Evidence from completed retry");
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/deep-analysis"))).toHaveLength(2);
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/evidence"))).toHaveLength(2);
  await act(async () => {
    location.hash = "#Content/another-content";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  await screen.findByRole("heading", { name: "Another Content" });
  await waitFor(() => expect(fetch.mock.calls.some(([path]) => path.endsWith("/videos/another-content/evidence"))).toBe(true));
  expect(screen.queryByText("New canonical Evidence from completed retry")).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});
