# TASK-023B Handoff — Distillation Reservation / Continue Seam Amendment

## Metadata

- Task: `TASK-023B — Distillation Reservation / Continue Seam Amendment`
- START_HEAD: `4c7d3b2b33de43709839aacb61360748b39ee253`
- Documentation amendment: `c5021c3 docs(v1): add distillation reservation seam amendment`
- Feature: `24e17c6 feat: add distillation reservation and continuation`
- Database: `PRAGMA user_version = 12`; no migration and no m013.

## Delivered seam

`PersonalizedDistillationService.reserve_distillation_execution()` mints the
canonical TASK-022 identity itself; callers supply no execution ID. It validates
eligible Source/video and the exact persisted canonical available transcript
Evidence set, then writes only m010's finite
`PENDING / RESERVED_NOT_DISPATCHED / invocation_count=0` compound state. It
makes zero transport calls and creates no ResourceUsage, Intelligence, Evidence
support, card, Topic effect, usage, or cost.

`continue_reserved_distillation(execution_id)` accepts only that persisted ID.
It rebuilds the exact canonical command from m010 and persisted Evidence,
rejecting any changed/mismatched context. It repeats the existing TASK-021
eligibility and TASK-022 evidence, budget and model checks. Immediately before
the existing offline/test transport it atomically claims exactly the stored
request identity as `PENDING / DISPATCH_CLAIMED / invocation_count=1`; it then
uses the existing structured validation, admission and m010 ledger path.

After a crash/concurrent continuation, `DISPATCH_CLAIMED` is finalized or
returned as terminal `AMBIGUOUS`; it can never become Reserved or dispatch
again. Completed and rejected terminal records return their persisted result.
Legacy/unrecognised `PENDING` is not a continuation authority. A claimed or
terminal execution cannot be returned as a new Reservation, preserving the
strict distinction that **Reserved means definitely not dispatched**.

The m012 child can bind this exact pre-dispatch ID and its immutable binding is
unchanged. There is no Source Run worker, queue, trigger, scheduler, Topic
delegation, API/UI or TASK-024 implementation in this task.

## Verification

| Check | Result |
| --- | --- |
| Focused TASK-023B + TASK-022 + TASK-023A | `58 passed` |
| TASK-023B/022/023A/023/021 focused post-hardening set | `93 passed` |
| TASK-018 through TASK-023B, dispatch/AMBIGUOUS, scoring, Source/Automation regression set | `229 passed` |
| Full pytest (final) | `2118 passed, 1 skipped, 1 existing Pydantic serializer warning` |
| `uv run --offline mypy src` | PASS, 51 source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; existing uv build-system version warning |
| `git diff --check` | PASS |
| m010/m012 migration SQL | unchanged |
| Security scanner | EXIT 1; exactly 11 accepted existing synthetic fixture findings, 0 new TASK-023B findings; not PASS |

## Adversarial review / boundaries

The tests and review cover zero-call reservation, deterministic duplicate
reservation, foreign/noncanonical Evidence rejection, exact m012 binding,
restart-only continuation, budget-before-claim, successful-result recovery,
unknown transport, pre-transport claim crash, concurrent continuation,
legacy-PENDING rejection, schema-invalid and unsupported-claim non-retry, and
selected/actual model identity. No second ledger, Intelligence path, trusted
read, Topic effect, real provider/model call, credential field, migration,
provider-dispatch-v4 mutation, or AMBIGUOUS weakening was introduced.

Review found and fixed one P1 before final test: a `DISPATCH_CLAIMED` row was
initially accepted by duplicate reservation as a DTO reference. Reservation now
returns only the strict persisted pre-dispatch state; a claimed identity can only
be recovered as AMBIGUOUS. Re-review: **P0 = 0, P1 = 0, P2 = 0**.

## Next authorized action

`TASK-024` may restart only from this approved TASK-023B anchor and must use:

```text
reserve TASK-022 execution
-> bind exact ID to the m012 child
-> continue that exact ID
```

It must not pre-create a checkpoint and call legacy `distill()`. TASK-025 is not
started; m013 remains its sole ownership. Deep Analysis remains **BLOCKED /
unchanged**. No push, merge, tag or release was performed.
