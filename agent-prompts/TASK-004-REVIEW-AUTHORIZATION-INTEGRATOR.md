# TASK-004 Review Authorization — Status Integrator Packet

## 任务

你是 Status Integrator。你的唯一任务是在 main 把 TASK-004 从 `IN_PROGRESS` 同步为 `IN_REVIEW`，固定 Reviewed source head，并提交独立 Codex Reviewer 包。不得实现产品代码、运行产品测试、安装依赖、进入 TASK-003/TASK-004 source worktree 或启动 Reviewer。

## 固定上下文

- Main base: `main@74942436607e46a2356553ed0409cdc515dbc6c9`
- TASK-004 source: `grok/task-004-discovery-metadata@9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- TASK-004 source worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- TASK-004 prior status: `IN_PROGRESS`
- Target status: `IN_REVIEW`
- Active Reviewer: 全新独立 Codex 会话；尚未启动
- TASK-003 有进行中的未提交实现是预期状态；不得读取、写入、检查、清理、暂存它，也不得用它作为本轮阻塞条件。

先完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-004-discovery-metadata.md`
6. `agent-prompts/TASK-004-REVIEWER-CODEX.md`
7. 本包

## 唯一允许范围

在 main 仅允许暂存/提交以下 5 个文件：

- `agent-prompts/TASK-004-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`

不得修改任何产品代码、依赖、锁文件、TASK-004 source 或其他文件。Review authorization commit SHA 会在提交后由主控随 Reviewer 启动指令提供；不得在提交内容中尝试自引用 commit SHA。

## 门禁与检查

1. main 初始 HEAD 必须为 `7494243...`；初始准备内容精确为上述 5 文件，无预先暂存和无未暂存范围外内容。
2. TASK-004 source 必须干净、正好为 `9db800f...`，父链包含 `392edfb... -> 10f5ffa... -> 9db800f...`；相对 `dcc7d85...` 完整范围仍为原 TASK-004 17 文件集合。
3. TASK-004 的第二轮 P1 核验依据必须一致：无非私有 mapper、构造面只有 `timeout_seconds`、private hook 不在公开 Provider surface；这只是进入独立审查的门槛，不能预先写 `APPROVE` 或 `ACCEPTED`。
4. Git 身份必须为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。
5. 不运行 `uv`、pytest、Ruff、mypy、build 或任何真实网络路径。

提交前后执行：

```bash
git status --short
git diff --check
git diff --cached --check
git diff --name-only
git diff --cached --name-only
git status --short
```

提交信息建议：

```text
docs: authorize TASK-004 independent review
```

提交后 main 必须干净；只可只读确认 TASK-004 source 未变且干净。不要读取/检查 TASK-003。

## 返回格式

```text
Task: TASK-004 review authorization sync
Role: Status Integrator
Base:
Head commit:
Committed files:
Checks:
TASK-004 source/status/reviewer:
TASK-003 untouched:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
