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

## Iteration 26 (`EVO-W5-03`) — Reader "Connected Knowledge" & 1-Click Pairwise Research Compare

- **解决的用户问题**：用户在阅读单篇内容时，很难顺手发现库内同一 `#tag`、同专题或同频道的关联资料，更无法一键将「当前正在读的这一篇 + 关联的那一篇」直接送入 `#Research` 做正反对比提问。
- **核心改动**：
  1. 新增 [relatedContent.ts](../../../frontend/src/workspace/relatedContent.ts)：`findRelatedContentItems`（纯本机 Zero-Network 算法，按共同个人 `#tag` +5、同专题 +3、同标签领域 +2、同频道 +1 计算关联度并自动排除 Shorts 噪音，输出最高信号理由如 `共标 #核心结论` / `同专题 · ...`）。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx) & [styles.css](../../../frontend/src/workspace/styles.css)：`ContentDetailPanel` 底部「按需查阅原始资料」下方新增默认折叠的「关联延伸阅读」渐进式面板（`.reader-related-panel`），点击「展开关联 (N)」呈现关联卡片与双独立按钮（左键跳转延伸阅读，右 sibling「对比提问 →」带双视频 ID 与对比草稿跳转 `#Research` 预填且绝不误触发请求）。
- **自动化验证**：
  - 新增 [EvolutionIter26.test.tsx](../../../frontend/src/workspace/EvolutionIter26.test.tsx)（2 passed，覆盖共享 `#tag` 优先级排序、Shorts 排除、渐进式展开及点击「对比提问 →」锁定 2 篇跳转 `#Research`）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`985ms` (`assets/index-I-0CP-G-.js` / `assets/index-CqqKRhj6.css`)；Vitest：**84/84 files, 1332/1332 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content/vidDemoAgt1`）**：
  - 确认加载新资源 `index-I-0CP-G-.js` & `index-CqqKRhj6.css`（HTTP `200`）；默认收敛态展开后呈现 2 篇同专题关联内容；点击「对比提问 →」精确跳转 `#Research` 锁定 2 篇且 `0` 个 `/research/ask` 请求发出；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page/network 错误**。
  - 实机截图归档：[Related Dark](./screenshots/iter-26/step_1_iter26_related_dark.png)、[Related Light](./screenshots/iter-26/step_2_iter26_related_light.png)、[Related Mobile](./screenshots/iter-26/step_3_iter26_related_mobile.png)。

## Iteration 27 (`EVO-W5-04`) — Reader Personal Note Reflection Templates & Canonical Tag Suggestions

- **解决的用户问题**：阅读器打开空白思考卡片后用户常不知如何结构化沉淀；同时跨文章手工输入 `#tag` 容易因大小写或近义词差异产生碎片化标签。
- **核心改动**：
  1. [ReaderPersonalNoteCard.tsx](../../../frontend/src/workspace/ReaderPersonalNoteCard.tsx)：在文本框上方新增 3 个结构化复盘模板胶囊（`+ 3-2-1 复盘`、`+ 质疑与待核查`、`+ 下一步行动`），点击以追加方式写入且绝不覆盖已有正文；在标签输入框下方同步本机 `listPersonalTagCounts()`（自动排除当前条目已用标签），提供最多 8 个已有标签一键点选复用。
  2. [styles.css](../../../frontend/src/workspace/styles.css)：新增 `.personal-note-templates-row`、`.personal-note-template-chip`、`.personal-note-suggested-tags` 与 `.personal-note-suggested-tag` 样式。
- **自动化验证**：
  - 新增 [EvolutionIter27.test.tsx](../../../frontend/src/workspace/EvolutionIter27.test.tsx)（验证保留原有文本追加 3-2-1 模板、已用标签自动去重不重复推荐、点击推荐标签一键追加持久化）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`851ms` (`assets/index-jY4qGLSK.js` / `assets/index-D9yleBer.css`)；Vitest：**85/85 files, 1333/1333 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content/vidDemoSol2` → `#Content/vidDemoAgt1`）**：
  - 确认加载新资源 `index-jY4qGLSK.js` & `index-D9yleBer.css`（HTTP `200`）；追加 `#实践复盘` 后在 `vidDemoAgt1` 自动推荐 `+ #实践复盘`，点击模板与推荐标签即时生效持久化；Dark / Light / `390x844` 移动端（`mobileOverflow: false`）；**0 console/page 错误**。
  - 实机截图归档：[Templates Dark](./screenshots/iter-27/step_1_iter27_templates_dark.png)、[Templates Light](./screenshots/iter-27/step_2_iter27_templates_light.png)、[Templates Mobile](./screenshots/iter-27/step_3_iter27_templates_mobile.png)。
