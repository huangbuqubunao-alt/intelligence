# 产品与技术基线审计报告（Product Baseline Audit）

- **审计更新日期**：2026-11-23（`Asia/Shanghai`）
- **审计人**：AI 产品负责人（CPO / Market & UX / Tech Lead / QA / Growth & Ops）
- **活跃开发分支**：`antigravity/task-user-readiness-20261112`（最新代码基线提交 `fee43f4d977bdf9edd03282b98e9b679aceea2c4`，已含 Iteration #1 深链导出、`EXP-002` 本机模型基准、Iteration #2 零配置 `youtube-intel start` 与 Iteration #3 实机体验缺陷修复）
- **公开主线对照基线（`main` & `origin/main`）**：`a8201527c5bcc7f7d97e143d605162f73db3ff23`（GitHub Actions [`Public Beta CI #45137542384`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45137542384) Python 11 组套件 + Frontend Vitest 双端全绿）
- **当前运营边界**：**内部自主迭代与产品完善阶段**（严格不招募真实外部用户、不发起真人试跑、不把 AI 模拟体验当成真人需求证据）

---

## 一、十维全景接管审计（严格区分事实、推断与假设）

| 审计维度 | 已证实的事实（代码/运行/测试实测） | 合理推断 | 待验证假设 |
|---|---|---|---|
| **1. 产品定位与目标市场** | 代码契约明确 `release_posture: PUBLIC_BETA`（Apache-2.0）、支持 YouTube + B 站 `BV` + 本地音视频(`.mp4/.wav/.mp3/.m4a <=4h`) + 本地 `.md/.txt`，核心能力为本地证据锁死、Fail-Closed 拒答与 Obsidian Markdown 导出；GitHub `huangbuqubunao-alt/intelligence` 当前为 `PUBLIC`（0 Stars / 0 Forks / 0 external PRs）。 | “YouTube 英文原讲 + B 站中文拆解 + 本地 Markdown 同库对比 + Obsidian 深链带出”在中文技术/投研/深度内容消费人群中具备比通用 RAG 更尖锐的场景切口。 | 真人目标用户是否会持续两周以上将其融入 Obsidian 工作流，而不回流免费 Google NotebookLM + 网页总结插件。 |
| **2. 当前功能与核心业务流程** | 端到端链路：`youtube-intel start` 零配置冷启动 / `youtube-intel demo` 离线展示 → 多源入库（SQLite WAL + SHA-256 hash 校验）→ `<180s` 短视频自动折叠 → 本机 Ollama 或显式授权 BYOK 云端提炼（每日预算熔断）→ `Research` 混合 FTS5 BM25 跨源问答（`TIME_RANGE` + `TEXT_RANGE` + Fail-Closed `REFUSED_INSUFFICIENT_EVIDENCE`）→ 严格 7 天周报 & 主题演化 → Obsidian `.md`/`.zip` 包导出（带 `https://...?t=` 与 `ev:` 指纹）。 | 主干“导入→问答核验→带走笔记”核心闭环已打通，无需扩展新数据源即具备完整单机研究体验。 | 长周期订阅场景下（追更 10+ 频道）7 日周报的每周复看习惯是否成立。 |
| **3. 已完成、未完成与废弃功能** | **已完成**：Iteration #1 深链出处；Iteration #2 零配置 `youtube-intel start` + `--check-only`；Iteration #3（`fee43f4`）修复 Demo 越域假阳性拒答、macOS 浏览器上传恢复按钮、全新工作区 Settings 实时状态同步、空库 Research/Topics/Intelligence 引导与 `Escape` 关窗。<br>**未完成/暂缓**：团队协作版、Obsidian 双向监听插件、V2 爬虫（X/网页正文/播客）、多图 VLM。<br>**受控冻结/废弃**：默认关闭且 fail-closed 的 `TASK-016` 多模型深研实验链路（`deep_analysis_tier: EXPERIMENTAL`）、历史 `GOV-001` 冻结试跑门禁、自动隐式 `hybrid` 云端切换、原生非 WSL Windows 运行。 | 继续收敛当前单机核验流程的激活与导出确定性，ROI 远高于提前解冻高维护成本的 V2 爬虫。 | 团队协同与 Obsidian 插件是否在单机留存成立后真有强需求。 |
| **4. UI/UX 设计与实机交互质量** | Stage A Chromium 实机审计（`1440×900` & `375×812`）实测出全新工作区 3 个 P0 障碍（macOS 启动 `youtube-intel start` 无法在浏览器传本地文件、Settings 误报待检查、空库问答直接抛 HTTP `409`）与 Demo 越域乱答；Iteration #3 修复后 Chromium 实机复检全绿，移动 `375×812` 保持 `0px` 横向溢出、`.nav-item` 高度 `40px`、本地 `.md` 浏览器上传返回 HTTP `201`。 | 一周内的首次体验障碍已从“必卡死/报错”收敛到“清晰有下一步动作”；仅余非核心视觉微调（例如 `#Settings` 三栏次级信息精简、Content 详情按钮换行微调）。 | 真实首次用户在脱离提示下能否自如完成“Switch to browser upload → `.md` 导入 → 提问 → 导出”。 |
| **5. 前后端架构** | Python 3.12+ 后端（123 个 `.py` 模块：`local_api.py` 单端口静态+API、CSP 隔离、`fast_read_api.py` TTL 缓存、WAL + inode 守护）；React + TypeScript + Vite 前端（78 个 `.ts/.tsx` 模块、JSX 手工状态路由 + SWR 预取）；单机零额外中间件依赖。 | 单进程回环静态托管 + SQLite 分层兼顾部署极简性与可恢复性；在 500–2000 条以内资料库表现极快（实测 Demo 所有读接口 `2ms–52ms`）。 | 当用户个人库规模增长到数千条视频（>1000）时，`list_videos(limit=500)` 的截断上限需平滑升级。 |
| **6. 数据结构与存储机制** | 双 SQLite 分离：核心事实库 `state.sqlite3`（视频/字幕哈希/`evidence_id`/不可变范围）+ Sidecar AI 库 `.workspace-ai/hub.sqlite3`（摘要、问答会话、7 日周报、`cloud_call_ledger` 每日预算账本）；BYOK 凭据优先隔离至 macOS Keychain，零明文回显。`prepare_local_workspace()` 在 `fee43f4` 起幂等初始化 `hub.sqlite3` schema。 | 分库保护了核心层可审计性与无污染备份恢复；所有引用必须经由核心层候选池回填。 | 长期历史快照（JSON 全量备份）在极大媒体库下的导出体积与恢复速度表现。 |
| **7. 测试覆盖与质量现状** | **Stage D 提交 `fee43f4` 全量实测全绿**：`ruff check src tests scripts` 0 错、`mypy src` 136 文件 0 错、11 组 CI `pytest` **140/140 passed**（含新增 Demo 越域拒答 + Launcher Settings 校验 + 20 例 Eval + 250 条规模检索）、`npm run build` 通过、Vitest **54/54 文件 / 1240/1240 tests passed**；另有 CPO 日报新增测试 **4/4 passed**。 | 自动化回归与防幻觉单元契约已达到较高工程确定性；外部云端 CI 上一基线 `a820152` 双端全绿。 | 真实外网长视频在多变 `yt-dlp` 字幕格式与高并发写入场景下的长稳性（需真实环境下多轮观察，而非合成单测）。 |
| **8. 技术债与潜在安全风险** | **安全扫描**：`scripts/security_scan.sh` 命中 17 条，`src/` / `frontend/` / `scripts/` / `product-ops/` 全部 **0 命中**（仅历史测试假密钥与历史文档）。<br>**已核实风险**：① GitHub 仓库当前为 `PUBLIC`（已转为内部迭代阶段但仍公开可见），且 `main` 领先分支尚未同步 `fee43f4`；② `list_videos(limit=500)` 全库扫描上限与全量 JSON 备份在超大库场景存在扩展Ceiling；③ 原生非 WSL Windows 因 `fcntl` 不可用受限（已有运行时错误引导）；④ 外部真人体检指标仍为 0。 | 在内部阶段，最大系统风险不是漏洞泄漏（已逐一加固与扫描），而是未通过持续市场/模拟反馈及时精简复杂设置项。 | 待授权转入真人试验后的未知平台接口限流/反爬摩擦分布。 |
| **9. 现有运营与商业化准备情况** | 基础设施已就绪：GitHub `PUBLIC` + Apache-2.0 `LICENSE`/`NOTICE` + `ci.yml` + 每日日报生成器 `scripts/generate_daily_ops_report.py` + 创始人已在 Antigravity 面板启用 21:00 日报自动化侧车；零额外第三方 SaaS 开销。商业化仍停留在方案推演与定价锚点对比期，**无真实付费转化数据**。 | 在未过外部留存门禁前，坚持“Apache-2.0 单机核心免费 + 按工作流效率/团队协同收费假设”比自研计费中台或倒卖 Token 更合理。 | 个人用户对“$\$29\text{–}\$49$ 买断工作流包”与团队席位付费的实际接受度。 |
| **10. 历史开发决策及依据** | `DEC-OPS-001`（补深链导出）、`DEC-OPS-002`（上主线激活 CI）、`DEC-OPS-003`（延后 V2 爬虫与隐式 hybrid）、`DEC-OPS-004`（`EXP-002` 本机 Ollama 实测）、`DEC-OPS-005`（零配置启动器）、`DEC-OPS-006`（Stage D 修复 Stage A 实机发现的 4 项阻断障碍）。每次迭代均先核验痛点或实机失败证据，绝不无证据加功能。 | 维持小步快跑、实机验真与严控边界策略有效防止了“功能膨胀却打不开”。 | 未来什么时候终止内部打磨、申请创始人批准进入受控真人首测。 |

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
