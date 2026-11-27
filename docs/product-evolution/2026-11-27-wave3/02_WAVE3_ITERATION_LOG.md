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
