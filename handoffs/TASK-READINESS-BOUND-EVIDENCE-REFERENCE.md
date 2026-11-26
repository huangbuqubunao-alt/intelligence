# TASK-READINESS-BOUND-EVIDENCE-REFERENCE — Implementer

- Date:2026-10-29; role `/root/cloud_preview_writer`; suggested IN_REVIEW, clean STOP after the commit containing this report.
- Base `ee3f82d1a77b066f8ae5956a2efa7f953d025eb9`; WT `/Users/developer/Documents/yia-worktrees/readiness-bound-evidence-reference`; branch `codex/task-readiness-bound-evidence-reference`.
- Exact assigned task/proposal plus Root's refinements: model never echoes a full input hash; stable chronological catalog; old terminal UNKNOWN Backup behavior preserved. No new real execution authorization.

## Result / reuse

DIRECT: accepted v2 grounding semantics, BigModel fixed HTTP/decoder/single-call lifecycle, pure request validation, original Evidence/claim parser and authority validator, existing immutable consent/claim/usage/Backup. DIRECT Python standard-library JSON/hash/dataclasses. No dependencies, imported third-party code or license change; no new runner/framework.

New `bound_evidence_reference.py` is a pure representation codec. Complete Evidence is sorted by trusted `(start_ms,end_ms,evidence_id)`; `E01` is earliest, refs remain stable under input permutation. Excerpts/Unicode and the complete set are retained. The existing20 maximum is enforced by `_canonical_reservation_evidence` and `_legal_evidence`; v3 preserves it, never slices to fit, and retains the existing128KiB complete request/2MiB response bounds.

The new fixed qualification-only profile is `bigmodel-glm-4.7-flash-thinking-json-bound-evidence-qualification-v3`, prompt `intelligence-grounding-bound-evidence-v3`, protocol marker `bound-evidence-reference-v1`. Instantiate `BigModelGlm47FlashBoundEvidenceDistillationTransport` explicitly; there is no UI/config/runtime selection addition. Endpoint/model/parameters/300s absolute deadline/zero retries reuse the original transport. Inherited normal eligibility remains False and default production spending policy remains denied.

Model-facing source rows are exactly `{ref,excerpt}`. All other source/task metadata and the entire accepted `_GROUNDING_V2_CONTRACT` remain. Only the three explicit representation passages of a fresh v2 message are replaced; the frozen old builders/classes are unchanged. Positive output has the original seven fields plus fixed `reference_protocol`; each citation is exactly `{ref,stance}`. NO_NEW has exactly protocol/result/evidence and every supplied `{ref}` once. Old IDs/times, extra keys, duplicate keys/refs, wrong types, unknown refs/protocol, malformed/nonfinite/deep/oversized JSON and incomplete NO_NEW are rejected. Claim strings/arrays/numbers/claim_kind/stance are never repaired, trimmed, reclassified or strengthened.

`_BoundEvidenceVerifiedDistillationInput` is a new exact frozen subclass carrying only its explicit profile marker. Legacy base/v2 classes and raw asdict/projection remain unchanged; typed nested Evidence is retained. Profile projection → semantic hash → reservation ID → existing immutable consent remain bound, with fixed tuple/type/profile checks before credentials.

The backend adapter calculates `request_origin_hash = SHA256(full verified input projection)` locally for the actual request. The model does not receive or echo this hash. `_BoundEvidenceTransportResult` separately retains **original public raw**, `normalized_raw` and `request_origin_hash`; base result fields remain exact. Alias names are request-local, not globally unique or cryptographic authority. The fixed marker grants no permission or semantic correctness.

For v3 only, service dispatch requires the exact new result carrier, verifies origin against its current verified input, independently re-runs normalization and compares the derived representation, then calls the **unchanged original `_parse_candidate`** and original persistence authority. Cross-input/result mixes, changed normalization and attempted old-protocol raw are rejected. Conditional/contradicting stances remain unchanged; lack of supporting Evidence still fails the old validator. Old v2 synthetic wrong-location raw still rejects. Old actual failures/raw/cases were neither accessed nor modified.

`cloud_wait_cancellation.py` adds only the explicit v3 prompt/profile pair to the existing finite reservation reconstruction. New missing-key and known TLS-before-POST WAIT0 retain reliable cancellation/restart/Backup semantics. No SQL/state/ledger/consent/budget/restore-rule change. Existing terminal UNKNOWN remains inv1, uncancellable and nonreplayable, and may be backed up under its already accepted finite terminal accounting rules.

## Checks / preserved failures

Python commands all explicitly used `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-bound-evidence-reference/src`, and `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`. Local ignored evidence is `.var/bound-evidence-reference/`.

| Evidence | Result |
|---|---|
| Initial reference/NO_NEW RED → GREEN |2 missing-codec failures (`red.log`), then2 PASS (`first-green.log`) |
| Complete precise11-file affected group |**430 PASS,6 FAIL /167.79s**, `affected.log`; every failure is an existing latest42 expectation after the accepted43 baseline |
| Necessary old-version assertion repair + final two compatibility tests |**8 PASS /8.05s**, `incremental.log`: all6 failed cases + independent v2 bytes golden + legacy v2 wrong-location rejection |
| Original NO_NEW/zero-result subset |11 PASS /6.21s, `no-new.log` |
| Final JSON boundary delta |5 PASS, `parser-boundary.log`: duplicate/nonfinite/malformed/deep/oversized; catches excessive nesting as a bounded invalid representation |
| Strict mypy |125 source files PASS, `type-final.log` |
| Compile / Ruff / diff |125 source files + changed tests in-memory compile; changed source/tests Ruff and `git diff --check` PASS |
| Independent old-source proof |`protected.log`/`protected.json`:42 SQL files001–043 byte identical,80 old top-level definitions +44 unaffected service methods byte identical, old parser byte identical; old-path compose/dispatch AST identical after removing only the new version branch |
| Legacy request compatibility |Pure synthetic old fixed source loaded independently: v1/v2 base/asdict/profile/request bytes equal current; committed v2 golden protects the independent baseline |

Complete affected group (no full629/6000/frontend repetition):

```text
tests/unit/test_bound_evidence_reference.py
tests/unit/test_grounded_cloud_prompt_v2.py
tests/unit/test_bigmodel_distillation_adapter.py
tests/integration/test_bigmodel_distillation_transport.py
tests/unit/test_bigmodel_claims.py
tests/unit/test_cloud_wait_zero_cancel.py
tests/integration/test_local_text_input_proof.py
tests/unit/test_local_grounding_harness.py
tests/unit/test_long_grounding_projection.py
tests/unit/test_summary_evidence_candidates.py
tests/integration/test_summary_evidence_authority.py
```

The affected run contains the complete new codec/service tests then present: chronological mapping, complete1/20 sets, cross-origin, schema/types/overflow/extra keys, source denial, old-profile refusal, exact raw/normalized distinction, independent service recomputation, consent/normal budget closure, success/NO_NEW/rejected/timeout/202 once accounting, full ZIP restore and both WAIT0 cancel/restart/restore paths. Two compatibility tests and one deep-JSON case were added afterward and run in the listed narrow deltas; no new fake model framework. All inputs are synthetic or existing synthetic test factories, no real case text/oracle.

Root explicitly accepted changing **only two** latest-version expectations in `test_local_text_input_proof.py` from42→43. Legacy34–38 values, rollback-to38, every old row, DATA, and all original assertions remain. State/migrations were already43 and byte identical to base; these6 failures are baseline assertion drift, not codec regressions. Original failure evidence is preserved; no skipped/disabled test or weakened authority assertion.

Development mistakes retained in logs: early Ruff removed imports not yet used by appended tests (restored imports); first focused lifecycle test incorrectly expected terminal UNKNOWN to block Backup (corrected to the existing documented finite terminal behavior, stronger UNKNOWN/once/cancel + ZIP restore assertions). No product/state change for either.

## Frozen compatibility identifiers / limits

- v3 profile projection SHA256 `06af7d8ff198575b1586d20cd2b4055de98e72907c13203e1235e454fbbb7d36`.
- Representation contract SHA256 `980a5ce292a61011e753ffbc115ac2def66a6c5e57e99b195e2c85b7d1fb4d22`.
- Independent unchanged v2 request SHA256 `462e6ed87d6e0b248df2c835ef98812a9fac0a6062bc41424eaf1023d2e16d87`; profile `d0819b95c5f5ca6f4c06d669b14e8e2c3e962ee28ed70164e47841dbf2470316`; raw asdict `da547a316dfd3af6634ddbe23f9cc339f66a513a14f4be777593af93028f27d2`.
- Scripts, committed fixtures/oracles, frontend, state.py and runtime_composition.py unchanged. No Schema/deps/toolchain/config/native/key/network/model/liveQA/actual-package/main access/change.
- No real model qualification, account entitlement, billing or semantic quality claim. A valid new representation is only a format/provenance prerequisite; retained judgment still requires independent quality acceptance. Root alone decides a separately frozen unseen public case and at most one real request after targeted source/package review. This task adds no execution capsule or real-call permission.
