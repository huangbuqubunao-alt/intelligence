# TASK-READINESS-LOCAL-INTELLIGENCE-TEXT implementation handoff

## Metadata

- Role: Implementer `local_text`; independent Reviewer `intel_bounded_review` pending.
- Base: `2978550aee692c7b24d5707d2eb4ebdfcc1d0e2f`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-local-intelligence-text`.
- Branch: `codex/task-readiness-local-intelligence-text`.
- Final full commit SHA is supplied in the delivery message; implementation and
  this report are in that same atomic commit.
- Approvals: task card, LOCAL_INTELLIGENCE_CHAIN_PROPOSAL,
  LOCAL_TEXT_TRUSTED_READER_ADDENDUM and the subsequently specifically approved
  LOCAL_TEXT_READ_CURRENT_ADDENDUM at root `54a8c20`. The latter was read from
  `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/docs/validation/end-to-end-user-readiness/LOCAL_TEXT_READ_CURRENT_ADDENDUM.md`;
  root owns that governance document and task-card amendment.

## Goal and delivered scope

Real LOCAL TXT/MD source authority supplies exact TEXT_RANGE references, Unicode
code-point offsets, derived lines, source/canonical/excerpt hashes and NULL
timestamps. Manual source/Summary admission is source-bound and remains manual
only. The new independent wire is `local-text-distillation-v1`; provider output
cannot invent or expand a range. Strict parsing rejects unknown/missing/extra
fields, booleans as positions, duplicate JSON keys, fabricated hashes/times,
mixed locators, cross-Content references and incomplete NO_NEW coverage.

Schema 38 remains unchanged. The immutable versioned execution ID holds sealed
input/context hashes and an identity hash that binds exact command fields and
the independent profile hash. The card hash binds those commitments and every
cited range. The reader requires exactly one matching checkpoint and ledger for
the revision, validates status/invocation/source/Content/model identity and
profile, resolves the current source ranges, then verifies the exact card hash.
It never tries alternate hashes or infers a new version from NULL timestamps.
The approved public `read_current` hook applies the same `_read_card` validation
to actual LOCAL text cards before direct Save, list_saved or Topic can consume
the trusted revision. Save/Topic write transactions and CAS are unchanged.

Admission rechecks the exact current source, Summary and coverage context in the
transaction. Historical reading preserves the original context commitment while
revalidating current source authority and lawful revision state; a genuinely new
verified deterministic Summary does not rewrite old cards or make them unreadable.

The existing Evidence UI shows real text lines or bilingual unavailable copy.
Internal Content/Evidence IDs are serialized in the hash; on refresh or history
navigation the current Content DTO must contain that same Evidence before focus
is restored. URL offsets and timestamps never grant authority. The layout reuses
the existing workspace DESIGN.md; no new screen, nav or stylesheet is introduced.

Independent `LocalTextDistillationProfile` and preparation-only harness freeze
exact model/digest, prompt/schema/parameter hashes and code hashes. There is no
generate function, factory installation or production receipt. Content inputs
are not yet frozen. All model qualification remains false; real LOCAL8 is still
BLOCKED by the failed original four-case/semantic qualification.

## Reuse and scope hygiene

- DIRECT: standard-library JSON/hashlib/SQLite, existing source_authority and
  Evidence resolver, Summary/current pointer, sealed command/input, reservation,
  budget/ledger/cancellation, NO_NEW transaction, authoritative reader, Save,
  Topic and Backup/Restore. Existing approved dependencies are reused as installed.
- ADAPT: only the first-party exact text wire/profile/hash and reader binding.
- REJECT: pseudo 0ms evidence, mixed timed/text authority, external URL authority,
  missing hash/range validation, output repair, inherited old receipt/qualification.
- No third-party code was copied; source/license inventory remains
  docs/REUSE_REGISTER.md and the existing project NOTICE. No dependency, lockfile,
  toolchain, schema or provider code was changed.
- Actual files: distillation.py, state.py, intelligence_read.py, local_api.py;
  App.tsx/uiLanguage.tsx/App.test.tsx; corresponding two local integration test
  files; preparation script/profile JSON; this handoff and LOCAL_TEXT_CONTRACT.md.
- runtime_composition.py, Save/Topic writers, subtitle providers, raw/archive
  contracts, production configuration and formal owner data are unchanged.

## Verification

All positive outputs are explicitly offline fixture transport outputs. They are
not real-model qualification or owner acceptance evidence.

| Check | Evidence/result |
|---|---|
| TDD baseline | Two TXT/MD tests initially failed at manual-ready rejection; real text ranges/NULL times now pass. |
| Final affected backend suite | 333 PASS in 230.78s, `.var/local-text/verified-final-checks.log`; nine execution-binding/profile checks PASS in 18.83s after the final fixture strengthening below. |
| New negative current/save/list/topic paths | Eight execution/ledger corruption types closed; targeted 13 checks PASS. |
| True Summary refresh/history | New source-bound EXTRACTION produces a different verified Summary artifact; unchanged historical/card revision remains readable, PASS. |
| Save/Topic/Backup/Restore | Positive/NO_NEW fixtures preserve every table and DATA hash; durable reload, exact revision/evidence binding PASS. |
| Full frontend | 446 tests PASS, 27 files; latest log `.var/local-text/frontend-tests.log`. |
| TypeScript/build | npm run typecheck and npm run build PASS. |
| Strict typing | PYTHONPATH=src:. .venv/bin/python -m mypy --strict src scripts/prepare_readiness_local_text.py: 103 source files PASS. |
| Runtime/tests/scripts lint | PYTHONPATH=src:. .venv/bin/python -m ruff check src tests scripts PASS. |
| Diff hygiene | git diff --check PASS; changes confined to approved scope. |

Focused backend batch command (no hidden network/model qualification):

```sh
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/integration/test_local_intelligence_text.py \
  tests/integration/test_local_intelligence_timed.py \
  tests/integration/test_local_distillation_wire_branches.py \
  tests/integration/test_task022_personalized_distillation.py \
  tests/integration/test_task023b_distillation_reservation.py \
  tests/integration/test_task019_trusted_intelligence_read.py \
  tests/integration/test_task025a_saved_intelligence.py \
  tests/unit/test_ollama_local_distillation.py \
  tests/unit/test_distillation_dispatch.py -q
```

Coverage includes bilingual output, Unicode emoji/combining marks/multiline
positions, exact source/hash/range/version checks, before/final context damage,
complete NO_NEW, Cloud API/service zero payload/dispatch, old transport zero
credential/request receipt rejection, double click, WAITING_MODEL cancellation,
WAITING_BUDGET, unknown result/restart, saved/topic trust, historical Summary
refresh and exact Backup/Restore tables/files. Old YouTube wire/card hash and
DTO exact-shape regression checks remain intact. The previous timed test's
obsolete text-not-supported assertion was replaced with an explicit new-version
zero-invocation assertion; its foreign-source and unbound-storage rejection
checks remain.

## Failures corrected and remaining gates

- Old DTO exact-shape regression failed after adding locator fields to all
  references; narrowed the fields to TEXT_RANGE only, preserving old YouTube and
  timed DTOs. The original assertion is unchanged and passes.
- Fixture-only defects corrected: misplaced test assertions, duplicate-checkpoint
  SQL column count, keyword-only SaveIntelligence construction, and an invalid
  attempted same-artifact language relabel. The latter was replaced with a
  genuine source-bound extraction and newly verified Summary, not a weakened
  history assertion. No assertions/tests/CI gates were removed or skipped.
- Final preparation fixture now obtains the pinned model input directly from the
  application reservation rather than substituting caller fields. The input hash
  assertion and input/context corruption cases use the corrected execution-ID
  component indexes; all nine binding/preparation cases were rerun and passed.
- The broad `ruff check .` also scans historical docs Python examples and reports
  40 pre-existing out-of-scope errors, e.g. unused sys in
  docs/dogfood/opencode-user-pilot/build_manual_html.py:5 and semicolon examples
  in docs/validation/phase13. Those files are unchanged; required src/tests/scripts
  lint passes. No broad formatting cleanup was made.
- One preparation invocation accidentally used system python3 and failed on the
  existing tiktoken dependency. It was rerun successfully with the approved
  shared `.venv` and PYTHONPATH=src:.; no installation/dependency change occurred.
- Existing frontend act warnings remain in the old tests. New tests' warning was
  resolved by awaiting the UI action; assertions remain unchanged.
- Entire backend final-readiness regression, independent review, root's real
  TXT/MD and Research refresh GUI proof, and actual qualified Intelligence →
  Save → Topic ordinary-user positive acceptance remain overall gates. This task
  makes no claim that fixture output passed any real model gate.
- Model, public network, Cloud, credential reads, downloads, owner/formal data,
  launchd, merge/release/deployment: zero authorized real actions taken. Jev was
  not invoked under this task's explicit zero-model-call restriction.

## Delivery

Suggested status: IN_REVIEW; final affected checks passed. Implementer
stops all writing after the exact committed SHA is reported. No self-approval,
main merge, task-board DONE update or production activation is performed.
Independent Reviewer and root acceptance are pending.
