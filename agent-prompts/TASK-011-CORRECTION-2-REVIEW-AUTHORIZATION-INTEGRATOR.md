# TASK-011 Correction 2 review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@38d21bd5bfd3518cc0dde430b534c38ccc7f4013`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@0f589aca501ea4559aeb7f4dd7aeab2a41f52b79`，必须干净。
- Correction 2 唯一父为 Reviewer 2 evidence `6f9c75df90e10b964b36dbcefc52618422d83216`，后者唯一父为 Correction 1 `f4e30a56ddcf7d654bda4e0579f6080af59698f5`，且只修改 source handoff。
- Original base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；完整 source Diff 仍限七个实际批准路径，锁文件未变。

## Correction 2 证据与复审边界

- Implementer 报告在渲染或 Knowledge Sink/reports 写入前，以锚定目录 FD、`O_NOFOLLOW`、普通文件检查、受控读取和 SHA-256 比对验证每个受管视频 NoteRef，拒绝缺失、篡改、symlink、路径逃逸与 artifact provenance mismatch。
- 自报 focused unit=`2`、integration=`13`、full pytest=`414`、mypy、Ruff、CLI、locked sync、offline build 与 package inclusion PASS。这些均为待独立复跑证据，不得预写 Reviewer verdict。
- Reviewer 3 只能追加 source `handoffs/TASK-011.md`，必须复跑离线门禁、W-01..W-08、AC、P1 反例与五轴审查；不得改业务代码、依赖、锁、main 或任务状态。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-CORRECTION-2-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-011-REVIEWER-3-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

不得访问、修改或创建 TASK-012 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、Correction 2 范围、完整 source 范围与未变锁文件。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-011 设为 `IN_REVIEW`，授权全新独立 Reviewer 3；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-012 保持 `BLOCKED/UNASSIGNED`。
5. 提交信息：`docs: authorize TASK-011 note integrity review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-011 Correction 2 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-011=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
TASK-012 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
