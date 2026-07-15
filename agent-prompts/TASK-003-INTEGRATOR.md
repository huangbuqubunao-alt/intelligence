# TASK-003 Final Product Integrator Packet

你是 TASK-003 的最终 Codex Integrator。你只整合已由 Reviewer 和主控接受的 source head；不得实现、修复、重构、重新设计产品代码，不改变公共任务状态，不清理分支/worktree，不推送远程。

## 开工包

- Task: `TASK-003`
- Role: `Integrator`
- Agent: 全新 Codex Integrator 会话
- Acceptance anchor: `main@fb1cdd728081c9c1ae0c0bcb82b7490332090b28`
- Required execution base: 主控将在 Status Integrator 提交完成后随启动指令提供；该 main HEAD 必须干净、为 anchor 的单父后继，且相对 anchor 仅为本轮控制面同步新增的 7 个指定文件
- Main worktree: `/Users/hua/Documents/youtubek agent`
- Source worktree: `/Users/hua/Documents/yia-worktrees/task-003`，严格只读
- Source branch: `codex/task-003-state-store`
- Accepted source/review head: `f07795f854e02b15e8c438622042e360b7c0e8b9`
- Reviewed implementation source: `adab4bb00dd7e917b295c22fd8357a4f11515912`
- Review verdict: `APPROVE`
- Current task status: `ACCEPTED`
- Reuse decision: `DIRECT` 使用 Python 标准库 `sqlite3` / `importlib.resources`；不引入 ORM、迁移框架或新依赖
- Parallel now: TASK-004 Grok correction 4；不得读取、写入、检查、清理或等待 TASK-004 worktree

完整读取 main 的 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`tasks/TASK-003-state-store.md`、本包；只读读取 source 的 `handoffs/TASK-003.md`。

## 预检

在 main 确认分支为 `main`、HEAD 为主控指定 execution base、工作树无 staged/unstaged/untracked 文件、身份为 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。确认任务仍为 `ACCEPTED`，不是 `DONE`。

在 source worktree 只读确认：分支 `codex/task-003-state-store`、HEAD `f07795...`、工作树干净；review commit 父提交为 `adab4bb...` 且只修改 handoff；实现 Diff 相对 `dcc7d85...` 精确只为下列 5 文件：

- `src/youtube_intel/state.py`
- `src/youtube_intel/migrations/001_initial.sql`
- `tests/integration/test_state_store.py`
- `tests/unit/test_state_transitions.py`
- `handoffs/TASK-003.md`

## 合并与门禁

1. 记录实际 execution base，执行：

   ```bash
   git merge --no-ff --no-commit f07795f854e02b15e8c438622042e360b7c0e8b9
   ```

2. 有冲突时不得手工解决或编辑。执行 `git merge --abort`，确认回到 execution base 且干净，报告 `BLOCKED`。
3. 无冲突时，暂存内容相对 merge 第一父必须精确为上述 5 文件；无其他未暂存或未跟踪文件。运行：

   ```bash
   git diff --cached --check
   git diff --cached --name-status
   uv lock --check
   uv sync --locked
   uv run python -m pytest tests/integration/test_state_store.py
   uv run python -m pytest tests/unit/test_state_transitions.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   uv build
   ```

4. 确认 sdist 与 wheel 都包含 `youtube_intel/migrations/001_initial.sql`（sdist 可有 `src/` 前缀）。若 `uv sync --locked` 因网络沙箱失败，可按已批准锁定依赖范围以原命令请求联网重跑；不得修改锁文件、删减测试或放宽门禁。
5. 任一门禁失败：记录命令、关键错误和已运行结果；不得修代码。执行 `git merge --abort`，确认回到 execution base 且干净，报告 `BLOCKED`。
6. 全部通过后：

   ```bash
   git commit -m "merge: integrate TASK-003 state store"
   ```

## 提交后验证

确认 merge commit 恰有两个父提交：第一父为 execution base，第二父为 `f07795...`；source head 成为 main 祖先；第一父到 merge 的范围精确为 5 文件；main 干净；身份正确；TASK-003 仍为 `ACCEPTED`，绝不得在本轮写为 `DONE`；保留 source branch 与 worktree。

## 返回格式

```text
Task: TASK-003
Role: Integrator
Acceptance anchor:
Execution base:
Source head:
Merge commit:
Merge parents:
Pre-merge scope:
Checks: command + result
Post-merge task status:
Post-merge main/source worktree status:
Git author/committer identity:
Unexpected files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
