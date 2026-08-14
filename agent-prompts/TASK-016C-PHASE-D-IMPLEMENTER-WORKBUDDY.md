# TASK-016C Phase D — WorkBuddy Implementer Prompt

## Role and Stop Boundary

You are the WorkBuddy Implementer for **TASK-016C Phase D — Quality PASS Attestation and Canonical Hashing**. Implement only Phase D, create exactly one implementation commit, and stop for independent review. Do not merge, push, tag, rebase, squash, reset, rewrite history, or start later phases.

## Fixed Authorities

Read, before editing:

1. `docs/COLLABORATION.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. `docs/REUSE_REGISTER.md`
6. `tasks/TASK-016C-content-quality-layer.md`
7. `docs/decisions/ADR-025-content-quality-layer-scope-boundary.md`
8. `docs/TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md`
9. `docs/TASK-016C-CONTENT-QUALITY-TEST-PLAN.md`
10. `docs/TASK-016C-IMPLEMENTATION-MASTER-PLAN.md`
11. `handoffs/TASK-016C.md`
12. `agent-prompts/TASK-016C-PHASE-D-IMPLEMENTATION-AUTHORIZATION.md`

Accepted history: design `c547b7c46afbf254979331c2c56cddb93a8503f2`; Phase A `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`; Phase B `e942615cb852f7a1e6d7e06b11833076b1a4ade9`; Phase C `1743b00a7258890f8dd7e80ea056eab3eb4ce8f2`.

Before coding, verify your branch contains the synchronized Phase D authorization commit and is a descendant of Phase C `1743b00a7258890f8dd7e80ea056eab3eb4ce8f2`. Stop and report if false. Do not squash, rebase, or rewrite Phase A–C history.

## Objective

Implement the pure in-memory application contract for a quality `PASS`: reconstruct and hash a complete `ContentQualityResult`; construct and verify `quality-pass-attestation-v1`; bind it to candidate, quality-input, request, version, judge, and attempt identities; and fail closed on any malformed or mismatched value.

Do not run a judge, finalise scoring, persist data, create a cache item, or construct a trusted `ScoreResult`.

## Allowed Paths

Use the smallest change set from:

- `src/youtube_intel/domain.py`
- `src/youtube_intel/quality.py`
- `tests/unit/test_task016c_quality_attestation.py`
- `tests/unit/test_task016c_domain_contracts.py`
- `tests/unit/test_task016c_quality_judge_contract.py`
- `handoffs/TASK-016C.md`

The first three paths are expected. Existing contract tests may be minimally changed only when necessary. Stop for a decision before changing any other path. Do not change dependencies or lockfiles.

## Frozen Contract

### Untrusted reconstruction

Treat every candidate, quality input, quality result, and alleged attestation from Mapping, JSON, object instance, subclass, provider, model, cache, or caller as untrusted. Reconstruct and fully revalidate using the frozen Pydantic contracts before deciding. Never trust object type, trusted flag, overridden property, overridden serializer, `model_copy`, or `model_construct`.

Only fully valid `ContentQualityResult(PASS)` is eligible. A PASS must have at least one Evidence ID resolving in the supplied evidence registry. Empty registry, external Evidence IDs, malformed PASS, and all non-PASS values fail closed.

### Canonical result hash

Normalize signals by enum value and Evidence IDs by stable ID, sorted and deduplicated. Revalidate the whole result. `quality_result_hash` is SHA-256 of the complete canonical JSON result: UTF-8, `ensure_ascii=False`, sorted keys, and separators `(",", ":")`.

Do not hash unchecked input, a reduced PASS subset, or caller-provided serialization. Every frozen canonical field must change the hash or make validation fail.

### PASS attestation

The application, never a provider/model/cache/artifact, creates `quality-pass-attestation-v1`. It binds PASS status; candidate/input/result/request hashes; quality policy/schema/prompt versions; scoring schema/prompt versions; judge provider/model/digest/operation/request hash; attempt role; confidence values; Evidence IDs; and an `attestation_hash` over the complete canonical payload excluding only itself.

`decision_confidence` must be HIGH; grounding and usefulness confidence must be MEDIUM or HIGH. Attestation confidence values and Evidence IDs must mirror the validated quality result exactly. Any candidate/input/request/policy/prompt/schema/provider/model/digest/H2/attempt/confidence/Evidence-ID/hash mismatch fails closed.

### H1/H2 integrity

Do not alter current builders. H1 is the canonical validated `QualityJudgeOperationInput` hash. H2 is `build_provider_request_hash` for `local-content-quality-v1`, normalized input H1, provider, model, prompt version, and schema version. H1 and H2 are distinct. Bind and verify H2 without reimplementing either builder.

## Forbidden Work

Do not modify, call, or simulate:

- `providers/ollama.py`, `scoring.py` orchestration, runtime composition, or TASK-016B language validation;
- `state.py`, database, migrations, ProviderCall, cache recovery, artifacts, prewrite plans, temporary files, fsync, or rename/promote;
- `TrustedScoringFinalizer`, trusted ScoreResult construction, response artifact IDs, primary/repair orchestration, judge budget/recovery state, or Phase E–K;
- H1/H2 algorithms, dependencies, `pyproject.toml`, `uv.lock`, dictionaries, entity lists, or NLP heuristics;
- network, cloud, real Ollama, credentials, or fallback services.

Phase D is entirely in memory: it creates no filesystem, database, Artifact, cache, ProviderCall, response-ID, ScoreResult, or provider-success side effect.

## Required TDD Evidence

Write tests first and record their RED result; then implement the minimum GREEN change. Tests must demonstrate:

- deterministic valid-PASS result and attestation hashes;
- equivalent Mapping and JSON inputs produce identical canonical results;
- every canonical result/attestation binding field is hash-bound or rejected;
- malformed, non-PASS, evidence-free, and registry-external results reject;
- `model_copy`, `model_construct`, fake trusted flags, subclasses/properties/serializers, and provider/model-originated forged attestations cannot bypass;
- candidate/input/request/policy/prompt/schema/provider/model/digest/H2/attempt/confidence/Evidence-ID mismatches reject;
- unknown fields and forged hashes reject; and
- no ScoreResult, Artifact, cache, ProviderCall, response ID, filesystem, or database side effect occurs.

Include mutation-quality proof that tests fail if binding is removed, unchecked input is hashed, a bound field changes without affecting its hash, malformed PASS is accepted, or evidence-free PASS is accepted.

## Required Gates

```text
uv lock --check
uv sync --locked --offline
uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
uv run pytest -x -q
uv run mypy src
uv run ruff check .
git diff --check
```

Run no network/download, real Ollama, or cloud fallback. Review the final diff for permitted paths only and no persistence, runtime, dependency, or later-phase work.

## Commit, Handoff, and Stop

After all gates pass, create exactly one independently revertible commit:

```text
TASK-016C Phase D implement PASS attestation and canonical hashing
```

Append to `handoffs/TASK-016C.md`: parent and commit SHA, changed paths, RED/GREEN proof, gate outcomes, adversarial/mutation coverage, no-side-effect proof, reuse decision, skipped work, and risks. Stop after that commit. Do not merge, start review yourself, begin Phase E, or add persistence/runtime work.
