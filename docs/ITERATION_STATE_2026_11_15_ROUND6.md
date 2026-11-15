# 自主产品诊断、优化与持续迭代状态记录（2026-11-15 Round 6）

- **迭代分支（开发工作区）**：`antigravity/task-user-readiness-20261112`（`/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`，起始基线 `2d34958`）
- **正式交付运行区**：`main`（`/Users/hua/Documents/yia-worktrees/v1x-local-main`，起始基线 `a1fa49b`）
- **只读对照工作区（严禁修改）**：`codex/readiness-v4-budget-final-validation`（`18f366b`）
- **前置轮次状态**：Round 1–5 已全部完成并客观验收（见 `docs/ITERATION_STATE_2026_11_14.md` 至 `docs/ITERATION_STATE_2026_11_15_ROUND5.md`）。
- **当前阶段**：`ROUND_6_COMPLETED`

---

## 一、第一阶段与第二阶段：Round 6 真实生产库核验与六维诊断

对正式运行环境 `.var/owner/state.sqlite3` 与 `.workspace-ai/hub.sqlite3` 执行只读深度核验，结合用户真实工作流走查与 Phase 5 自我审查，识别并闭环修复 **3 项真实数据/字段口径缺陷** 与 **3 项核心决策闭环能力**：

| 编号 | 模块 / 用户场景 | 真实证据与问题本质 | 优先级 | 实际落地方案与验证状态 |
| --- | --- | --- | --- | --- |
| `R6-1a` | `#Home` 周报漏斗统计口径重复计入 Shorts 及历史存档虚高 | 生产库共 `115` 条视频（`79` 条 Shorts，`36` 条非 Shorts 长视频，其中 `31` 条必看），但旧版 `distill_video` 对 `<=95s` Shorts 未强制设为 `SKIP_NOISE`，且 `_compute_funnel_stats` 统计 `must_watch_count` 未排除 `is_short_noise=1`，导致周报顶栏显示 `精选 48 必看`（`79+48=127>115` 口径矛盾）；同时历史存档快照在部分未提炼时写入虚高 `must_watch_count`（`45/47`） | **P1（数据准确性修复）** | **PASS**：`distill_video` 强制 Shorts 为 `SKIP_NOISE`；`_compute_funnel_stats` 严格排除 `is_short_noise`；`_sanitize_stored_funnel_stats` 基于快照 `created_at` 与 `briefs_map` `updated_at` 精确回溯历史非 Shorts 必看数（实机恢复为单调一致的 `28 -> 30 -> 31 必看`） |
| `R6-1b` | `#Home` 周报多期存档缺少期次变化对比（Weekly Delta Diff） | 生产库已有 `3` 期周报存档，但查看最新一期或切换存档时仅显示静态全文，缺少“较上一期新增多少篇提炼内容、新增几篇必看、哪些趋势/产品切口为本期新增”的决策增量视图 | **P1（核心复盘价值）** | **PASS**：`get_latest_weekly_brief` 自动对比紧邻上一期存档，输出结构化 `delta`（`distilled_delta`、`must_watch_delta`、`new_picks`、`new_shifts_zh`、`new_opportunities_zh`、`summary_zh`），前端渲染紧凑的 `.weekly-delta-strip`（实机呈现 `较上期新增提炼 13 篇 · 新增 1 篇必看干货 · 3 项新趋势风向`） |
| `R6-2a` | `#Research` 空范围错误码前后端不匹配 + 来源胶囊数量显示 `(0)` | 后端空范围抛 `409 NO_GROUNDED_CONTENT`，前端仅判断 `INSUFFICIENT_MATERIAL`，导致空筛选误报“请检查本机 Ollama”；同时前端 `readResearchScopeOptions` 仅读取 `count` 未兼容后端 `video_count`，导致频道胶囊显示 `(0)` | **P1（错误态与统计修复）** | **PASS**：前端兼容 `NO_GROUNDED_CONTENT` 与 `INSUFFICIENT_MATERIAL` 给出区分场景的诚实引导；`readResearchScopeOptions` 兼容 `count ?? video_count`（实机恢复显示 `OpenAI (22)`、`Greg Isenberg (10)`、`本地实战课 (2)`） |
| `R6-2b` | `已收藏` 精选清单与 `AI 跨视频深度问答` 断链 | Round 5 支持 `S` 键快速收藏，但收藏多篇重点视频后无法一键针对“已收藏清单”发起跨视频对比追问 | **P1（批阅→研究闭环）** | **PASS**：后端 `ask_research_question` 支持 `starred_only: true` 并在 `scope_options` 暴露 `starred_count`；`#Research` 增加 `仅限已收藏 (N)` 胶囊，`#Content` 增加 `针对已收藏提问 (N)` 一键直达联动 |
| `R6-3` | `#Content` 36 篇未读干货缺少批量标已读与可撤销恢复 | 按专题或关键词浏览完一批内容后，仍需逐篇按键或点击标已读，缺少单事务批量更新与一键撤销机制 | **P2（批阅吞吐效率）** | **PASS**：新增单事务接口 `POST /api/v1/workspace-ai/curation/batch`；`#Content` 筛选栏提供无弹窗 `当前列表标已读 (N)` 按钮，执行后展示内联 `.curation-undo-strip` `撤销`（一键无损恢复原未读状态） |

### 主动排除项（拒绝过度设计）
- 不引入逐行红绿文本 Diff 弹窗（高认知负担且无助于决策，采用结构化指标与新上榜条目摘要）。
- 不在 `#Content` 每行左侧常驻多选复选框（破坏阅读界面克制感，采用“基于当前筛选列表批量已读 + 一键撤销”模式）。

---

## 二、小批次 TDD 提交链与独立验证证据

### 1. 代码提交链
- **Slice 1（后端 TDD）**：开发分支 `e13f34b` / 正式 `main` `cf6923b` — `feat(workspace-ai): fix Short funnel double-count, add weekly delta diff, starred Q&A scope & batch curation`
- **Slice 2（前端 TDD）**：开发分支 `0ad50c8` / 正式 `main` `ad9f926` — `feat(ui): add Weekly Brief delta diff strip, Content batch mark-read with undo & starred Q&A handoff`
- **Slice 3（Phase 5 自我审查校准）**：开发分支 `5c544cc` / 正式 `main` `c1ad3b9` — `fix(workspace-ai): reconcile legacy weekly archive must-watch counts by snapshot timestamp`

### 2. 自动化测试与静态门禁（全部 `PASS`）
- **后端全量集成与单测**：`29 passed in 93.99s`（`tests/integration/test_workspace_intelligence_hub.py` 含 `test_round6_funnel_accuracy_weekly_delta_starred_research_and_batch_curation`、`tests/integration/test_fast_read_api.py`、`tests/unit/test_owner_launcher.py`）
- **代码规范与类型检查**：`ruff check`（`All checks passed!`）、`mypy`（`Success: no issues found in 2 source files`）
- **前端全量测试与生产构建**：`49 passed (49)` 测试文件 / `1201 passed (1201)` 用例（含 `WorkspaceIntelligenceHub.test.tsx` 19 项），`npm run build`（`✓ built in 655ms`），`npx impeccable detect`（`0` 违规）

### 3. 独立浏览器子代理实机验收（`7d96d8c2-e991-4d7f-b41f-04d249cc22fb`，全部 `PASS`）
- **宿主核验事实（`BROWSER_HOST_FACTS`）**：访问源 `http://127.0.0.1:5488`，拦截源 `none`，实机截图 `browser_evidence/7d96d8c2-e991-4d7f-b41f-04d249cc22fb/final_step_49.png` 与 `final_step_59.png`。
- **实机验证项**：
  1. `#Home` 周报漏斗与 `#Content` 1:1 对齐：`收录 115 条内容 · 自动折叠 79 条 Shorts 宣传短片 · 精选 31 条必看干货`；历史存档下拉单调递增一致：`最新 · 2026-11-14（31 必看）` / `存档 · 2026-11-13（30 必看）` / `存档 · 2026-11-13（28 必看）`；期次对比条准确显示 `较上期新增提炼 13 篇 · 新增 1 篇必看干货 · 3 项新趋势风向 · 对比上期 2026-11-13`。
  2. `#Content` 搜索过滤后点击 `当前列表标已读 (2)` 立即生效并展示 `已将 2 篇内容标为已读` + `撤销`，点击 `撤销` 后 `未读干货 36` 完整无损还原。
  3. `#Content` 收藏 2 篇视频后点击 `针对已收藏提问 (2)` 直达 `#Research` 并自动激活 `仅限已收藏 (2)` 胶囊，频道来源胶囊准确显示 `OpenAI (22)`、`Greg Isenberg (10)`、`本地实战课 (2)`；随后已将测试收藏还原为 `已收藏 0`，用户生产库零残留污染。
  4. 全程浏览器控制台 `0` 错误、网络 `HTTP >= 400` 响应 `0` 个。

---

## 三、下一轮（Round 7）候选路线图

1. **`P2` 周报与跨视频问答结果的一键结构化导出增强**：支持在 `#Home` 周报演进对比视图中连同“本期较上期新增变化（Delta）”一并复制到 Markdown / 本地知识库草稿，方便团队周会同步。
2. **`P2` 频道来源健康度与干货产出率洞察（Channel Signal-to-Noise Ratio）**：在 `#Following` 订阅页展示各频道“必看干货率 vs Shorts 噪音占比”（如 OpenAI / Greg Isenberg 的有效长视频密度），辅助用户优化关注列表与同步策略。
3. **`P2` `#Research` 历史问答记录（Session History）本地留存与回看**：将高价值跨视频问答结论与引用锚点保存在本地 `hub.sqlite3`，刷新页面或跨日复盘无需重复等待大模型推理。
