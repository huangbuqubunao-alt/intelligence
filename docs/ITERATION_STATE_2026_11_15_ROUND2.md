# 自主产品诊断、优化与持续迭代状态记录（2026-11-15 Round 2）

- **迭代分支（开发工作区）**：`antigravity/task-user-readiness-20261112`（`/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`，起始基线 `8569b78`）
- **正式交付运行区**：`main`（`/Users/hua/Documents/yia-worktrees/v1x-local-main`，起始基线 `74c275f`）
- **只读对照工作区（严禁修改）**：`codex/readiness-v4-budget-final-validation`（`18f366b`）
- **前置轮次状态**：Round 1 已 100% 完成并验收（`docs/ITERATION_STATE_2026_11_14.md`，生产库 `115/115` 视频中文摘要全覆盖、Shorts 噪音自动折叠、一页纸周报、SQLite `FTS5` 跨语种检索、后台增量自动同步守护）。
- **当前阶段**：`ROUND_2_IN_PROGRESS`

---

## 一、第一阶段：Round 2 真实运行态接管与核验基线

基于 `/Users/hua/Documents/yia-worktrees/v1x-local-main/.var/owner/` 真实生产库（`state.sqlite3` + `.workspace-ai/hub.sqlite3`）与前端全部 7 个核心视图（`#Home`、`#Following`、`#Content`、`#Intelligence`、`#Topics`、`#Research`、`#Settings`）代码审计：

| 模块 / 场景 | 代码实现 | 自动化测试 | 真实用户体验可用性（2026-11-15 03:15） | 真实证据与核心缺口 |
| --- | --- | --- | --- | --- |
| `#Home` 周报与置顶专题栏 | 已实现 | 已测试 | **周报优秀，但置顶专题栏信息密度低** | 周报展示 `115` 条漏斗与必看精选；但右侧 `置顶专题 (Pinned Topics)` 仅显示标题 + `单来源`，看不到每个专题沉淀了多少条内容与核心结论 |
| `#Topics` 专题列表与详情页 | 仅底层骨架 | 基础测试 | **体验断层（空壳重复文案）** | 生产库已有 4 个置顶中文专题（`AI Agent 与自动化架构` 84 篇、`AI 产品机会与一人公司变现` 18 篇、`大模型演进与多模态实战` 9 篇、`开发者工具与工程效能` 4 篇）和 35 条关联；但点进任一专题，`证据` 区连续重复 15 遍完全相同的机械套话 `“一条当前内容支持此专题。”` + 裸 UUID，**无视频标题、无中文结论、无评分、无法点击跳转视频**，`时间线` 只有日期无内容 |
| `#Research` 跨视频深度问答 | 已实现全库检索 | 已测试 | **缺定向范围对比 + 新旧文案左右互搏** | 1) 只能笼统检索全库 115 条视频，无法按**特定频道/来源**（如只看 `Greg Isenberg` 或只看 `本地实战课`）、按**专题**或**勾选 2–5 个具体视频**做头对头对比；2) 后端已生成并入库 `action_items_zh`（下一步行动建议），前端却漏渲染；3) AI 问答面板正下方紧跟着旧版提示 `“研究仅使用你现有的资料库，不进行网页探索，也不调用模型 / 暂无研究”`，造成严重认知冲突 |
| `#Settings` AI 知识快照备份/恢复 | 导出已接 UI，恢复仅 API | API 已测 | **半闭环（缺 UI 一键恢复入口）** | Round 1 已实现 `/workspace-ai/backup` 与 `/workspace-ai/restore` 并在 `#Settings` 提供 `导出 AI 知识库快照 (.json)`，但界面尚无配套的 **`导入并恢复快照 (.json)`** 按钮，用户在界面内无法独立完成恢复闭环 |
| `#Following` 创作者健康度与恢复 | 详情弹窗内可重试 | 已测试 | **列表行恢复路径过深** | `OpenAI` 状态 `HEALTHY`（100 条已入库），而 `Greg Isenberg` 因前序偶发网络抖动处于 `OFFLINE`（退避等待中）；在 `#Following` 列表行上只有 `暂停关注` 和 `打开来源`，没有**一键 `立即重检`**，用户必须点进二级弹窗再翻到底部才能触发重试 |
| `owner_launcher.py` Ollama 自愈 | 已支持 brew 路径 | 已测试 | **缺 macOS `Ollama.app` 内置二进制兜底** | 当前候选路径为 `/opt/homebrew/bin/ollama` 与 `/usr/local/bin/ollama`；若用户直接拖拽安装 `/Applications/Ollama.app` 且未创建 `/usr/local/bin` 软链，则无法自动拉起守护进程 |

---

## 二、第二阶段：六维用户视角深度诊断（Round 2）

1. **产品价值（CPO 视角）**：
   - Round 1 解决了“内容进得来、噪音折得起、全库能提问”；Round 2 必须攻克**“结构化知识沉淀与定向对比决策”**——用户把 115 条视频沉淀进 4 大专题后，点开 `#Topics` 应该立刻看到按时间演进的中文高分观点脉络与产品启发，并能一键带着该专题跳去 `#Research` 深度追问，而不是面对 15 行 `“一条当前内容支持此专题”` 的工程占位符。
2. **用户体验（UX/UI 视角）**：
   - **消除精神分裂文案**：`#Research` 上半屏是“AI 跨视频深度问答”，下半屏却写“不调用模型 / 暂无研究”，必须将传统手工证据包收纳进底部折叠抽屉。
   - **缩短高频恢复路径**：`#Following` 对处于 `OFFLINE / PROVIDER_ERROR / RATE_LIMITED` 的关注源直接在列表行提供一键 `立即重检`；`#Settings` 补齐一键 `导入并恢复快照 (.json)`。
3. **技术质量（CTO 视角）**：
   - 所有新增能力继续坚持 **Sidecar 无侵入富化模式**（`has_sidecar_db()` 为假时 `/api/v1/topics` 与 `/api/v1/dashboard` 保持 100% 原始契约，确保密封测试零回归）。
   - `research_qa_sessions` 通过幂等列迁移新增 `scope_json`，前向/后向完全兼容 JSON 备份与恢复。
4. **功能完整性（QA 视角）**：
   - 后端早已计算并落盘 `action_items_zh`，前端漏展示属于典型“做了一半未闭环”，本轮直接打通展示。
   - AI 知识库快照补齐前端文件选择、Schema 校验、`POST /workspace-ai/restore` 调用与成功计数反馈，形成完整备份-恢复闭环。
5. **行业与竞品（Market 视角）**：
   - NotebookLM 的核心优势是“勾选指定 Source 集合做定向对话”；Readwise / Heptabase 的优势是“主题时间线聚合”。本轮在 `#Research` 补齐**来源/专题/多选视频定向范围对比** + 在 `#Topics` 补齐**时间轴观点演进流与一键专题提问**，在纯本地零成本前提下补齐对标 NotebookLM 的关键交互拼图。
6. **商业与长期价值（Growth 视角）**：
   - 当用户的专题页随每周新视频自动生长出带评分、带商业切口的演化时间线，且所有 AI 资产可一键导出/导入 JSON 快照时，迁移成本与长期复利效应显著增强。

---

## 三、第三阶段：Round 2 迭代优先级矩阵与“不做/简化”裁定

### 候选任务优先级评估

| 优先级 | 任务项 | 解决的具体问题 & 用户场景 | 成本 / 风险 | 验证成功方法 |
| --- | --- | --- | --- | --- |
| **P1** | **R2-1. `#Research` 定向范围对比问答工作台 + 行动建议透出 + 旧版冲突文案折叠** | 支持按频道（`OpenAI` / `Greg Isenberg` / `本地实战课`）、按专题或勾选多条视频做精准对比提问；展示 `下一步可执行动作`；折叠底部 `不调用模型` 冲突空状态 | 中 / 低风险 | Pytest 范围过滤与多视频对比测试 + Vitest 全量回归 + 真实浏览器定向提问验收 |
| **P1** | **R2-2. `#Topics`（及 `#Home` 置顶专题）AI 观点演进时间线富化 + 一键围绕专题提问** | 彻底终结 `#Topics` 详情页重复 15 遍 `一条当前内容支持此专题` 的无效体验，展示各专题收录数、必看数、按时间倒序的中文核心结论卡片、视频一键直达与 `围绕本专题跨视频提问` 联动按钮 | 中 / 低风险（`has_sidecar_db()` 门控，零破坏原有契约） | Pytest `/api/v1/topics` 富化与契约对等测试 + Vitest + 真实浏览器从 `#Topics` 联动跳 `#Research` |
| **P1** | **R2-3. `#Settings` AI 知识库快照一键导入恢复 UI + `#Following` 异常源列表行一键重检 + `Ollama.app` 路径兜底** | 闭合 UI 内备份导出/导入恢复全链路；让 `Greg Isenberg` 等网络抖动源在列表页一键重检恢复；兼容 `/Applications/Ollama.app` 原生路径 | 低 / 低风险 | Pytest 快照恢复含 `scope_json` & Launcher 路径测试 + Vitest 文件导入恢复测试 + 真实浏览器验证 |
| **P3** | 跨工作区云同步 / 浏览器扩展剪藏 / 多人群组共享 | 跨设备协作 | 高 / 超出单机私密定位 | **明确不做** |

### 明确识别：哪些不值得做、哪些设计应该简化

1. **坚决不做**：
   - 不在 `#Topics` 引入复杂的知识图谱力导向 Canvas（Force-Directed Graph）——对 4~20 个专题而言，清晰的“高分代表作 + 按时间演进观点卡片 + 一键跳专题问答”信息获取效率远高于花哨但难读的节点连线图；
   - 不修改核心 `topics` / `topic_memberships` SQLite Schema，也不触碰任何密封质量门禁模块；
   - 不增加任何第三方 npm/PyPI 依赖。
2. **果断简化与收纳**：
   - `#Research`：当 Workspace AI 引擎就绪且无旧版手工包时，将旧版 `不调用模型 / 新建研究 / 暂无研究` 收纳进底部 `<details>` 折叠区，消除首屏左右互搏；
   - `#Topics` 详情页：当存在富化中文演进条目时，直接首屏呈现可点击阅读的中文观点演进流，将充满机械重复句与裸 UUID 的旧版技术贡献明细折叠至底部 `<details>` 溯源抽屉。

---

## 四、第四阶段：小批次 TDD 执行进度记录

- [x] **Step 0**：完成 `.var/owner` 全表核验、UI 7 大页面源码审计与 Round 2 迭代状态建档
- [x] **Slice 1（后端 TDD）**：`ask_research_question` 来源/专题/多视频定向对比 + `scope_options` + `scope_json` 持久化与备份兼容、`enrich_topics_list_dto` / `enrich_topic_detail_dto` 专题演进富化、`owner_launcher.py` `Ollama.app` 路径兜底（`ruff` + `mypy` 0 错误，`24/24` Pytest 全绿）
- [ ] **Slice 2（前端 TDD）**：`WorkspaceAiResearchPanel` 范围筛选与多视频对比选择器 + `action_items_zh` 渲染、`Research.tsx` 旧版冲突文案折叠、`Topics` 演进时间线与一键专题提问联动、`WorkspaceAiSettingsPanel` 一键导入恢复 JSON 快照、`#Following` 异常源行内一键重检
- [ ] **Slice 3（生产同步与独立真实验收）**：Cherry-pick 至 `v1x-local-main`、重建前端与启动器、重启 `:5489` API 服务、重检恢复在线源、独立 Browser E2E 全链路走查验收并封板提交
