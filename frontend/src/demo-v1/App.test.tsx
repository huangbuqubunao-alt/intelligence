import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { DemoApp } from "./App";
import { assertFixtureRelationships, buildSearchIndex, followings, searchIndexMatches } from "./fixtures";

beforeEach(() => { window.location.hash = ""; });
afterEach(() => vi.unstubAllGlobals());

test("fixture graph keeps every cross-source relationship resolvable", () => {
  expect(assertFixtureRelationships()).toEqual([]);
});

test("pre-freeze fixture models a realistic Following library", () => {
  expect(followings).toHaveLength(18);
  expect(Object.fromEntries(["YouTube", "B站", "X", "Local"].map(provider => [provider, followings.filter(item => item.provider === provider).length]))).toEqual({
    YouTube: 7,
    B站: 4,
    X: 3,
    Local: 4,
  });
  expect(new Set(followings.map(item => item.group))).toEqual(new Set(["AI 模型", "AI Agent", "产品与商业", "学习", "个人收藏"]));
  expect(followings.every(item => item.focus.length > 0)).toBe(true);
  expect(assertFixtureRelationships()).toEqual([]);
});

test("pre-freeze path A keeps 18 Followings findable by group, filter and search", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  expect(screen.getByText("18 个关注对象")).toBeTruthy();
  expect(screen.getAllByRole("button", { name: /^查看关注：/ })).toHaveLength(18);
  for (const label of ["有更新", "产生新洞察", "需要处理", "已暂停"]) expect(screen.getByRole("button", { name: label })).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "产生新洞察" }));
  expect(screen.getByText("4 个关注对象")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "筛选：全部" }));

  fireEvent.click(screen.getByRole("button", { name: "AI Agent" }));
  expect(screen.getByText("5 个关注对象")).toBeTruthy();
  expect(screen.getByRole("button", { name: "查看关注：AI Explained" })).toBeTruthy();

  fireEvent.change(screen.getByLabelText("搜索关注对象"), { target: { value: "AI Explained" } });
  expect(screen.getAllByRole("button", { name: /^查看关注：/ })).toHaveLength(1);

  fireEvent.change(screen.getByLabelText("搜索关注对象"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: /^全部$/ }));
  fireEvent.click(screen.getByRole("button", { name: "已暂停" }));
  expect(screen.getByText("2 个关注对象")).toBeTruthy();
});

test("pre-freeze path B explains Following Focus and supports a per-Following override", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  fireEvent.click(screen.getByRole("button", { name: "查看关注：AI Explained" }));
  expect(screen.getByRole("heading", { name: "关注重点" })).toBeTruthy();
  expect(screen.getByText(/关注重点决定哪些内容值得处理；Topic 是长期形成的知识认知/)).toBeTruthy();
  expect((screen.getByLabelText("使用我的默认设置") as HTMLInputElement).checked).toBe(true);

  fireEvent.click(screen.getByLabelText("为这个关注单独设置"));
  expect((screen.getByLabelText("Agent") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("Benchmark") as HTMLInputElement).checked).toBe(true);
  fireEvent.click(screen.getByLabelText("技术实现"));
  expect((screen.getByLabelText("技术实现") as HTMLInputElement).checked).toBe(true);
  expect(screen.getByRole("heading", { name: "内容处理" })).toBeTruthy();
  expect((screen.getByLabelText("生成摘要") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("提取值得关注的洞察") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("自动关联主题") as HTMLInputElement).checked).toBe(true);
});

test("pre-freeze path C presents a video note before Evidence and makes chapters actionable", () => {
  window.location.hash = "#content-youtube-task-ui";
  render(<DemoApp initialExperience="workspace" />);
  expect(screen.getByRole("heading", { name: "视频摘要" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "核心要点" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "时间戳章节" })).toBeTruthy();
  expect(screen.getAllByRole("listitem")).toHaveLength(6);
  fireEvent.click(screen.getByRole("button", { name: "跳到 08:14：界面从聊天转向任务" }));
  expect(screen.getByText("已定位到 08:14 · 界面从聊天转向任务（Demo）")).toBeTruthy();
  expect(screen.getAllByText(/Evidence E1/).length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: "由该内容参与形成的 Intelligence" })).toBeTruthy();
  expect(screen.getByText(/Summary 回答“这个内容讲了什么”/)).toBeTruthy();
});

test("pre-freeze path D treats a complete summary without Intelligence as a normal result", async () => {
  window.location.hash = "#content-practical-ai";
  render(<DemoApp initialExperience="workspace" />);
  expect(screen.getByRole("heading", { name: "视频摘要" })).toBeTruthy();
  expect(screen.getByText("未发现值得长期保留的新洞察")).toBeTruthy();
  expect(screen.getByText(/摘要已成功生成，这不是处理失败/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "生成详细摘要（Demo）" }));
  expect(await screen.findByText("详细摘要已生成（Demo）")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "查看参与形成的洞察" })).toBeNull();
});

test("pre-freeze path E keeps multiple Evidence separate from one cross-source Intelligence", () => {
  window.location.hash = "#content-youtube-pricing";
  render(<DemoApp initialExperience="workspace" />);
  expect(screen.getByText("Evidence E5 · 12:40")).toBeTruthy();
  expect(screen.getByText("Evidence E8 · 18:05")).toBeTruthy();
  expect(screen.getByText("这条视频贡献 2 条 Evidence，并参与 1 条跨来源 Intelligence。")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "查看参与形成的洞察" }));
  expect(screen.getByRole("heading", { name: /Outcome-based pricing 正在成为/ })).toBeTruthy();
});

test("primary navigation and welcome position Intelligence as a multi-source product", () => {
  const { unmount } = render(<DemoApp initialExperience="onboarding" />);
  expect(screen.getByRole("heading", { name: /关注的信息.*可追溯的洞察/ })).toBeTruthy();
  expect(screen.getByText(/视频、帖子与本地内容/)).toBeTruthy();
  unmount();
  render(<DemoApp initialExperience="workspace" />);
  const nav = screen.getByRole("navigation", { name: "主导航" });
  expect(within(nav).getAllByRole("button").map(item => item.textContent)).toEqual(["首页", "关注", "洞察", "主题", "调研", "设置"]);
  expect(screen.getByText("Intelligence", { selector: ".brand-wordmark" })).toBeTruthy();
});

test("revision 3 path A keeps first-run model strategy simple and reaches Home without network", async () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  render(<DemoApp initialExperience="onboarding" />);
  fireEvent.click(screen.getByRole("button", { name: "开始设置" }));
  expect((screen.getByLabelText("自动配置") as HTMLInputElement).checked).toBe(true);
  expect(screen.getByText(/根据任务复杂度、成本和可用能力自动选择/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "继续添加关注" }));
  fireEvent.change(screen.getByLabelText("YouTube URL"), { target: { value: "https://youtube.com/@aiexplained" } });
  fireEvent.click(screen.getByRole("button", { name: "测试关注" }));
  expect(await screen.findByText("找到频道：AI Explained")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "继续设置偏好" }));
  fireEvent.click(screen.getByRole("button", { name: "保存偏好并继续" }));
  expect(screen.getByRole("heading", { name: "Intelligence 已经准备好了。" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "进入首页" }));
  expect(screen.getByRole("heading", { name: /今天有 3 件事值得关注/ })).toBeTruthy();
  expect(screen.getByText(/12 个新内容，其中 9 个已生成摘要，3 条形成新 Intelligence/)).toBeTruthy();
  expect(screen.getByText(/79% 本地处理/)).toBeTruthy();
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("revision 3 path B exposes understandable model strategies and advanced task routing", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  expect((screen.getByLabelText("自动") as HTMLInputElement).checked).toBe(true);
  fireEvent.click(screen.getByLabelText("优先本地"));
  expect(screen.getByText(/本地模型能完成的任务优先留在电脑上/)).toBeTruthy();
  fireEvent.click(screen.getByLabelText("成本优先"));
  expect(screen.getAllByText(/不会让系统绕过最低质量要求/).length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "高级模型设置" }));
  expect(screen.getByRole("heading", { name: "任务与模型" })).toBeTruthy();
  expect(screen.getByText("基础处理")).toBeTruthy();
  expect(screen.getByText("Ollama · Local")).toBeTruthy();
  expect(screen.getByRole("button", { name: "恢复自动推荐" })).toBeTruthy();
  expect(screen.getByText("Deep Research 不适用")).toBeTruthy();
});

test("revision 3 path C keeps conflicting evidence and uncertainty explicit", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "洞察" }));
  fireEvent.click(screen.getByRole("button", { name: /查看洞察：Outcome-based pricing/ }));
  expect(screen.getByRole("heading", { name: /Outcome-based pricing 正在成为/ })).toBeTruthy();
  expect(screen.getByText(/当前证据存在分歧。系统保留支持与反对观点/)).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Supporting Evidence" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Contradicting Evidence" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Conditional Evidence" })).toBeTruthy();
  expect(screen.getByText("部分支持")).toBeTruthy();
  expect(screen.getByText(/Last updated/)).toBeTruthy();
});

test("revision 3 Research history compares snapshots instead of overwriting conclusions", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "调研" }));
  fireEvent.click(screen.getByRole("button", { name: "查看 Research v1" }));
  expect(screen.getByText("研究生成：2026-09-15")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "查看 v2" }));
  expect(screen.getByRole("heading", { name: "Compared with previous research" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "新增 Evidence" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "删除 / 失效 Evidence" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "判断变化" })).toBeTruthy();
});

test("golden path B follows AI Explained through content, evidence and Intelligence", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  expect(screen.getByRole("heading", { name: "Intelligence Agent 现在在帮我关注什么？" })).toBeTruthy();
  expect(screen.getAllByText("B站 · UP主").length).toBeGreaterThan(0);
  expect(screen.getAllByText("X · Account").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "查看关注：AI Explained" }));
  expect(screen.getByRole("heading", { name: "AI Explained" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(screen.getByRole("button", { name: /查看内容：从聊天助手到任务执行系统/ }));
  expect(screen.getByRole("heading", { name: "从聊天助手到任务执行系统" })).toBeTruthy();
  expect(screen.getByText("YouTube Video")).toBeTruthy();
  expect(screen.getAllByText(/Evidence E1/).length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "查看参与形成的洞察" }));
  expect(screen.getByRole("heading", { name: "Agent 产品正在从聊天界面转向任务执行界面" })).toBeTruthy();
});

test("add Following exposes Provider breadth while keeping a complete YouTube mock flow", async () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  fireEvent.click(screen.getByRole("button", { name: "+ 添加关注" }));
  for (const provider of ["YouTube", "B站", "X", "抖音", "小红书", "本地视频"]) {
    expect(screen.getByRole("button", { name: new RegExp(provider) })).toBeTruthy();
  }
  fireEvent.change(screen.getByLabelText("YouTube URL"), { target: { value: "https://youtube.com/@practicalai" } });
  fireEvent.click(screen.getByRole("button", { name: "测试关注" }));
  expect(await screen.findByText("找到频道：Practical AI Engineering")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "保存关注（Demo）" }));
  expect(screen.getByRole("heading", { name: "Practical AI Engineering" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  expect(screen.getByRole("button", { name: /查看内容：从聊天原型到任务型 Agent/ })).toBeTruthy();
});

test("golden path C exposes cross-source Evidence and opens each matching content item", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: /查看洞察：Agent 产品正在从聊天界面转向任务执行界面/ }));
  expect(screen.getAllByText("AI Explained").length).toBeGreaterThan(0);
  expect(screen.getAllByText("某 AI UP 主").length).toBeGreaterThan(0);
  expect(screen.getAllByText("@agentbuilder").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "查看证据来源：YouTube 08:14" }));
  expect(screen.getByRole("heading", { name: "从聊天助手到任务执行系统" })).toBeTruthy();
  expect(screen.getByText("定位到 08:14 · Evidence E1")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "返回洞察" }));
  fireEvent.click(screen.getByRole("button", { name: "查看证据来源：B站 05:32" }));
  expect(screen.getByRole("heading", { name: "为什么 Agent 产品开始强调完成任务" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "返回洞察" }));
  fireEvent.click(screen.getByRole("button", { name: "查看证据来源：X 原帖" }));
  expect(screen.getByRole("heading", { name: "The moat is task completion, not chat quality" })).toBeTruthy();
});

test("revision 3 paths D and E show Topic lifecycle, evolution and Research history", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: /查看洞察：Agent 产品正在从聊天界面转向任务执行界面/ }));
  fireEvent.click(screen.getByRole("button", { name: "查看主题：AI Agent 商业化" }));
  expect(screen.getByRole("heading", { name: "AI Agent 商业化" })).toBeTruthy();
  expect(screen.getByText("状态：活跃")).toBeTruthy();
  expect(screen.getByText(/稳定 → 活跃/)).toBeTruthy();
  expect(screen.getByRole("heading", { name: "主要贡献来源" })).toBeTruthy();
  expect(screen.getByText("3 个关注对象共同贡献了这个主题的当前理解。")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "知识演进" })).toBeTruthy();
  expect(screen.getAllByText(/混合收费模式正在增加/).length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: "Research History" })).toBeTruthy();
  expect(screen.getByText("v1 · 2026-09-15")).toBeTruthy();
  expect(screen.getByText("v2 · 2026-10-12")).toBeTruthy();
  expect(screen.getByRole("button", { name: "重命名主题" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "合并主题" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "归档主题" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "深入调研" }));
  expect((screen.getByLabelText("我的资料库") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("当前对象：Topic · AI Agent 商业化") as HTMLInputElement).checked).toBe(false);
  expect((screen.getByLabelText("扩展探索（后续能力）") as HTMLInputElement).disabled).toBe(true);
  fireEvent.click(screen.getByLabelText("当前对象：Topic · AI Agent 商业化"));
  expect(screen.getByText("当前范围：Topic · AI Agent 商业化")).toBeTruthy();
  fireEvent.click(screen.getByLabelText("指定范围"));
  fireEvent.change(screen.getByLabelText("范围类型"), { target: { value: "following" } });
  expect(screen.getByLabelText("选择具体范围")).toBeTruthy();
  expect(screen.getByText("指定范围：关注对象 · AI Explained")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "开始调研" }));
  expect(screen.getByRole("heading", { name: "AI Agent 商业模式正在如何变化？" })).toBeTruthy();
  expect(screen.getByText("研究范围：指定范围 · 关注对象 · AI Explained")).toBeTruthy();
});

test("golden path F opens Research from a Following with current object prefilled", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  fireEvent.click(screen.getByRole("button", { name: "查看关注：AI Explained" }));
  fireEvent.click(screen.getByRole("button", { name: "调研这个关注对象" }));
  expect((screen.getByLabelText("我的资料库") as HTMLInputElement).checked).toBe(true);
  expect(screen.getByLabelText("当前对象：关注 · AI Explained")).toBeTruthy();
});

test("revision 3 paths F and G mock safe backup restore and Obsidian publishing", async () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(screen.getByRole("button", { name: "数据" }));
  expect(screen.getByRole("heading", { name: "我的 Intelligence 数据存在哪里？" })).toBeTruthy();
  expect(screen.getByText("SQLite 保存结构化运行数据；大文本与附件保存在本地文件中。")).toBeTruthy();
  expect(screen.getByText("~/Library/Application Support/Intelligence/")).toBeTruthy();
  expect(screen.getByText(/Intelligence 仍会在本机保留完整运行数据/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "创建备份" }));
  expect(await screen.findByText("Last backup: Today 21:32")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "恢复备份" }));
  fireEvent.click(screen.getByRole("button", { name: "选择有效备份" }));
  expect(screen.getByText("Backup valid")).toBeTruthy();
  expect(screen.getByText("126 Contents")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "选择损坏备份" }));
  expect(screen.getByText(/不会覆盖你当前的数据/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "连接 Obsidian" }));
  expect(await screen.findByText("/Users/demo/Documents/Obsidian/Intelligence")).toBeTruthy();
  expect((screen.getByLabelText("视频笔记 / Content Notes") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("Raw Transcript") as HTMLInputElement).checked).toBe(false);
  fireEvent.click(screen.getByLabelText("Raw Transcript"));
  expect((screen.getByLabelText("Raw Transcript") as HTMLInputElement).checked).toBe(true);
  expect(screen.getByText("单向发布：Intelligence → Obsidian")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "立即发布" }));
  expect(await screen.findByText("已发布到 Obsidian（Demo）")).toBeTruthy();
});

test("processing recovery remains mock-only without network", async () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "关注" }));
  fireEvent.click(screen.getByRole("button", { name: "查看关注：AI Explained" }));
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  fireEvent.click(screen.getByRole("button", { name: /查看内容：AI Agent 产品设计的三个误区/ }));
  expect(screen.getByText("分析没有完成，但关注对象和已保存资料没有丢失。")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "重新分析（Demo）" }));
  expect(await screen.findByText("重新分析完成（Demo）")).toBeTruthy();
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("preference trust states remain manageable", async () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(screen.getByRole("button", { name: "偏好" }));
  expect(screen.getByText("有效至 9 月 20 日")).toBeTruthy();
  expect(screen.getByText("已过期 · 当前不再生效")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "忽略推导偏好：近期关注评测实践" }));
  await waitFor(() => expect(screen.queryByText("近期关注评测实践")).toBeNull());
});

test("review drawer keeps empty, unavailable, processing, Evidence and offline recovery states accessible", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "演示异常状态" }));
  fireEvent.click(screen.getByRole("button", { name: "首次无关注" }));
  expect(screen.getByText("还没有关注")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "首次无洞察" }));
  expect(screen.getByText("还没有洞察")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "无 Topic" }));
  expect(screen.getByText("还没有主题")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Provider 不可用" }));
  expect(screen.getByText("AI 服务暂时不可用")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "处理中" }));
  expect(screen.getByText("正在处理 3 个内容")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "无 Evidence" }));
  expect(screen.getByText("Evidence 暂时不可用")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "离线" }));
  expect(screen.getByText("暂时无法连接本地服务")).toBeTruthy();
});

// ──────────────────────────────────────────────────────────────────────────
// FINAL PRE-FREEZE — MULTILINGUAL CONTENT + GLOBAL SEARCH
// ──────────────────────────────────────────────────────────────────────────

test("multilingual fixture keeps English sources with Chinese output and resolvable translations", () => {
  expect(assertFixtureRelationships()).toEqual([]);
  const index = buildSearchIndex();
  // An English YouTube source carries a Chinese summary (English source → Chinese output).
  const englishVideo = index.find(entry => entry.id === "content:content-youtube-agent-pricing-en");
  expect(englishVideo?.sourceLanguage).toBe("English");
  expect(englishVideo?.crossLanguage).toBe(true);
  // Tokenized matching lets a Chinese multi-word query locate it.
  expect(searchIndexMatches(englishVideo!, "Agent 商业化")).toBe(true);
  // The cross-language Intelligence is discoverable through the Chinese output language.
  const taskInterface = index.find(entry => entry.id === "intelligence:intel-task-interface");
  expect(taskInterface?.crossLanguage).toBe(true);
  expect(searchIndexMatches(taskInterface!, "任务执行界面")).toBe(true);
});

test("settings separate UI language, content output language and Evidence display", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  fireEvent.click(screen.getByRole("button", { name: "常规 / 语言" }));
  expect(screen.getByRole("heading", { name: "常规 / 语言" })).toBeTruthy();
  expect((screen.getByLabelText("界面语言 简体中文") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("内容输出语言 简体中文") as HTMLInputElement).checked).toBe(true);
  expect((screen.getByLabelText("Evidence 默认显示 双语") as HTMLInputElement).checked).toBe(true);
  expect(screen.getByText(/界面语言、源内容语言与内容输出语言是三个独立概念/)).toBeTruthy();

  fireEvent.click(screen.getByLabelText("内容输出语言 English"));
  expect(screen.getByText(/当前：界面 简体中文 · 输出 English · Evidence 双语/)).toBeTruthy();
  fireEvent.click(screen.getByLabelText("界面语言 English"));
  expect(screen.getByText(/当前：界面 English · 输出 English · Evidence 双语/)).toBeTruthy();
  expect(screen.getByText(/切换界面语言不会改变内容或生成物的存储与语言/)).toBeTruthy();
});

test("pre-freeze path A shows an English source rendered with Chinese output artifacts", () => {
  window.location.hash = "#content-youtube-agent-pricing-en";
  render(<DemoApp initialExperience="workspace" />);
  expect(screen.getByRole("heading", { name: "Are AI Agents moving past pure subscription pricing?" })).toBeTruthy();
  const badge = screen.getByLabelText("语言信息");
  expect(within(badge).getByText("源语言")).toBeTruthy();
  expect(within(badge).getByText("English")).toBeTruthy();
  expect(within(badge).getByText("内容输出语言")).toBeTruthy();
  expect(within(badge).getByText("简体中文")).toBeTruthy();
  // Generated artifacts stay in the Chinese output language.
  expect(screen.getByText(/这期英文视频观察到/)).toBeTruthy();
  expect(screen.getByRole("heading", { name: "核心要点" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "时间戳章节" })).toBeTruthy();
  expect(screen.getByText("订阅模式的现状")).toBeTruthy();
});

test("pre-freeze path B switches Evidence between 译文, 双语 and 原文 without duplicating records", () => {
  window.location.hash = "#content-youtube-agent-pricing-en";
  render(<DemoApp initialExperience="workspace" />);
  const evidenceSection = screen.getByRole("region", { name: "内容 Evidence" });
  const toggle = within(evidenceSection).getByRole("group", { name: "Evidence 显示" });
  // Default 双语: translation leads, English original stays visible.
  expect(within(evidenceSection).getByText(/越来越多 Agent 团队开始把部分收入与可核验结果挂钩/)).toBeTruthy();
  expect(within(evidenceSection).getAllByText(/A growing number of Agent teams/).length).toBeGreaterThan(0);

  fireEvent.click(within(toggle).getByRole("button", { name: "原文" }));
  expect(within(evidenceSection).queryByText(/越来越多 Agent 团队开始把部分收入与可核验结果挂钩/)).toBeNull();
  expect(within(evidenceSection).getAllByText(/A growing number of Agent teams/).length).toBeGreaterThan(0);

  fireEvent.click(within(toggle).getByRole("button", { name: "译文" }));
  expect(within(evidenceSection).getByText(/越来越多 Agent 团队开始把部分收入与可核验结果挂钩/)).toBeTruthy();
  expect(within(evidenceSection).queryByText(/A growing number of Agent teams/)).toBeNull();
  // Evidence count is unchanged across display modes (translation is not a new record).
  expect(within(evidenceSection).getAllByText(/^Evidence E9 · 11:12/).length).toBe(1);
});

test("pre-freeze path C mocks on-demand full transcript translation", async () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  window.location.hash = "#content-youtube-agent-pricing-en";
  render(<DemoApp initialExperience="workspace" />);
  const transcriptDetails = screen.getByText("查看可追溯内容文本").closest("details")!;
  expect(within(transcriptDetails).getByText(/为减少模型使用量，默认只翻译摘要、要点、章节和 Evidence/)).toBeTruthy();
  expect(within(transcriptDetails).getByText(/A growing number of Agent teams are tying/)).toBeTruthy();

  fireEvent.click(within(transcriptDetails).getByRole("button", { name: "翻译完整字幕" }));
  expect(await within(transcriptDetails).findByText("完整字幕已翻译（Demo）")).toBeTruthy();
  expect(within(transcriptDetails).getByText(/越来越多 Agent 团队开始把部分收入/)).toBeTruthy();
  expect(within(transcriptDetails).queryByText(/A growing number of Agent teams are tying/)).toBeNull();
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("pre-freeze path D presents one Chinese Intelligence supported by cross-language Evidence", () => {
  window.location.hash = "#intelligence-detail-pricing";
  render(<DemoApp initialExperience="workspace" />);
  expect(screen.getByRole("heading", { name: /Outcome-based pricing 正在成为/ })).toBeTruthy();
  expect(screen.getByText(/这条洞察由多种语言的来源共同支持/)).toBeTruthy();
  // English YouTube (E9), Chinese Bilibili (E6) and English X (E7) all feed one judgment.
  expect(screen.getAllByText(/A growing number of Agent teams/).length).toBeGreaterThan(0);
  expect(screen.getByText(/订阅加成功费的混合模式明显增多/)).toBeTruthy();
  expect(screen.getAllByText(/Enterprise buyers still prefer predictable subscriptions/).length).toBeGreaterThan(0);
});

test("pre-freeze path E offers a per-Following output-language override under progressive disclosure", () => {
  window.location.hash = "#following-practical-ai";
  render(<DemoApp initialExperience="workspace" />);
  expect(screen.getByRole("heading", { name: "这个关注的内容输出语言" })).toBeTruthy();
  expect((screen.getByLabelText("使用全局语言设置") as HTMLInputElement).checked).toBe(true);
  expect(screen.queryByLabelText("输出语言 English")).toBeNull();

  fireEvent.click(screen.getByLabelText("为这个关注单独设置输出语言"));
  expect(screen.getByLabelText("输出语言 English")).toBeTruthy();
  expect(screen.getByLabelText("输出语言 简体中文")).toBeTruthy();
  fireEvent.click(screen.getByLabelText("输出语言 English"));
  expect((screen.getByLabelText("输出语言 English") as HTMLInputElement).checked).toBe(true);
  expect(screen.getByText(/英语学习类来源单独输出 English/)).toBeTruthy();
});

test("pre-freeze path F locates Following, Content, Intelligence, Topic and Research via global search", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "搜索你的 Intelligence" }));
  fireEvent.change(screen.getByLabelText("搜索关键词"), { target: { value: "Agent 商业化" } });
  expect(screen.getByText(/找到 \d+ 条结果/)).toBeTruthy();
  const results = screen.getByRole("region", { name: "搜索结果" });
  for (const type of ["关注", "内容", "洞察", "主题", "调研"]) {
    expect(within(results).getAllByText(type).length).toBeGreaterThan(0);
  }
  // Clicking a result navigates to the existing Demo object.
  fireEvent.click(within(results).getByRole("button", { name: "打开主题：AI Agent 商业化" }));
  expect(screen.getByRole("heading", { name: "AI Agent 商业化" })).toBeTruthy();
});

test("pre-freeze path G narrows search results with lightweight type filters", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "搜索你的 Intelligence" }));
  fireEvent.change(screen.getByLabelText("搜索关键词"), { target: { value: "Agent 商业化" } });
  const results = screen.getByRole("region", { name: "搜索结果" });
  const filters = screen.getByRole("group", { name: "搜索范围筛选" });

  fireEvent.click(within(filters).getByRole("button", { name: /洞察/ }));
  expect(within(results).getAllByText("洞察").length).toBeGreaterThan(0);
  expect(within(results).queryByText("主题")).toBeNull();

  fireEvent.click(within(filters).getByRole("button", { name: /主题/ }));
  expect(within(results).getAllByText("主题").length).toBeGreaterThan(0);
  expect(within(results).queryByText("洞察")).toBeNull();
});

test("pre-freeze path H shows a clear no-result state that stays inside the library", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "搜索你的 Intelligence" }));
  fireEvent.change(screen.getByLabelText("搜索关键词"), { target: { value: "zzz 不存在的查询 qqq" } });
  expect(screen.getByRole("heading", { name: "没有找到匹配内容。" })).toBeTruthy();
  expect(screen.getByText(/换一个关键词/)).toBeTruthy();
  expect(screen.getByText(/V1 搜索只覆盖你的本地 Intelligence 资料库/)).toBeTruthy();
  expect(screen.queryByRole("region", { name: "搜索结果" })).toBeNull();
});

test("global search demonstrates cross-language discovery through the preferred output language", () => {
  render(<DemoApp initialExperience="workspace" />);
  fireEvent.click(screen.getByRole("button", { name: "搜索你的 Intelligence" }));
  fireEvent.change(screen.getByLabelText("搜索关键词"), { target: { value: "任务执行界面" } });
  const results = screen.getByRole("region", { name: "搜索结果" });
  expect(within(results).getByText("Agent 产品正在从聊天界面转向任务执行界面")).toBeTruthy();
  expect(within(results).getAllByText("跨语言").length).toBeGreaterThan(0);
});
