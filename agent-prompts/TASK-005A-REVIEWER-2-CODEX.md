# TASK-005A Correction 1 — 第二轮独立 Codex Reviewer

## 身份与目标

你是一个全新的、独立的 Codex Reviewer；你未参与 TASK-005A 原实现、第一轮审查、
Correction 1 或任何 Status Integrator 写入。你只审查 Correction 1
`3a7df1029a77b7dec84a76c304c10e372f755b77` 是否真正关闭 P1，并确认 TASK-005A
全部 AC、相关 ADR-007 条款、范围、复用、红线和五轴质量无回归。

你不得修改业务代码、测试、fixture、依赖、锁文件、任务状态或 main。唯一允许写入并
提交的是 source worktree `handoffs/TASK-005A.md` 的第二轮 Reviewer 结论。Verdict
只能是 `APPROVE` 或 `REJECT`；不得自行修复 finding。

## 固定对象与启动门禁

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main review authorization：动态执行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005A-REVIEWER-2-CODEX.md`
- Required authorization parent：`bb61921bc93c17e01e9b3f4e2971933b30802b21`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Original base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- First review evidence：`3cec2d6a7b60b11912c10e714dc1473197d7374f`
- Reviewed Correction 1 head：`3a7df1029a77b7dec84a76c304c10e372f755b77`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始时 main 必须在动态 authorization commit、它是 Required authorization parent 的
唯一直接后继、main 干净且 TASK-005A=`IN_REVIEW`；source 必须在 fixed Correction head、
分支正确且干净。source 历史任务/状态文件的 `BLOCKED/UNASSIGNED` 是 assignment 前快照，
不得阻塞或被改写。任一不符立即 `BLOCKED`；不得 stash、reset、checkout、merge、
rebase、cherry-pick、pull、清理或选择其他 SHA。

## 必读与范围门禁

完整读取 source 的 `AGENTS.md`、协作/系统设计、ADR-002/003/005/006/007、Reuse Register、
TASK-005A 任务卡、原 Implementer/第一轮 Reviewer/Correction 1 包、source handoff 和
本包。从 main 读取动态授权与当前控制面。先用 Codebase Memory 图谱定位新评分对象及
调用/类型边界；图谱不足才读精确源文件。

确认：

1. Correction head 的唯一父为 first evidence；Correction Diff 精确为 domain、contracts
   test 和 handoff 三文件；完整 original base...head 仍精确为原 8 路径；
2. `pyproject.toml`、`uv.lock` 未变，Correction 未碰 config、state、migration、Provider、
   transcripts/discovery、CLI、任务/ADR、真实数据、凭证或构建产物；
3. 无新增依赖、模型、SDK、网络/媒体/认证/Vault 或文件删除能力；复用仍限既有
   Pydantic、SQLite/Artifact Repository 与标准库。

## 必须独立复跑

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
git diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...3a7df1029a77b7dec84a76c304c10e372f755b77
```

Implementer 自报 53/10/34/251；记录实际结果。`uv sync --locked` 只可补齐既有锁定
依赖缓存；build 必须 offline。验证 sdist/wheel 仍包含 migration SQL 后，只可清理本轮
已忽略 `dist/`。

## 必须独立证明的 P1 关闭探针

对标准公开 bound API `instance.model_copy`，以不同于原测试的 valid 样本，分别探测
`TranscriptSample`、`ScoringInput`、`ScoringDecision`、`ScoringOutcome`：

1. 以上四类的每一个非空 `update`，包括 Reviewer 原始非法样本、空 mapping、未知字段、
   错误类型、嵌套对象替换、hash mismatch 与 `score == threshold/final=false`，都必须在
   返回实例前 fail-closed；不得产生不变量已失效对象。
2. `update=None` 的 shallow 和 `deep=True` copy 必须返回同类且仍 frozen/有效；如果实现
   选择禁止 updates，合法 update 也必须明确、稳定地拒绝，而不能静默忽略或部分应用。
3. 审查实现只作用于 TASK-005A 的四个新评分对象：既有非本任务 domain model 的
   `model_copy` 行为不得被无关改变。禁止以 `model_construct`、`__dict__`、
   `object.__setattr__`、自由 `dict`、`Any`、宽 `object`、`cast` 或 `type: ignore`
   掩盖绕过。
4. 用静态类型与运行时检查确认公开签名不会诱导合法调用者绕过验证；不要把刻意调用
   Pydantic 基类的 unbound/private Python escape hatch 当作本任务新 API，但若产品代码
   已暴露该路径则记录 finding。

随后独立复核第一轮已通过的 Probe A（config/resource）、Probe C（真实 SQLite 评分
原子性与回滚）、Probe D（Artifact CAS/expiry index），以及 AC-1 至 AC-5、ADR-007
L-02 至 L-15 的本任务责任边界。真实模型、服务、媒体、网络、认证、Vault 和文件删除
未获授权；不得以它们未执行作为 reject 理由。

## Finding、Verdict 与 evidence

按 correctness、architecture、security、performance、readability 五轴审查。任一未解决/
新 P0/P1、必需门禁失败或 P1 探针无法证明，判 `REJECT`；仅明确 P2/P3 且所有 AC/契约
通过，可 `APPROVE`。

只在 source handoff 追加第二轮 Reviewer 结论，暂存并提交该文件：

```text
docs: review TASK-005A correction 1
```

evidence commit 必须以 Correction head 为唯一父，且只修改 handoff。提交后 main/source
都应干净；不得 merge、push、改状态、启动 TASK-006/007 或清理 worktree。

## 回传格式

```text
Task: TASK-005A
Role: Second Independent Codex Reviewer
Reviewed Correction 1 head: 3a7df1029a77b7dec84a76c304c10e372f755b77
Review evidence commit:
Checks rerun:
P1 model_copy boundary probe:
Regression/AC/ADR matrix:
Findings: P0/P1/P2/P3
Five-axis/scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
