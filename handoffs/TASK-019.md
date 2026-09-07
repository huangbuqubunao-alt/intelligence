# TASK-019 Handoff — Trusted Intelligence Read Contract

## Outcome

- START_HEAD: `b494e4d8a0e2f56862934de8ed183bc400e4b4d1`
- Database: no migration; fresh databases remain at `PRAGMA user_version = 7`.
- TASK-018A prerequisite: satisfied. Revision-specific finite claim kinds are
  now required by the reader and legacy `UNCLASSIFIED` is rejected.

## Trusted read boundary

`AuthoritativeIntelligenceReader.read_current()` is the sole issuer of the
sealed `VerifiedIntelligenceRead`. It accepts only persisted state and never
accepts a caller-provided revision, evidence list, claim kind, or lifecycle
claim as authority. The result carries opaque Intelligence/revision IDs, the
exact finite claim kind, exact lifecycle state, and exact supporting Evidence
IDs. It cannot be publicly constructed, copied, serialized, subclassed, or
normally mutated.

The reader validates the exact current pointer (and rejects pointer regression
rather than selecting the latest row), revision ownership/history continuity,
non-`UNCLASSIFIED` finite classification, state-history evidence/prior-state
coherence, exact `EVIDENCE_SUPPORT` coverage, and Evidence/artifact/video
availability/provenance. Any malformed persistence or unavailable support is a
typed fail-closed rejection. `DISPUTED` remains readable with its explicit
state; `INVALIDATED`/`OVERTURNED` are unavailable from the ordinary current
path. Claim kind is never inferred from lifecycle or text.

## Application and deletion-impact seam

`LocalApiApplication` owns two controlled DTO routes:

- `GET /api/v1/intelligence/{id}` returns only the reader projection, or an
  explicit untrusted/unavailable code.
- `GET /api/v1/evidence/{id}/impact` returns direct supported revision links
  with each revision's Intelligence identity and current/history flag.

Repository additions deliberately expose raw persistence only to the reader:
artifact lookup, revision evidence links, direct Evidence-to-revision links,
and revision dependency edges. They confer no display authority. Existing m006
triggers continue to block unsupported current Evidence deletion/unavailability;
the preview supplies the task-owned impact foundation without deleting or
rewriting historical revisions.

## Verification

- Focused TASK-019 + TASK-018/018A + local API regression: `52 passed`.
- Full suite: `2004 passed, 1 skipped, 1 warning in 59.26s`.
  The existing warning is the TASK-016C Pydantic serializer warning for a
  deliberately malformed `status='REJECT'` fixture.
- `uv run --offline mypy src`: 46 source files, no issues.
- `uv run --offline ruff check .`: passed.
- `uv build --offline`: wheel and sdist built; known uv build-system-version
  warning only.
- `git diff --check`: passed before closeout.
- Security scanner not run: the frozen graph reserves its canonical scanner
  gate for later integration checkpoints; TASK-019 changes no credentials,
  provider, or execution surface.

## Adversarial review and re-review

The reviewed attacks cover forged/rewritten trusted objects, legacy and
arbitrary claim kinds, foreign/regressed current pointers, missing support
edges, stale unavailable Evidence, artifact/video provenance failure,
invalidated state, loss of disputed and claim-kind semantics, raw persistence
decode failure, direct current/history impact completeness, and local API
projection isolation. The initial review found two P1 defects: a mutable
trusted carrier and raw malformed-persistence errors that could bypass the
stable unavailable projection. Both were fixed and re-tested. Re-review:
`P0 = 0`, `P1 = 0`, `P2 = 0`.

## Frozen boundaries

Scoring authority remains exclusively `AuthoritativeScoringReader` /
`VerifiedScoringRead`; no scoring persistence or semantics changed. No
migration, preference behavior, Topic/Weekly/Investigation authority, provider
dispatch/AMBIGUOUS behavior, Note authority, credentials, or V2 behavior was
introduced. Deep Analysis remains **BLOCKED / unchanged**.
