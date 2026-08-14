# TASK-016C Phase D Implementation Authorization

**Status:** READY / AUTHORIZED
**Task:** TASK-016C Phase D — Quality PASS Attestation and Canonical Hashing
**Role:** WorkBuddy Implementer
**Authority type:** Control-plane only. This document does not start implementation.

## Accepted Baselines and Ancestry

| Authority | Commit |
| --- | --- |
| Accepted TASK-016C design | `c547b7c46afbf254979331c2c56cddb93a8503f2` |
| Accepted Phase A | `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3` |
| Accepted Phase B | `e942615cb852f7a1e6d7e06b11833076b1a4ade9` |
| Accepted Phase C | `1743b00a7258890f8dd7e80ea056eab3eb4ce8f2` |

The Phase D implementation commit must be a descendant of the synchronized control-plane commit and of Phase C `1743b00a7258890f8dd7e80ea056eab3eb4ce8f2`. Do not squash, rebase, reset, or rewrite Phase A–C history.

## Objective

Implement a pure, in-memory application-created `quality-pass-attestation-v1` and canonical `quality_result_hash` for a validated quality `PASS`. Phase D performs no judge transport, scoring finalization, persistence, cache recovery, or runtime migration.

## Allowed Files

Expected minimum implementation scope:

- `src/youtube_intel/domain.py`
- `src/youtube_intel/quality.py`
- `tests/unit/test_task016c_quality_attestation.py`

Minimal additions are allowed only in these existing contract tests when required:

- `tests/unit/test_task016c_domain_contracts.py`
- `tests/unit/test_task016c_quality_judge_contract.py`

Any other path requires a decision request. No dependency or lockfile changes are authorized.

## Frozen PASS Contract

### Untrusted reconstruction

All candidate, quality-input, quality-result, and purported-attestation Mapping, JSON, instance, subclass, serializer, provider, model, cache, or caller data is untrusted. Reconstruct and fully revalidate before use; do not trust type, flags, overridden properties, `model_copy`, `model_construct`, or overridden `model_dump`.

Only a fully valid `ContentQualityResult(PASS)` can be attested. Its Evidence IDs must be non-empty and resolve in the supplied registry. Empty registries, unknown IDs, malformed PASS objects, and every non-PASS result fail closed.

### Canonical `quality_result_hash`

Normalize signals by enum value (sort/deduplicate) and Evidence IDs by stable ID (sort/deduplicate), then revalidate the complete `ContentQualityResult`. SHA-256 its entire canonical JSON form using the existing encoding: UTF-8, `ensure_ascii=False`, sorted keys, separators `(",", ":")`.

No unchecked serialization, caller-supplied hash, or reduced PASS-field subset is allowed. Every frozen canonical field must change the hash or cause validation failure.

### In-memory attestation

The application constructs, and only verifies, schema `quality-pass-attestation-v1` with:

- `status=PASS`, `candidate_hash`, `quality_input_hash`, `quality_result_hash`, `scoring_request_hash`
- quality policy/schema/prompt versions and scoring schema/prompt versions
- judge provider/model/model digest/operation/request hash and attempt role
- `decision_confidence=HIGH`, `grounding_confidence`, `usefulness_confidence`, and Evidence IDs
- canonical `attestation_hash`, SHA-256 over the complete payload excluding itself

The attestation mirrors confidence values and Evidence IDs from the validated quality result exactly. Any candidate/input/request/policy/prompt/schema/provider/model/digest/H2/attempt/confidence/Evidence-ID/hash mismatch fails closed.

H1 remains the canonical validated `QualityJudgeOperationInput` hash. H2 remains the unchanged `build_provider_request_hash` result for `local-content-quality-v1` using H1, provider, model, prompt version, and schema version. H1 and H2 are distinct and neither builder may change.

## Forbidden Scope

Do not modify or invoke `providers/ollama.py`, `scoring.py` orchestration, runtime composition, TASK-016B language validation, `state.py`, database, migrations, ProviderCall, artifacts, cache recovery, filesystem protocol, `TrustedScoringFinalizer`, trusted `ScoreResult` construction, response IDs, primary/repair orchestration, judge budget state, or Phase E–K.

Do not add dependencies, alter `pyproject.toml` or `uv.lock`, use network/cloud/Ollama/credentials, or add dictionaries, brands, entity lists, or NLP heuristics. Phase D must create no file, database, cache, ProviderCall, Artifact, response-ID, ScoreResult, or provider-success side effect.

## TDD and Adversarial Requirements

Write RED tests before the minimum GREEN implementation. Tests must prove:

1. Valid PASS hashing and attestation are deterministic.
2. Equivalent Mapping and JSON inputs yield identical canonical results.
3. Every mutable canonical field changes the hash or fails validation.
4. Malformed, non-PASS, evidence-free, and registry-external results fail closed.
5. `model_copy`, `model_construct`, fake trusted flags, subclasses/properties/serializers, and provider/model-originated fake attestations cannot bypass reconstruction.
6. Every frozen identity/version/judge/H2/attempt/confidence/Evidence binding mismatch fails closed.
7. Unknown fields and forged hashes fail closed.
8. No ScoreResult, Artifact, cache, ProviderCall, response ID, filesystem, or database side effect occurs.

Include mutation-quality evidence that deleting binding, hashing unchecked objects, altering a bound field without hash change, accepting malformed PASS, or accepting evidence-free PASS would fail tests.

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

No download, network, real Ollama, or cloud fallback is permitted.

## Commit, Rollback, and Handoff

After all gates pass, create exactly one independently revertible implementation commit:

```text
TASK-016C Phase D implement PASS attestation and canonical hashing
```

Append evidence to `handoffs/TASK-016C.md`: RED/GREEN results, commands, SHA and parent, exact paths, adversarial coverage, no-side-effect confirmation, reuse decision, skipped work, and risks. Then stop for independent review; do not merge.
