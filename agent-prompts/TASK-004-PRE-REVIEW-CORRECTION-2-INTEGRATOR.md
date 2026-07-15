# TASK-004 Pre-review Correction 2 — Status Integrator Packet

## 任务

你是 Status Integrator，不实现产品代码，不运行产品测试，不进入 TASK-003/TASK-004 worktree，不安装依赖。你的唯一工作是在 main 同步 TASK-004 第二轮预审修复决定与 Grok 执行包。

## 固定上下文

- Role: `Status Integrator`
- Main base: `main@290b8a27e21e1c1dcb6022c57205acaf7e17713e`
- TASK-004 source: `grok/task-004-discovery-metadata@10f5ffaaa3e8651a02e2f94c1736b8417acf3021`
- TASK-004 source worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- TASK-004 status: `IN_PROGRESS`；Codex Reviewer 未启动
- TASK-003 worktree 有进行中的未提交实现是预期状态；不得读取、写入、检查、清理、暂存它，也不得用它作为本轮阻塞条件。

先完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-004-discovery-metadata.md`
6. `agent-prompts/TASK-004-CORRECTION-2-GROK.md`
7. 本包

## 允许范围

main 上仅允许暂存/提交以下 5 个文件：

- `agent-prompts/TASK-004-CORRECTION-2-GROK.md`
- `agent-prompts/TASK-004-PRE-REVIEW-CORRECTION-2-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`

不得修改其他文件、产品代码、任务依赖、依赖/锁文件或任务状态以外的控制面。不得触碰任何 source worktree。

## 需确认的事实

1. `main` 初始 HEAD 必须为 `290b8a...`，初始准备内容只能是上述 5 文件，且无预先暂存内容。
2. TASK-004 source 必须干净并正好为 `10f5ffa...`；其相对 `dcc7d85...` 的完整范围必须仍在原 TASK-004 的 17 文件集合内。
3. 首轮修复未解决 P1 的理由必须一致：非私有 `map_info_dict_to_video_metadata(info: object)` 与公开 `ydl_factory`/`last_opts` 测试注入不能由 `__all__` 或 `object` 包装豁免。
4. TASK-004 必须保持 `IN_PROGRESS`；不得启动 Reviewer。TASK-003 继续 `IN_PROGRESS` 且不触碰。
5. Git 身份必须为 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。

## 检查与提交

运行：

```bash
git status --short
git diff --check
git diff --cached --check
git diff --name-only
git diff --cached --name-only
git status --short
```

检查暂存范围精确为允许的 5 文件，且没有未暂存内容；不运行 `uv`、pytest、Ruff、mypy 或构建。提交建议：

```text
docs: request TASK-004 private test-hook correction
```

提交后确认 main 干净；只可只读确认 TASK-004 source 未变且干净。不要读取/检查 TASK-003。

## 返回格式

```text
Task: TASK-004 correction 2 sync
Role: Status Integrator
Base:
Head commit:
Committed files:
Checks:
TASK-004 source/status:
TASK-003 untouched:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
