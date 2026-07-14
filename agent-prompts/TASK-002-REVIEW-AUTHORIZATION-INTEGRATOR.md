# TASK-002 Review Authorization Status Integrator Packet

## 身份与边界

你是原 Status Integrator。本轮只验证并提交主控已准备的 TASK-002 修复记录、`IN_REVIEW` 状态和 Reviewer 包；不修改内容、不运行产品代码、不进入 TASK-002 worktree 写入。

## 固定基线

- Task: `TASK-002 review authorization sync`
- Role: `Status Integrator`
- Required base: `main@0fc7c84a786651d3fdf75c0f3007ba569600326c`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-002 worktree: `/Users/hua/Documents/yia-worktrees/task-002`，严格只读
- Required branch: `grok/task-002-config-domain-contracts`
- Required source head: `8f50df2f7e93d778f32947ca471740b6713c9aff`
- Required code evidence commit: `8492c42b971b01d3aaf4e6cb11e2e5a8210fe46a`

## 唯一允许提交的 6 个文件

- `agent-prompts/TASK-002-CORRECTION-GROK.md`
- `agent-prompts/TASK-002-REVIEWER-CODEX.md`
- `agent-prompts/TASK-002-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`

初始状态不是精确这 6 个文件、已有 staged 内容、main HEAD 不符、TASK-002 worktree 不干净或 source head 不符时立即停止。不得自行取消、覆盖或吸收其他修改。

## 必查事实

- TASK-002 为 `IN_REVIEW`；Grok 已停止写入，Codex 是唯一待启动 Reviewer。
- 父链为 base `46f8497e...` → 原实现 `4355a59...` → 修复代码 `8492c42...` → 交接证据 `8f50df2...`。
- `46f8497e...8f50df2...` 总范围仍恰好是原批准 8 文件，且任务 worktree 干净。
- 修复记录覆盖密钥样式输入脱敏、公共自由 `dict`、可变公共转换表和额外 `ErrorCode`；没有把 Reviewer 结论预写为 APPROVE。
- Reviewer 只允许写 `handoffs/TASK-002.md`，且必须独立重跑检查、评估 Provider 元数据契约。
- TASK-003/TASK-004 仍为 `BLOCKED`；没有依赖、锁文件、产品代码、真实 Vault/密钥、网络调用或 worktree 写操作。

## 检查与提交

依次运行：

```bash
git rev-parse HEAD
git status --short
git diff --check
git diff --name-only
git -C "/Users/hua/Documents/yia-worktrees/task-002" branch --show-current
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-002" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-list --parents -n 1 4355a59f6f95e409bcf15b3b8004bb112d0033b3
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-list --parents -n 1 8492c42b971b01d3aaf4e6cb11e2e5a8210fe46a
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-list --parents -n 1 8f50df2f7e93d778f32947ca471740b6713c9aff
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --name-status 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --check 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
```

只暂存上述 6 个文件，运行 `git diff --cached --check` 和 `git diff --cached --name-only`。提交消息：

```text
docs: authorize TASK-002 independent review
```

提交后运行 `git status --short`。不得改动准备内容、启动 Reviewer、安装依赖或写 TASK-002 worktree。

## 返回格式

```text
Task: TASK-002 review authorization sync
Role: Status Integrator
Base:
Head commit:
Checks:
Committed files:
TASK-002 source chain/scope/status:
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
