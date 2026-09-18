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
    if (input.endsWith("/videos/video-1")) return response({ video: { video_id: "video-1", channel_id: "channel-1", channel_name: "Fixture channel", title: "Evidence-led product lesson", source_url: "https://youtube.test/video-1", published_at: "2026-09-01T00:00:00Z", processing_status: "TRANSCRIPT_READY", last_updated: "2026-09-01T00:00:00Z" }, transcript: { status: "AVAILABLE", text: "A decision log preserves evidence and makes the reasoning traceable.", created_at: "2026-09-01T00:00:00Z" }, note: { v1: { status: "UNAVAILABLE", code: "NOTE_REF_NOT_PERSISTED" }, v2: { status: "UNAVAILABLE", code: "NOTE_V2_UNAVAILABLE" } }, history: [{ timestamp: "2026-09-01T00:00:00Z", status: "SUCCEEDED", summary: "Transcript processing completed." }] });
    if (input.endsWith("/videos")) return response({ videos: [{ video_id: "video-1", channel_id: "channel-1", channel_name: "Fixture channel", title: "Evidence-led product lesson", source_url: "https://youtube.test/video-1", published_at: "2026-09-01T00:00:00Z", processing_status: "TRANSCRIPT_READY", last_updated: "2026-09-01T00:00:00Z" }] });
    if (input.endsWith("/intelligence")) return response({ intelligence: [intelligence] });
    if (input.endsWith("/intelligence/intel-1")) return response({ intelligence });
    if (input.endsWith("/saved-intelligence")) return response({ saved: [{ intelligence_id: "intel-old", saved_at: "2026-09-01T00:00:00Z", intelligence: { status: "UNAVAILABLE", code: "CURRENT_NOT_ACTIVE", trusted: false } }] });
    if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [{ brief_id: "week-1", version: "V1", period_start: "2026-09-01T00:00:00Z", no_important_information: false, items: [{ topic_name: "Topic", intelligence_id: "intel-1", claim_kind: "FACT", source_state: "AVAILABLE", summary: "A factual weekly change.", evidence_ids: ["evidence-raw-1"], markers: [{ kind: "SUPERSEDED", reason: "A correction is available." }] }], weekly_v2: { status: "UNAVAILABLE" } }] });
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
  expect(screen.getAllByRole("button", { name: /^(Home|Following|Content|Intelligence|Topics|Settings)$/ })).toHaveLength(6);
  for (const legacy of ["Dashboard", "Sources", "Investigations", "Videos", "Activity", "Saved", "Weekly", "Daily", "Ask", "Runs", "Jobs"]) expect(screen.queryByRole("button", { name: new RegExp(`^${legacy}$`) })).toBeNull();
  expect(screen.getByText("Analysis is paused because no approved model is currently available.")).toBeTruthy();
  expect(screen.queryByText("MODEL_UNAVAILABLE")).toBeNull();
});

test("a fresh library gets a three-step local-first onboarding with an isolated synthetic sample", async () => {
  const fetchMock = vi.fn((input: string, _init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ intelligence: [], pinned_topics: [], weekly_v1: [], needs_attention: [], operations: { source_count: 0 } });
    if (input.endsWith("/sources")) return response({ sources: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  expect(await screen.findByRole("heading", { name: /Turn what you follow into traceable knowledge/ })).toBeTruthy();
  expect(screen.getByLabelText("Onboarding step 1 of 3")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(await screen.findByText("Recommended")).toBeTruthy();
  expect(screen.getByLabelText("Synthetic sample experience")).toBeTruthy();
  expect(screen.getByText(/UI-only example · not written to your library/)).toBeTruthy();
  expect(screen.getByText(/Evaluation baselines should be versioned before prompt changes/)).toBeTruthy();
  expect(fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === "POST")).toBe(false);

  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(await screen.findByLabelText("Onboarding step 3 of 3")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Add first Following" }));
  expect(await screen.findByText(/Set up your first Following/)).toBeTruthy();
});

test("onboarding never hides existing historical Intelligence even when there are no Followings", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ intelligence: [intelligence], pinned_topics: [], weekly_v1: [], needs_attention: [], operations: { source_count: 0 } });
    if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
    if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [] });
    return response({});
  }));

  render(<App />);
  expect(await screen.findByText("A rumor remains unresolved.")).toBeTruthy();
  expect(screen.queryByLabelText(/Onboarding step/)).toBeNull();
});

test("Content reads the existing video and transcript projections without fabricating notes", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(await screen.findByRole("button", { name: /Evidence-led product lesson/ }));
  expect(await screen.findByText("A decision log preserves evidence and makes the reasoning traceable.")).toBeTruthy();
  expect(screen.getByText("Summary / Video Notes")).toBeTruthy();
  expect(screen.getByText(/No summary is fabricated from missing output/)).toBeTruthy();
  expect(screen.getByText("Processing history")).toBeTruthy();
});

test("verified Intelligence preserves rumor, dispute, and evidence without watch-score language", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  expect(await screen.findByText("A rumor remains unresolved.")).toBeTruthy();
  expect(screen.getByText("Unconfirmed rumor")).toBeTruthy();
  expect(screen.getByText("Disputed")).toBeTruthy();
  fireEvent.click(screen.getByText("Evidence and source"));
  expect(screen.getByText(/source-1.*video-1.*1s/)).toBeTruthy();
  expect(screen.queryByText(/Worth Watching|Watch Score|Should I watch/)).toBeNull();
});

test("Save uses the persisted command rather than browser-only state", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Save" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/saved-intelligence/save", expect.objectContaining({ method: "POST", body: JSON.stringify({ intelligence_id: "intel-1" }) })));
});

test("Deep Analysis remains a truthful unavailable state in Settings", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText(/This screen cannot enable a provider/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Investigations" })).toBeNull();
});

test("Settings preserves preference provenance and renders unknown resource values as unknown", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText("Prefer evidence-led product analysis.")).toBeTruthy();
  expect(screen.getByText("Explicit")).toBeTruthy();
  expect(screen.getByText("Derived")).toBeTruthy();
  expect(screen.getByText("Temporary")).toBeTruthy();
  expect(screen.getByText(/Expires Sep 2, 2026/)).toBeTruthy();
  expect(screen.getByText("Resource Usage")).toBeTruthy();
  expect(screen.getByText(/Token usage: Unavailable/)).toBeTruthy();
  expect(screen.getByText(/Cost: Unavailable/)).toBeTruthy();
  expect(screen.queryByText(/estimated/i)).toBeNull();
});

test("legal NOT_RELEVANT filtering is shown as Skipped with Analyze, not as failure or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click(await screen.findByRole("button", { name: /Source.*Monitoring new videos/ }));
  expect(await screen.findByText("Skipped")).toBeTruthy();
  expect(screen.getByText(/Runs daily at 08:30/)).toBeTruthy();
  expect(screen.getByText("Excluded by your ignore rules.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Analyze this Video" })).toBeTruthy();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("Check Now preserves a legal guarded state without inventing a Source Run or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click(await screen.findByRole("button", { name: /Source.*Monitoring new videos/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Check Now" }));
  expect(await screen.findByText(/Processing is currently unavailable in this local setup/)).toBeTruthy();
  expect(screen.queryByText(/runtime side-effect guard/i)).toBeNull();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("stopping a Source uses the legal enabled command and is not historical deletion", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click(await screen.findByRole("button", { name: /Source.*Monitoring new videos/ }));
  expect(await screen.findByText(/existing Intelligence remains unchanged/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Stop future monitoring" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/sources/source-1", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ enabled: false }) })));
});

test("Topic detail waits for its typed projection instead of treating a list response as detail", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  fireEvent.click(await screen.findByRole("button", { name: /Topic.*Current understanding/ }));
  expect(await screen.findByText("Timeline")).toBeTruthy();
  expect(screen.getByText("Related Topics")).toBeTruthy();
});

test("Topic rename changes only the label through the existing Topic command", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  fireEvent.click(await screen.findByRole("button", { name: /Topic.*Current understanding/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Rename Topic" }));
  expect(screen.getByText(/does not rewrite Intelligence, Evidence, or Topic membership/i)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Topic name"), { target: { value: "Renamed Topic" } });
  fireEvent.click(screen.getByRole("button", { name: "Save name" }));

  await waitFor(() => expect(fetch).toHaveBeenCalledWith(
    "/api/v1/topics/topic-1",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ name: "Renamed Topic" }),
    }),
  ));
});


test("a new user can reach a Source setup surface with the bounded V1 controls", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input.endsWith("/sources")) return response({ sources: [] });
    return response({});
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  expect(await screen.findByText(/Set up your first Following/)).toBeTruthy();
  fireEvent.click(screen.getAllByRole("button", { name: "Add Following" })[1]);

  expect(await screen.findByRole("heading", { name: "Add a Following" })).toBeTruthy();
  expect(screen.getByLabelText("YouTube URL")).toBeTruthy();
  expect(screen.getByLabelText("Monitor this Following")).toBeTruthy();
  expect(screen.getByLabelText("Automatic schedule")).toBeTruthy();
  expect(screen.getByLabelText("Initial history")).toBeTruthy();
  expect(screen.getByLabelText("Per-run limit")).toBeTruthy();
  expect(screen.getByLabelText("Focus")).toBeTruthy();
  expect(screen.getByLabelText("Ignore")).toBeTruthy();
  expect(screen.getByLabelText("Distillation style")).toBeTruthy();
  expect(screen.getByText(/recent existing videos are considered when this Following is first added/i)).toBeTruthy();
  expect(screen.getByText(/maximum number of new videos processed in one bounded run/i)).toBeTruthy();
  expect(Array.from((screen.getByLabelText("Initial history") as HTMLSelectElement).options).map(option => option.value)).toEqual(["0", "1", "3", "5", "10"]);
  expect(Array.from((screen.getByLabelText("Per-run limit") as HTMLSelectElement).options).map(option => option.value)).toEqual(["1", "3", "5", "10"]);
  expect(Array.from((screen.getByLabelText("Distillation style") as HTMLSelectElement).options).map(option => option.value)).toEqual(["BALANCED", "TECHNICAL_DETAIL_FIRST", "PRODUCT_CASE_FIRST", "TREND_OPINION_FIRST"]);
});

test("Source setup writes only through the existing Source, policy, and schedule commands", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/sources") && init?.method === "POST") return response({ source: { source_id: "source-new", canonical_url: "https://youtube.test/new", enabled: true, processing_policy: "STANDARD_INTELLIGENCE", display_name: null, last_error: null } });
    if (input.endsWith("/sources/source-new/policy")) return response({ policy: {} });
    if (input.endsWith("/sources/source-new") && init?.method === "PATCH") return response({ source: {} });
    if (input.endsWith("/automation")) return response({ schedule: {} });
    if (input.endsWith("/sources")) return response({ sources: [] });
    return response({});
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click((await screen.findAllByRole("button", { name: "Add Following" }))[1]);
  fireEvent.change(screen.getByLabelText("YouTube URL"), { target: { value: "https://youtube.test/new" } });
  fireEvent.click(screen.getByLabelText("Monitor this Following"));
  fireEvent.change(screen.getByLabelText("Initial history"), { target: { value: "3" } });
  fireEvent.change(screen.getByLabelText("Per-run limit"), { target: { value: "10" } });
  fireEvent.change(screen.getByLabelText("Focus"), { target: { value: "product, AI" } });
  fireEvent.change(screen.getByLabelText("Ignore"), { target: { value: "rough" } });
  fireEvent.change(screen.getByLabelText("Distillation style"), { target: { value: "PRODUCT_CASE_FIRST" } });
  fireEvent.change(screen.getByLabelText("Automatic schedule"), { target: { value: "WEEKLY" } });
  fireEvent.click(screen.getAllByRole("button", { name: "Add Following" }).at(-1)!);
  await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/sources", expect.objectContaining({ method: "POST", body: JSON.stringify({ url: "https://youtube.test/new", processing_policy: "STANDARD_INTELLIGENCE" }) })));
  expect(fetch).toHaveBeenCalledWith("/api/v1/sources/source-new", expect.objectContaining({ method: "PATCH", body: JSON.stringify({ enabled: false, processing_policy: "STANDARD_INTELLIGENCE" }) }));
  expect(fetch).toHaveBeenCalledWith("/api/v1/sources/source-new/policy", expect.objectContaining({ method: "PUT", body: expect.stringContaining('"initial_history_count":3') }));
  expect(fetch).toHaveBeenCalledWith("/api/v1/automation", expect.objectContaining({ method: "POST", body: expect.stringContaining('"target_type":"SOURCE_CHECK"') }));
});

test("Saved, Topic, and Weekly keep trust meaning while hiding backend codes from primary reading", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Saved" }));
  expect(await screen.findByText(/no longer available as current Intelligence/)).toBeTruthy();
  expect(screen.queryByText("CURRENT_NOT_ACTIVE")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Weekly" }));
  expect(await screen.findByText(/Weekly digest · Sep 1, 2026/)).toBeTruthy();
  expect(screen.getByText("Evidence references").parentElement?.hasAttribute("open")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  expect(await screen.findByText(/Some support is unavailable/)).toBeTruthy();
  expect(screen.queryByText("DEGRADED")).toBeNull();
});
