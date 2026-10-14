# LOCAL TXT/MD Intelligence contract

This isolated implementation uses the accepted LOCAL source snapshot, canonical
text, extractive Summary pointer and source Evidence resolver. A manual command
requires the actual LOCAL_LIBRARY/DISCOVER_ONLY source and current verified
Summary; it never enables automatic library processing. LOCAL Cloud routes stay
unavailable before credentials, payload construction or invocation.

`local-text-distillation-v2` references contain exact Evidence ID, TEXT_RANGE,
Unicode code-point half-open offsets, derived one-based lines, source/canonical/
excerpt hashes, and explicit NULL start/end times. Mixed or missing fields,
fabricated ranges/hashes, duplicate JSON keys, foreign Evidence and incomplete
NO_NEW coverage are rejected. The old YouTube v5/timed wire, card hashes and
timed card DTO remain unchanged.

Schema 39 adds only the specifically approved immutable 15-field
`local_text_input_proofs` sidecar. Reservation validates current source facts and
creates checkpoint plus proof in one BEGIN IMMEDIATE transaction before dispatch.
The canonical original input/context JSON is bounded to 512 KiB combined UTF-8;
it preserves full source excerpts/ranges, display metadata, language, immutable
preferences and both policy revisions/effective rules, and the exact independent
profile/model/digest/prompt/schema/options. It creates no new DATA artifact.

`distillation:local-text-v2:<input hash>:<context hash>:<identity hash>` and the
card hash bind the recomputed proof projections/profile to one exact execution
and successful ledger. The version is never inferred from NULL timestamps or
alternative hashes. The old unpublished v1 local text format is not backfilled.
The old YouTube/timed identity and hash algorithms remain unchanged.

The context identifies the original Summary artifact/hash/language, its actual
Evidence and deterministic reconstruction. Historical validation reads those
specified original bytes, resolves the original Evidence, reconstructs the
original result/request hash and rehashes the complete sealed input/context.
A legal subsequent Summary refresh or preference/policy change preserves that
history. Damage to original Summary/source/Evidence/proof closes trusted reads.

Admission and NO_NEW revalidate the proof plus current context/CAS in their
existing transaction. Public `read_current` classifies LOCAL TEXT from durable
revision/card/execution associations, then invokes the same `_read_card` validator;
a missing card projection cannot downgrade to generic. Missing proof or ledger
rejects current/recorded cards, Save, saved-list trust and Topic association.
An ordinary generic revision with no distillation association stays readable.

The reserved revision identity family
`revision:distillation:distillation:local-text-v<decimal version>:` independently
requires strict verification, even if all card/checkpoint/ledger/proof rows are
missing. This identity grants no authority. Unknown future versions fail closed;
only the exact supported v2 execution and its exact revision identity can pass.
Incidental substrings and non-version suffixes do not classify generic revisions.
Schema39 Backup/Restore also traverses produced revisions through that same
reader, so removing all forward associations cannot bypass validation.

New schema 39 backups validate every proof and execution/ledger/result binding,
including canceled and unknown terminal executions. Old 34–38 packages retain
original validation/staging/activation contracts; normal startup runs the existing
continuous migrations followed by additive 039 (38 needs only 039). All original
domain rows and DATA are preserved; migration records and expected empty tables
are the only new state. No historical input is invented.

The existing Evidence display shows real lines (or honest unavailable text).
Internal navigation serializes only Content ID and Evidence ID. After refresh,
the current Content Evidence DTO must contain that same Evidence before focus
can occur; no URL parameter supplies offsets or timestamps. The view remains
the existing workspace layout documented in `frontend/src/workspace/DESIGN.md`.

`scripts/prepare_readiness_local_text.py` prepares the independent research
profile and optional exact request projection only. It has no model execution
entry point, runtime factory registration or qualification receipt. The pinned
9B model and original qualification remain failed; production qualification is
false, execution authority NONE, and real calls zero. Future LOCAL8 and genuine
ordinary Intelligence/save/Topic acceptance remain blocked by that prerequisite,
exact input/code freeze, independent pre-output review and a specific start
instruction. All positive tests in this task are explicitly offline fixtures.
`LOCAL_TEXT_PREPARATION_PROFILE_V3.json` records this repair candidate's source
hashes with unchanged v2 wire/profile, zero calls and authority NONE. V1/V2
preparation records remain historical evidence, not current code freezes.

User-facing reading steps: import TXT/MD, open Content and its original Evidence;
read the displayed line ranges; use Open Content from an Intelligence Evidence
reference to return to the same internal range. Refresh preserves that reference
identity and revalidates it. Cloud remains unavailable for local documents. A
WAITING_MODEL result reports the actual missing qualified model and can be
cancelled through the existing safe action; it does not manufacture a result.
