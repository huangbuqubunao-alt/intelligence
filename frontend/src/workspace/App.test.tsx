import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

const intelligence = { status: "AVAILABLE", trusted: true, intelligence_id: "intel-1", claim_kind: "RUMOR", state: "DISPUTED", card: { core_conclusion: "A rumor remains unresolved.", user_relevant_information: ["Watch for confirmation."], important_new_information: [], source_id: "source-1", video_id: "video-1", original_video_url: "https://youtube.test/video", evidence_links: [{ evidence_id: "evidence-1", start_ms: 1000, end_ms: 2000 }] } };
const response = (value: object) => Promise.resolve({ ok: true, json: async () => value });

beforeEach(() => {
  location.hash = "";
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ intelligence: [intelligence], pinned_topics: [], weekly_v1: [], needs_attention: [], operations: { source_count: 1 } });
    if (input.endsWith("/intelligence")) return response({ intelligence: [intelligence] });
    if (input.endsWith("/intelligence/intel-1")) return response({ intelligence });
    if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
    if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [] });
    if (input.endsWith("/topics")) return response({ topics: [] });
    if (input.endsWith("/sources")) return response({ sources: [{ source_id: "source-1", display_name: "Source", canonical_url: "https://youtube.test/source", enabled: true, processing_policy: "STANDARD_INTELLIGENCE", last_error: null }] });
    if (input.endsWith("/settings/preferences")) return response({ active: [], history: [] });
    if (input.endsWith("/settings/source-policy")) return response({ policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" } });
    if (input.endsWith("/settings")) return response({ providers: [{ provider: "Kimi", production_eligible: false, qualification_status: "UNQUALIFIED", reason: "Not qualified" }] });
    if (input.endsWith("/saved-intelligence/save") || input.endsWith("/saved-intelligence/unsave")) return response({ saved: true });
    return response({});
  }));
});
afterEach(() => vi.unstubAllGlobals());

test("frozen product IA exposes exactly its six first-level destinations", async () => {
  render(<App />);
  await screen.findByText("Important Intelligence");
  expect(screen.getAllByRole("button", { name: /^(Dashboard|Intelligence|Topics|Sources|Investigations|Settings)$/ })).toHaveLength(6);
  for (const legacy of ["Videos", "Activity", "Saved", "Weekly", "Daily", "Ask", "Runs", "Jobs"]) expect(screen.queryByRole("button", { name: new RegExp(`^${legacy}$`) })).toBeNull();
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
