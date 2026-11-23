# 产品与技术基线审计报告（Product Baseline Audit）

- **审计更新日期**：2026-11-23（`Asia/Shanghai`）
- **审计人**：AI 产品负责人（CPO / Market & UX / Tech Lead / QA / Growth & Ops）
- **活跃开发分支**：`antigravity/task-user-readiness-20261112`（已完成 Iteration #1–#6：深链导出、`EXP-002` 本机基准、零配置启动、首日体验清障、详情快读减负 `BL-006`、32 例 Eval `BL-005`、首轮引导/双语精修 `BL-007` 及 >500 大库分页/全库检索/SQLite `.backup()` 热快照 `BL-008`）
- **公开主线对照基线（`main` & `origin/main`）**：`f23954f9f1f7922ce626e3bbdafe4ee2d8ca01aa`（已按 `FD-005` 同步至 Iteration #3 基线，GitHub Actions [`Public Beta CI #45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) Python 11 组套件 + Frontend Vitest 双端全绿）
- **当前运营边界**：**内部自主迭代与产品完善阶段**（严格不招募真实外部用户、不发起真人试跑、不把 AI 模拟体验当成真人需求证据）

---

## 一、十维全景接管审计（严格区分事实、推断与假设）

| 审计维度 | 已证实的事实（代码/运行/测试实测） | 合理推断 | 待验证假设 |
|---|---|---|---|
| **1. 产品定位与目标市场** | 代码契约明确 `release_posture: PUBLIC_BETA`（Apache-2.0）、支持 YouTube + B 站 `BV` + 本地音视频(`.mp4/.wav/.mp3/.m4a <=4h`) + 本地 `.md/.txt`，核心能力为本地证据锁死、Fail-Closed 拒答与 Obsidian Markdown 导出；GitHub `huangbuqubunao-alt/intelligence` 当前为 `PUBLIC`（0 Stars / 0 Forks / 0 external PRs）。 | “YouTube 英文原讲 + B 站中文拆解 + 本地 Markdown 同库对比 + Obsidian 深链带出”在中文技术/投研/深度内容消费人群中具备比通用 RAG 更尖锐的场景切口。 | 真人目标用户是否会持续两周以上将其融入 Obsidian 工作流，而不回流免费 Google NotebookLM + 网页总结插件。 |
| **2. 当前功能与核心业务流程** | 端到端链路：`youtube-intel start` 零配置冷启动 / `youtube-intel demo` 离线展示 → 多源入库（SQLite WAL + SHA-256 hash 校验）→ `<180s` 短视频自动折叠 → 本机 Ollama 或显式授权 BYOK 云端提炼（每日预算熔断）→ `Research` 混合 FTS5 BM25 跨源问答（`TIME_RANGE` + `TEXT_RANGE` + Fail-Closed `REFUSED_INSUFFICIENT_EVIDENCE`）→ 严格 7 天周报 & 主题演化 → Obsidian `.md`/`.zip` 包导出（带 `https://...?t=` 与 `ev:` 指纹）。 | 主干“导入→问答核验→带走笔记”核心闭环已打通，无需扩展新数据源即具备完整单机研究体验。 | 长周期订阅场景下（追更 10+ 频道）7 日周报的每周复看习惯是否成立。 |
| **3. 已完成、未完成与废弃功能** | **已完成**：Iteration #1 深链出处；Iteration #2 零配置 `youtube-intel start` + `--check-only`；Iteration #3（`fee43f4`，已合流 `main@f23954f`）修复首日四项阻断；Iteration #4（`6760028`，`BL-006` + `BL-005`）补齐 `/evidence` 单快照快读与 32 例 Eval；Iteration #5（`2be958f`，`BL-007`）升级首轮三步引导与缺失双语辞书；Iteration #6（`BL-008`）突破 500 条视频全库限制并交付分页 `/api/v1/videos`、全库分块检索与 SQLite `.backup()` 零密钥热快照。<br>**未完成/暂缓**：团队协作版、Obsidian 双向监听插件、V2 爬虫（X/网页正文/播客）、多图 VLM。<br>**受控冻结/废弃**：默认关闭且 fail-closed 的 `TASK-016` 多模型深研实验链路（`deep_analysis_tier: EXPERIMENTAL`）、历史 `GOV-001` 冻结试跑门禁、自动隐式 `hybrid` 云端切换、原生非 WSL Windows 运行。 | 继续收敛当前单机核验流程的激活与导出确定性，ROI 远高于提前解冻高维护成本的 V2 爬虫。 | 团队协同与 Obsidian 插件是否在单机留存成立后真有强需求。 |
| **4. UI/UX 设计与实机交互质量** | Iteration #3–#5 连续闭环首日冷启动、内容详情与首轮引导：详情顶部动作收敛双层且瞬载 9 证据卡（`BL-006`），首轮三步引导新增可跳转步骤条、祖母绿进度条与三来源卡片，并在 Obsidian Dark `1440×900` 与 Warm Paper Light `375×812` 保持 `0px` 横向溢出、`0` console error 与 `0` HTTP `>=400`（`BL-007`）；Iteration #6 复审 `#Settings` 确认次级诊断已默认折叠收起，维持零扰动。 | 首次体验、引导可读性与详情阅读流均已达到顺畅水准；避免无收益的 UI 频繁改版。 | 真实首次用户在脱离提示下能否自如完成“引导 → 导入 → 提问 → 导出”。 |
| **5. 前后端架构** | Python 3.12+ 后端（123 个 `.py` 模块：`local_api.py` 单端口静态+API、CSP 隔离、`fast_read_api.py` TTL 缓存、WAL + inode 守护）；React + TypeScript + Vite 前端（78 个 `.ts/.tsx` 模块、JSX 手工状态路由 + SWR 预取）；Iteration #6 已将 `/api/v1/videos` 升级为向后兼容分页（`?limit=&offset=`）、8 处研究聚合转为分块全库加载（安全上限 10,000），并将冷启动 `/videos` 与 `/intelligence` cProfile 耗时分别压缩 3.5x 与 2.2x。 | 单进程回环静态托管 + SQLite 分层兼顾部署极简性与可恢复性；在 600+ 条资料库实测跨库检索仍仅 `0.23s`、分页单页 `48–98ms`。 | 当个人库突破数千乃至接近 10,000 条视频时，浏览器首次列表拉取与端到端长视频抽取体验需真实样本观测。 |
| **6. 数据结构与存储机制** | 双 SQLite 分离：核心事实库 `state.sqlite3`（视频/字幕哈希/`evidence_id`/不可变范围）+ Sidecar AI 库 `.workspace-ai/hub.sqlite3`（摘要、问答会话、7 日周报、`cloud_call_ledger` 每日预算账本）；BYOK 凭据优先隔离至 macOS Keychain，零明文回显。Iteration #6 保持核心与 Sidecar Schema 零改动，新增 `create_sqlite_hot_snapshot()` 通过原生 SQLite `.backup()` 生成 `hub-snapshot.sqlite3`（`0o600` + `PRAGMA integrity_check`）并紧缩 JSON 快照。 | 分库 + 在线 `.backup()` 快照同时保护核心层可审计性与 Sidecar 无锁热备份一致性。 | 长期运行数年生成多 GB 核心媒体文件后的磁盘压缩与增量归档诉求。 |
| **7. 测试覆盖与质量现状** | **Iteration #6 实测全绿闭环**：后端（最终代码后）`ruff` 0 错、`mypy` 136 文件 0 错、11 组 CI `pytest` 独跑 **143/143 passed in 505.13s**（含 600 条大库分页/跨库问答 `0.23s`/热快照 `5.5ms` 与 32 例 Eval）、`test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` **27/27 passed in 59.89s**；前端（Iteration #5 `@2be958f`，本轮零改动）`vite build` `3.23s` 零报错 + 全量 Vitest **54/54 文件 / 1244/1244 tests passed in `88.35s`** + Chromium 双主题实机全通；`main@f23954f` 云端 Actions [`#45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) 双端全绿。 | 自动化回归、600 条规模基准、热备份与防幻觉单元契约已达到高工程确定性。 | 真实外网长视频在多变 `yt-dlp` 字幕格式与高并发写入场景下的长稳性（需真实环境下多轮观察，而非合成单测）。 |
| **8. 技术债与潜在安全风险** | **安全扫描**：`scripts/security_scan.sh` 命中 17 条，`src/` / `frontend/` / `scripts/` / `product-ops/` 全部 **0 命中**（仅历史测试假密钥哨兵）。<br>**已核实风险**：① GitHub 仓库维持被动 `PUBLIC` 状态（按 `FD-005` 严守零外宣、零 Release、零招募），Iteration #4–#6 成果暂留存开发分支待按里程碑合流；② 10,000 条单批内存聚合以上规模需未来按需考虑分片/独立索引（当前远超个人冷启动阶段需求）；③ 原生非 WSL Windows 因 `fcntl` 不可用受限（已有运行时错误引导）；④ 外部真人体检指标仍为 0。 | 在内部阶段，最大系统风险不是漏洞泄漏或单机容量天花板，而是外部真实留存尚缺样本。 | 待授权转入真人试验后的未知平台接口限流/反爬摩擦分布。 |
| **9. 现有运营与商业化准备情况** | 基础设施已就绪：GitHub `PUBLIC` + Apache-2.0 `LICENSE`/`NOTICE` + `ci.yml` + 每日日报生成器 `scripts/generate_daily_ops_report.py` + 创始人已在 Antigravity 面板启用 21:00 日报自动化侧车；零额外第三方 SaaS 开销。商业化仍停留在方案推演与定价锚点对比期，**无真实付费转化数据**。 | 在未过外部留存门禁前，坚持“Apache-2.0 单机核心免费 + 按工作流效率/团队协同收费假设”比自研计费中台或倒卖 Token 更合理。 | 个人用户对“$\$29\text{–}\$49$ 买断工作流包”与团队席位付费的实际接受度。 |
| **10. 历史开发决策及依据** | `DEC-OPS-001`（补深链导出）、`DEC-OPS-002`（上主线激活 CI）、`DEC-OPS-003`（延后 V2 爬虫与隐式 hybrid）、`DEC-OPS-004`（`EXP-002` 本机 Ollama 实测）、`DEC-OPS-005`（零配置启动器）、`DEC-OPS-006`（Stage D 修复 Stage A 4 项阻断障碍并按 `FD-005` 同步 `main@f23954f`）、`DEC-OPS-007`（Iteration #4 交付 `BL-006` `/evidence` 快读 + SWR + 双层详情动作栏，以及 `BL-005` 32 例 Eval 扩容与 Demo 拒答词根防线）、`DEC-OPS-008`（Iteration #5 交付 `BL-007` 首轮可跳转 3 步引导 + 双主题移动适配 + 缺失中文补全）、`DEC-OPS-009`（Iteration #6 交付 `BL-008` >500 分页/全库分块检索/SQLite `.backup()` 热快照/冷读优化与 `#Settings` 零扰动复审）。每次迭代均先核验痛点或实机失败证据，绝不无证据加功能。 | 维持小步快跑、实机验真与严控边界策略有效防止了“功能膨胀却打不开”。 | 未来什么时候终止内部打磨、申请创始人批准进入受控真人首测。 |

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
