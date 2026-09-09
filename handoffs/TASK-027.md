# TASK-027 Handoff — Integrated V1 Acceptance

## Scope and authority

- START_HEAD: `272becc56231c2f3b99f9a487ed11c9b87e071d9`.
- Base integrity: all accepted TASK-018 through TASK-026 anchors are ancestors
  of START_HEAD; TASK-025A `102f2dd1…` is an ancestor.
- Database: fresh initialization applies `001` through `014`, records 14
  migrations, and ends at `PRAGMA user_version = 14`. No `015_*.sql` exists.
- TASK-027 added no migration, provider qualification, real provider call,
  credential access, Deep Analysis, TASK-016G behavior, V2 behavior, push,
  merge, tag, or release.

## Acceptance implementation

Existing deterministic V1 integration fixtures were reused rather than
recreating a UI-only chain. `test_task024_processing_orchestration.py` drives
the real TASK-021 policy, TASK-023A Source Run, TASK-023B reservation and
TASK-022 continuation/admission services against SQLite and an injected legal
offline transport. TASK-025/025A then use the real trusted reader/Topic
membership/Saved services. `po_demo.py` constructs a separate synthetic
product database through those legal service boundaries for loopback UI checks.

One bounded P1 acceptance-harness defect was found and corrected:

- The PO demo launcher could treat an unrelated process on its hard-coded ports
  as a successful demo. `6305322` assigns it owned default loopback ports
  `8766/5174`, injects that API target into Vite, requires both child PIDs to
  remain live during readiness, and adds a proxy-target unit regression. This
  changes no product, trust, migration, Provider, or V2 semantics.

## Primary acceptance matrix

| Acceptance area | Current evidence | Result |
| --- | --- | --- |
| Configure Source | TASK-021 policy tests prove exact initial `0/1/3/5/10`, recurring `1/3/5/10`, defaults, focus/ignore/style persistence and Preference non-mutation. | PASS |
| Check Now / schedule | TASK-024 proves manual and scheduled triggers share the durable core and differ only in finite metadata. | PASS |
| Backlog / limits | TASK-021 and TASK-024 retain overflow Source-video links for a later bounded run. | PASS |
| Filtering / Manual Analyze | TASK-021/024 prove SKIPPED is not failure; UNCERTAIN does not dispatch; Manual Analyze bypasses relevance only. | PASS |
| Durable Source Run / restart | TASK-023A/023B/024 prove persisted queue, priority, child checkpoints, exact IDs and safe reopen. | PASS |
| Reservation / continuation | TASK-023B/024 prove zero-call reserve, immutable Source Run child binding and exact-ID continuation. | PASS |
| At-most-once / AMBIGUOUS | TASK-022/023B/024 prove success reuse, duplicate trigger collision, restart/concurrency safety and zero AMBIGUOUS redispatch. | PASS |
| Budget / model | TASK-022/023B/024 prove pre-transport budget/model gates and finite Needs Attention. | PASS |
| Personalized distillation | TASK-020/021/022 prove active preference projection influences deterministic transport input without mutating Source policy, limits, schedule, model or budget. | PASS |
| Structured output / claims / Evidence | TASK-018A/019/022 prove finite kinds, reader-only admission, exact Evidence binding and fail-closed malformed/foreign/generated support. | PASS |
| Intelligence authority | TASK-019, TASK-025A and TASK-026 fixture prove `AuthoritativeIntelligenceReader` is the only product-facing authority; Saved never falls back to raw data. | PASS |
| Topic evolution | TASK-023 proves reader-only association, information-gain semantics, non-causal relations, append-only Timeline and degraded current projection. | PASS |
| Feedback learning loop | TASK-020/022 fixtures prove active feedback-derived context affects future deterministic distillation without rewriting explicit Source policy. | PASS |
| Save / unavailable Saved | TASK-025A plus PO demo prove durable idempotent Save/Unsave and retained relation with `CURRENT_NOT_ACTIVE`, not stale content. | PASS |
| Weekly V1 | TASK-025 and PO demo prove trusted Topic inputs, finite provenance, idempotency, empty week, immutable snapshots and correction marker. | PASS |
| Product IA / trust UX | Playwright at 1440x900 and 768x900 verifies the exact six destinations, evidence drill-down, labels, unavailable Saved, Weekly, Topics, Sources, Settings, V1 Investigations and BLOCKED Deep Analysis. | PASS |

## Failure and recovery matrix

| Scenario | Durable/user-facing state | Retry / dispatch | Data and trust result |
| --- | --- | --- | --- |
| Source disabled | `NEEDS_ATTENTION` / `USER_DECISION_REQUIRED` | no dispatch | history remains; disabled never deletes it |
| Normal skip | child `SKIPPED` | not a Retry; 0 calls | Video/filter reason remains inspectable |
| Uncertain filter | typed non-admission | 0 stage-2/transport calls | no silent RELEVANT promotion |
| Budget blocked | `NEEDS_ATTENTION` / `BUDGET_BLOCKED` | 0 transport calls, including P0/manual Analyze | child/checkpoint retained for legal attention |
| Model unavailable | `NEEDS_ATTENTION` / `MODEL_UNAVAILABLE` | 0 transport calls | no fallback or fabricated model state |
| Schema invalid | terminal rejected execution | semantic retry 0 | no partial Intelligence admission |
| Unsupported Evidence | rejection before/during admission | no trusted read | raw/generated/foreign evidence never becomes support |
| AMBIGUOUS outcome | `NEEDS_ATTENTION` / `AMBIGUOUS_EXTERNAL_OUTCOME` | repeated resume 0 redispatch | exact child/checkpoint retained; no generic Retry |
| Verified read unavailable | explicit unavailable envelope | no raw fallback | unavailable current content is not ordinary Intelligence |
| Topic support invalid | current `DEGRADED` | no truth rewrite | Timeline stays historical and provenance-bound |
| Saved target unavailable | `CURRENT_NOT_ACTIVE` with Unsave | no stale card/Evidence | relation persists, trust stays unavailable |
| Empty Weekly | finalized empty V1 snapshot | duplicate generation idempotent | truthful no-important-information result |
| Weekly correction | append-only `SUPERSEDED` marker | no rewrite | original finalized item remains immutable |
| Process restart | persisted queued/reserved checkpoints reload | continuation uses exact ID once | no process-memory authority |
| Duplicate / collision trigger | second run has no protected duplicate effect | no second protected dispatch | source/run/idempotency state remains auditable |

## Executed checks

| Command / check | Result |
| --- | --- |
| all V1 task integrations plus PO demo | `233 passed in 37.34s` |
| fresh SQLite acceptance probe | `user_version=14`; 14 files `001…014`; `m015_present=False` |
| PO-demo proxy regression | `10 passed` frontend tests |
| loopback Playwright product flow | PASS at `1440x900` and `768x900`; `0` external requests; `0` console errors |
| full pytest | `2198 passed, 1 skipped, 1 existing warning in 147.08s` |
| `uv run --offline mypy src` | PASS, 54 source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; wheel and sdist contain m013/m014; existing uv build-system-version warning only |
| frontend typecheck | PASS |
| frontend full tests / production build | `10 passed`; PASS |
| `git diff --check` | PASS at final review |

## Independent adversarial review

Reviewed the reader, Source Run, reservation, Saved, Topic, Weekly and product
fixture contracts against the frozen attack list. The focused integration tests
exercise raw-row/forged-reader rejection; no second trust root through Saved,
Topic or Weekly; finite claim labels; source-count versus independence;
append-only Timeline/Weekly; expired/derived Preference isolation; unified
manual/scheduled orchestration; pre-dispatch budget; no fallback/repair;
restart/concurrent resume; and no AMBIGUOUS redispatch. The frontend browser
fixture additionally checks first-level IA, unavailable states, labels, no
generic Retry, unknown cost, provider unavailability and Deep Analysis BLOCKED.

- P0: `0`
- P1: `0` after `6305322`
- P2: `0`
- Frozen core changed: `NO`
- V2 leakage: `0`

## Security disposition

The canonical scanner is run against the final staged tree. Its required result
is **exit 1**, exactly 11 accepted historical synthetic-fixture findings, and
zero new findings. This is recorded as a finite accepted disposition, never as
scanner PASS.

## Conclusion

TASK-027 is an integrated acceptance gate, not a release action. V1 remains
provider-free in this acceptance run: real model/provider calls `0`; Deep
Analysis remains `BLOCKED`; TASK-016G remains `UNAUTHORIZED`.
