# TASK-002 Final Integrator Packet Sync

## 身份与边界

你是原 Status Integrator。本轮只把最终产品 Integrator 包提交到 main，建立可审计的执行入口；不得合并 TASK-002、运行产品代码或写任务 worktree。

## 固定基线

- Task: `TASK-002 integrator-packet sync`
- Role: `Status Integrator`
- Required base: `main@1d8d16115173297aecb04a1a2ecfc2dc2927e3ff`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-002 worktree: `/Users/hua/Documents/yia-worktrees/task-002`，严格只读
- Required source/review head: `d98de3537187ac346e404d7899d0a9d90c228483`

## 唯一允许提交的 2 个文件

- `agent-prompts/TASK-002-INTEGRATOR-PACKET-SYNC.md`
- `agent-prompts/TASK-002-INTEGRATOR.md`

初始状态不是精确这 2 个文件、已有 staged 内容、main HEAD 不符、TASK-002 不是 `ACCEPTED`、source worktree 不干净或 source head 不符时立即停止。

## 必查事实

- 产品 Integrator 包以 acceptance commit `1d8d161...` 为 anchor，并要求执行时的 main HEAD 是“只新增本轮两个包文件”的单父提交。
- source head 固定为 `d98de353...`，不得改写、rebase 或再向 source 分支提交。
- TASK-002 仍为 `ACCEPTED`，不是 `DONE`；TASK-003/TASK-004 仍为 `BLOCKED`。
- 产品 Integrator 包要求非快进 merge commit、完整 uv 门禁、精确 8 文件范围和正确 Git 身份。
- 本轮不运行测试、不安装依赖、不执行 merge、不修改已有内容。

## 检查与提交

```bash
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git diff --check
git diff --name-only
git -C "/Users/hua/Documents/yia-worktrees/task-002" branch --show-current
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-002" status --short
```

`user.useConfigOnly` 不是 `true`、身份为空或含 `.local` 时停止。只暂存上述 2 个文件，运行 `git diff --cached --check` 和 `git diff --cached --name-only`。提交消息：

```text
docs: add TASK-002 final integration packet
```

提交后运行：

```bash
git status --short
git rev-parse HEAD
git rev-parse HEAD^
git diff --name-status 1d8d16115173297aecb04a1a2ecfc2dc2927e3ff..HEAD
git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>'
```

确认新提交的唯一父提交是 `1d8d161...`，且相对该 anchor 只新增本轮两个包文件。不得启动产品 Integrator。

## 返回格式

```text
Task: TASK-002 integrator-packet sync
Role: Status Integrator
Base:
Head commit:
Parent/packet scope:
Git identity:
Checks:
Committed files:
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
