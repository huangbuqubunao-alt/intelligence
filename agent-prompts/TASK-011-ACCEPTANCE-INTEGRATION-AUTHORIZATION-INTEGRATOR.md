# TASK-011 acceptance / final integration authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@6bc019d4d7ad0e1d04a05bdcece376ea02e7cd7f`，必须干净且为唯一父基线。
- Accepted source：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@1ecd4bc8c6138bab6683a011cbbecddf281263c3`，必须干净。
- Reviewer 3 evidence `1ecd4bc...` 的唯一父为 Correction 2 `0f589aca501ea4559aeb7f4dd7aeab2a41f52b79`，且只修改 source handoff；上游审查/修复链均为单父。
- Original base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；完整 source Diff 严格为七个实际批准路径，锁文件未变。

## 验收事实

- Reviewer 3 verdict=`APPROVE`，P0/P1/P2/P3=0；ADR-010 W-01..W-08 与 TASK-011 AC 均 PASS。
- 独立证据包含 locked sync、focused=`15`、full pytest=`414`、mypy、Ruff、CLI、offline build、sdist/wheel migration/video/weekly template inclusion，以及临时 SQLite/Vault 的 NoteRef 锚定/哈希、repeated upsert、原子失败补偿探针。
- 上述为既有审查证据；本控制面角色不得重新运行产品命令。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-011-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

不得访问、修改或创建 TASK-012 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、Reviewer evidence handoff-only scope、完整 source 范围与未变锁文件。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-011 设为 `ACCEPTED`，授权 Product Integrator；不得预写 merge SHA 或 DONE。TASK-012 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: accept and authorize TASK-011 integration`。提交后 main/source 必须干净，并确认 Integrator prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-011 acceptance / final integration authorization sync
Base / Head: <base> -> <head>
Review/source/status: <evidence>; TASK-011=ACCEPTED
Committed files: <exact five>
Checks: <Git-only gates>
TASK-012 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
