# 02｜Wave 7 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave7-20261127`
- **堆叠基线（Wave 6 PR #57）**：`06b75b9622fab6a33f069dc0084597a4d388f220` (14/14 CI green)
- **回退约定**：Iter 36–41 均为单一产品目标的原子提交；任一需求均可单次 `git revert <sha>` 独立撤回，或整批回退至 Wave 6 (`06b75b96`) / Wave 5 (`d34b4813`) / Wave 4 (`1ed93e67`) / Wave 3 (`ecb843ea`) / Wave 2 (`edd0b0b9`) / Wave 1 (`088554c4`) / `main` (`f7b97134`)。

---
## Iteration 36 (`EVO-W7-01`) — `#Content` Multi-Select Batch Tagging & Selected Obsidian Reading Pack Export

- **解决的用户问题**：在 `#Content` 多选模式下，用户虽然能选中多篇文章对比提问或复制纯文本摘要，但仍缺少**「批量追加个人 `#tag`」**以及**「将精选篇目连同 AI 结论与个人思考打包导出为 Obsidian Reading Pack `.md`」**的一站式带走能力。
- **核心改动**：
  1. [personalNotes.ts](../../../frontend/src/workspace/personalNotes.ts)：新增 `batchAddPersonalTags`，支持为选中多条内容批量合并追加 `#tag`（大小写去重、每条上限 12 个、绝不覆盖或清空原有批注正文）。
  2. 新增 [contentExport.ts](../../../frontend/src/workspace/contentExport.ts)：实现 `buildSelectedContentMarkdown`，生成含 `[[wikilinks]]` 目录索引、来源与评分元信息、核心结论、产品/商业启发及个人批注标签的 Obsidian 精选阅读包（`reading-pack-YYYY-MM-DD.md`）。
  3. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：在 `.content-selection-bar` 新增「批量打标签」行内气泡（含输入与现有 `#tag` 复用建议）与「导出精选 (.md)」按钮及状态提示。
- **自动化验证**：
  - 新增 [EvolutionIter36.test.tsx](../../../frontend/src/workspace/EvolutionIter36.test.tsx)（3 passed，覆盖批量打标签保留原正文、Reading Pack Markdown 格式清洗与多选工作台交互导出）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.00s` (`assets/index-D3a5bv9b.js` / `assets/index-CEo4D2Uv.css`)；Vitest：**94/94 files, 1352/1352 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content`）**：
  - 确认加载最新构建资源 `index-D3a5bv9b.js` 与 `index-CEo4D2Uv.css`（HTTP `200`）；多选 2 篇内容执行批量打标签（`#Wave7验证 #架构设计`）并导出 `reading-pack-2026-11-27.md`（1834 bytes），顶部 `#tag` 胶囊与「有笔记」计数同步实时更新；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Content Dark](./screenshots/iter-36/iter36_content_dark.png)、[Content Light](./screenshots/iter-36/iter36_content_light.png)、[Content Mobile](./screenshots/iter-36/iter36_content_mobile.png)。

## Iteration 37 (`EVO-W7-02`) — `#Topics` Personal Tag Governance (Rename / Merge & Delete)

- **解决的用户问题**：用户在内容库积累多个自建 `#tag` 后容易产生同义标签碎片（如 `#Agent` 与 `#Agents`）或废弃临时标签；在 `#Topics` 缺少原地重命名、合并及只删标签不误删批注正文的治理机制。
- **核心改动**：
  1. [personalNotes.ts](../../../frontend/src/workspace/personalNotes.ts)：新增 `renamePersonalTag`（大小写无关安全替换并跨笔记去重合并，保留所有思考正文）与 `deletePersonalTag`（移除标签，仅当批注正文与剩余标签均为空时才清理空壳条目）。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：在「我的自建标签」卡片新增「管理标签 / 完成管理」切换按钮，默认浏览态保持极简，展开治理态后为每个标签提供行内重命名/合并输入与安全删除动作。
- **自动化验证**：
  - 新增 [EvolutionIter37.test.tsx](../../../frontend/src/workspace/EvolutionIter37.test.tsx)（3 passed，覆盖合并去重、删标签保留正文与 `#Topics` 治理面板 UI 交互）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.20s` (`assets/index-CdKfYk17.js` / `assets/index-DcWKGOfm.css`)；Vitest（4 进程平衡并发）：**95/95 files, 1355/1355 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Topics`）**：
  - 确认加载最新构建资源 `index-CdKfYk17.js` 与 `index-DcWKGOfm.css`（HTTP `200`）；展开「管理标签」将 `#Wave7验证 (2)` 合并为 `#架构设计` 后标签计数精准收敛（5 → 4），并安全切回标签胶囊视图；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Topics Dark](./screenshots/iter-37/iter37_topics_dark.png)、[Topics Light](./screenshots/iter-37/iter37_topics_light.png)、[Topics Mobile](./screenshots/iter-37/iter37_topics_mobile.png)。

## Iteration 38 (`EVO-W7-03`) — `#Following` Instant Channel Search & Signal Audit `.md` Export

- **解决的用户问题**：当关注订阅源不断增加后，`#Following` 缺少即时频道名/链接过滤输入框；同时虽有顶部信噪比统计，用户却无法一键导出一份可用于定期「断舍离低干货/Shorts 频道」的信息食谱审计报告。
- **核心改动**：
  1. 新增 [followingAuditExport.ts](../../../frontend/src/workspace/followingAuditExport.ts)：实现 `buildFollowingAuditMarkdown`，按均分与必看数生成高信噪比频道榜，高亮低干货 / Shorts 噪音频道与健康异常提醒，并输出可执行信息食谱调优清单。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：在 `Sources` 顶部增加 `.following-toolbar` 即时搜索框（支持频道名、链接、`LOCAL`/`BILIBILI`/`YOUTUBE` 与「本地资料库」检索，零匹配时提供「清空搜索」一键恢复），并在健康简报栏新增「导出信源体检 (.md)」下载按钮。
- **自动化验证**：
  - 新增 [EvolutionIter38.test.tsx](../../../frontend/src/workspace/EvolutionIter38.test.tsx)（2 passed，覆盖信源榜单排序、异常预警、即时搜索清空恢复与审计 Markdown 导出）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`994ms` (`assets/index-DvYVt2RR.js` / `assets/index-GAUoG3-z.css`)；Vitest：**96/96 files, 1357/1357 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Following`）**：
  - 确认加载最新构建资源 `index-DvYVt2RR.js` 与 `index-GAUoG3-z.css`（HTTP `200`）；点击导出 `following-signal-audit-2026-11-27.md`（912 bytes）并展示 `已导出信源体检 (.md · 3 个信源)。`；搜索 `Atlas` 精准过滤至 1 条，零匹配搜索后点击「清空搜索」无损恢复；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Following Dark](./screenshots/iter-38/iter38_following_dark.png)、[Following Light](./screenshots/iter-38/iter38_following_light.png)、[Following Mobile](./screenshots/iter-38/iter38_following_mobile.png)。

## Iteration 39 (`EVO-W7-04`) — `#Research` Pinned-Only Filter & Save Grounded Answer to Source Note

- **解决的用户问题**：在 `#Research` 积累多条跨视频问答后，用户缺少一键聚焦「已置顶问答」的历史过滤开关；同时高价值的研究结论难以直接反哺写回对应被引用视频的个人批注中。
- **核心改动**：
  1. [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：在「历史跨视频问答」标题栏新增仅当存在置顶记录时才显示的「仅看置顶 (N)」开关（置于 `.ai-session-history` 列表外侧以完全兼容既有键盘与排序契约，联动筛选面板与研究汇编导出）。
  2. 在非拒答且具备至少 1 条已核验引用的问答动作栏新增「摘录进来源批注」按钮，点击后零后端调用即以幂等引用格式追加至首要引用视频的个人思考批注中并提示目标篇名（对拒答/零引用回答严格隐藏）。
- **自动化验证**：
  - 新增 [EvolutionIter39.test.tsx](../../../frontend/src/workspace/EvolutionIter39.test.tsx)（1 passed，验证仅看置顶过滤、零 `/research/ask` POST 反写来源批注、拒答隐藏按钮）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`916ms` (`assets/index-DCYJYqAq.js` / `assets/workspace-ai-hub-CUbqY7YM.js` / `assets/index-DIH8PVDv.css`)；Vitest：**97/97 files, 1358/1358 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Research`）**：
  - 全程 `0` live `/research/ask` POST、`0` console/page/network 错误；点击「摘录进来源批注」反馈 `已将研究结论摘录进《Building High-Margin Local-First AI Tools Solo Builders Love》个人批注。`，置顶并开启「仅看置顶 (1)」精准收敛历史记录；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）。
  - 实机截图归档：[Research Dark](./screenshots/iter-39/iter39_research_dark.png)、[Research Light](./screenshots/iter-39/iter39_research_light.png)、[Research Mobile](./screenshots/iter-39/iter39_research_mobile.png)。

## Iteration 40 (`EVO-W7-05`) — Reader 1-Click AI Takeaway Capture into Personal Notes

- **解决的用户问题**：在长视频/文稿阅读详情页，用户浏览 AI 提炼的「AI 产品化启发」和「商业变现与切入机会」列表时，仍需手动选中复制才能写进下方「我的思考与批注」卡片。
- **核心改动**：
  1. [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：为 `WorkspaceVideoAiBriefCard` 增加可选的 `onCaptureTakeaway` 与 `capturedNoteText` 同步状态，在每条启发旁渲染轻量 `+ 摘录` / `已摘录 ✓` 胶囊按钮（未传回调时不改变任何既有多列表呈现）。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx)：在 `ContentDetailPanel` 挂载回调，点击即刻调用 `appendQuoteToPersonalNote` 以幂等格式写入本机思考并实时更新 `personalNote` 状态与个人批注文本域。
- **自动化验证**：
  - 新增 [EvolutionIter40.test.tsx](../../../frontend/src/workspace/EvolutionIter40.test.tsx)（1 passed，覆盖一键摘录、`已摘录 ✓` 状态切换、幂等防重复与阅读器实时同步）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`874ms` (`assets/index-Bjre6ZJ1.js` / `assets/workspace-ai-hub-mTeg4sgk.js` / `assets/index-CVg34vlZ.css`)；Vitest：**98/98 files, 1359/1359 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content/vidDemoAgt1`）**：
  - 确认加载最新构建资源（HTTP `200`）；点击「AI 产品化启发」旁 `+ 摘录` 即刻变为 `已摘录 ✓` 且下方个人思考文本框实时追加对应引用段落；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Reader Dark](./screenshots/iter-40/iter40_reader_dark.png)、[Reader Light](./screenshots/iter-40/iter40_reader_light.png)、[Reader Mobile](./screenshots/iter-40/iter40_reader_mobile.png)。

## Iteration 41 (`EVO-W7-06`) — Unified v2 Portable Study State Snapshot & Wave 7 Full 8-View QA

- **解决的用户问题**：用户在 `#Settings` 导出本机个人笔记（`.json`）时此前未一并包含在 `#Content` 中辛苦沉淀的「常用筛选视图」（`SavedContentView`），跨设备或重装迁移时仍会丢失高频工作流视图配置。
- **核心改动**：
  1. [savedViews.ts](../../../frontend/src/workspace/savedViews.ts)：新增 `mergeSavedContentViews`，支持按过滤条件签名与 ID 双重去重，严守上限 8 条视图且不覆写已有常用视图。
  2. 新增 [studyWorkspaceSnapshot.ts](../../../frontend/src/workspace/studyWorkspaceSnapshot.ts)：实现 `exportStudyWorkspaceSnapshotJson`（产出 `version: 2` 统一学习快照：含 `notes` 与 `saved_views`）及 `importStudyWorkspaceSnapshotJson`（同时兼容旧版 `version: 1` 仅笔记 JSON 备份文件）。
  3. [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx)：在 `#Settings` 的导出/导入个人笔记流程中接入 v2 统一快照与 `savedViewCount` 实时回显，保持既有一切按钮文案与 v1 导入语义向下兼容。
- **自动化验证**：
  - 新增 [EvolutionIter41.test.tsx](../../../frontend/src/workspace/EvolutionIter41.test.tsx)（2 passed，覆盖 v2 导出/去重合并、v1 历史快照兼容及 `#Settings` 备份交互；原 `EvolutionIter17` / `EvolutionIter29` 均全绿通过）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`896ms` (`assets/index-CJarxaiA.js` / `assets/workspace-ai-hub-Bo4QxKIS.js` / `assets/index-CVg34vlZ.css`)；Vitest：**99/99 files, 1361/1361 passed**。
- **Chromium 实机 8 视图全界面 QA 巡检（`127.0.0.1:8799` Demo + `127.0.0.1:8796` Empty Workspace）**：
  - 确认加载最新构建产物 `index-CJarxaiA.js`、`workspace-ai-hub-Bo4QxKIS.js` 与 `index-CVg34vlZ.css`（HTTP `200`）。
  - 完整走查 `#Home`、`#Following`（频道搜索 + 信源体检导出）、`#Content`（多选批量打标签 + 阅读包导出）、`#Topics`（自建标签治理）、`#Intelligence`（仅看已批注 + Markdown 导出）、`#Content/vidDemoAgt1`（AI 启发一键 `+ 摘录`）、`#Research`（`摘录进来源批注` + 历史区，`0` live `/research/ask` POST）、`#Settings`（统一快照 `.json` 导出反馈 `已导出本机个人笔记与标签（共 3 条 · 含 1 个常用视图）。` + Dark / Light / `390x844` 移动端 `mobileOverflow: false`）与空白工作台 `8796/#Home`；全程 `0` console/page/network 错误。
  - 实机截图归档（11 张）位于 `screenshots/iter-41/`：[Settings Dark](./screenshots/iter-41/w7_v8_settings_dark.png)、[Settings Light](./screenshots/iter-41/w7_v8b_settings_light.png)、[Settings Mobile](./screenshots/iter-41/w7_v8c_settings_mobile.png)、[Empty Home](./screenshots/iter-41/w7_v9_empty_home.png) 等。
