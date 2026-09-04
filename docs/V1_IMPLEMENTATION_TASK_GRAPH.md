# V1 Implementation Task Graph

Status: **APPROVED IMPLEMENTATION PLANNING CONTRACT**
Anchor: `404c9e5bbe3c8d8aa50af26f7faafa172c2c8bb1` (`docs(product): freeze intelligence product specification`)
Scope: task decomposition only. It authorizes no runtime, provider, schema, or UI implementation.

## Freeze rules

Every task starts from an approved predecessor commit, has one implementer, one independent adversarial review, a written handoff, and an integration decision before it can be used as an anchor. No task may consume an unapproved worktree, merge, rebase, push, tag, or release. The fixed core is **DO NOT TOUCH**: TASK-016B/C scoring authority and trusted persistence/finalizer; `AuthoritativeScoringReader`; provider dispatch and `AMBIGUOUS`; credentials; Note authority; existing Weekly V2 authority; TASK-016G and Deep Analysis qualification. Deep Analysis remains **BLOCKED**.

All writes follow `UI -> loopback local API -> application service -> repository/runtime`; no browser, scheduler, or provider shortcut is permitted. Evidence is not Intelligence, Feedback is not Preference, current state is not history, and an untrusted intermediate is never a trusted read projection.

## DAG and merge order

```text
018 Persistence Foundation (m006)
  -> 019 Trusted Admission + Read Contract
  -> 020 Preference + Feedback (m007)
  -> 021 Source Policy + Filtering (m008)
  -> 022 Personalized Distillation + Ledger (m009)
  -> 023 Topic + Timeline (m010)
  -> 024 Unified Processing Orchestration
  -> 025 Weekly Intelligence Foundation (m011)
  -> 026 Frozen IA Integration
  -> 027 Integrated Acceptance / PO Demo
```

The graph is intentionally a single implementation lane. Although preference and source-policy semantics are conceptually independent after 018, both must evolve `state.py`, migration history, local API contracts, and source configuration. Parallel feature branches would create migration-number/ancestry ambiguity and a review-unfriendly conflict. Parallel-safe work is limited to read-only design review, reviewer preparation, and fixture design after their owner task is closed; no two implementation tasks are parallel-safe. Forbidden parallel pairs are any pair containing 018–023 or 025 (migration/state ownership), 024 with 021–023 (orchestration interface), 026 with any unclosed API/projection producer, and 027 with all implementation tasks.

Critical path is the full sequence above. Merge order is exactly task-number order; each branch is cut from the immediately preceding approved integration anchor. This is deliberate: migrations are forward-only and no task B may rely on task A's unreviewed working tree.

## Task summaries

| Task | Stable deliverable / start anchor | Depends on | Primary risk |
| --- | --- | --- | --- |
| 018 | m006 core Evidence/Intelligence/revision/dependency repository contracts | frozen HEAD | schema overreach or pointer-delete ghost claims |
| 019 | persisted-intelligence admission, dependency-impact calculation, and trusted read DTO contract | 018 | bypassing TASK-016 scoring authority or leaving ghost claims |
| 020 | m007 raw Feedback + derived Preference projections | 019 | feedback mutates explicit user intent |
| 021 | m008 Source policy and non-LLM filtering disposition | 020 | Check Now becomes retry or LLM is invoked needlessly |
| 022 | m009 evidence-bound personal distillation and resource ledger | 021 | unsupported claims, missing actual model/cost data |
| 023 | m010 Topics, membership, pin, timeline, light relations | 022 | copied claim text or mutable history |
| 024 | shared Manual/Scheduled/override orchestration using existing runtime | 023 | duplicate provider effect or AMBIGUOUS redispatch |
| 025 | m011 immutable V1 Weekly projection from trusted revisions | 024 | a second Weekly authority or raw-video summary |
| 026 | frozen IA and local API client integration | 025 | UI treats untrusted data as intelligence or hides existing capability |
| 027 | synthetic, provider-free V1 acceptance evidence | 026 | false product-completeness claim |

## Worktree policy

Create a dedicated V1 integration worktree/branch from the approved frozen anchor, for example `codex/v1-integration`; do not develop further in this TASK-017 worktree. For task N, create `codex/task-NN-<slug>` and a dedicated worktree from the exact SHA recorded as task N's `START_ANCHOR`. The integrator only integrates independently approved commits in the stated order and records the resulting SHA. No cherry-pick chain from an unreviewed branch, no detached base, and no root-repository work is allowed.

## Cross-cutting verification policy

Each task runs its focused unit/domain/repository/API tests plus `git diff --check`. A task touching a migration additionally runs fresh DB, sequential upgrade, failed migration rollback, and packaged-runtime initialization tests. A task touching Python runs Ruff and mypy for its scope; frontend tasks run frontend test/typecheck/build. Full `pytest`, `uv run --offline mypy src`, `uv run --offline ruff check .`, frontend typecheck/build, `uv build --offline`, and packaged-runtime checks are mandatory at 023, 025, 026, and 027. The canonical scanner has expected **EXIT 1**, exactly **11 accepted synthetic fixtures**, and **0 new findings**; this is never reported as PASS.

## V2 containment

No task activates or presents Early Signal, automatic Investigation, Evidence Expansion, external validation, Daily, Ask, advanced source credibility/independence inference, advanced resource optimization, or Deep Analysis. IDs/edges may be reserved only where the domain contract requires it; reserved UI is truthful, non-actionable, and explicitly future state.

## Adversarial graph review (round 2)

| Attack | Result / correction |
| --- | --- |
| A, E, I | Schema ownership is one task/version at a time (006–011); no task combines schema, orchestration, and major UI. |
| B, Q | 018/019 close persistence plus trusted-read admission before 022 and 026. |
| C, N | 020 closes event history, explicit/derived separation and expiry before distillation. |
| D, O | 018 revisions/edges and 019 deletion impact precede 023 Topics; 023 consumes trusted revisions only. |
| F | Ledger/checkpoint is m009 in 022, before the first V1 model-capable path; 024 reuses it. |
| G | 025 is a revision-reference V1 projection and explicitly preserves generic reports/Weekly V2 authority. |
| H, R | Investigation/Signals/Deep Analysis are V2-reserved or BLOCKED in every task and prompt. |
| J, K | No write-task parallelism is permitted because migration/state/API ancestry would conflict; exact predecessor SHA is mandatory. |
| L, M | 024 owns all triggers through the application service; manual override affects filtering only, while dispatch/AMBIGUOUS is untouched. |
| P | 021 modifies existing Source/Automation data compatibly; 024 delegates to the existing bounded scheduler/runtime rather than replacing it. |

Result after correction: **P0 = 0; P1 = 0; P2 = 0 for task-graph scope.** No Product Owner decision is currently required.
