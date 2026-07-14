# TASK-002 Reviewer Reassignment Status Integrator Packet

## 身份与边界

你是原 Status Integrator。本轮只验证并提交主控已准备的 TASK-002 Reviewer 改派：从尚未启动的 Codex 改为全新独立 Grok 会话。不得修改内容、运行产品代码或写 TASK-002 worktree。

## 固定基线

- Task: `TASK-002 reviewer reassignment sync`
- Role: `Status Integrator`
- Required base: `main@68ce933d9653be979503fc215039a4a232cf007e`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-002 worktree: `/Users/hua/Documents/yia-worktrees/task-002`，严格只读
- Required branch: `grok/task-002-config-domain-contracts`
- Required source head: `8f50df2f7e93d778f32947ca471740b6713c9aff`

## 唯一允许提交的 6 个文件

- `agent-prompts/TASK-002-REVIEWER-CODEX.md`
- `agent-prompts/TASK-002-REVIEWER-GROK.md`
- `agent-prompts/TASK-002-REVIEWER-REASSIGNMENT-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`

初始状态不是精确这 6 个文件、已有 staged 内容、main HEAD 不符、TASK-002 worktree 不干净或 source head 不符时立即停止。

## 必查事实

- TASK-002 保持 `IN_REVIEW`；Implementer 已停止写入。
- Codex Reviewer 从未启动，旧包明确为 `SUPERSEDED`；活动 Reviewer 是全新独立 Grok 会话。
- Grok Reviewer 不得复用 Implementer 上下文，只能写 `handoffs/TASK-002.md`，且必须设计两个独立反例/探针。
- source head、父链和 8 文件范围不变；TASK-003/TASK-004 仍为 `BLOCKED`。
- Git 仓库身份已由主控配置；`user.useConfigOnly=true`，提交身份不得再出现 `.local` 邮箱。不得在本轮修改 Git 配置。
- 没有依赖、锁文件、产品代码、真实 Vault/密钥、网络调用或 worktree 写操作。

## 检查与提交

依次运行：

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

`user.useConfigOnly` 不是 `true`、Author/Committer 为空或包含 `.local` 时停止；不得自行改配置。

只暂存上述 6 个文件，运行 `git diff --cached --check` 和 `git diff --cached --name-only`。提交消息：

```text
docs: reassign TASK-002 review to Grok
```

提交后运行：

```bash
git status --short
git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>'
```

不得改动准备内容、启动 Reviewer、安装依赖或写 TASK-002 worktree。

## 返回格式

```text
Task: TASK-002 reviewer reassignment sync
Role: Status Integrator
Base:
Head commit:
Git author/committer identity:
Checks:
Committed files:
TASK-002 source/status:
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
