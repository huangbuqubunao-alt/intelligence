import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

const response = (value: object) => Promise.resolve({ ok: true, json: async () => value });

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ sources: { total: 0, needs_attention: 0 }, new_videos: 0, recent_videos: [], next_scheduled_run: null, recent_processing: [], deep_analysis: { status: "BLOCKED", reason: "No qualified live provider." } });
    if (input.endsWith("/sources") && init?.method === "POST") return response({ source: { source_id: "s1" } });
    if (input.endsWith("/sources")) return response({ sources: [] });
    if (input.endsWith("/videos")) return response({ videos: [{ video_id: "abcdefghijk", channel_id: "UC1234567890123456789012", title: "Verified data", channel_name: "Channel", processing_status: "COMPLETE", scoring: { status: "VERIFIED" }, note: { status: "V2" }, deep_analysis: { status: "BLOCKED", reason: "No qualified live provider." }, last_updated: "2026-09-01" }] });
    if (input.endsWith("/weekly")) return response({ weekly: [] });
    if (input.endsWith("/automation")) return response({ schedules: [] });
    if (input.endsWith("/activity")) return response({ runs: [] });
    if (input.endsWith("/settings")) return response({ model_preference: { active_production_default: null }, providers: [{ provider: "Kimi", credential_status: "Not configured", adapter_available: true, qualification_status: "UNQUALIFIED", production_eligible: false, reason: "1/2; SCHEMA_INVALID" }] });
    if (input.endsWith("/system")) return response({ release_posture: "NO-GO", doctor: { status: "NOT_RUN" }, backup: { status: "NOT_RUN" } });
    return response({});
  }));
});

afterEach(() => vi.unstubAllGlobals());

test("add source flow saves only explicit source configuration", async () => {
  render(<App />); fireEvent.click(screen.getByText("Sources")); await screen.findByText(/Add a Channel/); fireEvent.click(screen.getByText("Add source")); fireEvent.change(screen.getByPlaceholderText("https://www.youtube.com/..."), { target: { value: "https://youtu.be/abcdefghijk" } }); fireEvent.click(screen.getByText("Save source")); await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/v1/sources", expect.objectContaining({ method: "POST" })));
});

test("provider and Deep Analysis blocked truth is visible", async () => {
  render(<App />); await screen.findByText("Deep Analysis unavailable"); fireEvent.click(screen.getByText("Settings")); expect(await screen.findByText("1/2; SCHEMA_INVALID")).toBeTruthy(); expect(screen.getByText("Active production model:")).toBeTruthy();
});

test("video detail protects verified score and ambiguous retry boundary", async () => {
  render(<App />); fireEvent.click(screen.getByText("Videos")); expect(await screen.findByText("Verified data")).toBeTruthy(); fireEvent.click(screen.getByText("Verified data")); fireEvent.click(screen.getByRole("button", { name: "Scoring" })); expect(screen.getByText(/AuthoritativeScoringReader/)).toBeTruthy(); fireEvent.click(screen.getByRole("button", { name: "History" })); expect(screen.getByText(/will not automatically retry/)).toBeTruthy();
});
