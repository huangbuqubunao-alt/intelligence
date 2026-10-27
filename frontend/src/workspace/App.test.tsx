import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App, intelligenceValidationCopy } from "./App";
import { apiProxyTarget } from "../api/proxy";

test.each(["evidence-1", "foreign-evidence"])("Content refresh re-resolves only its current Evidence identity: %s", async (target) => {
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/video-1/evidence")) return response({ evidence: [{
      evidence_id: "evidence-1", artifact_id: "artifact-1", locator_type: "TEXT_RANGE",
      start_line: 2, end_line: 4, start_ms: null, end_ms: null,
      source_language: "en", language: "en", original_excerpt: "Current resolver-verified text range.",
      lineage_kind: "ORIGINAL_TRANSCRIPT", role: "PRIMARY_ORIGINAL", translated_excerpt: null,
      translated_language: null, translation_target_language: "en", source_url: null,
    }] });
    return defaultFetch(path, init);
  }));
  const scroll = vi.fn();
  const originalScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: scroll });
  location.hash = `#Content/video-1/Evidence/${target}`;
  const view = render(<App />);
  await screen.findByText("Current resolver-verified text range.");
  if (target === "evidence-1") {
    await waitFor(() => expect(document.activeElement?.id).toBe("content-evidence-evidence-1"));
    expect(scroll).toHaveBeenCalledWith({ block: "center" });
    view.unmount();
    render(<App />);
    await waitFor(() => expect(document.activeElement?.id).toBe("content-evidence-evidence-1"));
  } else {
    expect(document.getElementById("content-evidence-foreign-evidence")).toBeNull();
    expect(scroll).not.toHaveBeenCalled();
  }
  expect(await screen.findByText("Lines 2–4")).toBeTruthy();
  if (originalScroll) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", originalScroll);
  else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
});

test("Intelligence text Evidence displays real lines and links its internal Evidence identity", async () => {
  const defaultFetch = globalThis.fetch;
  const local = { ...intelligence, card: { ...intelligence.card, original_video_url: null, source_url: null,
    evidence_links: [{ ...intelligence.card.evidence_links[0], locator_type: "TEXT_RANGE", start_ms: null,
      end_ms: null, start_line: 2, end_line: 4 }] } };
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/intelligence")) return response({ intelligence: [local], activity: [] });
    return defaultFetch(path, init);
  }));
  location.hash = "Intelligence";
  render(<App />);
  expect(await screen.findByText("Lines 2–4")).toBeTruthy();
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Open Content" })));
  expect(location.hash).toBe("#Content/video-1/Evidence/evidence-1");
});

test.each(["en", "zh-CN"])("Text Evidence retains honest missing-position copy in %s", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  const defaultFetch = globalThis.fetch;
  const local = { ...intelligence, card: { ...intelligence.card, original_video_url: null,
    evidence_links: [{ ...intelligence.card.evidence_links[0], locator_type: "TEXT_RANGE", start_ms: null, end_ms: null }] } };
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/intelligence")) return response({ intelligence: [local], activity: [] });
    return defaultFetch(path, init);
  }));
  location.hash = "Intelligence";
  render(<App />);
  expect(await screen.findByText(language === "en" ? "Text position unavailable" : "文字位置不可用")).toBeTruthy();
  expect(document.body.textContent).not.toContain("null–null");
});

test("Chinese Settings edits global interests through existing authority", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const defaultFetch = globalThis.fetch;
  const writes: { path: string; data: Record<string, unknown> }[] = [];
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (init?.method === "PUT") {
      writes.push({ path, data: JSON.parse(String(init.body)) });
      return response({});
    }
    return defaultFetch(path, init);
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(await screen.findByRole("button", { name: "编辑兴趣" }));
  fireEvent.click(screen.getByRole("button", { name: "添加关注词条" }));
  fireEvent.change(await screen.findByLabelText("我重点关注"), { target: { value: "AI Agent" } });
  fireEvent.click(screen.getByRole("button", { name: "添加关注词条" }));
  fireEvent.change(screen.getByLabelText("我重点关注 2"), { target: { value: "大模型" } });
  fireEvent.click(screen.getByRole("button", { name: "添加忽略词条" }));
  fireEvent.change(screen.getByLabelText("少看／忽略"), { target: { value: "重复新闻" } });
  fireEvent.click(screen.getByRole("button", { name: "保存偏好" }));
  await waitFor(() => expect(writes[0]?.data.focus_rules).toEqual(["AI Agent", "大模型"]));
  expect(writes[0].path).toMatch(/settings\/source-policy$/);
  expect(writes[0].data.ignore_rules).toEqual(["重复新闻"]);
  expect(writes.some(write => /confirm|deep-analysis/.test(write.path))).toBe(false);
});

test("Settings saves discovered candidate and secure credential without generation", async () => {
  const defaultFetch = globalThis.fetch;
  const writes: { path: string; data: Record<string, unknown> }[] = [];
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/settings/local-models")) return response({ connection: "REACHABLE", models: [{ model: "candidate:7b", qualified: false }] });
    if (init?.method === "PUT") {
      writes.push({ path, data: JSON.parse(String(init.body)) });
      return response({ configured: true, source: "KEYCHAIN" });
    }
    return defaultFetch(path, init);
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.change(await screen.findByLabelText("Discovered candidate"), { target: { value: "candidate:7b" } });
  fireEvent.click(screen.getByRole("button", { name: "Save candidate preference" }));
  await waitFor(() => expect(writes[0]?.data).toEqual({ provider: "Local", model: "candidate:7b" }));
  fireEvent.click(screen.getByText("Moonshot / kimi-k2.6 credential setup"));
  fireEvent.change(await screen.findByLabelText("Moonshot API key"), { target: { value: "synthetic-closure-ui" } });
  fireEvent.click(screen.getByRole("button", { name: "Save Moonshot key securely" }));
  await screen.findByText("Credential saved in macOS Keychain. Every cloud execution still needs separate consent.");
  expect((screen.getByLabelText("Moonshot API key") as HTMLInputElement).value).toBe("");
  expect(JSON.stringify(localStorage)).not.toContain("synthetic-closure-ui");
  expect(writes.map(write => write.path)).toEqual(["/api/v1/settings/model-preference", "/api/v1/settings/cloud-credential"]);
});

test("Chinese interest validation never displays raw backend prose", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => init?.method === "PUT"
    ? Promise.resolve({ ok: false, status: 422, json: async () => ({ error: { code: "VALIDATION_ERROR", message: "Backend validation failed." } }) })
    : defaultFetch(path, init)));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(await screen.findByRole("button", { name: "编辑兴趣" }));
  fireEvent.click(await screen.findByRole("button", { name: "保存偏好" }));
  expect((await screen.findByRole("alert")).textContent).toContain("偏好未能保存");
  expect(screen.queryByText("Backend validation failed.")).toBeNull();
});

it("keeps Research accessible when the independent Intelligence list fails", async () => {
  location.hash = "Intelligence";
  vi.stubGlobal("fetch", vi.fn((path: string) => {
    if (path.endsWith("/intelligence")) return Promise.resolve({ ok: false, json: async () => ({ error: { code: "UNAVAILABLE", message: "List unavailable" } }) });
    if (path.endsWith("/saved-intelligence")) return response({ saved: [] });
    return response({ research: [], total: 0, offset: 0, limit: 25 });
  }));
  render(<App />);
  await screen.findByText("List unavailable");
  fireEvent.click(screen.getByRole("button", { name: /^Research$/ }));
  expect(await screen.findByText("No Research yet. Start with a question and selected library Content.")).toBeTruthy();
  expect(within(screen.getByRole("navigation")).getAllByRole("button")).toHaveLength(6);
});

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
    original_video_url: "https://www.youtube.com/watch?v=video-1",
    evidence_links: [{
      evidence_id: "evidence-1",
      artifact_id: "artifact-1",
      start_ms: 1000,
      end_ms: 2000,
      language: "en",
      lineage_kind: "ORIGINAL_TRANSCRIPT",
      role: "PRIMARY_ORIGINAL",
      original_excerpt:
        "Attention lets each token weigh relevant context from other tokens.",
      translated_excerpt: null,
      translated_language: null,
      stance: "contradicting",
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

test.each(["en", "zh-CN"])("%s source excerpts do not claim the generation language", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content/video-1";
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/video-1")) return response({
      video: { video_id: "video-1", provider: "YOUTUBE", processing_status: "ORGANIZED", title: "Chinese source" },
      transcript: { status: "AVAILABLE", text: "这是原始中文字幕。" },
      note: { v2: { status: "AVAILABLE", method: "SOURCE_EXCERPTS", language: "en-US", summary: "保留原文摘录。" } },
      intelligence_result: { status: "NOT_PROCESSED" }, history: [],
    });
    return defaultFetch(path, init);
  }));
  render(<App />);
  await screen.findByText("保留原文摘录。");
  expect(screen.queryByText("en-US")).toBeNull();
  expect(screen.getByText(language === "zh-CN" ? "保留原文语言" : "Original source language (unchanged)")).toBeTruthy();
});

test.each(["en", "zh-CN"])("%s model Summary keeps its actual generation language", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content/video-1";
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/video-1")) return response({
      video: { video_id: "video-1", provider: "YOUTUBE", processing_status: "ORGANIZED", title: "Chinese source" },
      transcript: { status: "AVAILABLE", text: "这是原始中文字幕。" },
      note: { v2: { status: "AVAILABLE", language: "en-US", summary: "An English model Summary." } },
      intelligence_result: { status: "NOT_PROCESSED" }, history: [],
    });
    return defaultFetch(path, init);
  }));
  render(<App />);
  await screen.findByText("An English model Summary.");
  expect(screen.getByText("en-US")).toBeTruthy();
  expect(screen.queryByText("Original source language (unchanged)")).toBeNull();
  expect(screen.queryByText("保留原文语言")).toBeNull();
});

test.each([
  ["en", false], ["en", true], ["zh-CN", false], ["zh-CN", true],
])("%s cancels only the selected wait and reads true backup readiness (other work: %s)", async (language, otherWork) => {
  localStorage.setItem("yia.ui-language", String(language));
  location.hash = "Content/video-1";
  const defaultFetch = globalThis.fetch;
  let cancelled = false;
  const commands: { path: string; body: object }[] = [];
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (init?.method === "POST" && path.endsWith("/intelligence/cancel")) {
      commands.push({ path, body: JSON.parse(String(init.body)) });
      cancelled = true;
      return response({ execution: { status: "CANCELLED" } });
    }
    if (path.endsWith("/videos/video-1")) return response({
      video: { video_id: "video-1", title: "Cancellation Content", provider: "LOCAL", processing_status: "READY" },
      transcript: { status: "AVAILABLE", text: "Original source remains exact." },
      note: { v2: { status: "AVAILABLE", summary: "Preserved Summary." } },
      intelligence_result: { status: cancelled ? "CANCELLED" : "WAITING_MODEL", execution_id: "wait-1" },
      waiting_model_executions: cancelled ? [] : [{ execution_id: "wait-1", can_cancel: true, updated_at: "2026-10-11T00:00:00Z" }],
      manual_intelligence_eligible: true, cloud_intelligence_available: false, history: [],
    });
    if (path.endsWith("/backup-restore/status")) return response({ status: {
      ready: cancelled && !otherWork, reasons: !cancelled || otherWork ? ["DISTILLATION_ACTIVE"] : [],
      restore_pending: false, last_restore: null,
    } });
    return defaultFetch(path, init);
  }));
  render(<App />);
  const chinese = language === "zh-CN";
  expect(await screen.findByText(chinese ? "当前没有合格的洞察模型。" : "No qualified Intelligence model is currently available.")).toBeTruthy();
  expect(screen.getByRole("button", { name: chinese ? "提炼为洞察" : "Extract Intelligence" }).hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: chinese ? "取消本次提炼" : "Cancel this extraction" }));
  expect(await screen.findByText(chinese
    ? "本次提炼已取消，没有生成洞察。原 Content、字幕、摘要和 Evidence 均保留。"
    : "Extraction cancelled. No Intelligence was generated by this task. Original Content, transcript, Summary and Evidence are preserved.")).toBeTruthy();
  expect(screen.getByText("Original source remains exact.")).toBeTruthy();
  expect(screen.getByText("Preserved Summary.")).toBeTruthy();
  expect(commands).toEqual([{ path: "/api/v1/videos/video-1/intelligence/cancel", body: { execution_id: "wait-1" } }]);
  fireEvent.click(screen.getByRole("button", { name: chinese ? "设置" : "Settings" }));
  await waitFor(() => expect(screen.getByRole("button", { name: chinese ? "创建备份" : "Create Backup" }).hasAttribute("disabled")).toBe(Boolean(otherWork)));
});

test.each(["en", "zh-CN"])("%s backup explains an unfinished extraction without claiming model execution", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Settings";
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/backup-restore/status")) return response({ status: {
      ready: false, reasons: ["DISTILLATION_ACTIVE"], restore_pending: false, last_restore: null,
    } });
    return defaultFetch(path, init);
  }));
  render(<App />);
  const chinese = language === "zh-CN";
  expect(await screen.findByText(chinese ? /有一个提炼任务尚未结束/ : /an Intelligence extraction has not finished/)).toBeTruthy();
  expect(screen.queryByText(chinese ? /提炼任务仍在执行/ : /a distillation is still running/)).toBeNull();
  expect(screen.getByRole("button", { name: chinese ? "创建备份" : "Create Backup" }).hasAttribute("disabled")).toBe(true);
});

beforeEach(() => {
  localStorage.removeItem("intelligence.onboarding.completed.v1");
  location.hash = "";
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/settings/local-intelligence")) return response({ local_intelligence: { status: "NOT_CONFIGURED", etag: "b".repeat(64), selected_candidate_id: null,
        actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null }, blocking_work: [],
        candidates: [{ candidate_id: "fixed-0406", model: "qwen3.5:9b-q4_K_M", runtime: "0.40.6", catalog_hash: "a".repeat(64), installation: "READY" }] } });
      if (input.endsWith("/knowledge-delta")) {
        return response({ knowledge_delta: {
          window_start: "2026-09-26T08:00:00.000000Z", window_end: "2026-10-03T08:00:00.000000Z",
          timezone: "Asia/Shanghai", status: "available", detail_limit: 2,
          categories: ["content_completed", "intelligence_added", "intelligence_revised", "topic_updated", "source_health"]
            .map(kind => ({ kind, status: "available", count: 0, items: [] })),
        } });
      }
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
      if (input.endsWith("/videos/video-1")) {
        return response({
          video: {
            video_id: "video-1",
            channel_id: "channel-1",
            channel_name: "3Blue1Brown",
            title: "Transformers, the tech behind LLMs | Deep Learning Chapter 5",
            source_url: "https://youtube.test/video",
            published_at: "2026-09-01T00:00:00Z",
            processing_status: "TRANSCRIPT_READY",
            last_updated: "2026-09-01T00:00:00Z",
          },
          transcript: {
            status: "AVAILABLE",
            text: "Attention lets each token weigh relevant context from other tokens.",
            created_at: "2026-09-01T00:00:00Z",
          },
          note: {
            v1: { status: "UNAVAILABLE", code: "NOTE_REF_NOT_PERSISTED" },
            v2: { status: "UNAVAILABLE", code: "NOTE_V2_UNAVAILABLE" },
          },
          intelligence_result: {
            status: "NOT_PROCESSED",
            execution_id: null,
            has_new_intelligence: null,
            intelligence_id: null,
            revision_id: null,
            updated_at: null,
          },
          history: [],
        });
      }
      if (input.endsWith("/videos")) {
        return response({
          videos: [{
            video_id: "video-1",
            channel_id: "channel-1",
            channel_name: "3Blue1Brown",
            title: "Transformers, the tech behind LLMs | Deep Learning Chapter 5",
            source_url: "https://youtube.test/video",
            published_at: "2026-09-01T00:00:00Z",
            processing_status: "TRANSCRIPT_READY",
            last_updated: "2026-09-01T00:00:00Z",
          }],
        });
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
          source_run: {
            run_id: "run-check-now",
            state: "QUEUED",
            attention_reason: null,
            trigger: "MANUAL_CHECK_NOW",
            updated_at: "2026-09-01T00:00:00Z",
          },
          message: "Source Run submission is durably persisted.",
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
          general: {
            timezone: "Asia/Shanghai",
            output_language: "zh-CN",
            output_language_source: "BOOTSTRAP_DEFAULT",
            output_language_updated_at: null,
          },
          providers: [{
            provider: "moonshot",
            model: "kimi-k2.6",
            adapter_available: true,
            authorized: false,
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

test("UI language defaults to Chinese and a saved English choice survives remount", async () => {
  localStorage.removeItem("yia.ui-language");
  const first = render(<App />);
  expect(screen.getByRole("button", { name: "关注" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(await screen.findByRole("button", { name: "编辑语言" }));
  const uiLanguage = await screen.findByLabelText("界面语言");
  expect((uiLanguage as HTMLSelectElement).value).toBe("zh-CN");
  fireEvent.change(uiLanguage, { target: { value: "en" } });
  fireEvent.click(screen.getByRole("button", { name: "保存语言" }));
  await screen.findByRole("button", { name: "Following" });
  expect(screen.getByRole("button", { name: "Following" })).toBeTruthy();
  expect(localStorage.getItem("yia.ui-language")).toBe("en");
  first.unmount();
  render(<App />);
  expect(screen.getByRole("button", { name: "Settings" })).toBeTruthy();
  fireEvent.click(await screen.findByRole("button", { name: "Edit language" }));
  expect((await screen.findByLabelText("Interface language") as HTMLSelectElement).value).toBe("en");
});

test("Chinese Settings separates editable languages from factual and read-only status", async () => {
  localStorage.removeItem("yia.ui-language");
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(await screen.findByRole("button", { name: "编辑语言" }));
  expect((await screen.findByLabelText("界面语言") as HTMLSelectElement).value).toBe("zh-CN");
  expect((screen.getByLabelText("默认输出语言") as HTMLSelectElement).value).toBe("zh-CN");
  expect(screen.queryByLabelText("来源语言")).toBeNull();
  expect(screen.getByText(/来源语言自动识别/)).toBeTruthy();
  expect(screen.getByText("偏好记录（只读）")).toBeTruthy();
  expect(screen.getByText("来源策略（此处只读）")).toBeTruthy();
  expect(screen.getByText("模型与费用（只读）")).toBeTruthy();
  expect(screen.getByText("备份与恢复")).toBeTruthy();
  expect(screen.getByRole("button", { name: "创建备份" })).toBeTruthy();
});

test("Chinese Settings reports a qualified cloud model with a blocked runtime credential", async () => {
  localStorage.removeItem("yia.ui-language");
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/settings")) return response({
      general: { timezone: "Asia/Shanghai", output_language: "zh-CN", output_language_source: "USER_PREFERENCE", output_language_updated_at: null },
      providers: [{
        provider: "moonshot", model: "kimi-k2.6", adapter_available: true,
        configured: false, credential_status: "BLOCKED", authorized: false,
        production_eligible: false, qualification_status: "QUALIFIED",
        scope: "V1_VIDEO_DISTILLATION_ONLY",
        reason: "Cloud Intelligence requires qualification and an available backend credential.",
      }],
    });
    return defaultFetch(input, init);
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  expect(await screen.findByText(/运行环境缺少凭据/)).toBeTruthy();
  expect(screen.getByText(/每次云端执行仍需单独同意/)).toBeTruthy();
});

test("Chinese Following explains discovery-only state and the insight processing choice", async () => {
  localStorage.removeItem("yia.ui-language");
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input.endsWith("/sources/source-1")) return response({
      source: {
        source_id: "source-1", channel_id: "channel-1", canonical_url: "https://youtube.test/source",
        enabled: true, processing_policy: "DISCOVER_ONLY", last_error: null,
      },
      policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" },
      schedules: [], recent_videos: [], source_runs: [],
    });
    if (input.endsWith("/sources")) return response({ sources: [{
      source_id: "source-1", channel_id: "channel-1", canonical_url: "https://youtube.test/source",
      enabled: true, processing_policy: "DISCOVER_ONLY", last_error: null,
    }] });
    return response({});
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  fireEvent.click(await screen.findByRole("button", { name: /channel-1/ }));
  expect(await screen.findByText(/仅发现新视频.*尚未检查/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "编辑设置" }));
  expect(screen.getByRole("option", { name: "从相关视频中提炼洞察" })).toBeTruthy();
  expect(screen.getByText(/不是每个视频都会产生洞察/)).toBeTruthy();
});

test.each([
  ["SUCCEEDED_NO_NEW_INTELLIGENCE", false, /本次内容没有形成值得长期保留的新洞察/],
  ["WAITING_MODEL", false, /服务商或运行环境中的凭据不可用/],
  ["WAITING_MODEL", true, /请先查看数据与费用说明并确认本次执行/],
  ["REJECTED_EVIDENCE", false, /请检查原始字幕和来源/],
] as const)("Chinese Content explains %s with cloud availability %s", async (status, cloudAvailable, expected) => {
  localStorage.removeItem("yia.ui-language");
  const fetchMock = vi.fn((input: string, _init?: RequestInit) => {
    if (input.endsWith("/videos/video-1/evidence")) return response({ evidence: [{
      evidence_id: "evidence-1", artifact_id: "artifact-1", source_language: "en",
      lineage_kind: "ORIGINAL_TRANSCRIPT", role: "PRIMARY_ORIGINAL",
      original_excerpt: "The original English Evidence stays unchanged.",
      translated_excerpt: null, translated_language: null,
      translation_target_language: "zh-CN", start_ms: 1000, end_ms: 2000,
      created_at: "2026-09-01T00:00:00Z",
    }] });
    if (input.endsWith("/videos/video-1")) return response({
      video: {
        video_id: "video-1", channel_id: "channel-1", channel_name: "English source",
        title: "A real content title", source_url: "https://youtube.test/video-1",
        published_at: "2026-09-01T00:00:00Z", processing_status: "COMPLETE",
        last_updated: "2026-09-01T00:00:00Z",
      },
      cloud_intelligence_available: cloudAvailable,
      transcript: { status: "AVAILABLE", text: "The original English transcript stays unchanged." },
      note: { v2: { status: "AVAILABLE", language: "zh-CN", summary: "中文摘要。" } },
      intelligence_result: {
        status, execution_id: null, has_new_intelligence: false,
        intelligence_id: null, revision_id: null, updated_at: null,
      },
      history: [],
    });
    if (input.endsWith("/videos")) return response({ videos: [{
      video_id: "video-1", channel_id: "channel-1", channel_name: "English source",
      title: "A real content title", source_url: "https://youtube.test/video-1",
      published_at: "2026-09-01T00:00:00Z", processing_status: "COMPLETE",
      last_updated: "2026-09-01T00:00:00Z",
    }] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(await screen.findByRole("button", { name: /A real content title/ }));
  expect(await screen.findByText(expected)).toBeTruthy();
  expect(screen.getByText("The original English transcript stays unchanged.")).toBeTruthy();
  expect(await screen.findByText("The original English Evidence stays unchanged.")).toBeTruthy();
  expect(screen.getByText(/来源语言: en/)).toBeTruthy();
  expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

test("Chinese Content explains an invalid local Summary without leaking job codes", async () => {
  localStorage.removeItem("yia.ui-language");
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (input.endsWith("/videos/video-1")) return response({
      video: {
        video_id: "video-1", channel_id: "channel-1", channel_name: "English source",
        title: "An English video", source_url: "https://youtube.test/video-1",
        published_at: "2026-09-01T00:00:00Z", processing_status: "SCORED",
        last_updated: "2026-09-01T00:00:00Z",
      },
      transcript: { status: "AVAILABLE", text: "Original English transcript." },
      note: { v2: { status: "UNAVAILABLE", code: "CURRENT_SUMMARY_MISSING" } },
      intelligence_result: {
        status: "NOT_PROCESSED", execution_id: null, has_new_intelligence: null,
        intelligence_id: null, revision_id: null, updated_at: null,
      },
      history: [{
        timestamp: "2026-09-01T00:00:00Z", type: "JOB_STATUS", status: "FAILED_FINAL",
        summary: "ANALYSIS processing is FAILED_FINAL.", code: "INVALID_RESPONSE",
        context: { stage: "ANALYSIS" },
      }],
    });
    if (input.endsWith("/videos")) return response({ videos: [{
      video_id: "video-1", channel_id: "channel-1", channel_name: "English source",
      title: "An English video", source_url: "https://youtube.test/video-1",
      published_at: "2026-09-01T00:00:00Z", processing_status: "SCORED",
      last_updated: "2026-09-01T00:00:00Z",
    }] });
    return response({});
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(await screen.findByRole("button", { name: /An English video/ }));
  expect(await screen.findByText(/本地摘要未通过输出检查/)).toBeTruthy();
  expect(screen.getByText("尚未处理")).toBeTruthy();
  expect(screen.getAllByText(/2026年9月1日/).length).toBeGreaterThan(0);
  expect(screen.getByText("Original English transcript.")).toBeTruthy();
  expect(screen.queryByText(/FAILED_FINAL|INVALID_RESPONSE/)).toBeNull();
});

test("Content shows explicit no-new Intelligence success without confidence", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string) => {
    if (input.endsWith("/videos/video-1")) {
      return response({
        video: {
          video_id: "video-1",
          channel_id: "channel-1",
          channel_name: "Fixture channel",
          title: "Evidence-led product lesson",
          source_url: "https://youtube.test/video-1",
          published_at: "2026-09-01T00:00:00Z",
          processing_status: "COMPLETE",
          last_updated: "2026-09-01T00:00:00Z",
        },
        transcript: { status: "AVAILABLE", text: "Original transcript evidence." },
        note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
        intelligence_result: {
          status: "SUCCEEDED_NO_NEW_INTELLIGENCE",
          execution_id: "exec-zero",
          has_new_intelligence: false,
          intelligence_id: null,
          revision_id: null,
          updated_at: "2026-09-01T00:00:00Z",
        },
        history: [],
      });
    }
    if (input.endsWith("/videos")) {
      return response({ videos: [{
        video_id: "video-1", channel_id: "channel-1", channel_name: "Fixture channel",
        title: "Evidence-led product lesson", source_url: "https://youtube.test/video-1",
        published_at: "2026-09-01T00:00:00Z", processing_status: "COMPLETE",
        last_updated: "2026-09-01T00:00:00Z",
      }] });
    }
    return response({});
  }));

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(await screen.findByRole("button", { name: /Evidence-led product lesson/ }));

  expect(await screen.findByText("Intelligence result")).toBeTruthy();
  expect(screen.getByText(/Analysis complete — no new Intelligence/)).toBeTruthy();
  expect(screen.getByText(/nothing reached the threshold for adding new Intelligence/i)).toBeTruthy();
  expect(screen.queryByText(/\b\d+%\b/)).toBeNull();
  expect(screen.queryByText(/low confidence|medium confidence|high confidence/i)).toBeNull();
});

test("local Intelligence pause discloses cloud scope without sending data", async () => {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/videos/video-1")) {
      return response({
        video: {
          provider: "YOUTUBE", video_id: "video-1", channel_id: "channel-1", channel_name: "Fixture channel",
          title: "Local-first Content", source_url: "https://youtube.test/video-1",
          published_at: "2026-09-01T00:00:00Z", processing_status: "COMPLETE",
          last_updated: "2026-09-01T00:00:00Z",
        },
        transcript: { status: "AVAILABLE", text: "Original transcript." },
        note: { v2: { status: "AVAILABLE", language: "zh-CN", summary: "Local Summary." } },
        intelligence_result: {
          status: "WAITING_MODEL", execution_id: "local-waiting", has_new_intelligence: false,
          intelligence_id: null, revision_id: null, updated_at: "2026-09-01T00:00:00Z",
        },
        history: [],
      });
    }
    if (input.endsWith("/videos")) {
      return response({ videos: [{
        provider: "YOUTUBE", video_id: "video-1", channel_id: "channel-1", channel_name: "Fixture channel",
        title: "Local-first Content", source_url: "https://youtube.test/video-1",
        published_at: "2026-09-01T00:00:00Z", processing_status: "COMPLETE",
        last_updated: "2026-09-01T00:00:00Z",
      }] });
    }
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(await screen.findByRole("button", { name: /Local-first Content/ }));
  expect(await screen.findByText("Local Summary.")).toBeTruthy();
  expect(screen.getByText(/current local model cannot reliably create high-quality Intelligence/i)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Review cloud Intelligence" }));
  expect(screen.getByText(/Only bounded, verified Evidence excerpts/)).toBeTruthy();
  expect(screen.getByText(/Preparing a review does not create a task/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Prepare one request for review" })).toBeTruthy();
  expect(document.body.textContent).not.toContain("¥6.50");
  expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});
afterEach(() => vi.unstubAllGlobals());

test("PO demo can direct the development proxy to its owned loopback API", () => {
  expect(apiProxyTarget("http://127.0.0.1:8766")).toBe("http://127.0.0.1:8766");
});

test.each([
  ["NEW", "New Intelligence. It has not reached a confirmed validation state yet."],
  ["PENDING_CONFIRMATION", "Still needs validation. Review the cited Evidence before relying on it."],
  ["CONFIRMED", "Current trusted state: confirmed."],
  ["DISPUTED", "Still needs validation. Conflicting Evidence or interpretation remains unresolved."],
  ["UPDATED", "Updated. This is the current revision; older revisions are historical."],
  ["", "Validation state is unavailable."],
])("maps %s to honest validation posture copy", (state, expected) => {
  expect(intelligenceValidationCopy(state)).toBe(expected);
});

test("frozen product IA exposes exactly its six first-level destinations", async () => {
  render(<App />);
  await screen.findByText("What matters now");
  expect(
    screen.getAllByRole("button", {
      name: /^(Home|Following|Content|Intelligence|Topics|Settings)$/,
    }),
  ).toHaveLength(6);
  for (
    const legacy of [
      "Videos",
      "Dashboard",
      "Sources",
      "Investigations",
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

test("Content renders only the explicit current verified Summary and its trusted timed Evidence", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/videos/video-1")) {
        return response({
          video: {
            video_id: "video-1",
            channel_id: "channel-1",
            channel_name: "Fixture channel",
            title: "Evidence-led product lesson",
            source_url: "https://www.youtube.com/watch?v=video-1",
            published_at: "2026-09-01T00:00:00Z",
            processing_status: "COMPLETE",
            last_updated: "2026-09-01T00:00:00Z",
          },
          transcript: {
            status: "AVAILABLE",
            text: "Original transcript evidence.",
            created_at: "2026-09-01T00:00:00Z",
          },
          note: {
            v1: { status: "UNAVAILABLE", code: "NOTE_REF_NOT_PERSISTED" },
            v2: {
              status: "AVAILABLE",
              note_identity: "note-1",
              result_identity: "result-1",
              language: "zh-CN",
              summary: "这是当前正式摘要。",
              core_points: ["第一点。", "第二点。"],
              timestamped_key_points: [{
                text: "第一点。",
                start_seconds: 12,
                end_seconds: 18,
                evidence_ids: ["e1"],
              }],
              evidence_references: [{
                evidence_id: "e1",
                source: "transcript",
                excerpt: "Original transcript evidence.",
                start_seconds: 12,
                end_seconds: 18,
              }],
            },
          },
          intelligence_result: {
            status: "NOT_PROCESSED",
            execution_id: null,
            has_new_intelligence: null,
            intelligence_id: null,
            revision_id: null,
            updated_at: null,
          },
          history: [],
        });
      }
      if (input.endsWith("/videos")) {
        return response({
          videos: [{
            video_id: "video-1",
            channel_id: "channel-1",
            channel_name: "Fixture channel",
            title: "Evidence-led product lesson",
            source_url: "https://www.youtube.com/watch?v=video-1",
            published_at: "2026-09-01T00:00:00Z",
            processing_status: "COMPLETE",
            last_updated: "2026-09-01T00:00:00Z",
          }],
        });
      }
      return response({});
    }),
  );

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(
    await screen.findByRole("button", { name: /Evidence-led product lesson/ }),
  );
  expect(await screen.findByText("这是当前正式摘要。")).toBeTruthy();
  expect(screen.getByText("Timestamped key points")).toBeTruthy();
  expect(screen.getByRole("link", { name: "0:12" }).getAttribute("href"))
    .toContain("t=12");
  const evidenceDetails = screen.getByText("Evidence references").closest("details");
  expect(evidenceDetails).toBeInstanceOf(HTMLDetailsElement);
  if (!(evidenceDetails instanceof HTMLDetailsElement)) {
    throw new Error("Evidence references must render inside details.");
  }
  fireEvent.click(screen.getByText("Evidence references"));
  expect(within(evidenceDetails).getByText("Original transcript evidence."))
    .toBeTruthy();
});

test("Content Evidence supports translated, bilingual, and original modes with source trace", async () => {
  let generated = false;
  const originalExcerpt = "OpenAI introduced GPT-4 on March 14, 2023.";
  const translatedExcerpt = "OpenAI 于 2023 年 3 月 14 日推出了 GPT-4。";
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/videos/video-content/evidence")) {
      return response({
        evidence: [{
          evidence_id: "evidence-content-1",
          artifact_id: "artifact-content-1",
          lineage_kind: "ORIGINAL_TRANSCRIPT",
          role: "PRIMARY_ORIGINAL",
          source_language: "en",
          language: "en",
          original_excerpt: originalExcerpt,
          translated_excerpt: generated ? translatedExcerpt : null,
          translated_language: generated ? "zh-CN" : null,
          translation_target_language: "zh-CN",
          translation_status: generated ? "AVAILABLE" : "UNAVAILABLE",
          start_ms: 12_000,
          end_ms: 18_000,
          created_at: "2026-09-01T00:00:00Z",
          source_url: "https://www.youtube.com/watch?v=video-content",
        }],
      });
    }
    if (input.endsWith("/videos/video-content/evidence/evidence-content-1/translation")) {
      expect(init?.method).toBe("POST");
      generated = true;
      return response({
        evidence_id: "evidence-content-1",
        translated_excerpt: translatedExcerpt,
        translated_language: "zh-CN",
        translation_target_language: "zh-CN",
        translation_status: "AVAILABLE",
      });
    }
    if (input.endsWith("/videos/video-content")) {
      return response({
        video: {
          video_id: "video-content",
          channel_id: "channel-openai",
          channel_name: "OpenAI",
          title: "Introducing GPT-4",
          source_url: "https://www.youtube.com/watch?v=video-content",
          published_at: "2026-09-01T00:00:00Z",
          processing_status: "COMPLETE",
          last_updated: "2026-09-01T00:00:00Z",
        },
        transcript: { status: "AVAILABLE", text: originalExcerpt },
        note: { v2: { status: "AVAILABLE", language: "zh-CN", summary: "GPT-4 摘要。" } },
        intelligence_result: {
          status: "SUCCEEDED_NO_NEW_INTELLIGENCE",
          execution_id: "execution-1",
          has_new_intelligence: false,
          intelligence_id: null,
          revision_id: null,
          updated_at: "2026-09-01T00:00:00Z",
        },
        history: [],
      });
    }
    if (input.endsWith("/videos")) {
      return response({
        videos: [{
          video_id: "video-content",
          channel_id: "channel-openai",
          channel_name: "OpenAI",
          title: "Introducing GPT-4",
          source_url: "https://www.youtube.com/watch?v=video-content",
          published_at: "2026-09-01T00:00:00Z",
          processing_status: "COMPLETE",
          last_updated: "2026-09-01T00:00:00Z",
        }],
      });
    }
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(await screen.findByRole("button", { name: /Introducing GPT-4/ }));
  const evidencePanel = (await screen.findByText("Evidence · source transcript")).closest("section");
  if (!evidencePanel) throw new Error("Canonical Content Evidence panel is missing.");
  const evidenceContent = within(evidencePanel);
  expect(await evidenceContent.findByText(originalExcerpt)).toBeTruthy();
  expect(evidenceContent.getByText("Translation unavailable.")).toBeTruthy();
  expect(evidenceContent.getByRole("link", { name: "Open original at timestamp" })
    .getAttribute("href")).toContain("t=12");

  fireEvent.click(evidenceContent.getByRole("button", { name: "Translation" }));
  fireEvent.click(await evidenceContent.findByRole("button", { name: "Generate translation" }));
  expect(await evidenceContent.findByText(translatedExcerpt)).toBeTruthy();
  expect(generated).toBe(true);
  expect(evidenceContent.queryByText(originalExcerpt)).toBeNull();

  fireEvent.click(evidenceContent.getByRole("button", { name: "Bilingual" }));
  expect(evidenceContent.getByText(translatedExcerpt)).toBeTruthy();
  expect(evidenceContent.getByText(originalExcerpt)).toBeTruthy();

  fireEvent.click(evidenceContent.getByRole("button", { name: "Original" }));
  expect(evidenceContent.getByText(originalExcerpt)).toBeTruthy();
  expect(evidenceContent.queryByText(translatedExcerpt)).toBeNull();

  fireEvent.click(evidenceContent.getByRole("button", { name: "Translation" }));
  expect(evidenceContent.getByText(translatedExcerpt)).toBeTruthy();
  expect(evidenceContent.queryByText(originalExcerpt)).toBeNull();
});

test("Settings persists output language for future processing without rewriting history", async () => {
  let language: "zh-CN" | "en" = "zh-CN";
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/settings/output-language") && init?.method === "PUT") {
      language = JSON.parse(String(init.body)).output_language;
      return response({
        output_language: language,
        source: "USER_PREFERENCE",
        updated_at: "2026-09-01T00:00:00Z",
      });
    }
    if (input.endsWith("/settings")) {
      return response({
        general: {
          timezone: "Asia/Shanghai",
          output_language: language,
          output_language_source: language === "zh-CN"
            ? "BOOTSTRAP_DEFAULT"
            : "USER_PREFERENCE",
          output_language_updated_at: null,
        },
        providers: [],
      });
    }
    if (input.endsWith("/settings/preferences")) {
      return response({ active: [], history: [] });
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
      return response({ usage: [] });
    }
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  const view = render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(screen.queryByLabelText("Preferred output language")).toBeNull();
  fireEvent.click(await screen.findByRole("button", { name: "Edit language" }));
  const select = await screen.findByLabelText("Preferred output language");
  expect((select as HTMLSelectElement).value).toBe("zh-CN");
  expect((screen.getByLabelText("Interface language") as HTMLSelectElement).value).toBe("en");
  expect(screen.getByText(/Language choices apply to future output/)).toBeTruthy();
  expect(screen.getByText(/existing content is preserved/)).toBeTruthy();
  fireEvent.change(select, { target: { value: "en" } });
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Save language" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/settings/output-language",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ output_language: "en" }),
      }),
    )
  );
  await screen.findByRole("button", { name: "Edit language" });
  expect(screen.queryByLabelText("Preferred output language")).toBeNull();
  expect(screen.getByText(/Generated output: English/)).toBeTruthy();
  view.unmount();
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(await screen.findByRole("button", { name: "Edit language" }));
  expect((await screen.findByLabelText("Preferred output language") as HTMLSelectElement).value).toBe("en");
  expect((screen.getByLabelText("Interface language") as HTMLSelectElement).value).toBe("en");
});

test("Evidence stance and availability states are rendered without inference", async () => {
  const evidenceState = {
    ...intelligence,
    card: {
      ...intelligence.card,
      evidence_links: [
        { ...intelligence.card.evidence_links[0], evidence_id: "supporting", stance: "supporting" },
        { ...intelligence.card.evidence_links[0], evidence_id: "contradicting", stance: "contradicting" },
        { ...intelligence.card.evidence_links[0], evidence_id: "conditional", stance: "conditional" },
        {
          ...intelligence.card.evidence_links[0],
          evidence_id: "legacy",
          stance: null,
          original_excerpt: null,
        },
      ],
    },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/intelligence")) {
        return response({ intelligence: [evidenceState] });
      }
      if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
      if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [] });
      return response({});
    }),
  );

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByText("Evidence and source"));
  fireEvent.click(screen.getAllByRole("button", { name: "Translation" })[0]);
  expect(screen.getByText("Supporting")).toBeTruthy();
  expect(screen.getByText("Contradicting")).toBeTruthy();
  expect(screen.getByText("Conditional")).toBeTruthy();
  expect(screen.getByText("Relation not determined")).toBeTruthy();
  expect(screen.getByText(/Source excerpt unavailable for this historical Evidence/))
    .toBeTruthy();
  expect(screen.getAllByText(/Translation unavailable/)).toHaveLength(4);
});

test("Evidence can switch between translated, bilingual, and authoritative original views", async () => {
  const translatedIntelligence = {
    ...intelligence,
    card: {
      ...intelligence.card,
      evidence_links: [{
        ...intelligence.card.evidence_links[0],
        translated_excerpt: "译文：每个词元都可以关注其他词元的相关上下文。",
        translated_language: "zh-CN",
        translation_target_language: "zh-CN",
      }],
    },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/intelligence")) {
        return response({ intelligence: [translatedIntelligence] });
      }
      if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
      if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [] });
      return response({});
    }),
  );

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByText("Evidence and source"));
  expect(
    await screen.findByText("译文：每个词元都可以关注其他词元的相关上下文。"),
  ).toBeTruthy();
  expect(screen.queryByText(intelligence.card.evidence_links[0].original_excerpt))
    .toBeNull();

  fireEvent.click(screen.getAllByRole("button", { name: "Bilingual" })[0]);
  expect(screen.getByText(intelligence.card.evidence_links[0].original_excerpt))
    .toBeTruthy();
  expect(
    screen.getByText("译文：每个词元都可以关注其他词元的相关上下文。"),
  ).toBeTruthy();
  expect(screen.getByText("Provenance")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Open original at timestamp" }))
    .toBeTruthy();

  fireEvent.click(screen.getAllByRole("button", { name: "Original" })[0]);
  expect(screen.getByText(intelligence.card.evidence_links[0].original_excerpt))
    .toBeTruthy();
  expect(
    screen.queryByText("译文：每个词元都可以关注其他词元的相关上下文。"),
  ).toBeNull();
});

test("Evidence translation is generated only by an explicit UI action", async () => {
  const translatedIntelligence = {
    ...intelligence,
    card: {
      ...intelligence.card,
      evidence_links: [{
        ...intelligence.card.evidence_links[0],
        translated_excerpt: "译文：每个词元都可以关注其他词元的相关上下文。",
        translated_language: "zh-CN",
        translation_target_language: "zh-CN",
      }],
    },
  };
  let generated = false;
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/evidence/evidence-1/translation")) {
      expect(init?.method).toBe("POST");
      generated = true;
      return response({
        evidence_id: "evidence-1",
        translated_excerpt: "译文：每个词元都可以关注其他词元的相关上下文。",
        translated_language: "zh-CN",
        translation_target_language: "zh-CN",
        translation_status: "AVAILABLE",
      });
    }
    if (input.endsWith("/intelligence")) {
      return response({
        intelligence: [generated ? translatedIntelligence : intelligence],
      });
    }
    if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
    if (input.endsWith("/weekly/v1")) return response({ weekly_v1: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByText("Evidence and source"));
  expect(fetchMock.mock.calls.some(([input]) =>
    String(input).endsWith("/evidence/evidence-1/translation")
  )).toBe(false);
  fireEvent.click(screen.getAllByRole("button", { name: "Translation" })[0]);
  fireEvent.click(await screen.findByRole("button", { name: "Generate translation" }));
  expect(
    await screen.findByText("译文：每个词元都可以关注其他词元的相关上下文。"),
  ).toBeTruthy();
  expect(generated).toBe(true);
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
  expect(screen.getByText("This run needs a relevance or execution decision.")).toBeTruthy();
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
  expect(screen.getByText(/Paste a YouTube or Bilibili video link/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Add Source" })).toBeTruthy();
});

test("fresh onboarding explains local processing, multiple sources and remembers completion with an empty library", async () => {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/dashboard")) return response({ intelligence: [], pinned_topics: [], weekly_v1: [], needs_attention: [], operations: { source_count: 0 } });
    if (input.endsWith("/sources")) return response({ sources: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);
  const view = render(<App />);
  expect(await screen.findByText("FIRST RUN · 1 / 3")).toBeTruthy();
  expect(screen.getByText("Keep up with what matters to you.")).toBeTruthy();
  const concepts = document.querySelector(".onboarding-value-grid");
  for (const concept of ["Keep watching", "Understand quickly", "Build knowledge"]) expect(concepts?.textContent).toContain(concept);
  expect(concepts?.textContent).not.toMatch(/Evidence|Topic/);
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(await screen.findByText("FIRST RUN · 2 / 3")).toBeTruthy();
  expect(screen.getByText("Local-first processing")).toBeTruthy();
  expect(screen.getByText("Use local capability first. Never make a paid cloud call unless you explicitly opt in.")).toBeTruthy();
  expect(screen.getByText("Content can be organized without cloud Intelligence. Some videos have no available captions.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(await screen.findByText("FIRST RUN · 3 / 3")).toBeTruthy();
  expect(screen.getByText("Paste a YouTube video or channel link, import a public Bilibili video, or choose local files.")).toBeTruthy();
  expect(screen.getByText(/Bilibili creator following is unavailable/)).toBeTruthy();
  expect(screen.queryByText(/Runtime qualification is separate/)).toBeNull();
  expect(screen.queryByText(/production Following configuration path/)).toBeNull();
  expect(fetchMock.mock.calls.some(([, init]) => ["POST", "PUT", "PATCH", "DELETE"].includes(init?.method ?? "GET"))).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Add something" }));
  expect(await screen.findByText(/Set up your first Source/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Home" }));
  expect(await screen.findByText("No important new intelligence yet.")).toBeTruthy();
  expect(screen.queryByText(/FIRST RUN/)).toBeNull();
  view.unmount(); location.hash = "Home";
  render(<App />);
  expect(await screen.findByText("No important new intelligence yet.")).toBeTruthy();
  expect(screen.queryByText(/FIRST RUN/)).toBeNull();
});

test("skipping onboarding persists without creating Content or invoking a model", async () => {
  const fetchMock = vi.fn((input: string, _init?: RequestInit) => input.endsWith("/dashboard")
    ? response({ intelligence: [], pinned_topics: [], weekly_v1: [], needs_attention: [], operations: { source_count: 0 } }) : response({}));
  vi.stubGlobal("fetch", fetchMock);
  const view = render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Skip for now" }));
  expect(await screen.findByText("No important new intelligence yet.")).toBeTruthy();
  view.unmount(); render(<App />);
  expect(await screen.findByText("No important new intelligence yet.")).toBeTruthy();
  expect(screen.queryByText(/FIRST RUN/)).toBeNull();
  expect(fetchMock.mock.calls.every(([, init]) => !(init as RequestInit | undefined)?.method)).toBe(true);
});

test("historical Weekly data does not show a Brief or trigger first-run onboarding", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      if (input.endsWith("/dashboard")) {
        return response({
          intelligence: [],
          pinned_topics: [],
          weekly_v1: [{
            brief_id: "historic-week-1",
            version: "V1",
            period_start: "2026-09-01T00:00:00Z",
            no_important_information: false,
            items: [{
              topic_name: "Topic",
              intelligence_id: "historic-intel-1",
              claim_kind: "FACT",
              source_state: "AVAILABLE",
              summary: "An old weekly summary.",
              evidence_ids: [],
              markers: [],
            }],
          }],
          needs_attention: [],
          operations: { source_count: 0 },
        });
      }
      return response({});
    }),
  );
  render(<App />);

  expect(await screen.findByText("No important new intelligence yet."))
    .toBeTruthy();
  expect(screen.queryByText("This week")).toBeNull();
  expect(screen.queryByRole("button", { name: "Open Weekly" })).toBeNull();
  expect(screen.queryByText("An old weekly summary.")).toBeNull();
  expect(screen.queryByText("Turn what you follow into traceable knowledge."))
    .toBeNull();
});

test("Intelligence keeps Current and Saved while omitting the Weekly read surface", async () => {
  const fetchMock = vi.fn((input: string) => {
    if (input.endsWith("/intelligence")) {
      return response({ intelligence: [intelligence] });
    }
    if (input.endsWith("/saved-intelligence")) return response({ saved: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));

  expect(await screen.findByText("A rumor remains unresolved.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Current" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Saved" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Weekly" })).toBeNull();
  expect(fetchMock.mock.calls.some(([input]) =>
    String(input).endsWith("/weekly/v1")
  )).toBe(false);
});

test("verified Intelligence explains its disputed validation posture without inventing confidence", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  expect(await screen.findByText("A rumor remains unresolved.")).toBeTruthy();
  expect(screen.queryByText("This Intelligence is not available as current information."))
    .toBeNull();
  expect(screen.getByText("Unconfirmed rumor")).toBeTruthy();
  expect(screen.getByText("Disputed")).toBeTruthy();
  expect(
    screen.getByText(
      /Still needs validation\. Conflicting Evidence or interpretation remains unresolved\./,
    ),
  ).toBeTruthy();
  expect(screen.getByText(/not a numeric confidence score/)).toBeTruthy();
  expect(screen.queryByText(/\b\d+(?:\.\d+)?%\b/)).toBeNull();
  fireEvent.click(screen.getByText("Evidence and source"));
  expect(screen.getByText("Contradicting")).toBeTruthy();
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
    screen.getByRole("link", { name: "Open original at timestamp" }).getAttribute(
      "href",
    ),
  ).toBe("https://www.youtube.com/watch?v=video-1&t=1");
  expect(screen.queryByText(/Worth Watching|Watch Score|Should I watch/))
    .toBeNull();
});

test("Intelligence hierarchy labels relevance, new information, and supporting detail before Evidence", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  const why = await screen.findByText("Why this matters");
  const changed = screen.getByText("What is new");
  const details = screen.getByText("Important details");
  const evidence = screen.getByText("Evidence and source");
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

test("Deep Analysis remains truthful and Investigations stays outside V1 navigation", async () => {
  render(<App />);
  expect(screen.queryByRole("button", { name: "Investigations" })).toBeNull();
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
  expect(screen.getByText("Resource Usage (read-only)")).toBeTruthy();
  expect(screen.getByText(/Token usage: Unavailable/)).toBeTruthy();
  expect(screen.getByText(/Cost: Unavailable/)).toBeTruthy();
  expect(screen.queryByText(/estimated/i)).toBeNull();
});

test("Settings presents Kimi scope truthfully and keeps provider mechanics collapsed", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  const primaryModels = (await screen.findByText("Models and processing")).closest("section")!;
  expect(within(primaryModels).getByRole("heading", { name: "Intelligence", level: 3 })).toBeTruthy();
  expect(screen.getByText("Advanced and diagnostics").parentElement?.hasAttribute("open")).toBe(false);
  expect(screen.getByText("Qualified for V1 video analysis. Each cloud execution requires your separate consent."))
    .toBeTruthy();
  expect(screen.getByText("Deep Analysis is unavailable.")).toBeTruthy();
  const disclosure =
    screen.getByText("Provider and model details").parentElement;
  expect(disclosure?.hasAttribute("open")).toBe(false);
  expect(screen.getByText("moonshot · kimi-k2.6")).toBeTruthy();
  expect(screen.getByText("Scope: Video Distillation only.")).toBeTruthy();
});

test("Sources prefer a persisted friendly name while keeping the canonical URL accessible", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
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
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
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

test("Check Now submits a durable Source Run without inventing completion or Retry", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click(
    await screen.findByRole("button", {
      name: /Marques Brownlee.*Monitoring new videos/,
    }),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Check Now" }));
  expect(await screen.findByText(/durable Source Run was accepted/))
    .toBeTruthy();
  expect(screen.queryByText(/completed/i)).toBeNull();
  expect(screen.queryByText("Retry")).toBeNull();
});

test("stopping a Source uses the legal enabled command and is not historical deletion", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
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

test("a new user can paste a link without selecting a provider or schedule", async () => {
  vi.stubGlobal("fetch", vi.fn((input: string) => input.endsWith("/sources") ? response({ sources: [] }) : response({})));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  expect(await screen.findByText(/Set up your first Source/)).toBeTruthy();
  fireEvent.click(screen.getAllByRole("button", { name: "Add Source" })[1]);
  expect(await screen.findByRole("heading", { name: "Add a Source" })).toBeTruthy();
  expect(screen.getByLabelText("Paste link")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Import local file" })).toBeTruthy();
  for (const label of ["Monitor this Source", "Automatic schedule", "Enable automatic schedule", "Initial history", "Per-run limit", "Focus preference"]) expect(screen.queryByLabelText(label)).toBeNull();
  fireEvent.change(screen.getByLabelText("Paste link"), { target: { value: "https://youtube.test/new" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  expect(screen.getByRole("alert").textContent).toMatch(/supported HTTPS/);
  expect(fetch).not.toHaveBeenCalledWith("/api/v1/sources", expect.objectContaining({ method: "POST" }));
});

test("single video Add creates durable Content work without schedule or continuous Following", async () => {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/sources/import") && init?.method === "POST") return response({ source: { source_id: "source-new", video_id: "abcdefghijk" }, source_run: { state: "QUEUED" } });
    if (input.endsWith("/sources")) return response({ sources: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click((await screen.findAllByRole("button", { name: "Add Source" }))[1]);
  fireEvent.change(screen.getByLabelText("Paste link"), { target: { value: "https://youtu.be/abcdefghijk" } });
  expect(screen.getByText(/Its channel will not be followed/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  expect(await screen.findByText("Import accepted. Processing and any required attention appear in Content.")).toBeTruthy();
  const writes = fetchMock.mock.calls.filter(([path, init]) => init?.method === "POST" && !path.endsWith("/sources/check-stale"));
  expect(writes).toHaveLength(1);
  expect(writes[0][0]).toBe("/api/v1/sources/import");
  expect(JSON.parse(String(writes[0][1]?.body))).toEqual({ url: "https://www.youtube.com/watch?v=abcdefghijk", command_id: expect.any(String) });
  expect(screen.getByRole("link", { name: "Open Content" }).getAttribute("href")).toBe("#Content/abcdefghijk");
  expect(writes.some(([path]) => /automation|channels|creators/.test(path))).toBe(false);
});

test("Saved and Topic keep trust meaning while hiding backend codes from primary reading", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Saved" }));
  expect(await screen.findByText(/no longer available as current Intelligence/))
    .toBeTruthy();
  expect(screen.queryByText("CURRENT_NOT_ACTIVE")).toBeNull();
  expect(screen.queryByRole("button", { name: "Weekly" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Topics" }));
  expect(await screen.findByText(/Some support is unavailable/)).toBeTruthy();
  expect(screen.queryByText("DEGRADED")).toBeNull();
});

test("an admitted Intelligence can create and link a Topic through the UI", async () => {
  const baseline = fetch;
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    if (input.endsWith("/topics") && init?.method === "POST") {
      return response({ topic: { ...topic, topic_id: "topic:from-intelligence:intel-1", name: "Transformer research" } });
    }
    if (input.endsWith("/topics/topic:from-intelligence:intel-1/associations")) {
      return response({ association: { topic_id: "topic:from-intelligence:intel-1" } });
    }
    return baseline(input, init);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Intelligence" }));
  fireEvent.click(await screen.findByRole("button", { name: "Add to a Topic" }));
  fireEvent.change(screen.getByLabelText("Topic name"), {
    target: { value: "Transformer research" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create Topic and link Intelligence" }));
  expect(await screen.findByText("Linked to Topic: Transformer research")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/topics",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ command_id: "from-intelligence:intel-1", name: "Transformer research" }),
    }),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/topics/topic:from-intelligence:intel-1/associations",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ intelligence_id: "intel-1", association_kind: "NEW_INFORMATION" }),
    }),
  );
});

const daVideoList = {
  videos: [{
    video_id: "video-1",
    channel_id: "channel-1",
    channel_name: "Fixture channel",
    title: "Deep Analysis fixture",
    source_url: "https://www.youtube.com/watch?v=video-1",
    published_at: "2026-09-01T00:00:00Z",
    processing_status: "COMPLETE",
    last_updated: "2026-09-01T00:00:00Z",
    deep_analysis: { status: "NOT_REQUESTED", reason: null },
  }],
};

const daVideoDetail = {
  video: daVideoList.videos[0],
  transcript: {
    status: "AVAILABLE",
    text: "Original transcript evidence.",
    created_at: "2026-09-01T00:00:00Z",
  },
  note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
  intelligence_result: {
    status: "NOT_PROCESSED",
    execution_id: null,
    has_new_intelligence: null,
    intelligence_id: null,
    revision_id: null,
    updated_at: null,
  },
  history: [],
};

const daResult = {
  content_id: "video-1",
  result_identity: "result-1",
  content_identity: "content-1",
  output_language: "zh-CN",
  generated_at: "2026-10-01T00:00:00Z",
  evidence_citation_status: "PENDING_DURABLE_EVIDENCE_CONVERGENCE",
  roles: [
    { role: "CORE_CONCLUSION", text: "核心结论内容。", point_kind: "inference", confidence: "INSUFFICIENT_EVIDENCE" },
    { role: "KEY_EVIDENCE", text: "关键证据内容。", point_kind: "fact", confidence: "INSUFFICIENT_EVIDENCE" },
    { role: "UNCERTAINTY", text: "不确定性内容。", point_kind: "inference", confidence: "INSUFFICIENT_EVIDENCE" },
    { role: "RELEVANCE_TO_USER", text: "对我的意义。", point_kind: "inference", confidence: "INSUFFICIENT_EVIDENCE" },
    { role: "NEXT_QUESTION", text: "下一步追问。", point_kind: "inference", confidence: "INSUFFICIENT_EVIDENCE" },
  ],
};

function stubDeepAnalysis(
  state: { status: Record<string, unknown>; result: unknown },
  options: { onPost?: () => void; publishState?: string; publishError?: string; publishResult?: string } = {},
) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/deep-analysis/obsidian")) {
      if (init?.method === "POST") {
        return Promise.resolve({ ok: !options.publishError, json: async () => (options.publishError
          ? { error: { code: options.publishError, message: "Raw backend English failure" } }
          : { publish: { state: "PUBLISHED", relative_path: `Deep Analysis/${"a".repeat(240)}.md` } }) });
      }
      return response({ publish: { state: options.publishState ?? "AVAILABLE", result_identity: options.publishResult ?? "result-1" } });
    }
    if (init?.method === "POST") {
      options.onPost?.();
      return response({ deep_analysis: { result: state.result } });
    }
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return response({ deep_analysis: state });
    }
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    if (url.endsWith("/videos")) return response(daVideoList);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function openDeepAnalysisContent() {
  const savedLanguage = localStorage.getItem("yia.ui-language");
  const contentNav =
    savedLanguage === "zh-CN" ? "内容" : "Content";
  fireEvent.click(screen.getByRole("button", { name: contentNav }));
  fireEvent.click(
    await screen.findByRole("button", { name: /Deep Analysis fixture/ }),
  );
  const runLabel =
    savedLanguage === "zh-CN" ? "开始深度分析" : "Run Deep Analysis";
  // Wait for the Deep Analysis projection to resolve before asserting on it.
  await screen.findByRole("button", { name: runLabel });
}

test("publish status read recovery does not invent a failed write or publish a note", async () => {
  const originalFetch = stubDeepAnalysis({
    status: { availability: "AVAILABLE", qualified: false },
    result: { ...daResult, evidence_citation_status: "DURABLE_EVIDENCE_VERIFIED" },
  });
  let available = false;
  let statusReads = 0;
  const writes: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") writes.push(url);
    if (url.endsWith("/deep-analysis/obsidian") && init?.method !== "POST") {
      statusReads += 1;
      if (!available) return Promise.resolve(new Response("", { status: 500 }));
    }
    return originalFetch(input, init);
  }));

  render(<App />);
  await openDeepAnalysisContent();
  await screen.findByText("The local service is temporarily unavailable. Wait for it to recover, then reload this page.");
  // Existing result-identity key mounts once before and once after the result loads.
  expect(statusReads).toBe(2);
  expect((screen.getByRole("button", { name: "Publish to Obsidian" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByText("The write did not complete. Check vault permissions, paths, or file conflicts and retry.")).toBeNull();
  available = true;
  fireEvent.click(screen.getByRole("button", { name: "Reload page data" }));
  await waitFor(() => expect((screen.getByRole("button", { name: "Publish to Obsidian" }) as HTMLButtonElement).disabled).toBe(false));
  expect(statusReads).toBe(3);
  expect(writes).toEqual([]);
  expect(screen.queryByText("The local service is temporarily unavailable. Wait for it to recover, then reload this page.")).toBeNull();
});

test("Deep Analysis is a Content-level action and adds no top-level navigation", async () => {
  stubDeepAnalysis({
    status: {
      availability: "NOT_REQUESTED",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: null,
  });

  render(<App />);
  await openDeepAnalysisContent();

  expect(await screen.findByText("Deep Analysis")).toBeTruthy();
  // The frozen IA keeps exactly six first-level destinations.
  expect(
    screen.getAllByRole("button", {
      name: /^(Home|Following|Content|Intelligence|Topics|Settings)$/,
    }),
  ).toHaveLength(6);
  expect(screen.queryByRole("button", { name: "Deep Analysis" })).toBeNull();
});

test.each(["en", "zh-CN"])("Obsidian publish is explicit and localized in %s even with generation unqualified", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  const fetchMock = stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: false }, result: { ...daResult, evidence_citation_status: "DURABLE_EVIDENCE_VERIFIED" } });
  render(<App />);
  await openDeepAnalysisContent();
  const button = await screen.findByRole("button", { name: language === "en" ? "Publish to Obsidian" : "发布到 Obsidian" });
  await waitFor(() => expect(button.hasAttribute("disabled")).toBe(false));
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  fireEvent.click(button);
  expect(await screen.findByText(language === "en" ? "Published to Obsidian." : "已发布到 Obsidian。", { exact: false })).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/videos/video-1/deep-analysis/obsidian", expect.objectContaining({ method: "POST", body: JSON.stringify({ result_identity: "result-1" }) }));
});

test.each(["NO_VAULT", "RESULT_INELIGIBLE"])("Obsidian %s state disables publish without raw backend prose", async (state) => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: false }, result: daResult }, { publishState: state });
  render(<App />);
  await openDeepAnalysisContent();
  const button = await screen.findByRole("button", { name: "发布到 Obsidian" });
  expect(button.hasAttribute("disabled")).toBe(true);
  expect(await screen.findByText(state === "NO_VAULT" ? "尚未配置 Obsidian 笔记库。" : "仅经过核验的持久化深度分析结果可以发布。")).toBeTruthy();
});

test("Obsidian write failure is localized in Chinese", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: false }, result: { ...daResult, evidence_citation_status: "DURABLE_EVIDENCE_VERIFIED" } }, { publishError: "WRITE_FAILED" });
  render(<App />);
  await openDeepAnalysisContent();
  const button = await screen.findByRole("button", { name: "发布到 Obsidian" });
  await waitFor(() => expect(button.hasAttribute("disabled")).toBe(false));
  fireEvent.click(button);
  expect(await screen.findByText("写入未完成。请检查笔记库权限、路径或文件冲突后重试。")).toBeTruthy();
  expect(screen.queryByText("Raw backend English failure")).toBeNull();
});

test("Obsidian stale displayed result is disabled with a truthful localized state", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: false }, result: { ...daResult, evidence_citation_status: "DURABLE_EVIDENCE_VERIFIED" } }, { publishResult: "newer-result" });
  render(<App />);
  await openDeepAnalysisContent();
  expect(await screen.findByText("深度分析结果已更新。请重新打开此内容后再发布。")).toBeTruthy();
  expect(screen.getByRole("button", { name: "发布到 Obsidian" }).hasAttribute("disabled")).toBe(true);
});

test.each(["en", "zh-CN"])("%s production NONE retains trusted result, durable citations and explicit publish", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  const fetchMock = stubDeepAnalysis({
    status: { availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", qualified: false, production_eligible: false, route_id: null },
    result: durableDaResult,
  });
  render(<App />);
  await openDeepAnalysisContent();
  expect(await screen.findByText(durableDaResult.roles[0].text)).toBeTruthy();
  expect(screen.getAllByRole("link", { name: language === "en" ? "Evidence 1" : "证据 1" }).length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: language === "en" ? "Run Deep Analysis" : "开始深度分析" }).hasAttribute("disabled")).toBe(true);
  const publish = screen.getByRole("button", { name: language === "en" ? "Publish to Obsidian" : "发布到 Obsidian" });
  await waitFor(() => expect(publish.hasAttribute("disabled")).toBe(false));
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
  fireEvent.click(publish);
  await screen.findByText(language === "en" ? "Published to Obsidian." : "已发布到 Obsidian。", { exact: false });
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  expect(within(screen.getByRole("navigation", { name: language === "en" ? "Primary navigation" : "主导航" })).getAllByRole("button")).toHaveLength(6);
});

test.each([
  ["NOT_PROCESSED", "No canonical transcript has been recorded for this video.", "此内容尚未记录原始字幕。"],
  ["FAILED", "Transcript processing ended without a canonical transcript.", "字幕处理已结束，但未生成原始字幕。"],
  ["UNAVAILABLE", "The recorded canonical transcript cannot be safely read.", "已记录的原始字幕无法安全读取。"],
  ["UNKNOWN_BACKEND_STATE", "A readable transcript is not available yet.", "目前没有可阅读的原始字幕。"],
])("Content transcript %s uses localized state rather than backend prose", async (status, english, chinese) => {
  for (const [language, copy] of [["en", english], ["zh-CN", chinese]]) {
    localStorage.setItem("yia.ui-language", language);
    stubDeepAnalysis({ status: { availability: "NOT_QUALIFIED", qualified: false }, result: null });
    const baseFetch = vi.mocked(fetch).getMockImplementation()!;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
      String(input).endsWith("/videos/video-1")
        ? response({ ...daVideoDetail, transcript: { status, reason: "Raw backend English diagnostic" } })
        : baseFetch(input, init)));
    const view = render(<App />);
    await openDeepAnalysisContent();
    expect(await screen.findByText(copy)).toBeTruthy();
    expect(document.body.textContent).not.toContain("Raw backend English diagnostic");
    view.unmount();
  }
});

test("Deep Analysis is unavailable and honest when no model is qualified", async () => {
  stubDeepAnalysis({
    status: {
      availability: "NOT_QUALIFIED",
      reason: "No Deep Analysis model is currently qualified.",
      route_id: null,
      model_id: null,
      provider_id: null,
      qualified: false,
      consent_required: false,
    },
    result: null,
  });

  render(<App />);
  await openDeepAnalysisContent();

  expect(
    await screen.findByText(/no model is currently qualified for it/i),
  ).toBeTruthy();
  const runButton = screen.getByRole("button", { name: "Run Deep Analysis" });
  expect((runButton as HTMLButtonElement).disabled).toBe(true);
});

test("Deep Analysis renders the five product roles in order", async () => {
  stubDeepAnalysis({
    status: {
      availability: "AVAILABLE",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: daResult,
  });

  render(<App />);
  await openDeepAnalysisContent();

  expect(await screen.findByText("核心结论内容。")).toBeTruthy();
  // English mode must render English role headings, not hardcoded Chinese.
  for (const label of [
    "Core conclusion",
    "Key evidence",
    "Uncertainty",
    "Relevance to you",
    "Next question",
  ]) {
    expect(screen.getByText(label)).toBeTruthy();
  }
  // Deferred roles are never shown.
  expect(screen.queryByText("Relation to existing knowledge")).toBeNull();
  expect(screen.queryByText("Knowledge delta")).toBeNull();
  // Phase 1A never presents unverified refs as citations.
  expect(
    screen.getByText(/never presents an unverified reference as an authoritative citation/i),
  ).toBeTruthy();
});

test("Deep Analysis run is an explicit user-initiated POST", async () => {
  let posted = false;
  stubDeepAnalysis(
    {
      status: {
        availability: "AVAILABLE",
        reason: null,
        route_id: "local-ollama-qwen25-coder-7b",
        model_id: "qwen2.5-coder:7b",
        provider_id: "ollama-local",
        qualified: true,
        consent_required: false,
      },
      result: daResult,
    },
    { onPost: () => { posted = true; } },
  );

  render(<App />);
  await openDeepAnalysisContent();
  // Nothing runs on load.
  expect(posted).toBe(false);

  fireEvent.click(screen.getByRole("button", { name: "Run Deep Analysis" }));
  await waitFor(() => expect(posted).toBe(true));
});

test("Deep Analysis keeps Summary and Deep Analysis as distinct capabilities", async () => {
  stubDeepAnalysis({
    status: {
      availability: "NOT_REQUESTED",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: null,
  });

  render(<App />);
  await openDeepAnalysisContent();

  expect(await screen.findByText("Summary / Video Notes")).toBeTruthy();
  expect(screen.getByText("Deep Analysis")).toBeTruthy();
  expect(
    screen.getByText(/Summary explains what this content says/i),
  ).toBeTruthy();
});

test("Chinese Deep Analysis UI never leaks raw English backend status text", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : String(input);
    if (init?.method === "POST") return response({});
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return response({
        deep_analysis: {
          status: {
            availability: "NOT_QUALIFIED",
            reason_code: "NO_QUALIFIED_MODEL",
            // English diagnostic prose must not become Chinese product text.
            reason: "No Deep Analysis model is currently qualified.",
            route_id: null,
            model_id: null,
            provider_id: null,
            qualified: false,
            consent_required: false,
          },
          result: null,
        },
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await openDeepAnalysisContent();

  // Chinese product copy is shown, localized from the stable machine code.
  expect(await screen.findByText("未通过资格")).toBeTruthy();
  expect(
    screen.getByText("当前没有通过深度分析资格的模型，因此深度分析不可用。系统不会静默降级，摘要与证据仍可正常使用。"),
  ).toBeTruthy();
  // The raw English backend reason must not appear anywhere.
  expect(screen.queryByText(/No Deep Analysis model is currently qualified/)).toBeNull();
  const body = document.body.textContent ?? "";
  expect(body).not.toContain("No Deep Analysis model is currently qualified");
  // No engineering enum leaks into the Chinese UI.
  expect(body).not.toContain("NOT_QUALIFIED");
  expect(body).not.toContain("NO_QUALIFIED_MODEL");
});

test("English Deep Analysis UI remains correct after localization fix", async () => {
  localStorage.setItem("yia.ui-language", "en");
  stubDeepAnalysis({
    status: {
      availability: "NOT_QUALIFIED",
      reason_code: "NO_QUALIFIED_MODEL",
      reason: "No Deep Analysis model is currently qualified.",
      route_id: null,
      model_id: null,
      provider_id: null,
      qualified: false,
      consent_required: false,
    },
    result: null,
  });

  render(<App />);
  await openDeepAnalysisContent();

  expect(await screen.findByText("Not qualified")).toBeTruthy();
  expect(
    screen.getByText(/no model is currently qualified for it/i),
  ).toBeTruthy();
  // The run action stays disabled while nothing is qualified.
  const runButton = screen.getByRole("button", { name: "Run Deep Analysis" });
  expect((runButton as HTMLButtonElement).disabled).toBe(true);
});

test("Chinese Deep Analysis POST failure is localized by machine code", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const englishProse = "No Deep Analysis model is currently qualified. Deep Analysis is unavailable.";
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : String(input);
    if (init?.method === "POST") {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: "DEEP_ANALYSIS_NOT_QUALIFIED",
            message: englishProse,
            details: { reason_code: "NO_QUALIFIED_MODEL", availability: "NOT_QUALIFIED" },
          },
        }),
      });
    }
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return response({
        deep_analysis: {
          status: {
            availability: "AVAILABLE",
            reason_code: "RESULT_AVAILABLE",
            reason: null,
            route_id: "local-ollama-qwen25-coder-7b",
            model_id: "qwen2.5-coder:7b",
            provider_id: "ollama-local",
            qualified: true,
            consent_required: false,
          },
          result: daResult,
        },
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  // Navigate using the Chinese UI labels.
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(await screen.findByRole("button", { name: /Deep Analysis fixture/ }));
  const runButton = await screen.findByRole("button", { name: "开始深度分析" });
  expect((runButton as HTMLButtonElement).disabled).toBe(false);
  fireEvent.click(runButton);
  const posts = fetchMock.mock.calls.filter((c: any[]) => c[1]?.method === "POST");
  if (posts.length === 0) throw new Error("no POST was issued to the backend");
  await waitFor(() =>
    expect(
      (document.body.textContent ?? "").includes("因此无法运行深度分析"),
    ).toBe(true),
  );
  const localizedBody = document.body.textContent ?? "";
  expect(localizedBody).not.toContain("No Deep Analysis model is currently qualified");
  const localized = document.body.textContent ?? "";
  expect(localized).not.toContain("No Deep Analysis model is currently qualified");
  // The backend English prose must not appear.
  const body = document.body.textContent ?? "";
  expect(body).not.toContain("No Deep Analysis model is currently qualified");
  expect(body).not.toContain("NO_QUALIFIED_MODEL");
  expect(body).not.toContain("DEEP_ANALYSIS_NOT_QUALIFIED");
});

test("Chinese Deep Analysis confidence is localized, not a raw enum", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  stubDeepAnalysis({
    status: {
      availability: "AVAILABLE",
      reason_code: "RESULT_AVAILABLE",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: daResult,
  });

  render(<App />);
  await openDeepAnalysisContent();

  const matches = await screen.findAllByText((_c, el) =>
    el?.textContent === "置信度: 证据不足");
  expect(matches.length).toBeGreaterThan(0);
  const body = document.body.textContent ?? "";
  expect(body).not.toContain("INSUFFICIENT_EVIDENCE");
});

test("English confidence and run-failure copy remain correct", async () => {
  localStorage.setItem("yia.ui-language", "en");
  stubDeepAnalysis({
    status: {
      availability: "AVAILABLE",
      reason_code: "RESULT_AVAILABLE",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: daResult,
  });

  render(<App />);
  await openDeepAnalysisContent();

  const englishConfidence = await screen.findAllByText((_c, el) =>
    el?.textContent === "Confidence: Insufficient Evidence");
  expect(englishConfidence.length).toBeGreaterThan(0);
});

test("Chinese mode renders all five Chinese role headings and no English enum names", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  stubDeepAnalysis({
    status: {
      availability: "AVAILABLE",
      reason_code: "RESULT_AVAILABLE",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: daResult,
  });

  render(<App />);
  await openDeepAnalysisContent();

  for (const label of ["核心结论", "关键证据", "不确定性", "对我的意义", "下一步追问"]) {
    expect(screen.getByText(label)).toBeTruthy();
  }
  const body = document.body.textContent ?? "";
  for (const enumName of [
    "CORE_CONCLUSION",
    "KEY_EVIDENCE",
    "UNCERTAINTY",
    "RELEVANCE_TO_USER",
    "NEXT_QUESTION",
  ]) {
    expect(body).not.toContain(enumName);
  }
});

test("English mode renders no hardcoded Chinese role headings", async () => {
  localStorage.setItem("yia.ui-language", "en");
  stubDeepAnalysis({
    status: {
      availability: "AVAILABLE",
      reason_code: "RESULT_AVAILABLE",
      reason: null,
      route_id: "local-ollama-qwen25-coder-7b",
      model_id: "qwen2.5-coder:7b",
      provider_id: "ollama-local",
      qualified: true,
      consent_required: false,
    },
    result: daResult,
  });

  render(<App />);
  await openDeepAnalysisContent();

  for (const label of [
    "Core conclusion",
    "Key evidence",
    "Uncertainty",
    "Relevance to you",
    "Next question",
  ]) {
    expect(screen.getByText(label)).toBeTruthy();
  }
  // No heading may be rendered with the hardcoded Chinese source labels.
  for (const chinese of ["核心结论", "关键证据", "不确定性", "对我的意义", "下一步追问"]) {
    const headings = Array.from(
      document.querySelectorAll(".section-label"),
    ).map((el) => el.textContent ?? "");
    expect(headings).not.toContain(chinese);
  }
});

test("Chinese GET failure does not render raw backend English prose", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const backendProse =
    "The local service rejected this request because the Content state is invalid.";
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: "DEEP_ANALYSIS_NOT_QUALIFIED",
            message: backendProse,
            details: { reason_code: "NO_QUALIFIED_MODEL", availability: "NOT_QUALIFIED" },
          },
        }),
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(await screen.findByRole("button", { name: /Deep Analysis fixture/ }));
  await screen.findByRole("button", { name: "开始深度分析" });

  await waitFor(() =>
    expect(
      (document.body.textContent ?? "").includes(
        "当前没有通过深度分析资格的模型，因此无法运行深度分析。",
      ),
    ).toBe(true),
  );
  // The localized copy is the primary text; the raw prose is diagnostic only.
  const body = document.body.textContent ?? "";
  expect(body).not.toContain("DEEP_ANALYSIS_NOT_QUALIFIED");
  expect(body).not.toContain("NO_QUALIFIED_MODEL");
});

test("English mode renders the English equivalent for a GET failure", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: "DEEP_ANALYSIS_NOT_QUALIFIED",
            message: "backend prose that must not be primary copy",
            details: { reason_code: "NO_QUALIFIED_MODEL" },
          },
        }),
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(await screen.findByRole("button", { name: /Deep Analysis fixture/ }));

  expect(
    await screen.findByText(
      "Deep Analysis could not run because no model is currently qualified for it.",
    ),
  ).toBeTruthy();
});

test("Chinese DA GET failure shows no raw backend prose", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const backendProse = "Local service failed safely.";
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: "DEEP_ANALYSIS_NOT_QUALIFIED",
            message: backendProse,
            details: { reason_code: "NO_QUALIFIED_MODEL" },
          },
        }),
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(await screen.findByRole("button", { name: /Deep Analysis fixture/ }));

  await waitFor(() =>
    expect(
      (document.body.textContent ?? "").includes(
        "当前没有通过深度分析资格的模型，因此无法运行深度分析。",
      ),
    ).toBe(true),
  );
  // Raw backend prose must not appear anywhere in normal DA product UI.
  expect(document.body.textContent ?? "").not.toContain(backendProse);
  expect(document.body.textContent ?? "").not.toContain("Local service failed safely");
  expect(document.body.textContent ?? "").not.toContain("NO_QUALIFIED_MODEL");
});

test("Chinese INTERNAL_ERROR is localized and never shows raw prose", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const backendProse = "Local service failed safely.";
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return Promise.resolve({
        ok: false,
        status: 500,
        json: async () => ({
          error: { code: "INTERNAL_ERROR", message: backendProse },
        }),
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(await screen.findByRole("button", { name: /Deep Analysis fixture/ }));

  await waitFor(() =>
    expect(
      (document.body.textContent ?? "").includes(
        "深度分析因本地服务失败而无法完成，没有生成任何结果。",
      ),
    ).toBe(true),
  );
  const body = document.body.textContent ?? "";
  expect(body).not.toContain(backendProse);
  expect(body).not.toContain("INTERNAL_ERROR");
});

test("English DA GET failure shows no raw backend prose", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const backendProse = "Local service failed safely.";
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/videos/video-1/deep-analysis")) {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: "DEEP_ANALYSIS_NOT_QUALIFIED",
            message: backendProse,
            details: { reason_code: "NO_QUALIFIED_MODEL" },
          },
        }),
      });
    }
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1/evidence")) return response({ evidence: [] });
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Content" }));
  fireEvent.click(await screen.findByRole("button", { name: /Deep Analysis fixture/ }));

  expect(
    await screen.findByText(
      "Deep Analysis could not run because no model is currently qualified for it.",
    ),
  ).toBeTruthy();
  expect(document.body.textContent ?? "").not.toContain(backendProse);
});

const durableDaResult = {
  ...daResult,
  evidence_citation_status: "DURABLE_EVIDENCE_VERIFIED",
  roles: daResult.roles.map((claim, index) => ({
    ...claim,
    evidence_ids: ["a".repeat(64)],
    language_validation: index === 4 ? "UNCERTAIN" : "VALID",
  })),
};

test.each(["en", "zh-CN"])("durable DA citations and uncertain language are truthful in %s UI", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: false }, result: durableDaResult });
  render(<App />);
  await openDeepAnalysisContent();
  const citationLabel = language === "en" ? "Evidence 1" : "证据 1";
  const citations = await screen.findAllByRole("link", { name: citationLabel });
  expect(citations).toHaveLength(5);
  expect(citations.every((link) => link.getAttribute("href") === `#content-evidence-${"a".repeat(64)}`)).toBe(true);
  expect(screen.getByText(language === "en"
    ? "Evidence citations have been verified against this Content’s original transcript."
    : "证据引用已与这段内容的原始字幕核验。")).toBeTruthy();
  expect(screen.getByText(language === "en" ? "Output language could not be fully verified." : "输出语言尚未完全核验。")).toBeTruthy();
  expect(screen.queryByText(/Per-claim Evidence citations are not shown yet/)).toBeNull();
});

test("legacy DA never renders refs even if a partial payload supplies them", async () => {
  stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: false }, result: {
    ...durableDaResult, evidence_citation_status: "PENDING_DURABLE_EVIDENCE_CONVERGENCE",
  } });
  render(<App />);
  await openDeepAnalysisContent();
  expect(await screen.findByText(/never presents an unverified reference/)).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Evidence 1" })).toBeNull();
  expect(screen.queryByText("Output language could not be fully verified.")).toBeNull();
});

test("running DA refreshes the existing Content Evidence view", async () => {
  const fetchMock = stubDeepAnalysis({ status: { availability: "AVAILABLE", qualified: true }, result: durableDaResult });
  render(<App />);
  await openDeepAnalysisContent();
  await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/evidence"))).toHaveLength(1));
  fireEvent.click(screen.getByRole("button", { name: "Run Deep Analysis" }));
  await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/evidence"))).toHaveLength(2));
});

test.each(["en", "zh-CN"])("%s cloud Deep Analysis discloses cost before consent and denial sends no execution", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  const executions: unknown[] = [];
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/deep-analysis/preflight")) return response({ preflight: {
      execution_id: "one-execution", route_id: "cloud-route", provider_id: "openai", model_id: "qualified-model",
      credential_configured: true, qualification_status: "QUALIFIED", data_egress_mode: "SELECTED_EVIDENCE_ONLY",
      cost: { state: "UNKNOWN", hard_monetary_cap: false, input_characters: 1234 },
    } });
    if (url.endsWith("/deep-analysis") && init?.method === "POST") {
      executions.push(JSON.parse(String(init.body))); return response({});
    }
    if (url.endsWith("/deep-analysis")) return response({ deep_analysis: { status: {
      availability: "NOT_REQUESTED", qualified: true, production_eligible: true,
      consent_required: true, route_id: "cloud-route", provider_id: "openai", model_id: "qualified-model",
    }, result: null } });
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    if (url.endsWith("/evidence")) return response({ evidence: [] });
    return response({});
  }));
  render(<App />);
  await openDeepAnalysisContent();
  const runName = language === "en" ? "Run Deep Analysis" : "开始深度分析";
  fireEvent.click(screen.getByRole("button", { name: runName }));
  const disclosure = language === "en" ? "The monetary cost is unknown. No hard spending cap is enforced." : "金额费用未知；本次执行没有强制金额上限。";
  expect(await screen.findByText(disclosure)).toBeTruthy();
  expect(executions).toHaveLength(0);
  const authorizeName = language === "en" ? "Authorize this cloud run" : "授权本次云端执行";
  expect((screen.getByRole("button", { name: authorizeName }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Cancel cloud run" : "取消云端执行" }));
  expect(executions).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: runName }));
  await screen.findByText(disclosure);
  fireEvent.click(screen.getByRole("checkbox", { name: language === "en" ? "I acknowledge the unknown cost for this execution." : "我已知晓本次执行的费用未知。" }));
  fireEvent.click(screen.getByRole("button", { name: authorizeName }));
  await waitFor(() => expect(executions).toEqual([{ route_id: "cloud-route", execution_id: "one-execution", authorize_cloud: true, acknowledge_unknown_cost: true, egress_mode: "SELECTED_EVIDENCE_ONLY" }]));
});

test.each([
  ["en", "CREDENTIAL_MISSING", "The model is qualified, but its cloud credential is missing. Configure the runtime credential before requesting Deep Analysis."],
  ["zh-CN", "CREDENTIAL_MISSING", "模型已通过资格评测，但缺少云端凭据。请配置运行时凭据后再请求深度分析。"],
  ["en", "ROUTE_UNREACHABLE", "The model is qualified, but the provider is currently unreachable. Deep Analysis cannot run until connectivity is restored."],
  ["zh-CN", "ROUTE_UNREACHABLE", "模型已通过资格评测，但目前无法连接提供方。恢复连接后才能执行深度分析。"],
])("%s qualified model with %s stays unavailable with a precise explanation", async (language, reason, copy) => {
  localStorage.setItem("yia.ui-language", language);
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/deep-analysis")) return response({ deep_analysis: { status: {
      availability: "UNAVAILABLE", reason_code: reason, qualified: true, production_eligible: false,
      consent_required: true, route_id: null, provider_id: null, model_id: null,
    }, result: null } });
    if (url.endsWith("/videos")) return response(daVideoList);
    if (url.endsWith("/videos/video-1")) return response(daVideoDetail);
    if (url.endsWith("/evidence")) return response({ evidence: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await openDeepAnalysisContent();
  expect(await screen.findByText(copy)).toBeTruthy();
  expect((screen.getByRole("button", { name: language === "en" ? "Run Deep Analysis" : "开始深度分析" }) as HTMLButtonElement).disabled).toBe(true);
  expect(document.body.textContent).not.toContain("UNAVAILABLE");
  expect(fetchMock.mock.calls.every(call => !String(call[0]).endsWith("/preflight"))).toBe(true);
});


test.each([
  ["content", "video-1", "Open Content", "Content", "/videos/video-1"],
  ["intelligence", "intelligence:fixture", "Open Intelligence", "Intelligence", "/intelligence/intelligence:fixture"],
  ["topic", "topic-1", "Open Topic", "Topics", "/topics/topic-1"],
  ["source", "source-1", "Open Following", "Following", "/sources/source-1"],
])("Home Delta opens the existing %s target without new navigation", async (kind, id, label, page, path) => {
  const baseFetch = vi.mocked(fetch).getMockImplementation()!;
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    requests.push(input);
    if (input.endsWith("/knowledge-delta")) return response({ knowledge_delta: {
      window_start: "2026-09-26T08:00:00.000000Z", window_end: "2026-10-03T08:00:00.000000Z",
      timezone: "Asia/Shanghai", status: "available", detail_limit: 2,
      categories: [{ kind: kind === "content" ? "content_completed" : kind === "topic" ? "topic_updated" : kind === "source" ? "source_health" : "intelligence_added",
        status: "available", count: 1, items: [{ id: "change", kind: "content_completed", label: "Content completed", title: "Delta target",
          target: { kind, id }, occurred_at: "2026-10-03T08:00:00.000000Z", facts: {} }] }],
    } });
    if (input.endsWith("/intelligence/intelligence:fixture")) return response({ intelligence });
    return baseFetch(input, init);
  }));
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: `${label}: Delta target` }));
  expect(await screen.findByRole("heading", { name: page, level: 1 })).toBeTruthy();
  await waitFor(() => expect(requests).toContain(`/api/v1${path}`));
  expect(within(screen.getByRole("navigation", { name: "Primary navigation" })).getAllByRole("button")).toHaveLength(6);
});

test("Chinese Backup explains a block in Chinese instead of the backend English message", async () => {
  localStorage.removeItem("yia.ui-language");
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/backup-restore/status")
    ? response({ status: {
      ready: false, reasons: ["SOURCE_RUN_ACTIVE"], restore_pending: false, last_restore: null,
      // The service still returns English prose; the UI must not render it.
      message: "Backup is unavailable because: A Following Source Run is active.",
    } })
    : defaultFetch(path, init)));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  const backupPanel = (await screen.findByRole("heading", { name: "备份与恢复" })).closest("section")!;
  const status = await within(backupPanel).findByRole("status");
  expect(status.textContent).toContain("有一个采集任务仍在执行");
  expect(status.textContent).not.toContain("Source Run is active");
  expect(status.textContent).not.toMatch(/[A-Za-z]{4,}\s+[A-Za-z]{4,}/);
});


test("one-time video imports do not become continuous Following rows", async () => {
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/sources")
    ? response({ sources: [{ source_id: "one-time", source_type: "VIDEO_URL", display_name: "Imported video title", canonical_url: "https://youtu.be/abcdefghijk", enabled: true, processing_policy: "DISCOVER_ONLY", last_error: null }] }) : original(path, init)));
  render(<App />); fireEvent.click(screen.getByRole("button", { name: "Following" }));
  await screen.findAllByRole("button", { name: "Add Source" });
  await waitFor(() => expect(screen.queryByText("Imported video title")).toBeNull());
});

test.each([["RETRY_REQUIRED", false], ["NEEDS_ATTENTION", false], ["RETRY_REQUIRED", true]])("one-time Content %s Summary failure=%s retry remains visible and polls accepted durable work to completion", async (initialStatus, summaryFailure) => {
  location.hash = "Content/video-1";
  let accepted = false;
  let reads = 0;
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/sources/import-source/check") && init?.method === "POST") {
      accepted = true;
      return response({ source_run: { run_id: "retry-run", state: "QUEUED" } });
    }
    if (path.endsWith("/videos/video-1")) {
      const status = !accepted ? initialStatus : ++reads === 1 ? "WAITING" : "ORGANIZED";
      return response({ ...daVideoDetail, video: { ...daVideoDetail.video, provider: "YOUTUBE", source_id: "import-source", processing_status: status,
        caption_timing_status: !accepted && initialStatus === "NEEDS_ATTENTION" ? "UNAVAILABLE" : undefined,
        summary_preparation_status: !accepted && summaryFailure ? "NEEDS_ATTENTION" : undefined,
      } });
    }
    return original(path, init);
  }));
  render(<App />);
  if (summaryFailure) expect(await screen.findByText("Timed captions are saved, but the Summary could not be prepared. Retry to organize this Content; your captured text and source references are kept.")).toBeTruthy();
  fireEvent.click(await screen.findByRole("button", { name: /^Retry$/ }));
  expect(await screen.findByText("Retry accepted. Processing status will update here.")).toBeTruthy();
  await waitFor(() => expect(screen.queryByRole("button", { name: /^Retry$/ })).toBeNull());
  await waitFor(() => expect(reads).toBeGreaterThan(1), { timeout: 4000 });
  expect(await screen.findByText("Completed", { exact: true })).toBeTruthy();
});

test.each(["en", "zh-CN"])("%s settled Summary failure explains a retry without implying missing captions", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content/video-1";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/video-1")) return response({ ...daVideoDetail, video: {
      ...daVideoDetail.video, provider: "YOUTUBE", source_id: "import-source", processing_status: "RETRY_REQUIRED",
      summary_preparation_status: "NEEDS_ATTENTION", retry_allowed: true,
    } });
    return original(path, init);
  }));
  render(<App />);
  expect(await screen.findByText(language === "en"
    ? "Timed captions are saved, but the Summary could not be prepared. Retry to organize this Content; your captured text and source references are kept."
    : "带时间的字幕已保存，摘要整理未完成。点击重试以整理此内容；已获取的文本和出处会保留。")).toBeTruthy();
  expect((screen.getByRole("button", { name: language === "en" ? /^Retry$/ : /^重试$/ }) as HTMLButtonElement).disabled).toBe(false);
  expect(screen.queryByText(language === "en" ? "Organizing content…" : "正在整理内容…")).toBeNull();
  expect(screen.queryByText(language === "en"
    ? "The captured captions have no verified source timing. Content needs timed captions before Summary and source references can be prepared."
    : "已获取的字幕没有可验证的原始时间。需要带时间的字幕，才能生成摘要和出处。")).toBeNull();
});

test.each([["en", false], ["zh-CN", false], ["en", true], ["zh-CN", true]])("%s completed plain captions with retry source=%s explain missing timing without claiming work is running", async (language, hasSource) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content/video-1";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/videos/video-1")) return response({ ...daVideoDetail, video: {
      ...daVideoDetail.video, provider: "YOUTUBE", processing_status: "NEEDS_ATTENTION", caption_timing_status: "UNAVAILABLE",
      source_id: hasSource ? "import-source" : undefined,
    } });
    return original(path, init);
  }));
  render(<App />);
  expect(await screen.findByText(language === "en"
    ? "The captured captions have no verified source timing. Content needs timed captions before Summary and source references can be prepared."
    : "已获取的字幕没有可验证的原始时间。需要带时间的字幕，才能生成摘要和出处。" )).toBeTruthy();
  expect(screen.queryByText(language === "en" ? "Organizing content…" : "正在整理内容…")).toBeNull();
  if (hasSource) {
    expect(screen.getByText(language === "en"
      ? "Retry to check this source for native timed captions. Your captured text and history are kept."
      : "点击重试，检查此来源是否提供原生时间字幕。已获取的文本和处理历史会保留。")).toBeTruthy();
    expect((screen.getByRole("button", { name: language === "en" ? /^Retry$/ : /^重试$/ }) as HTMLButtonElement).disabled).toBe(false);
  }
});

test.each(["en", "zh-CN"])("%s non-retryable Content explains the prerequisite and disables retry semantically", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content/video-1";
  const original = globalThis.fetch;
  const mutations: string[] = [];
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (init?.method === "POST") mutations.push(path);
    if (path.endsWith("/videos/video-1")) return response({ ...daVideoDetail, video: { ...daVideoDetail.video, provider: "YOUTUBE", source_id: "import-source", processing_status: "FAILED", retry_allowed: false } });
    return original(path, init);
  }));
  render(<App />);
  const retry = await screen.findByRole("button", { name: language === "en" ? /^Retry$/ : /^重试$/ });
  expect(retry.hasAttribute("disabled")).toBe(true);
  expect(screen.getByText(language === "en" ? "This Content needs source or processing readiness review before it can be processed again." : "此内容需要先核对来源或处理就绪状态，才能再次处理。")).toBeTruthy();
  fireEvent.click(retry);
  expect(mutations).toEqual([]);
});

test.each([
  ["WAITING_CONTENT", "等待内容整理"],
  ["WAITING_MODEL", "等待合格的洞察模型"],
  ["WAITING_BUDGET", "等待获准的处理资源"],
  ["SUCCEEDED_NO_NEW_INTELLIGENCE", "已完成，未产生新洞察"],
])("Chinese optional Intelligence %s has an ordinary localized status label", async (status, label) => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = "Content/video-1";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/videos/video-1")
    ? response({ ...daVideoDetail, intelligence_result: { ...daVideoDetail.intelligence_result, status } })
    : original(path, init)));
  render(<App />);
  expect(await screen.findByText(label, { exact: true })).toBeTruthy();
  expect(screen.queryByText(status, { exact: true })).toBeNull();
});

test.each(["en", "zh-CN"])("%s saved unresolved Source never implies active Following on Home", async language => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Home";
  const original = globalThis.fetch;
  const fetchMock = vi.fn((path: string, init?: RequestInit) => path.endsWith("/dashboard")
    ? response({ intelligence: [], pinned_topics: [], weekly_v1: [], needs_attention: [], operations: { source_count: 1 } })
    : original(path, init));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  expect(await screen.findByText(language === "en"
    ? "Open Following to check your saved sources or add something new. Content is organized first; generating Intelligence is optional."
    : "打开关注，检查已保存的来源或添加新内容。系统先整理内容；是否进一步生成洞察，由你选择。", { exact: true })).toBeTruthy();
  expect(screen.queryByText(/You have a Following|你已添加关注/)).toBeNull();
  expect(screen.queryByText(/FIRST RUN/)).toBeNull();
  expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

test.each(["en", "zh-CN"])("%s empty Content explains single-content and local entry without internal demo prose", async language => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/videos") ? response({ videos: [] }) : original(path, init)));
  render(<App />);
  expect(await screen.findByText(language === "en"
    ? "No Content yet. Add a video link, follow a YouTube channel, or import a local file."
    : "暂无内容。添加视频链接，持续关注 YouTube 频道，或导入本地文件。", { exact: true })).toBeTruthy();
  expect(screen.queryByText(/Demo fixtures/)).toBeNull();
});

test("user hash navigation (browser back/forward or editing the address bar) switches views", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = "";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => original(path, init)));
  render(<App />);
  await screen.findByRole("heading", { name: "首页" });
  location.hash = "Settings";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByRole("heading", { name: "设置" });
  location.hash = "Topics";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByRole("heading", { name: "主题" });
  location.hash = "Content";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByRole("heading", { name: "内容" });
  location.hash = "Following";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByRole("heading", { name: "关注" });
  location.hash = "";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByRole("heading", { name: "首页" });
});

test("hashchange to a Content deep link still opens that Content detail", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = "";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/videos/video-1")
    ? response({ ...daVideoDetail, video: { ...daVideoDetail.video, provider: "YOUTUBE", source_id: "import-source" } })
    : original(path, init)));
  render(<App />);
  await screen.findByRole("heading", { name: "首页" });
  location.hash = "Content/video-1";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByText("Deep Analysis fixture");
  expect(location.hash).toBe("#Content/video-1");
});

test("import success notice survives the programmatic navigation that follows it", async () => {
  // Regression: onImported() calls setImported(true) and then openContent(),
  // which assigns location.hash. The hashchange handler must recognize that
  // assignment as programmatic navigation (programmaticHash stores the hash
  // WITH the leading "#", matching location.hash). If the stored value ever
  // misses the "#", the handler misclassifies the navigation as user-driven
  // and clears the just-set import notice.
  const baseFetch = vi.mocked(fetch);
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.includes("/local/imports") && init?.method === "POST")
      return response({ import: { content_id: "video-9", filename: "note.txt", status: "READY", duplicate: false } });
    if (input.endsWith("/videos/video-9"))
      return response({ ...daVideoDetail, video: { ...daVideoDetail.video, video_id: "video-9" } });
    if (input.endsWith("/sources")) return response({ sources: [] });
    if (input.endsWith("/videos")) return response({ videos: [] });
    return baseFetch(input, init);
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  fireEvent.click((await screen.findAllByRole("button", { name: "Add Source" }))[1]);
  fireEvent.click(screen.getByRole("button", { name: "Import local file" }));
  const file = new File(["hello"], "note.txt", { type: "text/plain" });
  fireEvent.change(screen.getByLabelText("Choose local files"), { target: { files: [file] } });

  const hashes: string[] = [];
  const trackHash = () => hashes.push(location.hash);
  window.addEventListener("hashchange", trackHash);
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));

  // The import succeeds: onImported() sets imported=true and openContent()
  // assigns location.hash. The notice must render...
  await screen.findByText("File imported. Its processing status appears below.");
  // ...and the hashchange fired by openContent() must be recognized as
  // programmatic navigation, so the notice is not cleared.
  await waitFor(() => expect(hashes).toContain("#Content/video-9"));
  window.removeEventListener("hashchange", trackHash);
  expect(location.hash).toBe("#Content/video-9");
  expect(screen.getByText("File imported. Its processing status appears below.")).toBeTruthy();
});


test("queued stale hash events do not clear the current imported detail", async () => {
  const baseFetch = vi.mocked(fetch);
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input.includes("/local/imports") && init?.method === "POST")
      return response({ import: { content_id: "video-9", filename: "note.txt", status: "READY", duplicate: false } });
    if (input.endsWith("/videos/video-9")) return response({ ...daVideoDetail, video: { ...daVideoDetail.video, video_id: "video-9" } });
    return baseFetch(input, init);
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Following" }));
  const addButtons = await screen.findAllByRole("button", { name: "Add Source" });
  fireEvent.click(addButtons[addButtons.length - 1]);
  fireEvent.click(screen.getByRole("button", { name: "Import local file" }));
  fireEvent.change(screen.getByLabelText("Choose local files"), { target: { files: [new File(["hello"], "note.txt", { type: "text/plain" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  await screen.findByText("File imported. Its processing status appears below.");
  window.dispatchEvent(new HashChangeEvent("hashchange", { newURL: "http://localhost/#Following" }));
  expect(screen.getByText("File imported. Its processing status appears below.")).toBeTruthy();
  expect(location.hash).toBe("#Content/video-9");
});

test("transcription setup deep links reach Settings and return to the exact Content", async () => {
  location.hash = "Settings/transcription/video-1";
  const base = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/local/transcription/capability")
    ? response({ capability: { state: "MODEL_MISSING", runtime_available: true, model_present: false, production_eligible: false } })
    : base(path, init)));
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Local audio and video transcription" })).toBeTruthy();
  fireEvent.click(screen.getByRole("link", { name: "Back to Content" }));
  expect(await screen.findByRole("heading", { name: "Transformers, the tech behind LLMs | Deep Learning Chapter 5" })).toBeTruthy();
  expect(location.hash).toBe("#Content/video-1");
  expect(within(screen.getByRole("navigation")).getAllByRole("button")).toHaveLength(6);
});

test("cancelling language drafts writes nothing and keeps the current interface", async () => {
  const fetch = vi.mocked(globalThis.fetch);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(await screen.findByRole("button", { name: "Edit language" }));
  fireEvent.change(screen.getByLabelText("Interface language"), { target: { value: "zh-CN" } });
  fireEvent.change(screen.getByLabelText("Preferred output language"), { target: { value: "en" } });
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.getByRole("button", { name: "Settings" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Edit language" })).toBeTruthy();
  expect(fetch.mock.calls.some(([, options]) => options?.method === "PUT")).toBe(false);
});

test("Content list, detail, and browser history share the canonical deep link", async () => {
  location.hash = "Content";
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Transformers, the tech behind LLMs/ }));
  await screen.findByRole("heading", { name: "Transformers, the tech behind LLMs | Deep Learning Chapter 5" });
  expect(location.hash).toBe("#Content/video-1");
  location.hash = "Content";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  await screen.findByRole("button", { name: /Transformers, the tech behind LLMs/ });
  location.hash = "Content/video-1";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  fireEvent.click(await screen.findByRole("button", { name: "Back to Content" }));
  expect(location.hash).toBe("#Content");
  expect(await screen.findByRole("button", { name: /Transformers, the tech behind LLMs/ })).toBeTruthy();
});

test("Chinese Backup rejects invalid files with localized recovery guidance", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.change(await screen.findByLabelText("选择备份文件"), { target: { files: [new File(["text"], "note.txt")] } });
  expect((await screen.findByRole("alert")).textContent).toBe("请选择 Intelligence 生成的 ZIP 备份文件。");
});

test("Backup inspection errors remain visible after a successful readiness refresh", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const base = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/backup-restore/status")) return response({ status: { ready: true, reasons: [], restore_pending: false } });
    if (path.endsWith("/restore/stage")) return Promise.resolve({ ok: false, status: 409, json: async () => ({ error: { code: "BACKUP_RESTORE_REJECTED", message: "Backup archive is invalid or truncated." } }) });
    return base(path, init);
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.change(await screen.findByLabelText("选择备份文件"), { target: { files: [new File(["broken"], "broken.zip", { type: "application/zip" })] } });
  await waitFor(() => expect(screen.getByRole("button", { name: "创建备份" }).hasAttribute("disabled")).toBe(false));
  expect((await screen.findByRole("alert")).textContent).toBe("备份检查未通过，请选择完整的 Intelligence ZIP 备份；当前数据未改变。");
  expect(screen.queryByRole("button", { name: "恢复此备份…" })).toBeNull();
});

test("a disconnected local service gives Chinese recovery guidance and a retry action", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = "Content";
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  render(<App />);
  expect(await screen.findByText("本地服务未连接。请重新打开 Intelligence，连接恢复后点击重试。")).toBeTruthy();
  expect(screen.getByRole("button", { name: "重试" })).toBeTruthy();
  expect(screen.queryByText("Failed to fetch")).toBeNull();
});

test.each(["en", "zh-CN"])("%s empty restart response offers a bounded Content read reload and clears on recovery", async (language) => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = "Content/video-1";
  let available = false;
  let reads = 0;
  const writes: string[] = [];
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") writes.push(path);
    if (path.endsWith("/videos")) return response({ videos: [{ ...daVideoDetail.video, processing_status: "ORGANIZED" }] });
    if (path.endsWith("/videos/video-1")) {
      reads += 1;
      return available ? response({ ...daVideoDetail, video: { ...daVideoDetail.video, processing_status: "ORGANIZED" } })
        : Promise.resolve(new Response("", { status: 500 }));
    }
    return original(path, init);
  }));
  render(<App />);
  const copy = language === "en"
    ? "The local service is temporarily unavailable. Wait for it to recover, then reload this page."
    : "本地服务暂时不可用。请等待服务恢复，再重新加载此页面。";
  expect(await screen.findByText(copy)).toBeTruthy();
  expect(document.body.textContent).not.toContain("Unexpected end of JSON input");
  const label = language === "en" ? "Reload page data" : "重新加载页面数据";
  expect(reads).toBe(1);
  fireEvent.click(screen.getByRole("button", { name: label }));
  expect(await screen.findByText(copy)).toBeTruthy();
  expect(reads).toBe(2); // Still offline; there is no automatic retry loop.
  available = true;
  fireEvent.click(screen.getByRole("button", { name: label }));
  expect(await screen.findByText("Original transcript evidence.")).toBeTruthy();
  expect(reads).toBe(3);
  expect(screen.queryByText(copy)).toBeNull();
  expect(writes).toEqual([]);
});

test("page read reload preserves an open import draft and does not replay Following mutations", async () => {
  location.hash = "Following";
  let unavailable = false;
  const writes: string[] = [];
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") writes.push(path);
    if (path.endsWith("/sources") && unavailable) return Promise.resolve(new Response("", { status: 500 }));
    return original(path, init);
  }));
  render(<App />);
  fireEvent.click((await screen.findAllByRole("button", { name: "Add Source" }))[0]);
  const draft = "https://www.youtube.com/@my-unsaved-channel";
  fireEvent.change(screen.getByLabelText("Paste link"), { target: { value: draft } });
  unavailable = true;
  fireEvent(window, new Event("focus"));
  await screen.findByText("The local service is temporarily unavailable. Wait for it to recover, then reload this page.");
  const priorWrites = [...writes];
  unavailable = false;
  fireEvent.click(screen.getByRole("button", { name: "Reload page data" }));
  await screen.findAllByRole("button", { name: "Add Source" });
  expect((screen.getByLabelText("Paste link") as HTMLInputElement).value).toBe(draft);
  expect(writes).toEqual(priorWrites);
});

test("a failed page read does not leave its error on a different route", async () => {
  location.hash = "Content";
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => path.endsWith("/videos")
    ? Promise.resolve(new Response("", { status: 500 })) : original(path, init)));
  render(<App />);
  await screen.findByText("The local service is temporarily unavailable. Wait for it to recover, then reload this page.");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  await screen.findByRole("heading", { name: "Language" });
  expect(screen.queryByText("The local service is temporarily unavailable. Wait for it to recover, then reload this page.")).toBeNull();
});

 test("global style-only save preserves each literal comma and internal whitespace rule", async () => {
  const defaultFetch = globalThis.fetch;
  const original = {initial_history_count:3,per_run_max_new_videos:10,focus_rules:["robotics, autonomy","产品，案例","first\n  second\tkept","CRLF\r\nkept"],ignore_rules:["ads, promo","广告，推广"],distillation_style:"BALANCED"};
  const writes: Record<string, unknown>[] = [];
  vi.stubGlobal("fetch",vi.fn((path:string,init?:RequestInit)=>{
    if(path.endsWith("/settings/source-policy")) {
      if(init?.method==="PUT"){writes.push(JSON.parse(String(init.body)));return response({});}
      return response({policy:original});
    }
    return defaultFetch(path,init);
  }));
  render(<App/>);fireEvent.click(screen.getByRole("button",{name:"Settings"}));
  fireEvent.click(await screen.findByRole("button",{name:"Edit interests"}));
  fireEvent.change(screen.getByLabelText("Insight style"),{target:{value:"TECHNICAL_DETAIL_FIRST"}});
  fireEvent.click(screen.getByRole("button",{name:"Save preferences"}));
  await waitFor(()=>expect(writes).toHaveLength(1));
  expect(writes[0].focus_rules).toEqual(original.focus_rules);expect(writes[0].ignore_rules).toEqual(original.ignore_rules);
 });

test("cloud Intelligence confirms the preview ticket while keeping the input hash distinct", async () => {
  const defaultFetch = globalThis.fetch;
  const confirmations: object[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    if (input.endsWith("/cloud-intelligence/review")) return response({ review: {
      execution_id: "read-only-preview", verified_input_hash: "a".repeat(64), review_hash: "b".repeat(64),
      video_id: "video-1", source_id: "source-1", provider: "offline-only", model: "offline-model", evidence_ids: ["evidence-1"], cost_status: "UNKNOWN",
      expires_at: new Date(Date.now() + 300_000).toISOString(), output_language: "en",
      readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" },
      outgoing_data: { video_id: "video-1", output_language: "en", evidence: [{ evidence_id: "evidence-1", excerpt: "Offline verified excerpt." }], personalization: [], source_focus_rules: [], source_ignore_rules: [], distillation_style: "BALANCED" },
      outgoing_request: { model: "offline-model", max_tokens: 8192 },
    } });
    if (input.endsWith("/cloud-intelligence/confirm")) {
      confirmations.push(JSON.parse(String(init?.body)));
      return response({});
    }
    const result = await defaultFetch(input, init);
    if (input.endsWith("/videos/video-1")) {
      const data = await result.json();
      return response({ ...data, video: { ...data.video, provider: "YOUTUBE" },
      cloud_intelligence_available: true,
      note: { v2: { status: "AVAILABLE", language: "en", summary: "Read-only preview fixture." } },
      intelligence_result: { status: "WAITING_MODEL", execution_id: null, has_new_intelligence: false },
      });
    }
    return result;
  }));
  location.hash = "#Content/video-1";
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  expect(screen.getByText(/Preparing a review does not create a task/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  const confirm = await screen.findByRole("button", { name: "Authorize this one cloud execution" });
  expect(confirmations).toEqual([]);
  fireEvent.click(confirm);
  await waitFor(() => expect(confirmations).toEqual([{
    execution_id: "read-only-preview", review_hash: "b".repeat(64), authorize: true,
  }]));
});


test("BigModel settings deep link opens the exact candidate and returns to Content Evidence", async () => {
  const defaultFetch = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/settings/bigmodel-credential")) return response({ provider: "zhipu_bigmodel", model: "glm-4.7-flash", configured: false, source: "NONE", qualification: "NOT_VERIFIED", budget: "CLOSED" });
    return defaultFetch(path, init);
  }));
  location.hash = "#Settings/models/bigmodel?return=%23Content%2Fvideo-1%2FEvidence%2Fevidence-1";
  render(<App />);
  await screen.findByText("Not configured");
  await waitFor(() => expect(document.activeElement?.id).toBe("bigmodel-settings"));
  expect(document.getElementById("bigmodel-settings")?.getAttribute("open")).not.toBeNull();
  expect(screen.getByRole("link", { name: "Back to Content" }).getAttribute("href")).toBe("#Content/video-1/Evidence/evidence-1");
  expect(screen.getAllByRole("navigation")[0].querySelectorAll("button")).toHaveLength(6);
});
