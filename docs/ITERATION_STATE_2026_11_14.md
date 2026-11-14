# 自主产品诊断、优化与持续迭代状态记录（2026-11-14 Round 1）

- **迭代分支（开发工作区）**：`antigravity/task-user-readiness-20261112`（`/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`，起始基线 `3dc8fbd1f90e346b4c04f6cf2cd1aa6eacc1db80`）
- **正式交付运行区**：`main`（`/Users/hua/Documents/yia-worktrees/v1x-local-main`，起始基线 `71557160505f03ce2075655bb0dcb7809b9e0fa3`）
- **只读对照工作区（严禁修改）**：`codex/readiness-v4-budget-final-validation`（`18f366b80e9f184795e44d7716f49d0ac418fb7f`）
- **当前阶段**：`ROUND_1_COMPLETED`（全部 P0/P1 目标已完成开发、测试、生产库 115/115 回填、独立浏览器真实验收及现场问题闭环修复，可随时无缝衔接 Round 2）

---

## 一、第一阶段：真实现状核验基线（区分已实现 / 已测试 / 真实可用 / 尚未闭环）

| 能力模块 | 代码状态 | 自动化测试 | 真实运行可用性核验（2026-11-14 23:31） | 证据与缺口说明 |
| --- | --- | --- | --- | --- |
| 本地优先中文摘要 + 0-10 分 + Shorts 折叠 | 已实现 | 已测试（Pytest + Vitest） | **部分闭环（102/115）** | `.var/owner/` 共 `115` 条视频，其中 `102` 条已生成中文摘要；但后台新抓取的 **3 条带字幕 OpenAI 新视频**（含 20 分钟 `GPT-6 Cyber` Firefox 漏洞修复深度访谈 `PkAmyub12K8`）与 **10 条无字幕 `METADATA_READY` 视频**未自动触发摘要，导致内容流顶部最新 3 条仍是英文裸标题、2 条新 Shorts 混入主列表 |
| 本地 `.mp4` 课程 Apple Silicon MLX 转写 | 已实现 | 已测试 | **真实可用（3/3 完结）** | `_FastOfflineMlxLectureTranscriber` 单通 ~18x 实时速度已完成 3 门 84–95 分钟中文 AI 课转写与提炼 |
| 一页纸《本周 AI 产品与商业情报周报》 | 已实现 | 已测试 | **真实可用** | 首页直接渲染高信噪比周报与必看清单，支持一键导出 Obsidian `[[wikilinks]]` Markdown |
| 跨视频带时间戳中文问答（`#Research`） | 已实现 | 已测试 | **可用但存在入口深与中英跨语种检索短板** | 1) `#Research` 不在顶部导航，只能从洞察卡片深层点入；2) `_tokenize_query` 纯字面重合检索在“中文提问 → 英文原话字幕（如 Firefox / vulnerability）”且视频尚未生成中文摘要或关键词未对齐时召回偏弱 |
| 首页告警与设置页心智统一 | 部分实现 | 已测试 | **存在双轨割裂噪音** | 1) 首页 `needs_attention` 仍展示昨天已解决且所有子任务已终态的 `Greg Isenberg (EXECUTION_CONDITION_UNRESOLVED)` 历史幽灵告警；2) `#Settings` 在新双轨 `Ollama qwen3.5:9b` 下方直接平铺旧版 `qwen3:8b 质量验收未通过` 等工程诊断面板，造成严重认知冲突 |
| 重启后自愈与本机推理守护 | 部分实现 | 部分测试 | **存在重启断流缺口** | 宿主机重启后，不仅 `:5488/:5489` 停止，本机 `ollama serve`（`:11434`）也处于未启动状态；`owner_launcher.py` 未自动拉起或预检本机 Ollama，且新抓视频缺少后台自动增量摘要守护线程 |
| 核心备份恢复与 Sidecar 知识资产保护 | 核心已实现 | 已测试 | **Sidecar 缺少独立快照备份** | `BackupRestoreService` 已验证 `201 Created`，但为遵守核心备份白名单，`.workspace-ai/hub.sqlite3` 位于 `data/` 之外，尚缺一键 JSON 快照备份/恢复与自动滚动快照 |

---

## 二、第二阶段：六维用户视角诊断摘要

1. **产品价值**：高信噪比漏斗（`0-10` 分 + Shorts 自动折叠 + 一页纸周报）精准命中创作者/产品经理“订得多看不过来”痛点；但**增量自动化闭环未彻底打通**——一旦后台抓到新视频却还要手动点提炼，产品就会退化为“一次性脚本”而非“全天候情报助手”。
2. **用户体验**：
   - 首页顶部的历史幽灵告警（`Greg Isenberg: EXECUTION_CONDITION_UNRESOLVED`）削弱产品信任感；
   - 内容流顶部出现未提炼英文新视频与未折叠无字幕 Shorts（如 15 秒 Messi 广告片），破坏第一眼整洁度；
   - `#Research` 跨视频问答作为高价值杀手锏却藏在二级页面深处；
   - 设置页新旧两套 AI 模型状态同屏打架。
3. **技术质量**：`FastReadApiApplication` 单快照缓存将热读压缩至 `<15ms`，架构干净；但跨视频检索仅靠表层字面切词，未使用 SQLite 原生 `FTS5` 与中英双语术语扩展。
4. **功能完整性**：10 条 YouTube 官方无字幕视频（`METADATA_READY`，含 6 条 `15s-49s` 预热短片和 4 条带官方简介视频）此前直接报 `409 TRANSCRIPT_REQUIRED`，既不能折叠进 Shorts 抽屉，也没有诚实的“基于标题与官方简介速览”。
5. **行业与竞品**：相比 Readwise Reader / NotebookLM / Glasp，本产品核心壁垒是 **Apple Silicon 本地零成本私密推理 + 跨视频时间戳原话级溯源 + Obsidian 双链无缝导出**。补齐后台增量自动提炼与双语混合检索后，日常留存体验将跃升一个台阶。
6. **商业与长期价值**：本地零边际成本体验是最佳获客漏斗，云端 BYOK 与可恢复知识资产备份是长期留存基石。

---

## 三、第三阶段：迭代优先级清单与“不做/精简”裁定

### 候选优先级矩阵

| 优先级 | 任务项 | 解决的用户问题 | 实施复杂度 / 风险 | 验证方法 |
| --- | --- | --- | --- | --- |
| **P0** | **1. 全覆盖增量 AI 闭环 + 后台自动同步守护 + Ollama 启动自愈**（支持有字幕精炼 + 无字幕诚实简介速览 `METADATA_ONLY` + `serve-api` 后台自动同步 + `owner_launcher.py` 自动检测拉起 `ollama serve`） | 彻底消灭“新抓视频变回英文裸标题、无字幕 Shorts 污染主列表、重启后本机 AI 失联”三大断链痛点 | 中 / 低风险（`METADATA_ONLY` 严格标记 `source_basis="METADATA_ONLY"`，绝不伪造字幕时间戳或污染 `intelligences` 权威表） | Pytest 增量同步与无字幕边界测试 + 真实将 `.var/owner` 全部 **115/115** 视频 100% 提炼入库 |
| **P1** | **2. 认知减负与幽灵告警清理（UI 精简收敛）**（清理已被新全局关注规则取代的历史终态 `EXECUTION_CONDITION_UNRESOLVED` 首页告警；`#Settings` 将旧版工程资质面板收纳进高级折叠抽屉；详情页消除双份摘要重复展示） | 打开首页零误报、打开设置页一眼看懂当前 AI 引擎、打开详情页只读一份权威中文结论 | 低 / 低风险（仅在 `workspace_ai` 激活时折叠旧面板，100% 保持全部 49 个既有前端测试零回归） | Pytest Dashboard 过滤测试 + Vitest 全量 49 文件 + 真实浏览器走查 |
| **P1** | **3. 跨视频双语混合检索（SQLite `FTS5` + 中英术语扩展）+ 顶栏 & `⌘K` 一键直达 `#Research` + Sidecar 知识快照备份** | 中文提问也能精准命中英文底层技术视频原话（如问中文“浏览器安全漏洞修复”直达 `GPT-6 Cyber` Firefox 原话时间戳）；任何页面一键唤起跨视频问答；AI 摘要与问答记录可一键备份恢复 | 中 / 低风险（零外部 PyPI/npm 新增依赖，纯标准库 SQLite `FTS5`） | Pytest 跨语种检索与快照恢复测试 + Vitest + 真实浏览器端到端提问验证 |
| **P2** | 4. 主题页时间线演化对比视图与多选视频定向对比问答 UI | 帮助深度研究者对比同一话题前后观点变化 | 中 / 低 | 留作下一轮候选 |
| **P3** | 5. 浏览器插件 / 移动端适配 / 多用户协作 | 扩展采集入口 | 高 / 高偏离风险 | 当前明确不做 |

### 明确识别：哪些不值得做、哪些隐藏/简化

1. **坚决不做（拒绝过度工程）**：
   - 不引入外部重量级向量数据库（Chroma / Qdrant / FAISS）或新 PyPI/npm 依赖——100~1000 条个人视频库规模下，SQLite `FTS5` + 双语词表扩展毫秒级响应且零运维负担；
   - 不对无字幕 YouTube 视频偷偷触发 `yt-dlp` 音频抓取（严格遵守项目安全边界与版权/风控红线），而是诚实提供标注 `基于标题与官方简介速览` 的元数据级中文摘要与噪音折叠；
   - 不改动第 7 个主导航按钮（遵守 `DESIGN.md` 6 主导航键盘无障碍契约），改用顶栏工具区快捷入口 + `⌘K` 命令面板直达 `#Research`。
2. **果断隐藏/简化（消除开发者视角噪音）**：
   - 当 `workspace_ai` 启用时，将 `#Settings` 中令普通用户困惑的旧版 `qwen3:8b 质量验收未通过 / 本地转写能力 FAILED / 受控云端账单资格` 折叠进底部 `<details>` 高级诊断区；
   - 当视频已有 `ai_brief` 时，折叠详情页底部旧版英文抽取式 `note.v2` 重复卡片，避免两套摘要上下打架；
   - 自动过滤已被新 `focus_rules` 解决且子项已全部终态的历史 `EXECUTION_CONDITION_UNRESOLVED` 幽灵告警。

---

## 四、第四阶段：小批次执行进度记录

- [x] **Step 0**：核验仓库分支、Git 状态、宿主机进程与 `.var/owner` 真实库状态（`115` 视频，`102` 已提炼，`13` 待同步），落盘本状态文件
- [x] **Slice 1（后端 TDD）**：无字幕 `METADATA_ONLY` 诚实速览、`sync_pending_videos` + 后台守护同步线程、SQLite `FTS5` 双语检索、Dashboard 幽灵告警过滤、Sidecar 快照备份恢复、`owner_launcher.py` Ollama 自愈启动（验证：`test_workspace_intelligence_hub.py` + `test_owner_launcher.py` 20 passed，`test_fast_read_api.py` 1 passed，Ruff & Mypy 0 errors）
- [x] **Slice 2（前端 TDD）**：顶栏 `AI 跨视频问答` 按钮 + `⌘K` 命令面板直达、`#Settings` 旧版工程面板折叠收纳 + Sidecar 备份导出按钮、内容列表增量同步状态条与 `基于标题与官方简介速览` 诚实徽标（验证：全量 49 文件 `1190 passed`，`tsc -b && vite build` 成功，`impeccable detect` 0 违例）
- [x] **Slice 3（生产同步与独立真实验收）**：同步至 `v1x-local-main`、完成全部 **115/115** 视频中文提炼（105 条有字幕精炼 + 10 条无字幕诚实速览）与最新 115 条全量周报更新、启动 `:5488/:5489` 常驻服务、执行独立 Browser E2E 五大链路验收，并闭环修复真实验收捕获的 2 项现场细节（`DURABLE_CONTENT_IDENTITY` 占位行误触发同步条与 `1970` 空日期回退、`#Settings` 折叠抽屉按需懒挂载消除 `/local/transcription/capability` 500 噪音）

---

## 五、第五阶段：独立验收结论与下一轮接续点（Round 2 Ready）

- **自动化门禁结果（PASS）**：
  - Python：`test_workspace_intelligence_hub.py` + `test_owner_launcher.py` `20 passed`；`test_fast_read_api.py` `1 passed`；`ruff check` 0 errors；`mypy` 0 issues。
  - Frontend：全量 `49 passed` 测试文件（`1190 passed` 用例）；`tsc -b && vite build` 零报错；`impeccable detect --json` `[]`（0 违例）。
- **生产库与备份门禁（PASS）**：
  - `.var/owner/`：`total_videos = 115`，`briefed_count = 115`，`pending_count = 0`；首页 `needs_attention = []`；核心备份 `POST /api/v1/backup-restore/backups` 返回 `201`；Sidecar 快照 `GET /api/v1/workspace-ai/backup` 返回 `200`（含 115 条摘要，零密钥）。
- **独立浏览器 E2E 验收（PASS）**：
  - 现场验证截图：`final_step_49.png`（`#Home` 周报与快捷栏）、`final_step_71.png`（`#Content` 零误报横幅与 9.2 排序列表）；`#Research` 中文提问直达英文 `PkAmyub12K8` 时间轴原话 `[E1] 06:23`；`#Settings` 28 个请求全部 `200 OK`、零 `500` 报错。
- **下一轮（Round 2）按价值排序候选**：
  1. **首选推荐（最高 ROI）**：在 `#Research` 增加“限定频道 / 主题 / 多选视频范围”的定向对比提问器（让用户可一键对比某 2–3 个竞品视频或本地课章节的异同）。
  2. **次选（P2）**：在 `#Topics` 主题详情页合入按发布时间排序的“观点演进对比卡片”，直观展示同一主题在数周内的技术/商业判断变化。
  3. **第三候选（P2）**：针对创作者抓取遇到临时网络波动（如 `Greg Isenberg` 偶发代理超时），提供带指数退避的后台静默重试状态提示与一键单源重检快捷入口。
