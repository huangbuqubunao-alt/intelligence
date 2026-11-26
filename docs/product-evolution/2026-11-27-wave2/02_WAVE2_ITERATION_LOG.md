# 02｜Wave 2 迭代演进与验证日志（Iteration Log）

- **分支**：`antigravity/autonomous-product-evolution-wave2-20261127`
- **基线 anchor（Wave 1 / PR #52）**：`088554c45f9d8d05818f415871fd124655280969`
- **回退约定**：每次迭代均为单一产品目标的原子提交；若某一需求在终审被拒绝，可直接按单次提交执行 `git revert <sha>`，或整批回退至 Wave 1 PR #52。

---

*(以下由各迭代完成后实时追加真实修改、测试数据、Chromium 实机结果与隐私扫描记录。)*

---

## Iteration 6 (`EVO-W2-01`) — Day-1 内置安全示例笔记一键体验 + 空关注页视觉层级降噪

- **解决的用户问题**：全新空工作区（`8798`）用户在尚无链接或本地文件时无法快速体验完整「本地导入 → 原文核验 → 提炼总结 → Obsidian 导出」路径；同时空 `#Following` 页面右上角与空状态卡存在两枚完全一致的绿色主按钮分散焦点。
- **核心改动**：
  1. 新增 [starterSample.ts](../../../frontend/src/workspace/starterSample.ts)：生成纯本机离线的双语架构笔记 `intelligence-starter-local-first-rag.md`，走真实 `uploadLocal` -> `POST /api/v1/local/imports` 完整入库链路（零外网请求、零云端模型消费）。
  2. 更新 [App.tsx](../../../frontend/src/workspace/App.tsx) 空状态首页 `Dashboard` 与空状态 `ContentPage`：在「导入第一个内容」/「添加内容」旁增加「一键导入示例笔记体验」（`Try with built-in sample note`）次级按钮及异常反馈。
  3. 精修空 `#Following` 视觉层级（与 [styles.css](../../../frontend/src/workspace/styles.css) `.following-capability-note`）：在保持双 `Add Source` 按钮可访问性与既有测试契约不变的前提下，将顶部 `.page-actions` 按钮降级为 `button-secondary`，让空状态卡 CTA 成为唯一主按钮焦点。
- **自动化验证**：
  - 新增 [EvolutionIter6.test.tsx](../../../frontend/src/workspace/EvolutionIter6.test.tsx)（3 passed）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：built in `1.18s` (`assets/index-Bqo5D_QE.js`)；Vitest：**64/64 files, 1292/1292 passed**。
- **Chromium 实机验证（`127.0.0.1:8798` 空工作区）**：
  - 加载 `assets/index-Bqo5D_QE.js`（`200 OK`）；**0 console errors、0 page errors、0 HTTP >=400**。
  - 实测在 `#Home` 点击「一键导入示例笔记体验」触发 `POST /api/v1/local/imports?filename=intelligence-starter-local-first-rag.md` -> **`201 Created`**，自动打开文档阅读器并完整渲染 `速跳 · 文档原文`。
  - `390x844` 移动端零横向溢出；Warm Paper Light 与 Obsidian Dark 对比度清晰。
  - 实机截图归档：[Empty Home Dark](./screenshots/iter-6/step_4_shot_1_iter6_empty_home_dark.png)、[Empty Home Mobile Light](./screenshots/iter-6/step_6_shot_1_iter6_empty_home_mobile.png)、[Empty Following](./screenshots/iter-6/step_8_shot_1_iter6_empty_following.png)、[Starter Note Reader](./screenshots/iter-6/step_10_shot_1_iter6_starter_reader.png)。

---

## Iteration 7 (`EVO-W2-02`) — 专题→研究「对比共识与分歧」直达桥 + 同范围追问模板

- **解决的用户问题**：用户在 `#Topics` 查看「跨来源观点对照」后无法一键带着这些对应内容进入 `#Research` 进行头对头共识/分歧追问；同时每次得到有据回答后仍面对空白输入框，缺乏零静默扣费的深挖追问模板；移动端 390px 下指定多视频对比选项标题被挤成窄竖条。
- **核心改动**：
  1. [WorkspaceAiWidgets.tsx](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx)：新增 `setPendingResearchDraftQuestion` / `consumePendingResearchDraftQuestion` 可编辑预设草稿交接（绝不自动提交，零静默云端调用）；在有据回答卡片下方新增「同范围继续深挖」3 条分析视角胶囊及状态回显。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx)：在 `#Topics`「跨来源观点对照」区块标题旁增加「对比共识与分歧 (N) →」按钮，点击自动锁定来源视频 ID 并带入预填对比问题进入 `#Research`。
  3. [demo_showcase.py](../../../src/youtube_intel/demo_showcase.py) & [test_public_beta_demo_showcase.py](../../../tests/integration/test_public_beta_demo_showcase.py)：基于真实 Chromium 首轮实测发现的回放检索遗漏，补充跨来源对比/深挖问句的正向概念词规范化（同时严格保持全部无关/编造/反前提问题的拒答红线）。
  4. [styles.css](../../../frontend/src/workspace/styles.css)：新增 `.topic-perspectives-head`、`.ai-followup-strip`、`.ai-followup-chip`、`.ai-followup-toast`，并修复 `<=720px` 下 `.ai-video-compare-option` 响应式换行排版。
- **自动化验证**：
  - 后端：`ruff check`、`mypy` 0 errors；`tests/integration/test_public_beta_demo_showcase.py` → **8 passed in 56.00s**。
  - 前端：`npx tsc --noEmit --incremental false` 0 errors；`npm run build` (`815ms`, `assets/index-DIj2APOA.js`)；新增 [EvolutionIter7.test.tsx](../../../frontend/src/workspace/EvolutionIter7.test.tsx)（3 passed）；Vitest **65/65 files, 1295/1295 passed**。
- **Chromium 实机验证（`127.0.0.1:8799` Demo 工作区）**：
  - 验证加载 `assets/index-DIj2APOA.js`（`200 OK`）；**0 console errors、0 page errors、0 HTTP >=400**。
  - 从「一人公司与 AI 产品化」点击「对比共识与分歧 (2) →」跳转 `#Research`，准确锁定 2 篇视频并预填可编辑问题（`0` 次自动发请求）；点击「AI 提问」返回 `200 OK`（`answer_status: GROUNDED`, `refused: false`, **3 条跨源可点击验证引用 `[E1]`/`[E2]`/`[E5]`**）并展现 3 枚深挖胶囊；`390x844` Warm Paper Light 移动端标题自然全宽换行、`mobileOverflow: false`。
  - 实机截图归档：[Topic Compare CTA](./screenshots/iter-7/step_4_shot_1_iter7_topic_compare_cta.png)、[Research Handoff](./screenshots/iter-7/step_6_shot_1_iter7_research_handoff_dark.png)、[Grounded Followups](./screenshots/iter-7/step_10_shot_1_iter7_research_grounded_followups.png)、[Light Mobile 390px](./screenshots/iter-7/step_14_shot_1_iter7_research_light_mobile.png)。

---

## Iteration 8 (`EVO-W2-03`) — `#Content` 两级分诊工具栏与 `390x844` 移动端首屏上提

- **解决的用户问题**：解决基线审计 `AUD-10`（`390x844` 手机端 `#Content` 顶部 6 行筛选器占满 `304.5px` 高度，将第 1 条内容推到 `y=578.59px` 的屏下边缘）。
- **核心改动**：
  1. [App.tsx](../../../frontend/src/workspace/App.tsx) (`ContentPage`)：将筛选栏重整为「高频分诊主栏 `.library-filter-primary`（搜索框 + 价值分流胶囊 + 移动端「筛选 (N)」开关按钮）」与「精细筛选次栏 `.library-filter-secondary`（频道 / 专题 / 平台来源 / 排序 / 批量标已读）」，并实时统计已启用的精细筛选项数。
  2. [styles.css](../../../frontend/src/workspace/styles.css)：桌面端 (`>=769px`) 保持全量筛选器直接展开、隐藏移动端按钮；`<=768px` 移动端将搜索与「筛选」同行排列、价值分流胶囊转为单行横向滚动、次级筛选默认折叠按需展开。
- **自动化验证**：
  - 新增 [EvolutionIter8.test.tsx](../../../frontend/src/workspace/EvolutionIter8.test.tsx)（1 passed）。
  - `npx tsc --noEmit --incremental false` 0 errors；`npm run build` (`1.25s`, `assets/index-BEv7z-hV.js`)；Vitest：**66/66 files, 1296/1296 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content`）**：
  - 验证加载 `assets/index-BEv7z-hV.js`（`200 OK`）；**0 console errors、0 page errors、0 HTTP >=400**。
  - `390x844` Warm Paper Light 首屏筛选栏高度从 `304.5px` 降至 **`87.5px`（-71.3%）**，首条内容顶边从 `578.59px` 上提至 **`361.59px`（-217px，首屏完整可见近 3 条内容）**，`mobileOverflow: false`；展开/选择高分优先/收起正确保留 `筛选 (1)` 角标；桌面端 `1440x900` 保持 `87.5px / 228.40px`。
  - 实机截图归档：[Content Desktop Dark](./screenshots/iter-8/step_4_shot_1_iter8_content_desktop_dark.png)、[Content Mobile Collapsed Light](./screenshots/iter-8/step_4_shot_2_iter8_content_mobile_collapsed_light.png)、[Content Mobile Expanded Dark](./screenshots/iter-8/step_10_shot_1_iter8_content_mobile_expanded_dark.png)。

---

## Iteration 9 (`EVO-W2-04`) — 阅读器出版级来源卡片、一键带出溯源引用与移动端关键帧适配

- **解决的用户问题**：无内嵌封面的视频详情页在阅读器顶部显示空洞占位区且缺乏直接核对原话入口；同时抽屉内的证据卡片不支持一键复制带出处的 Markdown 引用句；此外移动端关键帧预览导航缺少换行保护。
- **核心改动**：
  1. [ReaderMediaStage.tsx](../../../frontend/src/workspace/ReaderMediaStage.tsx)：新增 `evidenceCount`、`transcriptAvailable`、`onOpenEvidenceDrawer` 属性；无缩略图时渲染 `.reader-media-poster.is-editorial-card` 出版级来源卡片，展示「已保存可核验原文 · N 条原话证据」状态及「核对原话证据」CTA（保留本地 `.md` 文档无视频多余控件）。
  2. [App.tsx](../../../frontend/src/workspace/App.tsx)：接入 `ReaderMediaStage` 上述属性并传入 `videoTitle` 到 `ContentEvidencePanel`；在 `.evidence-card-footer` 新增「复制引用」（`> "<text>"\n— 《Title》 [locator]`）按钮及瞬态「已复制」反馈。
  3. [styles.css](../../../frontend/src/workspace/styles.css)：新增 `.reader-media-poster.is-editorial-card`、`.reader-media-editorial-copy`、`.reader-media-editorial-status`、`.reader-media-poster-actions`、`.evidence-copy-quote-btn` 样式及移动端 `.visual-keyframe-lightbox-nav` 换行规则。
- **自动化验证**：
  - 新增 [EvolutionIter9.test.tsx](../../../frontend/src/workspace/EvolutionIter9.test.tsx)（2 passed）。
  - `npx tsc --noEmit --incremental false`：0 errors；`npm run build`：`1.07s` (`assets/index-BLVovRka.js`)；Vitest：**67/67 files, 1298/1298 passed**。
- **Chromium 实机验证（`127.0.0.1:8799/#Content/vidDemoAgt1` & 本地 `.md`）**：
  - 验证加载 `assets/index-BLVovRka.js`（`200 OK`）；**0 console errors、0 page errors、0 HTTP >=400**。
  - 深色 Obsidian Dark 与浅色 Warm Paper Light 均清晰渲染「已保存可核验原文 · 9 条原话证据」与「核对原话证据」CTA；点击打开抽屉并点击「复制引用」成功切换为「已复制」；按 `Esc` 关闭抽屉且焦点准确回到触发按钮。
  - `390x844` 移动端 `mobileOverflow: false`；本地 `.md` 文档 `demo-architecture-notes.md` 无任何多余视频/字幕/关键帧控件。
  - 实机截图归档：[Editorial Card Dark](./screenshots/iter-9/step_19_shot_1_iter9_editorial_card_dark.png)、[Editorial Card Light](./screenshots/iter-9/step_6_shot_2_iter9_editorial_card_light.png)、[Drawer Copy Quote](./screenshots/iter-9/step_8_shot_1_iter9_drawer_copy_quote.png)、[Mobile Reader 390px](./screenshots/iter-9/step_10_shot_1_iter9_mobile_reader.png)、[Local Markdown Clean](./screenshots/iter-9/step_14_shot_1_iter9_local_md_clean.png)。
