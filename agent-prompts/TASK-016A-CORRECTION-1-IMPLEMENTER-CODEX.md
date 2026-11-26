# TASK-016A Correction 1 Implementer — finite Evidence timestamps

固定 source：`/Users/developer/Documents/yia-worktrees/task-016a-intelligence-contract-foundation`
分支 `codex/task-016a-intelligence-contract-foundation`，HEAD 必须为 Reviewer evidence
`6a564b18a3c91e4366c1b744733910dc5584854b`，其唯一父必须为 implementation
`210dd203e722eabf3453808f490f4afe52139183`。开始前核验 source 干净和 Review 1
handoff-only 范围。

只修复 P1：`KnowledgeEvidence.start_seconds/end_seconds` 必须是有限、非负值；JSON
overflow、`NaN`、`+Inf`、`-Inf`、对象构造及 JSON round-trip 必须 fail-closed 或稳定
保持相同合法值。不得改变任何其他 Knowledge/Config 语义。

Correction 唯一允许修改：

- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `handoffs/TASK-016A.md`

先添加失败回归，再最小修复。运行 focused、mypy、Ruff、全量 pytest、offline build、
Correction/完整范围 diff check。只创建一个单父 Correction commit；禁止依赖/锁/Schema/
runtime/provider/template、网络、模型、Key、Vault、merge/push 和 TASK-016B–H。
