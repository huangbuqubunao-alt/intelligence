# 自主产品诊断、优化与持续迭代状态记录（2026-11-15 Round 3）

- **迭代分支（开发工作区）**：`antigravity/task-user-readiness-20261112`（`/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`，起始基线 `312e867`）
- **正式交付运行区**：`main`（`/Users/hua/Documents/yia-worktrees/v1x-local-main`，起始基线 `5ad0704`）
- **只读对照工作区（严禁修改）**：`codex/readiness-v4-budget-final-validation`（`18f366b`）
- **前置轮次状态**：Round 1（`docs/ITERATION_STATE_2026_11_14.md`）与 Round 2（`docs/ITERATION_STATE_2026_11_15_ROUND2.md`）已 100% 完成并交付。
- **当前阶段**：`ROUND_3_COMPLETED`

---

## 一、第一阶段：Round 3 真实运行态接管与核验基线

直接对 `/Users/hua/Documents/yia-worktrees/v1x-local-main/.var/owner/` 生产库（`state.sqlite3` + `.workspace-ai/hub.sqlite3`）执行只读内存态 API 投射（`FastReadApiApplication.handle`）与全部 7 个核心视图（`#Home`、`#Following`、`#Content`、`#Intelligence`、`#Topics`、`#Research`、`#Settings`）代码审计：

| 模块 / 场景 | 代码实现 | 自动化测试 | 真实用户体验可用性（2026-11-15 05:00） | 真实证据与核心缺口 |
| --- | --- | --- | --- | --- |
| `#Home` 与 `#Intelligence` 洞察收藏闭环 | 后端已实现 | 仅测 POST 请求发包 | **真实 Bug（状态写死 `saved={false}`）** | 生产库 `saved_intelligences = 0`。根因：`App.tsx` 在 `#Home`（`1779` 行）、`#Intelligence` 当前列表（`1923` 行）与 `IntelligenceDetail`（`1857` 行）全部硬编码 `saved={false}`！用户点击 `收藏` 写入 SQLite 后，按钮永远不变为 `取消收藏`，在首页更因 `onSaved={() => undefined}` 毫无状态反馈 |
| `#Home` 右侧 `需要处理 (Needs Attention)` | 已实现 | 已测试 | **假阳性告警与 `#Following` 状态矛盾** | 生产库 `Greg Isenberg` 在 `#Following` 已恢复为 `HEALTHY / COMPLETE` 且 `12/12` 视频已在 `hub.sqlite3` 提炼中文摘要；但因长视频 >20 证据分片触发旧版 `EXECUTION_CONDITION_UNRESOLVED`（`child_states == []`），`_filter_superseded_dashboard_attention` 误判保留，导致首页常驻一条无来源名称、无跳转入口的 `需要处理` 警告 |
| `#Content` 个人阅读分流与归档状态 | 未实现 | 未覆盖 | **缺失高频日用工作流（无已读/收藏）** | `115` 条视频（`46` 条非 Shorts 干货）长期按静态 AI 分数置顶，看完的高分旧视频永远霸占首屏，无法标记 `已读` 或 `收藏待看`，也无法一键筛选 `未读干货` / `已收藏` |
| `#Content` 原始 URL 占位符与状态徽章 | 部分实现 | 部分覆盖 | **视觉噪音与语义误导并存** | 1) `/api/v1/videos` 末尾 3 条 `work_kind: "DURABLE_CONTENT_IDENTITY"` 直播预告/不可用占位项（标题为裸 `https://www.youtube.com/watch?v=...`）因无 `ai_brief` 未被折叠，混在精读列表中；2) 5 条已生成 `简介速览 (METADATA_ONLY)` 的历史无字幕视频右侧仍挂着刺眼的红色 `失败 (Failed)` 状态签，让用户误以为 AI 总结失败 |
| `#Topics` 专题双链笔记导出（MOC） | 未实现 | 未覆盖 | **知识导出闭环缺最后一环** | `#Home` 周报、`#Content` 单视频与 `#Research` 跨视频问答均已支持一键复制/下载 Obsidian `[[双链]]` `.md`，唯独 `#Topics`（已聚合 84 篇 Agent 专题脉络）缺少一键导出专题 MOC 双链笔记与近 7 天活跃度提示 |

---

## 二、第二阶段：六维用户视角深度诊断（Round 3）

1. **产品价值（CPO 视角）**：
   - 信息情报工具从“惊艳演示”走向“每天打开用”的分水岭是**个人阅读状态流转（Triage Loop）**：能把想精读的长视频标为 `收藏待看`、把读完的视频标为 `已读` 并切到 `未读干货` 视图只看增量，同时让 `#Home` / `#Intelligence` 的洞察收藏按钮真正反映持久化状态。
2. **用户体验（UX/UI 视角）**：
   - 首页右侧出现无法定位来源的 `需要处理`，点去 `#Following` 却全是绿色 `来源检查正常`，极大消耗用户信任；
   - `#Content` 列表同时显示 `7.5 · 简介速览` 与 `失败`，以及裸露 3 条 `https://www.youtube.com/watch?v=...` 占位链接，破坏了精读工作台的整洁度与诚实语义。
3. **技术质量（CTO 视角）**：
   - 坚持 **Sidecar 零侵入扩展**：阅读状态存储于 `.workspace-ai/hub.sqlite3` 新增表 `video_curation_states`，严禁改动密封 `state.sqlite3` Schema；
   - 消除客户端请求瀑布流（Vercel React Best Practices `async-`）：首页洞察收藏状态随 `/api/v1/dashboard`（`has_sidecar_db()` 门控下）一次性带回 `saved_intelligence_ids`，零额外首屏串行请求，且 100% 保持后端持久化真值驱动。
4. **功能完整性（QA 视角）**：
   - 修复 `App.tsx` 三处 `saved={false}` 硬编码缺陷，让 `Save -> Unsave` 在 `#Home`、`#Intelligence`（当前/已收藏双 Tab）全链路闭环；
   - 新增的 `video_curation_states` 同步纳入 `/workspace-ai/backup` 与 `/workspace-ai/restore`（向后兼容旧版 `workspace-ai-backup-v1` 快照文件）。
5. **行业与竞品（Market 视角）**：
   - 对标 Readwise Reader / Feedbin 的高频 `Inbox / Unread / Starred` 极简分流体验，以及 Heptabase / Obsidian 用户的 Topic MOC（Map of Content）一键导出工作流。
6. **商业与长期价值（Growth 视角）**：
   - 用户在本地沉淀的“精选收藏 + 已读轨迹 + 专题 MOC 笔记”越丰富，产品的个人第二大脑粘性与复利价值越高。

---

## 三、第三阶段：Round 3 迭代优先级矩阵与“不做/简化”裁定

| 优先级 | 任务项 | 解决的具体问题 & 用户场景 | 成本 / 风险 | 验证成功方法 |
| --- | --- | --- | --- | --- |
| **P1** | **R3-1. 修复 `#Home` / `#Intelligence` 洞察收藏状态 Bug + 新增 `#Content` 视频 `收藏待看 / 标记已读` 个人分流闭环（含备份恢复兼容）** | 修复三处 `saved={false}` 硬编码 Bug；在 Sidecar `hub.sqlite3` 实现 `video_curation_states` 持久化，支持 `#Content` 列表与详情页一键切换 `收藏` / `已读` 及 `未读干货` / `已收藏` 过滤 | 中 / 低风险 | Pytest 状态切换与快照往返测试 + Vitest 收藏/已读交互回归 + 真实浏览器跨页面验证 |
| **P1** | **R3-2. `#Home` 已接管来源假阳性 `需要处理` 告警收敛 + `#Content` 无字幕诚实状态徽章与原始链接占位符自动收纳** | 消除 `Greg Isenberg` 已健康且全量提炼后仍在首页残留的 `EXECUTION_CONDITION_UNRESOLVED` 幽灵警告；将已生成 `简介速览` 视频的 `失败` 徽章修正为诚实的 `无原生字幕`；自动折叠 `DURABLE_CONTENT_IDENTITY` 裸 URL 占位项 | 低 / 低风险（严格保留活跃子任务告警与无 Sidecar 原始契约） | Pytest 告警收敛边界测试 + Vitest 全量 49 文件回归 + 真实浏览器首屏核验 |
| **P1** | **R3-3. `#Topics` 专题 MOC Obsidian `[[双链]]` Markdown 一键导出 + 近 7 天活跃增量提示** | 补齐四大知识消费面最后一处 Markdown 双链导出缺口，支持一键复制专题 MOC 双链笔记与下载 `.md`（纯浏览器剪贴板/下载，零外部 Vault 写入） | 低 / 低风险 | Pytest `enrich_topic_detail_dto` Markdown 契约测试 + Vitest + 真实浏览器导出预览核验 |
| **P3** | 多级文件夹嵌套收藏夹 / 拖拽看板（Kanban） | 过度复杂的阅读器管理 | 中 / 徒增认知负担 | **明确不做**（保持 `未读干货 / 已收藏` 单层轻量高频分流） |

### 明确识别：哪些不值得做、哪些设计应该简化

1. **坚决不做**：
   - 不做多级收藏夹目录树、自定义颜色标签系统或拖拽看板——对情报阅读器而言，`未读干货` + `必看长视频` + `已收藏` 单层筛选芯片配合行内一键 `收藏 / 已读` 是操作阻力最低的黄金组合；
   - 不触碰任何密封门禁模块、不修改 `state.sqlite3` Schema、不写入外部真实 Obsidian Vault、不新增任何第三方依赖。
2. **果断简化与收纳**：
   - `#Content` 默认视图自动将 `work_kind === "DURABLE_CONTENT_IDENTITY"` 的未开播/不可用裸链接占位项收纳进底部折叠抽屉，不在首屏精读流制造故障感；
   - `METADATA_ONLY` 视频用平实准确的 `无原生字幕` 替代惊悚的 `失败`，消除与 `简介速览` 卡片的语义冲突。

---

## 四、第四阶段：小批次 TDD 执行进度记录

- [x] **Step 0**：完成生产库全表与内存 API 投射审计、定位 3 处 `saved={false}` 硬编码 Bug 与 `EXECUTION_CONDITION_UNRESOLVED` 空子任务漏网根因，建立本状态记录
- [x] **Slice 1（后端 TDD）**：`video_curation_states` 持久化与 `/workspace-ai/videos/<id>/curation` 路由、备份恢复往返兼容、`enrich_topic_detail_dto` 专题 MOC `obsidian_markdown` 与 `recent_7d_count`、`/api/v1/dashboard` `saved_intelligence_ids` 与已全量提炼来源的 `EXECUTION_CONDITION_UNRESOLVED` 过滤（27/27 Pytest 通过，Ruff 0 error，Mypy 0 issue）
- [x] **Slice 2（前端 TDD）**：`#Home` / `#Intelligence` 真实持久化收藏状态联动、`#Content` 列表与详情页 `收藏 / 已读` 控制与 `未读干货 / 已收藏` 筛选 + `无原生字幕` 诚实标签 + 裸链接占位折叠、`#Topics` 专题 MOC 双链导出按钮与预览抽屉（49/49 Vitest 文件共 1,196 项测试全绿、`tsc + vite build` 零报错、`impeccable detect` 0 违规）
- [x] **Slice 3（正式环境部署与独立 Browser Subagent E2E 验收）**：同步至 `v1x-local-main`、重建 `.var/Intelligence.app` 与 `build-provenance.json`、独立 `browser` 子代理（`d68ad577-56c8-4b9c-8154-65906709b25c`）完成跨页面真实点击与截图核验（`final_step_43.png`、`final_step_53.png`）

---

## 五、第五阶段：独立真实验收证据汇总（Round 3）

| 验收项 | 状态 | 真实客观证据 |
| --- | --- | --- |
| 后端集成与启动器契约（Pytest） | **PASS** | `tests/integration/test_workspace_intelligence_hub.py` + `tests/unit/test_owner_launcher.py`：**25/25 passed**；`tests/integration/test_fast_read_api.py`（无 Sidecar 字节级兼容与连接/延迟预算）：**2/2 passed** |
| Python 静态检查（Ruff + Mypy） | **PASS** | `ruff check`：`All checks passed!`；`mypy`：`Success: no issues found in 2 source files` |
| 前端全量回归测试（Vitest） | **PASS** | **49/49 test files, 1,196/1,196 tests passed**（含新增 3 组 Round 3 TDD 用例，共 14 项 `WorkspaceIntelligenceHub.test.tsx` 全绿） |
| 前端生产构建与视觉检测 | **PASS** | `tsc -b && vite build`：exit `0`（`658ms`）；`impeccable detect --json`：`[]`（0 违规） |
| 真实浏览器 E2E 交互核验（`http://127.0.0.1:5488`） | **PASS** | 宿主核验（`BROWSER_HOST_FACTS`）：`#Home` 幽灵 `需要处理` 告警彻底消失、`收藏 -> 取消收藏` 与 `#Intelligence`（当前/已收藏双 Tab）跨页实时同步；`#Content` 6 枚分流芯片、行内 `收藏 / 标已读` 切换、`无原生字幕` 替代误导性 `失败`（全列表 0 个 `失败` 徽章）、79 条 Shorts 与 3 条未开播占位链接自动折叠；`#Topics` 展示 `近7天 +13` 并完成专题 MOC `[[wikilinks]]` Markdown 复制与预览；全程 `0` Console Error、`0` HTTP >= 400（真机截图：`final_step_43.png`、`final_step_53.png`） |

---

## 六、第六阶段：可恢复接续状态与下一轮路线（Round 4 候选）

1. **当前停止条件达成**：Round 3 确定的全部高价值 P1 任务（`R3-1` 洞察与视频个人收藏/已读分流闭环、`R3-2` 首页假阳性告警收敛与内容列表诚实标签/占位收纳、`R3-3` 专题 MOC 双链笔记导出）已 100% 完成并通过自动化与真实浏览器验收。
2. **下一轮（Round 4）候选方向**（按实际使用反馈择优启动）：
   - **R4-1（P2）**：`⌘K` 全局命令面板支持快速检索 `已收藏` 视频与按中文一句话结论模糊直达，进一步缩短高频复盘路径；
   - **R4-2（P2）**：`#Home` 周报支持历史周次切换下拉（对比上周与本周趋势演进，复用 `weekly_ai_briefs` 既有历史表，零 Schema 破坏）；
   - **R4-3（P2）**：当用户在 `#Content` 详情页阅读完长视频或复制双链笔记后，提供轻量的“顺手标为已读并返回未读列表”快捷动线。
