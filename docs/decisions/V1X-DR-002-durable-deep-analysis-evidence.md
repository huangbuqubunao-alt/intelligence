# V1X-DR-002: Phase 1B durable Deep Analysis Evidence convergence

Status: Accepted implementation of Owner-frozen Phase 1B / R3 authority rules.
Date: 2026-10-02. Predecessor: [V1X-DR-001](V1X-DR-001-content-deep-analysis.md).

This records new V1.x work; it does not amend historical V1 product scope or
reopen the reviewed Phase 1A closure at
`55317503716681c886d7dc5a69e25c7ec0fd4072`. Deep Analysis remains an advanced
Content action, separate from Summary and the Content → Intelligence → Topic
chain. Knowledge relations, Knowledge Delta, Research and DA Obsidian publishing
remain deferred. Production model qualification remains Phase 1C.

## One Evidence authority

Only backend-admitted timed transcript cues can support authoritative citations.
Metadata, title, descriptions and source labels remain context only. A
canonical-only transcript cannot produce authoritative citations and fails
closed before dispatch. Missing authority is reported honestly.

Phase 1B reuses `timed_transcript_candidates`, the Summary `_plan_promotion`
builder, repository `_promote_summary_evidence_in_transaction`, and the shared
verified Evidence text resolver. It creates no alternate Evidence store.
Candidates are deterministic whole cue groups, capped at 24; groups above the
2,000-character admitted excerpt limit are omitted, never truncated. The model
only references issued candidate ids. Backend validation reconstructs the
registry from current trusted cues; then selected candidates become real
`evidence` rows with `evidence_text_bindings`. Backend construction owns original
text, cue bounds, real timing, ownership and `build_evidence_id` identity.

Candidate ids are not aliases for durable ids. The native persisted claim JSON
contains only promoted durable ids. Temporary candidates survive solely in the
immutable request/provider audit needed to replay admission. An id's syntax,
including a valid-looking SHA256 or an already-existing foreign Evidence id, is
never proof that the model was issued that candidate.

## Explicit contract identities

Provider output remains five roles, with bounded candidate `evidence_refs`:
`v1x-content-deep-analysis-model-output-v2`. Prompt identity is
`v1x-content-deep-analysis-phase1b-prompt-v1`. The provider never authors
KnowledgeContent, Evidence excerpts, offsets, timestamps or durable identities.
Text canonicalization, capacity, epistemic kinds and relevance minimum reuse the
frozen Phase 1A admission rules. `why_it_matters` still derives only from the
first relevance claim. Optional uncertainty/next-question lists remain optional.
Declared claim citations retain the historical AnalysisPoint policy of 1..10
refs; no historical zero-ref AnalysisPoint contract is widened or removed.

The existing result table gains `persistence_version` and
`durable_authority_identity`. Native persistence version is
`deep-analysis-persistence-v2`; durable JSON schema is
`v1x-content-deep-analysis-durable-result-v1`. It contains ordered role, text,
epistemic kind, exact durable refs, output language and honest per-claim language
validation. Exact supported validation policy is
`PHASE_1B_VALIDATION_POLICY`; this binds the new schema, grounding, five-role
language, no-KG and provenance policy versions into A1/A2/A3 and cache identity.
A separate integrity digest binds durable JSON, result/model-content identity,
policy and creation/validation times. Hash checks supplement semantic replay;
resealing corrupt JSON does not grant authority.

`result_identity` remains the append-only execution/provenance identity, not a
semantic merge key. No cross-run merge is introduced. Future semantic identity
may combine Content identity, output language and knowledge schema identity.
An internal KnowledgeContent read adapter preserves existing consumer types and
exact per-claim refs; its compatibility topics remain semantically inert.

## Membership and same-Content enforcement

Migration 030 creates:

```sql
CREATE TABLE deep_analysis_evidence (
  result_identity TEXT NOT NULL REFERENCES deep_analysis_persisted_results(result_identity),
  evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
  created_at TEXT NOT NULL,
  PRIMARY KEY (result_identity, evidence_id)
);
CREATE INDEX idx_deep_analysis_evidence_evidence_id
  ON deep_analysis_evidence(evidence_id);
```

PK and FKs enforce unique pairs and existing result/Evidence rows on normal
repository connections. They do not prove Content ownership or that JSON cites
the linked row. Application write and read logic therefore requires the linked
set to equal the union of all claim refs exactly, with no extras or omissions.
It verifies canonical result Content → timed transcript → canonical artifact →
Evidence ownership, as well as AVAILABLE, PRIMARY_ORIGINAL, EXTRACTION source
policy, original language, deterministic identity, cue/text hashes and timing.
Cross-Content authority fails closed even when both rows and both FKs are valid.

## Transaction, restart and retry

One `BEGIN IMMEDIATE` transaction reconstructs the source authority, promotes
all selected Evidence plus text bindings, inserts the native result and complete
provider/audit/validation records, inserts memberships, and performs the entire
trusted-read verification before COMMIT. Any promotion, result, membership or
verification failure rolls back all newly created authority. Existing shared
Evidence survives failed retries; no partial result can be trusted.

Retries look up exact result identity or eligible cache identity, require
consistent admitted model-content identity, and reverify the existing complete
row. The original timestamps and membership remain unchanged. Conflicting or
corrupt cached results are rejected rather than overwritten.

Trusted read uses one SQLite snapshot and reconstructs admission and promotion
from live source authority. It verifies supported persistence/schema/policy,
A1/A2/A3, canonical Content/source/output language, request/consent/context,
provider/model/envelope/payload identities, strict provider JSON, result/content
provenance identity, complete single-attempt replay, cache eligibility,
creation/validation timestamps, durable JSON integrity and semantics, exact
memberships, same-Content/source Evidence resolution and all five role languages.
No candidate ref can survive authoritative binding. Existing product semantics
skip a corrupt newer result in favor of the newest older verified result; when
none verifies, no result is returned. Being newest or running the migration is
never an authority grant.

## Legacy, Note V2 and language

Migration defaults existing rows to `deep-analysis-persistence-v1`. There is no
backfill, alias or automatic upgrade. Phase 1A rows remain readable with a
transitional citation notice, no public candidate ids, and rejected trusted
Note/export eligibility. Authoritative citation use requires regeneration via
Phase 1B.

Only an unchanged opaque verified persisted Phase 1B read becomes Note V2
eligible. Raw runtime successes remain insufficient. Native Note uses original
Evidence and exact relationships across all five roles, excludes compatibility
KG/topics, and keeps the existing Note schema. This does not publish DA to
Obsidian or promote DA into Summary. The Content UI exposes verified citation
links through its existing Evidence view and refreshes that view after a run.

Language validation runs independently on every claim in all five roles at
admission, binding and reread. INVALID fails trust; UNCERTAIN remains UNCERTAIN
and is labeled in the UI. Existing mixed-script/name/code/technical-term rules
are reused, without a new script-percentage heuristic. UI, output and source
language remain independent. Evidence stays original-language; translations are
presentations, never a second authority.

## Migration ordinal and Backup/Restore

The starting clean V1.x history ended at 028. Read-only M13 inspection confirmed
HEAD `e228294f705401b0200439076c3378b78f9c9d84`, 35 dirty/untracked entries and an
untracked `029_add_v1_model_configuration.sql`; no committed/integrated 029 was
present in repository history. Its SHA256 was
`583e5bcaeec9573f6d2ca6cb79fe26a65fa1c83aedc7d656d4cd611b2f6bccf3`.
Therefore Phase 1B allocates **030**, preserving M13's in-flight ordinal.
Migration loading uses file ordinals, not list positions. There are 29 packaged
migrations and the resulting SQLite user_version is **30**. Upgrade/retry tests
preserve the existing history/checksums and confirm PK, FKs, index, rollback,
quick_check, integrity_check and legacy preservation. No M13 files are used by
migration tests or changed by this implementation.

Backup required-table coverage now explicitly includes
`deep_analysis_persisted_results`, `deep_analysis_evidence`, `evidence`,
`evidence_text_bindings`, `timed_transcripts`, `timed_transcript_cues`, `artifacts`
and `videos`. A schema-discovery coverage assertion detects new DA tables or
result-FK dependents omitted from that verification set. Unrelated tables are
not automatically required.

Backup and restore check exact migration history/schema version, membership
constraints and foreign keys, then reverify every DA result and the complete
staged Evidence graph. Existing safe archive parsing, DATA hash validation,
staging, confirmation, activation and rollback are preserved. Missing results,
Evidence or memberships, dangling or unreferenced memberships, wrong Content,
resealed JSON, unsupported identities and corrupted provider/attempt state all
reject before replacing live state. Valid restore retains trusted Note eligibility.

**Compatibility sharp edge:** restore requires exact schema version 30. Older
version-28 (or other-version) archives are not directly restorable by this build.
No backup migration framework is added. Existing valid live state is preserved
on incompatible/corrupt archives.

## Review and validation record

Self-review pass 1 inspected the real migration/promotion/reader/Note/restore
diff and the ten A–J authority questions. Remediations included schema health
checks, exact result retries, membership constraint verification and native
canonical schema/prompt binding. Pass 2 independently attacked resealed JSON,
all claim relationships, cross-Content data, source authority and provenance.
It found incomplete historical attempt replay: A1/A2/A3 alone did not detect
changed provider/model/consent/ordinal/transport fields. Phase 1B now replays the
whole single-attempt record using the runtime's shared constructor; five red
probes became regression tests. Historical Phase 1A trust is not reinterpreted.
A further corrupt newer-row probe found that invalid UTF-8 escaped the read
validation boundary; the reader now classifies malformed encodings/structures
as rejected rows, preserving fallback to an older verified result.
Browser probes found durable-id overflow at 320px; scoped citation/Evidence
wrapping fixes it without changing product navigation.

All 20 Owner-required authority attacks are covered by real-SQLite tests,
including failures after Evidence, result, membership and precommit validation;
resealed archive attacks verify byte-identical live database/DATA preservation.
Final validation counts, commit identity, M13 preservation and final HEAD review
are recorded in the Phase 1B completion report. No paid/cloud/model dispatch,
production qualification, generic routing, dependency change, PR, push or M13
mutation is part of this milestone.
