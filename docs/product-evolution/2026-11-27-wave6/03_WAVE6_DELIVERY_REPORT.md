# Intelligence｜Wave 6 自主产品演进交付报告（EVO-W6-01 ~ EVO-W6-06）

- **交付分支**：`antigravity/autonomous-product-evolution-wave6-20261127`
- **堆叠基线**：Wave 5 PR #56 (`d34b4813c01c9f2b01f0e402ed9bfb3f453701ba`)
- **`VERIFIED_CODE_SHA`**：`e629f54c79c03974273adee81e61842d866e32d9`
- **交付时间**：2026-11-27 (Asia/Shanghai)

---

## 一、产品经理视角交付总结（解决的核心用户问题）

Wave 6 围绕**「高亮抗遗忘主动回忆 → 周度 Obsidian 复盘交付 → 专题/洞察个人思考双向打通 → 采集与阅读器全键盘流效率」**展开，持续深化 Intelligence 作为「可审计个人 AI 知识工作台」的核心差异化体验：

1. **`#Home` 一键导出 7 日知识复盘周报（Iter 30）**：用户在首页查看「最近 7 天发生了什么变化？」时，可直接点击「导出周报 (.md)」生成符合 Obsidian `[[wikilinks]]` 规范的结构化周报，自动聚合本周新增与演化条目、周期内的个人思考批注 `#tag` 与摘录，以及下周待核查清单。
2. **`#Intelligence`「仅看已批注」与可信洞察导出（Iter 31）**：支持在洞察卡片流一键切换「仅看已批注 (N)」聚焦自己亲自思考过的高价值洞见；并在筛选条及已收藏条同时提供「导出 Markdown (.md)」，严格仅收录已验证可信结论（过滤未验证/不可用条目）并附带本机个人批注。
3. **`#Home`「温故知新 · 主动回忆」双面记忆巩固卡片（Iter 32）**：针对 Readwise 式的「高亮墓地效应」，在首页右栏推出「先回忆、再核对」卡片，优先抽取含本人批注或高分长期内容（自动剔除短片噪音）；默认仅展示标题与来源提示，点击「展开核对」后再揭示原结论与本人思考，点击「记住了 ✓」计入按本地自然日自动重置的复习进度。
4. **`#Topics` 专题详情融合个人批注与增强 MOC 导出（Iter 33）**：在专题演进时间轴卡片上直接呈现绿色 `已批注` 徽标与个人思考摘录；并在专题 MOC 导出栏新增「附带本专题个人批注 (N)」开关（默认开启），一键复制或下载时将 AI 专题脉络与本人研究批注无缝合并。
5. **快速粘贴采集模板、阅读耗时预览与阅读器 `N` 键直达思考（Iter 34）**：在快速粘贴文稿/笔记卡片新增 `+ 会议纪要`、`+ 文章精读摘录`、`+ 调研对比备忘` 三枚结构化模板与实时「约 N 分钟精读 · 字数 · KB 占比」提示；并在阅读器增加单键 `N` 快捷键直接定位并聚焦「我的思考与批注」（含防误输入护栏）。
6. **`G + 键` 全局极速跳转和弦、快捷键清单同步与全界面验收（Iter 35）**：实现 `G + H/F/C/I/T/R/S` 双键跳转和弦（`800ms` 窗口并拦截 `#Content` 单键 `S` 防误触收藏），在 `⌘K` 命令面板补充「查看有批注的内容」，并同步更新 `?` 快捷键指南弹窗与 8 视图双主题/移动端全量走查。

---

## 二、逐迭代回退索引表（Per-Iteration Revert Map）

每一轮迭代均为独立、原子化的单点需求提交；对任意单一需求不满意时，只需执行对应 `git revert <sha>` 即可精准撤回，不影响 Wave 1–5 或其余 Wave 6 特性：

| 迭代编号 | 需求代号 | 提交 SHA | 核心产品能力 | 回退影响范围 |
| :--- | :--- | :--- | :--- | :--- |
| **Iter 30** | `EVO-W6-01` | `40f3abd0` | `#Home` 7 日知识复盘周报 `.md` 一键导出（含周期个人批注） | 仅移除 `weeklyReviewExport.ts` 与 `KnowledgeDelta.tsx` 导出按钮 |
| **Iter 31** | `EVO-W6-02` | `0b7f5526` | `#Intelligence`「仅看已批注 (N)」筛选与可信洞察 `.md` 导出 | 仅移除 `intelligenceExport.ts` 与 `IntelligencePage` 筛选/导出控制 |
| **Iter 32** | `EVO-W6-03` | `a8f5f297` | `#Home`「温故知新 · 主动回忆」双面巩固卡片（含跨日重置） | 仅移除 `activeRecall.ts` 与 `.home-recall-panel` |
| **Iter 33** | `EVO-W6-04` | `2a9fc1c1` | `#Topics` 详情演进卡片内联个人批注与专题 MOC 合并开关 | 仅移除 `buildTopicMarkdownWithPersonalNotes` 与 `.topic-entry-note-box` |
| **Iter 34** | `EVO-W6-05` | `26d6bad6` | 快速粘贴结构化模板 + 阅读耗时预览 + 阅读器 `N` 键直达思考框 | 仅移除 `QuickPasteNoteForm.tsx` 模板预览与 `ReaderPersonalNoteCard.tsx` `N` 键监听 |
| **Iter 35** | `EVO-W6-06` | `e629f54c` | `G+H/F/C/I/T/R/S` 全局和弦跳转、快捷键清单同步与 `⌘K` 批注入口 | 仅移除 `App.tsx` `G+key` 监听、命令入口与 `KeyboardShortcutsModal.tsx` 同步项 |

### 整波级安全回退锚点（Wave Rollback Anchors）

- 回退整批 **Wave 6**：重置或基于 **Wave 5** 基线 [`d34b4813c01c9f2b01f0e402ed9bfb3f453701ba`](../2026-11-27-wave5/03_WAVE5_DELIVERY_REPORT.md)（PR #56）
- 回退至 **Wave 4**：`1ed93e67281ebf59044c53c67e553f5934bf6f4b`（PR #55）
- 回退至 **Wave 3**：`ecb843ea61c9e48589ce8d40d3f6cd48d702307d`（PR #54）
- 回退至 **Wave 2**：`edd0b0b9a3b6db170e0da49436007f95f21ff31d`（PR #53）
- 回退至 **Wave 1**：`088554c45f9d8d05818f415871fd124655280969`（PR #52）
- 仓库 **`main` 基线**：`f7b97134a9fafd3e8e447851a4237bdc66f7e60e`（全程未受污染）

---

## 三、全量构建与自动化测试证据（On `VERIFIED_CODE_SHA = e629f54c`）

| 检查项 | 命令与覆盖范围 | 实测结果 |
| :--- | :--- | :--- |
| TypeScript 类型检查 | `npx tsc --noEmit --incremental false` | **0 errors** |
| Vite 生产构建 | `npm run build` | **通过 (`902ms`)** · `assets/index-DoDpLJli.js` / `assets/index-ClFtVfhH.css` |
| Vitest 全量前端单测 | `npm test -- --run`（含 `EvolutionIter30`–`EvolutionIter35`） | **93/93 文件，1349/1349 用例全部通过** |
| `uv lock --check` | 依赖锁完整性校验 | **Resolved 107 packages，通过** |
| `ruff check src tests scripts` | Python 静态代码规范检查 | **All checks passed** |
| `mypy src` | Python 全量类型检查（138 个源文件） | **Success: no issues found in 138 source files** |
| `scripts/ci_test_manifest.py verify` | 全仓 pytest 清单 100% 对齐校验 | **Verified: 7401 collected / 7190 runnable**（含 0 项 Python 源码变更） |
| Python 核心套件（组合 + 定向复核） | `test_contracts.py` + `test_public_beta_demo_showcase.py` + `test_final_blocker_closure.py` + `test_po_demo.py` | 组合跑 **106 passed, 1 failed (`85.02s`)**（`test_demo_launcher_rejects_occupied_ports_before_starting_children` 受限于本地 10s 子进程限时）；定向隔离复跑该用例 **1 passed in 7.70s**；远端 GitHub Actions CI 进行全矩阵 **14/14** 校验 |

---

## 四、Wave 6 实机 Chromium 8 视图全量验收

在本地 Curated Demo（`http://127.0.0.1:8799`）与 Empty Workspace（`http://127.0.0.1:8796`）均完成硬刷新验证（确认 `index-DoDpLJli.js` 与 `index-ClFtVfhH.css` 返回 HTTP `200`）：

- **Console 错误 / 未捕获异常 / 非预期失败请求 / 误触 Live AI**：全部为 **`0`**；
- **主题与响应式**：Obsidian Dark、Warm Paper Light 及 `390x844` 移动端全视图 **`mobileOverflow: false`**；
- **实机证据归档目录**：
  - Iter 30：[screenshots/iter-30/](./screenshots/iter-30/step_1_iter30_weekly_dark.png)（3 张）
  - Iter 31：[screenshots/iter-31/](./screenshots/iter-31/step_1_iter31_intel_dark.png)（3 张）
  - Iter 32：[screenshots/iter-32/](./screenshots/iter-32/step_1_iter32_recall_dark.png)（3 张）
  - Iter 33：[screenshots/iter-33/](./screenshots/iter-33/step_1_iter33_topics_dark.png)（3 张）
  - Iter 34：[screenshots/iter-34/](./screenshots/iter-34/step_1_iter34_quick_paste_dark.png)（3 张）
  - Iter 35 8 视图 QA：[screenshots/iter-35/](./screenshots/iter-35/w6_v7b_shortcuts_dark.png)（11 张）
