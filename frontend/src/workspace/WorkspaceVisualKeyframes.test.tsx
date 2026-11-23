import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { UiLanguageProvider } from "./uiLanguage";
import { VideoVisualAnalysis, WorkspaceVisualKeyframePanel } from "./WorkspaceAiWidgets";

function makeVisualAnalysis(withSpeakerFrame = true): VideoVisualAnalysis {
  return {
    video_id: "vidLocalMp4",
    visual_summary_zh: "结合 PPT 架构图与折线图梳理关键帧成本与召回收益。",
    visual_takeaways_zh: [
      "三层抽帧与 dHash 去重将重复幻灯片控制在极低体积。",
      "图表显示 960px JPEG 兼顾文字清晰度与视觉 Token 开销。",
    ],
    frame_count: withSpeakerFrame ? 3 : 2,
    informative_frame_count: 2,
    provider: "ollama",
    model: "gemma3:4b",
    updated_at: "2026-11-23T14:00:00Z",
    frames: [
      {
        frame_index: 1,
        frame_id: "f01-00000100",
        filename: "frame_01_00000100.jpg",
        timestamp_ms: 100,
        timestamp_label: "00:00",
        selection_reason: "OPENING",
        frame_kind: "ARCHITECTURE",
        has_visual_info: true,
        title_zh: "系统三层多模态架构总图",
        visual_detail_zh: "展示本地 ffmpeg 抽帧、dHash 去重与预算闸门模块。",
        transcript_fusion_zh: "开篇讲解为何仅对单视频按需开启视觉分析。",
        nearby_transcript: "我们先看整体架构图，先抽帧再去重。",
        image_url: "/api/v1/workspace-ai/videos/vidLocalMp4/keyframes/f01-00000100.jpg",
        image_available: true,
      },
      ...(withSpeakerFrame
        ? [
            {
              frame_index: 2,
              frame_id: "f02-00002000",
              filename: "frame_02_00002000.jpg",
              timestamp_ms: 2000,
              timestamp_label: "00:02",
              selection_reason: "UNIFORM",
              frame_kind: "SPEAKER",
              has_visual_info: false,
              title_zh: "讲者口述过渡镜头",
              visual_detail_zh: "仅见主讲人镜头，无新增 PPT 文字。",
              transcript_fusion_zh: "讲者过渡下一部分性能测试数据。",
              nearby_transcript: "接下来看延迟实测对比。",
              image_url: "/api/v1/workspace-ai/videos/vidLocalMp4/keyframes/f02-00002000.jpg",
              image_available: true,
            },
          ]
        : []),
      {
        frame_index: withSpeakerFrame ? 3 : 2,
        frame_id: "f03-00004500",
        filename: "frame_03_00004500.jpg",
        timestamp_ms: 4500,
        timestamp_label: "00:05",
        selection_reason: "SCENE_CHANGE",
        frame_kind: "CHART",
        has_visual_info: true,
        title_zh: "抽帧规模与延迟对比柱状图",
        visual_detail_zh: "显示 8 帧去重方案延迟压降至 2 秒左右。",
        transcript_fusion_zh: "原话补充说明超过 12 帧后边际收益递减。",
        nearby_transcript: "去重后控制到 8 帧以内性价比最高。",
        image_url: "/api/v1/workspace-ai/videos/vidLocalMp4/keyframes/f03-00004500.jpg",
        image_available: true,
      },
    ],
  };
}

describe("WorkspaceVisualKeyframePanel", () => {
  beforeEach(() => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  test("hides visual keyframe panel for non-local-video content and disables CTA when ffmpeg missing", () => {
    const { container } = render(
      <UiLanguageProvider>
        <WorkspaceVisualKeyframePanel
          videoId="vidYT123456"
          isLocalVideo={false}
          ffmpegAvailable={true}
          visualAnalysis={null}
          onCompleted={vi.fn()}
        />
      </UiLanguageProvider>,
    );
    expect(container.firstChild).toBeNull();

    render(
      <UiLanguageProvider>
        <WorkspaceVisualKeyframePanel
          videoId="vidLocalMp4"
          isLocalVideo={true}
          ffmpegAvailable={false}
          visualAnalysis={null}
          onCompleted={vi.fn()}
        />
      </UiLanguageProvider>,
    );
    const btn = screen.getByRole("button", { name: "结合画面分析关键帧" });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/未检测到本机 ffmpeg/)).toBeTruthy();
  });

  test("triggers on-demand keyframe analysis, filters speaker frames, opens accessible Lightbox, and links zip pack", async () => {
    const analysis = makeVisualAnalysis(true);
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ video_id: "vidLocalMp4", analysis }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onCompleted = vi.fn();

    render(
      <UiLanguageProvider>
        <WorkspaceVisualKeyframePanel
          videoId="vidLocalMp4"
          isLocalVideo={true}
          ffmpegAvailable={true}
          visualAnalysis={null}
          onCompleted={onCompleted}
        />
      </UiLanguageProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "结合画面分析关键帧" }));

    await waitFor(() => {
      expect(screen.getByText("系统三层多模态架构总图")).toBeTruthy();
    });
    expect(onCompleted).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/workspace-ai/videos/vidLocalMp4/visual-analysis",
      expect.objectContaining({ method: "POST" }),
    );

    const zipLink = screen.getByRole("link", { name: "下载带图笔记包 (.zip)" });
    expect(zipLink.getAttribute("href")).toBe(
      "/api/v1/workspace-ai/videos/vidLocalMp4/visual-pack.zip",
    );

    // Filter out speaker-only frames
    const filterBtn = screen.getByRole("button", { name: "仅看含 PPT/图表帧" });
    fireEvent.click(filterBtn);
    expect(screen.queryByText("讲者口述过渡镜头")).toBeNull();
    expect(screen.getByText("抽帧规模与延迟对比柱状图")).toBeTruthy();

    // Open Lightbox on first visible card, navigate with ArrowRight, close with Escape
    fireEvent.click(screen.getByRole("button", { name: /系统三层多模态架构总图/ }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("[00:00] 系统三层多模态架构总图")).toBeTruthy();
    expect(within(dialog).getByText("1 / 2")).toBeTruthy();

    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(within(dialog).getByText("[00:05] 抽帧规模与延迟对比柱状图")).toBeTruthy();
    expect(within(dialog).getByText("2 / 2")).toBeTruthy();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("renders actionable recovery alerts for LOCAL_VISION_MODEL_UNSUPPORTED and CLOUD_DAILY_BUDGET_EXCEEDED", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({
          error: {
            code: "LOCAL_VISION_MODEL_UNSUPPORTED",
            message: "当前模型 qwen3:8b 暂不支持视觉输入，请改用 gemma3:4b。",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({
          error: {
            code: "CLOUD_DAILY_BUDGET_EXCEEDED",
            message: "已达到今日云端调用上限，已阻断请求。",
          },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <UiLanguageProvider>
        <WorkspaceVisualKeyframePanel
          videoId="vidLocalMp4"
          isLocalVideo={true}
          ffmpegAvailable={true}
          visualAnalysis={null}
          onCompleted={vi.fn()}
        />
      </UiLanguageProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "结合画面分析关键帧" }));
    const alert1 = await screen.findByRole("alert");
    expect(within(alert1).getByText(/gemma3:4b/)).toBeTruthy();
    expect(within(alert1).getByRole("link").getAttribute("href")).toBe("#Settings");

    fireEvent.click(screen.getByRole("button", { name: "结合画面分析关键帧" }));
    const alert2 = await screen.findByRole("alert");
    expect(within(alert2).getByText(/今日云端调用上限/)).toBeTruthy();
    expect(within(alert2).getByRole("link").getAttribute("href")).toBe("#Settings");
  });
});
