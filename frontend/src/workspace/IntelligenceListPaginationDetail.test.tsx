import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function buildIntelFixture(index: number) {
  const num = index + 1;
  const isOpenAi = index % 2 === 0;
  return {
    status: "AVAILABLE",
    trusted: true,
    intelligence_id: `intel-item-${num}`,
    claim_kind: "SUPPORTED_STATEMENT",
    state: "CONFIRMED",
    linked_topics: [
      isOpenAi
        ? { topic_id: "topic:agent-arch", name: "AI Agent 与自动化架构" }
        : { topic_id: "topic:solo-biz", name: "AI 产品机会与一人公司变现" },
    ],
    card: {
      core_conclusion: `第 ${num} 条核心洞察结论：高密度列表架构验证`,
      user_relevant_information: [
        `第 ${num} 条精华提要：用一行关键看点帮助快速判断是否值得深读。`,
      ],
      important_new_information: [`第 ${num} 条新增信息长段落详情正文。`],
      meaningful_details: [`第 ${num} 条关键细节条目 A`, `第 ${num} 条关键细节条目 B`],
      source_id: isOpenAi ? "src-openai" : "src-greg",
      source_display_name: isOpenAi ? "OpenAI" : "Greg Isenberg",
      source_url: isOpenAi ? "https://www.youtube.com/@OpenAI" : "https://www.youtube.com/@GregIsenberg",
      video_id: `vid-${num}`,
      video_title: `Source Video ${num}`,
      original_video_url: `https://www.youtube.com/watch?v=vid-${num}`,
      evidence_links: [
        {
          evidence_id: `ev-${num}-1`,
          artifact_id: `art-${num}`,
          start_ms: 12000,
          end_ms: 28000,
          locator_type: "TIMED_MEDIA",
          language: "en",
          lineage_kind: "TRANSCRIPT",
          role: "PRIMARY",
          original_excerpt: `Original quote for insight ${num}.`,
          translated_excerpt: `第 ${num} 条原片双语证据译文摘录。`,
          translated_language: "zh-CN",
          translation_target_language: "zh-CN",
          stance: "supporting",
        },
        {
          evidence_id: `ev-${num}-2`,
          artifact_id: `art-${num}`,
          start_ms: 45000,
          end_ms: 60000,
          locator_type: "TIMED_MEDIA",
          language: "en",
          lineage_kind: "TRANSCRIPT",
          role: "SUPPORTING",
          original_excerpt: `Second quote for insight ${num}.`,
          translated_excerpt: `第 ${num} 条第二处原片证据译文。`,
          translated_language: "zh-CN",
          translation_target_language: "zh-CN",
          stance: "supporting",
        },
      ],
    },
  };
}

describe("Intelligence L1 compact list, pagination, and Plan A L2 detail view", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Intelligence";
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders compact 4-field L1 rows without bloated L2 sections, paginates 10 per page, supports quick Save without opening detail, and resets page on filter change", async () => {
    const items = Array.from({ length: 25 }, (_, i) => buildIntelFixture(i));
    const savedIds = new Set<string>();

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/saved-intelligence/save") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as { intelligence_id: string };
        savedIds.add(body.intelligence_id);
        return okJson({ saved: true });
      }
      if (input.endsWith("/saved-intelligence/unsave") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as { intelligence_id: string };
        savedIds.delete(body.intelligence_id);
        return okJson({ saved: false });
      }
      if (input.endsWith("/intelligence")) {
        return okJson({ intelligence: items, activity: [] });
      }
      if (input.endsWith("/saved-intelligence")) {
        return okJson({
          saved: items
            .filter((it) => savedIds.has(it.intelligence_id))
            .map((it) => ({
              intelligence_id: it.intelligence_id,
              saved_at: "2026-11-17T10:00:00Z",
              intelligence: it,
            })),
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    // Page 1 shows items 1..10 ONLY, not item 11..25
    expect(
      await screen.findByRole("heading", { name: "第 1 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "第 10 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "第 11 条核心洞察结论：高密度列表架构验证" }),
    ).toBeNull();

    // L1 shows the 4 essential elements: conclusion, 1-line summary, provenance/topic/evidence count, and quick Save
    expect(
      screen.getByText("第 1 条精华提要：用一行关键看点帮助快速判断是否值得深读。"),
    ).toBeTruthy();
    expect(screen.getAllByText("2 处原片证据").length).toBe(10);

    // L1 MUST NOT render bloated L2 sections inline
    expect(screen.queryByText("为何重要")).toBeNull();
    expect(screen.queryByText("新增信息")).toBeNull();
    expect(screen.queryByText("重要细节")).toBeNull();
    expect(screen.queryByText("证据与原始来源")).toBeNull();
    expect(screen.queryByText("第 1 条新增信息长段落详情正文。")).toBeNull();

    // Quick Save on item 1 stays on L1 list and does NOT open L2 detail
    const firstRow = screen
      .getByRole("heading", { name: "第 1 条核心洞察结论：高密度列表架构验证" })
      .closest("article")!;
    fireEvent.click(within(firstRow).getByRole("button", { name: "收藏" }));
    await waitFor(() =>
      expect(within(firstRow).getByRole("button", { name: "取消收藏" })).toBeTruthy(),
    );
    expect(screen.queryByText("新增信息")).toBeNull();

    // Pagination bar shows Page 1 of 3 (25 items) and navigates to Page 2
    const pagination = screen.getByRole("navigation", { name: "洞察分页导航" });
    expect(pagination.textContent).toContain("第 1 / 3 页");
    expect(pagination.textContent).toContain("共 25 条");

    fireEvent.click(within(pagination).getByRole("button", { name: "下一页" }));
    expect(
      await screen.findByRole("heading", { name: "第 11 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "第 1 条核心洞察结论：高密度列表架构验证" }),
    ).toBeNull();
    expect(pagination.textContent).toContain("第 2 / 3 页");

    // Filtering by source while on Page 2 automatically resets pagination back to Page 1
    const sourceGroup = screen.getByRole("group", { name: "按来源筛选洞察" });
    fireEvent.click(within(sourceGroup).getByRole("button", { name: "OpenAI (13)" }));
    expect(pagination.textContent).toContain("第 1 / 2 页");
    expect(pagination.textContent).toContain("共 13 条");
    expect(
      screen.getByRole("heading", { name: "第 1 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
  });

  it("opens Plan A standalone L2 detail view, steps Prev/Next across page boundaries, and returns to exact L1 page and filter state (including Saved tab)", async () => {
    const items = Array.from({ length: 25 }, (_, i) => buildIntelFixture(i));
    const savedItems = items.slice(0, 12).map((it) => ({
      intelligence_id: it.intelligence_id,
      saved_at: "2026-11-17T10:00:00Z",
      intelligence: it,
    }));

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/intelligence")) {
          return okJson({ intelligence: items, activity: [] });
        }
        if (input.endsWith("/saved-intelligence")) {
          return okJson({ saved: savedItems });
        }
        return okJson({});
      }),
    );

    render(<App />);
    expect(
      await screen.findByRole("heading", { name: "第 1 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();

    // Go to Page 2 and open item #12 into Plan A Detail View
    const pagination = screen.getByRole("navigation", { name: "洞察分页导航" });
    fireEvent.click(within(pagination).getByRole("button", { name: "第 2 页" }));
    expect(
      await screen.findByRole("heading", { name: "第 12 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();

    fireEvent.click(
      screen.getByRole("button", { name: "第 12 条核心洞察结论：高密度列表架构验证" }),
    );

    // L2 Detail View displays full card sections + back button with Page 2 memory + Prev/Next stepper
    expect(await screen.findByText("为何重要")).toBeTruthy();
    expect(screen.getByText("新增信息")).toBeTruthy();
    expect(screen.getByText("第 12 条新增信息长段落详情正文。")).toBeTruthy();
    expect(screen.getByText("重要细节")).toBeTruthy();
    expect(screen.getByText("证据与原始来源")).toBeTruthy();
    expect(screen.getByRole("button", { name: "返回洞察列表（第 2 页）" })).toBeTruthy();

    const stepper = screen.getByRole("group", { name: "切换相邻洞察" });
    expect(stepper.textContent).toContain("第 12 / 25 条");

    // Step Previous twice: #12 -> #11 -> #10 (crosses boundary to Page 1!)
    fireEvent.click(within(stepper).getByRole("button", { name: "上一条" }));
    expect(stepper.textContent).toContain("第 11 / 25 条");
    fireEvent.click(within(stepper).getByRole("button", { name: "上一条" }));
    expect(stepper.textContent).toContain("第 10 / 25 条");
    expect(screen.getByRole("button", { name: "返回洞察列表（第 1 页）" })).toBeTruthy();

    // Step Next back to #11 (Page 2) and click Back -> lands right on Page 2!
    fireEvent.click(within(stepper).getByRole("button", { name: "下一条" }));
    expect(stepper.textContent).toContain("第 11 / 25 条");
    fireEvent.click(screen.getByRole("button", { name: "返回洞察列表（第 2 页）" }));

    expect(
      await screen.findByRole("heading", { name: "第 11 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "第 1 条核心洞察结论：高密度列表架构验证" }),
    ).toBeNull();
    expect(screen.queryByText("新增信息")).toBeNull();

    // Switch to "已收藏" (Saved) tab -> also uses compact list + 10-per-page pagination + Plan A Detail View
    fireEvent.click(screen.getByRole("button", { name: "已收藏" }));
    const savedPagination = await screen.findByRole("navigation", { name: "洞察分页导航" });
    expect(savedPagination.textContent).toContain("第 1 / 2 页");
    expect(savedPagination.textContent).toContain("共 12 条");
    expect(screen.queryByText("新增信息")).toBeNull();

    fireEvent.click(within(savedPagination).getByRole("button", { name: "下一页" }));
    expect(
      await screen.findByRole("heading", { name: "第 12 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "查看详情：第 12 条核心洞察结论：高密度列表架构验证" }),
    );
    expect(await screen.findByText("第 12 条新增信息长段落详情正文。")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "返回洞察列表（第 2 页）" }));
    expect(
      await screen.findByRole("heading", { name: "第 12 条核心洞察结论：高密度列表架构验证" }),
    ).toBeTruthy();
  });
});
