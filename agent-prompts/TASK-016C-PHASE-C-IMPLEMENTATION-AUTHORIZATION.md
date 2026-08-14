# TASK-016C Phase C — Local Judge Contract and H1/H2 Authorization

## Status

`READY / AUTHORIZED FOR WORKBUDDY PHASE C ONLY`

## Fixed ancestry

- Accepted design baseline: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Accepted Phase A implementation: `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`
- Accepted Phase A evidence: `cbbe398e4d50a3c5b62f6d1bc20f83915f51aabc`
- Accepted Phase B execution head: `e942615cb852f7a1e6d7e06b11833076b1a4ade9`
- Execution branch: `workbuddy/task-016c-content-quality-layer`

The Phase C implementation commit must be the direct descendant of `e942615…`. It must
preserve the complete accepted design, Phase A, and Phase B history. Squash, rebase, history
rewrite, or dropping earlier phase commits is forbidden.

## Objective

Implement only the local Content Quality Judge contract and its two immutable identity layers:

```text
validated QualityJudgeOperationInput
  → canonical JSON / SHA-256
  → H1 judge_normalized_input_hash
  → existing build_provider_request_hash(...)
  → H2 judge_request_hash
```

Establish a fixed local Judge request/response contract using the existing loopback-only
Ollama boundary and trusted current local-scoring provider/model/digest configuration. This
phase does not orchestrate primary/repair scoring, reserve or persist ProviderCalls, construct
attestations or ScoreResults, or write files.

## Allowed files

- `src/youtube_intel/quality.py`
- `src/youtube_intel/domain.py` only for the minimum accepted Phase C contract types or trusted
  revalidation needed by the Judge boundary
- `src/youtube_intel/providers/ollama.py` only for a separately named local Quality Judge
  adapter using the existing constrained loopback transport
- `tests/unit/test_task016c_quality_judge_contract.py`
- `tests/integration/test_ollama_provider.py` only for focused fake-transport Judge-contract
  coverage

Any additional path requires `DECISION NEEDED` before modification.

## Frozen scope and rules

### H1 and H2

- H1 is the SHA-256 of canonical JSON for a fully validated
  `QualityJudgeOperationInput`.
- H1 includes scoring request hash, attempt role (`PRIMARY` or `REPAIR`), candidate hash,
  quality-input hash, policy/prompt/schema versions, and trusted Judge provider/model/digest.
- H2 must be derived only through the unchanged existing
  `build_provider_request_hash(...)` using:

  ```text
  operation = local-content-quality-v1
  normalized_input_hash = H1
  provider = trusted Judge provider
  model = trusted Judge model
  prompt_version = quality prompt version
  schema_version = quality schema version
  ```

- H1 and H2 must not be interchangeable and are expected to differ.
- Do not modify `build_provider_request_hash` or ADR-003’s six-dimensional request-hash
  semantics.

### Local Judge contract

- provider is fixed to the existing local Ollama boundary;
- model and digest are derived from trusted current local-scoring configuration;
- policy, prompt, and schema versions are fixed constants;
- request behavior is `temperature=0`, `stream=false`, `think=false`, and no tools;
- Judge response is a strict finite enum/mapping contract and can reference only pre-existing
  evidence IDs;
- unknown fields, invalid enum values, free diagnostics, registry-external evidence IDs,
  invalid JSON, decode/transport failure, model/digest mismatch, timeout, or response limits
  fail closed as `UNCERTAIN`.

No model download, pull, remote endpoint, user-selected remote model, cloud fallback, or
network fallback is permitted. Tests use fake loopback transport only; this authorization does
not authorize a real Ollama call.

## Forbidden scope

Do not modify:

- `scoring.py`, `state.py`, runtime composition, Artifact/cache/database/migrations;
- ProviderCall reservation, completion, persistence, or recovery;
- QualityPassAttestation, TrustedScoringFinalizer, canonical scoring artifact envelope,
  PREWRITE_VALIDATE, write plan, filesystem protocol, or DB registration;
- primary/repair orchestration and budget state machine;
- TASK-016B Language Validator, Cloud, Router, Weekly production, or Phase D–K.

Do not add a dependency, modify `pyproject.toml` or `uv.lock`, add dictionaries or semantic
heuristics, expose evidence excerpts/prompt/response content in logs, or access local user
configuration, `.workbuddy/`, `config/settings.yaml`, or `config/channels.yaml`.

## TDD requirements

Write RED tests before minimal implementation. At minimum cover:

1. canonical H1 stability across validated Mapping/JSON reconstruction;
2. every H1 input field changes H1, including PRIMARY versus REPAIR;
3. H2 equals the existing builder output and differs from H1;
4. H2 changes when any builder dimension changes;
5. malformed, unchecked `model_copy`, `model_construct`, Mapping, or JSON operation inputs
   cannot produce trusted H1/H2;
6. fixed local Judge request uses trusted provider/model/digest, fixed policy/prompt/schema,
   no tools, `temperature=0`, `stream=false`, and `think=false`;
7. loopback-only endpoint, no download/pull/fallback, and fake transport boundary;
8. strict response fields/enums and evidence-ID registry binding;
9. invalid response, invalid JSON/UTF-8, timeout, oversized response, and model/digest
   mismatch fail closed as `UNCERTAIN`;
10. no ProviderCall, Artifact, cache, ScoreResult, attestation, persistence, or filesystem
    side effect is created.

## Required gates

```bash
uv lock --check
uv sync --locked --offline
uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
uv run pytest -x -q tests/integration/test_ollama_provider.py
uv run pytest -x -q
uv run mypy src
uv run ruff check .
git diff --check
```

## Commit and rollback

Create exactly one Phase C implementation commit after all gates pass. The commit message must
be:

```text
TASK-016C Phase C implement local Judge contract and H1 H2 identity
```

The commit must be independently revertible with no migration, persisted data remediation,
Artifact cleanup, cache invalidation, or ProviderCall repair. Stop after reporting completion:
no merge, push, tag, Phase D, or real Ollama execution.
