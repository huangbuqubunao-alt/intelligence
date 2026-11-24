# TASK-014B0 Correction 2 — Codex Implementer（仅实际 smoke 子命令拒绝配置输入）

你是 TASK-014B0 的原 Codex Implementer，只处理 Correction 1 Reviewer `REJECT` 的 Correction 2。本包只登记正式
修复分配；它本身不启动 Implementer。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、
`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、
`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、
`tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`、ADR-013、前两轮 Implementer/Reviewer 包、source
`handoffs/TASK-014B0.md` 与本包。如任一文件冲突，停止并报告。

## 固定分配

```text
Task: TASK-014B0 Correction 2 — reject configuration inputs only for the actual smoke subcommand
Role: Original Implementer
Agent: Codex
Control-plane base: main@931b872a933709fb696b6495b61e2f37a4a9f9eb
Only source worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke
Source branch: codex/task-014-phase-b0-restricted-public-subtitle-smoke
Correction base/source HEAD: 48df2e2a0afb54d5f6252f197dddf32ff685f0db
Required sole parent of correction commit: 48df2e2a0afb54d5f6252f197dddf32ff685f0db
Correction 1 review evidence: 48df2e2a0afb54d5f6252f197dddf32ff685f0db (REJECT; P1)
Reuse decision: DIRECT — existing argparse surface, locked smoke runner, Python standard library and existing offline Fake tests; no new or copied third-party code
```

## Correction 2 目标

只关闭已确认的 P1：当前实现把 argv 中任何 `smoke-public-subtitles` 字符串当作 active command，误伤普通命令的合法
参数值。必须先在不读取配置、不构造 smoke runner、不初始化临时根的前提下识别已解析的实际子命令；只有该子命令是
`smoke-public-subtitles` 时，才拒绝 `--project-root`、`--settings`、`--channels`（包括命令前后、分离值与
`--flag=value` 形式）。

`check/process/retry/weekly/doctor` 允许其合法参数值为 `smoke-public-subtitles`，且保持原有解析、配置及默认
fail-closed 语义。不得通过任意 argv 字符串包含、子串或值猜测实现。保留 smoke 的 1–3 ID/临时根、一次调用、无重试、
正文不落盘、脱敏、零业务记录和所有禁止资源边界。

## 唯一允许修改范围

1. `src/youtube_intel/cli.py`
2. `tests/integration/test_public_subtitle_smoke.py`
3. `handoffs/TASK-014B0.md`

不得修改任何其他 source 路径，包括 `public_subtitle_smoke.py`、`test_operations.py`、`docs/operations.md`、Provider
Adapter、`state.py`、domain/config、Schema/migration、依赖、锁文件、任务/状态控制面、LICENSE 或 B-1 evidence。
范围不足时停止并报告 `DECISION NEEDED`。

## 禁止事项与交付

不联网、不运行真实 B-1 smoke、不读配置/YAML/环境值/凭据/Cookie/真实 Vault/用户数据；不下载媒体或调用 ffmpeg、
Whisper、模型、Ollama、OpenAI、付费服务或 launchd；不新增依赖、不改 Schema/migration、默认 CLI/Pipeline/Job/
Repository 语义、发布状态或 Go/No-Go；不合并、push、rebase、reset、清理或启动 Reviewer。

仅添加最小离线 Fake 回归：普通命令把 `smoke-public-subtitles` 作为合法选项值时不被全局配置拒绝；实际 smoke 的
三项配置输入拒绝仍在 runner/Adapter/临时根前触发。后续正式启动的 Implementer 回合才可运行任务卡已有离线检查；
不得联网。提交前核验 `48df2e…...HEAD` 严格只有三条授权路径、无依赖/Schema 改动、`git diff --check` 与工作树状态；
更新 handoff 的 Correction 2 实际 SHA/状态后提交。不得自行将 TASK-014B0 标为 `IN_REVIEW`、`ACCEPTED` 或 `DONE`。
