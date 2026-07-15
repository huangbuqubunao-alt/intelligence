# TASK-003 Integration Authorization + TASK-004 Reject Sync — Status Integrator Packet

你是 Status Integrator。唯一任务是在 main 同步 TASK-004 第二次独立审查 `REJECT` 并授权原 Grok correction 4，同时提交 TASK-003 最终产品 Integrator 包。不得实现产品代码、运行产品检查、安装依赖、进入 source worktree、启动任何 Agent 或执行 merge。

## 固定上下文

- Main base: `main@fb1cdd728081c9c1ae0c0bcb82b7490332090b28`
- TASK-003 accepted source/review head: `codex/task-003-state-store@f07795f854e02b15e8c438622042e360b7c0e8b9`
- TASK-003 remains `ACCEPTED`，尚未合并或关闭
- TASK-004 second review source/evidence: `grok/task-004-discovery-metadata@5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`
- TASK-004 reviewed implementation parent: `30932e1742e948683f9e1c0f63236451b8d731bd`
- TASK-004 target: `IN_PROGRESS`，原 Grok correction 4 等待启动

完整读取 main 的 `AGENTS.md`、协作/状态文档、两张 TASK 卡、`TASK-003-INTEGRATOR.md`、`TASK-004-CORRECTION-4-GROK.md` 与本包。

## 唯一允许范围：精确 7 个文件

- `agent-prompts/TASK-003-INTEGRATION-AND-TASK-004-REJECT-INTEGRATOR.md`
- `agent-prompts/TASK-003-INTEGRATOR.md`
- `agent-prompts/TASK-004-CORRECTION-4-GROK.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

main 初始 HEAD 必须为 `fb1cdd7...`；准备内容必须精确属于这 7 个文件，无预先暂存和无范围外未暂存内容。不得修改 handoff、产品源码、依赖、锁文件、ADR、其他任务卡或 source worktree。

## 必查事实

1. 身份为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。
2. TASK-003 source worktree 只读且干净，HEAD `f07795...`；仍为 `ACCEPTED`，TASK-003 Integrator 包只授权后续 non-fast-forward merge 与任务卡门禁，不能在本轮执行 merge 或改 `DONE`。
3. TASK-004 source worktree 只读且干净，HEAD `5d66c28...`；review evidence 父提交必须为 `30932e1...` 且只修改 handoff。完整 Diff 相对 `dcc7d85...` 仍为 17 个批准文件。`REJECT` 的 P1 必须逐字准确：非法 `age_limit` 的 `AppError.video_id` 为 None；RSS entry 缺 channelId 被请求 channel 回填，造成 candidate/cursor 提交。不得把它们写成已修复。
4. correction 4 只允许五个既有 TASK-004 文件；TASK-003 Integrator 和 TASK-004 correction 4 在本次同步提交后可并行启动，但不得同时写 main。

只运行控制面 Git 检查：

```bash
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git diff --check
git diff --name-only
git -C "/Users/hua/Documents/yia-worktrees/task-003" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-003" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-004" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-004" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-004" rev-list --parents -n 1 5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58
git -C "/Users/hua/Documents/yia-worktrees/task-004" diff --name-status 30932e1742e948683f9e1c0f63236451b8d731bd..5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58
git diff --cached --check
git diff --cached --name-only
```

不得运行 uv、pytest、Ruff、mypy、build、数据库或网络。建议提交：

```text
docs: return TASK-004 fixes and authorize TASK-003 integration
```

提交后 main 必须干净；只读确认两个 source worktree 未变且干净。返回 Task、Role、Base、Head、identity、Committed files、checks、TASK-003 status/integrator、TASK-004 status/source、Verdict、remaining risks。
