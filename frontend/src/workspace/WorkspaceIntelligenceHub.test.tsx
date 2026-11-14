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
              work_kind: "PENDING_CONTENT_WORK",
              channel_id: "UC1111111111111111111111",
              channel_name: "OpenAI",
              title: "Queued Source Run Placeholder",
              published_at: "2026-11-14T09:00:00Z",
              processing_status: "WAITING",
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
});
