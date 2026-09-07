# TASK-020 Handoff — Preference & Feedback Domain

## Outcome

- START_HEAD: `30035f9fda9883dd72e530cbbf3be559c1ff6ad2`
- Migration: `008_add_preference_feedback.sql`; fresh and upgraded databases
  reach `PRAGMA user_version = 8`.
- TASK-020 owns only m008. Migration m009 is absent.
- No existing data is interpreted during upgrade: v007 data remains intact and
  preference/feedback projections begin empty.

## Durable contract

`feedback_events` is append-only immutable history. It retains a stable ID,
finite kind, finite scope/validated target, optional user content, optional
finite factual-correction class, local timestamp, and `RECORDED` effect state.
Quick feedback (`MORE_LIKE_THIS`, `LESS_LIKE_THIS`, `IMPORTANT`), natural
language, explicit-preference statements, and factual corrections remain
distinct. A factual correction records `WRONG_INTERPRETATION`,
`SOURCE_UNSUPPORTED`, `OUTDATED`, `VIEWPOINTS_MERGED`, or `OTHER`; it does not
touch Evidence, Transcript, or Intelligence.

`preferences` is not feedback history. It stores immutable records plus
append-only state events. The finite, enforced pairs are:

- `LONG_TERM` + `EXPLICIT`;
- `RECENT` + `DERIVED`;
- `TEMPORARY_FOCUS` + `TEMPORARY` with backend-UTC start and expiry.

The active projection requires an activation event, excludes terminal
replacement/deletion events, and excludes temporary focus at or after expiry.
History remains available. Replacement is atomic: old state is immutably
retired before the replacement is activated in the same SQLite transaction.
Supersession cannot cross horizon, provenance, scope, or target; a derived
record cannot overwrite explicit configuration.

The finite V1 scopes are global content, Source content, Video content,
Intelligence content, and distillation style. Source/Video/Intelligence
targets are checked against existing stable identities. Topic scope is not
introduced before TASK-023.

## Application/API seam

`PreferenceApplicationService` exposes typed commands. The loopback local API
accepts only explicit long-term preference creation, temporary focus creation,
finite feedback, explicit long-term replacement, and deletion. It exposes no
route for callers to submit derived provenance. Every preference mutation uses
an explicit command identity; exact repeats are idempotent and conflicting
reuse returns `409 CONFLICT`. Request objects reject unsupported fields and
temporary expiry requires RFC 3339 `Z` UTC, evaluated by backend time.

No preference/feedback path writes Source policy, Source enabled state,
Automation schedule, model preference, Evidence, Transcript, Intelligence,
scoring, provider dispatch, or credentials. No model/provider path is called.

## Verification

| Check | Result |
| --- | --- |
| TASK-020 focused migration/repository/API/adversarial tests | `21 passed` |
| TASK-020 + TASK-019 + TASK-018/018A + state + Source/Automation + scoring regressions | `185 passed` |
| full pytest | `2025 passed, 1 skipped, 1 existing Pydantic serializer warning` |
| `uv run --offline mypy src` | PASS, 47 source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; known uv build-system-version warning only |
| wheel/sdist migration discovery | PASS; both archives contain m008 |
| `git diff --check` | PASS |
| security scanner | NOT RUN; frozen task graph reserves its canonical scanner gate for later integration checkpoints; TASK-020 adds no credential/provider/external-execution surface |

## Adversarial review and re-review

Initial review found and corrected these P1 paths:

1. a direct repository supersession could activate before immutable retirement
   of its prior record;
2. a timestamp without explicit UTC authority could be treated as UTC;
3. a replacement replay could not be idempotent after its prior record had
   been retired; and
4. API command conflicts could surface as a generic failure.

The m008 lifecycle trigger, atomic replacement ordering, strict `Z` timestamp
validation, and explicit `409` mapping close those paths. Re-review attacks
raw SQLite arbitrary kind/horizon/target writes, derived-over-explicit
supersession, raw feedback mutation, duplicate command reuse, expiry boundary,
factual-correction separation, Source-scoped feedback, and provider-call
absence. Result: **P0 = 0, P1 = 0, P2 = 0** for TASK-020 scope.

## Frozen boundaries

TASK-019 `AuthoritativeIntelligenceReader` / `VerifiedIntelligenceRead`,
TASK-016B/016C scoring authority, provider dispatch/`AMBIGUOUS`, credentials,
Note/Weekly authority, and Deep Analysis are unchanged. Deep Analysis remains
**BLOCKED / unchanged**. No TASK-021 Source-policy/filtering behavior or V2
Investigation behavior is present.
