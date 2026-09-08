# V1 Acceptance Gates

Status: **FROZEN GATE DESIGN**

## Universal gate

An implementation task is APPROVE only after focused TDD tests are green, adversarial cases pass, its handoff records reuse/licence evidence, no frozen core is changed, `git diff --check` is clean, and an independent reviewer returns APPROVE. REQUEST CHANGES blocks the successor. STOP and request a Product Owner decision on a genuine conflict with the frozen product contract, an authority-boundary change, a new dependency/credential/provider requirement, destructive migration, or V2 activation.

## Per-task gates

| Task | Must prove | Adversarial gate |
| --- | --- | --- |
| 018 | immutable Evidence/revision and dependency links; current pointer is valid | evidence deletion cannot leave current ghost claim; bad FK/pointer rejected |
| 018A | immutable finite revision claim classification with fail-closed legacy sentinel | lifecycle cannot stand in for claim type; migration never guesses old semantics |
| 019 | only admitted persisted Intelligence is readable; exact evidence/revision labels and deletion/correction impact preview | raw artifacts/score rows and forged DTOs cannot become authoritative; unavailable evidence marks dependents unsupported |
| 020 | feedback event history and derived preference are distinct; expiry works | Less-like-this cannot change explicit config; correction is not feedback |
| 021 | deterministic metadata filtering, skip reason, cap/history, manual override audit | manual analyze overrides relevance only; no LLM or provider call in filter |
| 022 | evidence-bound Card/revision plus actual model/usage-or-UNKNOWN ledger | unsupported claim, missing evidence, budget/model pause, or AMBIGUOUS has no admitted result |
| 023 | Topic association/dedupe/pin/timeline references revisions | merge/split does not rewrite Evidence/Intelligence identity |
| 023A | durable finite Source Run trigger/priority/state/checkpoint/attention/idempotency persistence | m005/m010 cannot be overloaded; AMBIGUOUS child state never gains retry permission |
| 023B | zero-call canonical TASK-022 reservation and exact restart-safe continuation | claimed/unknown dispatch becomes AMBIGUOUS; no second ledger, Intelligence, or m012 ID replacement |
| 024 | Check Now/scheduler/manual override share one service and consume safe Source Run checkpoints plus TASK-023B reservation/continue | duplicate trigger, budget stop, model wait, partial resume, AMBIGUOUS never redispatch |
| 025 | Weekly only references trusted revisions/Topics and is immutable | raw video cannot generate it; correction adds marker, does not rewrite; no Weekly V2 claim |
| 025A | m014 fresh/upgrade preservation; idempotent Save/Unsave; backend saved time; reader-resolved Saved list | unavailable/invalidated targets never fall back to raw content; no Preference/Feedback/Topic/Weekly/model effects or second trust root |
| 026 | frozen IA exposes evidence/context and truthful unavailable/reserved states | browser cannot call DB/provider; Investigations cannot appear active; old capability remains reachable/reframed |
| 027 | provider-free synthetic journey covers V1 state transitions | model unavailable, budget exhausted, skip override, AMBIGUOUS, Deep Analysis BLOCKED remain truthful |

## Integration and PO gate

The prerequisite sequence includes TASK-025 → TASK-025A → TASK-026 → TASK-027.
TASK-026 retains required Save/Saved/Unsave UI but consumes the closed TASK-025A
backend contract without a migration. TASK-027 verifies Save/Unsave and an
unavailable saved target at schema v014; it adds no product migration.

Before 027 acceptance: full unit/domain/repository/migration/application-service/API/scheduler/frontend/E2E/packaged-runtime suites pass at the required checkpoints; scanner output is exactly EXIT 1/11 accepted fixtures/0 new findings. The PO demo fixture must show a Source run with an explicit skipped video, manual analyze override, trusted Intelligence evidence drill-down, Topic/pin/timeline, raw Feedback influencing later selection without overwriting explicit preference, a Weekly V1 snapshot, Needs Attention, wait-model/budget-exhausted/AMBIGUOUS states, and Deep Analysis BLOCKED. No real provider/YouTube call is allowed absent separate PO authorization.
