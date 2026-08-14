# TASK-016C Phase A — WorkBuddy Implementer Authorization

## Role and fixed objects

You are the WorkBuddy Implementer for **TASK-016C Phase A: Domain Contracts and Candidate Boundary**.

- Implementation branch: `workbuddy/task-016c-content-quality-layer`
- Implementation base: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Accepted design authority: [ADR-025](../docs/decisions/ADR-025-content-quality-layer-scope-boundary.md), [Interface Design](../docs/TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md), [Test Plan](../docs/TASK-016C-CONTENT-QUALITY-TEST-PLAN.md), and [task card](../tasks/TASK-016C-content-quality-layer.md)

If the design, task card, or current code cannot be reconciled within this exact scope, stop and report `DECISION NEEDED`. Do not reinterpret the accepted design.

## Goal

Implement only the Phase A domain contracts required for later content-quality work. Establish an untrusted `ScoringCandidate`, content-quality input/result contracts, finite status/confidence/signal/reason matrix, evidence identity constraints, a QualityJudgeOperationInput skeleton, and trusted revalidation helpers.

## Exact allowed paths

- `src/youtube_intel/domain.py`
- `tests/unit/test_task016c_domain_contracts.py` (new)
- a minimal existing contract-test file only if needed to preserve current public behavior

Do not modify any other production file unless Codex issues a replacement authorization.

## Mandatory boundaries

- Preserve `ScoringCandidate.score: float` and `dimensions: ScoreDimensions | None`.
- Preserve every current `ScoreResult` public business field and do not modify TASK-016B Language Validator.
- Do not implement a deterministic Gate, Judge transport, H1/H2 identity, attestation, finalizer orchestration, write plan, filesystem persistence, Artifact persistence, cache recovery, repair orchestration, database behavior, or runtime composition.
- Do not add a dependency, edit `pyproject.toml`/`uv.lock`, add a migration/table/Artifact kind, or add brand/entity/product dictionaries, token heuristics, Cloud, Router, Weekly production, network, or external knowledge.
- Do not read, modify, stage, or commit `.workbuddy/`, `config/settings.yaml`, or `config/channels.yaml`.

## TDD requirements

Write failing tests first, then make the smallest domain-only GREEN change. Cover at minimum:

1. candidate `score=7.5` and optional `dimensions=None`;
2. business-field compatibility between candidate and existing `ScoreResult`;
3. valid and invalid ContentQualityResult status/reason/signal/confidence matrix;
4. PASS cross-field invariants;
5. REJECT and UNCERTAIN legal/illegal combinations;
6. duplicate signals/evidence identities and finite-number rejection including NaN/Infinity;
7. `model_copy(update=...)`, `model_construct(...)`, Mapping and JSON restore all crossing the trusted revalidation boundary;
8. no mutation or weakening of TASK-016B language checks.

## Verification and stop condition

Run focused tests, relevant existing contract regression, `uv run mypy src`, `uv run ruff check .`, and `git diff --check`. Record RED and GREEN evidence.

When Phase A is complete, commit only the authorized implementation/test paths, report branch, base, HEAD, exact diff scope, checks, tracked cleanliness, reuse decision, and `design deviations: NONE` or a list. Then stop. Do not merge, push, tag, create later-phase work, or start Phase B.
