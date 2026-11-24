# TASK-011 second review reject / Correction 2 sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@0bc9950d9818c739f5932d884d4803634d60eea7`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@6f9c75df90e10b964b36dbcefc52618422d83216`，必须干净。
- Reviewer 2 evidence `6f9c75d...` 的唯一父为 Correction 1 `f4e30a56ddcf7d654bda4e0579f6080af59698f5`，且只修改 source handoff；Correction 1 的唯一父为 Reviewer 1 evidence `3759d54...`。
- Original base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；完整 source Diff 仍限七个实际批准路径，锁文件未变。

## 审查拒绝事实

- Verdict=`REJECT`，P0=0、P1=1。Reviewer 2 在 P1 后停止，未完成的包内容与 Vault 故障矩阵不得写为通过。
- P1：`reporting.py` 只使用索引行构造视频 `NoteRef`，未验证受管 `Videos/...` 文件存在、锚定路径/symlink 安全和内容 SHA-256；缺失或篡改笔记仍可写入无效周报链接，违反 ADR-010 W-02/W-03 与 fail-closed 条件。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-SECOND-REVIEW-REJECT-CORRECTION-2-INTEGRATOR.md`
2. `agent-prompts/TASK-011-CORRECTION-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

不得访问、修改或创建 TASK-012 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、Reviewer evidence handoff-only scope、完整 source 范围与未变锁文件。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-011 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 2；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-012 保持 BLOCKED。
5. 提交信息：`docs: return TASK-011 for note integrity correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 2 边界

- 只授权 source `reporting.py`、`test_week_period.py`、`test_weekly_report.py` 和 `handoffs/TASK-011.md`。
- 在任何 Knowledge Sink 或 reports 写入前，受管视频 NoteRef 必须验证：相对且受锚定的路径、无 symlink/路径逃逸、常规文件存在、索引 identity/provenance 与文件内容 SHA-256 一致；缺失、篡改、类型或身份不匹配均 fail-closed，且无 Vault/reports 写入。
- 仅扩展 pytest `tmp_path` 最小 Vault 回归，保留 W-01..W-07、Analysis-only 聚合、稳定 upsert 与 DB 补偿；不得调用模型、Provider、网络或真实 Vault。
- 不得扩展 `state.py`、`providers/obsidian.py`、模板、fixtures、依赖/锁、Schema/migration、`complete_stage`、CLI、TASK-012 或真实资源。若现有冻结对象不足，报告 `DECISION NEEDED`。

## 回传格式

```text
Task: TASK-011 second review reject / Correction 2 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-011=IN_PROGRESS
Committed files: <exact five>
Checks: <Git-only gates>
TASK-012 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
