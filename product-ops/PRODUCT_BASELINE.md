# 产品与技术基线审计报告（Product Baseline Audit）

- **审计日期**：2026-11-23（`Asia/Shanghai`）
- **审计人**：AI 产品负责人（CPO / Tech Lead / Growth & Ops）
- **工作区与基线分支**：`/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`（分支 `antigravity/task-user-readiness-20261112`，最新已验证代码提交 `09f98d4fb764a1a5936b03963fbf520c1bc5a0a2`）
- **主线对照基线**：`main` & `origin/main` @ `4c034b7b298b57b87f037e08877518f8c6d18086`（tree 等价于 `bb06de9`，尚落后本分支 4 笔关键加固与迭代提交：`0fc61a7`、`c85625b`、`89a9878`、`09f98d4`）

---

## 一、产品现状报告（真实边界分层盘点）

仓库结构规模：`src/youtube_intel/` 共 123 个 `.py` 模块，前端 `frontend/src/workspace/` 共 78 个 `.ts/.tsx` 模块，全仓 `tests/` 共采集到 `7,319` 项历史与现行测试。必须严格区分五类能力边界：

| 类别 | 具体能力与资产 | 真实状态说明与证据 |
|---|---|---|
| **1. 已实际实现且通过端到端验证的能力** | YouTube（RSS/yt-dlp 元数据与字幕）/ B 站（`BV...` 字幕）/ 本地音视频（`.mp4/.wav/.mp3/.m4a` 至多 4 小时 + 可选 Apple Silicon `mlx-whisper`）/ 本地 `.md`/`.txt`（`TEXT_RANGE` 段落证据）；双轨 AI 提炼（本机 Ollama 默认免费 / 可选隔离 BYOK 云端 DeepSeek·OpenAI·Kimi，每日默认 30 次调用预算 + 后台禁止云端静默扣费）；Home（近 7 日变化 + 严格 7 天滚动周报）/ Following / Content（180s 短视频折叠护栏 + 失败恢复 CTA）/ Intelligence / Topics（演化与 MOC）/ Research（视频+Markdown 跨源问答 + Fail-Closed 诚实拒答 + 可点击 `https://...?t=...` 外链回跳导出）/ Settings & 零密钥备份恢复；单端口离线 `youtube-intel demo` | 本工作分支最新验证：CI 10 组 `pytest` **133 passed**、`ruff` 0 错、`mypy` 136 文件 0 错、`vite build` 通过、Vitest **54/54 文件 / 1237/1237 用例全过**；并具备先前 Playwright Chrome E2E 12/12 与 55/55 后端审计基线 |
| **2. 部分完成 / 需配合外部前提的能力** | ① GitHub 仓库与公开发布：Apache-2.0（`LICENSE`/`NOTICE`）已落盘，但仓库在 GitHub 上仍为 **`PRIVATE`**、`0` 次 Actions 运行（`.github/workflows/ci.yml` 在分支上未合并到 `main`）；<br>② 无人值守日常运维：CLI `launchd` `.plist.example` 已存在但未安装，`scripts/generate_daily_ops_report.py` 已交付，Antigravity 定时自动化需创始人授权启用；<br>③ 无字幕视频本地语音转写：仅在 Apple Silicon 且用户另行 `uv sync --extra mac-whisper` 时完整可用 | GitHub CLI `gh repo view`（2026-11-23）：`visibility: PRIVATE`、`stargazerCount: 0`、`gh run list`: `no runs found`；Windows 原生（非 WSL2）受 `fcntl` 锁限制在运行时拦截并给出指引 |
| **3. 仅存在于文档/规划中的计划** | ① 团队协作版/Obsidian 自动化双向守护同步插件、商业化付费层级；<br>② V2 数据源（RSS/网页正文/X/Reddit/播客自动抓取）、多图/关键帧 VLM 批量视觉分析；<br>③ 10 位真实外部双语研究者的受控测试与留存实验 | 见 `docs/PRD.md` 第 3.2 节与本次 `product-ops/EXPERIMENTS.md`（均明确标为未实施/待验证） |
| **4. 尚未经过真实验证的环节** | ① **真实外网用户价值、自然获客、7 日留存与付费意愿**：目前真实外部日活/留存为 `0 / 暂无数据`；<br>② **未预置陌生双语材料（真实 YouTube 英文长视频 + B 站中文视频 + 本地 Markdown）在本机真实 Ollama 模型下的公开示范录屏/基准样本**：`youtube-intel demo` 默认使用离线合成回放器（`demo-replay`），虽已坦诚标注，仍缺“真实模型首次冷跑不翻车”公开证据包 | 会话历史与 `qa/` 证据均使用合成或受控测试桩；`.var/owner` 个人库按安全红线未用于对外样本 |
| **5. 已证明受控停用/历史冻结或明确废弃的方案** | ① **受控多模型深研流水线（`TASK-016` / `EXPERIMENTAL`）**：默认关闭且 fail-closed，历史试运行中 GLM-4.7-Flash / 早期低量化 Qwen 试跑曾在真实语义审查中被独立判 `REJECT`；历史 `GOV-001` 冻结校验包 190 项按设计因代码哈希演进继续失败关闭，不伪造通过；<br>② **自动隐式 `hybrid` 云端路由**与**原生 Windows 非 WSL 运行** | `docs/RELEASE_CHECKLIST.md`、`qa/defects.md`、`GET /api/v1/system` (`release_posture: "PUBLIC_BETA"`, `deep_analysis_tier: "EXPERIMENTAL"`) |

---

## 二、用户价值及核心业务流程地图

**核心用户承诺**：“把跨平台的视频与本地笔记里的一个判断，核回精确原话/段落，再带走一篇离开工作台依然能点开原片的 Markdown 研究笔记。”

```text
[多源采集] YouTube 频道/URL · B站 BV · 本地音视频(<=4h) · 本地 .md/.txt
     │
     ▼  (hash 校验 + SQLite WAL 落盘 + source_authority 防篡改)
[结构化过滤与提炼]
  ├─ 短视频噪声护栏 (<180s 折叠进 Shorts 抽屉，>180s 长讲解保护)
  ├─ 免费本机 Ollama 默认评估/提炼 (0–10 评分 · 核心论点严格绑定真实窗口/TEXT_RANGE)
  ├─ 无字幕诚实降级 (Metadata 速览 / 引导本地文件替代 / MLX Whisper)
  └─ 可选 BYOK 云端 (显式授权 + 每日额度记账，后台禁用)
     │
     ▼
[跨源核验与综合]
  ├─ Research Q&A：Video (TIME_RANGE) + Markdown (TEXT_RANGE) 混合 FTS5 BM25 检索 (<=500条)
  ├─ Fail-Closed 门禁：无有效支持证据 => 拒答 (REFUSED_INSUFFICIENT_EVIDENCE) + 分离仅供参考片段
  ├─ Weekly Brief：严格 7 天滚动窗口（空窗诚实报告，绝不用上月旧片凑数）
  └─ Topic Evolution：跨频道共识/分歧时间线 + Obsidian MOC
     │
     ▼  (核心留存出口 · Batch A 已打通外链)
[可携带知识交付] Obsidian [[wikilinks]] 笔记 / .zip 知识库包 / 纯文本提纲
  └─ 含原片 HTTPS 深链 (?t=75s / ?t=65)、Markdown 段落偏移 P#(start–end) 与 ev: 哈希前缀
```

---

## 三、技术架构与质量风险清单

| 风险 ID | 严重度 | 风险描述 | 现状与缓解措施 |
|---|---|---|---|
| **TECH-01** | **P1（发布同步阻塞）** | `main` 与 `origin/main` 仍停在 `4c034b7`，缺少本分支 4 笔安全/反幻觉/跨源 Markdown/深链导出修复（`0fc61a7`..`09f98d4`），GitHub CI 在 `main` 上运行数为 0 | 等创始人批准 `FD-001` 后 cherry-pick/快进至 `main` 并触发 Actions |
| **TECH-02** | **P1（真实外网环境差异）** | 所有主工作台回归测试使用 mock LLM 响应与离线字幕夹具，真实 Ollama 模型（如 `qwen3.5:9b`）在中英文混合长材料下对 JSON Strict `[E1]..[En]` 拒答指令的服从率未在本分支上录成实机基准 | 通过 `EXP-002` 在隔离工作区使用真实本机 Ollama 对公开双语视频进行实测与验收 |
| **TECH-03** | **P2（双 SQLite 库一致性）** | 主库 `state.sqlite3` 与 AI Sidecar `.workspace-ai/hub.sqlite3` 分库隔离保护了核心恢复与零入侵契约，但跨库写操作无分布式两阶段提交（极端断电或局部备份恢复后需重解析） | 所有重要证据引用以核心层 `evidence_id` 为唯一锚点，已按 Codex 边界阻止 hub 自造假证据；长远可补充打开旧问答时的核心存在性复核校验 |
| **TECH-04** | **P2（大规模 JSON 全量快照上限）** | `export_backup_snapshot()` 全表序列化 `hub.sqlite3` 到 JSON；`list_videos(limit=500)` 在超过 500 条视频时会截断全库问答扫描 | 在 500–2000 条库规模触发时迁移为 SQLite 原生热备份与全库 FTS5 索引表（列入月度技术观察项） |
| **TECH-05** | **INFO（历史/静态门禁记录）** | ① `GOV-001`：190 项历史冻结试运行检查失败关闭（按设计不修改）；<br>② `SEC-001`：`scripts/security_scan.sh` 命中 17 条，`src/` 与 `frontend/` 为 0 命中，全在 `tests/` 假密钥与旧日志；<br>③ 原生 Windows 受限于 `fcntl` 锁 | 在公开 `README.md` 与 `RELEASE_CHECKLIST.md` 如实披露，不隐瞒、不伪造全绿 |

---

## 四、关键指标现状及数据缺口

- **北极星指标**：周真实可核验研究收获人次（Weekly Verified Research Takeaways：完成至少 1 篇非样例资料的跨源问答或精炼并复制/导出 Markdown 笔记的活跃用户数）→ **当前：暂无数据**。
- **社区与分发漏斗**：GitHub Stars = `0`、Forks = `0`、外部真实 Issue = `0`、下载量 = **暂无数据**（原因：仓库当前 `PRIVATE`，尚未公开发布与外部触达）。
- **核心数据缺口**：产品遵守 Zero-Telemetry，不采集任何云端埋点，因此外部留存与首次成功耗时仅能通过**受邀用户本地自愿导出的诊断计数（或受控 10 人试用观察）**与 **GitHub 公开漏斗（Clone/Star/Discussion/Issue）**衡量，禁止偷偷加第三方统计 SDK。

---

## 五、当前产品成熟度评估

依据产品生命周期标准，Intelligence 当前处于：**阶段一：技术就绪、市场与用户价值待验证期（Pre-PMF Public Beta / Value-Unverified）**。

- **做对了什么**：工程底座、反幻觉约束（Fail-Closed 拒答 + 核心层不可变范围证据）、本地优先与零静默扣费保护均明显强于市面上绝大多数一次性“套壳总结”脚本。
- **最大的缺口**：我们验证了“软件按设计工作”，但**尚未证明有 10 位真实目标用户会在脱离开发者指导后持续每周使用它、把它放进自己的 Obsidian 研究流水线，并认为它比免费 Google NotebookLM + BibiGPT 更不可替代**。

---

## 六、未来 30 天初步行动路线图（摘要）

1. **第 1 周（对齐基线与可信证据包）**：将本分支 4 笔安全与可信加固合并上 `main`、跑通 GitHub Actions、完成 **真实本机 Ollama 处理陌生中英双语材料 + 本地 Markdown 的公开演示录屏**（替代纯合成回放的第一印象）。
2. **第 2 周（开源公开与首批 5–10 位种子研究者实验）**：获得创始人 L3 批准后公开 GitHub 仓库，面向目标 ICP（重度 Obsidian 用户、双语内容创作者、AI 研究者）招募 5–10 名 Mac/Linux/WSL 用户做「拿自己的一组 B 站+YouTube+Markdown 验证一个判断」实测（`EXP-001`）。
3. **第 3 周（激活摩擦消除与核心留存迭代）**：根据前 10 位用户真实卡点，集中优化冷启动（yt-dlp/Ollama 检查引导、一键导出 Obsidian Vault 目录直写选项、或 B 站/YouTube 字幕常见失效修复），不扩无关大需求。
4. **第 4 周（PMF 复盘与商业化验证判断）**：核查“第 7 天还在继续导出笔记或提问的用户比例”，若 `<30%` 则深挖定位/形态调整；若 `>=40%`，开始小范围验证增值付费假设（`待验证假设`：如一键配置向导包 / 团队共享核查包 / 自动化定期研究简报）。
