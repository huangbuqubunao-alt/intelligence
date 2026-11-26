# TASK-011 implementation evidence / review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@0aa7e8d607656ded7c47c017ad1387bf361781b4`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`，必须干净。
- Implementation 唯一父为固定 base `44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；完整 Diff 精确为 `reporting.py`、`state.py`、`providers/obsidian.py`、`templates/weekly.md`、两份既定 tests 和 source handoff，未改依赖/锁。
- Source 的 `IN_PROGRESS` 卡是分配 base 快照；实时状态仅以 main 本提交为准。

## 实现证据与审查边界

- Implementer 自报确定性 ISO 周报、候选查询、验证的 NoteRef/Score/Analysis 聚合、固定 Jinja 模板、临时 Vault 原子 upsert、重复与 DB 失败补偿；focused=`2/3`、full pytest=`404`、mypy、Ruff、CLI、locked sync、offline build 与 package inclusion PASS。这些仅为待独立复跑证据。
- Reviewer 1 只可追加 source `handoffs/TASK-011.md`，复跑离线门禁与 ADR-010 矩阵；不得改业务代码、依赖、锁、main 或任务状态。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-011-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

不得访问、修改或创建 TASK-012 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、7 路径 source 范围与未变锁文件。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-011 设为 `IN_REVIEW`，授权全新独立 Reviewer；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-012 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: authorize TASK-011 independent review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-011 implementation evidence / review authorization sync
Base / Head: <base> -> <head>
Source/status: <source>; TASK-011=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
TASK-012 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
