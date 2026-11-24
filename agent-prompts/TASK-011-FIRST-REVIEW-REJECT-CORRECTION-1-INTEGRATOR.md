# TASK-011 first review reject / Correction 1 sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@8d7eaffd5b790b2ffd964793557d1b8f20168978`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@3759d54a74abaa8e6627b8107298d0938fbe3441`，必须干净。
- Reviewer evidence：`3759d54...` 唯一父为 implementation `0ae7f936...`，只修改 source handoff。
- Original base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；完整 source Diff 仍限七个实际批准路径，锁文件未变。

## 审查拒绝事实

- Verdict=`REJECT`，P0=0、P1=1。Reviewer 在 P1 后停止，后续门禁/探针未运行，不得写为通过。
- P1：周报没有实现 ADR-010 W-03 的趋势聚合；关键词和持续关注方向只读取 `ScoreResult.topics`，忽略已验证的 `AnalysisResult`。周报必须只从验证的 Analysis/Score/NoteRef 聚合，且趋势、关键词、持续方向算法稳定、确定性、可测试。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-011-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

不得访问、修改或创建 TASK-012 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、evidence handoff-only scope、完整 source 范围与未变锁文件。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-011 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 1；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-012 保持 BLOCKED。
5. 提交信息：`docs: return TASK-011 for analysis trend correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 1 边界

- 只授权 source `reporting.py`、`test_week_period.py`、`test_weekly_report.py` 和 `handoffs/TASK-011.md`。
- 趋势、关键词和持续关注方向必须以受验证的 `AnalysisResult` 为必要输入，并在已有 Score/NoteRef 资格后再聚合；忽略或安全拒绝缺失、篡改或不匹配的分析，不得降级为只用 `ScoreResult.topics`。
- 算法必须确定性，明确标准化、排序、并列与空周行为；不得调用任何模型、Provider、网络或真实 Vault。保留 ISO 周、候选资格、稳定 upsert、模板和临时 Vault 原子写/补偿回归。
- 不得扩展 `state.py`、`providers/obsidian.py`、模板、依赖/锁、Schema/migration、`complete_stage`、CLI、TASK-012 或真实资源。若现有公开契约不足，报告 `DECISION NEEDED`。

## 回传格式

```text
Task: TASK-011 first review reject / Correction 1 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-011=IN_PROGRESS
Committed files: <exact five>
Checks: <Git-only gates>
TASK-012 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
