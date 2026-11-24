# TASK-021 Handoff — Source Policy & Filtering

## Metadata

- Task: `TASK-021 — Source Policy & Filtering`
- Role: `Implementer / adversarial reviewer`
- Corrected authority anchor: `52e35cb1b99e955d6cd133329df737074b3d2c6c`
  (`docs(v1): correct TASK-021 migration authority`)
- Feature commit: `a0e434de28e647f179fbf9a175a485713cee3caf`
- Adversarial correction: `e3c145534d3d4424dd06c46a74ace0fb89de00ad`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-021-source-policy-filtering-m009`
- Branch: `codex/task-021-source-policy-filtering-m009`
- Date: `2026-09-07`

## Scope and durable contract

Migration `009_add_source_policy_filtering.sql` advances `v008 → v009` and
leaves existing Source, Automation, Intelligence, Preference, and Feedback data
untouched. It creates no `m010`, makes no inferred policy from historic video
data, and bootstraps only the frozen global defaults: initial history `5`,
per-run maximum `5`, empty focus/ignore rules, and `BALANCED` style.

`source_policy_revisions` is immutable append-only policy history;
`source_policy_current` is the explicit current pointer. Source fields either
inherit the current global policy or explicitly override it. Initial-history
values are exactly `0/1/3/5/10`; recurring limits are exactly `1/3/5/10`.
They are separately selected, so neither first intake nor recurring intake can
silently borrow the other limit. Rule lists, override modes, and styles are
finite and validated at both application and migration boundaries.

Stage 1 is deterministic metadata-only screening. Shorts and explicit ignore
matches skip; a focus match is relevant; insufficient metadata or no configured
focus rules produces only a typed Stage-2 request. No Stage-2 implementation,
provider, model, Job, scheduler, retry, or dispatch call exists in this task.

Every persisted filter decision records its stable ID, Source/video identity,
stage, finite outcome/reason, effective global/Source policy revisions, prior
decision when applicable, and timestamp. The history is append-only. Skipping
does not touch the Video lifecycle or create a failed Job. Manual Analyze adds
an idempotent relevance-only override decision for a currently skipped video;
it has `execution_authorized: false` at the local API boundary. TASK-024 must
still apply budget, qualification, at-most-once, and `AMBIGUOUS` safety before
any execution.

TASK-020 Preference/Feedback is not imported or mutated by the policy service.
Derived/recent preference and temporary focus cannot change explicit Source
focus, ignore, style, limits, enablement, or schedules.

## Local application/API seam

`SourcePolicyApplicationService` is the only TASK-021 policy write/read seam.
The loopback local API validates bounded JSON commands for global and Source
policy updates, policy reads, filter audit reads, and manual-analyze intent.
It rejects unsupported fields and arbitrary enum values. There is no
frontend-to-SQLite route and no route to submit a filter outcome/reason or
invoke Stage 2.

## Verification

| Check | Result |
| --- | --- |
| TASK-021 migration/policy/filter/API/adversarial suite | `13 passed` |
| TASK-021 + TASK-020 + TASK-019 + Source/Automation/local-API regressions | `77 passed` |
| Legacy persistence/migration/scoring/provider regressions | `106 passed` |
| Full pytest | `2038 passed, 1 skipped, 1 existing Pydantic serializer warning` |
| `uv run --offline mypy src` | PASS, `48` source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; known build-system-version warning only |
| Wheel inspection | PASS; includes `youtube_intel/migrations/009_add_source_policy_filtering.sql` |
| `git diff --check` | PASS |
| `bash scripts/security_scan.sh` | Exit `1`, exactly `11` accepted pre-existing synthetic fixture findings, no TASK-021 finding; not a scanner PASS |

## Adversarial review and re-review

The first review found and corrected two P1 concerns before final re-test:

1. a naive `published_at` could make bounded ordering host-dependent; candidates
   now require an aware timestamp; and
2. raw SQLite could submit non-string/oversized rule arrays or attach manual
   fields to an automated decision; m009 now rejects both.

Re-review covered derived/temporary preference non-mutation, global/source
override isolation, finite API and SQLite validation, persisted skipped Video
visibility, skip-versus-failure separation, manual override idempotency and
non-execution, pending backlog retention, Stage-1/Stage-2 provider absence,
append-only audit history, `m010` absence, TASK-019 trusted reads, scoring
authority, `AMBIGUOUS`, and Deep Analysis. Result: **P0 = 0, P1 = 0, P2 = 0**
within TASK-021 scope.

## Frozen boundaries and handoff

TASK-016B/016C scoring and lineage, `AuthoritativeScoringReader`, TASK-019
trusted reads, TASK-020 preference separation, provider dispatch v4,
`AMBIGUOUS`, credentials, Note/Weekly authority, and all provider
qualification remain unchanged. Deep Analysis remains **BLOCKED / unchanged**.
There is no TASK-022 personalized distillation, evidence/claim generation,
ledger, cost accounting, or V2 Investigation implementation.

Recommended verdict: `APPROVE`.

`TASK-021 closed; ready for TASK-022 authorization.`
