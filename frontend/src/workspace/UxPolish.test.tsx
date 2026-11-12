import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { cleanCaptionText, cleanTimedSegments } from "./captionClean";
import { CloudSpendingSettings } from "./CloudSpendingSettings";
import { runViewTransition } from "./motion";
import { UiLanguageProvider } from "./uiLanguage";

const V5_PROFILE = "moonshot-k31-system-synthesis-v5-judgment-stream-20261112";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

describe("captionClean rolling auto-caption deduplication", () => {
  it("collapses consecutive duplicate lines and progressive rollup prefixes while keeping clean text untouched", () => {
    const rolling = [
      "which reduces the uncertainty of where",
      "which reduces the uncertainty of where",
      "to search.",
      "to search.",
      "And then",
      "And then you act on that hypothesis.",
    ].join("\n");
    const result = cleanCaptionText(rolling);
    expect(result.text).toBe(
      "which reduces the uncertainty of where\nto search.\nAnd then you act on that hypothesis.",
    );
    expect(result.collapsedCount).toBeGreaterThanOrEqual(3);

    const clean = cleanCaptionText("Single clean sentence without duplicates.");
    expect(clean).toEqual({
      text: "Single clean sentence without duplicates.",
      collapsedCount: 0,
    });
  });

  it("removes carry-over duplicate lines across adjacent timed segments while preserving authoritative timestamps", () => {
    const segments = [
      { start_ms: 1000, end_ms: 3000, text: "First line\nSecond rolling line" },
      { start_ms: 3000, end_ms: 5200, text: "Second rolling line\nThird fresh line" },
      { start_ms: 5200, end_ms: 6000, text: "Third fresh line" },
    ];
    const cleaned = cleanTimedSegments(segments);
    expect(cleaned.collapsedCount).toBe(2);
    expect(cleaned.segments).toEqual([
      { start_ms: 1000, end_ms: 3000, text: "First line\nSecond rolling line" },
      { start_ms: 3000, end_ms: 5200, text: "Third fresh line" },
    ]);
  });
});

describe("Cloud profile auto-default, live distillation timer, and reading deduplication", () => {
  beforeEach(() => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content/cloud-demo";
  });

  it("auto-selects the qualified v5 profile, groups archived profiles, and ticks a live elapsed timer during confirmation", async () => {
    let resolveConfirm!: (value: unknown) => void;
    const confirmPromise = new Promise(resolve => {
      resolveConfirm = resolve;
    });

    vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body } as Response);
      if (input.endsWith("/videos")) {
        return ok({ videos: [{ video_id: "cloud-demo", provider: "YOUTUBE", channel_id: "c1", channel_name: "Demo", title: "Demo Video", source_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ", published_at: "2026-11-10T00:00:00Z", processing_status: "ANALYZED", last_updated: "2026-11-10T00:00:00Z" }] });
      }
      if (input.endsWith("/videos/cloud-demo")) {
        return ok({
          video: { video_id: "cloud-demo", provider: "YOUTUBE", channel_id: "c1", channel_name: "Demo", title: "Demo Video", source_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ", published_at: "2026-11-10T00:00:00Z", processing_status: "ANALYZED", last_updated: "2026-11-10T00:00:00Z" },
          manual_intelligence_eligible: true,
          cloud_intelligence_available: true,
          transcript: {
            status: "AVAILABLE",
            text: "Repeated auto caption line\nRepeated auto caption line\nFresh line",
            timed_segments: [
              { start_ms: 1000, end_ms: 2500, text: "Repeated auto caption line\nRepeated auto caption line" },
              { start_ms: 2500, end_ms: 4000, text: "Repeated auto caption line\nFresh line" },
            ],
          },
          note: {
            v2: {
              status: "AVAILABLE",
              method: "SOURCE_EXCERPTS",
              summary: "Excerpt dup line\nExcerpt dup line\nSecond clean line",
              core_points: [],
              timestamped_key_points: [],
              evidence_references: [],
            },
          },
          intelligence_result: {
            status: "WAITING_MODEL",
            execution_id: "wait-1",
            has_new_intelligence: false,
            intelligence_id: null,
            revision_id: null,
            updated_at: "2026-11-10T00:00:00Z",
          },
          history: [],
        });
      }
      if (input.endsWith("/cloud-intelligence/profiles")) {
        return ok({
          profiles: [
            { profile_id: "legacy", provider: "moonshot", model: "kimi-k2.6", adapter_available: true, qualified: false },
            { profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", adapter_available: true, qualified: false },
            { profile_id: V5_PROFILE, provider: "moonshot", model: "kimi-k3.1-pro", adapter_available: true, qualified: true },
          ],
        });
      }
      if (input.endsWith("/cloud-intelligence/review") && init?.method === "POST") {
        const parsed = JSON.parse(String(init.body));
        expect(parsed.profile_id).toBe(V5_PROFILE);
        return ok({
          review: {
            profile_id: V5_PROFILE,
            video_id: "cloud-demo",
            execution_id: "exec-v5",
            source_id: "src-1",
            provider: "moonshot",
            model: "kimi-k3.1-pro",
            output_language: "zh-CN",
            cost_status: "UNKNOWN",
            expires_at: "2099-01-01T00:00:00Z",
            review_hash: "a".repeat(64),
            verified_input_hash: "b".repeat(64),
            evidence_ids: ["ev-1"],
            outgoing_data: {
              video_id: "cloud-demo",
              output_language: "zh-CN",
              evidence: [{ evidence_id: "ev-1", excerpt: "Fresh line" }],
              personalization: [],
              source_focus_rules: ["AI"],
              source_ignore_rules: [],
              distillation_style: "BALANCED",
            },
            outgoing_request: {
              model: "kimi-k3.1-pro",
              max_completion_tokens: 5888,
              messages: [{ role: "user", content: 'UNTRUSTED_CURRENT_SUMMARY_BASELINE={"summary":"clean"}' }],
            },
            spending: { reserve_microunits: 1_164_029, currency: "CNY" },
            readiness: { can_confirm: true, blockers: [], budget_state: "POLICY_READY" },
          },
        });
      }
      if (input.endsWith("/cloud-intelligence/confirm") && init?.method === "POST") {
        await confirmPromise;
        return ok({ execution: { status: "SUCCEEDED" } });
      }
      if (input.endsWith("/evidence")) {
        return ok({
          evidence: [{
            evidence_id: "ev-1",
            artifact_id: "art-1",
            lineage_kind: "ORIGINAL_TRANSCRIPT",
            role: "PRIMARY_ORIGINAL",
            source_language: "en",
            language: "en",
            original_excerpt: "Evidence rolling line\nEvidence rolling line\nUnique tail",
            translated_excerpt: null,
            translated_language: null,
            translation_target_language: "zh-CN",
            translation_status: "UNAVAILABLE",
            start_ms: 1000,
            end_ms: 4000,
            created_at: "2026-11-10T00:00:00Z",
            source_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
          }],
        });
      }
      if (input.endsWith("/deep-analysis")) {
        return ok({ deep_analysis: { status: { availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", reason: null, route_id: null, model_id: null, provider_id: null, qualified: false, consent_required: false }, result: null } });
      }
      return ok({});
    }));

    render(<App />);

    // Clean reading deduplication active by default on Summary, Transcript, and Evidence, with verbatim toggle
    expect(await screen.findByText(/Excerpt dup line/)).toBeTruthy();
    const toggleButtons = await screen.findAllByRole("button", { name: /显示逐行原文/ });
    expect(toggleButtons.length).toBeGreaterThanOrEqual(2);
    fireEvent.click(toggleButtons[0]);
    expect(await screen.findByRole("button", { name: /切换精简阅读/ })).toBeTruthy();

    // Open cloud disclosure -> v5 auto-selected + optgroups rendered
    fireEvent.click(await screen.findByRole("button", { name: "查看云端洞察预览" }));
    const select = (await screen.findByRole("combobox", { name: "云端洞察模型方案" })) as HTMLSelectElement;
    await vi.waitFor(() => expect(select.value).toBe(V5_PROFILE));
    expect(select.querySelectorAll("optgroup").length).toBe(2);

    // Prepare & authorize -> live distillation progress card + ticking timer
    fireEvent.click(screen.getByRole("button", { name: "准备审核本次请求" }));
    await screen.findByText(/1\.164029/);

    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "授权本次云端执行" }));
    const progress = screen.getByTestId("distill-live-progress");
    expect(progress.textContent).toContain("0:00");
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.getByTestId("distill-live-progress").textContent).toContain("0:03");

    await act(async () => {
      resolveConfirm({});
    });
  });
});

describe("CloudSpendingSettings presets, v5 default, and quota meter", () => {
  it("defaults to v5 when policy is unset, applies quick preset chips while still requiring price acknowledgement, and renders quota bar", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    const basePrice = {
      price_hash: "a".repeat(64),
      price_date: "2026-10-29",
      profile_id: "moonshot-k31-system-synthesis-v1-20261029",
      model: "kimi-k3.1-pro",
      input_microcny_per_token_worst: 26,
      output_microcny_per_token: 68,
      billing_guarantee: false as const,
    };
    const v5Price = {
      ...basePrice,
      profile_id: V5_PROFILE,
      price_hash: "e".repeat(64),
      price_date: "2026-11-12",
    };
    let currentState: Record<string, unknown> = {
      revision: 0,
      policy: null,
      held_microunits: 2_328_058,
      held_requests: 2,
      remaining_microunits: 9_671_942,
      remaining_requests: 6,
      blocker: "CLOUD_SPENDING_POLICY_REQUIRED",
      price: basePrice,
      prices: [basePrice, v5Price],
    };
    const puts: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn(async (_path: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body));
        puts.push(body);
        currentState = {
          ...currentState,
          revision: 1,
          blocker: null,
          price: v5Price,
          policy: {
            enabled: body.enabled,
            total_microunits: 12_000_000,
            per_request_microunits: 2_000_000,
            max_calls: body.max_calls,
            price_hash: v5Price.price_hash,
          },
        };
      }
      return { ok: true, status: 200, json: async () => ({ spending_policy: currentState }) } as Response;
    }));

    render(<UiLanguageProvider><CloudSpendingSettings /></UiLanguageProvider>);
    const combobox = (await screen.findByRole("combobox", { name: "模型策略与价格参考" })) as HTMLSelectElement;
    expect(combobox.value).toBe(V5_PROFILE);

    // Click recommended preset
    fireEvent.click(screen.getByRole("button", { name: /日常推荐/ }));
    expect((screen.getByLabelText("累计预留预算（元）") as HTMLInputElement).value).toBe("12.000000");
    expect((screen.getByLabelText("单次预留上限（元）") as HTMLInputElement).value).toBe("2.000000");
    expect((screen.getByLabelText("累计请求次数上限") as HTMLInputElement).value).toBe("8");
    expect((screen.getByLabelText("启用这份有限费用策略") as HTMLInputElement).checked).toBe(true);

    const saveBtn = screen.getByRole("button", { name: "保存有限费用额度" }) as HTMLButtonElement;
    expect(saveBtn.className).toContain("button");
    expect(saveBtn.disabled).toBe(true); // Explicit acknowledgement still required!

    fireEvent.click(screen.getByLabelText("我接受此固定模型方案及价格参考，理解每次请求仍需单独确认。"));
    expect(saveBtn.disabled).toBe(false);
    fireEvent.click(saveBtn);

    await screen.findByText(/费用额度已保存/);
    expect(puts).toHaveLength(1);
    expect(puts[0].accept_price_hash).toBe(v5Price.price_hash);
    expect(within(screen.getByTestId("spending-quota-meter")).getByText(/2\.328058/)).toBeTruthy();
  });
});

describe("runViewTransition Web Platform motion reuse", () => {
  it("uses document.startViewTransition when supported and reduced-motion is off, and skips it under reduced-motion", () => {
    const originalMatchMedia = window.matchMedia;
    const startViewTransition = vi.fn((cb: () => void) => {
      cb();
      return { finished: Promise.resolve() };
    });
    Object.defineProperty(document, "startViewTransition", {
      configurable: true,
      value: startViewTransition,
    });
    window.matchMedia = vi.fn().mockImplementation(() => ({ matches: false })) as unknown as typeof window.matchMedia;

    let committed = 0;
    runViewTransition(() => {
      committed += 1;
    });
    expect(committed).toBe(1);
    expect(startViewTransition).toHaveBeenCalledTimes(1);

    // Reduced motion must bypass startViewTransition while still committing synchronously
    window.matchMedia = vi.fn().mockImplementation(() => ({ matches: true })) as unknown as typeof window.matchMedia;
    runViewTransition(() => {
      committed += 1;
    });
    expect(committed).toBe(2);
    expect(startViewTransition).toHaveBeenCalledTimes(1);

    Reflect.deleteProperty(document, "startViewTransition");
    window.matchMedia = originalMatchMedia;
  });
});
