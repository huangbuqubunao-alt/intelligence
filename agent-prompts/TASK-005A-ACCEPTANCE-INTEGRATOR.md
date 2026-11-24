# TASK-005A Correction 1 审查验收同步 — Status Integrator

你是全新的 Codex Status Integrator。你只核验并提交主控准备的 Reviewer 2 evidence、
`TASK-005A=ACCEPTED` 控制面；不得实现/修改产品 source 或 handoff，不得运行 `uv`、
测试、构建、数据库、网络、模型或服务命令，不得启动 Integrator、merge、push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@22d65d4a27a7dfe95fec88f1985ed8ae98703d65`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Original base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Correction 1：`3a7df1029a77b7dec84a76c304c10e372f755b77`
- Reviewer evidence/source head：`e726656ffcc96b3c61d12f649c5574dc927add62`
- Required identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确、暂存区为空；工作区必须恰有下列
4 个准备 Markdown 文件且没有其他变更。source 必须位于 reviewer evidence、分支正确且
干净。任一不符立即 `BLOCKED`；不得 stash、reset、checkout、merge、rebase、
cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-005A-ACCEPTANCE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `tasks/README.md`
4. `tasks/TASK-005A-local-model-shared-contracts.md`

## 必须核验

1. Reviewer evidence 的唯一父为 Correction 1，且 evidence Diff 只修改
   `handoffs/TASK-005A.md`；source worktree 干净。
2. Correction Diff 精确为 domain、contracts test、handoff 三路径；original base 的完整
   产品范围仍精确为原 8 个批准路径，`pyproject.toml`/`uv.lock` 未变。
3. Reviewer Verdict=`APPROVE`；focused 53/10/34、全量 251、mypy、Ruff、CLI、offline
   build/package、fixed Diff，P1 model_copy fail-closed、SQLite 原子/回滚、Artifact CAS/
   index-only、AC-1 至 AC-5 和适用 ADR-007 条款均 PASS，P0/P1/P2/P3 均无。
4. main 控制面写 TASK-005A=`ACCEPTED`，但不得预写 merge SHA 或 `DONE`；Product
   Integrator 尚未授权/启动。TASK-006/TASK-007 继续 BLOCKED/UNASSIGNED。
5. 模型、Ollama、ffmpeg、网络、媒体、Cookie/登录、Vault/密钥和文件删除授权均未变化。

## 提交

记录准备文件 SHA-256，检查前后必须一致。运行 `git diff --check`、source Diff checks、
`git diff --cached --check` 与 cached scope 检查；只暂存 4 个文件并创建：

```text
docs: accept TASK-005A correction 1 review
```

提交后确认唯一父为 Required main base、main/source 干净且范围精确。不得运行产品命令、
写 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005A acceptance sync
Role: Status Integrator
Base: main@22d65d4a27a7dfe95fec88f1985ed8ae98703d65
Head commit:
Git identity:
Committed files:
Checks:
Review/source/status:
TASK-006/TASK-007 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
