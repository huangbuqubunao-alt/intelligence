# V1 Release Checklist

- 当前结论：`NO-GO — Phase A 仅建立资料与风险披露`
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
| SBOM 覆盖直接/传递锁定组件 | PARTIAL | 已有锁文件清单；TL 需将最终目标发行物的实际包含集、许可证、版权和 NOTICE 补齐。 |
| `yt-dlp[default,deno]` / `mutagen==1.48.1` | BLOCKED | TL/发布负责人决定 GPL-2.0-or-later 下的源码、二进制、bundle/容器分发方案。 |
| OpenAI SDK、tiktoken、Jinja2、MarkupSafe 及传递项 | BLOCKED | 确认 Apache-2.0/MIT/BSD-3-Clause 的现有证据、补齐 MarkupSafe 与所有实际包含传递项的证据/NOTICE。 |
| `o200k_base.tiktoken` | BLOCKED | PO/TL 对文件级来源、许可证、归属、NOTICE 与是否可进发行物签署。哈希和本地无网络回退不能替代此签署。 |
| MLX Whisper、模型、ffmpeg、Ollama/qwen | BLOCKED / 条件性 | 明确是否完全排除；若包含，逐项完成许可证、模型来源、系统工具、程序/模型供应链审查。 |

## 安全、隐私与可靠性

| 项目 | 状态 | 验收条件 |
|---|---|---|
| 云端默认关闭与最小化出站数据 | BLOCKED | 审查 ADR-008 实现和最终配置；未启用时无云调用。 |
| SDK 隔离导入与匿名管道密钥 | BLOCKED | 确认主进程不导入 SDK；子进程仅白名单环境；密钥不进入 env/argv/文件/异常/日志。 |
| Vault、模板和日志边界 | BLOCKED | 仅已授权临时 Vault 验证后，复核无真实 Vault/用户内容、无用户模板和无敏感日志。 |
| at-most-once 风险披露 | BLOCKED | PO 明确接受或拒绝三处残余崩溃窗口：Provider→SQLite、replace→SQLite、音频 cleanup 最终 CAS。不得声明 exactly-once。 |
| 备份/恢复演练 | BLOCKED | 在隔离临时 SQLite/DATA/Vault 完成、保留命令/结果；绝不覆盖真实数据或 Vault。 |

## 验证与 smoke

| 项目 | 状态 | 必要条件 |
|---|---|---|
| 离线测试、类型、lint、构建 | 已有历史离线证据；本阶段未复跑 | QA 在正式授权后运行任务卡指定命令，并记录确切版本与结果。 |
| `doctor` | NOT RUN | 只使用批准的临时/示例配置；结果不得替代真实 Provider/Vault 验证。 |
| 四阶段真实 smoke | NOT AUTHORIZED | 必须逐阶段遵循 [授权矩阵](SMOKE_AUTHORIZATION_MATRIX.md)；无 PO 书面批准不执行。 |
| 真实 Vault、用户笔记和 launchd | NOT AUTHORIZED | 保持单独授权；不因其他 smoke 通过而隐含获批。 |

### Phase B-1 directory-only public-subtitle execution — 2026-07-28

- Status: `FAIL / NO-GO`.
- The single authorized directory-only invocation for `--khbXchTeE` and `JTxsNm9IdYU`
  exited `1` after all three offline provisioning checks and absolute-launcher verification
  passed. No retry or alternative invocation was performed.
- The permitted sanitized output did not emit a fixed diagnostic code or per-ID counters;
  therefore this record does not infer the required `metadata=1 / enumerate=1 / read=0`
  budgets. See
  `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-DIRECTORY-ONLY-PUBLIC-YOUTUBE.md`.
- TASK-014 remains `IN_PROGRESS / No-Go`; no release, risk acceptance, or final Go is implied.

## 最终签署记录（发布前填写）

| 角色 | 决定（GO / NO-GO） | 姓名/日期 | 证据链接与限制 |
|---|---|---|---|
| PO | 未签署 |  |  |
| TL / 发布负责人 | 未签署 |  |  |
| QA | 未签署 |  |  |
| 隐私 Reviewer | 未签署 |  |  |

只有四项均为 `GO`、所有 `BLOCKED` 项有可审计的关闭证据、且发布形态与 SBOM/NOTICE
一致时，才可由主控另行决定发布。否则维持 `NO-GO` 并开立范围明确的后续任务。
