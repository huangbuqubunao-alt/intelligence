# V1X-PHASE6-DR-001: Derived Research revision comparison

Status: Phase 6 implementation under the owner's continuous goal, 2026-10-03.
Accepted base: `15f720377b661164a227ba599281b81b33a1e189`; schema 31.

## Definition and authority

Research Diff answers what differs between two trusted immutable revisions of
one stable Research semantic item. It is a read projection, computed on demand.
It creates no execution, revision, table, cache, current pointer, provenance,
backup entry, Intelligence evidence, Knowledge Delta fact or Obsidian artifact.
No migration, model/provider/cloud dispatch, translation or external web call.
Jev model routing is not used under this goal's explicit no-model boundary.

Phase 5 audit: execution equals revision; sealed result identity identifies the
revision. Exact packet JSON and payload/result seals bind per-item execution
sequence, question, selected Content, output language and source snapshots.
Existing `verify_row` is the trusted historical-read boundary. Diff validates both
rows through that boundary inside one read-only transaction. Missing Research,
missing base/target, wrong owner, incompatible contract and corrupt/unavailable
authority fail closed. No untrusted packet is projected. Current pointer, today's
retrieval and latest Intelligence are never used to derive the explicit Diff.

GET `/api/v1/research/{research_id}/diff?base_revision=…&target_revision=…`
requires three 64-character lowercase hex identities. Duplicate/unknown/missing
query parameters are rejected. Base → target preserves caller direction, even
newer → older. Self-comparison is valid and returns no material changes.

## Product semantics and matching

The persisted packet has original Evidence and recorded Intelligence
interpretations; there is no separate generated-finding identity or narrative.
The typed `research-diff-v1` projection keeps authority classes separate:

- Referenced Content: Content ids used by Evidence/interpretations, matched by
  Content id. Selected scope remains fixed identity context on both revisions.
- Evidence: durable Evidence id, with exact stored excerpt/range/language and
  Content target. Added entries come from target; removed entries from base.
- Interpretations / Intelligence revision references: canonical SHA256 of stored
  Intelligence id, revision id, Content/source id, conclusion, classification,
  recorded state and sorted Evidence–stance pairs. Array positions and display
  labels are not identities. Different structured interpretations are removed
  and added; we do not claim a semantically “changed finding.” This group also
  represents old/new Intelligence revision references without double counting.
- Changed packet fields: material status, Evidence/Intelligence candidate counts,
  retrieval truncation and canonical unresolved flags. These are factual packet
  metadata, never stronger/weaker support or generated change analysis.

Each group includes unchanged count. Added/removed entries sort by authoritative
id or canonical digest, with deterministic derived entry ids. Fixed field order
controls packet changes. Evidence–stance relation pairing remains intact.
Execution id, sequence, assembled timestamp, result seal and contextual Content
title changes do not create material changes. Sequence/timestamp/scope labels are
revision context outside change lists. Question/scope/language/contract identity
mismatches are rejected, never ordinary edits or silently normalized.

The summary sums added/removed reference entries across the three distinct
classes and counts changed packet fields. It does not count unique real-world
facts or infer strength. Insufficient ↔ available transitions remain factual
status and reference changes. Identical reruns have a legitimate empty state.

## Bounds, product and restoration

Full comparison is bounded by accepted packets: each side has at most 20 selected
Content, 24 Evidence and 6 interpretations; at most five packet fields change.
No Diff pagination or silent subset truncation. `complete` means complete for
these two bounded packets, not exhaustive library retrieval. Packet truncation
remains visible. Historical labels and references come from their own sides.
Content/Evidence links use exact stored ids. Intelligence navigation follows the
existing product contract: today's Intelligence state; a stored revision label
and own Research revision link preserve historical traceability.

History remains a bounded section of Research detail, with six primary nav
entries. Current can compare with the first trusted previous entry on the first
History page; historical can compare with explicitly resolved current. Page-level
unavailable/corrupt states remain honest; no unbounded search for a previous row.
Backend supports arbitrary trusted A/B for future selection. Diff deep routes
retain explicit ids for reload/restart and source-return navigation. Controls and
machine errors support zh-CN/en; original source content is never rewritten.

Backup contains only accepted revision/source authorities. Restoring them
recomputes identical explicit Diff. Moving current to C or adding later Evidence
or Intelligence cannot alter A/B. Opening Diff never emits Knowledge Delta or
any cross-product authority. Future comparison work may extend derived typed
projections or selection UX; persisted Diff, synthesis, cross-item comparison,
Knowledge Delta integration and Obsidian export require separate decisions.

Reuse: DIRECT existing Python/Pydantic/React, canonical hashing, sealed historical
validator, source navigation and backup staging. New scoped projection/API/UI and
adversarial tests only. No new dependency, toolchain or historical-doc rewrite.
