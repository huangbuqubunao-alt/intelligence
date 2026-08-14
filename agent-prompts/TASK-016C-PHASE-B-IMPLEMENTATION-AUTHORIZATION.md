# TASK-016C Phase B Implementation Authorization

## Status

`READY / AUTHORIZED FOR WORKBUDDY PHASE B ONLY`

## Fixed ancestry

- Accepted design: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Accepted Phase A implementation: `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`
- Current Phase A evidence head: `cbbe398e4d50a3c5b62f6d1bc20f83915f51aabc`
- Execution branch: `workbuddy/task-016c-content-quality-layer`

The Phase B implementation commit must be a descendant of `cbbe398e…`, preserving both
the accepted Phase A implementation and the accepted design as ancestors. It must not
squash, rebase, rewrite, or drop Phase A history. Phase B may create exactly one
implementation commit.

## Objective

Implement the pure local `DeterministicContentQualityGate`. Its only permitted deterministic
rejections are `EMPTY_CONTENT`, `CONTROL_CHARACTER_INVALID`, and `EXACT_REPETITION`.

The Gate never returns `PASS`, calls no Judge/LLM/Ollama/network/model/Cloud service, and
creates no Artifact, cache, ProviderCall, database, filesystem, or persistence effect.

## Allowed files

- `src/youtube_intel/quality.py`
- `tests/unit/test_task016c_quality_gate.py`
- `src/youtube_intel/domain.py` only when the accepted Phase A domain contracts cannot
  support Gate integration otherwise; the handoff must state the exact need and prove the
  change minimal.

## Forbidden scope

Do not modify `providers/ollama.py`, `scoring.py`, `state.py`, runtime composition, Artifact,
cache, database, migration, ProviderCall, H1/H2, QualityPassAttestation,
TrustedScoringFinalizer, filesystem protocol, repair orchestration, TASK-016B Language
Validator, Cloud, Router, Weekly production, or Phase C–K.

Do not add dependencies or `uv.lock` changes, entity/brand/technology/acronym dictionaries,
NLP, token heuristics, semantic similarity, fuzzy matching, POS/dependency analysis, stemming,
lowercase/casefold, Unicode normalization, or external calls.

## Frozen Gate semantics

### `EMPTY_CONTENT`

Inspect Gate input `reason` only. Reject raw-empty input or input empty after fixed ASCII
whitespace trim. Do not make language, quality, semantic, usefulness, entity, or identifier
decisions.

### `CONTROL_CHARACTER_INVALID`

The fixed order is:

```text
raw input scan → reject invalid characters → normalization for repetition only
```

Allow LF `U+000A` and TAB `U+0009`. Reject all Unicode `Cc` except those two, plus NULL
`U+0000`, ZERO WIDTH SPACE `U+200B`, and BOM / ZERO WIDTH NO-BREAK SPACE `U+FEFF`.
`U+200B` and `U+FEFF` are explicit rejects and cannot rely on category alone.

### `EXACT_REPETITION`

Operate on `reason` only:

1. fixed ASCII trim;
2. LF split;
3. remove exact empty segments;
4. compare adjacent segments by exact code-point equality.

Required outcomes: `A\\nA` rejects; `A\\nB`, `A\\nB\\nA`, and `Same\\nsame` continue.
Lowercase, casefold, Unicode/punctuation normalization, tokenization, fuzzy/semantic
comparison, and entity matching are forbidden.

## TDD and acceptance

Write RED tests before minimal GREEN implementation. Cover empty and ASCII-whitespace-only
content, valid boundary content, LF/TAB acceptance, `Cc`/NULL/`U+200B`/`U+FEFF` rejection,
adjacent and non-adjacent repetition, exact-empty handling, ASCII trim, and proof that
identifier/entity/technical phrases continue without Gate classification.

Tests must kill these incorrect variants: removal of control validation, fuzzy repetition,
lowercase/casefold normalization, and removal of exact-empty-segment handling. Transient
mutation probes must be reverted before commit.

Required gates:

```bash
uv lock --check
uv sync --locked --offline
uv run pytest -x -q tests/unit/test_task016c_quality_gate.py
uv run pytest -x -q
uv run mypy src
uv run ruff check .
git diff --check
```

## Commit and rollback

Create exactly one implementation commit:

```text
TASK-016C Phase B implement deterministic safety gate
```

The commit must be independently revertible without data remediation, migration, Artifact
cleanup, or cache invalidation. Stop after completion: no merge, push, tag, or Phase C.
