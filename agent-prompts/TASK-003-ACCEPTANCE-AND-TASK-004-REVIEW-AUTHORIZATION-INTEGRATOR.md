# TASK-003 Acceptance + TASK-004 Second Review Authorization — Status Integrator Packet

你是 Status Integrator。唯一任务是在 main 同步两项已经由主控决定的控制面事实：将 TASK-003 记录为 `ACCEPTED`，以及将 TASK-004 correction 3 记录为 `IN_REVIEW` 并提交一个全新独立 Codex Reviewer 包。不得实现产品代码、运行产品检查、安装依赖、进入任何 source worktree、启动 Reviewer 或合并分支。

## 固定上下文

- Main base: `main@375a5aa0f8ed319a6395c689167457f6625b8938`
- TASK-003 source/review head: `codex/task-003-state-store@f07795f854e02b15e8c438622042e360b7c0e8b9`
- TASK-003 reviewed implementation: `adab4bb00dd7e917b295c22fd8357a4f11515912`
- TASK-003 target: `ACCEPTED`，尚未合并，绝不得写为 `DONE`
- TASK-004 source head: `grok/task-004-discovery-metadata@30932e1742e948683f9e1c0f63236451b8d731bd`
- TASK-004 reviewed correction parent: `f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- TASK-004 target: `IN_REVIEW`，全新独立 Codex Reviewer 尚未启动；绝不得预写 `APPROVE`、`ACCEPTED` 或 `DONE`

完整读取 main 的 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`tasks/README.md`、两张 TASK 卡、`agent-prompts/TASK-004-IMPLEMENTATION-EVIDENCE-INTEGRATOR.md`、`agent-prompts/TASK-003-REVIEWER-GROK.md`、`agent-prompts/TASK-004-CORRECTION-3-GROK.md`、新的 `agent-prompts/TASK-004-REVIEWER-2-CODEX.md` 与本包。

## 唯一允许范围：精确 6 个文件

- `agent-prompts/TASK-003-ACCEPTANCE-AND-TASK-004-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-2-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

main 初始 HEAD 必须为 `375a5aa...`；准备内容必须精确属于这 6 个文件、无预先暂存和无范围外未暂存内容。不得修改 handoff、产品源码、依赖、锁文件、ADR、其他任务卡或 source worktree。

## 必查事实

1. Git identity 必须为 `Mozhu <maintainer@example.invalid>`，且 `user.useConfigOnly=true`。
2. TASK-003 source worktree 只读且干净，分支为 `codex/task-003-state-store`、HEAD 为 `f07795...`；review evidence 的父提交必须为 `adab4bb...`，review commit 相对父提交仅修改 `handoffs/TASK-003.md`。相对 `dcc7d85...` 的 implementation Diff 仍只为批准的 5 个文件。Review verdict 为 `APPROVE`，AC-1 至 AC-5、ADR-003 S-01 至 S-08 全 PASS，P0/P1/P2 均无；仅记录 P3 与 at-most-once 风险，不得降级或隐去。
3. TASK-004 source worktree 只读且干净，分支为 `grok/task-004-discovery-metadata`、HEAD 为 `30932e1...`；correction 相对 `f34cbb...` 精确为 5 个文件，完整 Diff 相对 `dcc7d85...` 仍为原批准的 17 个文件。第二个 Reviewer 必须是全新独立 Codex 会话，且尚未启动。
4. TASK-005 及后续任务继续 `BLOCKED`；真实 YouTube、Cookie、登录、remote components、ffmpeg、媒体/字幕下载仍未授权。

只运行控制面和 Git 只读检查：

```bash
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git diff --check
git diff --name-only
git -C "/Users/developer/Documents/yia-worktrees/task-003" branch --show-current
git -C "/Users/developer/Documents/yia-worktrees/task-003" rev-parse HEAD
git -C "/Users/developer/Documents/yia-worktrees/task-003" status --short
git -C "/Users/developer/Documents/yia-worktrees/task-003" rev-list --parents -n 1 f07795f854e02b15e8c438622042e360b7c0e8b9
git -C "/Users/developer/Documents/yia-worktrees/task-003" diff --name-status adab4bb00dd7e917b295c22fd8357a4f11515912..f07795f854e02b15e8c438622042e360b7c0e8b9
git -C "/Users/developer/Documents/yia-worktrees/task-003" diff --name-status dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...adab4bb00dd7e917b295c22fd8357a4f11515912
git -C "/Users/developer/Documents/yia-worktrees/task-004" branch --show-current
git -C "/Users/developer/Documents/yia-worktrees/task-004" rev-parse HEAD
git -C "/Users/developer/Documents/yia-worktrees/task-004" status --short
git -C "/Users/developer/Documents/yia-worktrees/task-004" diff --name-status f34cbb09d628ebb256bf5f2895adfd10dbd61812...30932e1742e948683f9e1c0f63236451b8d731bd
git -C "/Users/developer/Documents/yia-worktrees/task-004" diff --name-status dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...30932e1742e948683f9e1c0f63236451b8d731bd
git diff --cached --check
git diff --cached --name-only
```

不得运行 `uv`、pytest、Ruff、mypy、build、数据库或真实网络。建议提交信息：

```text
docs: accept TASK-003 and authorize TASK-004 review
```

提交后 main 必须干净；仅只读复核两个 source worktree 不变且干净。返回 Task、Role、Base、Head、identity、Committed files、checks、TASK-003 acceptance、TASK-004 source/status/reviewer、Verdict 和 remaining risks。
