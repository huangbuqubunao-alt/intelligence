# 产品与技术基线审计报告（Product Baseline Audit）

- **审计更新日期**：2026-11-23（`Asia/Shanghai`）
- **审计人**：AI 产品负责人（CPO / Market & UX / Tech Lead / QA / Growth & Ops）
- **活跃开发分支**：`antigravity/task-user-readiness-20261112`（领先 `main@4d24df4` 含 Iteration #9 / `BL-012` Round 19 易用性与自检可读性打磨，**待创始人按 L3 裁决合流 `main`**）
- **公开主线对照基线（`main` & `origin/main`）**：`4d24df449e346bb5bc65070ca571f364b851ead1`（已按 `FD-007` 同步 Iteration #8 / `BL-011` + 13 组 CI 接线，GitHub Actions [`#45201809374`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45201809374) & [`#45206505478`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45206505478) 双端全绿）
- **当前运营边界**：**内部自主迭代与产品完善阶段**（严格不招募真实外部用户、不发起真人试跑、不把 AI 模拟体验当成真人需求证据）

---

## 一、十维全景接管审计（严格区分事实、推断与假设）

| 审计维度 | 已证实的事实（代码/运行/测试实测） | 合理推断 | 待验证假设 |
|---|---|---|---|
| **1. 产品定位与目标市场** | 代码契约明确 `release_posture: PUBLIC_BETA`（Apache-2.0）、支持 YouTube + B 站 `BV` + 本地音视频(`.mp4/.wav/.mp3/.m4a <=4h`) + 本地 `.md/.txt`，核心能力为本地证据锁死、Fail-Closed 拒答与 Obsidian Markdown 导出；GitHub `huangbuqubunao-alt/intelligence` 当前为 `PUBLIC`（0 Stars / 0 Forks / 0 external PRs）。 | “YouTube 英文原讲 + B 站中文拆解 + 本地 Markdown 同库对比 + Obsidian 深链带出”在中文技术/投研/深度内容消费人群中具备比通用 RAG 更尖锐的场景切口。 | 真人目标用户是否会持续两周以上将其融入 Obsidian 工作流，而不回流免费 Google NotebookLM + 网页总结插件。 |
| **2. 当前功能与核心业务流程** | 端到端链路：`youtube-intel start` 零配置冷启动 / `youtube-intel demo` 离线展示 → 多源入库（SQLite WAL + SHA-256 hash 校验）→ `<180s` 短视频自动折叠 → 本机 Ollama 或显式授权 BYOK 云端提炼（每日预算熔断）→ 按需点击触发本地视频关键帧抽取 + 64 位 dHash 去重 + 原话字幕时间对齐融合分析（Ollama `/api/chat` `images` 或受控 BYOK `low` 图，支持 Lightbox 浏览与带图 `visual-pack.zip` 导出）→ `Research` 混合 FTS5 BM25 跨源问答（`TIME_RANGE` + `TEXT_RANGE` + Fail-Closed `REFUSED_INSUFFICIENT_EVIDENCE`）→ 严格 7 天周报 & 主题演化 → Obsidian `.md`/`.zip` 包导出（带 `https://...?t=`、`ev:` 指纹与 `![[assets/...jpg]]`）。 | 主干“导入→图文融合核验→带走笔记”核心闭环已打通，无需扩展新数据源即具备完整单机研究体验。 | 长周期订阅场景下（追更 10+ 频道）7 日周报与按需关键帧配合使用的每周复看习惯是否成立。 |
| **3. 已完成、未完成与废弃功能** | **已完成**：Iteration #1–#8（含 `BL-011`）均已按 `FD-005`–`FD-007` 同步公开主线 `main@4d24df4`；Iteration #9（`BL-012` / Round 19：`⌘K` 专题洞察/追问动作、`#Topics` 搜索排序、`#Research` 细滚动条与 `--check-only` 一行式就绪结论）已在研发分支完成研发与全量验收，待按 L3 批准合流 `main`。<br>**未完成/暂缓**：后台自动全量批量跑视频关键帧 VLM（继续 `DEFER` 防静默消耗）、V2 爬虫（X/网页正文/播客/PDF）、Obsidian 双向监听插件、深研调查工作流（`EarlySignal`/`Investigation`）、团队协作版、打包分发评估（`BL-009`）。<br>**受控冻结/废弃**：默认关闭且 fail-closed 的 `TASK-016` 多模型深研实验链路（`deep_analysis_tier: EXPERIMENTAL`）、历史 `GOV-001` 冻结试跑门禁、自动隐式 `hybrid` 云端切换、原生非 WSL Windows 运行。 | 保持“单视频用户主动点击触发、3–12 帧有界抽取 + `$0` 本地优先”既满足演示/图表类视频痛点，又守住零静默成本防线。 | 团队协同与 Obsidian 插件是否在单机留存成立后真有强需求。 |
| **4. UI/UX 设计与实机交互质量** | Iteration #3–#5 连续闭环首日冷启动、内容详情与首轮引导；Iteration #8 在 `#Content/<id>` `#section-intelligence` 新增双主题响应式关键帧卡片、PPT/讲者筛选与键盘无障碍 Lightbox（`ArrowLeft`/`ArrowRight`/`Escape`），在 Obsidian Dark `1440×900` 与 Warm Paper Light `375×812` 实机均保持 `0px` 横向溢出、`0` console error 与 `0` HTTP `>=400`；非视频/音频自动隐藏面板，Iteration #6 `#Settings` 继续保持默认折叠零扰动。 | 首次体验、多模态图卡可读性与详情阅读流均达到顺畅可用水平。 | 真实首次用户在脱离提示下能否自如完成“引导 → 导入 → 图文抽帧 → 导出”。 |
| **5. 前后端架构** | Python 3.12+ 后端（124 个 `.py` 模块，新增 `visual_keyframes.py` + `FastReadApiApplication` 关键帧路由）；React + TypeScript + Vite 前端（`WorkspaceVisualKeyframes` 响应式图卡/Lightbox，79 个 `.ts/.tsx` 模块）；大库分页、全库分块读取与冷读优化持续完整生效。 | 单进程回环静态托管 + Sidecar 隔离图像根目录（`0o700`/`0o600`）兼顾极简部署与安全边界。 | 当个人库长期沉淀数百组关键帧包后的本地磁盘占用整理需求。 |
| **6. 数据结构与存储机制** | 双 SQLite 分离：核心事实库 `state.sqlite3` 保持零 Schema 改动；Sidecar AI 库 `.workspace-ai/hub.sqlite3` 在 Iteration #8 新增 `video_visual_analyses` 表与 `.workspace-ai/keyframes/<hash16>/` 受控图库（随 Sidecar 快照备份恢复），BYOK 凭据优先隔离至 macOS Keychain。 | 分库 + 临时目录原子替换确保重跑/失败回滚零损坏且不污染核心审计表。 | 长期运行生成较多离线图包后的主动清理阈值设计。 |
| **7. 测试覆盖与质量现状** | **研发分支全绿闭环（Iteration #9）**：`ruff` 0 错、`mypy src`（137 文件）0 错、`vite build` `1.03s`、全量 Vitest **`56/56` / `1249/1249 passed in 93.45s`**、13 组完整 CI `pytest` 独跑 **`152/152 passed in 527.50s`**、安全扫描无新增告警、`--check-only` 实测 `[ALL READY]` + Chromium `8795` 双主题实机全通（主线 `main@092951b` 云端 [`#45201809374`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45201809374) `151/151` + `1247/1247` 对照全绿）。 | Round 19 全部细节项与冷启动可观察性已完成工程验证，分支随时可合流 `main`。 | 真实外网长视频在多变 `yt-dlp` 字幕与多类型课件画面上的长期效果（待后续观察）。 |
| **8. 技术债与潜在安全风险** | **安全扫描**：`scripts/security_scan.sh` 命中 17 条，`src/` / `frontend/` / `scripts/` / `product-ops/` 与新增测试全部 **0 命中**（仅历史测试假密钥哨兵）。<br>**已核实风险**：① GitHub 仓库维持被动 `PUBLIC` 状态（按 `FD-005`/`FD-006`/`FD-007` 严守零外宣、零 Release、零招募）；② `/api/v1/videos/<id>/evidence` 单内容页有序返回前 21 条展示切片（长内容尾段由跨源问答 FTS5 检索引擎与后端核验覆盖）；③ 原生非 WSL Windows 因 `fcntl` 不可用受限（已有运行时错误引导）；④ 外部真人体检指标仍为 0。 | 在内部阶段，最大系统风险不是漏洞泄漏或单机导出兼容性，而是外部真实留存尚缺样本。 | 待授权转入真人试验后的未知平台接口限流/反爬摩擦分布。 |
| **9. 现有运营与商业化准备情况** | 基础设施已就绪：GitHub `PUBLIC` + Apache-2.0 `LICENSE`/`NOTICE` + `ci.yml` + 每日日报生成器 `scripts/generate_daily_ops_report.py` + 创始人已在 Antigravity 面板启用 21:00 日报自动化侧车；零额外第三方 SaaS 开销。商业化仍停留在方案推演与定价锚点对比期，**无真实付费转化数据**。 | 在未过外部留存门禁前，坚持“Apache-2.0 单机核心免费 + 按工作流效率/团队协同收费假设”比自研计费中台或倒卖 Token 更合理。 | 个人用户对“$\$29\text{–}\$49$ 买断工作流包”与团队席位付费的实际接受度。 |
| **10. 历史开发决策及依据** | `DEC-OPS-001`~`DEC-OPS-012`（前期闭环、零配置冷启动、Stage D、Iteration #4–#7/`FD-006` 以及 Iteration #8 `BL-011` 按需轻量关键帧抽取、dHash 去重、Ollama/受控 BYOK 图文融合、Lightbox、`assets/*.jpg` Obsidian `.zip` 打包连同 **`FD-007` 合流 `main@092951b`**）。每次迭代均先核验痛点或实机证据，严控边界不盲目扩线。 | 维持小步快跑、实机验真与严控边界策略有效防止了“功能膨胀却失控消费”。 | 未来何时启动受控真人首测或推进下一轮高优细节打磨。 |

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
