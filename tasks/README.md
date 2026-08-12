# YIA 任务分配索引

## 当前门禁

项目状态：`TASK_003_DONE__TASK_004_DONE__TASK_005_DONE__TASK_005A_DONE__TASK_006_DONE__TASK_007_DONE__TASK_008_DONE__TASK_009_DONE__TASK_014_IN_PROGRESS_NO_GO`

DEC-01 至 DEC-10 已批准，`TASK-000`、`TASK-001` 均为 `DONE`。`TASK-001` 的实现与审查证据已通过 merge commit `5273e069aa34392db957e82b8803a709bdd1ab1f` 进入 `main`，整合后门禁全部通过。

`TASK-002` 的实现、预审修复、独立 Grok 审查和最终整合均已完成；审查证据 commit 为 `d98de3537187ac346e404d7899d0a9d90c228483`，merge commit 为 `823d68a2dffc1745e04cbbe54c817bf0c117a6fa`。整合后全部门禁通过，状态为 `DONE`。

`TASK-003` 已由 Codex Integrator 以 merge commit `072511f20b587f973b29437d79080f6cb7863f1a` 整合到 main，整合后门禁全通过，状态为 `DONE`。`TASK-004` 已由 Codex Product Integrator 以 merge commit `dc3f097ce125bc8390b04d0913b5d00f44eae3e8` 整合：双父、固定 17 文件范围及 lock/sync、state 30、unit 36、integration 10、全量 132、mypy/wiring、Ruff、CLI、build/migration 门禁均通过；状态在本次收口后为 `DONE`。

TASK-005 已由 Codex Product Integrator 以 merge commit `cfc302ddc41cd908777f49de292327640b6f8314` 整合到 main，双父和 first-parent 11 文件范围正确；整合后全部受影响离线门禁、offline build 与 package inclusion 通过，并已 closure 同步为 `DONE`。唯一 Service/私有 test hook 聚合 P2 继续登记。ADR-007 已接受并建立 TASK-005A 共享契约任务；TASK-005A、TASK-006/007 的后续结果见下文当前状态。

TASK-005A 已由 Codex Product Integrator 以 merge commit
`865f4fed90dcc22ea43688442c1c4f210b4d31b7` 整合并关闭为 `DONE`：双父与 first-parent
8 路径范围正确，整合后全部离线门禁及 package inclusion 通过。产品负责人现已从共同
base `6b4d59c...` 并行分配 TASK-006 阶段 A 与 TASK-007 离线实现：TASK-006 独占
`pyproject.toml`/`uv.lock`，只获包解析/锁定/安装授权；TASK-007 不改依赖/锁文件且仅用
离线 Fake。两项真实模型、服务、ffmpeg、媒体和凭据路径继续未授权。

TASK-006/TASK-007 已分别以 merge commit `fd9a074...`、`3d49ec...` 整合并关闭为
`DONE`。TASK-008/TASK-009 两个只读 Scout 已在 `main@bb9c6b7...` 完成且仓库无
变化；两项均判定 `DECISION NEEDED`。产品负责人已于 2026-07-20 批准 ADR-008
A-01 至 A-15、ADR-009 N-01 至 N-15 和三项精确依赖范围，并于 2026-07-21 补充批准
ADR-008 A-16/A-17。TASK-008A 的依赖与资源
门禁已满足，现已从 `main@82d1fd7...` 分配到独立 Codex worktree。实现 source
`3822512...` 的第一轮 Reviewer evidence `0f52c30...` 为 `REJECT`（P1=6）。
Correction 1 source `d95745f...` 已提交，完整范围为原 7 路径加固定
`o200k_base.tiktoken` 资源；第二轮 Reviewer evidence `7a8239f...` 已 `APPROVE`，
P0–P3 均无，Product Integrator 已以 merge `64a9c416...` 整合并关闭为 `DONE`。TASK-009A 首轮独立审查 evidence `f73b287...` 为 `REJECT`：纯 Protocol 未在运行时拒绝 naive 时间、空白版本和低价值写入。经产品负责人批准，原 Codex Implementer 修复 `KnowledgeSink` 执行边界与回归测试；第二轮 evidence `e30b40c...` 为 `APPROVE`，并已由 Product Integrator 以 merge `9b0269eddbd29cee83a056d44951d7973c87492b` 整合并关闭为 `DONE`。TASK-008/TASK-009 已从 `main@473119704c7638d7afd4e68d84d00e85064ceabd` 并行分配给 Codex：前者仅限离线 Fake/隔离 SDK，后者仅限测试临时目录文件探针。

ADR-005 已接受“复用优先”策略；所有后续任务包必须引用 `docs/REUSE_REGISTER.md` 并给出 `Reuse decision`，不得未经评估从零实现或整套嵌入第三方应用。

TASK-014 Phase A 的唯一 Implementer source `8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59` 是
`main@d0d136a4754a97954f64f1ca39b87837e639decc` 的唯一非 merge 后继，范围精确为 README、SBOM、
第三方 NOTICE、发布检查表、smoke 矩阵、handoff 与 `.gitignore` 七路径。独立 Reviewer evidence
`88f1b36fdef75146315e91f93b71c36463132ffb` 是其唯一后继、仅追加 source handoff，Verdict=`APPROVE` 且无
P0–P3；两次核验的 source 工作树均干净。此结论只通过 Phase A 资料审查，TASK-014 整体仍为
`IN_PROGRESS` / `No-Go`：mutagen GPL 分发结论、BPE 文件归属/NOTICE、真实 smoke、真实 Vault 边界、
at-most-once 风险签署与最终 PO/TL/QA Go-No-Go 均未完成。未授权发布、真实 smoke、uv、测试、构建、网络、
真实 API/模型、凭据/Vault、依赖变更、项目自身 LICENSE、push、合并或清理。
Phase A accepted source `88f1b36...` 已以 `--no-ff` merge `3165009...` 整合，七路径资料及根目录 ignore 锚定已核验；
TASK-014 仍不得标为 `DONE` 或发布批准。

TASK-014 Phase B-1 旧的最终真实公开字幕 smoke 已 `FAIL`：`--khbXchTeE`、`JTxsNm9IdYU` 各完成一次元数据和字幕目录读取，
但均在正文读取前 `INVALID_RESPONSE` 失败，正文读取均为零；没有认证、媒体、用户数据或重试。唯一 B-1 evidence source 为
`/Users/hua/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry` / `codex/task-014-phase-b1-console-entry-retry@
9acab5d876b38d64a9aeab7aca3474be2676ce38`（唯一父提交 `365c8fc...`）。该 evidence 不合并、不写成通过；TASK-014 仍为
`IN_PROGRESS` / `No-Go`。旧 evidence 不重跑、不合并或复用。已授权但尚未启动的只读后续工作是
`agent-prompts/PREFLIGHT-TASK-014-PHASE-B1-PUBLIC-SUBTITLE-ADAPTER-COMPATIBILITY-SCOUT.md`：只读比较 Adapter 假设、
错误映射、离线 Fake/fixture 与真实脱敏 evidence，聊天回传最小修复建议及一次后续验证所需的精确授权。
本阶段不授权登录/Cookie/API key、真实 Vault、用户数据、媒体下载、ffmpeg、模型、Ollama、OpenAI、付费调用或
高频重试。唯一新的 auditable directory-only 一次性 execution source 为
`/Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-auditable-execution` /
`codex/task-014-phase-b1-directory-only-auditable-execution@58f0215aa329b99d74429e8616bb5f8f673ef102`；正式包为
`agent-prompts/TASK-014-RELEASE-READINESS-PHASE-B1-DIRECTORY-ONLY-AUDITABLE-EXECUTION-CODEX.md`，只授权 B4
`--directory-only` 与 B5 安全摘要，对两个固定 ID 各一次 1/1/0。TASK-014 继续 `IN_PROGRESS` / `No-Go`；即使成功，
也不关闭 mutagen GPL、BPE 文件归属/NOTICE、at-most-once 风险或最终 PO/TL/QA Go-No-Go。
旧 execution worktree（`task-014-release-readiness-phase-b1-execution`）建立在 Phase A 合并前主线，禁止访问、
修改、合并、清理或复用。
旧 final source evidence `5698802...` 仅为缺失锁定 `fsspec==2026.6.0` 的历史环境阻断，两个固定 ID 均未调用，
绝不是通过结果，也不得合并。先前 venv Retry 的 `365c8f...` blocker 是把已存在空目录传给 `--temporary-root`，违反入口
要求的“不存在 smoke-root 子路径”契约且未触达 YouTube；参数纠正后的最终 Retry 已产生 `9acab5d...` 失败 evidence。所有
Executor 包均废止；Scout 禁止网络、YouTube、测试、构建、依赖变更、代码/文档写入、worktree 创建和 `.codebase-memory` 工件。

旧 Phase B-1 blocker evidence `be230490...`（仅存在于 B0 合并前的旧 source，绝不访问或合并）确认默认 CLI 曾缺少受控组合入口。
产品负责人因此批准 ADR-013 和 TASK-014B0：新增仅服务发布 QA 的 `smoke-public-subtitles`，严格限定 1–3 个
显式视频 ID、一次 metadata/字幕目录/一条字幕正文读取、30 秒 timeout、无自动重试与全新临时根。唯一 source
`4e506847854f20a43011b0a15db3a1c8e320656d` 是控制面 `c62310ab79f01f5f311c9f54bb28365905f5a81a` 的唯一后继，严格
为 CLI、专用组合模块、两份离线 Fake 测试、operations 文档与 handoff 六路径，worktree 清洁且无依赖/Schema 改动。
第一轮 Reviewer evidence `f8e336…` 仅追加 source handoff，Verdict=`REJECT`：P1 为 smoke 仍接受三项全局配置路径
参数；P2 为 handoff 元数据过期。Correction 1 source `cafcde…` 是 `f8e336…` 的唯一后继，严格为 `cli.py`、对应离线
Fake 测试与 handoff 三路径，无依赖/Schema 改动。Correction 1 Reviewer evidence `48df2e…` 为 `REJECT`：argv 包含
判断误伤普通命令的合法参数值。Correction 2 source `b7cb846…` 是 `48df2e…` 的唯一后继，严格为 `cli.py`、对应离线
Fake 测试与 handoff 三路径，无依赖/Schema 改动。Correction 2 Reviewer evidence `010fb7…` 仅追加 handoff，
Verdict=`APPROVE`、P0–P3 均无。Product Integrator 已以 `--no-ff` merge
`e50b211c9214ef3e170c28d4f7bb6229c9f1c55b` 整合 B0：双父/accepted-source 祖先/六路径范围及无依赖、锁文件、
Schema/migration、`state.py` 改动均已核验；既有离线 Fake `13`、全量 `451`、mypy、Ruff、CLI help 与离线 build 均通过。
B0 现为 `DONE`，但这不是真实 smoke 或发布批准；TASK-014 仍为 `IN_PROGRESS` / `No-Go`。

## 状态定义

- `BLOCKED`：存在明确依赖或审批阻塞。
- `READY`：依赖和审批满足，可以由主控对话分配。
- `IN_PROGRESS`：已由一名执行者领取。
- `IN_REVIEW`：已提交证据，等待独立复核。
- `ACCEPTED`：独立审查和主控验收通过，等待整合。
- `DONE`：已整合到主线且整合后检查通过。

任务状态只由主控对话在主线更新。实现者和 Reviewer 通过 `handoffs/TASK-<id>.md` 报告，不直接修改公共任务状态。

## 任务表

| 任务 | 名称 | 负责人角色 | 当前状态 | 依赖 |
|---|---|---|---|---|
| [TASK-000](TASK-000-product-decisions.md) | 关闭 V1 开工决策 | PO + TL | DONE | 无 |
| [TASK-001](TASK-001-project-scaffold.md) | 工程脚手架与质量门禁 | Codex + Grok + Integrator | DONE | 000 |
| [TASK-002](TASK-002-config-domain-contracts.md) | 配置与领域契约 | Grok Implementer + 独立 Grok Reviewer + Integrator | DONE | 001 |
| [TASK-003](TASK-003-state-store.md) | SQLite 状态存储 | Codex Implementer + 独立 Grok Reviewer + Codex Integrator | DONE | 002 |
| [TASK-004](TASK-004-discovery-metadata.md) | 频道发现与元数据 | Codex Integrator merge `dc3f097...` | DONE | 002 |
| [TASK-005](TASK-005-subtitle-pipeline.md) | 字幕获取与规范化 | 已整合并关闭；merge `cfc302...` | DONE | 003, 004 |
| [TASK-005A](TASK-005A-local-model-shared-contracts.md) | 本地模型共享契约 | 已整合并关闭；merge `865f4fed...` | DONE | 005 |
| [TASK-006](TASK-006-local-transcription.md) | 本地 Whisper 转写 | 已整合并关闭；merge `fd9a074...` | DONE | 005A；模型/ffmpeg/媒体另批 |
| [TASK-007](TASK-007-local-scoring.md) | Ollama 本地评分 | 已整合并关闭；merge `3d49ec...` | DONE | 005A；Ollama/模型另批 |
| [TASK-008A](TASK-008A-cloud-analysis-shared-contracts.md) | 云分析共享契约与依赖基线 | 已整合并关闭；merge `64a9c416...` | DONE | 007；BPE NOTICE/license 留待 TASK-014 |
| [TASK-009A](TASK-009A-obsidian-note-shared-contracts.md) | Obsidian 共享契约与依赖基线 | 已整合并关闭；merge `9b0269...` | DONE | 008A |
| [TASK-008](TASK-008-deep-analysis.md) | 可选云端深度分析 | 已整合并关闭；merge `4f9ca390...` | DONE | 008A, 009A；真实云另批 |
| [TASK-009](TASK-009-obsidian-notes.md) | Obsidian 视频笔记 | 已整合并关闭；merge `1cb718b...` | DONE | 009A；真实 Vault 另批 |
| [TASK-010](TASK-010-orchestration-recovery.md) | 流程编排与恢复 | 已整合并收口；merge `3d2122c...` | DONE | 003-009 |
| [TASK-011](TASK-011-weekly-report.md) | 周报 | 已整合并关闭；merge `2ba42c2...` | DONE | 009, 010 |
| [TASK-012](TASK-012-cli-operations.md) | CLI、调度与日志 | 已整合并关闭；merge `4841cf8...` | DONE | 010, 011 |
| [TASK-013A](TASK-013A-local-transcription-continuation.md) | 本地转写持续处理 | 已整合并关闭；merge `8f70fe3...` | DONE | 006, 010 |
| [TASK-013](TASK-013-e2e-acceptance.md) | 端到端验收 | 已整合并关闭；merge `efb3034...` | DONE | 011, 012, 013A |
| [TASK-014](TASK-014-release-readiness.md) | 发布准备（Phase A 资料已整合；B10-classified 真实 smoke `FAIL`） | PO + TL + QA 发布门禁；B3/B4/B5/B6/B7/B8/B10 已关闭，B9 与 B10-classified 失败 evidence 均未合并；B11 已验收待离线整合 | IN_PROGRESS / No-Go | 013 |
| [TASK-014B3](TASK-014B3-public-subtitle-directory-diagnostics.md) | 公开字幕目录兼容性诊断 | ADR-015 已接受并已整合；merge `f5ebc87…` | DONE | 014；ADR-015 |
| [TASK-014B4](TASK-014B4-directory-only-public-subtitle-smoke.md) | 受限 directory-only 公开字幕 smoke | merge `133819f…`；离线 sync、Fake `18`、mypy、Ruff、CLI help、build、范围与泄漏扫描通过；source 保留 | DONE | 014；ADR-016；B0/B2/B3 DONE |
| [TASK-014B5](TASK-014B5-safe-smoke-summary-output.md) | 安全 smoke 摘要输出 | merge `41e9793…`；离线 lock/sync、Fake `19`、mypy、Ruff、CLI help、build、范围与 stdout/stderr/JSONL 泄漏扫描通过；source 保留 | DONE | 014；B3/B4 DONE |
| [TASK-014B6](TASK-014B6-safe-directory-shape-diagnostics.md) | 安全字幕目录结构诊断 | merge `f402400…`；离线 lock/sync、Provider/Smoke `104`、mypy、Ruff、CLI help、build、六路径范围与 stdout/stderr/JSONL/fixture 泄漏扫描通过；source 保留 | DONE | 014；B3/B4/B5 DONE；ADR-017 |
| [TASK-014B7](TASK-014B7-safe-directory-origin-fingerprint.md) | 字幕目录安全来源与结构指纹 | merge `81ee343…`；lock/sync、Provider/Smoke `114`、mypy、Ruff、CLI help、离线 build、范围与泄漏扫描通过；source 保留 | DONE | 014；B3/B4/B5/B6 DONE；ADR-018 |
| [TASK-014B8](TASK-014B8-restricted-directory-keyname-diagnostic.md) | 受限键名级字幕目录诊断 | merge `8bedbf1…`；lock/sync、focused `119`、full pytest `490`、mypy、Ruff、CLI help、offline build、范围与全输出面泄漏扫描通过；source 保留 | DONE | 014；B3/B4/B5/B6/B7 DONE；ADR-019 |
| [TASK-014B10](TASK-014B10-safe-content-availability-diagnostic.md) | 安全内容可用性诊断 | merge `5b485fa…`；lock/sync、focused `137`、full pytest `508`、mypy、Ruff、CLI help、offline build、五/三/handoff-only 范围、Diff 与全输出面泄漏扫描通过；失败补充探针未计 PASS，source 保留 | DONE | 014；B4/B5/B6/B7/B8 DONE；ADR-020 |
| [TASK-014B11](TASK-014B11-safe-directory-contract-diagnostics.md) | 安全字幕目录契约状态诊断 | Scout 报告 `11` 命中：`9` 个非新增 self-match、`2` 个新增 unknown；未确认真实凭据但风险未排除。Correction 2 仅授权两份 integration tests 与 handoff，须先安全分类，原 `f57b21c…` merge 继续阻断 | IN_PROGRESS / Codex | 014；B4/B5/B6/B7/B8/B10 DONE；ADR-021 |
| [TASK-014B0](TASK-014B0-restricted-public-subtitle-smoke-entry.md) | 受限公开字幕 smoke 组合入口 | 已整合并 closure；merge `e50b211…` | DONE | 014；ADR-013 |
| [TASK-014B2](TASK-014B2-console-entry.md) | 正式 console entry | 已整合并 closure；merge `99a22d…`；仅既有 CLI 入口的离线打包暴露 | DONE | 014；ADR-014 |
| [TASK-015](TASK-015-runtime-composition.md) | 正式 Runtime Composition 与 Local-First Smoke | merge `451766f…`；Maintainer APPROVE，675 tests | DONE | 013；ADR-022 |
| [TASK-016](TASK-016-intelligence-output.md) | Local / Hybrid / Cloud Intelligence 与中文知识输出 | Codex Orchestrator；Local-only 第一里程碑 | IN_PROGRESS | 015；ADR-023 |
| [TASK-016A](TASK-016A-intelligence-contract-foundation.md) | Intelligence Mode、配置与 Knowledge V2 契约基础 | UNASSIGNED | READY | 015；ADR-023 |

## 主控分配模板

主控对话将任务设为 `IN_PROGRESS` 时必须记录：

```text
Task: TASK-XXX
Agent/role: <Codex|Grok Build>/<Implementer|Reviewer|Integrator>
Base: <branch>@<commit>
Worktree: <absolute path>
Branch: <branch>
Allowed scope: <task card or files>
Required checks: <commands>
Special approvals: <none or links>
Reuse decision: <DIRECT | ADAPT | REFERENCE | REJECT/DEFER + source/version>
```

实现者使用 `handoffs/TEMPLATE.md` 建立任务交接报告。Reviewer 只在实现 commit 之后启动，并在交接报告给出 `APPROVE` 或 `REJECT`。

只有 Reviewer 核对外部证据、主控验收、Integrator 整合到主线并通过整合后检查，任务才能设为 `DONE`。完整规则见 `docs/COLLABORATION.md`。
