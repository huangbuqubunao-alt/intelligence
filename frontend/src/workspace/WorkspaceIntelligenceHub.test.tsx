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
});
