# 02｜Wave 6 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave6-20261127`
- **堆叠基线（Wave 5 PR #56）**：`d34b4813c01c9f2b01f0e402ed9bfb3f453701ba` (14/14 CI green)
- **回退约定**：Iter 30–35 均为单一产品目标的原子提交；任一需求均可单次 `git revert <sha>` 独立撤回，或整批回退至 Wave 5 (`d34b4813`) / Wave 4 (`1ed93e67`) / Wave 3 (`ecb843ea`) / Wave 2 (`edd0b0b9`) / Wave 1 (`088554c4`) / `main` (`f7b97134`)。

---
## Iteration 30 (`EVO-W6-01`) — `#Home` 7-Day Weekly Knowledge Review Markdown Export

- **解决的用户问题**：用户在 `#Home` 能查看「最近 7 天发生了什么变化？」，但此前缺少一键将该周期变动与当周个人思考批注打包成可归档进 Obsidian 的结构化周报工作流。
- **核心改动**：
  1. 新增 [weeklyReviewExport.ts](../../../frontend/src/workspace/weeklyReviewExport.ts)：实现 `buildWeeklyReviewMarkdown` 与轻量级 `downloadMarkdownText`，按 Obsidian `[[wikilinks]]` 规范格式化周期统计概览、各类别条目的时间/修订/证据数/状态迁移明细、严格对齐 7 日时间窗的本机个人批注 `#tag` 与摘录块，以及下周待核查清单。
  2. [KnowledgeDelta.tsx](../../../frontend/src/workspace/KnowledgeDelta.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：在 7 日变化卡片标题栏右侧新增轻量「导出周报 (.md)」按钮（不可用或无变化时自动隐藏），点击即刻下载 `weekly-knowledge-review-YYYY-MM-DD.md` 并显示自动消退的状态反馈。
- **自动化验证**：
  - 新增 [EvolutionIter30.test.tsx](../../../frontend/src/workspace/EvolutionIter30.test.tsx)（2 passed，覆盖窗口边界笔记过滤、标题防破坏清洗、`[[wikilinks]]` 生成与 Blob 下载交互）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`915ms` (`assets/index-Cupf6YYi.js` / `assets/index-a4D8ZBrm.css`)；Vitest：**88/88 files, 1339/1339 passed**（含原 `KnowledgeDelta.test.tsx` 全绿）。
- **Chromium 实机验证（`127.0.0.1:8799/#Home`）**：
  - 确认加载最新构建资源（HTTP `200`）；点击「导出周报 (.md)」触发 `weekly-knowledge-review-2026-11-27.md` 下载并提示 `已导出本周复盘周报 (.md · 4 条动态 · 2 篇批注)。`；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Weekly Dark](./screenshots/iter-30/step_1_iter30_weekly_dark.png)、[Weekly Light](./screenshots/iter-30/step_2_iter30_weekly_light.png)、[Weekly Mobile](./screenshots/iter-30/step_3_iter30_weekly_mobile.png)。

## Iteration 31 (`EVO-W6-02`) — `#Intelligence` Noted-Only Filter & Verified Insights Markdown Export

- **解决的用户问题**：在 `#Intelligence` 洞察卡片流中，用户虽然能看到 `已批注 · #tag` 徽标，但无法一键筛选出「仅自己亲自批注过的洞察」，也无法将当前筛选范围或已收藏的高可信洞察直接导出为包含个人笔记的 Obsidian Markdown 汇编文档。
- **核心改动**：
  1. 新增 [intelligenceExport.ts](../../../frontend/src/workspace/intelligenceExport.ts)：实现 `buildVerifiedIntelligenceMarkdown`，严格仅收录 `status === "AVAILABLE" && trusted === true` 条目（严滤未验证/不可用数据），按 `[[Title]]` 双链输出核心判断、要点、原话证据引用，并自动附加对应视频的本机个人批注与 `#tags`。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：`IntelligencePage` 实时监听 `PERSONAL_NOTES_CHANGED_EVENT`，存在已批注洞察时呈现「仅看已批注 (N)」开关胶囊（动态联动来源与专题计数）；筛选条与已收藏摘要条均新增「导出 Markdown (.md)」按钮并反馈确认状态。
- **自动化验证**：
  - 新增 [EvolutionIter31.test.tsx](../../../frontend/src/workspace/EvolutionIter31.test.tsx)（2 passed，覆盖未验证条目过滤、个人批注嵌入、切换「仅看已批注 (1)」精确过滤与 Blob Markdown 下载内容验证）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`925ms` (`assets/index-DiYsXj_z.js` / `assets/index-ALwNnug0.css`)；Vitest：**89/89 files, 1341/1341 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Intelligence`）**：
  - 确认加载最新构建资源（HTTP `200`）；激活「仅看已批注 (2)」精准筛选 2 / 4 张已批注洞察，点击「导出 Markdown (.md)」下载 `verified-insights-2026-11-27.md`（2915 bytes）并显示 `已导出 Markdown (.md · 2 条)。`；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Intel Dark](./screenshots/iter-31/step_1_iter31_intel_dark.png)、[Intel Light](./screenshots/iter-31/step_2_iter31_intel_light.png)、[Intel Mobile](./screenshots/iter-31/step_3_iter31_intel_mobile.png)。
