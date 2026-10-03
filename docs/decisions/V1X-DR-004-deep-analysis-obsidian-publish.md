# V1X-DR-004: Phase 2 Deep Analysis → Obsidian Publish

Status: Owner-authorized V1.x implementation. Date: 2026-10-03.
Dependency: accepted Phase 1B `432f085d76824dfa51a447622aa2dba23ff8bfc8`.
This adds a V1.x projection; it does not rewrite historical V1 scope.

SQLite is the only product authority. Obsidian is a user-owned, external,
one-way Markdown projection. There is no round-trip import or synchronization;
editing a note cannot affect Deep Analysis, Evidence, Summary, Intelligence,
Topic, subsequent analysis inputs or trusted provenance.

Publication requires an explicit Content action. Generation, startup, reads,
restart and configuration never publish automatically. The existing configured
vault root/subdirectory is reused. There is no additional enable flag, vault
discovery or layout replacement. A configured target does not authorize an
automatic write. Test fixtures use disposable vaults only.

## Authority and product rendering

The publisher consumes the existing newest-verified Content read, including its
corrupt-newer-row fallback, then the existing opaque verified-read check and
`require_trusted_note_eligibility`. Native durable Phase 1B is required. The
trusted read already proves supported schema/policy, result-specific membership,
same-Content original Evidence, complete admission and restart provenance.
Phase 1A, raw runtime output, forged reads, candidates, missing memberships,
cross-Content corruption and unsupported schemas cannot publish. Prompt labels
echoed into canonical claim prose cause export rejection rather than editing or
omitting a claim. This presentation guard adds no product authority.

The new `NoteKind.DEEP_ANALYSIS` (`deep-analysis`) is distinct from Summary,
Video and Weekly notes. The managed folder is `Deep Analysis/` beneath the
existing logical `vault_root/vault_subdir`, following the sink's kind-folder
pattern. Note V2 supplies verified original Evidence references; the durable
result supplies each exact claim and its ordered Evidence ids. Rendering has
five localized headings: Core conclusion, Key evidence, Uncertainty, Relevance
to you and Next question. Optional empty roles stay empty, without fake prose.
Each claim carries its own durable citation ids; original excerpts and real
timing appear in a clearly labeled Evidence section. Inline Markdown escaping
and whitespace presentation reuse the existing note convention. No model
excerpt or new Evidence translation is created. UNCERTAIN language remains
labeled. There are **no invented wikilinks**, including from model/title text.

## Stable semantic identity and provenance

The merge key is the repository's DACS-1 SHA256 of:

```json
{
  "schema_version": "deep-analysis-obsidian-semantic-key-v1",
  "content_identity": "<canonical Content identifier>",
  "output_language": "<en or zh-CN>",
  "knowledge_content_schema_identity": "<verified request schema>"
}
```

Here **Content identity** means `canonical_input.video_identity`, the durable
identity of the Content. The historical persisted read's `content_identity`
field is a **generated KnowledgeContent payload digest**, not the Content id;
it changes when claim output changes and is therefore recorded separately as
`knowledge_content_identity`. Using that digest as a merge component would
violate the frozen same-Content-rerun rule.

`result_identity` is provenance only. It never participates in filename suffix
or managed-note lookup. A newer valid execution updates the same semantic note,
even when its result identity, generated-content hash or Content title changes.
The first path remains stable through title changes and restarts. `en` and
`zh-CN` have separate keys. Relevant schema changes have separate keys; an
unsupported schema is rejected until product authority supports it. The UI
submits the displayed result identity to prevent stale actions from publishing
an unseen replacement. That request binding is not a merge key.

JSON-quoted YAML frontmatter includes kind, product/ownership marker, projection
schema, semantic note identity, canonical Content identity, video id,
**output_language**, knowledge schema, result identity, generated-content hash,
authoritative creation/validation times, durable Evidence schema and validation
policy identity. No candidates, credentials, cloud keys or tokens are included.

## Filesystem, editing and recovery

The existing `ObsidianNoteSink`, filename sanitization, fixed sandboxed Jinja
templates, managed/user markers, bounded regular-file reader, anchored directory
FDs, no-follow opens and atomic writer are extended. NFC/portable title rules
and a full semantic-hash suffix prevent traversal and collisions. Multiple
matching suffixes fail closed. A preexisting file must have exact Content,
kind, producer, semantic identity, language, schema and standalone ownership
markers. Renamed unsafe basenames are rejected before any write. Unrelated
user files are never adopted or overwritten.

Republish replaces generated frontmatter and the managed region, preserving the
existing `My thoughts`/`我的思考` user region byte for byte. It does not implement
a three-way Markdown merge. Edited/missing ownership markers fail safely.
Owner-authored user-region links remain owner content, not generated knowledge.

The shared writer verifies and fsyncs a complete temporary file, rechecks the
destination and uses atomic no-replace hard-link publication for first creation.
Updates retain the prior inode until directory fsync completes, so a injected
post-replace fsync failure can restore the previous complete note. Rollback
checks the newly published inode/content before acting and cannot knowingly
replace a concurrent owner's edit. Temporary/rollback names are hidden and are
never Markdown notes. Partial-write, file-fsync, replace, directory-fsync,
read-only, collision and symlink failures are regression tested. The existing
root-final-component/subdirectory/child symlink and directory-chain guarantees
remain; this does not claim a general hostile-filesystem transaction primitive.

Publish status is a read-only machine state; action outcomes are PUBLISHED,
UPDATED or UNCHANGED. NO_VAULT, RESULT_INELIGIBLE, RESULT_CHANGED and WRITE_FAILED
drive localized UI copy. File paths are relative and wrap on mobile. No primary
navigation destination is added. There is no new publish audit table or
migration; publication never advances processing jobs or changes authority rows.

## Backup and parallel-development boundaries

External vault files are **excluded from Intelligence SQLite/DATA Backup and
Restore**. Missing projections after restore are not corruption; the user can
explicitly republish from verified SQLite authority. The vault never becomes a
required artifact in product backups. Real archive/restore tests prove this.

Publication is independent of current production generation qualification. A
previous valid result is publishable while current generation is NOT_QUALIFIED.
Phase 1C routing, qualification, cloud consent/cost and production model rules
are not changed or consumed. Phase 1C and M13 worktrees are read-only audit
subjects. No migration, dependency change, model/network dispatch, real-vault
write, merge, push, PR or deployment is part of this phase.

## Verification and review

The Phase 2 integration suite covers every owner-required adversarial scenario,
plus prompt-label prose leakage, malformed markers, concurrency, stale actions
and model-authored wikilinks. Reviews inspect actual Markdown and the diff from
accepted Phase 1B. Filesystem findings are fixed in the shared infrastructure,
then its existing regression suite is rerun. Full validation counts, commits
and isolation observations are recorded in `handoffs/V1X-PHASE2-OBSIDIAN.md`.
