import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { Research } from "./Research";
import { UiLanguageProvider } from "./uiLanguage";

const okJson = (body: unknown, status = 200) =>
  Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);

beforeEach(() => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

describe("Workspace AI Upgrade (P0 + P1 + P2)", () => {
  it("renders Weekly AI Brief on Home with Shorts funnel stats, clickable picks, and Obsidian wikilinks copy", async () => {
    location.hash = "#Home";
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    const weeklyBrief = {
      brief_id: "weekly-2026-w46",
      week_label: "2026-11-09 至 2026-11-15",
      title_zh: "《本周 AI 产品与商业情报周报》",
      executive_summary_zh:
        "本周 OpenAI 聚焦可审计工具契约，Greg Isenberg 与本地实战课共同指向垂直工作流一人公司变现。",
      core_trends_zh: ["Agent 工程从对话形态转向状态机编排与确定性评测"],
      product_opportunities_zh: ["为垂直 SaaS 嵌入带人工确认节点的本地优先 Agent"],
      business_opportunities_zh: ["围绕高频行业合规审校切入高客单价年费订阅"],
      must_watch_picks: [
        {
          video_id: "vidLong0001",
          title: "Building Reliable AI Agents in Production",
          channel_name: "OpenAI",
          score: 9.4,
          reason_zh: "完整拆解生产级 Agent 工具契约与回滚机制。",
        },
      ],
      funnel_stats: {
        total_videos: 112,
        distilled_count: 112,
        must_watch_count: 18,
        shorts_filtered_count: 64,
        local_courses_count: 3,
      },
      obsidian_markdown:
        "# 《本周 AI 产品与商业情报周报》\n\n- 关联主题：[[AI Agent 与自动化架构]]\n- 必看：[[Building Reliable AI Agents in Production]]",
      provider: "ollama",
      model: "qwen3.5:9b",
      created_at: "2026-11-13T10:00:00Z",
    };

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/weekly-brief/generate") && init?.method === "POST") {
        return okJson({
          weekly_brief: {
            ...weeklyBrief,
            executive_summary_zh: "已刷新：最新跨源 AI 产品周报结论。",
          },
        });
      }
      if (input.endsWith("/dashboard")) {
        return okJson({
          intelligence: [],
          pinned_topics: [
            {
              topic_id: "topic-agent",
              name: "AI Agent 与自动化架构",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "CONFIRMED",
              independence: "SINGLE_SOURCE",
              contributions: [],
              timeline: [],
              relations: [],
            },
          ],
          needs_attention: [],
          operations: { source_count: 3 },
          workspace_weekly_brief: weeklyBrief,
        });
      }
      if (input.includes("/changes/recent")) {
        return okJson({
          window: {
            start_at: "2026-11-06T00:00:00Z",
            end_at: "2026-11-13T00:00:00Z",
            timezone: "Asia/Shanghai",
            days: 7,
          },
          status: "COMPLETE",
          degraded_sections: [],
          counts: {
            intelligence_added: 0,
            intelligence_updated: 0,
            topics_changed: 0,
            content_processed: 0,
            sources_needing_attention: 0,
          },
          groups: {
            intelligence_added: [],
            intelligence_updated: [],
            topics_changed: [],
            content_processed: [],
            sources_needing_attention: [],
          },
        });
      }
      if (input.endsWith("/videos/vidLong0001")) {
        return okJson({
          video: {
            video_id: "vidLong0001",
            provider: "YOUTUBE",
            channel_id: "UC1111111111111111111111",
            channel_name: "OpenAI",
            title: "Building Reliable AI Agents in Production",
            source_url: "https://www.youtube.com/watch?v=vidLong0001",
            published_at: "2026-11-12T08:00:00Z",
            processing_status: "READY",
            last_updated: "2026-11-13T08:00:00Z",
          },
          transcript: { status: "AVAILABLE", text: "Tool contracts." },
          note: { v2: { status: "UNAVAILABLE" } },
          intelligence_result: {
            status: "SUCCEEDED",
            execution_id: "exec-1",
            has_new_intelligence: true,
            intelligence_id: "intelligence:workspace-ai:vidLong0001",
            revision_id: "r1",
            updated_at: "2026-11-13T08:00:00Z",
          },
          history: [],
        });
      }
      if (input.endsWith("/evidence")) return okJson({ evidence: [] });
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByText("《本周 AI 产品与商业情报周报》")).toBeTruthy();
    expect(screen.getByText(/自动折叠 64 条 Shorts/)).toBeTruthy();
    expect(screen.getByText(/本周 OpenAI 聚焦可审计工具契约/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "复制双链周报" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("[[AI Agent 与自动化架构]]"));

    fireEvent.click(screen.getByRole("button", { name: "重新生成周报" }));
    expect(await screen.findByText("已刷新：最新跨源 AI 产品周报结论。")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Building Reliable AI Agents in Production/ }));
    await waitFor(() => expect(location.hash).toBe("#Content/vidLong0001"));
  });

  it("folds <=90s Shorts noise in Content library while surfacing 0-10 scores, Chinese headlines, and filter pills", async () => {
    location.hash = "#Content";
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/videos")) {
          return okJson({
            videos: [
              {
                video_id: "vidShortPromo",
                provider: "YOUTUBE",
                channel_id: "UC1111111111111111111111",
                channel_name: "OpenAI",
                title: "Sora 30s Visual Teaser #shorts",
                published_at: "2026-11-13T09:00:00Z",
                processing_status: "ORGANIZED",
                last_updated: "2026-11-13T09:00:00Z",
                duration_seconds: 32,
                ai_brief: {
                  video_id: "vidShortPromo",
                  headline_zh: "纯视觉效果展示短片，无产品架构与技术增量。",
                  summary_zh: "32 秒视觉预热短片。",
                  score: 2.8,
                  score_reason_zh: "低于 90 秒纯宣发短片。",
                  recommendation_tier: "SKIP_NOISE",
                  content_bucket: "SHORTS_PROMO",
                  is_short_noise: true,
                  topics_zh: ["视频生成"],
                  topic_cluster_zh: "多模态生成与交互产品",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vidDeepDive",
                provider: "YOUTUBE",
                channel_id: "UC1111111111111111111111",
                channel_name: "Greg Isenberg",
                title: "How to Build a $1M AI Micro-SaaS in 2026",
                published_at: "2026-11-12T09:00:00Z",
                processing_status: "READY",
                last_updated: "2026-11-12T09:00:00Z",
                duration_seconds: 2450,
                ai_brief: {
                  video_id: "vidDeepDive",
                  headline_zh: "一人公司切入高毛利 AI SaaS 的关键是绑定行业存量高痛点表单流。",
                  summary_zh: "详细拆解选品、冷启动获客与按结果定价模型。",
                  score: 9.3,
                  score_reason_zh: "包含完整获客漏斗与定价实操。",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  topics_zh: ["一人公司", "AI SaaS"],
                  topic_cluster_zh: "一人公司与 AI 商业变现",
                  product_opportunities_zh: ["高频 PDF 表单自动核验流水线"],
                  business_opportunities_zh: ["按席位+处理单量阶梯年费"],
                },
              },
              {
                video_id: "vidLocalCourse",
                provider: "LOCAL",
                media_kind: "VIDEO",
                format: "mp4",
                channel_id: "local",
                channel_name: "Local",
                title: "3. Agent.mp4",
                published_at: "2026-11-11T09:00:00Z",
                processing_status: "READY",
                last_updated: "2026-11-11T09:00:00Z",
                duration_seconds: 5052,
                ai_brief: {
                  video_id: "vidLocalCourse",
                  headline_zh: "系统讲解 ReAct 与状态机 Agent 的工程边界及避坑清单。",
                  summary_zh: "84 分钟本地中文实战课。",
                  score: 9.5,
                  score_reason_zh: "一手中文工程实战拆解。",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "TUTORIAL",
                  is_short_noise: false,
                  topics_zh: ["AI Agent", "状态机"],
                  topic_cluster_zh: "AI Agent 与自动化架构",
                  product_opportunities_zh: ["可视化工作流断点回放"],
                  business_opportunities_zh: ["企业私有化 Agent 交付模板"],
                },
              },
            ],
          });
        }
        return okJson({});
      }),
    );

    render(<App />);
    expect(await screen.findByText("3. Agent.mp4")).toBeTruthy();
    expect(screen.getByText(/系统讲解 ReAct 与状态机 Agent/)).toBeTruthy();
    expect(screen.getByText(/9\.5/)).toBeTruthy();
    expect(screen.getByText(/已自动折叠 1 条 Shorts/)).toBeTruthy();

    // Filter to Tutorials only
    fireEvent.click(screen.getByRole("button", { name: /实操教程/ }));
    expect(screen.getByText("3. Agent.mp4")).toBeTruthy();
    expect(screen.queryByText("How to Build a $1M AI Micro-SaaS in 2026")).toBeNull();

    // Filter to Shorts explicitly -> reveals the Short item cleanly
    fireEvent.click(screen.getByRole("button", { name: /Shorts 短片/ }));
    expect(screen.getByText("Sora 30s Visual Teaser #shorts")).toBeTruthy();
    expect(screen.queryByText("3. Agent.mp4")).toBeNull();
  });

  it("supports 1-click offline local .mp4 transcription + Chinese AI distillation + Obsidian export on Content detail", async () => {
    location.hash = "#Content/localMp4Course1";
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    let transcribed = false;
    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/workspace-ai/videos/localMp4Course1/transcribe") && init?.method === "POST") {
        transcribed = true;
        return okJson({
          video_id: "localMp4Course1",
          transcription_status: "READY",
          segment_count: 12,
          ai_brief: {
            video_id: "localMp4Course1",
            headline_zh: "多模态产品落地的核心是将视觉理解嵌入闭环业务动作而非纯聊天。",
            summary_zh: "完整拆解多模态输入校验、延迟优化与商业场景。",
            score: 9.4,
            score_reason_zh: "高密度中文多模态产品实战课。",
            recommendation_tier: "MUST_WATCH",
            content_bucket: "TUTORIAL",
            is_short_noise: false,
            topics_zh: ["多模态", "产品实战"],
            topic_cluster_zh: "多模态生成与交互产品",
            product_opportunities_zh: ["拍照即录单的移动端多模态助手"],
            business_opportunities_zh: ["跨境电商多语言商品图合规巡检 SaaS"],
            obsidian_markdown:
              "# 4. 多模态产品实战.mp4\n\n- 主题：[[多模态生成与交互产品]]\n- 结论：多模态产品落地的核心是将视觉理解嵌入闭环业务动作而非纯聊天。",
          },
        });
      }
      if (input.endsWith("/videos/localMp4Course1")) {
        return okJson({
          video: {
            video_id: "localMp4Course1",
            provider: "LOCAL",
            media_kind: "VIDEO",
            format: "mp4",
            channel_id: "local",
            channel_name: "Local",
            title: "4. 多模态产品实战.mp4",
            source_url: null,
            published_at: "2026-11-12T08:00:00Z",
            processing_status: transcribed ? "READY" : "TRANSCRIPTION_UNAVAILABLE",
            last_updated: "2026-11-13T08:00:00Z",
            duration_seconds: 1528,
            ...(transcribed
              ? {
                  ai_brief: {
                    video_id: "localMp4Course1",
                    headline_zh: "多模态产品落地的核心是将视觉理解嵌入闭环业务动作而非纯聊天。",
                    summary_zh: "完整拆解多模态输入校验、延迟优化与商业场景。",
                    score: 9.4,
                    score_reason_zh: "高密度中文多模态产品实战课。",
                    recommendation_tier: "MUST_WATCH",
                    content_bucket: "TUTORIAL",
                    is_short_noise: false,
                    topics_zh: ["多模态", "产品实战"],
                    topic_cluster_zh: "多模态生成与交互产品",
                    product_opportunities_zh: ["拍照即录单的移动端多模态助手"],
                    business_opportunities_zh: ["跨境电商多语言商品图合规巡检 SaaS"],
                    obsidian_markdown:
                      "# 4. 多模态产品实战.mp4\n\n- 主题：[[多模态生成与交互产品]]\n- 结论：多模态产品落地的核心是将视觉理解嵌入闭环业务动作而非纯聊天。",
                  },
                }
              : {}),
          },
          transcript: transcribed
            ? {
                status: "AVAILABLE",
                text: "多模态产品实战第一课。",
                timed_segments: [{ start_ms: 0, end_ms: 5000, text: "多模态产品实战第一课。" }],
              }
            : { status: "TRANSCRIPTION_UNAVAILABLE" },
          note: {
            v2: transcribed
              ? {
                  status: "AVAILABLE",
                  language: "zh-CN",
                  method: "MODEL_SUMMARY",
                  summary: "完整拆解多模态输入校验、延迟优化与商业场景。",
                  core_points: ["将视觉理解嵌入闭环动作"],
                  timestamped_key_points: [],
                  evidence_references: [],
                }
              : { status: "UNAVAILABLE" },
          },
          intelligence_result: {
            status: transcribed ? "SUCCEEDED" : "NOT_PROCESSED",
            execution_id: null,
            has_new_intelligence: transcribed ? true : null,
            intelligence_id: transcribed ? "intelligence:workspace-ai:localMp4Course1" : null,
            revision_id: transcribed ? "r1" : null,
            updated_at: null,
          },
          history: [],
          ...(transcribed
            ? {
                obsidian_markdown:
                  "# 4. 多模态产品实战.mp4\n\n- 主题：[[多模态生成与交互产品]]\n- 结论：多模态产品落地的核心是将视觉理解嵌入闭环业务动作而非纯聊天。",
              }
            : {}),
        });
      }
      if (input.endsWith("/transcription")) {
        return okJson({ transcription: { status: transcribed ? "READY" : "MODEL_MISSING", can_start: false } });
      }
      if (input.endsWith("/evidence")) return okJson({ evidence: [] });
      if (input.endsWith("/deep-analysis")) {
        return okJson({
          deep_analysis: {
            status: {
              availability: "NOT_QUALIFIED",
              reason_code: "NO_QUALIFIED_MODEL",
              reason: null,
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
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const txBtn = await screen.findByRole("button", { name: "离线语音转写并提炼中文洞察" });
    fireEvent.click(txBtn);

    expect(
      (await screen.findAllByText(/多模态产品落地的核心是将视觉理解嵌入闭环业务动作而非纯聊天/)).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("拍照即录单的移动端多模态助手")).toBeTruthy();
    expect(screen.getByText("跨境电商多语言商品图合规巡检 SaaS")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "复制双链笔记" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("[[多模态生成与交互产品]]"));
  });

  it("answers Cross-Video Grounded Chinese AI questions in Research and jumps to exact video Evidence on citation click", async () => {
    location.hash = "#Research";
    const onOpen = vi.fn();

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/research/sessions") && !init?.method) {
          return okJson({
            sessions: [],
            suggested_questions: [
              "OpenAI、Greg Isenberg 与本地实战课对 AI Agent 落地有什么共识与分歧？",
            ],
          });
        }
        if (input.endsWith("/workspace-ai/research/ask") && init?.method === "POST") {
          return okJson({
            session: {
              session_id: "qa-session-01",
              question: "OpenAI、Greg Isenberg 与本地实战课对 AI Agent 落地有什么共识与分歧？",
              answer_zh:
                "三方一致认为高可靠 AI Agent 必须建立在严格工具契约与状态机之上 [E1]，而商业变现应优先切入垂直行业工作流而非通用聊天 [E2]。",
              key_takeaways_zh: [
                "技术底座：工具 Schema 契约 + 确定性状态机 [E1]",
                "商业切口：垂直工作流按结果收费 [E2]",
              ],
              citations: [
                {
                  ref_label: "E1",
                  video_id: "vidOpenAI01",
                  video_title: "OpenAI Agent Architecture Roundtable",
                  channel_name: "OpenAI",
                  evidence_id: "ev_openai_001",
                  start_ms: 15000,
                  end_ms: 28000,
                  timestamp_label: "00:15",
                  excerpt: "Tool contracts and deterministic evals are foundational.",
                },
                {
                  ref_label: "E2",
                  video_id: "vidCourse02",
                  video_title: "3. Agent.mp4",
                  channel_name: "Local",
                  evidence_id: "ev_course_002",
                  start_ms: 300000,
                  end_ms: 318000,
                  timestamp_label: "05:00",
                  excerpt: "一人公司做垂直工作流比做通用问答更容易收年费。",
                },
              ],
              obsidian_markdown: "# AI 跨视频深度问答\n\n- [[OpenAI Agent Architecture Roundtable]]",
              provider: "ollama",
              model: "qwen3.5:9b",
              created_at: "2026-11-13T10:30:00Z",
            },
          });
        }
        if (input === "/api/v1/research" && !init?.method) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    render(
      <UiLanguageProvider>
        <Research onOpen={onOpen} />
      </UiLanguageProvider>,
    );

    const suggestedBtn = await screen.findByRole("button", {
      name: "OpenAI、Greg Isenberg 与本地实战课对 AI Agent 落地有什么共识与分歧？",
    });
    fireEvent.click(suggestedBtn);

    expect(
      await screen.findByText(/三方一致认为高可靠 AI Agent 必须建立在严格工具契约与状态机之上/),
    ).toBeTruthy();

    const citationBtn = screen.getByRole("button", {
      name: /\[E1\].*OpenAI Agent Architecture Roundtable.*00:15/,
    });
    fireEvent.click(citationBtn);
    expect(onOpen).toHaveBeenCalledWith("content", "vidOpenAI01", "ev_openai_001");
  });

  it("configures Local Ollama vs BYOK Cloud Engine in Settings without leaking API keys or firing extra mount GETs", async () => {
    location.hash = "#Settings";
    const writes: { path: string; body: Record<string, unknown> }[] = [];

    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/workspace-ai/settings") && init?.method === "PUT") {
        const parsed = JSON.parse(String(init.body));
        writes.push({ path, body: parsed });
        return okJson({
          active_mode: parsed.active_mode ?? "cloud_byok",
          ollama_base_url: "http://127.0.0.1:11434",
          ollama_model: "qwen3.5:9b",
          ollama_reachable: true,
          installed_ollama_models: ["qwen3.5:9b", "qwen3:8b"],
          cloud_provider: parsed.cloud_provider ?? "deepseek",
          cloud_base_url: parsed.cloud_base_url ?? "https://api.deepseek.com/v1",
          cloud_model: parsed.cloud_model ?? "deepseek-chat",
          cloud_key_configured: Boolean(parsed.cloud_api_key),
        });
      }
      if (path.endsWith("/workspace-ai/settings")) {
        return okJson({
          active_mode: "local_ollama",
          ollama_base_url: "http://127.0.0.1:11434",
          ollama_model: "qwen3.5:9b",
          ollama_reachable: true,
          installed_ollama_models: ["qwen3.5:9b", "qwen3:8b"],
          cloud_provider: "deepseek",
          cloud_base_url: "https://api.deepseek.com/v1",
          cloud_model: "deepseek-chat",
          cloud_key_configured: false,
        });
      }
      if (path.endsWith("/settings/local-intelligence")) {
        return okJson({
          local_intelligence: {
            status: "NOT_CONFIGURED",
            etag: "b".repeat(64),
            selected_candidate_id: null,
            actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null },
            blocking_work: [],
            candidates: [],
          },
        });
      }
      if (path.endsWith("/settings")) {
        return okJson({
          general: {
            timezone: "Asia/Shanghai",
            output_language: "zh-CN",
            output_language_source: "USER",
            output_language_updated_at: null,
          },
          providers: [],
          cloud_credential: { configured: false, source: "NONE" },
        });
      }
      if (path.endsWith("/settings/preferences")) return okJson({ active: [], history: [] });
      if (path.endsWith("/settings/source-policy")) {
        return okJson({
          policy: {
            initial_history_count: 5,
            per_run_max_new_videos: 5,
            focus_rules: [],
            ignore_rules: [],
            distillation_style: "BALANCED",
          },
        });
      }
      if (path.endsWith("/settings/resource-usage")) return okJson({ usage: [] });
      if (path.endsWith("/settings/local-models")) return okJson({ connection: "REACHABLE", models: [] });
      if (path.endsWith("/local/transcription/capability")) {
        return okJson({ capability: { state: "READY", runtime_available: true, model_present: true } });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const configBtn = await screen.findByRole("button", { name: "配置 AI 摘要与问答引擎" });
    // Before opening, zero /workspace-ai/settings requests fired on mount!
    expect(fetchMock.mock.calls.some(([p]) => String(p).includes("/workspace-ai/settings"))).toBe(false);

    fireEvent.click(configBtn);
    const panel = (await screen.findByText("AI 摘要、评分与跨视频问答引擎")).closest("section")!;
    fireEvent.change(within(panel).getByLabelText("运行模式"), { target: { value: "cloud_byok" } });
    const keyInput = within(panel).getByLabelText("云端 API Key（仅存 macOS 钥匙串）") as HTMLInputElement;
    fireEvent.change(keyInput, { target: { value: "sk-live-secret-999" } });
    fireEvent.click(within(panel).getByRole("button", { name: "保存 AI 引擎配置" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0].body.active_mode).toBe("cloud_byok");
    expect(writes[0].body.cloud_api_key).toBe("sk-live-secret-999");
    await waitFor(() => expect(keyInput.value).toBe(""));
    expect(JSON.stringify(localStorage)).not.toContain("sk-live-secret-999");
  });

  it("launches Cross-Video AI Q&A from global utility dock or Cmd+K palette while keeping 6-item primary navigation intact", async () => {
    location.hash = "#Home";
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/dashboard")) {
          return okJson({
            intelligence: [],
            pinned_topics: [],
            needs_attention: [],
            operations: { source_count: 2 },
          });
        }
        if (input.includes("/changes/recent")) {
          return okJson({
            window: {
              start_at: "2026-11-06T00:00:00Z",
              end_at: "2026-11-13T00:00:00Z",
              timezone: "Asia/Shanghai",
              days: 7,
            },
            status: "COMPLETE",
            degraded_sections: [],
            counts: {
              intelligence_added: 0,
              intelligence_updated: 0,
              topics_changed: 0,
              content_processed: 0,
              sources_needing_attention: 0,
            },
            groups: {
              intelligence_added: [],
              intelligence_updated: [],
              topics_changed: [],
              content_processed: [],
              sources_needing_attention: [],
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({ sessions: [], suggested_questions: ["跨视频测试问题？"] });
        }
        if (input.includes("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    render(<App />);
    const primaryNav = await screen.findByRole("navigation", { name: "主导航" });
    expect(within(primaryNav).getAllByRole("button")).toHaveLength(6);

    const dock = screen.getByRole("region", { name: "快捷操作" });
    const qaDockBtn = within(dock).getByRole("button", { name: "AI 跨视频问答" });
    fireEvent.click(qaDockBtn);

    await waitFor(() => expect(location.hash).toBe("#Research"));
    expect(await screen.findByRole("region", { name: "AI 跨视频深度问答" })).toBeTruthy();

    // Navigate back to Home, then open Cmd+K and trigger AI Q&A action
    fireEvent.click(within(primaryNav).getByRole("button", { name: "首页" }));
    await waitFor(() => expect(location.hash).toBe("#Home"));

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const cmdOption = await screen.findByRole("option", { name: /AI 跨视频深度问答/ });
    fireEvent.click(cmdOption);
    await waitFor(() => expect(location.hash).toBe("#Research"));
  });

  it("syncs pending unbriefed videos in 1 click, displays honest Metadata-only badges, and supports captionless YouTube preview distillation", async () => {
    location.hash = "#Content";
    let synced = false;

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/workspace-ai/sync-pending") && init?.method === "POST") {
        synced = true;
        return okJson({
          processed_count: 1,
          processed: [{ video_id: "vidNewNoCap", source_basis: "METADATA_ONLY", score: 5.8 }],
          errors: [],
          sync_status: { total_videos: 2, briefed_count: 2, pending_count: 0 },
        });
      }
      if (input.endsWith("/workspace-ai/videos/vidNewNoCap/distill") && init?.method === "POST") {
        synced = true;
        return okJson({
          ai_brief: {
            video_id: "vidNewNoCap",
            source_basis: "METADATA_ONLY",
            headline_zh: "基于官方简介：展示 Firefox 安全漏洞自动定位与补丁验证流程。",
            summary_zh: "官方暂未开放英文字幕，本速览仅依据视频标题与频道简介提炼，不含时间轴引用。",
            score: 6.2,
            score_reason_zh: "原视频暂无字幕，基于官方简介生成速览。",
            recommendation_tier: "WORTH_SKIMMING",
            content_bucket: "DEEP_DIVE",
            is_short_noise: false,
            topics_zh: ["网络安全", "自动化补丁"],
            topic_cluster_zh: "AI Agent 与自动化架构",
            product_opportunities_zh: [],
            business_opportunities_zh: [],
          },
        });
      }
      if (input.endsWith("/videos")) {
        return okJson({
          videos: [
            {
              video_id: "vidReady1",
              provider: "YOUTUBE",
              channel_id: "UC1111111111111111111111",
              channel_name: "OpenAI",
              title: "Structured Outputs Deep Dive",
              published_at: "2026-11-12T08:00:00Z",
              processing_status: "ORGANIZED",
              last_updated: "2026-11-12T08:00:00Z",
              duration_seconds: 1200,
              ai_brief: {
                video_id: "vidReady1",
                source_basis: "TRANSCRIPT",
                headline_zh: "严格 JSON Schema 契约消除生产环境工具调用解析失败。",
                summary_zh: "带完整字幕验证的深度技术分享。",
                score: 9.1,
                score_reason_zh: "一手工程架构。",
                recommendation_tier: "MUST_WATCH",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                topics_zh: ["Schema"],
                topic_cluster_zh: "AI Agent 与自动化架构",
                product_opportunities_zh: [],
                business_opportunities_zh: [],
              },
            },
            {
              video_id: "vidNewNoCap",
              provider: "YOUTUBE",
              channel_id: "UC1111111111111111111111",
              channel_name: "OpenAI",
              title: "Live Security Demo (No Captions Yet)",
              published_at: "2026-11-14T08:00:00Z",
              processing_status: "METADATA_READY",
              last_updated: "2026-11-14T08:00:00Z",
              duration_seconds: 860,
              ...(synced
                ? {
                    ai_brief: {
                      video_id: "vidNewNoCap",
                      source_basis: "METADATA_ONLY",
                      headline_zh: "基于官方简介：展示 Firefox 安全漏洞自动定位与补丁验证流程。",
                      summary_zh:
                        "官方暂未开放英文字幕，本速览仅依据视频标题与频道简介提炼，不含时间轴引用。",
                      score: 6.2,
                      score_reason_zh: "原视频暂无字幕，基于官方简介生成速览。",
                      recommendation_tier: "WORTH_SKIMMING",
                      content_bucket: "DEEP_DIVE",
                      is_short_noise: false,
                      topics_zh: ["网络安全"],
                      topic_cluster_zh: "AI Agent 与自动化架构",
                      product_opportunities_zh: [],
                      business_opportunities_zh: [],
                    },
                  }
                : {}),
            },
            {
              video_id: "virtualPendingWork01",
              provider: "YOUTUBE",
              work_kind: "DURABLE_CONTENT_IDENTITY",
              channel_id: null as unknown as string,
              channel_name: null as unknown as string,
              title: "https://www.youtube.com/watch?v=virtualPendingWork01",
              published_at: null as unknown as string,
              processing_status: "NEEDS_ATTENTION",
              last_updated: "2026-11-14T09:00:00Z",
            },
          ],
        });
      }
      if (input.endsWith("/videos/vidNewNoCap")) {
        return okJson({
          video: {
            video_id: "vidNewNoCap",
            provider: "YOUTUBE",
            channel_id: "UC1111111111111111111111",
            channel_name: "OpenAI",
            title: "Live Security Demo (No Captions Yet)",
            source_url: "https://www.youtube.com/watch?v=vidNewNoCap",
            published_at: "2026-11-14T08:00:00Z",
            processing_status: "METADATA_READY",
            last_updated: "2026-11-14T08:00:00Z",
            duration_seconds: 860,
            ai_brief: {
              video_id: "vidNewNoCap",
              source_basis: "METADATA_ONLY",
              headline_zh: "基于官方简介：展示 Firefox 安全漏洞自动定位与补丁验证流程。",
              summary_zh:
                "官方暂未开放英文字幕，本速览仅依据视频标题与频道简介提炼，不含时间轴引用。",
              score: 6.2,
              score_reason_zh: "原视频暂无字幕，基于官方简介生成速览。",
              recommendation_tier: "WORTH_SKIMMING",
              content_bucket: "DEEP_DIVE",
              is_short_noise: false,
              topics_zh: ["网络安全"],
              topic_cluster_zh: "AI Agent 与自动化架构",
              product_opportunities_zh: [],
              business_opportunities_zh: [],
            },
          },
          transcript: { status: "UNAVAILABLE" },
          note: { v2: { status: "UNAVAILABLE" } },
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
      if (input.endsWith("/evidence")) return okJson({ evidence: [] });
      if (input.endsWith("/deep-analysis")) {
        return okJson({
          deep_analysis: {
            status: {
              availability: "NOT_QUALIFIED",
              reason_code: "NO_QUALIFIED_MODEL",
              reason: null,
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
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const syncBtn = await screen.findByRole("button", { name: /一键同步中文摘要/ });
    fireEvent.click(syncBtn);

    expect(await screen.findByText(/基于官方简介：展示 Firefox 安全漏洞自动定位/)).toBeTruthy();
    expect(screen.getByText("简介速览")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /一键同步中文摘要/ })).toBeNull();
    expect(screen.queryByText(/1970/)).toBeNull();

    // Open detail page of the captionless YouTube video
    fireEvent.click(screen.getByRole("button", { name: /Live Security Demo/ }));
    expect(await screen.findByText(/基于标题与官方简介速览/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /重新生成简介中文速览/ })).toBeTruthy();
    // Should NOT render a contradictory "暂无总结 / 视频笔记" empty banner right below the brief card!
    expect(screen.queryByText(/暂无总结.*不会根据缺失输出编造内容/)).toBeNull();
  });

  it("collapses legacy model qualification diagnostics on Settings when workspace_ai is active and exports zero-secret AI backup JSON", async () => {
    location.hash = "#Settings";
    const createObjectURL = vi.fn(() => "blob:workspace-ai-backup");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/workspace-ai/backup")) {
        return okJson({
          schema_version: "workspace-ai-backup-v1",
          exported_at: "2026-11-15T00:00:00Z",
          video_ai_briefs: [{ video_id: "vid1", headline_zh: "备份测试" }],
          weekly_ai_briefs: [],
          ai_research_sessions: [],
        });
      }
      if (path.endsWith("/settings/local-intelligence")) {
        return okJson({
          local_intelligence: {
            status: "NOT_CONFIGURED",
            etag: "b".repeat(64),
            selected_candidate_id: null,
            actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null },
            blocking_work: [],
            candidates: [],
          },
        });
      }
      if (path.endsWith("/settings")) {
        return okJson({
          general: {
            timezone: "Asia/Shanghai",
            output_language: "zh-CN",
            output_language_source: "USER",
            output_language_updated_at: null,
          },
          providers: [],
          cloud_credential: { configured: false, source: "NONE" },
          workspace_ai: {
            active_mode: "local_ollama",
            ollama_base_url: "http://127.0.0.1:11434",
            ollama_model: "qwen3.5:9b",
            ollama_reachable: true,
            installed_ollama_models: ["qwen3.5:9b"],
            cloud_provider: "deepseek",
            cloud_base_url: "https://api.deepseek.com/v1",
            cloud_model: "deepseek-chat",
            cloud_key_configured: false,
          },
        });
      }
      if (path.endsWith("/settings/preferences")) return okJson({ active: [], history: [] });
      if (path.endsWith("/settings/source-policy")) {
        return okJson({
          policy: {
            initial_history_count: 5,
            per_run_max_new_videos: 5,
            focus_rules: [],
            ignore_rules: [],
            distillation_style: "BALANCED",
          },
        });
      }
      if (path.endsWith("/settings/resource-usage")) return okJson({ usage: [] });
      if (path.endsWith("/settings/local-models")) return okJson({ connection: "REACHABLE", models: [] });
      if (path.endsWith("/local/transcription/capability")) {
        return okJson({ capability: { state: "READY", runtime_available: true, model_present: true } });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<App />);
    const aiEnginePanel = await screen.findByRole("region", {
      name: "AI 摘要、评分与跨视频问答引擎",
    });
    expect(aiEnginePanel.id).toBe("settings-models");

    const legacyDrawer = container.querySelector("details.legacy-model-diagnostics") as HTMLDetailsElement | null;
    expect(legacyDrawer).not.toBeNull();
    expect(legacyDrawer?.open).toBe(false);
    expect(
      fetchMock.mock.calls.some(([p]) => String(p).includes("/local/transcription/capability")),
    ).toBe(false);

    const exportBtn = within(aiEnginePanel).getByRole("button", {
      name: "导出 AI 知识库快照 (.json)",
    });
    fireEvent.click(exportBtn);

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([p]) => String(p).endsWith("/workspace-ai/backup"))).toBe(true),
    );
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/已导出 AI 摘要、周报与问答快照/)).toBeTruthy();
  });

  it("supports scoped and multi-video comparative Research Q&A, renders action_items_zh, and collapses legacy non-AI research copy", async () => {
    location.hash = "#Research";
    const askBodies: Record<string, unknown>[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/research/sessions") && !init?.method) {
          return okJson({
            sessions: [],
            suggested_questions: ["对比这两条视频的 Agent 变现路径？"],
            scope_options: {
              channels: [
                { key: "Greg Isenberg", label: "Greg Isenberg", count: 12 },
                { key: "LOCAL", label: "本地实战课", count: 3 },
              ],
              topic_clusters: [{ name: "AI 产品机会与一人公司变现", count: 18 }],
              videos: [
                {
                  video_id: "vidGreg1",
                  title: "Micro-SaaS Playbook",
                  channel_name: "Greg Isenberg",
                  score: 9.2,
                },
                {
                  video_id: "vidLocal1",
                  title: "3. Agent.mp4",
                  channel_name: "本地实战课",
                  score: 9.5,
                },
              ],
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/ask") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body));
          askBodies.push(parsed);
          return okJson({
            session: {
              session_id: "qa-scoped-01",
              question: parsed.question,
              scope_label_zh: "对比已选 2 条视频",
              answer_zh: "两条视频均建议从高频垂直表单切入 [E1] [E2]。",
              key_takeaways_zh: ["优先切入高客单价 B2B 审批流 [E1]"],
              action_items_zh: [
                "本周挑选 1 个行业高频 PDF 审核环节做最小闭环原型",
                "按处理单量设置阶梯年费验证付费意愿",
              ],
              citations: [
                {
                  ref_label: "E1",
                  video_id: "vidGreg1",
                  video_title: "Micro-SaaS Playbook",
                  channel_name: "Greg Isenberg",
                  evidence_id: "ev_g1",
                  start_ms: 12000,
                  end_ms: 24000,
                  timestamp_label: "00:12",
                  excerpt: "Pick one painful B2B PDF workflow.",
                },
              ],
              obsidian_markdown: "# 定向对比问答",
              provider: "ollama",
              model: "qwen3.5:9b",
              created_at: "2026-11-15T01:00:00Z",
            },
          });
        }
        if (input === "/api/v1/research" && !init?.method) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    const { container } = render(
      <UiLanguageProvider>
        <Research onOpen={vi.fn()} />
      </UiLanguageProvider>,
    );

    const sourceChip = await screen.findByRole("button", { name: /本地实战课.*3/ });
    expect(sourceChip).toBeTruthy();

    // Legacy "不调用模型" packet builder must be tucked into a closed <details> drawer when AI sessions load
    const legacyDrawer = container.querySelector(
      "details.legacy-model-diagnostics",
    ) as HTMLDetailsElement | null;
    expect(legacyDrawer).not.toBeNull();
    expect(legacyDrawer?.open).toBe(false);

    // Open multi-video comparison picker and select both videos
    const compareToggle = screen.getByRole("button", { name: /指定多视频对比/ });
    fireEvent.click(compareToggle);
    fireEvent.click(screen.getByLabelText(/Micro-SaaS Playbook/));
    fireEvent.click(screen.getByLabelText(/3\. Agent\.mp4/));

    const input = screen.getByLabelText("跨视频提问");
    fireEvent.change(input, { target: { value: "对比这两条视频的 Agent 变现路径" } });
    fireEvent.click(screen.getByRole("button", { name: "AI 提问" }));

    await waitFor(() => expect(askBodies).toHaveLength(1));
    expect(askBodies[0]).toMatchObject({
      question: "对比这两条视频的 Agent 变现路径",
      video_ids: ["vidGreg1", "vidLocal1"],
    });
    expect(await screen.findByText("对比已选 2 条视频")).toBeTruthy();
    expect(screen.getByText("本周挑选 1 个行业高频 PDF 审核环节做最小闭环原型")).toBeTruthy();
  });

  it("renders chronological Chinese AI insight evolution in Topics, collapses repetitive contribution boilerplate, and jumps to scoped Research Q&A", async () => {
    location.hash = "#Topics";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/topics")) {
          return okJson({
            topics: [
              {
                topic_id: "topic-monetize",
                name: "AI 产品机会与一人公司变现",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "SINGLE_SOURCE",
                independence: "SINGLE_SOURCE",
                contributions: [],
                timeline: [],
                relations: [],
                ai_evolution: {
                  video_count: 18,
                  must_watch_count: 9,
                  avg_score: 8.9,
                  latest_headline_zh: "垂直行业表单流自动化是一人公司高毛利切口。",
                  source_channels: ["Greg Isenberg", "本地实战课"],
                },
              },
            ],
          });
        }
        if (input.endsWith("/topics/topic-monetize")) {
          return okJson({
            topic: {
              topic_id: "topic-monetize",
              name: "AI 产品机会与一人公司变现",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "SINGLE_SOURCE",
              independence: "SINGLE_SOURCE",
              contributions: [
                {
                  intelligence_id: "intel-1",
                  claim_kind: "OPPORTUNITY",
                  state: "SINGLE_SOURCE",
                  available: true,
                  evidence_ids: ["ev-1"],
                },
              ],
              timeline: [
                {
                  event_id: "evt-1",
                  event_kind: "CREATED",
                  state: "SINGLE_SOURCE",
                  created_at: "2026-11-14T10:00:00Z",
                },
              ],
              relations: [
                {
                  related_topic_id: "topic-agent",
                  related_topic_name: "AI Agent 与自动化架构",
                },
              ],
              ai_evolution: {
                video_count: 2,
                must_watch_count: 2,
                avg_score: 9.3,
                latest_headline_zh: "垂直行业表单流自动化是一人公司高毛利切口。",
                source_channels: ["Greg Isenberg", "本地实战课"],
                entries: [
                  {
                    video_id: "vidGreg1",
                    title: "Micro-SaaS Playbook",
                    channel_name: "Greg Isenberg",
                    published_at: "2026-11-14T08:00:00Z",
                    score: 9.2,
                    recommendation_tier: "MUST_WATCH",
                    source_basis: "TRANSCRIPT",
                    headline_zh: "垂直行业表单流自动化是一人公司高毛利切口。",
                    summary_zh: "拆解从痛点访谈到首月 MRR 的实操路径。",
                    product_opportunities_zh: ["合规表单自动核验 SaaS"],
                    business_opportunities_zh: ["按席位+单量阶梯年费"],
                  },
                ],
              },
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [],
            suggested_questions: [],
            scope_options: {
              channels: [],
              topic_clusters: [{ name: "AI 产品机会与一人公司变现", count: 18 }],
              videos: [],
            },
          });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    const { container } = render(<App />);
    expect(await screen.findByText(/18 条内容 · 9 条必看/)).toBeTruthy();
    expect(screen.getByText("垂直行业表单流自动化是一人公司高毛利切口。")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /AI 产品机会与一人公司变现/ }));
    expect(await screen.findByText("Micro-SaaS Playbook")).toBeTruthy();
    expect(screen.getByText("AI Agent 与自动化架构")).toBeTruthy();

    // Repetitive boilerplate contribution rows are collapsed inside <details>
    const rawContribDrawer = container.querySelector(
      "details.topic-raw-contributions",
    ) as HTMLDetailsElement | null;
    expect(rawContribDrawer).not.toBeNull();
    expect(rawContribDrawer?.open).toBe(false);

    // Clicking "围绕本专题跨视频提问" jumps to #Research with that topic pre-selected
    fireEvent.click(screen.getByRole("button", { name: "围绕本专题跨视频提问" }));
    await waitFor(() => expect(location.hash).toBe("#Research"));
    const topicSelect = (await screen.findByLabelText("限定专题")) as HTMLSelectElement;
    expect(topicSelect.value).toBe("AI 产品机会与一人公司变现");
  });

  it("imports and restores AI knowledge snapshot JSON in Settings and triggers inline 1-click Retry check for OFFLINE sources in Following", async () => {
    location.hash = "#Settings";
    let restoredPayload: unknown = null;
    let retriedSourceCheck = false;

    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/workspace-ai/restore") && init?.method === "POST") {
        restoredPayload = JSON.parse(String(init.body));
        return okJson({
          restored: {
            video_ai_briefs: 3,
            weekly_ai_briefs: 1,
            ai_research_sessions: 2,
          },
        });
      }
      if (path.endsWith("/sources/youtube-channel-greg/check") && init?.method === "POST") {
        retriedSourceCheck = true;
        return okJson({ source_run: { run_id: "run-retry-1" } });
      }
      if (path.endsWith("/sources")) {
        return okJson({
          sources: [
            {
              source_id: "youtube-channel-greg",
              provider: "YOUTUBE",
              source_type: "CHANNEL",
              display_name: "Greg Isenberg",
              canonical_url: "https://www.youtube.com/@GregIsenberg",
              enabled: true,
              processing_policy: "DISCOVER_ONLY",
              last_error: { code: "OFFLINE" },
              tracking: {
                health: retriedSourceCheck ? "HEALTHY" : "OFFLINE",
                coverage: "COMPLETE",
                baseline_at: "2026-11-12T00:00:00Z",
                update_count: 12,
                pending_count: 0,
                checking: false,
              },
            },
          ],
        });
      }
      if (path.endsWith("/settings/local-intelligence")) {
        return okJson({
          local_intelligence: {
            status: "NOT_CONFIGURED",
            etag: "b".repeat(64),
            selected_candidate_id: null,
            actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null },
            blocking_work: [],
            candidates: [],
          },
        });
      }
      if (path.endsWith("/settings")) {
        return okJson({
          general: {
            timezone: "Asia/Shanghai",
            output_language: "zh-CN",
            output_language_source: "USER",
            output_language_updated_at: null,
          },
          providers: [],
          cloud_credential: { configured: false, source: "NONE" },
          workspace_ai: {
            active_mode: "local_ollama",
            ollama_base_url: "http://127.0.0.1:11434",
            ollama_model: "qwen3.5:9b",
            ollama_reachable: true,
            installed_ollama_models: ["qwen3.5:9b"],
            cloud_provider: "deepseek",
            cloud_base_url: "https://api.deepseek.com/v1",
            cloud_model: "deepseek-chat",
            cloud_key_configured: false,
          },
        });
      }
      if (path.endsWith("/settings/preferences")) return okJson({ active: [], history: [] });
      if (path.endsWith("/settings/source-policy")) {
        return okJson({
          policy: {
            initial_history_count: 5,
            per_run_max_new_videos: 5,
            focus_rules: [],
            ignore_rules: [],
            distillation_style: "BALANCED",
          },
        });
      }
      if (path.endsWith("/settings/resource-usage")) return okJson({ usage: [] });
      if (path.endsWith("/settings/local-models")) return okJson({ connection: "REACHABLE", models: [] });
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const restoreInput = (await screen.findByLabelText(
      "导入 AI 知识库快照文件",
    )) as HTMLInputElement;
    const snapshotFile = new File(
      [
        JSON.stringify({
          schema_version: "workspace-ai-backup-v1",
          video_ai_briefs: [{ video_id: "v1" }],
          weekly_ai_briefs: [],
          ai_research_sessions: [],
        }),
      ],
      "workspace-ai-backup-2026-11-15.json",
      { type: "application/json" },
    );
    fireEvent.change(restoreInput, { target: { files: [snapshotFile] } });

    await waitFor(() => expect(restoredPayload).not.toBeNull());
    expect(await screen.findByText(/已恢复 3 条中文摘要、1 份周报与 2 条跨视频问答记录/)).toBeTruthy();

    // Navigate to Following and click inline 1-click "立即重检" on the OFFLINE Greg Isenberg row
    const primaryNav = screen.getByRole("navigation", { name: "主导航" });
    fireEvent.click(within(primaryNav).getByRole("button", { name: "关注" }));
    const retryBtn = await screen.findByRole("button", { name: "立即重检" });
    fireEvent.click(retryBtn);

    await waitFor(() => expect(retriedSourceCheck).toBe(true));
  });

  it("persists Save/Unsave state across Home and Intelligence Current/Saved tabs", async () => {
    location.hash = "#Home";
    let isSaved = false;

    const intelCard = {
      status: "AVAILABLE",
      trusted: true,
      intelligence_id: "intel-save-1",
      claim_kind: "FACT",
      state: "CONFIRMED",
      card: {
        core_conclusion: "生产级 Agent 必须具备显式工具契约与失败回滚保护。",
        user_relevant_information: ["直接影响一人公司自动化工作流的交付可靠性。"],
        important_new_information: ["引入无副作用幂等校验降低误操作。"],
        meaningful_details: ["支持本地与云端双轨回退。"],
        source_id: "youtube-channel-openai",
        source_display_name: "OpenAI",
        source_url: "https://www.youtube.com/@OpenAI",
        video_id: "vid-agent-1",
        video_title: "Agent Reliability Guide",
        original_video_url: "https://www.youtube.com/watch?v=vid-agent-1",
        evidence_links: [],
      },
    };

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/saved-intelligence/save") && init?.method === "POST") {
        isSaved = true;
        return okJson({ saved: true });
      }
      if (input.endsWith("/saved-intelligence/unsave") && init?.method === "POST") {
        isSaved = false;
        return okJson({ saved: false });
      }
      if (input.endsWith("/dashboard")) {
        return okJson({
          intelligence: [intelCard],
          saved_intelligence_ids: isSaved ? ["intel-save-1"] : [],
          pinned_topics: [],
          needs_attention: [],
          operations: { source_count: 1 },
        });
      }
      if (input.endsWith("/knowledge-delta")) {
        return okJson({
          knowledge_delta: {
            window_start: "2026-11-08T00:00:00Z",
            window_end: "2026-11-15T00:00:00Z",
            timezone: "Asia/Shanghai",
            status: "available",
            detail_limit: 2,
            categories: [],
          },
        });
      }
      if (input.endsWith("/intelligence/intel-save-1")) {
        return okJson({ intelligence: intelCard });
      }
      if (input.endsWith("/intelligence")) {
        return okJson({ intelligence: [intelCard], activity: [] });
      }
      if (input.endsWith("/saved-intelligence")) {
        return okJson({
          saved: isSaved
            ? [
                {
                  intelligence_id: "intel-save-1",
                  saved_at: "2026-11-15T05:00:00Z",
                  intelligence: intelCard,
                },
              ]
            : [],
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const homeSaveBtn = await screen.findByRole("button", { name: "收藏" });
    fireEvent.click(homeSaveBtn);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "取消收藏" })).toBeTruthy(),
    );

    const primaryNav = screen.getByRole("navigation", { name: "主导航" });
    fireEvent.click(within(primaryNav).getByRole("button", { name: "洞察" }));

    const currentUnsaveBtn = await screen.findByRole("button", { name: "取消收藏" });
    fireEvent.click(currentUnsaveBtn);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "收藏" })).toBeTruthy(),
    );
  });

  it("supports personal Star/Read curation, Unread/Starred filters, honest no-caption status, and raw-URL placeholder folding in Content", async () => {
    location.hash = "#Content";
    let isStarred = false;
    let isRead = false;
    const curationCalls: Record<string, unknown>[] = [];

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (
        input.endsWith("/workspace-ai/videos/vid-deep/curation") &&
        init?.method === "POST"
      ) {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        curationCalls.push(body);
        if (typeof body.starred === "boolean") isStarred = body.starred;
        if (typeof body.is_read === "boolean") isRead = body.is_read;
        return okJson({
          video_id: "vid-deep",
          starred: isStarred,
          is_read: isRead,
        });
      }
      if (input.endsWith("/videos")) {
        return okJson({
          videos: [
            {
              video_id: "vid-deep",
              provider: "YOUTUBE",
              channel_id: "UC-openai",
              channel_name: "OpenAI",
              title: "Agent Orchestration Masterclass",
              source_url: "https://www.youtube.com/watch?v=vid-deep",
              published_at: "2026-11-14T10:00:00Z",
              processing_status: "READY",
              duration_seconds: 1800,
              last_updated: "2026-11-14T10:05:00Z",
              ai_brief: {
                video_id: "vid-deep",
                source_basis: "TRANSCRIPT",
                headline_zh: "状态机编排让多步 Agent 可恢复可审计。",
                summary_zh: "详解长任务恢复机制。",
                score: 9.3,
                score_reason_zh: "架构干货密度极高",
                recommendation_tier: "MUST_WATCH",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                starred: isStarred,
                is_read: isRead,
                topics_zh: ["Agent"],
                topic_cluster_zh: "AI Agent 与自动化架构",
                product_opportunities_zh: [],
                business_opportunities_zh: [],
              },
            },
            {
              video_id: "vid-meta",
              provider: "YOUTUBE",
              channel_id: "UC-greg",
              channel_name: "Greg Isenberg",
              title: "Solo Founder Pricing Breakdown",
              source_url: "https://www.youtube.com/watch?v=vid-meta",
              published_at: "2026-11-13T10:00:00Z",
              processing_status: "FAILED",
              duration_seconds: 1420,
              last_updated: "2026-11-13T10:05:00Z",
              ai_brief: {
                video_id: "vid-meta",
                source_basis: "METADATA_ONLY",
                headline_zh: "围绕高客单价年费阶梯设计一人公司定价。",
                summary_zh: "基于官方简介提炼。",
                score: 7.5,
                score_reason_zh: "简介含定价框架",
                recommendation_tier: "WORTH_SKIMMING",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                starred: false,
                is_read: false,
                topics_zh: ["定价"],
                topic_cluster_zh: "AI 产品机会与一人公司变现",
                product_opportunities_zh: [],
                business_opportunities_zh: [],
              },
            },
            {
              video_id: "rawPlaceholder1",
              work_kind: "DURABLE_CONTENT_IDENTITY",
              provider: "YOUTUBE",
              channel_id: "UC-openai",
              channel_name: "OpenAI",
              title: "https://www.youtube.com/watch?v=rawPlaceholder1",
              source_url: "https://www.youtube.com/watch?v=rawPlaceholder1",
              published_at: "2026-11-12T10:00:00Z",
              processing_status: "METADATA_READY",
              duration_seconds: null,
              last_updated: "2026-11-12T10:00:00Z",
            },
          ],
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<App />);
    expect(await screen.findByText("Agent Orchestration Masterclass")).toBeTruthy();

    // METADATA_ONLY video shows honest "无原生字幕" instead of alarming "失败"
    expect(screen.getByText("无原生字幕")).toBeTruthy();
    expect(screen.queryByText("失败")).toBeNull();

    // DURABLE_CONTENT_IDENTITY raw-URL placeholder is auto-folded into bottom <details>
    const foldDrawer = container.querySelector(
      "details.shorts-fold-drawer",
    ) as HTMLDetailsElement | null;
    expect(foldDrawer).not.toBeNull();
    expect(foldDrawer?.open).toBe(false);
    expect(within(foldDrawer!).getByText("https://www.youtube.com/watch?v=rawPlaceholder1")).toBeTruthy();

    // Star vid-deep and filter by "已收藏"
    const starBtns = screen.getAllByRole("button", { name: "收藏待看" });
    fireEvent.click(starBtns[0]);
    await waitFor(() => expect(curationCalls).toContainEqual({ starred: true }));
    expect(await screen.findByRole("button", { name: "已收藏 · 取消" })).toBeTruthy();

    const filterGroup = screen.getByRole("group", { name: "内容价值分流" });
    fireEvent.click(within(filterGroup).getByRole("button", { name: "已收藏" }));
    expect(screen.getByText("Agent Orchestration Masterclass")).toBeTruthy();
    expect(screen.queryByText("Solo Founder Pricing Breakdown")).toBeNull();

    // Switch back to "全部", mark vid-deep read, and filter by "未读干货"
    fireEvent.click(within(filterGroup).getByRole("button", { name: "全部" }));
    const readBtns = await screen.findAllByRole("button", { name: "标记已读" });
    fireEvent.click(readBtns[0]);
    await waitFor(() => expect(curationCalls).toContainEqual({ is_read: true }));

    fireEvent.click(within(filterGroup).getByRole("button", { name: "未读干货" }));
    expect(screen.queryByText("Agent Orchestration Masterclass")).toBeNull();
    expect(screen.getByText("Solo Founder Pricing Breakdown")).toBeTruthy();
  });

  it("renders Topic MOC Obsidian [[wikilinks]] Markdown export and 7-day freshness count in Topics", async () => {
    location.hash = "#Topics";
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/topics")) {
          return okJson({
            topics: [
              {
                topic_id: "topic-agent",
                name: "AI Agent 与自动化架构",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CONFIRMED",
                independence: "MULTI_SOURCE",
                contributions: [],
                timeline: [],
                relations: [],
                ai_evolution: {
                  video_count: 24,
                  must_watch_count: 11,
                  recent_7d_count: 5,
                  avg_score: 9.0,
                  latest_headline_zh: "多智能体协作进入确定性编排阶段。",
                  source_channels: ["OpenAI", "本地实战课"],
                },
              },
            ],
          });
        }
        if (input.endsWith("/topics/topic-agent")) {
          return okJson({
            topic: {
              topic_id: "topic-agent",
              name: "AI Agent 与自动化架构",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "CONFIRMED",
              independence: "MULTI_SOURCE",
              contributions: [],
              timeline: [],
              relations: [],
              ai_evolution: {
                video_count: 24,
                must_watch_count: 11,
                recent_7d_count: 5,
                avg_score: 9.0,
                latest_headline_zh: "多智能体协作进入确定性编排阶段。",
                source_channels: ["OpenAI", "本地实战课"],
                obsidian_markdown:
                  "# AI Agent 与自动化架构\n\n- 关联专题：[[AI 产品机会与一人公司变现]]\n- 核心必看：[[Agent Orchestration Masterclass]]",
                entries: [
                  {
                    video_id: "vid-deep",
                    title: "Agent Orchestration Masterclass",
                    channel_name: "OpenAI",
                    published_at: "2026-11-14T10:00:00Z",
                    score: 9.3,
                    recommendation_tier: "MUST_WATCH",
                    source_basis: "TRANSCRIPT",
                    headline_zh: "状态机编排让多步 Agent 可恢复可审计。",
                    summary_zh: "详解长任务恢复机制。",
                    product_opportunities_zh: [],
                    business_opportunities_zh: [],
                  },
                ],
              },
            },
          });
        }
        return okJson({});
      }),
    );

    render(<App />);
    expect(await screen.findByText(/近7天 \+5/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /AI Agent 与自动化架构/ }));
    const copyMocBtn = await screen.findByRole("button", { name: "复制专题双链笔记" });
    fireEvent.click(copyMocBtn);

    expect(writeText).toHaveBeenCalledWith(
      expect.stringContaining("[[Agent Orchestration Masterclass]]"),
    );
    expect(screen.getByRole("button", { name: "下载专题 .md" })).toBeTruthy();
  });

  it("R4: filters Intelligence cards by search & source, renders Topic cross-source synthesis + sibling jumps without contradictory UNRESOLVED copy, and switches Weekly Brief history", async () => {
    // 1) Home Weekly Brief historical snapshot switcher
    location.hash = "#Home";
    const historyList = [
      {
        brief_id: "wb-2026-w46-new",
        title_zh: "《本周 AI 产品与商业情报周报》",
        created_at: "2026-11-15T06:00:00Z",
        provider: "ollama",
        model: "qwen3.5:9b",
        must_watch_count: 18,
        distilled_count: 112,
        total_videos: 115,
      },
      {
        brief_id: "wb-2026-w45-old",
        title_zh: "《上周 AI 工程化情报周报》",
        created_at: "2026-11-08T06:00:00Z",
        provider: "ollama",
        model: "qwen3.5:9b",
        must_watch_count: 11,
        distilled_count: 74,
        total_videos: 80,
      },
    ];
    const latestBrief = {
      brief_id: "wb-2026-w46-new",
      week_label: "",
      title_zh: "《本周 AI 产品与商业情报周报》",
      executive_summary_zh: "最新一期：聚焦受控状态机与垂直 SaaS 定价。",
      core_trends_zh: ["状态机编排成为主流"],
      product_opportunities_zh: ["本地优先研究工作台"],
      business_opportunities_zh: ["高客单价年费订阅"],
      must_watch_picks: [],
      funnel_stats: {
        total_videos: 115,
        distilled_count: 112,
        must_watch_count: 18,
        shorts_filtered_count: 64,
      },
      obsidian_markdown: "# 最新周报",
      provider: "ollama",
      model: "qwen3.5:9b",
      created_at: "2026-11-15T06:00:00Z",
      history: historyList,
    };
    const olderBrief = {
      ...latestBrief,
      brief_id: "wb-2026-w45-old",
      title_zh: "《上周 AI 工程化情报周报》",
      executive_summary_zh: "历史存档：聚焦早期多模态评测基准与成本优化。",
      created_at: "2026-11-08T06:00:00Z",
    };

    const makeCard = (
      id: string,
      conclusion: string,
      sourceName: string,
      videoTitle: string,
    ) => ({
      intelligence_id: id,
      status: "AVAILABLE",
      trusted: true,
      claim_kind: "ANALYSIS",
      state: "CONFIRMED",
      confirmed: true,
      evidence_ids: [`ev-${id}`],
      card: {
        core_conclusion: conclusion,
        user_relevant_information: ["核心拆解"],
        important_new_information: [],
        meaningful_details: [],
        filtered_noise: [],
        source_id: `src-${sourceName}`,
        source_display_name: sourceName,
        video_id: `vid-${id}`,
        video_title: videoTitle,
        evidence_links: [],
        preference_ids: [],
        source_policy_revision_id: null,
      },
    });

    const fetchMock = vi.fn((input: string) => {
      if (input.includes("/workspace-ai/weekly-brief?brief_id=wb-2026-w45-old")) {
        return okJson({ weekly_brief: olderBrief, history: historyList });
      }
      if (input.endsWith("/dashboard")) {
        return okJson({
          intelligence: [],
          pinned_topics: [],
          needs_attention: [],
          operations: { source_count: 3 },
          workspace_weekly_brief: latestBrief,
        });
      }
      if (input.includes("/changes/recent")) {
        return okJson({
          window: { start_at: "2026-11-08T00:00:00Z", end_at: "2026-11-15T00:00:00Z", timezone: "Asia/Shanghai", days: 7 },
          status: "COMPLETE",
          degraded_sections: [],
          counts: { intelligence_added: 0, intelligence_updated: 0, topics_changed: 0, content_processed: 0, sources_needing_attention: 0 },
          groups: { intelligence_added: [], intelligence_updated: [], topics_changed: [], content_processed: [], sources_needing_attention: [] },
        });
      }
      if (input.endsWith("/intelligence")) {
        return okJson({
          intelligence: [
            makeCard("i1", "GPT-6 Cyber 在真实代码库自动定位高危安全漏洞。", "OpenAI", "Mozilla Firefox Security Case"),
            makeCard("i2", "一人公司高毛利 AI 产品需优先绑定行业合规表单。", "Greg Isenberg", "Solo AI SaaS Playbook"),
            makeCard("i3", "本地离线语音转写结合双链笔记构建私有第二大脑。", "本地实战课", "3. Agent.mp4"),
            makeCard("i4", "多模态实时语音交互延迟已压降至可商用阈值。", "OpenAI", "Realtime Voice Update"),
          ],
          activity: [],
        });
      }
      if (input.endsWith("/saved-intelligence")) {
        return okJson({ saved: [] });
      }
      if (input.endsWith("/topics")) {
        return okJson({
          topics: [
            {
              topic_id: "topic-agent",
              name: "AI Agent 与自动化架构",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "UNRESOLVED",
              independence: "UNKNOWN",
              contributions: [],
              timeline: [{ event_id: "ev1", state: "UNRESOLVED", created_at: "2026-11-14T10:00:00Z" }],
              relations: [],
              ai_evolution: {
                video_count: 26,
                must_watch_count: 21,
                recent_7d_count: 13,
                avg_score: 8.4,
                latest_headline_zh: "受控工具契约是生产级 Agent 落地前提。",
                source_channels: ["OpenAI", "本地实战课", "Greg Isenberg"],
              },
            },
            {
              topic_id: "topic-biz",
              name: "AI 产品机会与一人公司变现",
              pinned: false,
              lifecycle: "ACTIVE",
              current_state: "UNRESOLVED",
              independence: "UNKNOWN",
              contributions: [],
              timeline: [],
              relations: [],
              ai_evolution: {
                video_count: 9,
                must_watch_count: 7,
                recent_7d_count: 4,
                avg_score: 8.7,
                latest_headline_zh: "按可量化 ROI 定价优于按席位收费。",
                source_channels: ["Greg Isenberg"],
              },
            },
          ],
        });
      }
      if (input.endsWith("/topics/topic-agent")) {
        return okJson({
          topic: {
            topic_id: "topic-agent",
            name: "AI Agent 与自动化架构",
            pinned: true,
            lifecycle: "ACTIVE",
            current_state: "UNRESOLVED",
            independence: "UNKNOWN",
            contributions: [],
            timeline: [{ event_id: "ev1", state: "UNRESOLVED", created_at: "2026-11-14T10:00:00Z" }],
            relations: [],
            ai_evolution: {
              video_count: 26,
              must_watch_count: 21,
              recent_7d_count: 13,
              avg_score: 8.4,
              latest_headline_zh: "受控工具契约是生产级 Agent 落地前提。",
              synthesis_zh: "受控工具契约是生产级 Agent 落地前提；结合确定性状态机与离线评测集才能支撑企业级交付。",
              independence_summary_zh: "已汇聚 OpenAI、本地实战课、Greg Isenberg 共 3 个独立来源交叉印证（共 26 篇内容，21 篇必看干货）。",
              top_opportunities_zh: ["带原话时间戳溯源的垂直情报工作台"],
              source_channels: ["OpenAI", "本地实战课", "Greg Isenberg"],
              related_topics: [
                {
                  topic_id: "topic-biz",
                  name: "AI 产品机会与一人公司变现",
                  video_count: 9,
                  must_watch_count: 7,
                  avg_score: 8.7,
                  shared_sources: ["Greg Isenberg"],
                },
              ],
              obsidian_markdown: "# AI Agent MOC",
              entries: [
                {
                  video_id: "vid-1",
                  title: "Mozilla Firefox Security Case",
                  channel_name: "OpenAI",
                  published_at: "2026-11-14T10:00:00Z",
                  score: 9.2,
                  recommendation_tier: "MUST_WATCH",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "受控工具契约是生产级 Agent 落地前提。",
                  summary_zh: "详解安全审计闭环。",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              ],
            },
          },
        });
      }
      if (input.endsWith("/topics/topic-biz")) {
        return okJson({
          topic: {
            topic_id: "topic-biz",
            name: "AI 产品机会与一人公司变现",
            pinned: false,
            lifecycle: "ACTIVE",
            current_state: "UNRESOLVED",
            independence: "UNKNOWN",
            contributions: [],
            timeline: [],
            relations: [],
            ai_evolution: {
              video_count: 9,
              must_watch_count: 7,
              recent_7d_count: 4,
              avg_score: 8.7,
              latest_headline_zh: "按可量化 ROI 定价优于按席位收费。",
              synthesis_zh: "围绕高痛点 B2B 合规流切入一人公司年费订阅。",
              independence_summary_zh: "当前聚合自单一来源（Greg Isenberg，共 9 篇内容），可结合更多独立频道交叉印证。",
              top_opportunities_zh: [],
              source_channels: ["Greg Isenberg"],
              related_topics: [],
              obsidian_markdown: "# 商业变现 MOC",
              entries: [
                {
                  video_id: "vid-2",
                  title: "Solo AI SaaS Playbook",
                  channel_name: "Greg Isenberg",
                  published_at: "2026-11-13T10:00:00Z",
                  score: 8.9,
                  recommendation_tier: "MUST_WATCH",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "按可量化 ROI 定价优于按席位收费。",
                  summary_zh: "定价实操拆解。",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              ],
            },
          },
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    // Clean single "+" import label (no "+ + 导入")
    const quickImportBtn = await screen.findByRole("button", { name: "快捷导入" });
    expect(quickImportBtn.textContent?.trim()).toBe("导入");

    // Weekly Brief historical switcher
    expect(await screen.findByText("最新一期：聚焦受控状态机与垂直 SaaS 定价。")).toBeTruthy();
    const historySelect = screen.getByRole("combobox", { name: "切换历史周报期次" });
    fireEvent.change(historySelect, { target: { value: "wb-2026-w45-old" } });
    expect(await screen.findByText("历史存档：聚焦早期多模态评测基准与成本优化。")).toBeTruthy();

    // Navigate to #Intelligence and filter by source + Chinese keyword
    const primaryNav = screen.getByRole("navigation", { name: "主导航" });
    fireEvent.click(within(primaryNav).getByRole("button", { name: "洞察" }));
    expect(await screen.findByText(/自动定位高危安全漏洞/)).toBeTruthy();
    expect(screen.getByText(/一人公司高毛利 AI 产品/)).toBeTruthy();

    const sourceGroup = screen.getByRole("group", { name: "按来源筛选洞察" });
    fireEvent.click(within(sourceGroup).getByRole("button", { name: /OpenAI/ }));
    expect(screen.getByText(/自动定位高危安全漏洞/)).toBeTruthy();
    expect(screen.queryByText(/一人公司高毛利 AI 产品/)).toBeNull();

    const intelSearch = screen.getByRole("searchbox", { name: "搜索洞察结论或视频标题" });
    fireEvent.change(intelSearch, { target: { value: "实时语音" } });
    expect(screen.getByText(/多模态实时语音交互延迟/)).toBeTruthy();
    expect(screen.queryByText(/自动定位高危安全漏洞/)).toBeNull();

    // Navigate to #Topics -> Topic detail shows grounded synthesis & jumps to sibling topic without "来源仍有分歧"
    fireEvent.click(within(primaryNav).getByRole("button", { name: "主题" }));
    fireEvent.click(await screen.findByRole("button", { name: /AI Agent 与自动化架构/ }));
    expect(await screen.findByText(/结合确定性状态机与离线评测集才能支撑企业级交付/)).toBeTruthy();
    expect(screen.getByText(/共 3 个独立来源交叉印证/)).toBeTruthy();
    expect(screen.queryByText(/来源仍有分歧/)).toBeNull();
    expect(screen.queryByText(/目前缺少足够的可靠信息/)).toBeNull();

    // Preserves required Panel headings Timeline ("时间线") and Related Topics ("关联主题")
    expect(screen.getByRole("heading", { name: /时间线/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /关联主题/ })).toBeTruthy();

    // Click sibling topic chip in Related Topics -> navigates directly to topic-biz
    fireEvent.click(screen.getByRole("button", { name: /AI 产品机会与一人公司变现/ }));
    expect(await screen.findByText(/围绕高痛点 B2B 合规流切入一人公司年费订阅/)).toBeTruthy();
  });

  it("R4: indexes beyond 40 videos with Chinese AI headlines in ⌘K CommandPalette and supports 1-click Mark Read & Next Unread in Content detail", async () => {
    location.hash = "#Content/vid-read-1";
    const readIds = new Set<string>();

    // Generate 45 Short promos FIRST + 2 high-value deep dives at indices 45 & 46 to prove 40-item truncation is gone
    const fillerShorts = Array.from({ length: 45 }, (_, idx) => ({
      video_id: `vid-short-${idx}`,
      provider: "YOUTUBE",
      channel_id: "UC-openai",
      channel_name: "OpenAI",
      title: `Short Promo Clip #${idx}`,
      published_at: "2026-11-14T10:00:00Z",
      processing_status: "ORGANIZED",
      duration_seconds: 35,
      last_updated: "2026-11-14T10:00:00Z",
      ai_brief: {
        video_id: `vid-short-${idx}`,
        headline_zh: "短视频宣传预热片段",
        summary_zh: "短片",
        score: 2.5,
        score_reason_zh: "短片",
        recommendation_tier: "SKIP_NOISE",
        content_bucket: "SHORTS_PROMO",
        is_short_noise: true,
        starred: false,
        is_read: false,
        topics_zh: ["短片"],
        topic_cluster_zh: "大模型演进与多模态实战",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
    }));

    const buildDeepVideo = (
      id: string,
      title: string,
      headlineZh: string,
      score: number,
      starred: boolean,
    ) => ({
      video_id: id,
      provider: "LOCAL",
      media_kind: "VIDEO",
      format: "mp4",
      channel_id: "local",
      channel_name: "Local",
      title,
      published_at: "2026-11-10T10:00:00Z",
      processing_status: "READY",
      duration_seconds: 3600,
      last_updated: "2026-11-10T10:00:00Z",
      ai_brief: {
        video_id: id,
        headline_zh: headlineZh,
        summary_zh: headlineZh,
        score,
        score_reason_zh: "高价值实战课",
        recommendation_tier: "MUST_WATCH",
        content_bucket: "TUTORIAL",
        is_short_noise: false,
        starred,
        is_read: readIds.has(id),
        topics_zh: ["安全漏洞", "一人公司"],
        topic_cluster_zh: "AI Agent 与自动化架构",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
    });

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      const curMatch = input.match(/\/workspace-ai\/videos\/([^/]+)\/curation$/);
      if (curMatch && init?.method === "POST") {
        const vid = decodeURIComponent(curMatch[1]);
        const body = JSON.parse(String(init.body)) as { is_read?: boolean };
        if (body.is_read) readIds.add(vid);
        return okJson({ video_id: vid, starred: false, is_read: readIds.has(vid) });
      }
      if (input.endsWith("/videos")) {
        return okJson({
          videos: [
            ...fillerShorts,
            buildDeepVideo(
              "vid-read-1",
              "1. First Lecture.mp4",
              "第一讲：Agent 工具沙箱隔离与权限最小化。",
              9.1,
              false,
            ),
            buildDeepVideo(
              "vid-read-2",
              "5. Hidden Beyond Forty.mp4",
              "第五讲：用确定性回放捕获高隐蔽性浏览器漏洞。",
              9.6,
              true,
            ),
          ],
        });
      }
      if (input.endsWith("/videos/vid-read-1")) {
        const v = buildDeepVideo(
          "vid-read-1",
          "1. First Lecture.mp4",
          "第一讲：Agent 工具沙箱隔离与权限最小化。",
          9.1,
          false,
        );
        return okJson({
          video: v,
          transcript: { status: "AVAILABLE", text: "Sandbox isolation." },
          note: { v2: { status: "UNAVAILABLE" } },
          intelligence_result: { status: "NOT_PROCESSED" },
          history: [],
        });
      }
      if (input.endsWith("/videos/vid-read-2")) {
        const v = buildDeepVideo(
          "vid-read-2",
          "5. Hidden Beyond Forty.mp4",
          "第五讲：用确定性回放捕获高隐蔽性浏览器漏洞。",
          9.6,
          true,
        );
        return okJson({
          video: v,
          transcript: { status: "AVAILABLE", text: "Deterministic replay." },
          note: { v2: { status: "UNAVAILABLE" } },
          intelligence_result: { status: "NOT_PROCESSED" },
          history: [],
        });
      }
      if (input.endsWith("/evidence")) return okJson({ evidence: [] });
      if (input.endsWith("/intelligence")) return okJson({ intelligence: [] });
      if (input.endsWith("/topics")) return okJson({ topics: [] });
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByText("1. First Lecture.mp4")).toBeTruthy();

    // Distilled Chinese AI Brief sits front-and-center inside #section-intelligence while legacy NOT_PROCESSED diagnostics is collapsed
    const intelSection = document.getElementById("section-intelligence")!;
    expect(within(intelSection).getByText("第一讲：Agent 工具沙箱隔离与权限最小化。")).toBeTruthy();
    const legacyDiag = intelSection.querySelector("details.legacy-model-diagnostics") as HTMLDetailsElement | null;
    expect(legacyDiag).toBeTruthy();
    expect(legacyDiag?.open).toBe(false);

    // Open ⌘K Command Palette and search Chinese AI conclusion of video #46 ("高隐蔽性浏览器漏洞")
    fireEvent.click(screen.getByRole("button", { name: /搜索与直达/ }));
    const cmdkInput = await screen.findByRole("combobox", {
      name: "搜索页面、内容、洞察或命令",
    });
    fireEvent.change(cmdkInput, { target: { value: "浏览器漏洞" } });
    expect(await screen.findByText("5. Hidden Beyond Forty.mp4")).toBeTruthy();
    fireEvent.keyDown(cmdkInput, { key: "Escape" });

    // Click 1-click "标已读并看下一篇" -> marks vid-read-1 read and navigates directly to vid-read-2!
    const markAndNextBtn = await screen.findByRole("button", {
      name: /标已读并看下一篇/,
    });
    fireEvent.click(markAndNextBtn);

    await waitFor(() => expect(readIds.has("vid-read-1")).toBe(true));
    await waitFor(() => expect(location.hash).toBe("#Content/vid-read-2"));
    expect(await screen.findByText("5. Hidden Beyond Forty.mp4")).toBeTruthy();
  });

  it("R5: surfaces Weekly Brief incremental freshness banner with 1-click regenerate and exports Obsidian [[wikilinks]] Vault .zip bundle", async () => {
    location.hash = "#Home";
    let refreshed = false;
    const bundleCalls: string[] = [];
    const createObjectURL = vi.fn(() => "blob:obsidian-vault-zip");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const staleBrief = {
      brief_id: "wb-2026-w46-stale",
      week_label: "2026-W46",
      title_zh: "《本周 AI 产品与商业情报周报》",
      executive_summary_zh: "旧版周报摘要：涵盖前序 34 篇内容。",
      core_trends_zh: ["端侧推理与受控 Agent 融合"],
      product_opportunities_zh: ["私有情报工作台"],
      business_opportunities_zh: ["年费订阅制"],
      must_watch_picks: [],
      funnel_stats: {
        total_videos: 113,
        distilled_count: 34,
        must_watch_count: 29,
        shorts_filtered_count: 79,
      },
      freshness: {
        is_archive: false,
        is_stale: true,
        new_videos_count: 2,
        new_must_watch_count: 1,
        new_titles: ["OpenAI Agent SDK Deep Dive", "Solo SaaS Pricing"],
      },
      obsidian_markdown: "# 旧版周报\n\n- [[AI Agent 与自动化架构]]",
      provider: "ollama",
      model: "qwen3.5:9b",
      created_at: "2026-11-14T16:44:00Z",
      history: [
        {
          brief_id: "wb-2026-w46-stale",
          title_zh: "《本周 AI 产品与商业情报周报》",
          created_at: "2026-11-14T16:44:00Z",
          must_watch_count: 29,
          distilled_count: 34,
          total_videos: 113,
        },
      ],
    };

    const freshBrief = {
      ...staleBrief,
      brief_id: "wb-2026-w46-fresh",
      executive_summary_zh: "最新版周报摘要：已纳入最新 2 篇深度干货。",
      funnel_stats: {
        total_videos: 115,
        distilled_count: 36,
        must_watch_count: 30,
        shorts_filtered_count: 79,
      },
      freshness: {
        is_archive: false,
        is_stale: false,
        new_videos_count: 0,
        new_must_watch_count: 0,
        new_titles: [],
      },
    };

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/workspace-ai/weekly-brief/generate") && init?.method === "POST") {
        refreshed = true;
        return okJson({ weekly_brief: freshBrief, history: freshBrief.history });
      }
      if (input.includes("/workspace-ai/obsidian-bundle")) {
        bundleCalls.push(input);
        return okJson({
          filename: "Obsidian-AI情报知识库-all-2026-11-15.zip",
          scope: "all",
          counts: {
            total_files: 8,
            video_notes: 4,
            topic_mocs: 2,
            weekly_briefs: 1,
            research_qa_notes: 1,
          },
          index_markdown: "# AI 情报知识库总览 (MOC)",
          archive_base64: "UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==",
        });
      }
      if (input.endsWith("/dashboard")) {
        return okJson({
          intelligence: [],
          pinned_topics: [],
          needs_attention: [],
          operations: { source_count: 3 },
          workspace_weekly_brief: refreshed ? freshBrief : staleBrief,
        });
      }
      if (input.includes("/changes/recent")) {
        return okJson({
          window: {
            start_at: "2026-11-08T00:00:00Z",
            end_at: "2026-11-15T00:00:00Z",
            timezone: "Asia/Shanghai",
            days: 7,
          },
          status: "COMPLETE",
          degraded_sections: [],
          counts: {
            intelligence_added: 0,
            intelligence_updated: 0,
            topics_changed: 0,
            content_processed: 0,
            sources_needing_attention: 0,
          },
          groups: {
            intelligence_added: [],
            intelligence_updated: [],
            topics_changed: [],
            content_processed: [],
            sources_needing_attention: [],
          },
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByText(/自上次生成周报以来新增 2 篇干货（含 1 篇必看）/)).toBeTruthy();
    expect(screen.getByText(/OpenAI Agent SDK Deep Dive/)).toBeTruthy();

    // 1-click refresh incorporates new videos and clears the staleness banner
    fireEvent.click(screen.getByRole("button", { name: "立即纳入刷新周报" }));
    expect(await screen.findByText("最新版周报摘要：已纳入最新 2 篇深度干货。")).toBeTruthy();
    expect(screen.queryByText(/自上次生成周报以来新增/)).toBeNull();

    // Select scope "all" and export Obsidian Vault .zip bundle
    const scopeSelect = screen.getByRole("combobox", { name: "Obsidian 知识库包导出范围" });
    fireEvent.change(scopeSelect, { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "导出 Obsidian 知识库包 (.zip)" }));

    await waitFor(() =>
      expect(bundleCalls.some((url) => url.includes("scope=all"))).toBe(true),
    );
    expect(await screen.findByText(/已导出 Obsidian 双链知识库包（共 8 篇 \.md 笔记/)).toBeTruthy();
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it("R5: displays live bucket counts, filters Content by AI topic cluster, and supports guarded keyboard triage in list and detail reader", async () => {
    location.hash = "#Content";
    const starredIds = new Set<string>();
    const readIds = new Set<string>();
    const curationCalls: Array<{ id: string; body: { starred?: boolean; is_read?: boolean } }> = [];

    const buildItems = () => [
      {
        video_id: "vid-agent",
        provider: "YOUTUBE" as const,
        channel_id: "UC-openai",
        channel_name: "OpenAI",
        title: "Agent Orchestration Masterclass",
        source_url: "https://www.youtube.com/watch?v=vid-agent",
        published_at: "2026-11-14T10:00:00Z",
        processing_status: "READY",
        duration_seconds: 1800,
        last_updated: "2026-11-14T10:05:00Z",
        ai_brief: {
          video_id: "vid-agent",
          source_basis: "TRANSCRIPT" as const,
          headline_zh: "状态机编排让多步 Agent 可恢复可审计。",
          summary_zh: "详解长任务恢复机制。",
          score: 9.4,
          score_reason_zh: "架构干货密度极高",
          recommendation_tier: "MUST_WATCH" as const,
          content_bucket: "DEEP_DIVE" as const,
          is_short_noise: false,
          starred: starredIds.has("vid-agent"),
          is_read: readIds.has("vid-agent"),
          topics_zh: ["Agent"],
          topic_cluster_zh: "AI Agent 与自动化架构",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      {
        video_id: "vid-biz",
        provider: "YOUTUBE" as const,
        channel_id: "UC-greg",
        channel_name: "Greg Isenberg",
        title: "Solo SaaS Pricing Tutorial",
        source_url: "https://www.youtube.com/watch?v=vid-biz",
        published_at: "2026-11-13T10:00:00Z",
        processing_status: "READY",
        duration_seconds: 1500,
        last_updated: "2026-11-13T10:05:00Z",
        ai_brief: {
          video_id: "vid-biz",
          source_basis: "TRANSCRIPT" as const,
          headline_zh: "围绕高客单价年费阶梯设计一人公司定价。",
          summary_zh: "实操定价教程。",
          score: 8.6,
          score_reason_zh: "实操框架清晰",
          recommendation_tier: "MUST_WATCH" as const,
          content_bucket: "TUTORIAL" as const,
          is_short_noise: false,
          starred: starredIds.has("vid-biz"),
          is_read: readIds.has("vid-biz"),
          topics_zh: ["定价"],
          topic_cluster_zh: "AI 产品机会与一人公司变现",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      {
        video_id: "vid-short",
        provider: "YOUTUBE" as const,
        channel_id: "UC-openai",
        channel_name: "OpenAI",
        title: "Teaser Clip #1",
        source_url: "https://www.youtube.com/watch?v=vid-short",
        published_at: "2026-11-12T10:00:00Z",
        processing_status: "ORGANIZED",
        duration_seconds: 42,
        last_updated: "2026-11-12T10:05:00Z",
        ai_brief: {
          video_id: "vid-short",
          source_basis: "TRANSCRIPT" as const,
          headline_zh: "发布会预热短片",
          summary_zh: "短片",
          score: 2.8,
          score_reason_zh: "短片",
          recommendation_tier: "SKIP_NOISE" as const,
          content_bucket: "SHORTS_PROMO" as const,
          is_short_noise: true,
          starred: false,
          is_read: false,
          topics_zh: ["短片"],
          topic_cluster_zh: "大模型演进与多模态实战",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
    ];

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      const curMatch = input.match(/\/workspace-ai\/videos\/([^/]+)\/curation$/);
      if (curMatch && init?.method === "POST") {
        const vid = decodeURIComponent(curMatch[1]);
        const body = JSON.parse(String(init.body)) as { starred?: boolean; is_read?: boolean };
        curationCalls.push({ id: vid, body });
        if (typeof body.starred === "boolean") {
          if (body.starred) starredIds.add(vid);
          else starredIds.delete(vid);
        }
        if (typeof body.is_read === "boolean") {
          if (body.is_read) readIds.add(vid);
          else readIds.delete(vid);
        }
        return okJson({
          video_id: vid,
          starred: starredIds.has(vid),
          is_read: readIds.has(vid),
        });
      }
      if (input.endsWith("/videos")) {
        return okJson({ videos: buildItems() });
      }
      if (input.endsWith("/videos/vid-agent")) {
        return okJson({
          video: buildItems()[0],
          transcript: { status: "AVAILABLE", text: "Agent orchestration transcript." },
          note: { v2: { status: "UNAVAILABLE" } },
          intelligence_result: { status: "NOT_PROCESSED" },
          history: [],
        });
      }
      if (input.endsWith("/videos/vid-biz")) {
        return okJson({
          video: buildItems()[1],
          transcript: { status: "AVAILABLE", text: "Pricing tutorial transcript." },
          note: { v2: { status: "UNAVAILABLE" } },
          intelligence_result: { status: "NOT_PROCESSED" },
          history: [],
        });
      }
      if (input.endsWith("/evidence")) return okJson({ evidence: [] });
      if (input.endsWith("/intelligence")) return okJson({ intelligence: [] });
      if (input.endsWith("/topics")) return okJson({ topics: [] });
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<App />);
    expect(await screen.findByText("Agent Orchestration Masterclass")).toBeTruthy();

    // 1) Live numerical bucket counts while keeping exact accessible names
    const filterGroup = screen.getByRole("group", { name: "内容价值分流" });
    const allBtn = within(filterGroup).getByRole("button", { name: "全部" });
    const unreadBtn = within(filterGroup).getByRole("button", { name: "未读干货" });
    const starredBtn = within(filterGroup).getByRole("button", { name: "已收藏" });
    const tutorialBtn = within(filterGroup).getByRole("button", { name: "实操教程" });
    const shortsBtn = within(filterGroup).getByRole("button", { name: "Shorts 短片" });
    expect(allBtn.querySelector(".bucket-count-badge")?.textContent).toBe("2");
    expect(unreadBtn.querySelector(".bucket-count-badge")?.textContent).toBe("2");
    expect(starredBtn.querySelector(".bucket-count-badge")?.textContent).toBe("0");
    expect(tutorialBtn.querySelector(".bucket-count-badge")?.textContent).toBe("1");
    expect(shortsBtn.querySelector(".bucket-count-badge")?.textContent).toBe("1");

    // 2) Filter by AI Topic Cluster dropdown
    const topicSelect = screen.getByRole("combobox", { name: "按专题筛选内容" });
    fireEvent.change(topicSelect, { target: { value: "AI 产品机会与一人公司变现" } });
    expect(screen.queryByText("Agent Orchestration Masterclass")).toBeNull();
    expect(screen.getByText("Solo SaaS Pricing Tutorial")).toBeTruthy();

    // Reset topic filter back to ALL
    fireEvent.change(topicSelect, { target: { value: "ALL" } });
    expect(screen.getByText("Agent Orchestration Masterclass")).toBeTruthy();
    expect(screen.getByText("Solo SaaS Pricing Tutorial")).toBeTruthy();

    // 3) Guarded keyboard triage: "/" focuses search input; typing "s" inside input is ignored
    const searchInput = screen.getByRole("searchbox", { name: "搜索内容库" }) as HTMLInputElement;
    fireEvent.keyDown(window, { key: "/" });
    expect(document.activeElement).toBe(searchInput);
    fireEvent.keyDown(searchInput, { key: "s" });
    expect(curationCalls.length).toBe(0);

    // Blur search input -> j / k navigates rows -> s stars active row -> Enter opens detail
    searchInput.blur();
    fireEvent.keyDown(window, { key: "j" });
    await waitFor(() => {
      const activeShell = container.querySelector('[data-kb-active="true"]');
      expect(activeShell?.textContent).toContain("Solo SaaS Pricing Tutorial");
    });
    fireEvent.keyDown(window, { key: "k" });
    await waitFor(() => {
      const activeShell = container.querySelector('[data-kb-active="true"]');
      expect(activeShell?.textContent).toContain("Agent Orchestration Masterclass");
    });

    fireEvent.keyDown(window, { key: "s" });
    await waitFor(() =>
      expect(curationCalls).toContainEqual({ id: "vid-agent", body: { starred: true } }),
    );
    await waitFor(() =>
      expect(starredBtn.querySelector(".bucket-count-badge")?.textContent).toBe("1"),
    );

    fireEvent.keyDown(document.body, { key: "Enter" });
    await waitFor(() => expect(location.hash).toBe("#Content/vid-agent"));
    expect(await screen.findByRole("button", { name: "返回内容" })).toBeTruthy();

    // 4) Detail reader keyboard shortcuts: "e" marks read & advances to vid-biz; "u" returns to #Content
    fireEvent.keyDown(window, { key: "e" });
    await waitFor(() => expect(readIds.has("vid-agent")).toBe(true));
    await waitFor(() => expect(location.hash).toBe("#Content/vid-biz"));
    expect(await screen.findByText("Solo SaaS Pricing Tutorial")).toBeTruthy();

    fireEvent.keyDown(window, { key: "u" });
    await waitFor(() => expect(location.hash).toBe("#Content"));
  });

  it("R6: renders Weekly Brief period-over-period delta diff, supports reversible batch mark-read in Content, and hands off starred shortlist to Research Q&A with honest NO_GROUNDED_CONTENT recovery", async () => {
    location.hash = "#Home";
    const starredIds = new Set<string>(["vid-r6-1"]);
    const readIds = new Set<string>();
    const batchCalls: Array<{ video_ids: string[]; is_read?: boolean; starred?: boolean }> = [];
    const askCalls: Array<Record<string, unknown>> = [];
    let failEmptyStarredOnce = true;

    const buildVideos = () => [
      {
        video_id: "vid-r6-1",
        provider: "YOUTUBE" as const,
        channel_id: "UC-openai",
        channel_name: "OpenAI",
        title: "Eval Driven Agent Engineering",
        source_url: "https://www.youtube.com/watch?v=vid-r6-1",
        published_at: "2026-11-15T01:00:00Z",
        processing_status: "READY",
        duration_seconds: 1920,
        last_updated: "2026-11-15T01:05:00Z",
        ai_brief: {
          video_id: "vid-r6-1",
          source_basis: "TRANSCRIPT" as const,
          headline_zh: "评测集驱动的 Agent 迭代闭环。",
          summary_zh: "工程拆解。",
          score: 9.3,
          score_reason_zh: "高密度工程实战",
          recommendation_tier: "MUST_WATCH" as const,
          content_bucket: "DEEP_DIVE" as const,
          is_short_noise: false,
          starred: starredIds.has("vid-r6-1"),
          is_read: readIds.has("vid-r6-1"),
          topics_zh: ["Agent"],
          topic_cluster_zh: "AI Agent 与自动化架构",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      {
        video_id: "vid-r6-2",
        provider: "YOUTUBE" as const,
        channel_id: "UC-greg",
        channel_name: "Greg Isenberg",
        title: "Outcome Pricing for Vertical AI",
        source_url: "https://www.youtube.com/watch?v=vid-r6-2",
        published_at: "2026-11-14T20:00:00Z",
        processing_status: "READY",
        duration_seconds: 1680,
        last_updated: "2026-11-14T20:05:00Z",
        ai_brief: {
          video_id: "vid-r6-2",
          source_basis: "TRANSCRIPT" as const,
          headline_zh: "按交付结果阶梯定价提升续费率。",
          summary_zh: "商业定价拆解。",
          score: 8.9,
          score_reason_zh: "商业闭环清晰",
          recommendation_tier: "MUST_WATCH" as const,
          content_bucket: "DEEP_DIVE" as const,
          is_short_noise: false,
          starred: starredIds.has("vid-r6-2"),
          is_read: readIds.has("vid-r6-2"),
          topics_zh: ["定价"],
          topic_cluster_zh: "AI 产品机会与一人公司变现",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/dashboard")) {
          return okJson({
            intelligence: [],
            saved_intelligence_ids: [],
            pinned_topics: [],
            needs_attention: [],
            operations: { source_count: 2 },
            workspace_weekly_brief: {
              brief_id: "wb-r6-latest",
              title_zh: "《本周 AI 产品与商业情报周报》",
              executive_summary_zh: "本期聚焦评测驱动 Agent 与按结果定价。",
              core_trends_zh: ["评测先行成为生产级共识"],
              product_opportunities_zh: ["自动化回归评测沙箱"],
              business_opportunities_zh: ["按结果分成订阅"],
              must_watch_picks: [
                {
                  video_id: "vid-r6-1",
                  title: "Eval Driven Agent Engineering",
                  channel_name: "OpenAI",
                  score: 9.3,
                  reason_zh: "评测集驱动闭环",
                },
              ],
              funnel_stats: {
                total_videos: 115,
                distilled_count: 115,
                must_watch_count: 31,
                shorts_filtered_count: 79,
              },
              freshness: {
                is_archive: false,
                is_stale: false,
                new_videos_count: 0,
                new_must_watch_count: 0,
                new_titles: [],
              },
              delta: {
                previous_brief_id: "wb-r6-prev",
                previous_created_at: "2026-11-13T10:00:00Z",
                previous_title_zh: "《本周 AI 产品与商业情报周报》",
                total_videos_delta: 13,
                distilled_delta: 13,
                must_watch_delta: 2,
                new_picks: [
                  {
                    video_id: "vid-r6-1",
                    title: "Eval Driven Agent Engineering",
                    channel_name: "OpenAI",
                    score: 9.3,
                    headline_zh: "评测集驱动的 Agent 迭代闭环。",
                  },
                ],
                new_shifts_zh: ["评测先行成为生产级共识"],
                new_opportunities_zh: ["自动化回归评测沙箱"],
                summary_zh: "较上期新增提炼 13 篇 · 新增 2 篇必看干货 · 1 篇新晋必看上榜",
              },
              obsidian_markdown: "# 周报",
              provider: "local_ollama",
              model: "qwen2.5:7b",
              created_at: "2026-11-15T01:00:00Z",
            },
          });
        }
        if (input.endsWith("/delta")) {
          return okJson({ delta: { since: null, items: [] } });
        }
        if (input.endsWith("/workspace-ai/curation/batch") && init?.method === "POST") {
          const body = JSON.parse(String(init.body)) as {
            video_ids: string[];
            is_read?: boolean;
            starred?: boolean;
          };
          batchCalls.push(body);
          for (const vid of body.video_ids) {
            if (typeof body.is_read === "boolean") {
              if (body.is_read) readIds.add(vid);
              else readIds.delete(vid);
            }
            if (typeof body.starred === "boolean") {
              if (body.starred) starredIds.add(vid);
              else starredIds.delete(vid);
            }
          }
          return okJson({ updated_count: body.video_ids.length, items: [] });
        }
        if (input.endsWith("/videos")) {
          return okJson({ videos: buildVideos() });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [],
            suggested_questions: ["已收藏视频有哪些共识？"],
            scope_options: {
              starred_count: starredIds.size,
              channels: [{ key: "OpenAI", label: "OpenAI", video_count: 29 }],
              topic_clusters: [{ name: "AI Agent 与自动化架构", video_count: 14 }],
              videos: buildVideos().map((v) => ({
                video_id: v.video_id,
                title: v.title,
                channel_name: v.channel_name,
                score: v.ai_brief.score,
                starred: v.ai_brief.starred,
                topic_cluster_zh: v.ai_brief.topic_cluster_zh,
              })),
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/ask") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body)) as Record<string, unknown>;
          askCalls.push(parsed);
          if (failEmptyStarredOnce) {
            failEmptyStarredOnce = false;
            return new Response(
              JSON.stringify({
                error: {
                  code: "NO_GROUNDED_CONTENT",
                  message: "当前筛选范围内没有可用于跨视频溯源问答的已转写内容。",
                },
              }),
              { status: 409, headers: { "Content-Type": "application/json" } },
            );
          }
          return okJson({
            session: {
              session_id: "qa-r6-starred",
              question: String(parsed.question),
              scope_label_zh: "仅限已收藏（1 篇）",
              answer_zh: "已收藏的 OpenAI 视频强调评测集先行 [E1]。",
              key_takeaways_zh: ["先建离线评测再扩工具链"],
              action_items_zh: ["落地最小评测集"],
              citations: [
                {
                  ref_label: "E1",
                  video_id: "vid-r6-1",
                  video_title: "Eval Driven Agent Engineering",
                  channel_name: "OpenAI",
                  evidence_id: "ev-r6-1",
                  start_ms: 5000,
                  end_ms: 15000,
                  timestamp_label: "00:05",
                  excerpt: "Deterministic eval harnesses keep agent releases safe.",
                },
              ],
              obsidian_markdown: "# 已收藏问答",
              provider: "local_ollama",
              model: "qwen2.5:7b",
              created_at: "2026-11-15T01:10:00Z",
            },
          });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    render(<App />);

    // 1) Home Weekly Brief shows accurate 31 must-watch count + Period-over-Period Delta strip
    expect(await screen.findByText(/精选 31 条必看干货/)).toBeTruthy();
    const deltaRegion = screen.getByRole("region", { name: "较上期周报演进对比" });
    expect(within(deltaRegion).getByText(/较上期新增提炼 13 篇/)).toBeTruthy();
    expect(
      within(deltaRegion).getByRole("button", { name: /Eval Driven Agent Engineering/ }),
    ).toBeTruthy();

    // 2) Navigate to #Content -> batch mark current list read (2) + reversible 1-click Undo
    fireEvent.click(screen.getByRole("button", { name: "内容" }));
    const batchReadBtn = await screen.findByRole("button", { name: /当前列表标已读.*2/ });
    fireEvent.click(batchReadBtn);

    await waitFor(() =>
      expect(batchCalls).toContainEqual({
        video_ids: ["vid-r6-1", "vid-r6-2"],
        is_read: true,
      }),
    );
    const undoBtn = await screen.findByRole("button", { name: "撤销" });
    fireEvent.click(undoBtn);
    await waitFor(() =>
      expect(batchCalls).toContainEqual({
        video_ids: ["vid-r6-1", "vid-r6-2"],
        is_read: false,
      }),
    );

    // 3) 1-click handoff from #Content starred shortlist -> #Research with starred_only=true
    const askStarredBtn = await screen.findByRole("button", { name: /针对已收藏提问.*1/ });
    fireEvent.click(askStarredBtn);
    await waitFor(() => expect(location.hash).toBe("#Research"));

    // Verify backend video_count (29) is parsed on source chips & starred chip is active
    expect(await screen.findByRole("button", { name: "OpenAI (29)" })).toBeTruthy();
    const starredScopeChip = screen.getByRole("button", { name: /仅限已收藏.*1/ });
    expect(starredScopeChip.getAttribute("aria-pressed")).toBe("true");

    // First submit triggers 409 NO_GROUNDED_CONTENT -> shows honest scope guidance (NOT Ollama error)
    const qInput = screen.getByLabelText("跨视频提问");
    fireEvent.change(qInput, { target: { value: "提炼已收藏内容的核心工程建议" } });
    fireEvent.click(screen.getByRole("button", { name: "AI 提问" }));

    expect(await screen.findByText(/当前已收藏清单中暂无带时间轴字幕的内容/)).toBeTruthy();
    expect(screen.queryByText(/请检查本机 Ollama/)).toBeNull();
    expect(askCalls[0]).toMatchObject({
      question: "提炼已收藏内容的核心工程建议",
      starred_only: true,
    });

    // Retry succeeds and renders grounded answer scoped to starred shortlist
    fireEvent.click(screen.getByRole("button", { name: "AI 提问" }));
    expect(await screen.findByText("仅限已收藏（1 篇）")).toBeTruthy();
    expect(screen.getByText(/已收藏的 OpenAI 视频强调评测集先行/)).toBeTruthy();
  });

  it("R7: surfaces Following source signal-to-noise metrics with 1-click Content/Research handoffs, filters Content by channel, and supports Research session search + follow-up scope reuse", async () => {
    window.localStorage.setItem("yia.onboarding.v1", "done");
    window.localStorage.setItem("yia.uiLanguage", "zh-CN");
    location.hash = "#Following";

    const askCalls: Record<string, unknown>[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn((rawInput: RequestInfo | URL, init?: RequestInit) => {
        const input = String(rawInput);
        if (input.endsWith("/capabilities/creator-following")) {
          return okJson({
            capability: {
              available: true,
              providers: ["YOUTUBE"],
              reason_code: null,
            },
          });
        }
        if (input.endsWith("/sources/check-stale")) {
          return okJson({ checked: 0 });
        }
        if (input.endsWith("/sources")) {
          return okJson({
            sources: [
              {
                source_id: "youtube-channel-openai",
                provider: "YOUTUBE",
                source_type: "CHANNEL",
                canonical_url: "https://www.youtube.com/@OpenAI",
                handle_or_channel_id: "@OpenAI",
                display_name: "OpenAI",
                enabled: true,
                insight_count: 20,
                tracking: {
                  health: "HEALTHY",
                  coverage: "CONTINUOUS",
                  checking: false,
                  baseline_complete: true,
                  last_checked_at: "2026-11-15T01:00:00Z",
                  last_new_content_at: "2026-11-15T00:30:00Z",
                  tracked_count: 100,
                  ready_count: 23,
                  processing_count: 0,
                  pending_count: 0,
                  unavailable_count: 0,
                  update_count: 2,
                },
              },
              {
                source_id: "youtube-channel-greg",
                provider: "YOUTUBE",
                source_type: "CHANNEL",
                canonical_url: "https://www.youtube.com/@GregIsenberg",
                handle_or_channel_id: "@GregIsenberg",
                display_name: "Greg Isenberg",
                enabled: true,
                insight_count: 9,
                tracking: {
                  health: "HEALTHY",
                  coverage: "CONTINUOUS",
                  checking: false,
                  baseline_complete: true,
                  last_checked_at: "2026-11-15T01:00:00Z",
                  last_new_content_at: "2026-11-15T00:40:00Z",
                  tracked_count: 12,
                  ready_count: 11,
                  processing_count: 0,
                  pending_count: 0,
                  unavailable_count: 0,
                  update_count: 1,
                },
              },
              {
                source_id: "youtube-channel-noisy",
                provider: "YOUTUBE",
                source_type: "CHANNEL",
                canonical_url: "https://www.youtube.com/@NoisyShortsFeed",
                handle_or_channel_id: "@NoisyShortsFeed",
                display_name: "Noisy Shorts Feed",
                enabled: true,
                insight_count: 0,
                tracking: {
                  health: "HEALTHY",
                  coverage: "CONTINUOUS",
                  checking: false,
                  baseline_complete: true,
                  last_checked_at: "2026-11-15T01:00:00Z",
                  last_new_content_at: null,
                  tracked_count: 15,
                  ready_count: 0,
                  processing_count: 0,
                  pending_count: 0,
                  unavailable_count: 0,
                  update_count: 0,
                },
              },
            ],
            ai_signal_by_source: {
              "youtube-channel-openai": {
                source_id: "youtube-channel-openai",
                channel_key: "OpenAI",
                channel_label: "OpenAI",
                total_videos: 100,
                distilled_count: 100,
                long_form_count: 23,
                shorts_count: 77,
                must_watch_count: 20,
                worth_skimming_count: 3,
                unread_long_count: 5,
                avg_long_score: 8.4,
                signal_rate_pct: 23,
              },
              "youtube-channel-greg": {
                source_id: "youtube-channel-greg",
                channel_key: "Greg Isenberg",
                channel_label: "Greg Isenberg",
                total_videos: 12,
                distilled_count: 12,
                long_form_count: 11,
                shorts_count: 1,
                must_watch_count: 9,
                worth_skimming_count: 2,
                unread_long_count: 3,
                avg_long_score: 8.5,
                signal_rate_pct: 92,
              },
              "youtube-channel-noisy": {
                source_id: "youtube-channel-noisy",
                channel_key: "Noisy Shorts Feed",
                channel_label: "Noisy Shorts Feed",
                total_videos: 15,
                distilled_count: 15,
                long_form_count: 0,
                shorts_count: 15,
                must_watch_count: 0,
                worth_skimming_count: 0,
                unread_long_count: 0,
                avg_long_score: null,
                signal_rate_pct: 0,
              },
            },
          });
        }
        if (input.endsWith("/videos")) {
          return okJson({
            videos: [
              {
                video_id: "vid-openai-1",
                provider: "YOUTUBE",
                channel_id: "UC-openai",
                channel_name: "OpenAI",
                title: "OpenAI Cyber Security Harness",
                published_at: "2026-11-15T00:00:00Z",
                processing_status: "ORGANIZED",
                last_updated: "2026-11-15T00:00:00Z",
                duration_seconds: 1600,
                caption_timing_status: "AVAILABLE",
                ai_brief: {
                  video_id: "vid-openai-1",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "安全评测沙箱驱动高危漏洞自动修复",
                  summary_zh: "OpenAI 分享安全补丁闭环。",
                  score: 9.1,
                  score_reason_zh: "工程含金量高",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["AI 安全"],
                  topic_cluster_zh: "AI Agent 与自动化架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vid-greg-1",
                provider: "YOUTUBE",
                channel_id: "UC-greg",
                channel_name: "Greg Isenberg",
                title: "Vertical AI Directory Playbook",
                published_at: "2026-11-15T00:10:00Z",
                processing_status: "ORGANIZED",
                last_updated: "2026-11-15T00:10:00Z",
                duration_seconds: 1950,
                caption_timing_status: "AVAILABLE",
                ai_brief: {
                  video_id: "vid-greg-1",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "高信噪比垂直 AI 工作流变现拆解",
                  summary_zh: "一人公司切入高复购垂直 SaaS。",
                  score: 9.3,
                  score_reason_zh: "商业闭环清晰",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: true,
                  is_read: false,
                  topics_zh: ["商业变现"],
                  topic_cluster_zh: "一人公司与 AI 商业变现",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
            ],
          });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [
              {
                session_id: "qa-hist-compare",
                question: "本地实战课里关于 AI Agent 工程落地最核心的建议是什么？",
                scope_label_zh: "对比 2 条指定视频",
                scope: {
                  scope_label_zh: "对比 2 条指定视频",
                  starred_only: false,
                  channel_key: null,
                  topic_cluster: null,
                  video_ids: ["vid-local-1", "vid-local-2"],
                },
                video_count: 2,
                answer_zh: "本地实战课建议先固定确定性状态机再接入工具调用 [E1]。",
                key_takeaways_zh: ["状态机优先于自由路由"],
                action_items_zh: ["梳理核心节点契约"],
                citations: [
                  {
                    ref_label: "E1",
                    video_id: "vid-local-1",
                    video_title: "3. Agent.mp4",
                    channel_name: "本地实战课",
                    evidence_id: "ev-loc-1",
                    start_ms: 10000,
                    end_ms: 20000,
                    timestamp_label: "00:10",
                    excerpt: "先把状态机边界定死。",
                  },
                ],
                obsidian_markdown: "# 本地实战对比",
                provider: "local_ollama",
                model: "qwen2.5:7b",
                created_at: "2026-11-15T01:20:00Z",
              },
              {
                session_id: "qa-hist-full",
                question: "Mozilla 是如何用 GPT-6 Cyber 扫描修复 Firefox 安全漏洞的？",
                scope_label_zh: "",
                scope: {},
                video_count: 2,
                answer_zh: "Mozilla 通过回归沙箱自动复现崩溃并验证补丁 [E1] [E2]。",
                key_takeaways_zh: ["沙箱复现先于补丁生成"],
                action_items_zh: ["引入漏洞回归测试集"],
                citations: [
                  {
                    ref_label: "E1",
                    video_id: "vid-openai-1",
                    video_title: "OpenAI Cyber Security Harness",
                    channel_name: "OpenAI",
                    evidence_id: "ev-oa-1",
                    start_ms: 12000,
                    end_ms: 24000,
                    timestamp_label: "00:12",
                    excerpt: "Reproduce crashes inside deterministic sandboxes.",
                  },
                  {
                    ref_label: "E2",
                    video_id: "vid-greg-1",
                    video_title: "Vertical AI Directory Playbook",
                    channel_name: "Greg Isenberg",
                    evidence_id: "ev-gr-1",
                    start_ms: 30000,
                    end_ms: 42000,
                    timestamp_label: "00:30",
                    excerpt: "Automated QA workflows save engineering hours.",
                  },
                ],
                obsidian_markdown: "# Mozilla 安全修复",
                provider: "local_ollama",
                model: "qwen2.5:7b",
                created_at: "2026-11-15T01:10:00Z",
              },
              {
                session_id: "qa-hist-monetize",
                question: "一人公司如何用垂直 AI 工作流做高毛利变现？",
                scope_label_zh: "来源：Greg Isenberg",
                scope: {
                  scope_label_zh: "来源：Greg Isenberg",
                  starred_only: false,
                  channel_key: "Greg Isenberg",
                  topic_cluster: null,
                  video_ids: null,
                },
                video_count: 1,
                answer_zh: "聚焦高客单价行业审批痛点按席位或结果年费定价 [E1]。",
                key_takeaways_zh: ["卖结果而非卖聊天"],
                action_items_zh: ["验证垂直客群付费意愿"],
                citations: [
                  {
                    ref_label: "E1",
                    video_id: "vid-greg-1",
                    video_title: "Vertical AI Directory Playbook",
                    channel_name: "Greg Isenberg",
                    evidence_id: "ev-gr-2",
                    start_ms: 45000,
                    end_ms: 60000,
                    timestamp_label: "00:45",
                    excerpt: "Charge annual retainers for outcome-based workflows.",
                  },
                ],
                obsidian_markdown: "# 垂直变现问答",
                provider: "local_ollama",
                model: "qwen2.5:7b",
                created_at: "2026-11-15T01:00:00Z",
              },
            ],
            suggested_questions: [],
            scope_options: {
              starred_count: 1,
              channels: [
                { key: "OpenAI", label: "OpenAI", provider: "YOUTUBE", video_count: 23 },
                { key: "Greg Isenberg", label: "Greg Isenberg", provider: "YOUTUBE", video_count: 10 },
                { key: "LOCAL", label: "本地实战课", provider: "LOCAL", video_count: 2 },
              ],
              topic_clusters: [
                { name: "一人公司与 AI 商业变现", video_count: 6 },
                { name: "AI Agent 与自动化架构", video_count: 5 },
              ],
              videos: [
                {
                  video_id: "vid-greg-1",
                  title: "Vertical AI Directory Playbook",
                  channel_name: "Greg Isenberg",
                  channel_key: "Greg Isenberg",
                  score: 9.3,
                  starred: true,
                  topic_cluster_zh: "一人公司与 AI 商业变现",
                },
                {
                  video_id: "vid-openai-1",
                  title: "OpenAI Cyber Security Harness",
                  channel_name: "OpenAI",
                  channel_key: "OpenAI",
                  score: 9.1,
                  starred: false,
                  topic_cluster_zh: "AI Agent 与自动化架构",
                },
                {
                  video_id: "vid-local-1",
                  title: "3. Agent.mp4",
                  channel_name: "本地实战课",
                  channel_key: "LOCAL",
                  score: 9.2,
                  starred: false,
                  topic_cluster_zh: "AI Agent 与自动化架构",
                },
                {
                  video_id: "vid-local-2",
                  title: "4. Multimodal.mp4",
                  channel_name: "本地实战课",
                  channel_key: "LOCAL",
                  score: 9.0,
                  starred: false,
                  topic_cluster_zh: "AI Agent 与自动化架构",
                },
              ],
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/ask") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>;
          askCalls.push(parsed);
          return okJson({
            session: {
              session_id: "qa-followup-01",
              question: String(parsed.question),
              scope_label_zh: "对比 2 条指定视频",
              scope: {
                scope_label_zh: "对比 2 条指定视频",
                video_ids: parsed.video_ids ?? null,
              },
              video_count: 2,
              answer_zh: "追问结论：两节本地课一致建议先用离线评估集锁定工具误调率 [E1]。",
              key_takeaways_zh: ["离线评估集锁定误调率"],
              action_items_zh: ["补充 20 条边界用例"],
              citations: [],
              obsidian_markdown: "# 追问结果",
              provider: "local_ollama",
              model: "qwen2.5:7b",
              created_at: "2026-11-15T01:30:00Z",
            },
          });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    const { container } = render(<App />);

    // 1) #Following surfaces signal-to-noise metrics per source + high-signal filter
    expect(
      await screen.findByText(/干货 23\/100 \(23%\) · 必看 20 · 均分 8\.4 · 折叠 77 Shorts/),
    ).toBeTruthy();
    expect(
      screen.getByText(/干货 11\/12 \(92%\) · 必看 9 · 均分 8\.5 · 折叠 1 Shorts/),
    ).toBeTruthy();

    const followingFilter = screen.getByLabelText("筛选关注") as HTMLSelectElement;
    fireEvent.change(followingFilter, { target: { value: "high_signal" } });
    expect(screen.queryByText("Noisy Shorts Feed")).toBeNull();
    expect(screen.getByText("Greg Isenberg")).toBeTruthy();

    // 2) 1-click "看干货 (11)" on Greg Isenberg -> #Content pre-filtered to Greg Isenberg
    const gregRow = container.querySelector('[data-source-id="youtube-channel-greg"]') as HTMLElement;
    expect(gregRow).not.toBeNull();
    fireEvent.click(within(gregRow).getByRole("button", { name: /看干货 \(11\)/ }));

    await waitFor(() => expect(location.hash).toBe("#Content"));
    const channelSelect = (await screen.findByLabelText("按频道筛选")) as HTMLSelectElement;
    expect(channelSelect.value).toBe("Greg Isenberg");
    expect(screen.getByText("Vertical AI Directory Playbook")).toBeTruthy();
    expect(screen.queryByText("OpenAI Cyber Security Harness")).toBeNull();

    // 3) Back to #Following -> 1-click "问此频道" on Greg Isenberg -> #Research scoped to Greg Isenberg
    fireEvent.click(screen.getByRole("button", { name: "关注" }));
    const gregRowAgain = (await waitFor(() =>
      container.querySelector('[data-source-id="youtube-channel-greg"]'),
    )) as HTMLElement;
    fireEvent.click(within(gregRowAgain).getByRole("button", { name: "问此频道" }));

    await waitFor(() => expect(location.hash).toBe("#Research"));
    const gregScopeChip = await screen.findByRole("button", { name: "Greg Isenberg (10)" });
    expect(gregScopeChip.getAttribute("aria-pressed")).toBe("true");

    // 4) Research session history shows video counts, filters via search, and supports 1-click follow-up scope reuse
    const historySearch = screen.getByLabelText("筛选历史问答");
    fireEvent.change(historySearch, { target: { value: "Mozilla" } });
    expect(screen.queryByRole("button", { name: /一人公司如何用垂直 AI 工作流.*1 篇/ })).toBeNull();
    const mozillaHistBtn = screen.getByRole("button", {
      name: /Mozilla 是如何用 GPT-6 Cyber.*2 篇/,
    });
    fireEvent.click(mozillaHistBtn);
    fireEvent.change(historySearch, { target: { value: "" } });

    // Full-library session (`scope: {}`) offers 1-click follow-up on its 2 cited videos
    const citeFollowBtn = screen.getByRole("button", { name: "围绕引用视频追问 (2)" });
    fireEvent.click(citeFollowBtn);
    expect(screen.getByRole("button", { name: "指定多视频对比 (已选 2)" })).toBeTruthy();
    const qInput = screen.getByLabelText("跨视频提问");
    expect(document.activeElement).toBe(qInput);

    // Scoped comparison session (`video_ids: ["vid-local-1", "vid-local-2"]`) restores exact scope on "同范围继续追问"
    fireEvent.click(
      screen.getByRole("button", {
        name: /本地实战课里关于 AI Agent 工程落地.*2 篇/,
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "同范围继续追问" }));
    expect(screen.getByLabelText(/3\. Agent\.mp4/)).toHaveProperty("checked", true);
    expect(screen.getByLabelText(/4\. Multimodal\.mp4/)).toHaveProperty("checked", true);

    fireEvent.change(qInput, { target: { value: "这两节本地课对离线评估集怎么设计？" } });
    fireEvent.click(screen.getByRole("button", { name: "AI 提问" }));

    await waitFor(() => expect(askCalls).toHaveLength(1));
    expect(askCalls[0]).toMatchObject({
      question: "这两节本地课对离线评估集怎么设计？",
      video_ids: ["vid-local-1", "vid-local-2"],
    });
  });

  it("R8: renders Weekly Brief delta shifts when picks unchanged, links Topic channel breakdown & detail [[topic]] tag into Content filters, and indexes AI Q&A sessions + channels in Cmd+K", async () => {
    location.hash = "#Home";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/dashboard")) {
          return okJson({
            intelligence: [],
            pinned_topics: [],
            needs_attention: [],
            operations: { source_count: 2 },
            workspace_weekly_brief: {
              brief_id: "wb-r8-latest",
              week_label: "2026-W46",
              title_zh: "《本周 AI 产品与商业情报周报》",
              executive_summary_zh: "本周核心演进聚焦于长周期自主智能体与安全验证闭环。",
              core_trends_zh: ["从‘工具’到‘员工’：长周期自主执行成为核心壁垒"],
              product_opportunities_zh: ["长周期任务监控与自愈平台"],
              business_opportunities_zh: ["按节省工时订阅收费"],
              must_watch_picks: [
                {
                  video_id: "vid-openai-1",
                  title: "OpenAI Cyber Security Harness",
                  channel_name: "OpenAI",
                  score: 9.2,
                  reason_zh: "详解自动化漏洞定位与补丁回归验证。",
                },
              ],
              funnel_stats: {
                total_videos: 115,
                distilled_count: 115,
                must_watch_count: 31,
                shorts_filtered_count: 79,
              },
              delta: {
                previous_brief_id: "wb-r8-prev",
                previous_created_at: "2026-11-13T15:15:01Z",
                previous_title_zh: "《上周情报周报》",
                total_videos_delta: 3,
                distilled_delta: 13,
                must_watch_delta: 1,
                new_picks: [],
                new_shifts_zh: [
                  "从‘工具’到‘员工’：长周期自主执行成为核心壁垒",
                  "安全工程范式转移：从人工审计到‘漏洞即代码’自动闭环",
                ],
                new_opportunities_zh: ["长周期任务监控平台"],
                summary_zh: "较上期新增提炼 13 篇 · 新增 1 篇必看干货 · 2 项新趋势风向",
              },
              obsidian_markdown:
                "# 《本周 AI 产品与商业情报周报》\n\n> **较上期演进对比**：2 项新趋势风向\n> - **本期新趋势风向**：从‘工具’到‘员工’：长周期自主执行成为核心壁垒",
              provider: "ollama",
              model: "qwen3.5:9b",
              created_at: "2026-11-14T16:44:06Z",
            },
          });
        }
        if (input.endsWith("/knowledge-delta")) {
          return okJson({
            knowledge_delta: {
              window_start: "2026-11-08T00:00:00Z",
              window_end: "2026-11-15T00:00:00Z",
              timezone: "Asia/Shanghai",
              status: "available",
              detail_limit: 2,
              categories: [],
            },
          });
        }
        if (input.endsWith("/videos")) {
          return okJson({
            videos: [
              {
                video_id: "vid-openai-1",
                provider: "YOUTUBE",
                channel_id: "UC-openai",
                channel_name: "OpenAI",
                title: "OpenAI Cyber Security Harness",
                source_url: "https://www.youtube.com/watch?v=vid-openai-1",
                published_at: "2026-11-14T10:00:00Z",
                processing_status: "READY",
                duration_seconds: 1800,
                last_updated: "2026-11-14T10:05:00Z",
                ai_brief: {
                  video_id: "vid-openai-1",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "自动化回归沙箱让漏洞修复具备确定性闭环。",
                  summary_zh: "详解自动化安全验证。",
                  score: 9.2,
                  score_reason_zh: "工程密度极高",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["安全自动化"],
                  topic_cluster_zh: "AI Agent 与自动化架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vid-greg-agent",
                provider: "YOUTUBE",
                channel_id: "UC-greg",
                channel_name: "Greg Isenberg",
                title: "Building Vertical AI Agent Agencies",
                source_url: "https://www.youtube.com/watch?v=vid-greg-agent",
                published_at: "2026-11-14T08:00:00Z",
                processing_status: "READY",
                duration_seconds: 2100,
                last_updated: "2026-11-14T08:05:00Z",
                ai_brief: {
                  video_id: "vid-greg-agent",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "围绕垂直诊所与律所封装标准化虚拟员工。",
                  summary_zh: "拆解一人公司 Agent 交付。",
                  score: 8.8,
                  score_reason_zh: "商业切口清晰",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["虚拟员工"],
                  topic_cluster_zh: "AI Agent 与自动化架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vid-greg-biz",
                provider: "YOUTUBE",
                channel_id: "UC-greg",
                channel_name: "Greg Isenberg",
                title: "Micro-SaaS Pricing Tiers",
                source_url: "https://www.youtube.com/watch?v=vid-greg-biz",
                published_at: "2026-11-13T08:00:00Z",
                processing_status: "READY",
                duration_seconds: 1650,
                last_updated: "2026-11-13T08:05:00Z",
                ai_brief: {
                  video_id: "vid-greg-biz",
                  source_basis: "TRANSCRIPT",
                  headline_zh: "分层年费提升微 SaaS 现金流。",
                  summary_zh: "拆解年费定价。",
                  score: 8.5,
                  score_reason_zh: "实操性强",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["定价"],
                  topic_cluster_zh: "AI 产品机会与一人公司变现",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
            ],
          });
        }
        if (input.includes("/videos/vid-openai-1") && !input.endsWith("/evidence") && !input.endsWith("/deep-analysis")) {
          return okJson({
            video: {
              video_id: "vid-openai-1",
              provider: "YOUTUBE",
              channel_id: "UC-openai",
              channel_name: "OpenAI",
              title: "OpenAI Cyber Security Harness",
              source_url: "https://www.youtube.com/watch?v=vid-openai-1",
              published_at: "2026-11-14T10:00:00Z",
              processing_status: "READY",
              duration_seconds: 1800,
              last_updated: "2026-11-14T10:05:00Z",
              ai_brief: {
                video_id: "vid-openai-1",
                source_basis: "TRANSCRIPT",
                headline_zh: "自动化回归沙箱让漏洞修复具备确定性闭环。",
                summary_zh: "详解自动化安全验证。",
                score: 9.2,
                score_reason_zh: "工程密度极高",
                recommendation_tier: "MUST_WATCH",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                starred: false,
                is_read: false,
                topics_zh: ["安全自动化"],
                topic_cluster_zh: "AI Agent 与自动化架构",
                product_opportunities_zh: ["CI 安全自动修复插件"],
                business_opportunities_zh: [],
              },
            },
            transcript: { status: "AVAILABLE", text: "Deterministic security verification." },
            note: {
              v2: {
                status: "AVAILABLE",
                method: "SOURCE_EXCERPTS",
                summary: "Deterministic security verification.",
                core_points: [],
                timestamped_key_points: [],
                evidence_references: [],
              },
            },
            intelligence_result: {
              status: "NOT_PROCESSED",
              has_new_intelligence: false,
              intelligence_id: null,
              revision_id: null,
              updated_at: "2026-11-14T10:05:00Z",
            },
            history: [],
          });
        }
        if (input.endsWith("/evidence")) return okJson({ evidence: [] });
        if (input.endsWith("/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: {
                availability: "NOT_QUALIFIED",
                reason_code: "NO_QUALIFIED_MODEL",
                reason: null,
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
        if (input.endsWith("/intelligence")) {
          // Simulate slow /intelligence endpoint so CommandPalette must populate /videos & /research/sessions without head-of-line blocking
          return new Promise(() => {});
        }
        if (input.endsWith("/topics")) {
          return okJson({
            topics: [
              {
                topic_id: "topic-agent-r8",
                name: "AI Agent 与自动化架构",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CONFIRMED",
                independence: "MULTI_SOURCE",
                contributions: [],
                timeline: [],
                relations: [],
                ai_evolution: {
                  video_count: 26,
                  must_watch_count: 21,
                  unread_count: 20,
                  recent_7d_count: 6,
                  avg_score: 8.7,
                  latest_headline_zh: "自动化回归沙箱让漏洞修复具备确定性闭环。",
                  source_channels: ["OpenAI", "Greg Isenberg"],
                  channel_breakdown: [
                    {
                      channel_key: "OpenAI",
                      channel_label: "OpenAI",
                      video_count: 18,
                      must_watch_count: 15,
                      unread_count: 14,
                    },
                    {
                      channel_key: "Greg Isenberg",
                      channel_label: "Greg Isenberg",
                      video_count: 6,
                      must_watch_count: 4,
                      unread_count: 6,
                    },
                  ],
                },
              },
            ],
          });
        }
        if (input.endsWith("/topics/topic-agent-r8")) {
          return okJson({
            topic: {
              topic_id: "topic-agent-r8",
              name: "AI Agent 与自动化架构",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "CONFIRMED",
              independence: "MULTI_SOURCE",
              contributions: [],
              timeline: [],
              relations: [],
              ai_evolution: {
                video_count: 26,
                must_watch_count: 21,
                unread_count: 20,
                recent_7d_count: 6,
                avg_score: 8.7,
                latest_headline_zh: "自动化回归沙箱让漏洞修复具备确定性闭环。",
                synthesis_zh: "OpenAI 与 Greg Isenberg 一致聚焦可验证 Agent 工作流。",
                source_channels: ["OpenAI", "Greg Isenberg"],
                channel_breakdown: [
                  {
                    channel_key: "OpenAI",
                    channel_label: "OpenAI",
                    video_count: 18,
                    must_watch_count: 15,
                    unread_count: 14,
                  },
                  {
                    channel_key: "Greg Isenberg",
                    channel_label: "Greg Isenberg",
                    video_count: 6,
                    must_watch_count: 4,
                    unread_count: 6,
                  },
                ],
                obsidian_markdown: "# 专题知识索引（MOC）：[[AI Agent 与自动化架构]]",
                entries: [
                  {
                    video_id: "vid-openai-1",
                    title: "OpenAI Cyber Security Harness",
                    channel_name: "OpenAI",
                    published_at: "2026-11-14T10:00:00Z",
                    score: 9.2,
                    recommendation_tier: "MUST_WATCH",
                    source_basis: "TRANSCRIPT",
                    headline_zh: "自动化回归沙箱让漏洞修复具备确定性闭环。",
                    summary_zh: "详解自动化安全验证。",
                    product_opportunities_zh: [],
                    business_opportunities_zh: [],
                  },
                ],
              },
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [
              {
                session_id: "qa-r8-first",
                question: "本地实战课里关于 AI Agent 工程落地最核心的建议是什么？",
                scope_label_zh: "对比 2 条指定视频",
                video_count: 2,
                answer_zh: "第一条默认会话答案：本地课强调状态机。",
                key_takeaways_zh: [],
                action_items_zh: [],
                citations: [],
                obsidian_markdown: "# Q1",
                provider: "ollama",
                model: "qwen3.5:9b",
                created_at: "2026-11-15T01:00:00Z",
              },
              {
                session_id: "qa-r8-mozilla",
                question: "Mozilla 是如何用 GPT-6 Cyber 发现并修复 Firefox 漏洞的？",
                scope_label_zh: "全库 36 条长视频",
                video_count: 36,
                answer_zh: "Mozilla 借助确定性复现沙箱自动验证 Firefox 内存漏洞补丁 [E1]。",
                key_takeaways_zh: ["复现脚本先于补丁合并"],
                action_items_zh: [],
                citations: [
                  {
                    ref_label: "E1",
                    video_id: "vid-openai-1",
                    video_title: "OpenAI Cyber Security Harness",
                    channel_name: "OpenAI",
                    evidence_id: "ev-1",
                    start_ms: 12000,
                    end_ms: 20000,
                    timestamp_label: "00:12",
                    excerpt: "Deterministic reproduction harness.",
                  },
                ],
                obsidian_markdown: "# Q2",
                provider: "ollama",
                model: "qwen3.5:9b",
                created_at: "2026-11-14T20:00:00Z",
              },
            ],
            suggested_questions: [],
            scope_options: {
              starred_count: 0,
              channels: [
                { key: "OpenAI", label: "OpenAI", provider: "YOUTUBE", video_count: 18 },
                { key: "Greg Isenberg", label: "Greg Isenberg", provider: "YOUTUBE", video_count: 11 },
              ],
              topic_clusters: [
                { name: "AI Agent 与自动化架构", video_count: 26 },
                { name: "AI 产品机会与一人公司变现", video_count: 5 },
              ],
              videos: [],
            },
          });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    render(<App />);

    // 1) R8-1: #Home Weekly Brief delta strip renders concrete new trend shifts even when new_picks is empty
    const deltaRegion = await screen.findByRole("region", { name: "较上期周报演进对比" });
    expect(within(deltaRegion).getByText(/2 项新趋势风向/)).toBeTruthy();
    expect(
      within(deltaRegion).getByText("从‘工具’到‘员工’：长周期自主执行成为核心壁垒"),
    ).toBeTruthy();
    expect(
      within(deltaRegion).getByText("安全工程范式转移：从人工审计到‘漏洞即代码’自动闭环"),
    ).toBeTruthy();

    // 2) R8-3: Cmd+K indexes saved Cross-Video AI Q&A sessions and jumps directly to the matched session
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const cmdkDialog = await screen.findByRole("dialog", { name: /全局搜索与命令面板/ });
    const cmdkInput = within(cmdkDialog).getByRole("combobox");
    fireEvent.change(cmdkInput, { target: { value: "Mozilla" } });

    const mozillaCmdkOption = await within(cmdkDialog).findByRole("option", {
      name: /Mozilla 是如何用 GPT-6 Cyber 发现并修复 Firefox 漏洞的/,
    });
    fireEvent.click(mozillaCmdkOption);

    await waitFor(() => expect(location.hash).toBe("#Research"));
    expect(
      await screen.findByText(/Mozilla 借助确定性复现沙箱自动验证 Firefox 内存漏洞补丁/),
    ).toBeTruthy();

    // 3) R8-3 + Clear filter bugfix: Cmd+K channel quick-filter jumps to #Content pre-filtered to Greg Isenberg
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const cmdkDialog2 = await screen.findByRole("dialog", { name: /全局搜索与命令面板/ });
    const cmdkInput2 = within(cmdkDialog2).getByRole("combobox");
    fireEvent.change(cmdkInput2, { target: { value: "Greg Isenberg" } });

    const gregFilterOpt = await within(cmdkDialog2).findByRole("option", {
      name: /筛选频道干货：Greg Isenberg/,
    });
    fireEvent.click(gregFilterOpt);

    await waitFor(() => expect(location.hash).toBe("#Content"));
    const channelSelect = (await screen.findByLabelText("按频道筛选")) as HTMLSelectElement;
    expect(channelSelect.value).toBe("Greg Isenberg");
    expect(screen.getByText("Building Vertical AI Agent Agencies")).toBeTruthy();
    expect(screen.queryByText("OpenAI Cyber Security Harness")).toBeNull();

    // Verify "清空筛选" resets channelFilter as well!
    const searchBox = screen.getByRole("searchbox", { name: /搜索内容库/ });
    fireEvent.change(searchBox, { target: { value: "不存在的检索词xyz" } });
    fireEvent.click(await screen.findByRole("button", { name: "清空筛选" }));
    expect((screen.getByLabelText("按频道筛选") as HTMLSelectElement).value).toBe("ALL");
    expect(screen.getByText("OpenAI Cyber Security Harness")).toBeTruthy();

    // 4) R8-2: Open video detail -> click [[AI Agent 与自动化架构]] wikilink -> opens Topic MOC -> click Greg Isenberg channel breakdown chip -> filters #Content by BOTH Topic + Channel
    fireEvent.click(screen.getByText("OpenAI Cyber Security Harness"));
    await waitFor(() => expect(location.hash).toBe("#Content/vid-openai-1"));

    const topicWikilinkBtn = await screen.findByRole("button", {
      name: /\[\[AI Agent 与自动化架构\]\]/,
    });
    fireEvent.click(topicWikilinkBtn);

    await waitFor(() => expect(location.hash).toBe("#Topics"));
    expect(
      await screen.findByText("OpenAI 与 Greg Isenberg 一致聚焦可验证 Agent 工作流。"),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /在内容库筛选本专题 \(26\)/ })).toBeTruthy();

    const gregBreakdownChip = screen.getByRole("button", {
      name: /Greg Isenberg · 6 篇/,
    });
    fireEvent.click(gregBreakdownChip);

    await waitFor(() => expect(location.hash).toBe("#Content"));
    expect((await screen.findByLabelText("按专题筛选内容") as HTMLSelectElement).value).toBe(
      "AI Agent 与自动化架构",
    );
    expect((screen.getByLabelText("按频道筛选") as HTMLSelectElement).value).toBe("Greg Isenberg");
    expect(screen.getByText("Building Vertical AI Agent Agencies")).toBeTruthy();
    expect(screen.queryByText("Micro-SaaS Pricing Tiers")).toBeNull();
    expect(screen.queryByText("OpenAI Cyber Security Harness")).toBeNull();
  });

  it("R9: advances Mark Read & Next strictly within active Content filter scope with filter context pill, and supports pinning & deleting Cross-Video Q&A sessions", async () => {
    location.hash = "#Content";
    const curationCalls: { url: string; body: unknown }[] = [];
    const qaPinCalls: { url: string; body: unknown }[] = [];
    const qaDeleteCalls: string[] = [];

    let greg1Read = false;
    let qaSessionsState = [
      {
        session_id: "qa-newer-scratch",
        question: "临时实验提问：测试模型连通性",
        scope_label_zh: "全库检索",
        video_count: 1,
        pinned: false,
        answer_zh: "这是一条临时测试提问。",
        key_takeaways_zh: [],
        action_items_zh: [],
        citations: [],
        obsidian_markdown: "# 临时实验提问",
        provider: "ollama",
        model: "qwen3.5:9b",
        created_at: "2026-11-15T12:00:00Z",
      },
      {
        session_id: "qa-older-core",
        question: "核心架构沉淀：多智能体状态机如何防死循环？",
        scope_label_zh: "限定频道：OpenAI",
        video_count: 3,
        pinned: false,
        answer_zh: "显式最大步数预算与幂等状态转移是关键。",
        key_takeaways_zh: ["显式状态机优于自由循环"],
        action_items_zh: ["增加步数熔断器"],
        citations: [
          {
            ref_label: "1",
            video_id: "vid-openai-top",
            video_title: "OpenAI Highest Score Harness",
            channel_name: "OpenAI",
            evidence_id: "ev-r9-1",
            start_ms: 12000,
            end_ms: 28000,
            timestamp_label: "00:12",
            excerpt: "Explicit state budgets stop runaway agent loops.",
          },
        ],
        obsidian_markdown: "# 核心架构沉淀",
        provider: "ollama",
        model: "qwen3.5:9b",
        created_at: "2026-11-14T09:00:00Z",
      },
    ];

    const makeVideoDetail = (
      videoId: string,
      title: string,
      channelName: string,
      score: number,
      isRead: boolean,
      topicCluster = "AI Agent 与自动化架构",
    ) => ({
      video: {
        video_id: videoId,
        provider: "YOUTUBE",
        channel_id: channelName === "OpenAI" ? "UC1111111111111111111111" : "UC2222222222222222222222",
        channel_name: channelName,
        title,
        source_url: `https://www.youtube.com/watch?v=${videoId}`,
        published_at: "2026-11-15T08:00:00Z",
        processing_status: "READY",
        duration_seconds: 1800,
        ai_brief: {
          video_id: videoId,
          source_basis: "TRANSCRIPT",
          headline_zh: `${title} 核心结论`,
          summary_zh: `${title} 深度摘要`,
          score,
          score_reason_zh: "高价值工程拆解",
          recommendation_tier: "MUST_WATCH",
          content_bucket: "DEEP_DIVE",
          is_short_noise: false,
          starred: false,
          is_read: isRead,
          topics_zh: ["Agent 状态机"],
          topic_cluster_zh: topicCluster,
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      transcript: { status: "AVAILABLE", segments: [] },
      note: { v2: null },
      evidence: [],
      intelligence_result: { status: "NOT_REQUESTED" },
      history: [],
      obsidian_markdown: `# ${title}`,
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos")) {
          return okJson({
            videos: [
              {
                video_id: "vid-openai-top",
                provider: "YOUTUBE",
                channel_id: "UC1111111111111111111111",
                channel_name: "OpenAI",
                title: "OpenAI Highest Score Harness",
                source_url: "https://www.youtube.com/watch?v=vid-openai-top",
                published_at: "2026-11-15T10:00:00Z",
                processing_status: "READY",
                duration_seconds: 2100,
                last_updated: "2026-11-15T10:05:00Z",
                ai_brief: makeVideoDetail("vid-openai-top", "OpenAI Highest Score Harness", "OpenAI", 9.8, false).video.ai_brief,
              },
              {
                video_id: "vid-greg-biz",
                provider: "YOUTUBE",
                channel_id: "UC2222222222222222222222",
                channel_name: "Greg Isenberg",
                title: "Greg SaaS Pricing Playbook",
                source_url: "https://www.youtube.com/watch?v=vid-greg-biz",
                published_at: "2026-11-15T09:30:00Z",
                processing_status: "READY",
                duration_seconds: 1700,
                last_updated: "2026-11-15T09:35:00Z",
                ai_brief: makeVideoDetail(
                  "vid-greg-biz",
                  "Greg SaaS Pricing Playbook",
                  "Greg Isenberg",
                  9.5,
                  false,
                  "AI 产品机会与一人公司变现",
                ).video.ai_brief,
              },
              {
                video_id: "vid-greg-1",
                provider: "YOUTUBE",
                channel_id: "UC2222222222222222222222",
                channel_name: "Greg Isenberg",
                title: "Greg Agent Workflow Part 1",
                source_url: "https://www.youtube.com/watch?v=vid-greg-1",
                published_at: "2026-11-15T09:00:00Z",
                processing_status: "READY",
                duration_seconds: 1600,
                last_updated: "2026-11-15T09:05:00Z",
                ai_brief: makeVideoDetail("vid-greg-1", "Greg Agent Workflow Part 1", "Greg Isenberg", 9.0, greg1Read).video.ai_brief,
              },
              {
                video_id: "vid-greg-2",
                provider: "YOUTUBE",
                channel_id: "UC2222222222222222222222",
                channel_name: "Greg Isenberg",
                title: "Greg Agent Workflow Part 2",
                source_url: "https://www.youtube.com/watch?v=vid-greg-2",
                published_at: "2026-11-15T08:00:00Z",
                processing_status: "READY",
                duration_seconds: 1500,
                last_updated: "2026-11-15T08:05:00Z",
                ai_brief: makeVideoDetail("vid-greg-2", "Greg Agent Workflow Part 2", "Greg Isenberg", 8.6, false).video.ai_brief,
              },
            ],
          });
        }
        if (input.endsWith("/videos/vid-greg-1")) {
          return okJson(makeVideoDetail("vid-greg-1", "Greg Agent Workflow Part 1", "Greg Isenberg", 9.0, greg1Read));
        }
        if (input.endsWith("/videos/vid-greg-2")) {
          return okJson(makeVideoDetail("vid-greg-2", "Greg Agent Workflow Part 2", "Greg Isenberg", 8.6, false));
        }
        if (input.endsWith("/workspace-ai/videos/vid-greg-1/curation") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body ?? "{}"));
          curationCalls.push({ url: input, body: parsed });
          if (typeof parsed.is_read === "boolean") greg1Read = parsed.is_read;
          return okJson({ video_id: "vid-greg-1", starred: false, is_read: greg1Read });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: qaSessionsState,
            suggested_questions: [],
            scope_options: { starred_count: 0, channels: [], topic_clusters: [], videos: [] },
          });
        }
        if (input.endsWith("/workspace-ai/research/sessions/qa-older-core/pin") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body ?? "{}"));
          qaPinCalls.push({ url: input, body: parsed });
          qaSessionsState = qaSessionsState
            .map((s) => (s.session_id === "qa-older-core" ? { ...s, pinned: Boolean(parsed.pinned) } : s))
            .sort((a, b) => Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)) || b.created_at.localeCompare(a.created_at));
          const updated = qaSessionsState.find((s) => s.session_id === "qa-older-core")!;
          return okJson({ session: updated });
        }
        if (input.endsWith("/workspace-ai/research/sessions/qa-newer-scratch/delete") && init?.method === "POST") {
          qaDeleteCalls.push(input);
          qaSessionsState = qaSessionsState.filter((s) => s.session_id !== "qa-newer-scratch");
          return okJson({ deleted: true, session_id: "qa-newer-scratch" });
        }
        if (input.includes("/creator-following")) {
          return okJson({ available: false, reason_code: "DISABLED" });
        }
        if (input.endsWith("/intelligence")) {
          return okJson({ intelligence: [] });
        }
        if (input.endsWith("/topics")) {
          return okJson({ topics: [] });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        return okJson({});
      }),
    );

    render(<App />);

    // 1) R9-1: Filter #Content by Topic + Channel ("Greg Isenberg"), open item #1, verify scoped filter pill & scoped Mark Read & Next
    const topicSelect = (await screen.findByLabelText("按专题筛选内容")) as HTMLSelectElement;
    fireEvent.change(topicSelect, { target: { value: "AI Agent 与自动化架构" } });
    const channelSelect = screen.getByLabelText("按频道筛选") as HTMLSelectElement;
    fireEvent.change(channelSelect, { target: { value: "Greg Isenberg" } });

    fireEvent.click(screen.getByText("Greg Agent Workflow Part 1"));
    await waitFor(() => expect(location.hash).toBe("#Content/vid-greg-1"));

    expect(
      await screen.findByText("当前筛选：AI Agent 与自动化架构 · Greg Isenberg"),
    ).toBeTruthy();

    const markNextBtn = await screen.findByRole("button", { name: "标已读并看下一篇" });
    expect(markNextBtn.textContent).toContain("本筛选 1");
    expect(markNextBtn.getAttribute("title")).toContain("Greg Agent Workflow Part 2");

    fireEvent.click(markNextBtn);
    await waitFor(() => expect(curationCalls).toHaveLength(1));
    await waitFor(() => expect(location.hash).toBe("#Content/vid-greg-2"));
    expect(await screen.findByRole("heading", { name: "Greg Agent Workflow Part 2" })).toBeTruthy();

    // 2) R9-2: Navigate to #Research, pin older landmark session -> floats to #1; delete scratch session -> removed & active falls back
    fireEvent.click(screen.getByRole("button", { name: "AI 跨视频问答" }));
    await waitFor(() => expect(location.hash).toBe("#Research"));

    const olderChip = await screen.findByRole("button", {
      name: /核心架构沉淀：多智能体状态机如何防死循环？ · 3 篇/,
    });
    fireEvent.click(olderChip);

    const pinBtn = screen.getByRole("button", { name: "置顶问答" });
    fireEvent.click(pinBtn);
    await waitFor(() => expect(qaPinCalls).toHaveLength(1));
    expect(qaPinCalls[0].body).toEqual({ pinned: true });
    expect(await screen.findByRole("button", { name: "已置顶 · 取消" })).toBeTruthy();

    const historyGroup = document.querySelector(".ai-session-history") as HTMLElement;
    const historyButtons = within(historyGroup).getAllByRole("button");
    expect(historyButtons[0].textContent).toContain("[置顶]");
    expect(historyButtons[0].textContent).toContain("核心架构沉淀：多智能体状态机如何防死循环？");

    // Select throwaway scratch session and delete it
    fireEvent.click(
      within(historyGroup).getByRole("button", { name: /临时实验提问：测试模型连通性/ }),
    );
    fireEvent.click(screen.getByRole("button", { name: "删除问答" }));
    await waitFor(() => expect(qaDeleteCalls).toHaveLength(1));
    expect(screen.queryByText("临时实验提问：测试模型连通性")).toBeNull();
    expect(
      screen.getByRole("heading", { name: "核心架构沉淀：多智能体状态机如何防死循环？" }),
    ).toBeTruthy();

    // 3) Cmd+K shows "已置顶" subtitle on pinned Q&A session
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const cmdInput = await screen.findByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "状态机" } });
    const pinnedOpt = await screen.findByRole("option", {
      name: /核心架构沉淀：多智能体状态机如何防死循环/,
    });
    expect(pinnedOpt.textContent).toContain("已置顶");
  });

  it("R10: filters Intelligence cards by linked Topic with [[Topic]] jump & 1-click Copy Insight Card, and copies plain-text brief in Cross-Video Q&A", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Intelligence";

    const copiedTexts: string[] = [];
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async (text: string) => {
          copiedTexts.push(text);
        }),
      },
    });

    const makeIntelItem = (
      id: string,
      conclusion: string,
      sourceName: string,
      videoTitle: string,
      topicId: string,
      topicName: string,
    ) => ({
      status: "AVAILABLE",
      trusted: true,
      intelligence_id: id,
      claim_kind: "SYSTEM_INFERENCE",
      state: "CORROBORATED",
      linked_topics: [{ topic_id: topicId, name: topicName }],
      card: {
        core_conclusion: conclusion,
        user_relevant_information: [`${conclusion} 对产品设计的直接启发。`],
        important_new_information: [`${videoTitle} 给出的最新验证信号。`],
        meaningful_details: ["关键工程指标提升 3 倍"],
        source_id: `src-${id}`,
        source_display_name: sourceName,
        source_url: "https://www.youtube.com/@example",
        video_id: `vid-${id}`,
        video_title: videoTitle,
        original_video_url: `https://www.youtube.com/watch?v=vid-${id}`,
        evidence_links: [
          {
            evidence_id: `ev-${id}`,
            artifact_id: `art-${id}`,
            start_ms: 75000,
            end_ms: 92000,
            locator_type: "TIMED_MEDIA",
            language: "en",
            lineage_kind: "DIRECT_QUOTE",
            role: "PRIMARY",
            original_excerpt: "Vertical workflow pricing beats generic chat wrappers.",
            translated_excerpt: null,
            translated_language: null,
            stance: "supporting",
          },
        ],
      },
    });

    const mockIntel = [
      makeIntelItem(
        "intel-agent-1",
        "状态机拆解让多智能体生产可靠性提升三倍",
        "OpenAI",
        "Stateful Agents Deep Dive",
        "topic:agent-arch",
        "AI Agent 与自动化架构",
      ),
      makeIntelItem(
        "intel-agent-2",
        "Schema 强约束工具调用可消除 90% 参数幻觉",
        "OpenAI",
        "Tool Contract Engineering",
        "topic:agent-arch",
        "AI Agent 与自动化架构",
      ),
      makeIntelItem(
        "intel-agent-3",
        "离线基准评测集是 Agent 迭代的唯一护城河",
        "AI 实战课",
        "Agent Eval Playbook",
        "topic:agent-arch",
        "AI Agent 与自动化架构",
      ),
      makeIntelItem(
        "intel-biz-1",
        "一人公司聚焦垂直行业年费工作流远优于通用聊天壳",
        "Greg Isenberg",
        "Solo AI SaaS Pricing",
        "topic:solo-biz",
        "AI 产品机会与一人公司变现",
      ),
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((rawInput: RequestInfo | URL) => {
        const input = String(rawInput);
        if (input.endsWith("/intelligence")) {
          return okJson({ intelligence: mockIntel, activity: [] });
        }
        if (input.endsWith("/saved-intelligence")) {
          return okJson({ saved: [] });
        }
        if (input.endsWith("/topics")) {
          return okJson({
            topics: [
              {
                topic_id: "topic:agent-arch",
                name: "AI Agent 与自动化架构",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CORROBORATED",
                independence: "MULTI_SOURCE",
                contributions: [],
                timeline: [],
                relations: [],
              },
              {
                topic_id: "topic:solo-biz",
                name: "AI 产品机会与一人公司变现",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CORROBORATED",
                independence: "SINGLE_SOURCE",
                contributions: [],
                timeline: [],
                relations: [],
              },
            ],
          });
        }
        if (input.endsWith("/topics/topic:solo-biz")) {
          return okJson({
            topic: {
              topic_id: "topic:solo-biz",
              name: "AI 产品机会与一人公司变现",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "CORROBORATED",
              independence: "SINGLE_SOURCE",
              contributions: [],
              timeline: [],
              relations: [],
              ai_evolution: {
                topic_name: "AI 产品机会与一人公司变现",
                video_count: 1,
                must_watch_count: 1,
                avg_score: 9.3,
                recent_7d_count: 1,
                latest_headline_zh: "一人公司垂直工作流定价策略",
                synthesis_zh: "聚焦高客单价垂直场景。",
                obsidian_markdown: "# AI 产品机会与一人公司变现\n",
                entries: [
                  {
                    video_id: "vid-intel-biz-1",
                    title: "Solo AI SaaS Pricing",
                    channel_name: "Greg Isenberg",
                    score: 9.3,
                    recommendation_tier: "MUST_WATCH",
                    headline_zh: "一人公司垂直工作流定价策略",
                  },
                ],
              },
            },
          });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [
              {
                session_id: "qa-r10-1",
                question: "垂直行业 AI SaaS 如何设计高留存定价？",
                scope_label_zh: "频道：Greg Isenberg",
                answer_zh: "按交付结果而非席位收费，锁定核心业务表单流转。",
                key_takeaways_zh: ["切入高频刚需审批节点", "提供可审计人工兜底"],
                action_items_zh: ["梳理目标行业 Top 3 重复手工单据"],
                citations: [
                  {
                    ref_label: "E1",
                    video_id: "vid-intel-biz-1",
                    video_title: "Solo AI SaaS Pricing",
                    channel_name: "Greg Isenberg",
                    evidence_id: "ev-intel-biz-1",
                    timestamp_label: "01:15",
                    start_ms: 75000,
                    excerpt: "Vertical workflow pricing beats generic chat wrappers.",
                  },
                ],
                provider: "ollama",
                model: "qwen3:8b",
                obsidian_markdown: "---\ntags: [ai-qa]\n---\n# [[Solo AI SaaS Pricing]]\n",
                created_at: "2026-11-16T00:00:00Z",
                video_count: 1,
                pinned: false,
              },
            ],
            suggested_questions: [],
            scope_options: { starred_count: 0, channels: [], topic_clusters: [], videos: [] },
          });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        if (input.includes("/creator-following")) {
          return okJson({ available: false, reason_code: "DISABLED" });
        }
        return okJson({});
      }),
    );

    render(<App />);

    // 1) Filter #Intelligence by linked Topic -> narrows 4 cards down to 1
    const intelTopicSelect = (await screen.findByLabelText("按专题筛选洞察")) as HTMLSelectElement;
    expect(intelTopicSelect.textContent).toContain("AI Agent 与自动化架构 (3)");
    expect(intelTopicSelect.textContent).toContain("AI 产品机会与一人公司变现 (1)");

    fireEvent.change(intelTopicSelect, { target: { value: "topic:solo-biz" } });
    expect(
      screen.getByRole("heading", { name: "一人公司聚焦垂直行业年费工作流远优于通用聊天壳" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "状态机拆解让多智能体生产可靠性提升三倍" }),
    ).toBeNull();

    // 2) Copy Insight Card -> copies structured plain-text insight with timestamped quote
    const copyInsightBtn = screen.getByRole("button", { name: "复制洞察卡片" });
    fireEvent.click(copyInsightBtn);
    await waitFor(() => expect(copiedTexts).toHaveLength(1));
    expect(copiedTexts[0]).toContain("【验证洞察】一人公司聚焦垂直行业年费工作流远优于通用聊天壳");
    expect(copiedTexts[0]).toContain("Greg Isenberg");
    expect(copiedTexts[0]).toContain("Solo AI SaaS Pricing");
    expect(copiedTexts[0]).toContain("AI 产品机会与一人公司变现");
    expect(copiedTexts[0]).toContain("Vertical workflow pricing beats generic chat wrappers.");
    expect(copiedTexts[0]).not.toContain("[[");

    // 3) Click [[AI 产品机会与一人公司变现]] chip on IntelligenceCard -> opens that Topic detail in #Topics
    fireEvent.click(
      screen.getByRole("button", { name: "[[AI 产品机会与一人公司变现]]" }),
    );
    await waitFor(() => expect(location.hash).toBe("#Topics"));
    expect(await screen.findByText("聚焦高客单价垂直场景。")).toBeTruthy();

    // 4) Navigate to #Research and click "复制纯文本提纲" -> copies YAML-free, wikilink-free plain-text brief
    fireEvent.click(screen.getByRole("button", { name: "AI 跨视频问答" }));
    await waitFor(() => expect(location.hash).toBe("#Research"));

    const copyPlainBtn = await screen.findByRole("button", { name: "复制纯文本提纲" });
    fireEvent.click(copyPlainBtn);
    await waitFor(() => expect(copiedTexts).toHaveLength(2));
    expect(copiedTexts[1]).toContain("【跨视频深度问答】垂直行业 AI SaaS 如何设计高留存定价？");
    expect(copiedTexts[1]).toContain("按交付结果而非席位收费，锁定核心业务表单流转。");
    expect(copiedTexts[1]).toContain("切入高频刚需审批节点");
    expect(copiedTexts[1]).toContain("梳理目标行业 Top 3 重复手工单据");
    expect(copiedTexts[1]).toContain("[E1] 《Solo AI SaaS Pricing》（Greg Isenberg · 01:15）");
    expect(copiedTexts[1]).not.toContain("---");
    expect(copiedTexts[1]).not.toContain("[[");
  });

  it("R11: hands off Topic detail to filtered Intelligence cards, localizes Chinese Claim & Local library pills without gluing Topic stats, and copies plain-text Video AI summary", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Topics";

    const copiedTexts: string[] = [];
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async (text: string) => {
          copiedTexts.push(text);
        }),
      },
    });

    const makeCard = (
      id: string,
      claimKind: string,
      conclusion: string,
      sourceName: string,
      videoId: string,
      videoTitle: string,
      topicId: string,
      topicName: string,
    ) => ({
      status: "AVAILABLE",
      trusted: true,
      intelligence_id: id,
      claim_kind: claimKind,
      state: "NEW",
      linked_topics: [{ topic_id: topicId, name: topicName }],
      card: {
        core_conclusion: conclusion,
        user_relevant_information: [`${conclusion} 的落地路径。`],
        important_new_information: [],
        meaningful_details: [],
        source_id: `src-${id}`,
        source_display_name: sourceName,
        source_url: sourceName === "Local library" ? null : "https://www.youtube.com/@greg",
        video_id: videoId,
        video_title: videoTitle,
        original_video_url:
          sourceName === "Local library"
            ? null
            : `https://www.youtube.com/watch?v=${videoId}`,
        evidence_links: [
          {
            evidence_id: `ev-${id}`,
            artifact_id: `art-${id}`,
            start_ms: 30000,
            end_ms: 45000,
            locator_type: "TIMED_MEDIA",
            language: "en",
            lineage_kind: "DIRECT_QUOTE",
            role: "PRIMARY",
            original_excerpt: "Charge for verified outcomes, not seats.",
            translated_excerpt: null,
            translated_language: null,
            stance: "supporting",
          },
        ],
      },
    });

    const mockIntel = [
      makeCard(
        "intel-biz-1",
        "EVIDENCE_BACKED_STATEMENT",
        "垂直工作流按交付结果定价留存率翻倍",
        "Greg Isenberg",
        "vid-biz-1",
        "Outcome Pricing Playbook",
        "topic:solo-biz",
        "AI 产品机会与一人公司变现",
      ),
      makeCard(
        "intel-biz-2",
        "FACT",
        "年付合同显著降低一人公司现金流波动",
        "Greg Isenberg",
        "vid-biz-2",
        "Annual Plans for Solo Founders",
        "topic:solo-biz",
        "AI 产品机会与一人公司变现",
      ),
      makeCard(
        "intel-local-1",
        "RUMOR",
        "端侧小模型推理延迟已可支撑实时语音代理",
        "Local library",
        "vid-local-1",
        "Local Voice Agent Workshop",
        "topic:agent-arch",
        "AI Agent 与自动化架构",
      ),
      makeCard(
        "intel-agent-2",
        "SYSTEM_INFERENCE",
        "确定性状态机优于纯提示词自治循环",
        "OpenAI",
        "vid-agent-2",
        "Deterministic Agent Graphs",
        "topic:agent-arch",
        "AI Agent 与自动化架构",
      ),
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((rawInput: RequestInfo | URL) => {
        const input = String(rawInput);
        if (input.endsWith("/topics")) {
          return okJson({
            topics: [
              {
                topic_id: "topic:solo-biz",
                name: "AI 产品机会与一人公司变现",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CORROBORATED",
                independence: "SINGLE_SOURCE",
                contributions: [
                  {
                    intelligence_id: "intel-biz-1",
                    claim_kind: "EVIDENCE_BACKED_STATEMENT",
                    state: "NEW",
                    available: true,
                    evidence_ids: ["ev-intel-biz-1"],
                  },
                  {
                    intelligence_id: "intel-biz-2",
                    claim_kind: "FACT",
                    state: "NEW",
                    available: true,
                    evidence_ids: ["ev-intel-biz-2"],
                  },
                ],
                timeline: [],
                relations: [],
              },
            ],
          });
        }
        if (input.endsWith("/topics/topic:solo-biz")) {
          return okJson({
            topic: {
              topic_id: "topic:solo-biz",
              name: "AI 产品机会与一人公司变现",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "CORROBORATED",
              independence: "SINGLE_SOURCE",
              contributions: [
                {
                  intelligence_id: "intel-biz-1",
                  claim_kind: "EVIDENCE_BACKED_STATEMENT",
                  state: "NEW",
                  available: true,
                  evidence_ids: ["ev-intel-biz-1"],
                },
                {
                  intelligence_id: "intel-biz-2",
                  claim_kind: "FACT",
                  state: "NEW",
                  available: true,
                  evidence_ids: ["ev-intel-biz-2"],
                },
              ],
              timeline: [],
              relations: [],
              ai_evolution: {
                topic_name: "AI 产品机会与一人公司变现",
                video_count: 2,
                must_watch_count: 2,
                avg_score: 8.6,
                recent_7d_count: 1,
                source_channels: ["Greg Isenberg"],
                latest_headline_zh: "结果导向定价模型",
                synthesis_zh: "一人公司应围绕高价值垂直结果收费。",
                obsidian_markdown: "# AI 产品机会与一人公司变现\n",
                entries: [
                  {
                    video_id: "vid-biz-1",
                    title: "Outcome Pricing Playbook",
                    channel_name: "Greg Isenberg",
                    score: 8.6,
                    recommendation_tier: "MUST_WATCH",
                    headline_zh: "结果导向定价模型",
                  },
                ],
              },
            },
          });
        }
        if (input.endsWith("/intelligence")) {
          return okJson({ intelligence: mockIntel, activity: [] });
        }
        if (input.endsWith("/saved-intelligence")) {
          return okJson({ saved: [] });
        }
        if (input.endsWith("/videos/vid-biz-1/evidence")) {
          return okJson({
            video_id: "vid-biz-1",
            source_url: "https://www.youtube.com/watch?v=vid-biz-1",
            evidence: [],
          });
        }
        if (input.endsWith("/videos/vid-biz-1/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: { availability: "NOT_REQUESTED", qualified: false },
              result: null,
            },
          });
        }
        if (input.endsWith("/videos/vid-biz-1")) {
          return okJson({
            video: {
              video_id: "vid-biz-1",
              provider: "YOUTUBE",
              channel_id: "UC2222222222222222222222",
              title: "Outcome Pricing Playbook",
              channel_name: "Greg Isenberg",
              source_url: "https://www.youtube.com/watch?v=vid-biz-1",
              published_at: "2026-11-15T00:00:00Z",
              processing_status: "READY",
              duration_seconds: 1800,
              ai_brief: {
                video_id: "vid-biz-1",
                score: 9.2,
                recommendation_tier: "MUST_WATCH",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                source_basis: "TRANSCRIPT",
                topics_zh: ["结果定价"],
                topic_cluster_zh: "AI 产品机会与一人公司变现",
                score_reason_zh: "给出了可复制的结果付费合同结构",
                headline_zh: "告别按席位收费：垂直 AI 工作流按业务结果定价留存率翻倍",
                summary_zh: "拆解了单人 SaaS 如何将定价锚定在客户节省的人工工时与成交单量上。",
                product_opportunities_zh: ["内置可审计 ROI 看板展示每周自动处理单量"],
                business_opportunities_zh: ["采用基础年费加超额结果分成混合订阅"],
                obsidian_markdown: "---\ntags: [ai-video]\n---\n# [[Outcome Pricing Playbook]]\n",
                provider: "ollama",
                model: "qwen3:8b",
                starred: true,
                is_read: false,
              },
            },
            transcript: { status: "AVAILABLE", segments: [] },
            note: { v2: null },
            evidence: [],
            intelligence_result: { status: "NOT_REQUESTED" },
            history: [],
            obsidian_markdown: "---\ntags: [ai-video]\n---\n# [[Outcome Pricing Playbook]]\n",
          });
        }
        if (input.endsWith("/videos")) {
          return okJson({ videos: [] });
        }
        if (input.includes("/creator-following")) {
          return okJson({ available: false, reason_code: "DISABLED" });
        }
        return okJson({});
      }),
    );

    render(<App />);

    // 1) Open Topic detail on #Topics -> verify stats text isn't glued ("8.6Greg Isenberg") & click "查看本专题验证洞察 (2)"
    fireEvent.click(await screen.findByRole("button", { name: /AI 产品机会与一人公司变现/ }));
    expect(await screen.findByText("一人公司应围绕高价值垂直结果收费。")).toBeTruthy();
    const funnelStrip = document.querySelector(".weekly-funnel-strip");
    expect(funnelStrip?.textContent ?? "").not.toContain("8.6Greg");
    expect(funnelStrip?.textContent ?? "").toContain("8.6");

    const jumpIntelBtn = screen.getByRole("button", { name: "查看本专题验证洞察 (2)" });
    fireEvent.click(jumpIntelBtn);

    // 2) Lands on #Intelligence pre-filtered to "topic:solo-biz" with localized Chinese Claim badges!
    await waitFor(() => expect(location.hash).toBe("#Intelligence"));
    const intelTopicSelect = (await screen.findByLabelText("按专题筛选洞察")) as HTMLSelectElement;
    expect(intelTopicSelect.value).toBe("topic:solo-biz");
    expect(
      screen.getByRole("heading", { name: "垂直工作流按交付结果定价留存率翻倍" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "端侧小模型推理延迟已可支撑实时语音代理" }),
    ).toBeNull();

    // Verify Chinese Claim localization (no raw English "Supported statement" or "Fact")
    expect(screen.getByText("有证据支撑的陈述")).toBeTruthy();
    expect(screen.getByText("事实")).toBeTruthy();
    expect(screen.queryByText("Supported statement")).toBeNull();

    // Reset Topic filter to ALL -> verify "Local library" source pill is localized to "本地资料库 (1)" and "RUMOR" -> "待核实传闻"
    fireEvent.change(intelTopicSelect, { target: { value: "ALL" } });
    expect(screen.getByText("待核实传闻")).toBeTruthy();
    const localPill = screen.getByRole("button", { name: "本地资料库 (1)" });
    expect(screen.queryByRole("button", { name: "Local library (1)" })).toBeNull();
    fireEvent.click(localPill);
    expect(
      screen.getByRole("heading", { name: "端侧小模型推理延迟已可支撑实时语音代理" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "垂直工作流按交付结果定价留存率翻倍" }),
    ).toBeNull();

    // 3) Reset source filter, open Content detail from first card, and click "复制纯文本摘要"
    fireEvent.click(screen.getByRole("button", { name: "全部 (4)" }));
    const detailsToggle = screen.getAllByText("证据与原始来源")[0];
    fireEvent.click(detailsToggle);
    fireEvent.click(screen.getAllByRole("button", { name: "打开内容" })[0]);

    const copyPlainSummaryBtn = await screen.findByRole("button", { name: "复制纯文本摘要" });
    fireEvent.click(copyPlainSummaryBtn);
    await waitFor(() => expect(copiedTexts).toHaveLength(1));
    expect(copiedTexts[0]).toContain("【视频深度摘要】《Outcome Pricing Playbook》");
    expect(copiedTexts[0]).toContain("Greg Isenberg");
    expect(copiedTexts[0]).toContain("9.2/10");
    expect(copiedTexts[0]).toContain("告别按席位收费：垂直 AI 工作流按业务结果定价留存率翻倍");
    expect(copiedTexts[0]).toContain("内置可审计 ROI 看板展示每周自动处理单量");
    expect(copiedTexts[0]).toContain("采用基础年费加超额结果分成混合订阅");
    expect(copiedTexts[0]).toContain("https://www.youtube.com/watch?v=vid-biz-1");
    expect(copiedTexts[0]).not.toContain("---");
    expect(copiedTexts[0]).not.toContain("[[");
  });
});
