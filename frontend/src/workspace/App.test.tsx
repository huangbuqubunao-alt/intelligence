import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import { apiProxyTarget } from "../api/proxy";

const intelligence = {
  status: "AVAILABLE",
  trusted: true,
  intelligence_id: "intel-1",
  claim_kind: "RUMOR",
  state: "DISPUTED",
  card: {
    core_conclusion: "A rumor remains unresolved.",
    user_relevant_information: [
      "Watch for confirmation before changing your plans.",
    ],
    important_new_information: [
      "A second source now challenges the original claim.",
    ],
    meaningful_details: ["The available sources are not yet independent."],
    source_id: "source-1",
    source_display_name: "3Blue1Brown",
    source_url: "https://youtube.test/source",
    video_id: "video-1",
    video_title: "Transformers, the tech behind LLMs | Deep Learning Chapter 5",
    original_video_url: "https://youtube.test/video",
    evidence_links: [{
      evidence_id: "evidence-1",
      start_ms: 1000,
      end_ms: 2000,
      excerpt:
        "Attention lets each token weigh relevant context from other tokens.",
    }],
  },
};
const topic = {
  topic_id: "topic-1",
  name: "Topic",
  pinned: false,
  lifecycle: "ACTIVE",
  current_state: "DEGRADED",
  independence: "UNKNOWN",
  contributions: [],
  timeline: [{
    event_id: "event-1",
    event_kind: "NEW_INFORMATION",
    state: "UNRESOLVED",
    created_at: "2026-09-01T00:00:00Z",
  }],
  relations: [],
};
const response = (value: object) =>
  Promise.resolve({ ok: true, json: async () => value });

beforeEach(() => {
  location.hash = "";
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/dashboard")) {
        return response({
          intelligence: [{
            status: "UNAVAILABLE",
            trusted: false,
            code: "CURRENT_NOT_ACTIVE",
          }, intelligence],
          pinned_topics: [],
          weekly_v1: [],
          needs_attention: [{
            run_id: "attention-1",
            state: "NEEDS_ATTENTION",
            attention_reason: "MODEL_UNAVAILABLE",
            trigger: "MANUAL_CHECK_NOW",
            updated_at: "2026-09-01T00:00:00Z",
          }],
          operations: { source_count: 1 },
        });
      }
      if (input.endsWith("/intelligence")) {
        return response({ intelligence: [intelligence] });
      }
      if (input.endsWith("/intelligence/intel-1")) {
        return response({ intelligence });
      }
      if (input.endsWith("/saved-intelligence")) {
        return response({
          saved: [{
            intelligence_id: "intel-old",
            saved_at: "2026-09-01T00:00:00Z",
            intelligence: {
              status: "UNAVAILABLE",
              code: "CURRENT_NOT_ACTIVE",
              trusted: false,
            },
          }],
        });
      }
      if (input.endsWith("/weekly/v1")) {
        return response({
          weekly_v1: [{
            brief_id: "week-1",
            version: "V1",
            period_start: "2026-09-01T00:00:00Z",
            no_important_information: false,
            items: [{
              topic_name: "Topic",
              intelligence_id: "intel-1",
              claim_kind: "FACT",
              source_state: "AVAILABLE",
              summary: "A factual weekly change.",
              evidence_ids: ["evidence-raw-1"],
              markers: [{
                kind: "SUPERSEDED",
                reason: "A correction is available.",
              }],
            }],
            weekly_v2: { status: "UNAVAILABLE" },
          }],
        });
      }
      if (input.endsWith("/topics/topic-1")) return response({ topic });
      if (input.endsWith("/topics")) return response({ topics: [topic] });
      if (
        input.endsWith("/sources/source-1") && init?.method === "PATCH"
      ) {
        return response({ source: { source_id: "source-1", enabled: false } });
      }
      if (input.endsWith("/sources/source-1/check")) {
        return response({
          status: "BLOCKED",
          message: "Check now is blocked by the runtime side-effect guard.",
        });
      }
      if (input.endsWith("/sources/source-1")) {
        return response({
          source: {
            source_id: "source-1",
            display_name: null,
            friendly_name: "Marques Brownlee",
            channel_id: "UCBJycsmduvYEL83R_U4JriQ",
            canonical_url: "https://youtube.test/source",
            enabled: true,
            processing_policy: "STANDARD_INTELLIGENCE",
            last_error: null,
          },
          policy: {
            initial_history_count: 5,
            per_run_max_new_videos: 5,
            focus_rules: ["AI"],
            ignore_rules: ["rough"],
            distillation_style: "BALANCED",
          },
          schedules: [{
            schedule_id: "schedule-1",
            frequency: "DAILY",
            local_time: "08:30",
            enabled: true,
          }],
          recent_videos: [{
            video_id: "skip-1",
            title: "Rough draft",
            processing_status: "METADATA_READY",
            filter: { outcome: "NOT_RELEVANT", reason: "IGNORE_RULE_MATCH" },
          }],
          source_runs: [],
        });
      }
      if (input.endsWith("/sources")) {
        return response({
          sources: [{
            source_id: "source-1",
            display_name: null,
            friendly_name: "Marques Brownlee",
            channel_id: "UCBJycsmduvYEL83R_U4JriQ",
            canonical_url: "https://youtube.test/source",
            enabled: true,
            processing_policy: "STANDARD_INTELLIGENCE",
            last_error: null,
          }],
        });
      }
      if (input.endsWith("/settings/preferences")) {
        return response({
          active: [],
          history: [
            {
              preference_id: "explicit",
              horizon: "LONG_TERM",
              provenance: "EXPLICIT",
              statement: "Prefer evidence-led product analysis.",
              expires_at: null,
            },
            {
              preference_id: "derived",
              horizon: "RECENT",
              provenance: "DERIVED",
              statement: "Recent interest in evaluation practice.",
              expires_at: null,
            },
            {
              preference_id: "temporary",
              horizon: "TEMPORARY_FOCUS",
              provenance: "TEMPORARY",
              statement: "Focus this week on decision logs.",
              expires_at: "2026-09-02T00:00:00Z",
            },
          ],
        });
      }
      if (input.endsWith("/settings/source-policy")) {
        return response({
          policy: {
            initial_history_count: 5,
            per_run_max_new_videos: 5,
            focus_rules: [],
            ignore_rules: [],
            distillation_style: "BALANCED",
          },
        });
      }
      if (input.endsWith("/settings/resource-usage")) {
        return response({
          usage: [{
            execution_id: "exec-1",
            reason: "PERSONALIZED_INTELLIGENCE",
            actual_provider: "offline-test",
            actual_model: "deterministic-v1",
            invocation_count: 1,
            input_tokens: null,
            output_tokens: null,
            cost_microunits: null,
            duration_ms: 0,
            status: "SUCCEEDED",
            budget_state: "ADMITTED",
            outcome: "ADMITTED",
          }],
        });
      }
      if (input.endsWith("/settings")) {
        return response({
          providers: [{
            provider: "NVIDIA NIM",
            model: "moonshotai/kimi-k3",
            adapter_available: true,
            authorized: true,
            production_eligible: true,
            qualification_status: "QUALIFIED",
            scope: "V1_VIDEO_DISTILLATION_ONLY",
            reason: "Approved for V1 Video Distillation only.",
          }],
        });
      }
      if (
        input.endsWith("/saved-intelligence/save") ||
        input.endsWith("/saved-intelligence/unsave")
      ) return response({ saved: true });
      return response({});
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

test("PO demo can direct the development proxy to its owned loopback API", () => {
  expect(apiProxyTarget("http://127.0.0.1:8766")).toBe("http://127.0.0.1:8766");
});

test("frozen product IA exposes exactly its six first-level destinations", async () => {
  render(<App />);
  await screen.findByText("What matters now");
  expect(
    screen.getAllByRole("button", {
      name: /^(Dashboard|Intelligence|Topics|Sources|Investigations|Settings)$/,
    }),
  ).toHaveLength(6);
  for (
    const legacy of [
      "Videos",
      "Activity",
      "Saved",
      "Weekly",
      "Daily",
      "Ask",
      "Runs",
      "Jobs",
    ]
  ) {
    expect(screen.queryByRole("button", { name: new RegExp(`^${legacy}$`) }))
      .toBeNull();
  }
  expect(screen.getByText("Video analysis is paused.")).toBeTruthy();
  expect(screen.queryByText("MODEL_UNAVAILABLE")).toBeNull();
});

test("Dashboard leads with meaningful Intelligence and keeps attention subordinate", async () => {
  render(<App />);
  const conclusion = await screen.findByText("A rumor remains unresolved.");
  const attention = screen.getByText("Needs Attention");
  expect(
    conclusion.compareDocumentPosition(attention) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).not.toBe(0);
  expect(screen.getByText("Why this matters")).toBeTruthy();
  expect(screen.getByText("What is new")).toBeTruthy();
  expect(screen.queryByText("This Intelligence is not available as current information."))
    .toBeNull();
  expect(screen.queryByText("Deep Analysis blocked")).toBeNull();
});

test("Needs Attention explains every legal category without primary runtime language", async () => {
  const reasons = [
    "MODEL_UNAVAILABLE",
    "BUDGET_BLOCKED",
    "AMBIGUOUS_EXTERNAL_OUTCOME",
    "USER_DECISION_REQUIRED",
    "EXECUTION_CONDITION_UNRESOLVED",
  ];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/dashboard")) {
        return response({
          intelligence: [intelligence],
          pinned_topics: [],
          weekly_v1: [],
          needs_attention: reasons.map((attention_reason, index) => ({
            run_id: `attention-${index}`,
            state: "NEEDS_ATTENTION",
            attention_reason,
            trigger: "MANUAL_CHECK_NOW",
            updated_at: "2026-09-01T00:00:00Z",
          })),
        });
      }
      return response({});
    }),
  );
  render(<App />);
  expect(await screen.findByText("Video analysis is paused.")).toBeTruthy();
  expect(screen.getByText("This run reached its budget limit.")).toBeTruthy();
  expect(screen.getByText("An external result could not be confirmed.")).toBeTruthy();
  expect(screen.getByText("Your decision is required.")).toBeTruthy();
  expect(screen.getByText("This run is waiting for a clear decision.")).toBeTruthy();
  for (const reason of reasons) expect(screen.queryByText(reason)).toBeNull();
  expect(screen.queryByText("Retry", { exact: true })).toBeNull();
});

test("an empty Dashboard explains the next useful step in ordinary language", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/dashboard")) {
        return response({
          intelligence: [],
          pinned_topics: [],
          weekly_v1: [],
          needs_attention: [],
        });
      }
      return response({});
    }),
  );
  render(<App />);
  expect(await screen.findByText("No important new intelligence yet."))
    .toBeTruthy();
  expect(screen.getByText(/Add a Source to start monitoring/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Add Source" })).toBeTruthy();
});

test("verified Intelligence preserves rumor, dispute, and evidence without watch-score language", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  expect(await screen.findByText("A rumor remains unresolved.")).toBeTruthy();
  expect(screen.queryByText("This Intelligence is not available as current information."))
    .toBeNull();
  expect(screen.getByText("Unconfirmed rumor")).toBeTruthy();
  expect(screen.getByText("Sources disagree")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Evidence" })).toBeTruthy();
  expect(screen.getByText("3Blue1Brown")).toBeTruthy();
  expect(
    screen.getByText(
      "Transformers, the tech behind LLMs | Deep Learning Chapter 5",
    ),
  ).toBeTruthy();
  expect(screen.getByText("0:01–0:02")).toBeTruthy();
  expect(
    screen.getByText(
      "Attention lets each token weigh relevant context from other tokens.",
    ),
  ).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Open video at 0:01" }).getAttribute(
      "href",
    ),
  ).toBe("https://youtube.test/video?t=1");
  expect(screen.queryByText(/Worth Watching|Watch Score|Should I watch/))
    .toBeNull();
});

test("Intelligence hierarchy labels relevance, new information, and supporting detail before Evidence", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  const why = await screen.findByText("Why this matters");
  const changed = screen.getByText("What is new");
  const details = screen.getByText("Important details");
  const evidence = screen.getByRole("heading", { name: "Evidence" });
  expect(
    why.compareDocumentPosition(changed) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).not.toBe(0);
  expect(
    changed.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).not.toBe(0);
  expect(
    details.compareDocumentPosition(evidence) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).not.toBe(0);
});

test("primary UI humanizes internal states while keeping technical diagnostics disclosed", async () => {
  render(<App />);
  await screen.findByText("A rumor remains unresolved.");
  const primaryText = Array.from(document.querySelectorAll("main *"))
    .filter((element) => !element.closest("details"))
    .map((element) =>
      element.childNodes.length === 1 ? element.textContent ?? "" : ""
    )
    .join(" ");
  expect(primaryText).not.toMatch(
    /TASK-|CURRENT_NOT_ACTIVE|FOCUS_MATCH|IGNORE_RULE_MATCH|UNQUALIFIED|SCHEMA_INVALID|PRODUCTION_ELIGIBLE|AMBIGUOUS|request hash|reservation|runtime side-effect guard/i,
  );
});

test("Save uses the persisted command rather than browser-only state", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Save" }));
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/saved-intelligence/save",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ intelligence_id: "intel-1" }),
      }),
    )
  );
});

test("Investigations and Deep Analysis remain truthful V1-unavailable states", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Investigations" }));
  expect(await screen.findByText("Investigations are not active in V1"))
    .toBeTruthy();
  expect(screen.getByText(/Evidence Expansion, external validation/))
    .toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText(/this screen cannot enable it/))
    .toBeTruthy();
});

test("Settings preserves preference provenance and renders unknown resource values as unknown", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText("Prefer evidence-led product analysis."))
    .toBeTruthy();
  expect(screen.getByText("Explicit")).toBeTruthy();
  expect(screen.getByText("Derived")).toBeTruthy();
  expect(screen.getByText("Temporary")).toBeTruthy();
  expect(screen.getByText(/Expires Sep 2, 2026/)).toBeTruthy();
  expect(screen.getByText("Resource Usage")).toBeTruthy();
  expect(screen.getByText(/Token usage: Unavailable/)).toBeTruthy();
  expect(screen.getByText(/Cost: Unavailable/)).toBeTruthy();
  expect(screen.queryByText(/estimated/i)).toBeNull();
});

test("Settings presents Kimi scope truthfully and keeps provider mechanics collapsed", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(await screen.findByText("Video Distillation")).toBeTruthy();
  expect(screen.getByText("Available for V1 video analysis only."))
    .toBeTruthy();
  expect(screen.getByText("Deep Analysis is unavailable.")).toBeTruthy();
  const disclosure =
    screen.getByText("Provider and model details").parentElement;
  expect(disclosure?.hasAttribute("open")).toBe(false);
  expect(screen.getByText("NVIDIA NIM · moonshotai/kimi-k3")).toBeTruthy();
  expect(screen.getByText("Scope: Video Distillation only.")).toBeTruthy();
});

test("Sources prefer a persisted friendly name while keeping the canonical URL accessible", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  expect(await screen.findByText("Marques Brownlee")).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Open Source" }).getAttribute("href"),
  ).toBe("https://youtube.test/source");
  expect(
    screen.queryByRole("button", { name: /^https:\/\/youtube\.test\/source/ }),
  ).toBeNull();
});

test("legal NOT_RELEVANT filtering is shown as Skipped with Analyze, not as failure or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(
    await screen.findByRole("button", {
      name: /Marques Brownlee.*Monitoring new videos/,
    }),
  );
  expect(await screen.findByText("Skipped")).toBeTruthy();
  expect(screen.getByText(/Runs daily at 08:30/)).toBeTruthy();
  expect(screen.getByText("Excluded by your ignore rules.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Analyze this Video" }))
    .toBeTruthy();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("Check Now preserves a legal guarded state without inventing a Source Run or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(
    await screen.findByRole("button", {
      name: /Marques Brownlee.*Monitoring new videos/,
    }),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Check Now" }));
  expect(await screen.findByText(/Check Now cannot start in this local demo/))
    .toBeTruthy();
  expect(screen.queryByText(/runtime side-effect guard/i)).toBeNull();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("stopping a Source uses the legal enabled command and is not historical deletion", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(
    await screen.findByRole("button", {
      name: /Marques Brownlee.*Monitoring new videos/,
    }),
  );
  expect(await screen.findByText(/existing Intelligence remains unchanged/))
    .toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Stop future monitoring" }),
  );
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/sources/source-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ enabled: false }),
      }),
    )
  );
});

test("Topic detail waits for its typed projection instead of treating a list response as detail", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  fireEvent.click(
    await screen.findByRole("button", { name: /Topic.*Current understanding/ }),
  );
  expect(await screen.findByText("Timeline")).toBeTruthy();
  expect(screen.getByText("Related Topics")).toBeTruthy();
});

test("a new user can reach a Source setup surface with the bounded V1 controls", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/sources")) return response({ sources: [] });
      return response({});
    }),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  expect(await screen.findByText(/Set up your first Source/)).toBeTruthy();
  fireEvent.click(screen.getAllByRole("button", { name: "Add Source" })[1]);

  expect(await screen.findByRole("heading", { name: "Add a Source" }))
    .toBeTruthy();
  expect(screen.getByLabelText("Source URL")).toBeTruthy();
  expect(screen.getByLabelText("Monitor this Source")).toBeTruthy();
  expect(screen.getByLabelText("Automatic schedule")).toBeTruthy();
  expect(screen.getByLabelText("Initial history")).toBeTruthy();
  expect(screen.getByLabelText("Per-run limit")).toBeTruthy();
  expect(screen.getByLabelText("Focus")).toBeTruthy();
  expect(screen.getByLabelText("Ignore")).toBeTruthy();
  expect(screen.getByLabelText("Distillation style")).toBeTruthy();
  expect(
    screen.getByText(
      /recent existing videos are considered when this Source is first added/i,
    ),
  ).toBeTruthy();
  expect(
    screen.getByText(
      /maximum number of new videos processed in one Source Run/i,
    ),
  ).toBeTruthy();
  expect(
    Array.from(
      (screen.getByLabelText("Initial history") as HTMLSelectElement).options,
    ).map((option) => option.value),
  ).toEqual(["0", "1", "3", "5", "10"]);
  expect(
    Array.from(
      (screen.getByLabelText("Per-run limit") as HTMLSelectElement).options,
    ).map((option) => option.value),
  ).toEqual(["1", "3", "5", "10"]);
  expect(
    Array.from(
      (screen.getByLabelText("Distillation style") as HTMLSelectElement)
        .options,
    ).map((option) => option.value),
  ).toEqual([
    "BALANCED",
    "TECHNICAL_DETAIL_FIRST",
    "PRODUCT_CASE_FIRST",
    "TREND_OPINION_FIRST",
  ]);
});

test("Source setup writes only through the existing Source, policy, and schedule commands", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/sources") && init?.method === "POST") {
        return response({
          source: {
            source_id: "source-new",
            canonical_url: "https://youtube.test/new",
            enabled: true,
            processing_policy: "STANDARD_INTELLIGENCE",
            display_name: null,
            last_error: null,
          },
        });
      }
      if (input.endsWith("/sources/source-new/policy")) {
        return response({ policy: {} });
      }
      if (
        input.endsWith("/sources/source-new") && init?.method === "PATCH"
      ) return response({ source: {} });
      if (input.endsWith("/automation")) return response({ schedule: {} });
      if (input.endsWith("/sources")) return response({ sources: [] });
      return response({});
    }),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Sources" }));
  fireEvent.click(
    (await screen.findAllByRole("button", { name: "Add Source" }))[1],
  );
  fireEvent.change(screen.getByLabelText("Source URL"), {
    target: { value: "https://youtube.test/new" },
  });
  fireEvent.click(screen.getByLabelText("Monitor this Source"));
  fireEvent.change(screen.getByLabelText("Initial history"), {
    target: { value: "3" },
  });
  fireEvent.change(screen.getByLabelText("Per-run limit"), {
    target: { value: "10" },
  });
  fireEvent.change(screen.getByLabelText("Focus"), {
    target: { value: "product, AI" },
  });
  fireEvent.change(screen.getByLabelText("Ignore"), {
    target: { value: "rough" },
  });
  fireEvent.change(screen.getByLabelText("Distillation style"), {
    target: { value: "PRODUCT_CASE_FIRST" },
  });
  fireEvent.change(screen.getByLabelText("Automatic schedule"), {
    target: { value: "WEEKLY" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Add Source" }).at(-1)!,
  );
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/sources",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          url: "https://youtube.test/new",
          processing_policy: "STANDARD_INTELLIGENCE",
        }),
      }),
    )
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/sources/source-new",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({
        enabled: false,
        processing_policy: "STANDARD_INTELLIGENCE",
      }),
    }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/sources/source-new/policy",
    expect.objectContaining({
      method: "PUT",
      body: expect.stringContaining('"initial_history_count":3'),
    }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/automation",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"target_type":"SOURCE_CHECK"'),
    }),
  );
});

test("Saved, Topic, and Weekly keep trust meaning while hiding backend codes from primary reading", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Saved" }));
  expect(await screen.findByText(/no longer available as current Intelligence/))
    .toBeTruthy();
  expect(screen.queryByText("CURRENT_NOT_ACTIVE")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Weekly" }));
  expect(await screen.findByText(/What mattered · Sep 1, 2026/)).toBeTruthy();
  const summary = screen.getByText("A factual weekly change.");
  const fact = screen.getByText("Fact");
  expect(
    summary.compareDocumentPosition(fact) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).not.toBe(0);
  expect(
    screen.getByText("Evidence references").parentElement?.hasAttribute("open"),
  ).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  expect(await screen.findByText(/Some support is unavailable/)).toBeTruthy();
  expect(screen.queryByText("DEGRADED")).toBeNull();
});
