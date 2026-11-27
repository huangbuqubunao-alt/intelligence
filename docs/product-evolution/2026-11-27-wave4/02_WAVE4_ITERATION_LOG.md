# 02｜Wave 4 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave4-20261127`
- **堆叠基线（Wave 3 PR #54）**：`ecb843ea61c9e48589ce8d40d3f6cd48d702307d` (14/14 CI green)
- **回退约定**：Iter 18–23 均为单一产品目标的原子提交；任一需求均可单次 `git revert <sha>` 独立撤回，或整批回退至 Wave 3 (`ecb843ea`) / Wave 2 (`edd0b0b9`) / Wave 1 (`088554c4`) / `main` (`f7b97134`)。

---

## Iteration 18 (`EVO-W4-01`) — `#Research` 高置信问答结果一键沉淀为本地研究笔记

- **解决的用户问题**：用户在 `#Research` 产出带 `[E1][E2]` 原话时间戳引用的跨视频综合对比答案后，此前仅能复制或下载散落 `.md` 文件，无法一键存入 `#Content` 本地文档库以持续检索、批注与二次阅读。
- **核心改动**：
  1. 新增 [researchExport.ts](../../../frontend/src/workspace/researchExport.ts)：`deriveResearchNoteFilename` 自动生成带问题短标题与会话后缀的安全 `.md` 文件名；`buildResearchSynthesisMarkdown` 严格校验 `if (session.refused || !session.citations.length) return ""`，拒绝沉淀无依据或拒答输出。
  2. [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx)：在 `WorkspaceAiResearchPanel` 操作栏仅面向非拒答且含有效引用的回答呈现「沉淀为本地研究笔记」按钮，直连 `uploadLocal("/local/imports?filename=...")` 落盘，完成后即时提供「✓ 已沉淀入内容库 · 打开阅读 →」一键跳进阅读器。
- **自动化验证**：
  - 新增 [EvolutionIter18.test.tsx](../../../frontend/src/workspace/EvolutionIter18.test.tsx)（2 passed，覆盖拒答拒绝沉淀、正常沉淀上传及跳转阅读）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`800ms` (`assets/index-Dd-oJxiP.js` / `assets/index-CZ-EQaXr.css` / `assets/workspace-ai-hub-C59t3FXw.js`)；Vitest：**76/76 files, 1317/1317 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Research` → `#Content/...`）**：
  - 验证加载 `assets/index-Dd-oJxiP.js`、`assets/index-CZ-EQaXr.css` & `assets/workspace-ai-hub-C59t3FXw.js`（均 `200 OK`）；**0 console errors、0 pageerrors、0 HTTP >=400**。
  - 点击「沉淀为本地研究笔记」发起真实 `POST /api/v1/local/imports?...` 返回 **`201`**；点击「✓ 已沉淀入内容库 · 打开阅读 →」立即跳转阅读器渲染完整 Markdown 综合结论（Obsidian Dark、Warm Paper Light、`390x844` 移动端均 `mobileOverflow: false`）。
  - 实机截图归档：[Research Promoted Dark](./screenshots/iter-18/step_6_iter18_research_promoted_dark.png)、[Reader Dark](./screenshots/iter-18/step_8_iter18_reader_dark.png)、[Reader Light](./screenshots/iter-18/step_10_iter18_reader_light.png)、[Reader Mobile](./screenshots/iter-18/final_step_10_iter18_reader_mobile.png)。

---

## Iteration 19 (`EVO-W4-02`) — `⌘K` 命令面板全文检索个人笔记与 `#tag` 标签筛选直达

- **解决的用户问题**：用户写入阅读器的思考批注、原文摘录与 `#tag` 自建标签无法被全局 `⌘K` 搜索引擎召回，随笔记累积检索效率下降。
- **核心改动**：
  1. [personalNotes.ts](../../../frontend/src/workspace/personalNotes.ts)：新增 `listPersonalTagCounts()`（跨本机笔记大小写归一化聚合统计 `#tag` 与命中 ID 列表）、`setPendingContentTag` / `consumePendingContentTag`。
  2. [CommandPalette.tsx](../../../frontend/src/workspace/ui/CommandPalette.tsx) & [App.tsx](../../../frontend/src/workspace/App.tsx)：在打开 `⌘K` 时读取本机笔记与标签映射；为内容条目补充笔记与标签 `aliases` 加权；新增 `notes`（「个人笔记与标签」）分组展示正文片段直达条目与「按个人标签筛选：#tag」快捷动作（空输入默认列表仍保持紧凑、兼容既有单测）。
- **自动化验证**：
  - 新增 [EvolutionIter19.test.tsx](../../../frontend/src/workspace/EvolutionIter19.test.tsx)（2 passed，覆盖标签聚合计数、正文关键词召回个人笔记跳转及 `#tag` 筛选指令回调）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.10s` (`assets/index-DUxlaPKo.js` / `assets/index-CZ-EQaXr.css` / `assets/CommandPalette-DRQm3yhf.js`)；Vitest：**77/77 files, 1319/1319 passed**。
- **Chromium 实机验证（`127.0.0.1:8799`）**：
  - 验证加载 `assets/index-DUxlaPKo.js`、`assets/index-CZ-EQaXr.css` & `assets/CommandPalette-DRQm3yhf.js`（均 `200 OK`）；**0 console errors、0 pageerrors、0 HTTP >=400**。
  - 在 `vidDemoAgt1` 保存带 `#核心结论 #状态机` 的个人批注后，在 `#Home` 打开 `⌘K` 输入「核心结论」即呈现「个人笔记与标签」分组（含「按个人标签筛选：#核心结论」与「核心状态机边界复盘：工具校验决定稳定性」片段），点击直达 `#Content/vidDemoAgt1`；Obsidian Dark、Warm Paper Light 及 `390x844` 移动端（`mobileOverflow: false`）清晰无溢出。
  - 实机截图归档：[Cmd+K Notes Dark](./screenshots/iter-19/step_10_iter19_cmdk_notes_dark.png)、[Cmd+K Notes Light](./screenshots/iter-19/step_16_iter19_cmdk_notes_light.png)、[Cmd+K Notes Mobile](./screenshots/iter-19/step_18_iter19_cmdk_notes_mobile.png)。
