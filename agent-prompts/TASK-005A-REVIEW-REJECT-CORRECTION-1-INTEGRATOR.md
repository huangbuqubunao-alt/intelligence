# TASK-005A 第一轮审查拒绝与 Correction 1 同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的第一轮审查结论、
`TASK-005A=IN_PROGRESS` 控制面和 Correction 1 Implementer 包；不得实现、审查或
修改产品 source，不得运行 `uv`、pytest、mypy、Ruff、build、数据库、模型、服务、
网络或真实资源命令，不得启动 Worker、merge、push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@315d4490ed60b051411ee7eef8d1127d72898c95`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Reviewed implementation：`85cd5362460044773317a48cbaae58e55aa735af`
- Reviewer evidence：`3cec2d6a7b60b11912c10e714dc1473197d7374f`
- Required identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确且暂存区为空；工作区必须恰有下列
5 个准备 Markdown 文件且没有其他修改/未跟踪路径。source 必须位于 reviewer evidence、
分支正确且干净。任一条件不符立即 `BLOCKED`；不得 stash、reset、checkout、merge、
rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-005A-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-005A-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-005A-local-model-shared-contracts.md`

## 必须核验

1. reviewer evidence 的唯一父提交为 reviewed implementation，且 evidence Diff 只修改
   `handoffs/TASK-005A.md`；source worktree 干净。
2. base...reviewer evidence 的完整产品范围仍精确为原 8 个批准路径，且 `pyproject.toml`/
   `uv.lock`、migration、Provider、`transcripts.py`、`discovery.py`、CLI 均无差异。
3. Reviewer Verdict=`REJECT`；唯一阻断 finding 为 P1：新公开 Pydantic
   `TranscriptSample`、`ScoringInput`、`ScoringDecision`、`ScoringOutcome` 可被
   `model_copy(update=...)` 绕过字段与跨字段验证。AC-2、ADR-007 L-03/L-05/L-06 失败；
   配置、SQLite 原子性、Artifact index 和全部离线门禁通过不抵消该 P1。
4. main 控制面将 TASK-005A 设为 `IN_PROGRESS`，原 Codex Implementer 获 Correction 1
   唯一写入权；下一 Reviewer 尚未启动，且不得预写 `APPROVE`、`ACCEPTED` 或 `DONE`。
5. Correction 1 精确 source scope 只能为 `src/youtube_intel/domain.py`、
   `tests/unit/test_contracts.py`、`handoffs/TASK-005A.md`；不得修改现有非本任务领域
   契约、Schema、依赖、锁文件、Provider、状态存储、配置、任务/ADR 或 main。
6. TASK-006/TASK-007 继续 `BLOCKED/UNASSIGNED`；模型、Ollama、ffmpeg、真实网络/媒体、
   Cookie、登录、Vault/密钥与文件删除仍未授权。

## 执行与提交

记录 5 个准备文件 SHA-256，检查前后必须一致。运行 `git diff --check`、完整 Diff、
source evidence Diff 和 `git diff --cached --check`；cached scope 必须精确为 5 个文件。
创建单一非 merge commit：

```text
docs: authorize TASK-005A correction 1
```

提交后确认唯一父为 Required main base、main/source 均干净，且：

```bash
git log -1 --format=%H -- agent-prompts/TASK-005A-CORRECTION-1-CODEX.md
```

解析为新 commit。不得运行产品命令、写 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005A first review reject / Correction 1 sync
Role: Status Integrator
Base: main@315d4490ed60b051411ee7eef8d1127d72898c95
Head commit:
Git identity:
Committed files:
Checks:
Review evidence/finding:
Correction source/scope/status:
TASK-006/TASK-007 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
