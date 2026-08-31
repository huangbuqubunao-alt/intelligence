# V1 Release Checklist

- 当前结论：`NO-GO — 2026-08-31 final sign-off completed; mandatory release gates remain blocked`
- 签署责任：PO、TL、QA、隐私 Reviewer；任何一方未签字或任一红线未满足即为 No-Go。
- 禁止误读：本检查表不执行真实 smoke，不批准发布，不改变任务状态。

## 发行身份与范围

| 项目 | 状态 | 签署/证据要求 |
|---|---|---|
| 版本、commit、Schema 版本和目标发行形态已冻结 | BLOCKED | TL 记录候选 commit、版本、`001_initial.sql` 对应 Schema 记录与发行形态。 |
| 发行物不含密钥、真实响应、私人字幕、真实 Vault/用户笔记 | BLOCKED | QA 对最终候选物执行经批准的凭据/内容审查。 |
| `.gitignore` 根目录边界 | PASS（静态） | `/data/`、`/logs/` 仅匹配仓库根；仍须由 QA 在最终候选树复核无误忽略夹具/资源/文档。 |
| README、运维说明和实际 CLI/Schema 一致 | BLOCKED | QA 在获批的干净环境和临时配置中核对；本阶段未运行 CLI。 |

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
| Vault、模板和日志边界 | PASS（技术证据；独立隐私签字仍 OPEN） | [Vault/template privacy review](VAULT_TEMPLATE_PRIVACY_REVIEW.md) 以临时 Vault、静态模板、合成哨兵和新鲜离线归档确认无真实 Vault/用户内容、无用户模板、无敏感日志/凭据值进入 wheel/sdist；不构成独立人类 Privacy Reviewer 签字。 |
| at-most-once 风险披露 | BLOCKED | PO 明确接受或拒绝三处残余崩溃窗口：Provider→SQLite、replace→SQLite、音频 cleanup 最终 CAS。不得声明 exactly-once。 |
| 备份/恢复演练 | BLOCKED | 在隔离临时 SQLite/DATA/Vault 完成、保留命令/结果；绝不覆盖真实数据或 Vault。 |

## 验证与 smoke

| 项目 | 状态 | 必要条件 |
|---|---|---|
| 离线测试、类型、lint、构建 | 已有历史离线证据；本阶段未复跑 | QA 在正式授权后运行任务卡指定命令，并记录确切版本与结果。 |
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
- The remaining mandatory gates are project/distribution licensing and notices, a qualified live Deep
  Analysis provider plus Product Owner output acceptance before TASK-016G, a cleanly closed global security
  scan, required Security/Privacy/PO/TL signatures and at-most-once acceptance, and authorized operational
  smoke/recovery/Vault validation. No push, tag, or public release occurred.

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
  a general exception, cover a new finding, authorize broader distribution, or
  satisfy the separate final human-signature gate.

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
- This is not a named independent human Security Reviewer signature and does not
  close the final signature table, provider qualification, privacy, operations,
  or any broader distribution gate.

## 最终签署记录（发布前填写）

| 角色 | 决定（GO / NO-GO） | 姓名/日期 | 证据链接与限制 |
|---|---|---|---|
| PO | 未签署 |  |  |
| TL / 发布负责人 | 未签署 |  |  |
| QA | 未签署 |  |  |
| 隐私 Reviewer | 未签署 |  |  |

只有四项均为 `GO`、所有 `BLOCKED` 项有可审计的关闭证据、且发布形态与 SBOM/NOTICE
一致时，才可由主控另行决定发布。否则维持 `NO-GO` 并开立范围明确的后续任务。
