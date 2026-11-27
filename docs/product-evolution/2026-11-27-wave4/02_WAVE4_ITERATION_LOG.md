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

---

## Iteration 20 (`EVO-W4-03`) — `#Content` 个人笔记 `#tag` 筛选条与 `#Topics` 自建标签直达桥

- **解决的用户问题**：AI 自动专题聚类之外，用户在个人批注里打上的自定义 `#tag`（如 `#核心结论`、`#状态机`）无法在 `#Topics` 专题总览与 `#Content` 内容列表间按标签一键交叉筛选聚合。
- **核心改动**：
  1. [App.tsx](../../../frontend/src/workspace/App.tsx)：在 `#Content`（含 `ContentFilterSnapshot` 与Scoped Next-Unread 连续精读）中接入 `tagFilter` 状态并响应 `PERSONAL_NOTES_CHANGED_EVENT` 与 `⌘K` `#tag` 跳转；当本机存在任意标签时在工具栏下方呈现 `.content-tag-filter-strip`（`我的标签：#核心结论 (1) ...`）。
  2. 在 `#Topics` 顶部新增按需呈现的 `.topics-personal-tags-card`（「我的自建标签」），点击任意 `#tag` 胶囊立即跳进按该标签精准筛选的 `#Content` 视图。
  3. [styles.css](../../../frontend/src/workspace/styles.css)：新增 `.content-tag-filter-strip`、`.content-tag-chip` 与 `.topics-personal-tags-card` 深浅双主题及移动端样式。
- **自动化验证**：
  - 新增 [EvolutionIter20.test.tsx](../../../frontend/src/workspace/EvolutionIter20.test.tsx)（2 passed，覆盖 `#Topics` 自建标签直达 `#Content` 精确筛选与重置，以及 `⌘K` 按个人标签过滤）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.04s` (`assets/index-CoCrF203.js` / `assets/index-BhqP1hHm.css`)；Vitest：**78/78 files, 1321/1321 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Topics` → `#Content`）**：
  - 验证加载 `assets/index-CoCrF203.js` & `assets/index-BhqP1hHm.css`（均 `200 OK`）；**0 console errors、0 pageerrors、0 HTTP >=400**。
  - `#Topics` 顶部展示「我的自建标签」`#核心结论 (1)`、`#状态机 (1)`；点击 `#核心结论 (1)` 跳转 `#Content` 并高亮激活 `.content-tag-chip.is-active`，精准收敛展示 `1 / 6` 匹配条目（`vidDemoAgt1`）；Obsidian Dark、Warm Paper Light 与 `390x844` 移动端均 `mobileOverflow: false`。
  - 实机截图归档：[Topics Personal Tags Dark](./screenshots/iter-20/step_4_iter20_topics_tags_dark.png)、[Content Tag Filter Dark](./screenshots/iter-20/step_6_iter20_content_tag_dark.png)、[Content Tag Filter Light](./screenshots/iter-20/step_10_iter20_content_tag_light.png)、[Content Tag Filter Mobile](./screenshots/iter-20/final_step_12_iter20_content_tag_mobile.png)。

## Iteration 21 (`EVO-W4-04`) — Reader Study Continuity, Reading Time Estimate & Comfort Typography
- **产品目标**：降低长资料反复阅读与回溯的认知切换成本——打开任意精读详情自动估算阅读耗时并提供"舒朗排版"模式，返回首页时右侧直出"最近阅读 · 继续精读"快捷续读入口。
- **代码变更**：
  - 新增 `frontend/src/workspace/readingHistory.ts`：`estimateReadingMinutes`（中文/英文分词估算 + 音视频时长兜底）、`readReadingHistory` / `recordReadingVisit` / `clearReadingHistory`（`yia.reading_history.v1` 最多保留 8 条 + 跨标签页事件同步）、`readReaderComfortMode` / `writeReaderComfortMode`。
  - 修改 `frontend/src/workspace/App.tsx`：`Dashboard` 新增 `continueReadingPanel`（在含周报/队列的常规首页与已导入示例笔记的新手首页双路径均展示最近 4 条访问记录及一键`清空`），`ContentDetailPanel` 新增阅读时间胶囊 `.reader-read-time-pill`、`标准排版 / 舒朗排版` 切换按钮（`.reader-comfort-toggle` + `.detail-panel.is-reading-comfort`）以及基于正文/分段的访问自动记账。
  - 修改 `frontend/src/workspace/styles.css`：新增 `.recent-reading-*`、`.reader-back-row-tools`、`.reader-read-time-pill`、`.detail-panel.is-reading-comfort` 等深浅色自适应样式。
  - 新增 `frontend/src/workspace/EvolutionIter21.test.tsx`：验证中英文与时长估算、进入 Reader 后自动入账并在 `#Home` 呈现与一键清空、`舒朗排版` 切换与 `aria-pressed` 状态持久化。
- **验证证据**：
  - TypeScript / Build / Vitest：`npx tsc --noEmit --incremental false`（0 errors）、`npm run build`（`assets/index-CMR687yE.js` + `assets/index-DjV7XEVn.css`）、Vitest **79/79 files, 1323/1323 tests passed**。
  - 实机 Chromium（`http://127.0.0.1:8799`）：确认新包 HTTP 200、`#Content/vidDemoAgt1` 展示 `约 1 分钟精读` 与 `舒朗排版 -> 标准排版` 切换、`#Home` 右栏出现 `最近阅读 · 继续精读`、点击 `继续 →` 回跳原文、点击 `清空` 即刻移除；Dark / Light / Mobile (`390x844`, `mobileOverflow: false`)、`0` console/network 错误。
  - 实机截图归档：[Reader Comfort Dark](./screenshots/iter-21/step_1_iter21_reader_comfort_dark.png)、[Home Continue Dark](./screenshots/iter-21/step_2_iter21_home_continue_dark.png)、[Home Continue Light](./screenshots/iter-21/step_3_iter21_home_continue_light.png)、[Home Continue Mobile](./screenshots/iter-21/step_4_iter21_home_continue_mobile.png)。

## Iteration 22 (`EVO-W4-05`) — Actionable `#Following` Attention Filter & Safe Source Recovery Guidance
- **产品目标**：让订阅源异常与低产排查变得可操作但不打扰用户——存在异常或缺少基线的信源时在健康简报栏直出“需处理异常信源 (N)”一键筛选，并在行内展示诚实、零静默重试的恢复建议与设置直达入口。
- **代码变更**：
  - 修改 `frontend/src/workspace/App.tsx`：向 `Sources` 传入 `onOpenSettings={() => navigate("Settings")}`，抽取 `isAttentionSource` 复用过滤规则，在 `.following-health-digest` 中当 `attentionSources.length > 0` 时渲染可切换的 `需处理异常信源 (N)` / `Needs attention (N)` 胶囊按钮；新增 `describeSourceRecoveryGuidance` 纯函数（覆盖频率限制、授权/抓取异常、无可用字幕、B 站连续追踪受限、缺少基线等状态，绝不触发任何自动后台重试），并在 `.source-row` 内作为 `.source-actions` 之后的独立网格跨列兄弟节点 `.source-recovery-hint`（绝不嵌套在 `button.source-select` 内）展示提示及可选 `前往设置` 入口。
  - 修改 `frontend/src/workspace/styles.css`：新增 `.following-health-review-btn.is-attention` 与跨列 `.source-recovery-hint` (`grid-column: 1 / -1`) 深浅色自适应样式。
  - 新增 `frontend/src/workspace/EvolutionIter22.test.tsx`：验证异常信源在 `.following-health-digest` 中一键筛选、`.source-recovery-hint` 不嵌套于 `<button class="source-select">`、点击筛选与恢复引导不会触发自动重检请求、点击 `前往设置` 正常跳转 `#Settings`。
- **验证证据**：
  - TypeScript / Build / Vitest：`npx tsc --noEmit --incremental false`（0 errors）、`npm run build`（`assets/index-DSDkFkus.js` + `assets/index-Mb47NKEr.css`）、Vitest **80/80 files, 1324/1324 tests passed**。
  - 实机 Chromium（`http://127.0.0.1:8799/#Following` & `http://127.0.0.1:8796/#Following`）：确认新包 HTTP 200；Demo 全健康信源下简报栏不误报异常、`待评估信源 (1)` 切换筛选正常、空工作区展示规范引导；Dark / Light / Mobile (`390x844`, `mobileOverflow: false`)、`0` console/network 错误。
  - 实机截图归档：[Following Dark](./screenshots/iter-22/step_1_iter22_following_dark.png)、[Following Light](./screenshots/iter-22/step_2_iter22_following_light.png)、[Following Mobile](./screenshots/iter-22/step_3_iter22_following_mobile.png)、[Empty Following](./screenshots/iter-22/step_4_iter22_empty_following.png)。

## Iteration 23 (`EVO-W4-06`) — Obsidian Markdown Personal Notes Digest Export & Wave 4 8-View QA Sweep
- **产品目标**：补齐个人精读笔记与 `#tag` 体系向外部知识库的无摩擦流转闭环，让用户不仅能做 JSON 整库迁移，还能一键将全部本机心得与时间戳摘录导出为带 Obsidian `[[wikilinks]]` 与标签索引的单文件 Markdown 汇编。
- **代码变更**：
  - 修改 `frontend/src/workspace/personalNotes.ts`：新增 `sanitizeWikilinkTitle` 与 `exportPersonalNotesMarkdown(titleByVideoId, zh)`，按最新更新时间倒序汇整全部非空个人笔记、生成标签计数索引与 `## [[Title]]` 双链条目，并对 0 条笔记场景返回规范可读说明。
  - 修改 `frontend/src/workspace/WorkspaceAiWidgets.tsx`：引入 `exportPersonalNotesMarkdown`，在 `.personal-notes-backup-row` 新增 `导出笔记汇编 (.md)` / `Export notes digest (.md)` 按钮，下载前尝试拉取 `/videos?limit=200` 自动回填可读标题（接口不可用时优雅回退至 `video_id`）。
  - 新增 `frontend/src/workspace/EvolutionIter23.test.tsx`：验证双链括号清洗、标签索引与时间倒序逻辑，以及设置页点击 `导出笔记汇编 (.md)` 后真实触发带解析标题的 Markdown 文件下载与状态提示。
- **验证证据**：
  - TypeScript / Build / Vitest：`npx tsc --noEmit --incremental false`（0 errors）、`npm run build`（`assets/index-Gn0wcjU9.js` + `assets/workspace-ai-hub-Bqbl7t3S.js` + `assets/index-Mb47NKEr.css`）、Vitest **81/81 files, 1326/1326 tests passed**。
  - 全表面 8 视图实机 Chromium QA（`http://127.0.0.1:8799` & `http://127.0.0.1:8796`）：覆盖 `#Settings`（`.md` 汇编导出确认反馈 + `.json` 导入导出）、`#Content/vidDemoAgt1`（阅读耗时与排版切换）、`#Home`（最近阅读续读栏）、`#Topics` 浅色主题（自建标签联动）、`#Following`（信噪比简报）、`#Research`（跨视频问答）、Mobile `390x844`（`mobileOverflow: false`）与 `8796` 空工作区；`0` console/page/network 错误。
  - 实机截图归档：[View 1 Settings MD Dark](./screenshots/iter-23/view1_settings_md_dark.png)、[View 2 Reader Dark](./screenshots/iter-23/view2_reader_dark.png)、[View 3 Home Dark](./screenshots/iter-23/view3_home_dark.png)、[View 4 Topics Light](./screenshots/iter-23/view4_topics_light.png)、[View 5 Following Dark](./screenshots/iter-23/view5_following_dark.png)、[View 6 Research Dark](./screenshots/iter-23/view6_research_dark.png)、[View 7 Settings Mobile](./screenshots/iter-23/view7_settings_mobile.png)、[View 8 Empty Settings](./screenshots/iter-23/view8_empty_settings.png)。
