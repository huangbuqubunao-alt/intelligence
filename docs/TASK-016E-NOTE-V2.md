# TASK-016E — Note V2

Status: `COMPLETE` pending orchestrator acceptance.

## Contract reconciliation

Note V2 is an immutable, ordinary deterministic derived artifact, not an
authority source or a replacement for the existing V1 Obsidian persistence
path. TASK-016 has no normative requirement for a new Note table, migration, or
automatic V1 reroute, so this slice adds none.

Its required sections are Summary, Why It Matters, Core Points, Knowledge
Graph, and Evidence. The non-empty optional Knowledge V2 fields are emitted in
the fixed order Key Facts, Important Concepts, Key Arguments, Counterpoints,
Product Opportunities, Business Opportunities, Actionable Directions,
Hypotheses to Validate, Action Recommendations, and Risks.

## Authoritative inputs and provenance

`build_note_v2` accepts only either a runtime-verified
`TrustedDeepAnalysisSuccess` or the unchanged result of 016D's
`VerifiedPersistedDeepAnalysisRead`. The runtime path checks finalizer admission
and obtains runtime-owned material; the persisted path checks its exact
revalidated-read proof. Raw `KnowledgeContent`, caller hashes, raw SQL rows,
lookalikes, copies, and tampered rows cannot construct a Note.

The compact provenance binds result and KnowledgeContent identities; A1/A2/A3;
validation-policy and Evidence Registry identities; scoring request hash and
separate `PRIMARY | REPAIR_H2C` classification; payload scope; and
provider/model audit identities. Note identity is DACS-1 over V2 semantic
content and that provenance, excluding observational timestamps and paths.

## Rendering and privacy

Rendering is a pure Markdown transformation using the existing bounded Markdown
escaping rules. Evidence appears only when cited by validated KnowledgeContent,
in exact Registry order, with ID/source/excerpt and trusted timestamps where
present. Note V2 does not take transcript input. In a
`SELECTED_EVIDENCE_ONLY` source it cannot reconstruct or expose unselected
transcript text.

## Reuse

`DIRECT`: existing KnowledgeContent/Evidence Registry, DACS-1, 016D verified
reader, runtime finalizer admission, and existing safe Markdown rendering
helpers. No dependency, migration, provider adapter, credential code, network
call, V1 persistence wiring, or Weekly V2 logic was added.

OpenAI live qualification remains `PENDING / CREDENTIAL BLOCKED`.

## Verified aggregation handoff amendment

TASK-016E additionally exposes the separately admitted
`VerifiedNoteV2Artifact` handoff for TASK-016F. This is a boundary bridge, not
a change to `NoteV2`: the Note schema, deterministic render and semantic DACS-1
identity remain frozen, and `NoteV2` remains `NOT AUTHORITY`. The wrapper binds
weekly-only authoritative metadata outside Note semantics; see
`TASK-016EF-VERIFIED-NOTE-ARTIFACT-CONTRACT-AMENDMENT.md`.
