import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App, ScoringTab } from "./App";

const response = (value: object) => Promise.resolve({ ok: true, json: async () => value });
let demoSystem = false;

beforeEach(() => {
  demoSystem = false;
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ sources: { total: 0, needs_attention: 0 }, new_videos: 0, recent_videos: [], next_scheduled_run: null, recent_processing: [], deep_analysis: { status: "BLOCKED", reason: "No qualified live provider." } });
    if (input.endsWith("/sources") && init?.method === "POST") return response({ source: { source_id: "s1" } });
    if (input.endsWith("/sources/s1")) return response({ source: { source_id: "s1", canonical_url: "https://youtube.test/source", enabled: true, processing_policy: "DISCOVER_ONLY" }, schedules: [], recent_videos: [{ video_id: "abcdefghijk", title: "Source video", published_at: "2026-09-01T00:00:00Z", processing_status: "COMPLETE" }], activity: { status: "AVAILABLE", runs: [] } });
    if (input.endsWith("/sources")) return response({ sources: [{ source_id: "s1", source_type: "CHANNEL", canonical_url: "https://youtube.test/source", display_name: "Source", enabled: true, processing_policy: "DISCOVER_ONLY", last_checked_at: null, last_error: null }] });
    if (input.endsWith("/videos/abcdefghijk")) return response({ video: { video_id: "abcdefghijk" }, scoring: { status: "AVAILABLE", score: 8.5, reason: "Clear product evidence.", topics: ["product"], should_summarize: true, trusted: true, provenance: { provider: "fixture", model: "verified-model", prompt_version: "v1", success_provenance: "VERIFIED_LINEAGE" } }, transcript: { status: "AVAILABLE", text: "Verified transcript text.", created_at: "2026-09-01T00:00:00Z" }, note: { v1: { status: "UNAVAILABLE", code: "NOTE_REF_NOT_PERSISTED" }, v2: { status: "UNAVAILABLE", code: "NOTE_V2_UNAVAILABLE" } }, history: [{ timestamp: "2026-09-01T00:00:00Z", type: "JOB_STATUS", status: "AMBIGUOUS", summary: "Provider may have received the request.", code: "AMBIGUOUS", context: { stage: "ANALYSIS" } }] });
    if (input.endsWith("/videos")) return response({ videos: [{ video_id: "abcdefghijk", channel_id: "UC1234567890123456789012", title: "Verified data", channel_name: "Channel", processing_status: "COMPLETE", scoring: { status: "VERIFIED" }, note: { status: "UNAVAILABLE" }, deep_analysis: { status: "BLOCKED", reason: "No qualified live provider." }, last_updated: "2026-09-01" }] });
    if (input.endsWith("/weekly")) return response({ weekly: [{ report_id: "weekly-1", iso_year: 2026, iso_week: 36, version: "UNKNOWN", status: "WRITTEN", content: null, content_status: "UNAVAILABLE", weekly_v2: { status: "UNAVAILABLE", code: "WEEKLY_V2_UNAVAILABLE" }, linkage: { status: "UNAVAILABLE_IN_CURRENT_AUTHORITY", videos: [] } }] });
    if (input.endsWith("/automation")) return response({ schedules: [] });
    if (input.endsWith("/activity")) return response({ runs: [] });
    if (input.endsWith("/settings")) return response({ model_preference: { active_production_default: null }, providers: [{ provider: "Kimi", credential_status: "Not configured", adapter_available: true, qualification_status: "UNQUALIFIED", production_eligible: false, reason: "1/2; SCHEMA_INVALID" }] });
    if (input.endsWith("/system")) return response({ release_posture: "NO-GO", doctor: { status: "NOT_RUN" }, backup: { status: "NOT_RUN" }, runtime: { mode: demoSystem ? "PO_REVIEW_DEMO" : "STANDARD_LOCAL", demo_data: demoSystem } });
    return response({});
  }));
});

afterEach(() => vi.unstubAllGlobals());

test("add source saves a configurable daily schedule without checking the source", async () => {
  render(<App />); fireEvent.click(screen.getByText("Sources")); await screen.findByText("Source", { selector: "strong" }); fireEvent.click(screen.getByText("Add source")); fireEvent.change(screen.getByPlaceholderText("https://www.youtube.com/..."), { target: { value: "https://youtu.be/abcdefghijk" } }); fireEvent.change(screen.getByLabelText("Schedule frequency"), { target: { value: "DAILY" } }); fireEvent.change(screen.getByLabelText("Schedule time"), { target: { value: "08:30" } }); fireEvent.click(screen.getByText("Save source")); await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/automation", expect.objectContaining({ method: "POST", body: JSON.stringify({ target_type: "SOURCE_CHECK", target_id: "s1", frequency: "DAILY", weekday: null, local_time: "08:30", enabled: true }) }))); expect(fetch).not.toHaveBeenCalledWith("/api/v1/sources/s1/check", expect.anything());
});

test("provider and Deep Analysis blocked truth is visible", async () => {
  render(<App />); await screen.findByText("Deep Analysis unavailable"); fireEvent.click(screen.getByText("Settings")); expect(await screen.findByText("1/2; SCHEMA_INVALID")).toBeTruthy(); expect(screen.getByText("Active production model:")).toBeTruthy();
});

test("video detail consumes transcript, note, and ambiguous lifecycle projections", async () => {
  render(<App />); fireEvent.click(screen.getByText("Videos")); expect(await screen.findByText("Verified data")).toBeTruthy(); fireEvent.click(screen.getByText("Verified data")); fireEvent.click(screen.getByRole("button", { name: "Scoring" })); expect(await screen.findByText("Clear product evidence.")).toBeTruthy(); expect(screen.getByText("VERIFIED SCORING")).toBeTruthy(); fireEvent.click(screen.getByRole("button", { name: "History" })); expect(screen.getByText(/will not automatically retry/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Transcript" })); expect(await screen.findByText("Verified transcript text.")).toBeTruthy(); fireEvent.click(screen.getByRole("button", { name: "Note" })); expect(screen.getByText("NOTE_REF_NOT_PERSISTED")).toBeTruthy();
});

test("weekly shows UNKNOWN truth without pretending to have V2 or linkage", async () => {
  render(<App />); fireEvent.click(screen.getByText("Weekly")); expect(await screen.findByText("2026 W36")).toBeTruthy(); expect(screen.getByText("UNKNOWN")).toBeTruthy(); expect(screen.getAllByText(/unavailable in current authority/)).toHaveLength(2);
});

test("source recent videos open the existing video detail", async () => {
  render(<App />); fireEvent.click(screen.getByText("Sources")); fireEvent.click(await screen.findByText("Open")); expect(await screen.findByText("Source video")).toBeTruthy(); fireEvent.click(screen.getByText("Source video")); expect(await screen.findByText("VIDEO DETAIL")).toBeTruthy();
});

test("scoring states never render unavailable or failed attempts as verified", () => {
  const { rerender } = render(<ScoringTab error={null} scoring={{ status: "NOT_AVAILABLE", reason: "No verified result." }} />);
  expect(screen.getByText("No verified result.")).toBeTruthy();
  expect(screen.queryByText("VERIFIED SCORING")).toBeNull();
  rerender(<ScoringTab error={null} scoring={{ status: "FAILED", code: "SCHEMA_INVALID" }} />);
  expect(screen.getByText("Scoring did not complete with a trusted result. No score is shown.")).toBeTruthy();
  expect(screen.getByText("SCHEMA_INVALID")).toBeTruthy();
  expect(screen.queryByText("VERIFIED SCORING")).toBeNull();
});

test("PO Review Demo badge is displayed only when the backend projects demo data", async () => {
  demoSystem = true;
  render(<App />);
  expect(await screen.findByText("PO Review Demo")).toBeTruthy();
});
