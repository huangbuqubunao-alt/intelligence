# TASK-016F — Weekly V2 Closed-Loop Review

Status: `APPROVE` — implementation complete pending orchestrator acceptance.

## Scope and invariant

Weekly V2 is a pure deterministic aggregation over process-admitted
`VerifiedNoteV2Artifact` values. `NoteV2` remains deterministic presentation,
not authority; its schema, renderer, and DACS-1 semantic identity are unchanged.

The handoff is created only by the already-initialized `RuntimeOperations`
composition. It captures the real runtime database path, data root, and scoring
configuration, then reconstructs fresh SQLite/scoring readers for each build.
It projects `VideoRecord.completed_at`, `VideoRecord.source_url`, and verified
`ScoreResult.score`; the process-local receipt is not persisted or part of the
artifact identity.

## Adversarial review rounds

1. The first review found two P0 minting paths: caller-provided repository/
   scoring lookalikes and an exposed admission writer. Both were removed.
2. The second review found nominal type checks remained forgeable by instance
   monkey-patching. The builder was moved into runtime-owned composition and a
   regression proves mutated runtime repository/reader instances are ignored.
3. The final review found a pre-runtime generic binder path. It is now private,
   exact-`RuntimeOperations` only, and its pre-runtime import order binds the
   real composition before rejecting a caller-defined class.
4. Independent final review: `APPROVE`, P0 `0`, implementation-critical P1 `0`.

## Evidence

- Boundary tests reject plain Note, Markdown, KnowledgeContent, live Deep
  Analysis, raw persisted SQL row, dict, identity string, copied/tampered
  artifact, and caller fake score/date/URL paths.
- Week membership uses ADR-010 configured-zone ISO `[start,end)` semantics;
  Top-N uses verified `ScoreResult.score DESC`, then `video_id ASC`, then
  artifact identity. Duplicate artifact identities deduplicate deterministically.
- The injected `SECRET_WEEKLY_UNSELECTED_TEXT` sentinel is absent from Note,
  artifact, Weekly identity, and rendered Weekly output.
- Live trusted and verified-persisted 016D inputs produce equal artifacts and
  Weekly V2 results.
- `uv run pytest`: `1894 passed, 1 warning`; focused artifact/Weekly tests:
  `15 passed`; `uv run mypy src`, Ruff, and `git diff --check`: PASS.

No LLM/provider/network call, migration, Note persistence, raw repository or
Deep Analysis read from Weekly, TASK-016B/C/D semantic change, push, or tag was
performed. OpenAI live qualification remains `PENDING / CREDENTIAL BLOCKED`.
