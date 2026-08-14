# TASK-016C Phase D Handoff Checklist

**Status:** READY / AUTHORIZED
**Review target:** One future implementation commit descended from the synchronized Phase D authorization and Phase C `1743b00a7258890f8dd7e80ea056eab3eb4ce8f2`.

## Implementer Completion Record

- [ ] Confirmed accepted design `c547b7c46afbf254979331c2c56cddb93a8503f2`, Phase A `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`, Phase B `e942615cb852f7a1e6d7e06b11833076b1a4ade9`, and Phase C `1743b00a7258890f8dd7e80ea056eab3eb4ce8f2` ancestry.
- [ ] Recorded one implementation commit and its sole parent; no squash, rebase, or history rewrite.
- [ ] Changed only authorized Phase D paths.
- [ ] Implemented application-created, in-memory `quality-pass-attestation-v1` only.
- [ ] Reconstructed and revalidated every untrusted Mapping, JSON, and object input before hashing or attesting.
- [ ] Verified full canonical `quality_result_hash`: normalized signal/Evidence ordering, complete canonical JSON, and SHA-256.
- [ ] Verified attestation hash excludes only itself and binds candidate/input/request/version/provider/model/digest/H2/attempt/confidence/Evidence identity.
- [ ] Confirmed PASS has non-empty valid registry-backed Evidence IDs; malformed/non-PASS/evidence-free/external-evidence results fail closed.
- [ ] Confirmed no ScoreResult, Artifact, cache, ProviderCall, response ID, filesystem, or database side effect.
- [ ] Recorded TDD RED then GREEN evidence and mutation-quality coverage.

## Mandatory Gate Evidence

- [ ] `uv lock --check`
- [ ] `uv sync --locked --offline`
- [ ] `uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`
- [ ] `uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`
- [ ] `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`
- [ ] `uv run pytest -x -q`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `git diff --check`

## Independent Reviewer Acceptance Matrix

The independent reviewer must demonstrate:

- [ ] Mapping, JSON, instance, subclass/property/serializer, `model_copy`, `model_construct`, and fake trusted-flag inputs cannot bypass reconstruction.
- [ ] Canonical result hashing is deterministic; all relevant fields are hash-bound or invalid.
- [ ] Attestation verifies exact candidate/input/request/version/provider/model/digest/H2/attempt/confidence/Evidence identity and fails closed on each mismatch.
- [ ] H1 and H2 remain distinct; the existing request-hash builder is unchanged.
- [ ] PASS cannot be attested without valid evidence registry references.
- [ ] Unknown fields and forged attestation hashes are rejected.
- [ ] No change starts a judge, network call, persistence protocol, cache recovery, ProviderCall, Finalizer, ScoreResult construction, or Phase E+ work.
- [ ] Diff scope, dependency/lockfile exclusion, and `git diff --check` pass.

## Required Handoff Content

The implementation handoff must state the commit SHA and parent, exact file list, RED/GREEN evidence, full-gate outcomes, adversarial and mutation cases, no-side-effect proof, reuse decision, skipped forbidden work, and remaining risks. A review verdict records only APPROVE or REJECT; it grants no merge authority.
