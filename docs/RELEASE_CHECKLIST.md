# V1 Release Checklist

- 当前结论：`NO-GO — 2026-08-31 final sign-off completed; mandatory release gates remain blocked`
- 当前受控发行治理：依据 `RELEASE_GOVERNANCE_HUMAN_GATE_AUDIT.md` 的
  `026e9b8` 审计及其后的 PO 决定，独立 Security/Privacy Reviewer、单独 TL、单独
  QA 和多角色签署表均为未来触发控制，不是当前阻塞项。技术证据与明确的 PO
  授权仍为强制条件。
- 禁止误读：本检查表不执行真实 smoke，不批准发布，不改变任务状态。

## 发行身份与范围

| 项目 | 状态 | 签署/证据要求 |
|---|---|---|
| 版本、commit、Schema 版本和目标发行形态已冻结 | BLOCKED | 记录候选 commit、版本、`001_initial.sql` 对应 Schema 与发行形态；当前不要求单独 TL。 |
| 发行物不含密钥、真实响应、私人字幕、真实 Vault/用户笔记 | BLOCKED | 对最终候选物执行经批准的凭据/内容审查；当前不要求单独 QA。 |
| `.gitignore` 根目录边界 | PASS（静态） | `/data/`、`/logs/` 仅匹配仓库根；最终候选树仍须有可审计的忽略边界证据。 |
| README、运维说明和实际 CLI/Schema 一致 | BLOCKED | 在获批的干净环境和临时配置中核对；本阶段未运行 CLI。 |

## 供应链、许可证与 NOTICE

| 项目 | 状态 | 必要的书面结论 |
|---|---|---|
| SBOM-A/SBOM-B 覆盖当前目标 | PASS（当前受控边界） | Source/wheel/sdist physical content and the 74-package separately installed macOS-arm64 runtime inventory are frozen in `docs/SBOM.md`; dev-only tooling is excluded. |
| `yt-dlp[default,deno]` / `mutagen==1.48.1` | PASS（当前受控边界） | GPL-2.0-or-later Mutagen is a separately installed runtime transitive, not wheel/sdist content. Bundle/container/installer/dependency-copy distribution remains NOT AUTHORIZED pending a separate GPL compliance package. |
| OpenAI SDK、tiktoken、Jinja2、MarkupSafe 及传递项 | PASS（当前受控边界） | SBOM-B and NOTICE Set B preserve exact installed metadata/license evidence without claiming that the project physically redistributes those packages. |
| `o200k_base.tiktoken` | PASS（不随项目发行） | classification `C`、Blob 来源/哈希与下游权利未明的证据均保留。ADR-028 令 wheel/sdist/source artifact 不携带该文件；仅显式管理员预置副本可在本地通过固定哈希验证后使用。 |
| MLX Whisper、模型、ffmpeg、Ollama/qwen | BLOCKED / 条件性 | 明确是否完全排除；若包含，逐项完成许可证、模型来源、系统工具、程序/模型供应链审查。 |

## 安全、隐私与可靠性

| 项目 | 状态 | 验收条件 |
|---|---|---|
| 云端默认关闭与最小化出站数据 | BLOCKED | 审查 ADR-008 实现和最终配置；未启用时无云调用。 |
| SDK 隔离导入与匿名管道密钥 | BLOCKED | 确认主进程不导入 SDK；子进程仅白名单环境；密钥不进入 env/argv/文件/异常/日志。 |
| Vault、模板和日志边界 | PASS（技术证据；命名 Privacy Reviewer 当前 DEFERRED） | [Vault/template privacy review](VAULT_TEMPLATE_PRIVACY_REVIEW.md) 以临时 Vault、静态模板、合成哨兵和新鲜离线归档确认无真实 Vault/用户内容、无用户模板、无敏感日志/凭据值进入 wheel/sdist；当前不要求额外命名 Privacy Reviewer 签字，未来触发时重新评估。 |
| at-most-once 风险披露 | PASS（有限 PO 决定；Window 1 已修复） | PO 拒绝 Provider→SQLite 自动重复并授权完成 fail-closed remediation；replace→SQLite 与音频 cleanup 最终 CAS 仅在当前受控姿态接受。不得声明 exactly-once；实时 Provider qualification、真实输出接受和运行验证仍独立 BLOCKED。 |
| 备份/恢复演练 | PASS（M10 core；真实 pipeline 数据克隆） | [M10 验收记录](M10_BACKUP_RESTORE_ACCEPTANCE.md)。范围为 Intelligence 管理的 SQLite + DATA；Vault 明确排除。未执行物理断电演练，不据此宣称整个发行已 GO。 |

## 验证与 smoke

| 项目 | 状态 | 必要条件 |
|---|---|---|
| 离线测试、类型、lint、构建 | 已有历史离线证据；本阶段未复跑 | 保持任务卡指定的客观检查和确切版本/结果记录；当前不要求单独 QA。 |
| `doctor` | NOT RUN | 只使用批准的临时/示例配置；结果不得替代真实 Provider/Vault 验证。 |
| 四阶段真实 smoke | NOT AUTHORIZED | 必须逐阶段遵循 [授权矩阵](SMOKE_AUTHORIZATION_MATRIX.md)；无 PO 书面批准不执行。 |
| 真实 Vault、用户笔记和 launchd | NOT AUTHORIZED | 保持单独授权；不因其他 smoke 通过而隐含获批。 |

### TASK-014B9 final disposition — 2026-08-30

- Historical `e975ff4`/`bd770ef` and the distinct `d75988a..e5642fc` one-shot are consumed and preserved;
  their results remain `CONTENT_UNAVAILABLE` and `INVALID_RESPONSE` respectively, both `1/1/0`.
- The final product-owner closed-loop review made zero live calls. The current B9 package fixes its one
  candidate and forbids replacement expansion, so another candidate requires a new formal B9 contract and
  authorization package before execution. B9 remains `BLOCKED / NOT QUALIFIED` and is not release approval.

### TASK-014B9 ADR-022 replacement amendment — 2026-08-30

- ADR-022 preserves both consumed attempts and permits only this PO/TL-authorized, separately committed
  package for one fixed replacement sample. Selection is not qualification; no automatic replacement,
  fallback, iteration, retry, substitution, timeout escalation, or release conclusion is authorized.
- Directory-only, B11, fail-closed, safe-evidence, and validation requirements are unchanged. The one package
  remains `IN PROGRESS` until its frozen sample has exactly one recorded result.

### TASK-014B9 ADR-022 selection disposition — 2026-08-31

- The one permitted metadata-only discovery identified only the retired historical B9 sample. No eligible
  replacement was frozen, no B9 qualification was called, and B9 remains `BLOCKED / NOT QUALIFIED`.
- This result does not authorize another discovery, fallback, sample substitution, or smoke call. A future
  qualification requires a new explicit PO/TL package naming its candidate before execution.

### TASK-014B9 pre-frozen replacement nomination — 2026-08-31

- The nomination-only cycle used one legal metadata-only discovery round to pre-freeze `5MWT_doo68k`. It did
  not invoke the B9 path, enumerate subtitles, or read a body; qualification remains unknown and unexecuted.
- A prepared named-sample package is ready for separate PO execution authorization. It permits one
  directory-only call only, with no fallback, retry, substitution, timeout escalation, or release conclusion.

### TASK-014B9 final named-sample qualification — 2026-08-31

- The separately authorized, fixed `5MWT_doo68k` package was consumed once and passed: exit `0`,
  metadata/enumerate/read=`1/1/0`, safe `OK`. Its scoped smoke-root artifacts were removed after inspection.
- Historical attempts remain preserved. No scanner policy, B11 rule, or release criterion changed; B9 is
  `QUALIFIED / CLOSED`, but TASK-014 remains `IN_PROGRESS / No-Go` pending release checklist sign-off.

### Final release sign-off — 2026-08-31

- B9 is now integrated on `main@21bf38f` by a clean fast-forward; its evidence is not a public-release
  approval. The final review records `NO-GO`, `P0=0`, and five release-critical P1 gates in
  [RELEASE_SIGNOFF.md](RELEASE_SIGNOFF.md).
- Historical final-sign-off wording recorded then-current role requirements. For
  the current posture, the later PO policy defers named Security/Privacy/TL/QA
  roles and the multi-role table only; qualified-provider/output acceptance,
  at-most-once PO acceptance, operational authorization, technical validation,
  and distribution boundaries remain mandatory. No push, tag, or public release
  occurred.

### Canonical scanner fixture evidence — 2026-08-31

- The canonical scan remains exit `1` with exactly 11 intentional-positive
  TASK-016 test-fixture findings. The Product Owner / Tech Lead has accepted a
  finite exception for exactly this matrix and current controlled private
  source/wheel/sdist posture. The scanner is not PASS or globally clean.
- The completed technical matrix, acceptance conditions, re-review triggers,
  synthetic-secret/runtime tracing, wheel/sdist exclusion, and controlled-source
  nuance are in
  [SECURITY_SCANNER_FIXTURE_DISPOSITION.md](SECURITY_SCANNER_FIXTURE_DISPOSITION.md).
- This resolves the security technical release blocker only. It does not create
  a general exception, cover a new finding, or authorize broader distribution.
  Under the current PO policy, it also does not require a separate final
  multi-role signature table.

### First-party owner attribution — 2026-08-31

- The Product Owner records `墨竹` as the pseudonymous first-party owner/
  copyright attribution identifier for the current private, proprietary,
  controlled source/wheel/sdist posture. Root `NOTICE` and the NOTICE-based
  package metadata carry that limited attribution.
- This resolves current owner attribution only. It does not claim a verified
  legal name or entity, registration, IP assignment, trademark, or final release
  signature; verified legal identity remains a separate future gate when an
  action's governing policy requires it.

### ADR-008 cloud-SDK isolation technical review — 2026-08-31

- Technical review is **APPROVED** for the current controlled posture:
  [recorded evidence](ADR008_CLOUD_SDK_ISOLATION_SECURITY_REVIEW.md) confirms
  zero local/offline cloud client construction and network attempts, explicit
  consent/provider binding, pipe-only credentials, `max_retries=0`, and BPE
  fail-closed ordering where the local BPE gate applies.
- This is not a named independent human Security Reviewer signature. Under the
  current PO policy that separate role is deferred; this evidence does not close
  provider qualification, operational, or broader-distribution gates.

## 当前受控发行的最终授权

当前个人/私有/专有/受控 source-wheel-sdist 姿态不要求由不存在的独立 TL、QA、
Security Reviewer 或 Privacy Reviewer 填写组织角色表。该处理只来自 `026e9b8`
治理审计及其后的明确 PO 决定；不记录或伪造任何人的姓名、身份或签字。

| 当前要求 | 状态 | 证据链接与限制 |
|---|---|---|
| 客观技术、隐私、安全、包边界和运行门禁 | 仍须满足 | 本检查表、`RELEASE_BLOCKERS.md` 和各项技术审查记录。 |
| PO 产品/风险/真实副作用/发行范围授权 | 仍须在适用动作前明确记录 | 不能由 Codex 或已存在的技术证据替代。 |
| 命名独立 Security/Privacy、单独 TL/QA、多角色表 | 当前 DEFERRED | 发生 public/broader/commercial/contractual/team/legal/compliance 触发时重新确定适用角色。 |

当前项目只有在所有非 deferred `BLOCKED` 项有可审计的关闭证据、所选动作所需的明确 PO
授权已经记录、且发行形态与 SBOM/NOTICE 一致时，才可能从 `NO-GO` 变化；本政策本身不作
该授权。否则维持 `NO-GO` 并开立范围明确的后续任务。

## PO Decision Addendum — 2026-11-20 (Public Beta & Apache-2.0 Source Posture)

On `2026-11-20`, the Product Owner explicitly recorded the following scoped scope-and-distribution transition decisions on working branch `antigravity/task-user-readiness-20261112`:

1. **Open-source license adopted for source distribution**: First-party code adopts **Apache-2.0** ([`LICENSE`](../LICENSE) and [`NOTICE`](../NOTICE)), replacing the prior proprietary no-redistribution restriction. Third-party runtime dependencies (`yt-dlp` transitive `mutagen`, `ffmpeg`, `Ollama`, `mlx-whisper`, and `o200k_base.tiktoken`) remain unbundled and separately installed by the user/environment.
2. **Release posture upgraded to `PUBLIC_BETA`**: Core local-first Workspace AI Hub (`YouTube`, `Bilibili`, local `.mp4/.wav/.mp3/.m4a/.md/.txt` ingestion, Ollama / BYOK distillation, Weekly Brief, Topic Evolution, Cross-Video Grounded Q&A, Obsidian export, and backup/restore) transitions from `NO-GO` to `PUBLIC_BETA` (`GET /api/v1/system` reports `"release_posture": "PUBLIC_BETA"`).
3. **Governed multi-model Deep Analysis classified as `EXPERIMENTAL`**: Legacy governed multi-model Deep Analysis qualification gates (`TASK-016` / `"deep_analysis_tier": "EXPERIMENTAL"`) remain strictly fail-closed unless explicitly qualified by the operator, and no longer block the `PUBLIC_BETA` release of the main workbench.
4. **Cross-platform packaging**: `mlx-whisper` (Apple Silicon only) is moved from core `dependencies` into `[project.optional-dependencies].mac-whisper` in `pyproject.toml` so Linux, Windows, and Intel macOS environments can install core dependencies cleanly.
