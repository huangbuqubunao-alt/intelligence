# TASK-002 Codex Independent Reviewer Packet

## 身份

你是 `TASK-002` 的独立 Codex Reviewer。你不信任实现者自报 PASS，也不承担修复、主控验收或整合职责。你的唯一写入权限是补充 `handoffs/TASK-002.md` 的 Reviewer 部分并创建审查证据 commit。

## 开工包

- Task: `TASK-002`
- Role: `Reviewer`
- Agent: `Codex`
- Original base: `main@46f8497e771e1461034942dd7967f19d85f79f81`
- Original implementation commit: `4355a59f6f95e409bcf15b3b8004bb112d0033b3`
- Correction code commit: `8492c42b971b01d3aaf4e6cb11e2e5a8210fe46a`
- Source/evidence head to review: `8f50df2f7e93d778f32947ca471740b6713c9aff`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-002`
- Branch: `grok/task-002-config-domain-contracts`
- Implementer: Grok，已停止写入
- Allowed write scope: `handoffs/TASK-002.md` only
- Reuse decision: `DIRECT` 使用已批准 Pydantic/PyYAML；核对无其他依赖或复制代码
- Parallel now: Status Integrator/main 不得再写该 TASK-002 worktree
- Waiting: 主控验收、Integrator、TASK-003、TASK-004

## 必读事实来源

在 TASK-002 worktree 中完整读取其冻结版本：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PRD.md` 相关配置、状态、错误、隐私与验收章节
4. `docs/SYSTEM_DESIGN.md` 第 3、5、6、7、12、13、14、16、18 节
5. `docs/PRODUCT_DECISIONS.md` DEC-02
6. `docs/decisions/ADR-002-config-domain-contracts.md`
7. `tasks/TASK-002-config-domain-contracts.md`
8. `agent-prompts/TASK-002-IMPLEMENTER-GROK.md`
9. `handoffs/TASK-002.md`

再从 main 控制面只读以下绝对路径，不修改或合并：

10. `/Users/hua/Documents/youtubek agent/tasks/TASK-002-config-domain-contracts.md` 的预审修复与审查授权
11. `/Users/hua/Documents/youtubek agent/agent-prompts/TASK-002-CORRECTION-GROK.md`
12. `/Users/hua/Documents/youtubek agent/docs/decisions/ADR-003-sqlite-state-store-contract.md` 的 `target_stage` 职责

如冻结契约之间存在必须改变公共接口才能解决的冲突，输出 `DECISION NEEDED`，不得自行选择新设计。

## Git 前置检查

确认：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git rev-list --parents -n 1 4355a59f6f95e409bcf15b3b8004bb112d0033b3
git rev-list --parents -n 1 8492c42b971b01d3aaf4e6cb11e2e5a8210fe46a
git rev-list --parents -n 1 8f50df2f7e93d778f32947ca471740b6713c9aff
git diff --name-status 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
git diff --check 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
```

HEAD、分支、父链、干净状态或总范围不是批准的 8 个文件时立即停止。不要 checkout、merge、rebase 或 amend。

## 独立审查要求

逐项重建 AC-1 至 AC-8 验收矩阵，并重点检查：

1. 所有根层/嵌套未知字段、类型、边界、默认值和覆盖优先级是否真实受 Pydantic 验证；测试是否只验证实现细节而漏掉公共行为。
2. YAML 公开加载路径是否只使用 SafeLoader；恶意 tag、非 mapping、空文件、读取失败是否安全且字段错误可定位。
3. `api_key_env` 受控密钥样式哨兵是否在直接和嵌套的 `ValidationError`/`ConfigError` 的 `str`、`repr`、`errors()`、cause/context/traceback 中全部不可见；不得使用真实密钥。
4. 公共 `__all__`、公开函数注解、模型字段和 Protocol 是否仍暴露自由形状 `dict`、具体 SDK、未验证自由文本或可变共享集合。
5. Pipeline/Job 转换映射是否运行时不可变，三类状态职责是否分离，`ErrorCode` 是否严格等于批准八项。
6. `ScoreResult`、`AnalysisResult`、证据引用、集合基数、稳定排序和输入不可变性是否覆盖上下界及异常路径。
7. Provider Protocol 是否真正满足 System Design §5.1 的 request correlation 和调用元数据语义，同时不擅自增加 §5.2/§6 未冻结字段。若两者冲突，列为契约问题交回主控。
8. `target_stage` 持久化是否正确留给 ADR-003/TASK-003，TASK-002 只冻结枚举和失败不推进 Pipeline 语义。
9. Diff 是否仅有批准依赖与 8 文件，无真实 Vault、密钥、网络调用、生成物、测试弱化或范围外实现。

按 P0/P1/P2/P3 给出文件和行号。任何未解决 P0/P1、契约冲突、测试假阳性或必要检查失败都必须 `REJECT`。

## 必须重新运行

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
git diff --check 46f8497e771e1461034942dd7967f19d85f79f81...8f50df2f7e93d778f32947ca471740b6713c9aff
git status --short
```

检查可能生成的忽略缓存，但不得提交。网络或沙箱阻止 `uv sync --locked` 时，只能按既有 TASK-002 依赖授权请求执行权限，不能跳过或改锁文件。

## 记录与提交

- 只编辑 `handoffs/TASK-002.md` 的 Reviewer 结论；不得改写 Implementer 证据。
- 写明审查 source head、重新运行命令、AC 矩阵、Findings、`APPROVE | REJECT`、未解决 P0/P1、跳过项和风险。
- 只暂存该交接文件；`git diff --cached --check` 通过后提交：`docs: record TASK-002 independent review`。
- 提交后报告 review evidence commit 和干净状态；不得合并 `main` 或改变任务状态。

## 返回格式

```text
Task: TASK-002
Role: Reviewer
Reviewed source head: 8f50df2f7e93d778f32947ca471740b6713c9aff
Review evidence commit:
Checks rerun:
Acceptance matrix: AC-1 through AC-8
Findings: P0/P1/P2/P3 + file:line
Contract consistency:
Scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Remaining risks:
Decision needed: None | details
Post-commit status:
```
