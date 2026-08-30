# TASK-016E/F — Verified Note Artifact Contract Amendment

Status: `ACCEPTED`.

## Decision

The prior assumption that Weekly V2 could consume `NoteV2` directly is
insufficient. `NoteV2` is and remains an immutable deterministic semantic
presentation artifact; it is not an authority token and carries neither a
runtime admission receipt nor all weekly aggregation metadata.

Weekly V2 therefore consumes only `VerifiedNoteV2Artifact`.

```text
authoritative Deep Analysis (runtime success or verified 016D read)
  -> deterministic NoteV2
  +-> authoritative video/completion metadata + authoritative scoring read
  -> process-admitted VerifiedNoteV2Artifact
  -> deterministic WeeklyV2
```

## Layer boundaries

| Layer | Meaning |
| --- | --- |
| `NoteV2` / `NoteV2Identity` | Frozen semantic note content and its DACS-1 identity. Never authority. |
| `VerifiedNoteV2Artifact` | Runtime-verified 016E→016F handoff. It binds the Note, completed time, source/video metadata, existing score lineage, and Deep Analysis provenance. |
| `VerifiedNoteV2ArtifactIdentityV1` | DACS-1 identity over material weekly semantics: Note identity, source/video metadata, completion time, ranking score/reason and scoring lineage, plus Deep Analysis provenance/payload scope. It excludes the process-local admission receipt. |
| `WeeklyV2` | Pure deterministic aggregation over admitted artifact values only. |

## Authority and projection

The construction boundary accepts only `TrustedDeepAnalysisSuccess` or
`VerifiedPersistedDeepAnalysisRead`; it reuses the existing deterministic
`build_note_v2` path. It obtains weekly metadata before aggregation from the
authoritative completed `VideoRecord` and the existing `VerifiedScoringRead`,
then cross-checks the Deep Analysis-bound scoring request hash and provenance.

- Membership authority is `VideoRecord.completed_at`, preserving ADR-010's
  configured-timezone ISO `[start,end)` semantics.
- Top-N authority is the existing `ScoreResult.score` from the verified scoring
  reader, preserving `score DESC, video_id ASC`; artifact identity is the final
  deterministic tie-breaker only for otherwise duplicate external identities.
- The source URL is projected from the same completed `VideoRecord`, bound into
  the artifact identity, and never fetched by Weekly V2.
- `SELECTED_EVIDENCE_ONLY` remains closed: neither the artifact nor Weekly V2
  receives an unrestricted transcript.

The admission sidecar is process-local and is never persisted. A structurally
similar object, a copied Note, an identity string, or `isinstance` alone cannot
cross the boundary. There is no public API accepting `(note, score,
completed_at, source_url, ...)` as a minting claim.

## Non-goals

This amendment does not alter the NoteV2 schema, rendering, DACS-1 identity,
016D persistence shape, V1 weekly service, database schema, providers,
credentials, or Note persistence. Weekly V2 performs only selection, ordering,
fixed-field grouping, and rendering; it performs no LLM/provider call, new
analysis, repository query, or Deep Analysis read.
