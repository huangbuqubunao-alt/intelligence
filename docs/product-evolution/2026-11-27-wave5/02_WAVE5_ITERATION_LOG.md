# 02｜Wave 5 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave5-20261127`
- **堆叠基线（Wave 4 PR #55）**：`1ed93e67281ebf59044c53c67e553f5934bf6f4b` (14/14 CI green)
- **回退约定**：Iter 24–29 均为单一产品目标的原子提交；任一需求均可单次 `git revert <sha>` 独立撤回，或整批回退至 Wave 4 (`1ed93e67`) / Wave 3 (`ecb843ea`) / Wave 2 (`edd0b0b9`) / Wave 1 (`088554c4`) / `main` (`f7b97134`)。

---

## Iteration 24 (`EVO-W5-01`) — `#Content` Saved Smart Filter Views ("自定义常用视图")

- **解决的用户问题**：高频研究者在 `#Content` 常复用固定的多维筛选组合（如「必看长视频 + #核心结论」或特定频道+关键词），此前每次进入需重复逐项筛选，工作流无法沉淀。
- **核心改动**：
  1. 新增 [savedViews.ts](../../../frontend/src/workspace/savedViews.ts)：实现 `SavedContentView` 6 维组合条件持久化（`yia.content_saved_views.v1`、上限 8 条、相同条件自动去重更新、合法字面量规范校验）、默认命名生成器 `suggestSavedViewName` 与跨组件事件同步 `SAVED_VIEWS_CHANGED_EVENT`。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：有激活筛选时出现「保存视图」按钮与内联命名表单 `.content-save-view-popover`；存在已存视图时呈现 `.content-saved-views-strip`（「常用视图：」），采用双独立 `<button>` 胶囊（选择与删除绝不嵌套）一键还原 6 维筛选状态。
- **自动化验证**：
  - 新增 [EvolutionIter24.test.tsx](../../../frontend/src/workspace/EvolutionIter24.test.tsx)（2 passed，覆盖名称建议、同条件去重、`#Content` 多维保存/重置/一键恢复与兄弟删除键移除）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`951ms` (`assets/index-DJD-T-1I.js` / `assets/index-DxNL4ko4.css`)；Vitest：**82/82 files, 1328/1328 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content`）**：
  - 确认加载新资源 `index-DJD-T-1I.js` & `index-DxNL4ko4.css`（HTTP `200`）；保存「周度必看精选」后重置筛选再点击恢复过滤均精确生效，删除胶囊 cleanly 移除；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Saved Views Dark](./screenshots/iter-24/step_1_iter24_saved_views_dark.png)、[Saved Views Light](./screenshots/iter-24/step_2_iter24_saved_views_light.png)、[Saved Views Mobile](./screenshots/iter-24/step_3_iter24_saved_views_mobile.png)。

## Iteration 25 (`EVO-W5-02`) — `#Research` Structured Analysis Lenses & Multi-Session Markdown Dossier Export

- **解决的用户问题**：用户进入 `#Research` 面对开放提问框常不知如何组织对比视角；同时多轮高可信跨视频对比积累后，缺乏一键把全部已核验问答汇集成带目录的 Markdown 研究汇编文档（同时绝不混入无引用或拒答会话）。
- **核心改动**：
  1. [researchExport.ts](../../../frontend/src/workspace/researchExport.ts)：新增 `RESEARCH_LENSES`（共识与分歧 / 产品化与变现 / 落地行动清单 / 反例与盲区）、`buildLensPrompt` 与 `buildResearchDossierMarkdown`（严格剔除 `refused` 或零引用的问答条目，置顶优先+最新优先生成规范多章节 Markdown）。
  2. [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：提问区上方新增 `.research-lenses-bar`（点击仅预填并聚焦提问框，不自动发送请求）；历史会话下方新增独立 `.ai-session-history-footer` 提供「导出研究汇编 (.md)」下载与状态确认（保持 `.ai-session-history` 既有胶囊排序语义完全不变）。
- **自动化验证**：
  - 新增 [EvolutionIter25.test.tsx](../../../frontend/src/workspace/EvolutionIter25.test.tsx)（2 passed，覆盖严格剔除拒答/无引用记录、透镜预填不触发 `/ask`、`导出研究汇编 (.md)` 触发 Blob 下载并读取校验内容）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.84s` (`assets/index-MCDOyrUa.js` / `assets/workspace-ai-hub-D5LOhqAZ.js` / `assets/index-tZ46Rynv.css`)；Vitest：**83/83 files, 1330/1330 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Research`）**：
  - 确认加载新资源 `index-MCDOyrUa.js`、`workspace-ai-hub-D5LOhqAZ.js` & `index-tZ46Rynv.css`（HTTP `200`）；点击「视角 · 共识与分歧」精准预填提问框且 `0` 个 `/research/ask` 请求发出；点击「导出研究汇编 (.md)」呈现「已导出研究汇编 (.md · 含 2 条已核验问答)。」；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Research Lenses Dark](./screenshots/iter-25/step_1_iter25_research_dark.png)、[Research Lenses Light](./screenshots/iter-25/step_2_iter25_research_light.png)、[Research Lenses Mobile](./screenshots/iter-25/step_3_iter25_research_mobile.png)。
