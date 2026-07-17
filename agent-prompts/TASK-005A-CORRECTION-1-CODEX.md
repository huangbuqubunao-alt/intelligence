# TASK-005A Correction 1 — Codex Implementer

你是 TASK-005A 的原 Codex Implementer。第一轮独立审查已拒绝；你只修复 P1：公开
Pydantic 领域对象允许 `model_copy(update=...)` 绕过不变量。不得重做已通过的配置、
SQLite 或 Artifact 工作，也不得扩大功能、重新分配任务或启动 Reviewer。

## 固定状态与启动门禁

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main correction authorization：动态运行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005A-CORRECTION-1-CODEX.md`
- Required authorization parent：`315d4490ed60b051411ee7eef8d1127d72898c95`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- First review evidence / required source start：`3cec2d6a7b60b11912c10e714dc1473197d7374f`
- Reviewed implementation / original base：`85cd5362460044773317a48cbaae58e55aa735af` /
  `82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始时 main 必须位于动态 correction authorization、其唯一父为 Required authorization
parent、main 控制面为 `TASK-005A=IN_PROGRESS` 且干净；source 必须位于 first review
evidence、分支正确且干净。source 中历史任务状态是 assignment 前快照；只以 main
控制面判定当前状态。任一条件不符立即 `BLOCKED`，不得 stash、reset、checkout、merge、
rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许的 source 修改

1. `src/youtube_intel/domain.py`
2. `tests/unit/test_contracts.py`
3. `handoffs/TASK-005A.md`

相对 reviewer evidence 的 Correction Diff 与相对 original base 的完整产品 Diff 都必须
严格受此约束（完整 Diff 仍只能属于原 8 个批准路径）。不得改 `config.py`、`state.py`、
settings、migration、Provider、`transcripts.py`、`discovery.py`、CLI、依赖、锁文件、
任务/ADR/main 或其他测试。不得导入模型、SDK、网络、媒体、Cookie/登录、Vault/密钥，
不得新增 Schema 或执行文件删除。

## P1 的精确修复标准

`frozen=True` 只禁止属性赋值；它不能被当作 `BaseModel.model_copy(update=...)` 的验证
边界。必须对以下四个新增公共契约关闭 bypass：`TranscriptSample`、`ScoringInput`、
`ScoringDecision`、`ScoringOutcome`。

- 任何带 `update` 的公共 functional copy 必须重新经过字段和模型级验证，或明确拒绝
  所有 update；不得静默返回 unchecked 实例。
- 若保留合法 update 能力，合法更新仍必须产生相同的 frozen、具名、完全验证对象；
  不能以 `model_construct`、`__dict__`、`object.__setattr__`、自由 `dict`、`Any`、宽
  `object`、`cast` 或 `type: ignore` 规避验证。
- 对四个对象分别添加行为回归，至少覆盖 Reviewer 的非法样本：空/计数错误的
  `TranscriptSample`、样本和 transcript hash 不一致的 `ScoringInput`、错误类型的
  `ScoringDecision`、`score == threshold` 却 final=false 的 `ScoringOutcome`。另覆盖
  extra/未知 update，及所选合法-copy 策略的正例或明确拒绝行为。
- 修复应只影响 TASK-005A 新增评分对象。不要全局改变既有 `_DomainModel` 的 public
  行为；若认为必须共享改动，先证明所有受影响旧对象和调用方无兼容性风险，否则报告
  `DECISION NEEDED`。

先在当前 reviewer evidence 上用独立测试复现 RED，再作最小实现得到 GREEN。不得删除、
弱化或跳过现有断言。保留原 Reviewer 已通过的配置、SQLite、Artifact 与红线行为。

## 必须运行的检查

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest tests/unit/test_state_transitions.py
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...HEAD
```

`uv sync --locked` 只允许既有锁定依赖的缓存缺失包；不得重锁、加包或下载模型。验证
`pyproject.toml`/`uv.lock` 相对 original base 字节不变，sdist/wheel 仍包含
`migrations/001_initial.sql`；只清理本轮已忽略 `dist/`。审计完整 Diff、禁止路径和
敏感信息。

创建一个新的非 merge、非 amend commit，唯一父提交必须为 first review evidence。只在
handoff 追加 Correction 1 的 RED/GREEN、检查、范围、复用、跳过项与风险。不得修改
任务状态、启动 Reviewer、merge、push 或清理 worktree。

## 回传格式

```text
Task: TASK-005A
Role: Codex Implementer (Correction 1)
Starting review evidence:
Correction commit:
Changed files:
P1 closure evidence:
Checks:
Diff review:
Skipped checks:
Remaining risks:
Decision needed:
Post-commit status:
```
