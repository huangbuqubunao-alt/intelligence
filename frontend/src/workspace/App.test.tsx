import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import { apiProxyTarget } from "../api/proxy";

const intelligence = { status: "AVAILABLE", trusted: true, intelligence_id: "intel-1", claim_kind: "RUMOR", state: "DISPUTED", card: { core_conclusion: "A rumor remains unresolved.", user_relevant_information: ["Watch for confirmation."], important_new_information: [], source_id: "source-1", video_id: "video-1", original_video_url: "https://youtube.test/video", evidence_links: [{ evidence_id: "evidence-1", start_ms: 1000, end_ms: 2000 }] } };
const topic = { topic_id: "topic-1", name: "Topic", pinned: false, lifecycle: "ACTIVE", current_state: "DEGRADED", independence: "UNKNOWN", contributions: [], timeline: [{ event_id: "event-1", event_kind: "NEW_INFORMATION", state: "UNRESOLVED", created_at: "2026-09-01T00:00:00Z" }], relations: [] };
const response = (value: object) => Promise.resolve({ ok: true, json: async () => value });

beforeEach(() => {
  location.hash = "";
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ intelligence: [intelligence], pinned_topics: [], weekly_v1: [], needs_attention: [{ run_id: "attention-1", state: "NEEDS_ATTENTION", attention_reason: "MODEL_UNAVAILABLE", trigger: "MANUAL_CHECK_NOW", updated_at: "2026-09-01T00:00:00Z" }], operations: { source_count: 1 } });
    if (input.endsWith("/intelligence")) return response({ intelligence: [intelligence] });
    if (input.endsWith("/intelligence/intel-1")) return response({ intelligence });
    if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
    if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [] });
    if (input.endsWith("/topics/topic-1")) return response({ topic });
    if (input.endsWith("/topics")) return response({ topics: [topic] });
    if (input.endsWith("/sources/source-1") && init?.method === "PATCH") return response({ source: { source_id: "source-1", enabled: false } });
    if (input.endsWith("/sources/source-1/check")) return response({ status: "BLOCKED", message: "Check now is blocked by the runtime side-effect guard." });
    if (input.endsWith("/sources/source-1")) return response({ source: { source_id: "source-1", display_name: "Source", canonical_url: "https://youtube.test/source", enabled: true, processing_policy: "STANDARD_INTELLIGENCE", last_error: null }, policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: ["AI"], ignore_rules: ["rough"], distillation_style: "BALANCED" }, schedules: [{ schedule_id: "schedule-1", frequency: "DAILY", local_time: "08:30", enabled: true }], recent_videos: [{ video_id: "skip-1", title: "Rough draft", processing_status: "METADATA_READY", filter: { outcome: "NOT_RELEVANT", reason: "IGNORE_RULE_MATCH" } }], source_runs: [] });
    if (input.endsWith("/sources")) return response({ sources: [{ source_id: "source-1", display_name: "Source", canonical_url: "https://youtube.test/source", enabled: true, processing_policy: "STANDARD_INTELLIGENCE", last_error: null }] });
    if (input.endsWith("/settings/preferences")) return response({ active: [], history: [
      { preference_id: "explicit", horizon: "LONG_TERM", provenance: "EXPLICIT", statement: "Prefer evidence-led product analysis.", expires_at: null },
      { preference_id: "derived", horizon: "RECENT", provenance: "DERIVED", statement: "Recent interest in evaluation practice.", expires_at: null },
      { preference_id: "temporary", horizon: "TEMPORARY_FOCUS", provenance: "TEMPORARY", statement: "Focus this week on decision logs.", expires_at: "2026-09-02T00:00:00Z" },
    ] });
    if (input.endsWith("/settings/source-policy")) return response({ policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" } });
    if (input.endsWith("/settings/resource-usage")) return response({ usage: [{ execution_id: "exec-1", reason: "PERSONALIZED_INTELLIGENCE", actual_provider: "offline-test", actual_model: "deterministic-v1", invocation_count: 1, input_tokens: null, output_tokens: null, cost_microunits: null, duration_ms: 0, status: "SUCCEEDED", budget_state: "ADMITTED", outcome: "ADMITTED" }] });
    if (input.endsWith("/settings")) return response({ providers: [{ provider: "Kimi", production_eligible: false, qualification_status: "UNQUALIFIED", reason: "Not qualified" }] });
    if (input.endsWith("/saved-intelligence/save") || input.endsWith("/saved-intelligence/unsave")) return response({ saved: true });
    return response({});
  }));
});
afterEach(() => vi.unstubAllGlobals());

test("PO demo can direct the development proxy to its owned loopback API", () => {
  expect(apiProxyTarget("http://127.0.0.1:8766")).toBe("http://127.0.0.1:8766");
});

test("frozen product IA exposes exactly its six first-level destinations", async () => {
  render(<App />);
  await screen.findByText("Important Intelligence");
  expect(screen.getAllByRole("button", { name: /^(Dashboard|Intelligence|Topics|Sources|Investigations|Settings)$/ })).toHaveLength(6);
  for (const legacy of ["Videos", "Activity", "Saved", "Weekly", "Daily", "Ask", "Runs", "Jobs"]) expect(screen.queryByRole("button", { name: new RegExp(`^${legacy}$`) })).toBeNull();
  expect(screen.getByText("MODEL UNAVAILABLE")).toBeTruthy();
});

test("verified Intelligence preserves rumor, dispute, and evidence without watch-score language", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  expect(await screen.findByText("A rumor remains unresolved.")).toBeTruthy();
  expect(screen.getByText("Unconfirmed rumor").className).toContain("status-warning");
  expect(screen.getByText("DISPUTED")).toBeTruthy();
  fireEvent.click(screen.getByText("Evidence and source"));
  expect(screen.getByText(/evidence-1/)).toBeTruthy();
  expect(screen.queryByText(/Worth Watching|Watch Score|Should I watch/)).toBeNull();
});

test("Save uses the persisted command rather than browser-only state", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Save" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/saved-intelligence/save", expect.objectContaining({ method: "POST", body: JSON.stringify({ intelligence_id: "intel-1" }) })));
});

test("Investigations and Deep Analysis remain truthful V1-unavailable states", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Investigations" }));
  expect(await screen.findByText("Investigations are not active in V1")).toBeTruthy();
  expect(screen.getByText(/no active runtime, Evidence Expansion/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText(/Settings cannot trigger a provider/)).toBeTruthy();
});

test("Settings preserves preference provenance and renders unknown resource values as unknown", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText("Prefer evidence-led product analysis.")).toBeTruthy();
  expect(screen.getByText("EXPLICIT")).toBeTruthy();
  expect(screen.getByText("DERIVED")).toBeTruthy();
  expect(screen.getByText("TEMPORARY")).toBeTruthy();
  expect(screen.getByText(/expires 2026-09-02/)).toBeTruthy();
  expect(screen.getByText("Resource Usage")).toBeTruthy();
  expect(screen.getByText(/Token usage: UNKNOWN/)).toBeTruthy();
  expect(screen.getByText(/Cost: UNKNOWN/)).toBeTruthy();
  expect(screen.queryByText(/estimated/i)).toBeNull();
});

test("legal NOT_RELEVANT filtering is shown as Skipped with Analyze, not as failure or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(await screen.findByRole("button", { name: /Source STANDARD_INTELLIGENCE/ }));
  expect(await screen.findByText("SKIPPED")).toBeTruthy();
  expect(screen.getByText(/DAILY.*08:30/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Analyze this Video" })).toBeTruthy();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("Check Now preserves a legal guarded state without inventing a Source Run or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(await screen.findByRole("button", { name: /Source STANDARD_INTELLIGENCE/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Check Now" }));
  expect(await screen.findByText(/Check now is blocked by the runtime side-effect guard/)).toBeTruthy();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("stopping a Source uses the legal enabled command and is not historical deletion", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(await screen.findByRole("button", { name: /Source STANDARD_INTELLIGENCE/ }));
  expect(await screen.findByText(/does not delete historical Intelligence/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Stop future monitoring" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/sources/source-1", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ enabled: false }) })));
});

test("Topic detail waits for its typed projection instead of treating a list response as detail", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  fireEvent.click(await screen.findByRole("button", { name: /Topic.*Current knowledge/ }));
  expect(await screen.findByText("Timeline (historical)")).toBeTruthy();
  expect(screen.getByText("Related Topics")).toBeTruthy();
});
