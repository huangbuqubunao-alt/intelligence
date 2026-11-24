# TASK-018 交接报告

## 元数据

- Task: `TASK-018 — Domain Persistence Foundation`
- Role: `Implementer`
- Agent/session: `Codex`
- START_HEAD: `ea77ba0139bf4563b60a8057a40e1b62c430e215`
- Implementation commits: `254a89e57e1250f4a8f58cdd44247aacc6d25243`, `cd9df15da03af036171d9203ae247a1c7598d465`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-018-domain-persistence-foundation`
- Branch: `codex/task-018-domain-persistence-foundation`
- Migration: `006_add_intelligence_domain.sql`; `PRAGMA user_version` `5 → 6`

## 目标与范围

- 实现：m006 的 Evidence、Intelligence identity/current pointer、immutable
  IntelligenceRevision、StateHistory、revision-evidence links 与受限
  DependencyEdge repository contracts。
- 复用：`ADAPT` 已有 `sqlite3`、`BEGIN IMMEDIATE`、checksum migration history、
  `importlib.resources` discovery 与 typed state-record pattern；无新依赖。
- 未做：Topic/timeline（TASK-023）、admission/trusted reads/deletion impact UX
  （TASK-019）、execution/queue/resource ledger、provider/scoring/dispatch、Note/
  Weekly authority、Deep Analysis 或任何 V2 execution。

## Schema / repository evidence

- Evidence ID 是由 Video、Artifact、timestamp range、lineage kind 与 source role
  生成的稳定 SHA-256；Artifact 必须属于同一 Video 且未删除。
- Intelligence identity 与 current revision pointer 分表；composite FK、append-only
  revision numbering、immutable triggers 与 forward-only pointer trigger 阻止 foreign
  / missing / backward pointer。
- Revision insertion atomically writes exact, de-duplicated Evidence links、state event
  （state/prior state/reason/evidence）和 current pointer。历史 revision/state/links
  均不可 update/delete。
- Evidence、Video、Artifact 的 unavailable/deleted 变化会在任何 current revision
  仍引用时 fail closed；不产生 ghost Intelligence。完整 impact decision 留给 TASK-019。
- Dependency edges 仅允许 `EVIDENCE_SUPPORT` 或 `REVISION_SUPERSEDES`；前者必须是
  dependent revision 的 exact evidence link，后者必须是同一 Intelligence 的 immediate
  prior revision。无 opaque caller-defined authority edge。
- m006 不创建 provider/queue/execution/Topic/Brief/V2 tables；wheel 与 sdist 均包含迁移。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| Fresh DB / m006 schema / user_version | PASS | TASK-018 focused migration test |
| v005 Source/Automation preservation / idempotence | PASS | TASK-018 test plus state/orchestration regressions |
| Evidence identity / provenance / availability | PASS | deterministic-ID and unavailable/deleted attack tests |
| Revision/history/current pointer | PASS | append/history/foreign-pointer/backward-pointer tests |
| Exact evidence binding / deletion restriction | PASS | missing, duplicate, raw-SQL, artifact and Video attacks |
| Finite dependency edge foundation | PASS | allowed relation, exact link, same-identity/prior constraints |
| Migration rollback / fail closed | PASS | injected malformed m006 remains at v005 |
| Package runtime discovery | PASS | built wheel/sdist both list m006 resource |

## 检查结果

| 命令 | 结果 | 说明 |
|---|---|---|
| `uv run --offline pytest -q tests/integration/test_task018_domain_persistence.py` | PASS | 8 passed |
| persistence / Source / Automation / existing migration regressions | PASS | 97 passed, then 92 passed after adversarial fixes |
| `uv run --offline pytest -q` | PASS | 1974 passed, 1 skipped, 1 existing Pydantic serializer warning |
| `uv run --offline mypy src` | PASS | 45 source files clean |
| `uv run --offline ruff check .` | PASS | all checks passed |
| `uv build --offline` | PASS | wheel and sdist built; known uv build-system version warning only |
| `git diff --check` | PASS | no whitespace errors |
| `bash scripts/security_scan.sh` | NOT RUN | V1 graph requires canonical scanner at task 023+; TASK-018 card does not require it |

## Adversarial review / re-review

Initial adversarial review found and fixed these P1 paths:

1. raw pointer rollback to an older revision;
2. current Evidence claim surviving Artifact or Video unavailability/deletion;
3. `EVIDENCE_SUPPORT` edge not present in the revision's exact Evidence links.

Re-test and re-review result: `P0 = 0`, `P1 = 0`, `P2 = 0` for TASK-018 scope.
All exercised production repository paths and raw-SQL constraint bypass paths fail closed.

## Diff / frozen-core review

- Modified: m006, `state.py`, one runtime schema-version gate, targeted migration
  expectation tests, TASK-018 tests and this handoff/task status.
- Frozen core changed: **NO**. The runtime line only recognizes the newly owned
  current schema version; it does not alter scoring, dispatch, provider, credential,
  Note, Weekly, or Deep Analysis semantics.
- Deep Analysis: **BLOCKED / unchanged**.
- V2 leakage: **0**.
- No dependencies, lockfiles, secrets, real Vault access, provider call, push, merge,
  tag, release, reset, rebase, or rewrite.

## Implementer conclusion

- Implementation status: `APPROVE` after adversarial re-review.
- Task status: `IN_REVIEW`; the task remains ready for independent review / TASK-019
  authorization only. It is not merged or marked DONE.
- Remaining risk: TASK-019 owns policy-level dependency impact calculation and trusted
  read/admission; m006 intentionally supplies only its fail-closed storage foundation.
