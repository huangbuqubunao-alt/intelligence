# TASK-003 Implementation Evidence — Status Integrator Packet

## 任务

你是 Status Integrator。你的唯一任务是在 main 同步 TASK-003 已提交实现证据及其等待 Reviewer 容量的事实。不得实现产品代码、运行产品测试、安装依赖、进入 TASK-004 worktree 或启动任何 Reviewer。

## 固定上下文

- Main base: `main@372a31eb53eed39faeba9df545c5e665c7a63ba1`
- TASK-003 source: `codex/task-003-state-store@adab4bb00dd7e917b295c22fd8357a4f11515912`
- TASK-003 source worktree: `/Users/hua/Documents/yia-worktrees/task-003`
- TASK-003 status: 保持 `IN_PROGRESS`；Implementer 已停止写入，等待 Reviewer 容量
- TASK-004: `IN_REVIEW`，独立 Codex Reviewer 已启动；不得读取、写入、检查、清理、暂存或等待 TASK-004 worktree，也不得改变其状态。

先完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-003-state-store.md`
6. 本包

## 唯一允许范围

在 main 仅允许暂存/提交以下 4 个文件：

- `agent-prompts/TASK-003-IMPLEMENTATION-EVIDENCE-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`

不得修改任何产品代码、依赖、锁文件、handoff、TASK-003 source 或其他文件。

## 门禁与检查

1. main 初始 HEAD 必须为 `372a31e...`；初始准备内容精确为上述 4 文件，无预先暂存和无未暂存范围外内容。
2. TASK-003 source 必须干净、正好为 `adab4bb...`，相对 `dcc7d85...` 只包含 `state.py`、`001_initial.sql`、`tests/integration/test_state_store.py`、`tests/unit/test_state_transitions.py`、`handoffs/TASK-003.md`。
3. TASK-003 必须仍为 `IN_PROGRESS`，不能提前设为 `IN_REVIEW`/`ACCEPTED`/`DONE`，也不能启动 Grok Reviewer；原因是 TASK-004 Reviewer 是当前唯一活跃 Reviewer。
4. Git 身份必须为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。
5. 不运行 `uv`、pytest、Ruff、mypy、build、数据库或任何网络路径。

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
docs: record TASK-003 implementation evidence
```

提交后 main 必须干净；只可只读确认 TASK-003 source 未变且干净。不得读取/检查 TASK-004。

## 返回格式

```text
Task: TASK-003 implementation evidence sync
Role: Status Integrator
Base:
Head commit:
Committed files:
Checks:
TASK-003 source/status:
TASK-004 untouched:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
