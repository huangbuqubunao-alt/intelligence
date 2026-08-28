# TASK-016 — Focused Independent Review: Fallback Termination Correction R2

Status: **APPROVE**

Date: 2026-08-29

## 1. Scope and reviewed commit

This is a narrow, independent review of Correction R2's closure of the sole
remaining P1: fallback graph termination and cycle safety. It does not reopen
the already-approved provider-neutral architecture or TASK-016B/C semantics.

- Reviewed branch/commit: `main@fffbfe9cb87542347796e33076d9c3a4d33760c4`
- Original remaining P1: directed fallback graph cycles/re-entry lacked a
  deterministic pre-dispatch termination rule.
- Inputs reviewed: the second independent review, Correction R2's amendment,
  ADR-027, System Design §19, TASK-016 card, and TASK-016 handoff.
- Preflight: `main`, expected exact HEAD, clean worktree — **PASS**.
- Scope: `.workbuddy/` was not inspected. No implementation, contract, or
  closed-scope document was modified.

## 2. Focused findings and closure results

| Review area | Result | Evidence |
| --- | --- | --- |
| Cycle validation / DAG | PASS | §7.1 requires one finite DAG; §7.2 validates the entire effective plan before first dispatch, including self-, two-node, and longer cycles. Invalidity is `PRE_DISPATCH/INVALID_FALLBACK_POLICY` with zero dispatch. |
| Semantic node identity | PASS | `DeepAnalysisFallbackNodeIdentityV1` binds provider, model/revision policy, adapter, endpoint/deployment, credential execution profile, structured-output and generation profiles, context authority, qualification, and payload scope. |
| Duplicate semantic nodes | PASS | Two declared nodes with the same semantic identity are invalid even under different labels or paths. |
| Explicit start node | PASS | Exactly one `start_node_identity` is mandatory; auto/root/health selection and multiple roots are invalid. |
| Edge matching | PASS | Outgoing edges only; exact classified failure matching; pairwise-disjoint sets validated before dispatch; zero matches terminate and more than one is invalid/fail-closed. |
| Attempt bound / no revisit | PASS | A selected node may be attempted once only; a revisit is a fail-closed pre-dispatch invariant violation; semantic attempts are bounded by unique authorized nodes. |
| Failure-created permission | PASS | A failure creates no edge or expanded privacy, consent, credential, cloud, or payload authority. Only an explicit validated edge can advance. |
| Consent and privacy | PASS | Edge validation requires payload-scope, cloud-consent, and credential-profile authorization; missing per-run approval has zero destination dispatch. |
| Headless approval | PASS | An unavailable per-run approval terminates immediately as `AUTH_REQUIRED`; it may not wait, skip, select another edge, or dispatch. |
| Terminal states | PASS | `SUCCESS`, `TERMINAL_FAILURE`, `FALLBACK_PLAN_EXHAUSTED`, and `PRE_DISPATCH/INVALID_FALLBACK_POLICY` are distinct and deterministic. |
| Policy identity | PASS | The canonical policy identity binds start node, canonical semantic node set, canonical edges, failure-class sets, and edge scope/consent authorization data; defined sort order is independent of config-file order. |
| Provenance | PASS | Each selected semantic node records ordinal, node/provider/model/profile, trigger, edge/authorization, scope, consent, A1/A2/A3, every transport attempt, and result/failure. |
| Cache regression | PASS | Successful cache identity remains exact successful A1/A2/A3 plus validation policy and fresh revalidation. Fallback-policy/history remains audit evidence; consent/scope stay bound to successful A2/A3. |

## 3. Adversarial scenario matrix

| Case | Deterministic outcome | Result |
| --- | --- | --- |
| 1. `A -> A` | `PRE_DISPATCH/INVALID_FALLBACK_POLICY`; zero dispatch. | PASS |
| 2. `A -> B -> A` | `PRE_DISPATCH/INVALID_FALLBACK_POLICY`; zero dispatch. | PASS |
| 3. `A -> B -> C -> B` | `PRE_DISPATCH/INVALID_FALLBACK_POLICY`; zero dispatch. | PASS |
| 4. Distinct authorized `A -> B -> C` | Valid finite DAG; at most three semantic attempts. | PASS |
| 5. Two `A` edges match `TIMEOUT` | `PRE_DISPATCH/INVALID_FALLBACK_POLICY`; no preference or dispatch. | PASS |
| 6. `GROUNDING_INVALID`, no matching edge | `TERMINAL_FAILURE/GROUNDING_INVALID`. | PASS |
| 7. `TIMEOUT`, only `PROVIDER_UNAVAILABLE` edge | `TERMINAL_FAILURE/TIMEOUT`; no fallback. | PASS |
| 8. `B -> C` requires absent paid-cloud consent | Invalid policy before first dispatch; no `C` dispatch. | PASS |
| 9. Same target under two configuration aliases | Duplicate semantic node; pre-dispatch invalid. | PASS |
| 10. Required per-run approval in headless execution | Immediate `AUTH_REQUIRED` terminal result; no wait, skip, or dispatch. | PASS |
| 11. All authorized reachable nodes fail | `FALLBACK_PLAN_EXHAUSTED`; no additional attempt. | PASS |
| 12. Runtime would revisit an attempted node | `PRE_DISPATCH/INVALID_FALLBACK_POLICY`; no redispatch. | PASS |

## 4. Narrow regression and closed-scope result

Correction R2 preserves the directly adjacent approved constraints:

- A1/A2/A3 and validation-policy cache binding remain unchanged; the successful
  provider/model/profile and consent/scope remain part of the safe success
  identity.
- Payload authority, credential secrecy, untrusted provider output, and the
  sole `TrustedDeepAnalysisSuccess` mint boundary remain fail-closed.
- `VerifiedScoringRead.scoring_outcome.result.request_hash` remains the trusted
  scoring request identity. `scoring_success_provenance` remains only
  `PRIMARY | REPAIR_H2C`.
- The R2 commit changes no TASK-016B/C materials. It preserves scoring
  admission, repair, lineage, Phase G, and `AuthoritativeScoringReader`
  semantics.

## 5. Review decision

The original fallback termination P1 is fully closed. The complete policy is
validated before any dispatch; every valid policy is finite; dispatch is
deterministic, authorization-preserving, bounded, and provenance-visible.
There is no new implementation-critical ambiguity or cache/trust regression.

- New P0: **0**
- New implementation-critical P1: **0**
- Decision: **APPROVE**

The next gate is provider-neutral foundational contracts/domain types only.
This review does not authorize provider adapters, credentials, cloud activity,
or TASK-016D/E/F.
