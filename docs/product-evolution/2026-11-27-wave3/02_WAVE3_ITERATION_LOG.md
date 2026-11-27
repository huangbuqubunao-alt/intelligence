# 02｜Wave 3 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave3-20261127`
- **堆叠基线（Wave 2 PR #53）**：`edd0b0b9a3b6db170e0da49436007f95f21ff31d`
- **回退约定**：Iter 12–17 均为单一产品目标的原子提交；任一需求均可通过单次 `git revert <sha>` 独立撤回，或整条分支回退至 Wave 2 (`edd0b0b9`) / Wave 1 (`088554c4`) / `main` (`f7b97134`)。

---

## Iteration 12 (`EVO-W3-01`) — 阅读器字幕与原话证据即时搜索、安全高亮及单段带出处复制

- **解决的用户问题**：在 30–90 分钟长视频字幕或长文档原文中查找特定关键词、以及查找被折叠在第 4 条之后的原话证据条目只能手动滚动目视排查，核验效率低。
- **核心改动**：
  1. 新增 [ReaderSearchTools.tsx](../../../frontend/src/workspace/ReaderSearchTools.tsx)：纯 React 节点切分实现的 `highlightTextMatches`（禁用 `dangerouslySetInnerHTML`）、`formatSegmentQuote`、`splitSearchableParagraphs` 与 `<ReaderDrawerSearchBar>` 实时计数搜索条。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx)：在阅读器字幕抽屉（同时兼容分段时间轴与本地 Markdown 段落）与原话证据抽屉接入即时关键词检索与 `<mark className="reader-search-hit">` 高亮；时间轴列表新增单段「复制此段」与秒数外链；证据抽屉输入搜索词后自动穿透前 3 条折叠上限直接定位 `#4+` 命中条。
  3. [styles.css](../../../frontend/src/workspace/styles.css)：为 `.reader-drawer-search-bar`、`.reader-search-hit`、`.timed-transcript-item-actions` 等样式适配 Obsidian Dark 与 Warm Paper Light 高对比度视觉。
- **自动化验证**：
  - 新增 [EvolutionIter12.test.tsx](../../../frontend/src/workspace/EvolutionIter12.test.tsx)（2 passed）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`823ms` (`assets/index-B73gSnAn.js` / `assets/index-CH_rVH2g.css`)；Vitest：**70/70 files, 1306/1306 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content/vidDemoAgt1`）**：
  - 验证加载 `assets/index-B73gSnAn.js` & `assets/index-CH_rVH2g.css`（均 `200 OK`）；**0 console errors、0 pageerrors、0 HTTP >=400**。
  - 在字幕抽屉输入 `SQLite` 准确显示「命中 1 / 3 段」并高亮标记，点击「复制此段」瞬态切换为「已复制」；深浅双主题清晰可读。
  - 在原话证据抽屉输入 `recovery` 自动穿透折叠抽屉，直接呈现包含 `#4`、`#6`、`#9` 在内的全部 4 条命中卡片并高亮匹配词；`390x844` 移动端 `mobileOverflow: false`。
  - 实机截图归档：[Transcript Search Dark](./screenshots/iter-12/step_6_shot_1_iter12_transcript_search_dark.png)、[Transcript Search Light](./screenshots/iter-12/step_22_shot_1_iter12_transcript_search_light.png)、[Evidence Search Dark](./screenshots/iter-12/step_26_shot_1_iter12_evidence_search_dark.png)、[Drawer Search Mobile](./screenshots/iter-12/step_28_shot_1_iter12_drawer_search_mobile.png)。

---

## Iteration 13 (`EVO-W3-02`) — 快速粘贴 Markdown / 文章 / 会议纪要直接入库

- **解决的用户问题**：研究过程中随手复制的长文段落、会议纪要或 Markdown 笔记必须先在本机创建临时 `.md` 文件再走文件上传，打断输入心流。
- **核心改动**：
  1. 新增 [QuickPasteNoteForm.tsx](../../../frontend/src/workspace/QuickPasteNoteForm.tsx)：提供可选标题 + Markdown 正文编辑器、自动安全文件名推导（`derivePasteFilename` / `buildPastedMarkdownPayload`）、实时 UTF-8 字节计数器（严格守住 2 MiB 上限）与 `uploadLocal` 直传本地 `/local/imports`。
  2. [AddEntry.tsx](../../../frontend/src/workspace/AddEntry.tsx) & [App.tsx](../../../frontend/src/workspace/App.tsx)：在导入弹窗顶部切换栏新增「粘贴文本/笔记」（保持默认单行链接框与既有单测 100% 兼容）；在 `⌘K` 命令面板增加「粘贴文本或笔记入库」直达动作。
  3. [styles.css](../../../frontend/src/workspace/styles.css)：为 `.paste-note-textarea` 与 `.paste-note-meta-row` 适配桌面与 `390x844` 移动端。
- **自动化验证**：
  - 新增 [EvolutionIter13.test.tsx](../../../frontend/src/workspace/EvolutionIter13.test.tsx)（2 passed）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`800ms` (`assets/index-ByNkdImW.js` / `assets/index-DtM-lwXU.css`)；Vitest：**71/71 files, 1308/1308 passed**。
- **Chromium 实机验证（`127.0.0.1:8796` 空库实传 & `127.0.0.1:8799` Demo）**：
  - 验证加载 `assets/index-ByNkdImW.js` & `assets/index-DtM-lwXU.css`（均为 `200 OK`）；**0 console errors、0 pageerrors、0 HTTP >=400**。
  - 在 `8796` 打开导入 →「粘贴文本/笔记」，粘贴 Markdown 笔记并提交 `POST /api/v1/local/imports?filename=2026-Agent-Reliability-Notes.md` 返回 **`201`**，自动打开纯文档阅读器展现「原文已就绪 · 待提炼洞察」。
  - 在 `390x844` Warm Paper Light 下粘贴弹窗与文档阅读器均保持 **`mobileOverflow: false`**。
  - 实机截图归档：[Paste Modal Dark](./screenshots/iter-13/step_6_shot_1_iter13_paste_modal_dark.png)、[Pasted Reader Dark](./screenshots/iter-13/step_8_shot_1_iter13_pasted_reader_dark.png)、[Pasted Reader Mobile Light](./screenshots/iter-13/step_10_shot_1_iter13_pasted_reader_mobile_light.png)、[Paste Modal Mobile Light](./screenshots/iter-13/step_14_shot_1_iter13_paste_modal_mobile_light.png)。

---

## Iteration 14 (`EVO-W3-03`) — 阅读器个人思考批注、原话证据一键摘录与 Obsidian 笔记融合导出

- **解决的用户问题**：阅读长视频洞察与可追溯原话证据时，用户无法在当前阅读流中沉淀个人思考、摘录关键原句并在后续导出 Obsidian Markdown 时自动带上个人批注，研究闭环断裂。
- **核心改动**：
  1. 新增 [personalNotes.ts](../../../frontend/src/workspace/personalNotes.ts)：本地 `localStorage` (`yia.personal-notes.v1`) 个人笔记与 `#tag` 持久化 CRUD、`appendQuoteToPersonalNote`、防重复追加检测、`mergePersonalNoteIntoMarkdown`（导出 Obsidian Markdown 时自动注入 `## 我的思考与批注`）、`exportPersonalNotesJson` / `importPersonalNotesJson` 与跨组件状态广播事件。
  2. 新增 [ReaderPersonalNoteCard.tsx](../../../frontend/src/workspace/ReaderPersonalNoteCard.tsx)：按需展开式行内「我的思考与批注」编辑器与 `#tag` 标签输入（支持防抖落盘、失焦即时保存、清空重置与本机存储标识）。
  3. [App.tsx](../../../frontend/src/workspace/App.tsx) & [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx)：在 `ContentEvidencePanel` 每张证据卡底栏新增「+ 摘录到笔记」动作（含 `已摘录` 瞬态反馈并自动展开批注卡片）；在 `#Content` 列表为有个人批注的内容显示「有笔记」徽章；在 Obsidian Markdown 导出/复制流程自动融合个人笔记与标签。
  4. [styles.css](../../../frontend/src/workspace/styles.css)：为 `.reader-personal-note-*`、`.personal-note-*`、`.content-note-badge` 与 `.evidence-clip-note-btn` 适配深浅双主题与移动端窄屏布局。
- **自动化验证**：
  - 新增 [EvolutionIter14.test.tsx](../../../frontend/src/workspace/EvolutionIter14.test.tsx)（2 passed）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.11s` (`assets/index-BrfhhcIU.js` / `assets/index-cDWPMURx.css`)；Vitest：**72/72 files, 1310/1310 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content/vidDemoAgt1`）**：
  - 验证加载 `assets/index-BrfhhcIU.js` & `assets/index-cDWPMURx.css`（均为 `200 OK`）；**0 console errors、0 pageerrors、0 HTTP >=400**。
  - 在「原话证据 (9)」抽屉点击第一张证据卡「+ 摘录到笔记」，按钮切换为「已摘录」；关闭抽屉后「我的思考与批注」自动展开并写入带时间戳的引用块 `>`；追加个人想法与 `#核心结论 #待复盘` 标签并在 `page.reload` 刷新后验证完整持久留存。
  - 返回 `#Content` 列表确认 `vidDemoAgt1` 正确呈现 `有笔记` 徽章；Warm Paper Light 与 `390x844` 移动端（`mobileOverflow: false`）无裁切或横向溢出。
  - 实机截图归档：[Evidence Clip Dark](./screenshots/iter-14/step_10_shot_1_iter14_evidence_clip_dark.png)、[Personal Note Dark](./screenshots/iter-14/step_14_shot_1_iter14_personal_note_dark.png)、[Content Noted Badge Dark](./screenshots/iter-14/step_16_shot_1_iter14_content_badge_dark.png)、[Personal Note Light](./screenshots/iter-14/step_18_shot_1_iter14_personal_note_light.png)、[Personal Note Mobile](./screenshots/iter-14/final_step_20_iter14_personal_note_mobile.png)。
