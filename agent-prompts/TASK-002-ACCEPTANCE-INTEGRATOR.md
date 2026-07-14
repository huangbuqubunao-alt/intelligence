# TASK-002 Acceptance Status Integrator Packet

## 身份与边界

你是原 Status Integrator。本轮只验证并提交主控对 TASK-002 的 `ACCEPTED` 状态和验收记录；不得合并产品分支、运行产品代码或写 TASK-002 worktree。

## 固定基线

- Task: `TASK-002 acceptance sync`
- Role: `Status Integrator`
- Required base: `main@311412acfe3e276268ce0c6ffd359f9b044697c0`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-002 worktree: `/Users/hua/Documents/yia-worktrees/task-002`，严格只读
- Required branch: `grok/task-002-config-domain-contracts`
- Required review/source head: `d98de3537187ac346e404d7899d0a9d90c228483`
- Reviewed implementation source: `8f50df2f7e93d778f32947ca471740b6713c9aff`

## 唯一允许提交的 4 个文件

- `agent-prompts/TASK-002-ACCEPTANCE-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`

初始状态不是精确这 4 个文件、已有 staged 内容、main HEAD 不符、TASK-002 worktree 不干净或 review head 不符时立即停止。

## 必查事实

- TASK-002 为 `ACCEPTED`，不是 `DONE`；尚未合并产品代码。
- review commit `d98de353...` 的父提交为 `8f50df2...`，且相对父提交只修改 `handoffs/TASK-002.md`。
- Reviewer 为全新独立 Grok 会话，Verdict=`APPROVE`；AC-1 至 AC-8 全 PASS，必需检查无跳过，P0/P1/P2 均无。
- P3 `MappingProxyType` live view 被记录为非阻断风险；公共写入仍被拒绝。
- source 从 `46f8497e...` 到 `8f50df2...` 的范围仍恰好是批准 8 文件；review commit 只追加交接证据。
- TASK-003/TASK-004 仍为 `BLOCKED`，必须等待 TASK-002 合并并关闭为 `DONE`。
- Git `user.useConfigOnly=true`，Author/Committer 不得出现 `.local` 邮箱。
- 本轮没有依赖、锁文件、产品代码、真实 Vault/密钥、网络调用或 worktree 写操作。

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
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-list --parents -n 1 d98de3537187ac346e404d7899d0a9d90c228483
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --name-status 8f50df2f7e93d778f32947ca471740b6713c9aff..d98de3537187ac346e404d7899d0a9d90c228483
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --name-status 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --check 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
```

只暂存上述 4 个文件，运行 `git diff --cached --check` 和 `git diff --cached --name-only`。提交消息：

```text
docs: accept TASK-002 for integration
```

提交后运行：

```bash
git status --short
git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>'
```

不得合并 `d98de353...`、启动 TASK-003/004、修改准备内容、运行测试或写 TASK-002 worktree。

## 返回格式

```text
Task: TASK-002 acceptance sync
Role: Status Integrator
Base:
Head commit:
Git author/committer identity:
Checks:
Committed files:
TASK-002 review/source/status:
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
