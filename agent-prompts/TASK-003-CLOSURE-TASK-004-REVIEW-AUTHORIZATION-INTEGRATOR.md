# TASK-003 Closure + TASK-004 Review Authorization — Status Integrator Packet

你是 Status Integrator。唯一任务是在 main 关闭已整合的 TASK-003 为 `DONE`，并把 TASK-004 correction 4 同步为 `IN_REVIEW`、提交全新独立 Grok Reviewer 包。不得实现产品代码、运行产品检查、安装依赖、进入 source worktree、启动 Reviewer 或执行 merge。

## 固定上下文

- Main base: `main@072511f20b587f973b29437d79080f6cb7863f1a`
- TASK-003 merge commit: `072511f20b587f973b29437d79080f6cb7863f1a`，父提交为 `c524a05...` 与 `f07795...`
- TASK-003 target: `DONE`
- TASK-004 source: `grok/task-004-discovery-metadata@54c0ab201388cba35e481d7a511f21575946ad14`
- TASK-004 correction parent: `5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58`
- TASK-004 target: `IN_REVIEW`，全新独立 Grok Reviewer 尚未启动

完整读取 main 的 `AGENTS.md`、协作/状态文档、两张 TASK 卡、`TASK-004-CORRECTION-4-GROK.md`、`TASK-004-REVIEWER-3-GROK.md` 与本包。

## 唯一允许范围：精确 6 个文件

- `agent-prompts/TASK-003-CLOSURE-TASK-004-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-3-GROK.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

main 初始 HEAD 必须为 `072511f...`；准备内容必须精确属于这 6 个文件、无预先暂存和无范围外未暂存内容。不得修改 handoff、产品源码、依赖、锁文件、ADR、其他任务卡或 source worktree。

## 必查事实

1. 身份为 `Mozhu <maintainer@example.invalid>`，`user.useConfigOnly=true`。
2. TASK-003 merge 必须有两个父提交，第一父 `c524a05...`、第二父 `f07795...`；第一父差异精确为 5 个 TASK-003 文件，main 干净，整合后门禁已 PASS。只有这些事实成立才可写 `DONE`。
3. TASK-004 source worktree 只读且干净、HEAD `54c0ab2...`；correction 相对 `5d66c28...` 精确为 5 文件，完整 Diff 相对 `dcc7d85...` 仍为批准 17 文件。只记录 correction 4 的静态事实；不得预写 Reviewer `APPROVE`、`ACCEPTED` 或 `DONE`。
4. TASK-005 及后续继续 `BLOCKED`；真实 YouTube、Cookie、登录、remote components、ffmpeg、媒体/字幕下载仍未授权。

只运行控制面 Git 检查：

```bash
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git rev-list --parents -n 1 072511f20b587f973b29437d79080f6cb7863f1a
git diff --name-status 072511f20b587f973b29437d79080f6cb7863f1a^1..072511f20b587f973b29437d79080f6cb7863f1a
git -C "/Users/developer/Documents/yia-worktrees/task-004" rev-parse HEAD
git -C "/Users/developer/Documents/yia-worktrees/task-004" status --short
git -C "/Users/developer/Documents/yia-worktrees/task-004" rev-list --parents -n 1 54c0ab201388cba35e481d7a511f21575946ad14
git -C "/Users/developer/Documents/yia-worktrees/task-004" diff --name-status 5d66c28d6bd02a7cf31a27ffe9a31a2479f9da58...54c0ab201388cba35e481d7a511f21575946ad14
git diff --check
git diff --cached --check
git diff --cached --name-only
```

不得运行 uv、pytest、Ruff、mypy、build、数据库或网络。建议提交：

```text
docs: close TASK-003 and authorize TASK-004 review
```

提交后 main 必须干净；只读确认 TASK-004 source 未变且干净。返回 Task、Role、Base、Head、identity、Committed files、checks、TASK-003 closure、TASK-004 source/status/reviewer、Verdict、remaining risks。
