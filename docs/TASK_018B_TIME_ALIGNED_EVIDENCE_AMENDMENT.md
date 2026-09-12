# TASK-018B — Time-Aligned Canonical Transcript & Evidence Binding Amendment

Status: **APPROVED PRODUCT OWNER AMENDMENT**

## Purpose and scope

TASK-018B adds m015 because pre-m015 Evidence had temporal provenance but no
immutable authority for the exact text represented by its interval.  It applies
only to V1 transcript/Evidence domain records.  It does not enable cloud
transport, qualify a provider, make a network call, enable Deep Analysis, or
authorize TASK-016G.

## Canonical timed authority

`timed_transcripts` binds one Video and one existing canonical transcript
Artifact to a deterministic SHA-256 identity over ordered cue tuples:

```text
[start_ms, end_ms, SHA-256(canonical_cue_text)]
```

`timed_transcript_cues` retains the normalized cue text and its hash.  The
plain canonical transcript remains the deterministic `"\n"`-joined cue
projection with a final newline.  Ingest rejects a timed projection that does
not equal the existing canonical plain-text projection.

Cue precision is deliberately finite: intervals are `[start_ms, end_ms)` and
new exact-text Evidence must start at its first cue start and end at its last
cue end.  A cue is included in full.  There is no word-level inference,
partial-cue slicing, average-speed estimation, fuzzy matching, or re-tokenizing
of old plain text.

## Evidence text binding

`evidence_text_bindings` records exactly one immutable binding per Evidence:
the timed transcript identity/hash, contiguous cue interval, exact excerpt and
its SHA-256 hash.  Creation validates same Video and canonical Artifact,
complete contiguous cues, exact cue-aligned range, cue hashes, and deterministic
excerpt concatenation in one transaction.  `resolve_verified_evidence_text()`
returns only a hash-verified typed projection; missing, legacy-unbound,
deleted, unavailable, foreign, or inconsistent rows resolve fail-closed.

## Legacy and privacy

m015 creates no rows from existing transcripts or Evidence.  Pre-m015 Evidence
remains historically readable under its existing contract but is explicitly
unbound for exact provider-visible text.  The new domain records contain no
credential, provider/model, local path, raw feedback, or provider request body.
They do not duplicate a full transcript; only canonical cue text and bounded
Evidence excerpts are persisted.

## Dependency order

```text
TASK-018B → TASK-022B → TASK-022A → real YouTube provider qualification
```

TASK-022B alone later owns outbound disclosure and request-hash integration.
TASK-018B creates no competing distillation request hash.
