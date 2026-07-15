# TASK-004 Correction 3 Evidence — Status Integrator Packet

你是 Status Integrator。唯一任务是在 main 同步 TASK-004 第三轮修复 evidence 及其等待 Reviewer 容量的事实。不得实现产品代码、运行产品测试、安装依赖、进入 TASK-003/TASK-004 source worktree 或启动 Agent。

## 固定上下文

- Main base: `main@9ec416bdf38b4ee97fe4e7e8bd3a20e09f1ed163`
- TASK-004 source: `grok/task-004-discovery-metadata@30932e1742e948683f9e1c0f63236451b8d731bd`
- TASK-004 status: 保持 `IN_PROGRESS`；第三轮修复已提交，等待 Reviewer 容量
- TASK-003: `IN_REVIEW`，独立 Grok Reviewer 正在运行；不得读取、写入、检查、清理、暂存或等待其 worktree。

完整读取 main 的 `AGENTS.md`、协作/状态文档、TASK-004 任务卡、本包与 `TASK-004-CORRECTION-3-GROK.md`。

## 唯一允许范围：4 个文件

- `agent-prompts/TASK-004-IMPLEMENTATION-EVIDENCE-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`

main 初始 HEAD 必须为 `9ec416b...`；初始准备内容精确属于此范围且无预先暂存。只读确认 TASK-004 source 干净且为 `30932e1...`，correction 相对 `f34cbb...` 仅 5 个批准文件、完整范围仍为 17 文件。确认仍为 `IN_PROGRESS`，不得生成/启动 Reviewer 或写 `ACCEPTED`/`DONE`。

Git identity 必须为 `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。只运行控制面检查：

```bash
git status --short
git diff --check
git diff --cached --check
git diff --name-only
git diff --cached --name-only
git status --short
```

不得运行 uv、pytest、Ruff、mypy、build、数据库或真实网络。提交建议：

```text
docs: record TASK-004 correction evidence
```

提交后 main 干净；只读确认 TASK-004 source 未变且干净；不得读取/检查 TASK-003。返回 Task、Role、Base、Head、files、checks、TASK-004 status、TASK-003 untouched、Verdict、risks。
