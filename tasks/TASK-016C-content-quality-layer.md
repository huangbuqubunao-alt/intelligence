# TASK-016C — Content Quality Layer

## Status

`IN_PROGRESS / WorkBuddy Phase A only`

## Accepted design baseline

- Design SHA: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Decision: [ADR-025](../docs/decisions/ADR-025-content-quality-layer-scope-boundary.md)
- Interface: [TASK-016C Content Quality Interface Design](../docs/TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md)
- Test plan: [TASK-016C Content Quality Test Plan](../docs/TASK-016C-CONTENT-QUALITY-TEST-PLAN.md)
- Master plan: [TASK-016C Implementation Master Plan](../docs/TASK-016C-IMPLEMENTATION-MASTER-PLAN.md)

The baseline is frozen. This task does not authorize any semantic change to those documents.

## Current assignment: Phase A — Domain Contracts and Candidate Boundary

### Goal

Create the trusted domain types and invariants required by later TASK-016C phases while preserving TASK-016B and the public business shape of `ScoreResult`.

### Allowed production path

- `src/youtube_intel/domain.py`

### Allowed test paths

- `tests/unit/test_task016c_domain_contracts.py` (new)
- a minimal existing contract-test adjustment only when required to preserve a current public contract

### Explicitly out of scope

- Deterministic Gate logic;
- Ollama Quality Judge transport, H1/H2 persistence, attestation, finalizer, write plan, filesystem protocol, Artifact persistence, cache recovery, or repair orchestration;
- `scoring.py`, `providers/ollama.py`, `state.py`, `runtime.py`, database schema, migrations, dependencies, lockfile, Cloud, Router, Weekly production, and TASK-016B Language Validator.

### Required Phase A types and checks

- `ScoringCandidate` preserving `score: float`, `dimensions: ScoreDimensions | None`, and every existing scoring business field;
- Content Quality input/result, finite confidence/status/signal/reason matrix, evidence identity registry, QualityJudgeOperationInput skeleton, and trusted revalidation helpers;
- tests-first RED/GREEN coverage for valid and invalid matrices, duplicate identities/signals, NaN/Infinity, unchecked Pydantic copy/construct, Mapping/JSON restore, and candidate/business compatibility.

### Completion gate

WorkBuddy must report branch, base, HEAD, exact paths, RED evidence, focused and relevant regression results, mypy, Ruff, `git diff --check`, tracked worktree status, and `design deviations: NONE` or a list. WorkBuddy must then stop: no merge, push, tag, or Phase B.

### Reuse decision

`ADAPT`: existing Pydantic domain contracts and TASK-016B trusted-revalidation approach. No new dependency or data-store construct is authorized.
