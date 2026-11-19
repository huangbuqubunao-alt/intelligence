import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  buildMarkdownVideoNote,
  cleanTranslatedCaptionText,
  dedupeSummaryPoints,
} from "./captionClean";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

describe("Commercial reading & translation cleanup helpers", () => {
  it("strips translator meta-notes and doubled Chinese sentences while keeping source parentheses", () => {
    const persistedDirty = [
      "软件工程对智能体而言一直极具挑战性。软件工程对智能体而言一直极具挑战性。",
      "长期以来 notoriously difficult（ notoriously difficult 为原文中未翻译的英文短语，保留原样）",
      "好的，现在站在大象前面。(baaaaaaaaaaahhh!!)",
    ].join("\n");

    const cleaned = cleanTranslatedCaptionText(persistedDirty);
    expect(cleaned).not.toContain("为原文中未翻译");
    expect(cleaned).toContain("软件工程对智能体而言一直极具挑战性。");
    expect(cleaned.match(/软件工程对智能体而言一直极具挑战性。/g)).toHaveLength(1);
    expect(cleaned).toContain("(baaaaaaaaaaahhh!!)");
  });

  it("deduplicates repeated core_points and omits redundant single-sentence repeats of summary", () => {
    const zooLine = "All right, so here we are in front of the elephants.";
    expect(
      dedupeSummaryPoints(zooLine, [zooLine, zooLine, zooLine, zooLine]),
    ).toEqual([]);

    expect(
      dedupeSummaryPoints("完整摘要正文。", ["第一要点。", "第一要点。", "第二要点。"]),
    ).toEqual(["第一要点。", "第二要点。"]);
  });

  it("formats a clean Obsidian-ready Markdown note", () => {
    const md = buildMarkdownVideoNote({
      title: "Agent Engineering Deep Dive",
      channelName: "AI Lab",
      sourceUrl: "https://www.youtube.com/watch?v=IwglW_hIL_g",
      summary: "English summary.",
      chineseGuide: ["[00:03–00:37] 智能体工程的核心在于环境反馈。"],
      corePoints: ["Core point A"],
    });
    expect(md).toContain("# Agent Engineering Deep Dive");
    expect(md).toContain("智能体工程的核心在于环境反馈。");
    expect(md).toContain("Core point A");
  });
});

describe("Deep-link #Settings/models/moonshot?panel=spending & spacing fix", () => {
  it("routes ?panel=spending to Settings, expands Moonshot, scrolls CloudSpendingSettings, and spaces Remaining calls", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Settings/models/moonshot?panel=spending";

    const scrollSpy = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollSpy,
    });

    const priceHash = "e".repeat(64);
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body } as Response);
      if (input.endsWith("/settings/cloud-spending-policy")) {
        return ok({
          spending_policy: {
            revision: 1,
            policy: {
              enabled: true,
              total_microunits: 8_608_798,
              per_request_microunits: 2_000_000,
              max_calls: 7,
              price_hash: priceHash,
            },
            held_microunits: 8_608_798,
            held_requests: 7,
            remaining_microunits: 0,
            remaining_requests: 0,
            blocker: "CLOUD_BUDGET_EXHAUSTED",
            price: {
              price_hash: priceHash,
              price_date: "2026-11-12",
              profile_id: "moonshot-k31-system-synthesis-v5-judgment-stream-20261112",
              model: "kimi-k3.1-pro",
              input_microcny_per_token_worst: 26,
              output_microcny_per_token: 68,
              billing_guarantee: false,
            },
          },
        });
      }
      if (input.endsWith("/settings")) {
        return ok({
          general: { timezone: "Asia/Shanghai", output_language: "zh-CN", output_language_source: "USER", output_language_updated_at: null },
          providers: [],
          cloud_credential: { configured: true, source: "KEYCHAIN" },
        });
      }
      if (input.endsWith("/settings/local-intelligence")) {
        return ok({
          local_intelligence: {
            status: "NOT_CONFIGURED",
            etag: "b".repeat(64),
            selected_candidate_id: null,
            actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null },
            blocking_work: [],
            candidates: [{ candidate_id: "fixed-0406", model: "qwen3.5:9b-q4_K_M", runtime: "0.40.6", catalog_hash: "a".repeat(64), installation: "UNAVAILABLE" }],
          },
        });
      }
      if (input.endsWith("/settings/preferences")) return ok({ active: [], history: [] });
      if (input.endsWith("/settings/source-policy")) return ok({ policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" } });
      if (input.endsWith("/settings/resource-usage")) return ok({ usage: [] });
      if (input.endsWith("/settings/local-models")) return ok({ connection: "REACHABLE", models: [] });
      if (input.endsWith("/local/transcription/capability")) return ok({ capability: { state: "MODEL_MISSING", runtime_available: true, model_present: false } });
      if (input.endsWith("/settings/cloud-credential")) return ok({ configured: true, source: "KEYCHAIN" });
      if (input.endsWith("/settings/bigmodel-credential")) return ok({ provider: "zhipu_bigmodel", model: "glm-4.7-flash", qualification: "NOT_VERIFIED", budget: "CLOSED", configured: false, source: "NONE" });
      return ok({});
    }));

    render(<App />);
    expect(await screen.findByRole("heading", { name: "设置" })).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "云端费用额度" })).toBeTruthy();
    const quotaMeter = await screen.findByTestId("spending-quota-meter");
    expect(quotaMeter.textContent).toContain("剩余可调用次数：0");
    expect(quotaMeter.textContent).not.toContain("剩余可调用次数0");
    await waitFor(() => expect(scrollSpy).toHaveBeenCalled());
  });
});

describe("1-click local Chinese reading guide, Markdown copy, Evidence spotlight, and global Quick Import", () => {
  it("generates a zero-cloud-cost Chinese reading guide inside Summary, copies Markdown, and spotlights targeted Evidence", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Content/vid-en/Evidence/ev-2";

    let ev1Translated = true;
    let ev2Translated = false;
    const translationPosts: string[] = [];

    vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body } as Response);
      if (input.endsWith("/videos")) {
        return ok({
          videos: [{
            video_id: "vid-en",
            provider: "YOUTUBE",
            channel_id: "c1",
            channel_name: "AI Engineering",
            title: "Building Reliable Coding Agents",
            source_url: "https://www.youtube.com/watch?v=IwglW_hIL_g",
            published_at: "2026-11-10T00:00:00Z",
            processing_status: "ANALYZED",
            last_updated: "2026-11-10T00:00:00Z",
          }],
        });
      }
      if (input.endsWith("/videos/vid-en")) {
        return ok({
          video: {
            video_id: "vid-en",
            provider: "YOUTUBE",
            channel_id: "c1",
            channel_name: "AI Engineering",
            title: "Building Reliable Coding Agents",
            source_url: "https://www.youtube.com/watch?v=IwglW_hIL_g",
            published_at: "2026-11-10T00:00:00Z",
            processing_status: "ANALYZED",
            last_updated: "2026-11-10T00:00:00Z",
            language: "en",
            duration_seconds: 137,
          },
          transcript: { status: "AVAILABLE", text: "Segment one.\nSegment two." },
          note: {
            v2: {
              status: "AVAILABLE",
              method: "SOURCE_EXCERPTS",
              language: "en",
              summary: "Segment one. Segment two.",
              core_points: ["Segment one. Segment two.", "Segment one. Segment two."],
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
      if (input.endsWith("/videos/vid-en/evidence")) {
        return ok({
          evidence: [
            {
              evidence_id: "ev-1",
              artifact_id: "art-1",
              lineage_kind: "ORIGINAL_TRANSCRIPT",
              role: "PRIMARY_ORIGINAL",
              source_language: "en",
              language: "en",
              original_excerpt: "Agents need fast verification loops.",
              translated_excerpt: ev1Translated ? "智能体需要快速的验证闭环。（ fast verification 为原文中未翻译的英文短语，保留原样）" : null,
              translated_language: ev1Translated ? "zh-CN" : null,
              translation_target_language: "zh-CN",
              translation_status: ev1Translated ? "AVAILABLE" : "UNAVAILABLE",
              start_ms: 3000,
              end_ms: 15000,
              created_at: "2026-11-10T00:00:00Z",
              source_url: "https://www.youtube.com/watch?v=IwglW_hIL_g",
            },
            {
              evidence_id: "ev-1-dup",
              artifact_id: "art-1b",
              lineage_kind: "ORIGINAL_TRANSCRIPT",
              role: "SUPPORTING",
              source_language: "en",
              language: "en",
              original_excerpt: "Agents need fast verification loops.",
              translated_excerpt: null,
              translated_language: null,
              translation_target_language: "zh-CN",
              translation_status: "UNAVAILABLE",
              start_ms: 3000,
              end_ms: 15000,
              created_at: "2026-11-10T00:00:00Z",
              source_url: "https://www.youtube.com/watch?v=IwglW_hIL_g",
            },
            {
              evidence_id: "ev-2",
              artifact_id: "art-2",
              lineage_kind: "ORIGINAL_TRANSCRIPT",
              role: "PRIMARY_ORIGINAL",
              source_language: "en",
              language: "en",
              original_excerpt: "Deterministic tests catch regressions early.",
              translated_excerpt: ev2Translated ? "确定性测试能够尽早捕获回归缺陷。" : null,
              translated_language: ev2Translated ? "zh-CN" : null,
              translation_target_language: "zh-CN",
              translation_status: ev2Translated ? "AVAILABLE" : "UNAVAILABLE",
              start_ms: 16000,
              end_ms: 32000,
              created_at: "2026-11-10T00:00:00Z",
              source_url: "https://www.youtube.com/watch?v=IwglW_hIL_g",
            },
          ],
        });
      }
      if (input.endsWith("/videos/vid-en/evidence/ev-2/translation") && init?.method === "POST") {
        translationPosts.push(input);
        ev2Translated = true;
        return ok({
          evidence_id: "ev-2",
          translated_excerpt: "确定性测试能够尽早捕获回归缺陷。",
          translated_language: "zh-CN",
          translation_target_language: "zh-CN",
          translation_status: "AVAILABLE",
        });
      }
      if (input.endsWith("/deep-analysis")) {
        return ok({
          deep_analysis: {
            status: { availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", qualified: false, consent_required: false },
            result: null,
          },
        });
      }
      return ok({});
    }));

    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    render(<App />);

    // Evidence spotlight on ev-2
    const targetedCard = await screen.findByText("当前定位引用");
    expect(targetedCard.closest("#content-evidence-ev-2")?.className).toContain("is-targeted-evidence");

    // Cleaned persisted meta-note on ev-1
    expect(document.body.textContent).toContain("智能体需要快速的验证闭环。");
    expect(document.body.textContent).not.toContain("为原文中未翻译");

    // 1-click generate remaining Chinese reading guide (only translates untranslated ev-2!)
    const guideBtn = await screen.findByRole("button", { name: /一键生成中文导读|补全中文导读/ });
    await user.click(guideBtn);
    await waitFor(() => expect(translationPosts).toEqual(["/api/v1/videos/vid-en/evidence/ev-2/translation"]));
    const summarySection = document.getElementById("section-summary")!;
    expect(within(summarySection).getByText(/确定性测试能够尽早捕获回归缺陷。/)).toBeTruthy();
    expect(summarySection.querySelectorAll(".chinese-guide-list > li")).toHaveLength(2);

    // Copy Markdown note
    const copyBtn = screen.getByRole("button", { name: /复制 Markdown 笔记/ });
    await user.click(copyBtn);
    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText.mock.calls[0][0]).toContain("确定性测试能够尽早捕获回归缺陷。");

    // Global Quick Import button in utility dock opens shared Add dialog from #Home
    await act(async () => {
      location.hash = "#Home";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    const quickImport = await screen.findByRole("button", { name: "快捷导入" });
    await user.click(quickImport);
    expect(await screen.findByRole("dialog", { name: "添加内容" })).toBeTruthy();
  });
});
