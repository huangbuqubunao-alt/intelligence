# TASK-016C Phase B — WorkBuddy Implementer Prompt

You are authorized to implement **TASK-016C Phase B: Deterministic Safety Gate only**.

## Fixed source

Before editing, verify:

- branch: `workbuddy/task-016c-content-quality-layer`;
- accepted design: `c547b7c46afbf254979331c2c56cddb93a8503f2`;
- accepted Phase A implementation: `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`;
- current Phase A evidence head: `cbbe398e4d50a3c5b62f6d1bc20f83915f51aabc`;
- clean tracked worktree.

Your Phase B commit must descend from the complete Phase A history. Do not squash, rebase,
rewrite, or drop that history. Do not read, alter, stage, or commit `.workbuddy/`,
`config/settings.yaml`, or `config/channels.yaml`.

## Goal and allowed paths

Implement a pure local `DeterministicContentQualityGate` using only:

- `src/youtube_intel/quality.py`
- `tests/unit/test_task016c_quality_gate.py`
- minimally `src/youtube_intel/domain.py` only if strict Phase A contract integration requires it.

The Gate can reject only `EMPTY_CONTENT`, `CONTROL_CHARACTER_INVALID`, and
`EXACT_REPETITION`. It never returns `PASS`; all structurally valid unknown content continues
to a later phase.

## Required behavior

1. `EMPTY_CONTENT`: reject only raw-empty or fixed-ASCII-trim-empty `reason`.
2. `CONTROL_CHARACTER_INVALID`: raw scan before repetition normalization; allow LF/TAB;
   reject other `Cc`, NULL, `U+200B`, and `U+FEFF`.
3. `EXACT_REPETITION`: ASCII trim → LF split → exact-empty removal → adjacent exact
   code-point equality.

No Judge, LLM, Ollama, network, model, Cloud, persistence, Artifact, cache, ProviderCall, DB,
filesystem, dictionary, token, entity, semantic, fuzzy, POS/dependency, stemming, lowercase,
casefold, or Unicode-normalization behavior is authorized.

Do not modify `providers/ollama.py`, `scoring.py`, `state.py`, runtime, TASK-016B Language
Validator, DB/migrations, H1/H2, attestation, finalizer, filesystem protocol, repair, Cloud,
Router, Weekly production, or Phase C–K. Do not add dependencies or edit `uv.lock`.

## Mandatory TDD

Write RED tests first, then implement the smallest GREEN behavior. Cover:

- empty, ASCII whitespace, and valid boundary;
- LF/TAB acceptance and Cc/NULL/ZWSP/BOM rejection;
- `A\\nA`, `A\\nB`, `A\\nB\\nA`, `Same\\nsame`, exact empty segment removal, and ASCII trim;
- identifier/entity/technical phrases continuing without Gate classification.

The suite must kill removal of control validation, fuzzy comparison, lowercase/casefold, and
removal of exact-empty filtering. Record mutation-sensitive evidence; revert all temporary
mutants before committing.

## Gates and stop condition

Run:

```bash
uv lock --check
uv sync --locked --offline
uv run pytest -x -q tests/unit/test_task016c_quality_gate.py
uv run pytest -x -q
uv run mypy src
uv run ruff check .
git diff --check
```

Create exactly one commit:

```text
TASK-016C Phase B implement deterministic safety gate
```

Report branch/base/HEAD, exact paths, RED/GREEN and mutation evidence, all gate results,
tracked cleanliness, reuse decision, and `design deviations: NONE` or details. Then stop:
no merge, push, tag, or Phase C.
