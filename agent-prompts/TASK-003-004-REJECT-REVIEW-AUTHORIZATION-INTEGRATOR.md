# TASK-004 Reject / TASK-003 Review Authorization — Status Integrator Packet

你是 Status Integrator。唯一任务是在 main 同步 TASK-004 独立审查 `REJECT` 后退回原 Grok Implementer 修复，以及 TASK-003 进入全新独立 Grok Reviewer 的 `IN_REVIEW`。不得实现产品代码、运行产品测试、安装依赖、进入任一 source worktree 或启动 Agent。

## 固定上下文

- Main base: `main@1e3f58f8c52e8a1737fc3039797499c02a2c9935`
- TASK-004 review evidence/source head: `grok/task-004-discovery-metadata@f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- TASK-003 implementation source: `codex/task-003-state-store@adab4bb00dd7e917b295c22fd8357a4f11515912`
- TASK-004 target: `IN_PROGRESS`，Codex Reviewer 已结束，原 Grok 等待修复
- TASK-003 target: `IN_REVIEW`，全新 Grok Reviewer 等待启动

完整读取 `AGENTS.md`、协作/状态文档、TASK-003/004 任务卡、`TASK-004-CORRECTION-3-GROK.md`、`TASK-003-REVIEWER-GROK.md` 和本包。

## 唯一允许范围：精确 7 个文件

- `agent-prompts/TASK-003-004-REJECT-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-003-REVIEWER-GROK.md`
- `agent-prompts/TASK-004-CORRECTION-3-GROK.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

若准备内容不精确属于此清单，停止并报告；不得修改产品代码、依赖、锁文件、handoff、source worktree 或其他文件。

开始必须确认 main HEAD 为 `1e3f58f...`、无预先暂存、Git identity 为 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`。只读确认 TASK-004 worktree 干净且 HEAD `f34cbb...`，review evidence 相对 `9db800f...` 仅 handoff，完整范围仍为 17 文件；TASK-003 worktree 干净且 HEAD `adab4bb...`，相对 `dcc7d85...` 只为 5 个批准文件。

确认 TASK-004 P1 四项、P2 两项、P3 一项描述与修复包一致，不得降级或写成已接受；确认 TASK-003 Reviewer 是独立 Grok 会话，尚未启动。同步后，TASK-004 原 Grok 修复与 TASK-003 Grok Reviewer 可并行，范围和 worktree 隔离；不得启动第二个 TASK-004 Reviewer。

运行且仅运行控制面检查：

```bash
git status --short
git diff --check
git diff --cached --check
git diff --name-only
git diff --cached --name-only
git status --short
```

不得运行 uv、pytest、Ruff、mypy、build、数据库或真实网络路径。提交建议：

```text
docs: return TASK-004 fixes and start TASK-003 review
```

提交后 main 干净；只读确认两个 source worktree 未变且干净。返回 Task、Role、Base、Head、Committed files、Checks、TASK-004 source/status、TASK-003 source/status/reviewer、Verdict、risks。
