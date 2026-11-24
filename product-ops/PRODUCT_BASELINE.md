# 产品与技术基线审计报告（Product Baseline Audit）

- **审计更新日期**：2026-11-24（`Asia/Shanghai`）
- **审计人**：AI 产品负责人（CPO / Market & UX / Tech Lead / QA / Growth & Ops）
- **活跃开发分支 & 公开主线（`main` & `origin/main`）**：`main@4f3fe70`（已执行 `FD-009` 将 Iteration #10 / `BL-013` 全套缺陷修复、实机浏览走查及第 14 组云端 CI 守卫线性合入主线，[`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 双端全绿，无 GitHub Release，仓库保留 4 个历史 tag）
- **当前运营边界**：**内部自主迭代与产品完善阶段**（严格不招募真实外部用户、不发起真人试跑、不把 AI 模拟体验当成真人需求证据）

---

## 一、十维全景接管审计（严格区分事实、推断与假设）

| 审计维度 | 已证实的事实（代码/运行/测试实测） | 合理推断 | 待验证假设 |
|---|---|---|---|
| **1. 产品定位与目标市场** | 代码契约明确 `release_posture: PUBLIC_BETA`（Apache-2.0）、支持 YouTube + B 站 `BV` + 本地音视频(`.mp4/.wav/.mp3/.m4a <=4h`) + 本地 `.md/.txt`，核心能力为本地证据锁死、Fail-Closed 拒答与 Obsidian Markdown 导出；GitHub `huangbuqubunao-alt/intelligence` 当前为 `PUBLIC`（0 Stars / 0 Forks / 0 external PRs）。 | “YouTube 英文原讲 + B 站中文拆解 + 本地 Markdown 同库对比 + Obsidian 深链带出”在中文技术/投研/深度内容消费人群中具备比通用 RAG 更尖锐的场景切口。 | 真人目标用户是否会持续两周以上将其融入 Obsidian 工作流，而不回流免费 Google NotebookLM + 网页总结插件。 |
| **2. 当前功能与核心业务流程** | 端到端链路：`youtube-intel start` 零配置冷启动 / `youtube-intel demo` 离线展示 → 多源入库（SQLite WAL + SHA-256 hash 校验）→ `<180s` 短视频自动折叠 → 本机 Ollama 或显式授权 BYOK 云端提炼（每日预算熔断）→ 按需点击触发本地视频关键帧抽取 + 64 位 dHash 去重 + 原话字幕时间对齐融合分析（Ollama `/api/chat` `images` 或受控 BYOK `low` 图，支持 Lightbox 浏览与带图 `visual-pack.zip` 导出）→ `Research` 混合 FTS5 BM25 跨源问答（`TIME_RANGE` + `TEXT_RANGE` + Fail-Closed `REFUSED_INSUFFICIENT_EVIDENCE`）→ 严格 7 天周报 & 主题演化 → Obsidian `.md`/`.zip` 包导出（带 `https://...?t=`、`ev:` 指纹与 `![[assets/...jpg]]`）。 | 主干“导入→图文融合核验→带走笔记”核心闭环已打通，无需扩展新数据源即具备完整单机研究体验。 | 长周期订阅场景下（追更 10+ 频道）7 日周报与按需关键帧配合使用的每周复看习惯是否成立。 |
| **3. 已完成、未完成与废弃功能** | **已完成**：Iteration #1–#10（含 `BL-011` 关键帧图文融合、`BL-012` Round 19 与 `BL-013` Codex 22 项 + Claude 3 轮复核全套缺陷清零）已全部同步至公开主线 `main@4f3fe70`。<br>**未完成/暂缓**：后台自动全量批量跑视频关键帧 VLM（继续 `DEFER` 防静默消耗）、V2 爬虫（X/网页正文/播客/PDF）、Obsidian 双向监听插件、深研调查工作流（`EarlySignal`/`Investigation`）、团队协作版、打包分发评估（`BL-009`）。<br>**受控冻结/废弃**：默认关闭且 fail-closed 的 `TASK-016` 多模型深研实验链路（`deep_analysis_tier: EXPERIMENTAL`）、历史 `GOV-001` 冻结试跑门禁、自动隐式 `hybrid` 云端切换、原生非 WSL Windows 运行。 | 保持“单视频用户主动点击触发、3–12 帧有界抽取 + `$0` 本地优先”既满足演示/图表类视频痛点，又守住零静默成本防线。 | 团队协同与 Obsidian 插件是否在单机留存成立后真有强需求。 |
| **4. UI/UX 设计与实机交互质量** | Iteration #3–#5 连续闭环首日冷启动、内容详情与首轮引导；Iteration #8 在 `#Content/<id>` `#section-intelligence` 新增双主题响应式关键帧卡片、PPT/讲者筛选与键盘无障碍 Lightbox；Iteration #10 补齐 `#Content` 200+ 分页/全库搜索（含 `>100` 续拉）、`⌘K` 命中截断总数明示、尾段直达聚焦、切专题清除旧锁、IME 保护、Lightbox 焦点归还与同页历史切换；实机 Chromium（`8793` Demo + `8794` 355 条库）桌面/移动双主题 **`0px` 溢出、`0` console error、`0` HTTP `>=400`**。 | 首次体验、多模态图卡可读性与跨页切换一致性均达到内部验收标准。 | 真实首次用户在脱离提示下能否自如完成“引导 → 导入 → 图文抽帧 → 导出”。 |
| **5. 前后端架构** | Python 3.12+ 后端（137 个 `src` `.py` 源文件受 `mypy` 覆盖，`visual_keyframes.py` + `FastReadApiApplication` 关键帧/证据直达/全库检索路由 + `BEGIN IMMEDIATE` 原子计账 + `dir_fd` `O_NOFOLLOW` 安全校验 + 复用 `repo_conn` 保持冷读连接不超限）；React + TypeScript + Vite 前端（`WorkspaceVisualKeyframes` 响应式图卡/Lightbox、`CommandPalette` 全库联动与总数截断提示）；大库分页、全库分块读取与 `include_markdown=False` 列表冷读加速生效。 | 单进程回环静态托管 + Sidecar 隔离图像代数目录（`gen-<uuid>` `0o700`/`0o600`）兼顾极简部署与安全边界。 | 当个人库长期沉淀数百组关键帧包后的本地磁盘占用整理需求。 |
| **6. 数据结构与存储机制** | 双 SQLite 分离：核心事实库 `state.sqlite3` 保持零 Schema 改动；Sidecar AI 库 `.workspace-ai/hub.sqlite3` 维护 `video_visual_analyses` 与 `.workspace-ai/keyframes/<hash16>/gen-<uuid>/`（仅提交成功后切换代数并在单视频锁与提交后回收旧目录）；Iteration #10 备份快照通过 SHA-256 校验打包离线 JPEG 资产并在超出 `40 MiB` 关键帧原图预算或 `64 MiB` JSON 总包预算时分级优雅降级、输出 `skipped_visual_assets` + 告警而完整保留摘要/问答/配置，恢复时主库权威复核（覆盖摘要要点、有据引用与拒答关联片段 `related_excerpts`）并同步重生成 `NEEDS_REVERIFICATION` Obsidian Markdown 与 `.zip` 导出包。 | 分库 + SHA-256 资产校验 + 分级预算降级 + 原子代数切换确保恢复可自闭环、导出必可还原且不漏出未经核验的 Markdown 正文或片段。 | 长期运行生成较多离线图包后的主动清理阈值设计。 |
| **7. 测试覆盖与质量现状** | **公开主线 `main@4f3fe70` 云端与实机全绿**：GitHub Actions [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 双作业 `success`——`Frontend Build & Vitest` `1m37s`（`vite build` `1.37s` + `57/57` / `1257/1257`）、`Python Lint, Typecheck & Public Beta Integration` `5m55s`（`ruff` / `mypy` 137 文件 0 错 + 14 组全量 **`175 passed in 309.20s`**）；本地 16 组 **`202 passed`**，双端口 `8793`/`8794` 实机浏览器全部通过。 | Codex 22 项、Claude 3 轮独立对抗复核与实时实机走查均已完成闭环保护与上云持久守卫。 | 真实外网长视频在多变 `yt-dlp` 字幕与多类型课件画面上的长期效果（待后续观察）。 |
| **8. 技术债与潜在安全风险** | **安全扫描**：`scripts/security_scan.sh` 对新增与修改的源码/前端/测试/`product-ops/` 全部 **0 命中**（仅历史测试哨兵 17 条）。<br>**已核实风险**：① GitHub 仓库维持被动 `PUBLIC` 状态（严守零外宣、无 GitHub Release、本轮未新增发布标签、零招募）；② BYOK 文本/视觉双路派发已统一启用拒绝重定向传输层，本地推理前阻断纯文本模型盲发视觉请求；③ 原生非 WSL Windows 因 `fcntl` 不可用受限（已有运行时错误引导）；④ 外部真人体检指标仍为 0。 | 在内部阶段，最大系统风险已从工程/信任漏洞收敛至“尚缺外部真实留存样本”。 | 待授权转入真人试验后的未知平台接口限流/反爬摩擦分布。 |
| **9. 现有运营与商业化准备情况** | 基础设施已就绪：GitHub `PUBLIC` + Apache-2.0 `LICENSE`/`NOTICE` + `ci.yml` + 每日日报生成器 `scripts/generate_daily_ops_report.py` + 创始人已在 Antigravity 面板启用 21:00 日报自动化侧车；零额外第三方 SaaS 开销。商业化仍停留在方案推演与定价锚点对比期，**无真实付费转化数据**。 | 在未过外部留存门禁前，坚持“Apache-2.0 单机核心免费 + 按工作流效率/团队协同收费假设”比自研计费中台或倒卖 Token 更合理。 | 个人用户对“$\$29\text{–}\$49$ 买断工作流包”与团队席位付费的实际接受度。 |
| **10. 历史开发决策及依据** | `DEC-OPS-001`~`DEC-OPS-014`（涵盖前期闭环、冷启动、Stage D、Iteration #4–#9 合流 `main` 以及 Iteration #10 Codex 审查 15 P1 + 7 P2 缺陷清零）。每次迭代均先核验痛点或实机证据，严控边界不盲目扩线。 | 维持小步快跑、实机验真与严控边界策略有效防止了“功能膨胀却失控消费”。 | 未来何时启动受控真人首测或推进下一轮高优细节打磨。 |

---

## 二、核心用户价值链路（Verification-First Architecture）

```text
[多源采集] YouTube 频道/URL · B站 BV · 本地音视频(<=4h) · 本地 .md/.txt
     │  (Stage D 起：macOS 浏览器支持直接回环上传；SHA-256 哈希落盘与文本切片)
     ▼
[本地优先结构化提炼]
  ├─ 短视频噪声护栏 (<180s 折叠进 Shorts 抽屉)
  ├─ 免费本机 Ollama 默认跑通 (EXP-002 实测 qwen3.5:9b 3/3 有据作答 + 2/2 诚实拒答)
  └─ 可选 BYOK 云端（Keychain 隔离 + 日限额记账 + 变更 Endpoint 强制重认证 + 后台禁跑）
     │
     ▼
[跨源核验与透明拒答]
  ├─ Research Q&A：Video (TIME_RANGE) + Markdown (TEXT_RANGE) FTS5 BM25 混合检索
  ├─ Fail-Closed 门禁：无后端签发 evidence_id 支持即显式拒答 + 相关摘录物理分离
  └─ Offline Demo 同等门禁：词面边界校验，绝不拿固定模板强答越域诡计问题
     │
     ▼
[可携带离线知识资产]
  └─ Obsidian [[wikilinks]] 笔记 / .zip 知识包 / 纯文本提纲
     (含原片 HTTPS ?t= 深链、Markdown P#(start–end) 偏移与 ev: 指纹前缀)
```

---

## 三、外部真实度量与内部验证边界总结

- **真实外部用户数据（DAU / 激活率 / Day-7 留存 / NPS / 真实付费转化）**：**当前不可评估**（项目严格处于**内部自主迭代与产品完善阶段**，严禁私自触达真人用户）。
- **已实际跑通的内部依据**：
  - 全仓静态、构建、CI 单元测试及集成测试 100% 全绿；
  - `EXP-002` 真实本机 `qwen3.5:9b` 双语盲测（非合成 LLM 桩）达成 `100%` 有引用作答与 `100%` 诱导拒答；
  - AI 模拟四类用户旅程（新手首次启动、深度双语研究者、异常对抗与边界输入、移动端响应式 `375×812`）实机通过，最新结果完整登记于 [`TEST_LOG.md`](./TEST_LOG.md)。
