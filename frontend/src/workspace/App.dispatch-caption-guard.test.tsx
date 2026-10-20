import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });
it("keeps an unknown cloud dispatch blocked when a verified caption result arrives", async () => {
  localStorage.setItem("yia.ui-language", "en");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/reviewer-content";
  let finished = false, executions = 0, preflights = 0, deepReads = 0;
  const response = (body: object) => ({ ok: true, json: async () => body });
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/reviewer-content")) return response({ video: { video_id: "reviewer-content", provider: "YOUTUBE", title: "Reviewer content", processing_status: finished ? "ORGANIZED" : "FAILED", tracked_content_retry: { retry_allowed: false, expected_job_id: null, request: { request_id: "tracked:reviewer", video_id: "reviewer-content", source_id: "source", expected_job_id: "old", target_job_id: "new", state: finished ? "SUCCEEDED" : "FINALIZING", revision: finished ? 4 : 3, error_code: null, can_resume_local: false, can_close_local: false, can_cancel: false } } }, transcript: { status: "UNAVAILABLE" }, note: { v2: { status: finished ? "AVAILABLE" : "UNAVAILABLE", summary: finished ? "Reviewer fresh summary" : undefined } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] });
    if (path.endsWith("/deep-analysis/preflight")) {
      preflights++;
      return response({ preflight: { execution_id: `reviewer-execution-${preflights}`, route_id: "cloud", provider_id: "mock-cloud", model_id: "mock-qualified", credential_configured: true, qualification_status: "QUALIFIED", data_egress_mode: "SELECTED_EVIDENCE_ONLY", cost: { state: "UNKNOWN", hard_monetary_cap: false, input_characters: 123 } } });
    }
    if (path.endsWith("/deep-analysis") && init?.method === "POST") {
      executions++;
      throw new TypeError("Reviewer simulated response loss after dispatch");
    }
    if (path.endsWith("/deep-analysis")) {
      deepReads++;
      return response({ deep_analysis: { status: { availability: "NOT_REQUESTED", qualified: true, production_eligible: true, consent_required: true, route_id: "cloud" }, result: null } });
    }
    if (path.endsWith("/evidence")) return response({ evidence: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  const run = await screen.findByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(run);
  await screen.findByRole("region", { name: "Cloud Deep Analysis preflight" });
  fireEvent.click(screen.getByRole("checkbox", { name: "I acknowledge the unknown cost for this execution." }));
  fireEvent.click(screen.getByRole("button", { name: "Authorize this cloud run" }));
  await waitFor(() => expect(executions).toBe(1));
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(true));
  finished = true;
  fireEvent.click(screen.getByRole("button", { name: "Read caption retry status" }));
  await screen.findByText("Reviewer fresh summary");
  await waitFor(() => expect(deepReads).toBe(2));
  console.log(JSON.stringify({ executions, preflights, deepReads, runDisabledAfterCaptionSuccess: (run as HTMLButtonElement).disabled }));
  expect((run as HTMLButtonElement).disabled, "a caption refresh must not clear an ambiguous cloud dispatch").toBe(true);
});

it("invalidates an open preflight on caption refresh without a second execution", async () => {
  localStorage.setItem("yia.ui-language", "en");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/reviewer-content";
  let finished = false, executions = 0, preflights = 0, deepReads = 0;
  const response = (body: object) => ({ ok: true, json: async () => body });
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/reviewer-content")) return response({ video: { video_id: "reviewer-content", provider: "YOUTUBE", title: "Reviewer content", processing_status: finished ? "ORGANIZED" : "FAILED", tracked_content_retry: { retry_allowed: false, expected_job_id: null, request: { request_id: "tracked:reviewer", video_id: "reviewer-content", source_id: "source", expected_job_id: "old", target_job_id: "new", state: finished ? "SUCCEEDED" : "FINALIZING", revision: finished ? 4 : 3, error_code: null, can_resume_local: false, can_close_local: false, can_cancel: false } } }, transcript: { status: "UNAVAILABLE" }, note: { v2: { status: finished ? "AVAILABLE" : "UNAVAILABLE", summary: finished ? "Reviewer fresh summary" : undefined } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] });
    if (path.endsWith("/deep-analysis/preflight")) {
      preflights++;
      return response({ preflight: { execution_id: `reviewer-execution-${preflights}`, route_id: "cloud", provider_id: "mock-cloud", model_id: "mock-qualified", credential_configured: true, qualification_status: "QUALIFIED", data_egress_mode: "SELECTED_EVIDENCE_ONLY", cost: { state: "UNKNOWN", hard_monetary_cap: false, input_characters: 123 } } });
    }
    if (path.endsWith("/deep-analysis") && init?.method === "POST") {
      executions++;
      throw new TypeError("Reviewer simulated response loss after dispatch");
    }
    if (path.endsWith("/deep-analysis")) {
      deepReads++;
      return response({ deep_analysis: { status: { availability: "NOT_REQUESTED", qualified: true, production_eligible: true, consent_required: true, route_id: "cloud" }, result: null } });
    }
    if (path.endsWith("/evidence")) return response({ evidence: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  const run = await screen.findByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(run);
  const preflightRegion = await screen.findByRole("region", { name: "Cloud Deep Analysis preflight" });
  expect((screen.getByRole("button", { name: "Run Deep Analysis" }) as HTMLButtonElement).disabled).toBe(true);
  expect(preflightRegion.textContent).toContain("123");
  fireEvent.click(screen.getByRole("checkbox", { name: "I acknowledge the unknown cost for this execution." }));
  expect((screen.getByRole("button", { name: "Authorize this cloud run" }) as HTMLButtonElement).disabled).toBe(false);
  finished = true;
  fireEvent.click(screen.getByRole("button", { name: "Read caption retry status" }));
  await screen.findByText("Reviewer fresh summary");
  expect(screen.queryByRole("region", { name: "Cloud Deep Analysis preflight" })).toBeNull();
  const reRun = screen.getByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((reRun as HTMLButtonElement).disabled).toBe(false));
  expect(preflights).toBe(1);
  fireEvent.click(reRun);
  await screen.findByRole("region", { name: "Cloud Deep Analysis preflight" });
  expect((screen.getByRole("checkbox", { name: "I acknowledge the unknown cost for this execution." }) as HTMLInputElement).checked).toBe(false);
  fireEvent.click(screen.getByRole("checkbox", { name: "I acknowledge the unknown cost for this execution." }));
  fireEvent.click(screen.getByRole("button", { name: "Authorize this cloud run" }));
  await waitFor(() => expect(executions).toBe(1));
  expect(screen.queryByRole("region", { name: "Cloud Deep Analysis preflight" })).toBeNull();
  expect(preflights).toBe(2);
});

it("does not loop caption-result reads when a later read repeats the same success token", async () => {
  localStorage.setItem("yia.ui-language", "en");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/reviewer-content";
  let finished = false, executions = 0, deepReads = 0;
  const response = (body: object) => ({ ok: true, json: async () => body });
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/reviewer-content")) return response({ video: { video_id: "reviewer-content", provider: "YOUTUBE", title: "Reviewer content", processing_status: finished ? "ORGANIZED" : "FAILED", tracked_content_retry: { retry_allowed: false, expected_job_id: null, request: { request_id: "tracked:reviewer", video_id: "reviewer-content", source_id: "source", expected_job_id: "old", target_job_id: "new", state: finished ? "SUCCEEDED" : "FINALIZING", revision: finished ? 4 : 3, error_code: null, can_resume_local: false, can_close_local: false, can_cancel: false } } }, transcript: { status: "UNAVAILABLE" }, note: { v2: { status: finished ? "AVAILABLE" : "UNAVAILABLE", summary: finished ? "Reviewer fresh summary" : undefined } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] });
    if (path.endsWith("/deep-analysis/preflight")) return response({ preflight: { execution_id: "reviewer-execution-1", route_id: "cloud", provider_id: "mock-cloud", model_id: "mock-qualified", credential_configured: true, qualification_status: "QUALIFIED", data_egress_mode: "SELECTED_EVIDENCE_ONLY", cost: { state: "UNKNOWN", hard_monetary_cap: false, input_characters: 123 } } });
    if (path.endsWith("/deep-analysis") && init?.method === "POST") {
      executions++;
      throw new TypeError("Reviewer simulated response loss after dispatch");
    }
    if (path.endsWith("/deep-analysis")) {
      deepReads++;
      return response({ deep_analysis: { status: { availability: "NOT_REQUESTED", qualified: true, production_eligible: true, consent_required: true, route_id: "cloud" }, result: null } });
    }
    if (path.endsWith("/evidence")) return response({ evidence: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  const run = await screen.findByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(run);
  await screen.findByRole("region", { name: "Cloud Deep Analysis preflight" });
  fireEvent.click(screen.getByRole("checkbox", { name: "I acknowledge the unknown cost for this execution." }));
  fireEvent.click(screen.getByRole("button", { name: "Authorize this cloud run" }));
  await waitFor(() => expect(executions).toBe(1));
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(true));
  finished = true;
  fireEvent.click(screen.getByRole("button", { name: "Read caption retry status" }));
  await screen.findByText("Reviewer fresh summary");
  await waitFor(() => expect(deepReads).toBe(2));
  const evidenceReads = () => fetch.mock.calls.filter(([path]) => path.endsWith("/evidence")).length;
  expect(evidenceReads()).toBe(3);
  fireEvent.click(screen.getByRole("button", { name: "Read caption retry status" }));
  await waitFor(() => expect(evidenceReads()).toBe(4));
  await waitFor(() => expect(deepReads).toBe(2));
  expect((run as HTMLButtonElement).disabled).toBe(true);
  expect(executions).toBe(1);
});

it("isolates the blocked dispatch across Content navigation per existing video-id semantics", async () => {
  localStorage.setItem("yia.ui-language", "en");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/reviewer-content";
  let finished = false, executions = 0;
  const response = (body: object) => ({ ok: true, json: async () => body });
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/reviewer-content")) return response({ video: { video_id: "reviewer-content", provider: "YOUTUBE", title: "Reviewer content", processing_status: finished ? "ORGANIZED" : "FAILED", tracked_content_retry: { retry_allowed: false, expected_job_id: null, request: { request_id: "tracked:reviewer", video_id: "reviewer-content", source_id: "source", expected_job_id: "old", target_job_id: "new", state: finished ? "SUCCEEDED" : "FINALIZING", revision: finished ? 4 : 3, error_code: null, can_resume_local: false, can_close_local: false, can_cancel: false } } }, transcript: { status: "UNAVAILABLE" }, note: { v2: { status: finished ? "AVAILABLE" : "UNAVAILABLE", summary: finished ? "Reviewer fresh summary" : undefined } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] });
    if (path.endsWith("/videos/another-content")) return response({ video: { video_id: "another-content", provider: "YOUTUBE", title: "Another Content", processing_status: "ORGANIZED", tracked_content_retry: { retry_allowed: false, expected_job_id: null, request: null } }, transcript: { status: "UNAVAILABLE" }, note: { v2: { status: "AVAILABLE", summary: "Another summary" } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] });
    if (path.endsWith("/videos/another-content/evidence")) return response({ evidence: [] });
    if (path.endsWith("/deep-analysis/preflight")) return response({ preflight: { execution_id: "reviewer-execution-1", route_id: "cloud", provider_id: "mock-cloud", model_id: "mock-qualified", credential_configured: true, qualification_status: "QUALIFIED", data_egress_mode: "SELECTED_EVIDENCE_ONLY", cost: { state: "UNKNOWN", hard_monetary_cap: false, input_characters: 123 } } });
    if (path.endsWith("/deep-analysis") && init?.method === "POST") {
      executions++;
      throw new TypeError("Reviewer simulated response loss after dispatch");
    }
    if (path.endsWith("/deep-analysis")) return response({ deep_analysis: { status: { availability: "NOT_REQUESTED", qualified: true, production_eligible: true, consent_required: true, route_id: "cloud" }, result: null } });
    if (path.endsWith("/evidence")) return response({ evidence: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  const run = await screen.findByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(run);
  await screen.findByRole("region", { name: "Cloud Deep Analysis preflight" });
  fireEvent.click(screen.getByRole("checkbox", { name: "I acknowledge the unknown cost for this execution." }));
  fireEvent.click(screen.getByRole("button", { name: "Authorize this cloud run" }));
  await waitFor(() => expect(executions).toBe(1));
  await waitFor(() => expect((run as HTMLButtonElement).disabled).toBe(true));
  await act(async () => {
    location.hash = "#Content/another-content";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  const otherRun = await screen.findByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((otherRun as HTMLButtonElement).disabled).toBe(false));
  await act(async () => {
    location.hash = "#Content/reviewer-content";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  const returnedRun = await screen.findByRole("button", { name: "Run Deep Analysis" });
  await waitFor(() => expect((returnedRun as HTMLButtonElement).disabled).toBe(false));
  expect(executions).toBe(1);
});
