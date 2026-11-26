import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App } from "./App";
import { ReaderMediaStage } from "./ReaderMediaStage";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("ReaderMediaStage renders Editorial Source Card when heroPosterUrl is null and preserves image poster when present", () => {
  const onInspect = vi.fn();
  const { rerender } = render(
    <ReaderMediaStage
      zhReader={true}
      provider="YOUTUBE"
      channelName="Atlas Agent Lab"
      title="Deterministic State Machines"
      sourceUrl="https://www.youtube.com/watch?v=vid-1"
      durationSeconds={1200}
      heroPosterUrl={null}
      isLocalMedia={false}
      isBilibili={false}
      isPlayableLocalVideo={false}
      isPlayableLocalAudio={false}
      localMediaSrc=""
      playing={false}
      mediaErrorCode={null}
      onPlayStart={vi.fn()}
      onHidePlayer={vi.fn()}
      onMediaError={vi.fn()}
      onRetryMedia={vi.fn()}
      evidenceCount={9}
      transcriptAvailable={true}
      onOpenEvidenceDrawer={onInspect}
    />,
  );

  expect(document.querySelector(".reader-media-poster.is-editorial-card")).toBeTruthy();
  expect(screen.getByText("已保存可核验原文 · 9 条原话证据")).toBeTruthy();
  const inspectBtn = screen.getByRole("button", { name: "核对原话证据" });
  fireEvent.click(inspectBtn);
  expect(onInspect).toHaveBeenCalledOnce();

  rerender(
    <ReaderMediaStage
      zhReader={true}
      provider="LOCAL"
      channelName="Local"
      title="Architecture Video"
      sourceUrl={null}
      durationSeconds={600}
      heroPosterUrl="/api/v1/frames/f1.jpg"
      isLocalMedia={true}
      isBilibili={false}
      isPlayableLocalVideo={true}
      isPlayableLocalAudio={false}
      localMediaSrc="/api/v1/videos/vid-2/media"
      playing={false}
      mediaErrorCode={null}
      onPlayStart={vi.fn()}
      onHidePlayer={vi.fn()}
      onMediaError={vi.fn()}
      onRetryMedia={vi.fn()}
      evidenceCount={3}
      transcriptAvailable={true}
      onOpenEvidenceDrawer={onInspect}
    />,
  );
  expect(document.querySelector(".reader-media-poster.is-editorial-card")).toBeNull();
  expect(document.querySelector("img.reader-media-poster-img")).toBeTruthy();
});

test("Content Reader Evidence drawer copies verbatim source excerpt with locator and closes cleanly on Escape", async () => {
  location.hash = "#Content/vid-iter9";
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/v1/videos" || url.startsWith("/api/v1/videos?")) {
        return {
          ok: true,
          json: async () => ({
            videos: [
              {
                video_id: "vid-iter9",
                provider: "YOUTUBE",
                channel_name: "Atlas Lab",
                title: "Production Agents Talk",
                processing_status: "READY",
                duration_seconds: 1200,
              },
            ],
          }),
        };
      }
      if (url === "/api/v1/videos/vid-iter9") {
        return {
          ok: true,
          json: async () => ({
            video: {
              video_id: "vid-iter9",
              provider: "YOUTUBE",
              channel_name: "Atlas Lab",
              title: "Production Agents Talk",
              source_url: "https://www.youtube.com/watch?v=vid-iter9",
              processing_status: "READY",
              media_kind: "VIDEO",
              format: "mp4",
              source_language: "en",
              duration_seconds: 1200,
            },
            transcript: { status: "AVAILABLE", text: "Production agents require deterministic checkpoints." },
            note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
            intelligence_result: { status: "NOT_PROCESSED" },
            history: [],
          }),
        };
      }
      if (url.endsWith("/evidence")) {
        return {
          ok: true,
          json: async () => ({
            evidence: [
              {
                evidence_id: "ev-iter9-1",
                artifact_id: "art-1",
                video_id: "vid-iter9",
                locator_type: "TIME_RANGE",
                start_ms: 0,
                end_ms: 42000,
                source_language: "en",
                translation_target_language: "zh-CN",
                original_excerpt: "Every external tool call needs bounded schemas and SQLite checkpoints.",
                lineage_kind: "NATIVE_CAPTIONS",
                role: "PRIMARY",
              },
            ],
          }),
        };
      }
      if (url.endsWith("/deep-analysis")) {
        return {
          ok: true,
          json: async () => ({
            deep_analysis: {
              status: {
                availability: "NOT_QUALIFIED",
                reason_code: "NO_QUALIFIED_MODEL",
                qualified: false,
                production_eligible: false,
                consent_required: false,
                routes: [],
              },
              result: null,
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  const inspectBtn = await screen.findByRole("button", { name: "核对原话证据" });
  fireEvent.click(inspectBtn);

  const drawer = await screen.findByRole("dialog", { name: "原文与溯源资料" });
  const copyBtn = within(drawer).getByRole("button", { name: /复制引用：/ });
  fireEvent.click(copyBtn);

  expect(writeText).toHaveBeenCalledOnce();
  expect(writeText.mock.calls[0][0]).toContain(
    "Every external tool call needs bounded schemas and SQLite checkpoints.",
  );
  expect(writeText.mock.calls[0][0]).toContain("《Production Agents Talk》");
  expect(writeText.mock.calls[0][0]).toContain("[0:00–0:42]");

  await waitFor(() => {
    expect(within(drawer).getByText("已复制")).toBeTruthy();
  });

  fireEvent.keyDown(window, { key: "Escape" });
  await waitFor(() => {
    expect(screen.queryByRole("dialog", { name: "原文与溯源资料" })).toBeNull();
  });
});
