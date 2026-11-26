import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CreatorFollowingDetail } from "./CreatorFollowing";
import { UiLanguageProvider } from "./uiLanguage";
import { WorkspaceAiResearchPanel } from "./WorkspaceAiWidgets";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

test("CreatorFollowingDetail closes on Escape and pairs each dt/dd inside div", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const onClose = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => ({
        source: {
          provider: "YOUTUBE",
          source_id: "youtube-channel-test",
          display_name: "Atlas Agent Lab (Demo)",
          canonical_url: "https://www.youtube.com/@atlas",
          enabled: true,
          last_checked_at: null,
          last_success_at: null,
          tracking: {
            health: "HEALTHY",
            coverage: "COMPLETE",
            update_count: 2,
            pending_count: 0,
            unavailable_count: 0,
          },
        },
        recent_videos: [{ video_id: "vid1", title: "Demo Video", processing_status: "COMPLETE" }],
        source_runs: [],
      }),
    })),
  );

  render(
    <UiLanguageProvider>
      <CreatorFollowingDetail
        id="youtube-channel-test"
        capability={{ known: true, capability: { available: true, code: "AVAILABLE" } }}
        onClose={onClose}
        onRefresh={() => {}}
      />
    </UiLanguageProvider>,
  );

  const label = await screen.findByText("来源状态");
  expect(label.parentElement?.tagName).toBe("DIV");
  expect(label.nextElementSibling?.tagName).toBe("DD");

  fireEvent.keyDown(window, { key: "Escape" });
  expect(onClose).toHaveBeenCalledTimes(1);
});

test("WorkspaceAiResearchPanel shows 1-click all-sources recovery CTA on scoped refusal", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const askPayloads: Array<Record<string, unknown>> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options?: RequestInit) => {
      if (url.includes("/workspace-ai/research/sessions")) {
        return {
          ok: true,
          json: async () => ({
            sessions: [],
            suggested_questions: [],
            scope_options: {
              channels: [{ key: "Atlas Agent Lab (Demo)", label: "Atlas Agent Lab (Demo)", count: 2 }],
              topic_clusters: [{ name: "AI Agent 工程架构", count: 2 }],
              videos: [
                { video_id: "vid1", title: "Agent Video", channel_name: "Atlas Agent Lab (Demo)" },
                { video_id: "vid2", title: "Solo Video", channel_name: "Local-First Foundry (Demo)" },
              ],
              starred_count: 0,
            },
          }),
        };
      }
      if (url.includes("/workspace-ai/research/ask")) {
        const payload = JSON.parse(String(options?.body ?? "{}")) as Record<string, unknown>;
        askPayloads.push(payload);
        const isScoped = Boolean(payload.channel_key);
        return {
          ok: true,
          json: async () => ({
            session: {
              session_id: isScoped ? "sess-refused" : "sess-all",
              question: payload.question,
              scope_label_zh: isScoped ? "来源「Atlas Agent Lab (Demo)」" : "全部可核验来源",
              answer_zh: isScoped
                ? "【离线合成样例回放 · 证据不足拒答】未找到直接支撑。"
                : "【离线合成样例回放】通过本机免费 Ollama 实现零边际成本冷启动 [E1]。",
              key_takeaways_zh: isScoped ? [] : ["本机 Ollama 零边际成本启动 [E1]"],
              action_items_zh: [],
              citations: isScoped
                ? []
                : [
                    {
                      ref_label: "E1",
                      evidence_id: "ev-1",
                      video_id: "vid2",
                      video_title: "Solo Video",
                      timestamp_label: "00:00",
                      excerpt: "Zero-marginal-cost onboarding starts by supporting free local Ollama.",
                      verified: true,
                    },
                  ],
              related_excerpts: [],
              covered_sources: [],
              answer_status: isScoped ? "REFUSED_INSUFFICIENT_EVIDENCE" : "ANSWERED",
              refused: isScoped,
              source_integrity_status: isScoped ? "REFUSED" : "VERIFIED",
              fact_verification_state: isScoped ? "NO_VERIFIED_CITATIONS" : "SUPPORTED",
              provider: "demo-replay",
              created_at: "2026-11-26T12:00:00Z",
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(
    <UiLanguageProvider>
      <WorkspaceAiResearchPanel onOpen={() => {}} />
    </UiLanguageProvider>,
  );

  const channelBtn = await screen.findByRole("button", { name: /^Atlas Agent Lab \(Demo\)/ });
  fireEvent.click(channelBtn);

  const input = screen.getByLabelText("跨视频提问");
  fireEvent.change(input, { target: { value: "本地优先 AI 工具如何兼顾零边际成本和可信引用？" } });
  fireEvent.click(screen.getByRole("button", { name: "AI 提问" }));

  const expandBtn = await screen.findByRole("button", { name: "扩大到全部来源重新提问" });
  expect(askPayloads[0]).toEqual({
    question: "本地优先 AI 工具如何兼顾零边际成本和可信引用？",
    channel_key: "Atlas Agent Lab (Demo)",
  });

  fireEvent.click(expandBtn);
  await waitFor(() => expect(askPayloads.length).toBe(2));
  expect(askPayloads[1]).toEqual({
    question: "本地优先 AI 工具如何兼顾零边际成本和可信引用？",
  });
  expect(await screen.findByText(/通过本机免费 Ollama 实现零边际成本冷启动/)).toBeTruthy();
});
