# V1X Phase 4 Research Lite — final acceptance

Completed locally on `chatgpt/v1x-research-lite` in
`/Users/hua/Documents/yia-worktrees/v1x-research-lite`, starting exactly from
`ba9f27fd2869e24a0b30e58f3ef6e5e29c747a7b` (schema 30).
Reviewed implementation HEAD: `3c08ec7a1e1c908c284d23a9ff726f943c2b9405`.
The final documentation commit adds this report and the validation manifest only.
No merge, push, PR, external publication or paid/model invocation occurred.

The authoritative decision and dormant infrastructure inventory are in
[the Phase 4 decision record](../docs/decisions/V1X-PHASE4-DR-001-research-lite.md).
The checked counts, complete reviewed file list, migration checksums, isolation
fingerprints and local log digests are in
[the validation manifest](V1X-PHASE4-VALIDATION.json).

## Delivered behavior

Intelligence → Research → New Research → explicit question → select 1–20 library
Content items → assemble → inspect grouped original Evidence and existing
Intelligence interpretations → trace to Content/Evidence or current Intelligence.
A saved semantic route reopens after browser reload and actual backend restart.
Rerunning creates a new immutable execution and updates the same semantic item's
current pointer. The list shows current items only. No seventh primary destination,
chat, History, timeline, Diff, export, promotion or automatic domain mutation exists.
Research remains accessible if the independent Intelligence collection read fails.

No production Research model is qualified. Capability is a deterministic local
library packet; assembly, material availability, verified provenance and unsupported
synthesis are distinct states. No DA consent/qualification is reused for Research.
No external source discovery or ingestion, Summary/DA regeneration, Topic/Following
mutation, Knowledge Delta mutation or Obsidian write is dispatched by Research.

The question is explicit, outer whitespace is trimmed, internal whitespace/case
are preserved, empty/control/invalid-Unicode and >2,000-character input is rejected.
The Content scope is sorted/deduplicated and bounded; missing/private/unavailable
Content fails explicitly. Topic and Following/source scopes are not implemented;
compatibility topics and similar source names cannot become scope authority.

Semantic identity hashes the canonical contract/question/scope/output-language
input. Execution id is random, result identity seals execution plus canonical
packet hash, and execution number protects current-pointer ordering. Original
Evidence text is never translated, synthesized, clipped into a new quote or
minted as another Evidence object. UI language is independent of configured
output language and original source language.

Candidate selection uses bounded lexical matching, existing Content/Evidence
indexes and deterministic ties. It examines at most 100 Evidence candidates and
returns at most 24 original references plus 6 admitted interpretations. Counts
and omissions are disclosed. Additional Intelligence citations cannot conceal an
omitted oversized matching candidate. Missing material produces an honestly
persisted insufficient-material packet; it does not cause web/model fallback.

## Authority, storage and restore

Migration 031 advances schema to 31 with separate `research_items` and immutable
`research_results`, a composite deferred current-pointer FK, unique execution
identity/number, indexes and identity/append-only triggers. Historical migrations
and the reserved 029 remain unchanged. A single transaction assembles, verifies,
appends and updates the current pointer; other domain rows remain byte-equivalent.

Original timed Evidence is resolved through the shared durable resolver. Research
checks source/Content/artifact ownership, deterministic Evidence identity, cue text,
ranges, hashes, availability and recorded timestamps. Candidate/Phase 1A DA records
are never read as authority. Phase 1B-promoted shared Evidence can be consumed
independently through the shared authority, without importing DA-generated claims.

Admitted Intelligence preserves the exact recorded revision, conclusion, finite
claim classification, validation state, source link, complete Evidence membership
and stances. A narrow recorded-card reader reuses admission history, dependency,
source-membership and card-hash checks; later legitimate domain revisions do not
replace the recorded interpretation. A future-dated revision, missing source link,
corrupt source pointer or any false citation fails verification. Legacy FACT,
RUMOR and SYSTEM_INFERENCE remain qualified rather than flattened into prose.

Current reads revalidate canonical JSON, semantic/result/execution identity,
scope, contract, language, timestamps, every reference and the current pointer.
They reject corruption/regression without falling back to an older result.
Frozen titles are contextual labels; legitimate metadata refresh does not destroy
source identity. Evidence validation is batched; Intelligence retains the existing
trusted card-reader pattern, capped at six cards. Query-plan inspection confirms
Content-scoped Evidence and binding indexes. No transcripts outside scope load.

Backup/Restore requires both Research tables and their source-provenance tables,
checks the packaged 031 schema/constraints/triggers, and verifies every immutable
execution and current pointer on staged authority before replacing live state.
Valid Research survives restore and restart. Corrupt and correctly resealed
fabricated-quote archives preserve valid live database bytes. Schema-30 archives
are incompatible with this exact-schema-31 build; no archive migration framework
was added.

API: POST `/api/v1/research`; GET collection, `/scope`, `/capability`, and the
current semantic-id result. Question/scope/access/corrupt-authority failures use
stable machine codes; zh-CN/en controls map these to product copy without raw
backend prose or enum leakage. All question/title/quote rendering is React text,
SQL values are parameters, no user text becomes a path, and no credentials or
production configuration/dependencies/lockfiles were changed.

## Verification

| Check | Final external evidence |
| --- | --- |
| Phase 4 contract/API/migration/persistence/provenance/restore | 84 passed, including 44 adversarial and 9 backup tests |
| Integrated V1.x plus Research | 401 passed |
| Full backend after final remediation | 3,199 passed, 1 existing optional skip, 2 expected fixture warnings; 451.35 seconds |
| All frontend | 139 passed: App 91, Research 9, Knowledge Delta 7, historical demo 32 |
| Frontend typecheck / production build | Both passed; Vite build completed |
| Ruff | All source/tests/scripts passed |
| strict mypy | 77 source files passed |
| compileall / diff whitespace | Passed |
| designmd | 0 errors, 0 warnings |
| Actual database | Schema 31; complete 1–28,30,31 lineage/checksums; quick/integrity `ok`; zero FK violations |
| Research Chrome/HTTP/SQLite | 8 full flows + 8 actual-server-restart/current-route flows |
| Integrated Chrome/HTTP/SQLite/vault | 8 preserved Phase 1/2/3 flows |
| Browser languages/widths | zh-CN/en × 320,768,1024,1440; zero console errors, overflow or external requests |

Local logs and screenshots are in `.var/phase4/runtime/validation` and
`.var/phase4/browser-final-fresh`. The reproducible browser harness is
`frontend/research-lite.e2e.mjs` with `tests/e2e/research_fixture_server.py`.
Existing integrated browser regression also ran against its disposable fixture.
Tests use the existing Python environment with `PYTHONPATH=src` from this worktree;
no dependency installation or toolchain change was needed.

The optional unchanged `test_external_provisioned_canonical_asset_preserves_golden_token_ids`
skips because `YOUTUBE_INTEL_O200K_TEST_ASSET` is not supplied. No test was deleted,
skipped by a new change or weakened. The two warnings come from intentional
malformed-archive/Pydantic fixtures. Existing changed backend test files retain
all assertions (1,880 → 1,881); only current-schema expectations advanced, and the
historical Phase 1B migration tests explicitly retain their original ≤30 lineage.

## Required hostile cases

| Owner cases | Evidence / applicability |
| --- | --- |
| 1–3: empty, whitespace, oversized question | Contract/API rejection; malformed Unicode also rejected with stable states |
| 4–5: empty/missing scope | Contract/API/service rejection |
| 6–7,9: Topic/compatibility/Following | Unsupported scopes/routes rejected; no memberships inferred or consumed |
| 8: selected Content only | Same-Content/scope resolution and cross-scope hostile references |
| 10–11: no evidence / metadata only | Honest insufficient packet; metadata never timed Evidence |
| 12–14: candidate/Phase 1A/Phase 1B | Transitional/candidate rejection; independently durable promoted Evidence accepted |
| 15: cross-scope / missing references | Real foreign Evidence, false Intelligence/revision/source/claim/state/stance references rejected; Topic membership is not scope authority |
| 16–17: tamper/restart | Payload/resealed source attacks rejected; valid process restart remains readable |
| 18–20: identity/language/rerun | Stable canonical semantic identity; output-language identity; distinct execution with one current item |
| 21–23: domain mutation | Complete non-Research-table before/after row equality |
| 24–25: no model/cloud | Unsupported synthesis remains usable; network dispatch prohibited; browser external requests zero |
| 26–27: large/tied retrieval | 130 candidates bounded to 24 with stable ordering; omission disclosure and batch query budget |
| 28–29: zh-CN/en | Real browser and unit localization, corruption/errors, all claim kinds/stances, original text safety |
| 30–31: backup/restore | Valid current and append-only executions preserved; corrupt/resealed archive rejected without replacing live state |

## Reviews and remediation

Product review inspected actual desktop/mobile screenshots and live routes.
The packet is structured around a question, visible scope, recorded interpretations,
grouped original sources and unresolved questions. It remains useful without a
model and clearly says no synthesis ran. It never expands scope or becomes chat,
History or a second search authority.

Authority review and a fresh whole-diff review inspected contracts, SQL/triggers,
shared source validation, recorded-card adaptation, API, UI, backup, tests and
actual browser behavior rather than accepting test names as proof. Findings were
reproduced and remediated: schema doctor/lineage assumptions; Evidence query
batching; canonical artifact ownership; future Intelligence timestamps; corrupt
Intelligence pointers; localized stances and real finite claim kinds; independent
Research entry availability; invalid Unicode scope handling; capacity disclosure
when additional citations are present. Repeated focused, integrated, full/static,
frontend and browser validation followed these changes. Final review: no P0/P1 or
material Phase 4 P2 remains.

## Isolation, commits and Phase 5

Integration remains clean at `ba9f27fd2869e24a0b30e58f3ef6e5e29c747a7b`.
M13 remains at `e228294f705401b0200439076c3378b78f9c9d84`, dirty count 35,
tracked diff SHA256 `75e720ea3e96d659f259aef256bde0cc73ded747b86eb7aa7c223216597f501b`,
029 SHA256 `583e5bcaeec9573f6d2ca6cb79fe26a65fa1c83aedc7d656d4cd611b2f6bccf3`.
The initial task raw-status fingerprint discrepancy is retained in the manifest;
current M13 exactly matches the accepted integration preservation record's full
status and all 34 recorded dirty-file hashes. No Phase 4 writes occurred in
integration, M13 or historical source worktrees.

Implementation commits:
- `b7f9ed90b25af413190a60e8a488ad4b78d69605`: authority, persistence, API, restore, migration and tests.
- `b59f473de5beef6d06ae773b99e9e21888ccef64`: complete Research UI and real browser harness.
- `3c08ec7a1e1c908c284d23a9ff726f943c2b9405`: final input/classification/capacity remediation and hostile archive test.

Stable identities, separate append-safe execution storage and immutable source
snapshots support Phase 5. History/revisions UX, Diff, export and promotion remain
future decisions. Current deliberate limits are explicit selected Content, lexical
relevance, bounded packets, no model synthesis and schema-31-only restore. These
are documented product boundaries, not unresolved completion blockers.

V1X_PHASE4_RESEARCH_LITE_FULLY_COMPLETE_PHASE5_MAY_START
