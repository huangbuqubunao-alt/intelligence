# TASK-016 — Second Independent Review of Provider-Neutral Contract Correction R1

Status: **REQUEST CHANGES**

Date: 2026-08-29

## 1. Review scope and reviewed commit

Independent review-only closure and regression assessment of Correction R1. No
provider-neutral contract, implementation, credential, network, persistence/cache,
task-state, or TASK-016B/C document was modified. `.workbuddy/` was not inspected.

- Branch: `main`
- Reviewed commit: `6fe1a611c501aa6a7c3608bdac65bc6fb50b46cc`
- Original contract: `be5a78a5889b39ba32656332081313bd75818a1a`
- First review: `docs/TASK-016-DEEP-ANALYSIS-PROVIDER-NEUTRAL-CONTRACT-INDEPENDENT-REVIEW.md`
- Preflight: branch, exact HEAD, and clean worktree: PASS.

The R1 diff contains eight task-related documentation records only. It does not
modify source, tests, dependencies, configuration, the first review, or
TASK-016B/C materials.

## 2. Overall result

Correction R1 fully closes the original P0 and all eight original
implementation-critical P1 findings. DACS-1 and §4 bind A2 to the exact
provider-semantic request projection; §§3, 5--12 close payload, credential,
context, retry, response, validation/mint, cache, and qualification boundaries;
and §13 plus its cross-references supersede the prior Deep Analysis
fallback/retry conflict.

However, R1 introduces one implementation-critical fallback termination gap:
the permitted directed fallback graph is not required to be acyclic, bounded, or
non-reentrant. Implementation remains unauthorized pending R2.

## 3. Original-finding closure table

| Finding ID | Severity | Original issue | Correction location | Result | Residual severity |
| --- | --- | --- | --- | --- | --- |
| P0-1 | P0 | A2/cache omitted exact semantic request projection. | Amendment §§2, 4, 11; ADR-027. | CLOSED | None |
| P1-1 | P1 | Adapter could widen transcript payload. | Amendment §3. | CLOSED | None |
| P1-2 | P1 | Non-secret deployment/account identity absent. | Amendment §5, §11. | CLOSED | None |
| P1-3 | P1 | SDK retries neither mandatory to disable nor auditable. | Amendment §§8, 10, 12. | CLOSED | None |
| P1-4 | P1 | Consent/fallback admission ambiguous. | Amendment §7. | CLOSED | None; see R1-P1-1. |
| P1-5 | P1 | 016D lacked exact material for fresh revalidation. | Amendment §11. | CLOSED | None |
| P1-6 | P1 | Failure taxonomy lacked precedence/mapping. | Amendment §10. | CLOSED | None |
| P1-7 | P1 | Earlier retry/fallback rules conflicted. | Amendment §13; ADR-023; System Design §§11.2/12; ADR-027. | CLOSED | None |
| P1-8 | P1 | Qualification lacked immutable evidence/predicate. | Amendment §12. | CLOSED | None |
| P2-1 | P2 | Structured response identity ambiguous. | Amendment §9. | CLOSED | None |
| P2-2 | P2 | Declared capability could imply trust. | Amendment §§5, 12. | CLOSED | None |
| P2-3 | P2 | Local loopback scope needed explicit retention. | Amendment §13; ADR-023 notice. | CLOSED | None |

Original P0 closed: **YES (1/1)**.

Original implementation-critical P1 closed: **8/8**.

## 4. New findings introduced by R1

### R1-P1-1 — Directed fallback graph has no termination or non-reentry rule

**Severity: P1 — implementation-critical semantic ambiguity.**

Amendment §7 permits explicit directed edges and automatic advance after a
proven-no-send `PRE_DISPATCH/PROVIDER_UNAVAILABLE` (lines 239--258). It does
not require an acyclic graph, a maximum automatic advance count, or a
visited-profile/non-reentry rule.

For example, a matching pre-authorization can contain both `LOCAL-A ->
CLOUD_FREE-B` and `CLOUD_FREE-B -> LOCAL-A`. If both profiles fail their
pre-dispatch availability check, the contract permits repeated automatic
traversal forever. `whether new semantic attempts are allowed` is a Boolean,
not a finite bound or termination predicate.

This is not P0: only proven-no-send transitions are eligible, so this does not
repeat data egress or provider generation. It is P1 because implementation must
invent the core termination behavior (cycle rejection, a visited-profile rule,
or a finite bound), changing dispatch and attempt-history/provenance semantics.
R2 must choose and make one deterministic rule qualification-verifiable.

New P0: **0**.

New implementation-critical P1: **1**.

New P2: **0**.

## 5. Required closure checks

| Check | Result | Evidence |
| --- | --- | --- |
| A2 exact projection safe | YES | DACS-1 distinguishes omitted/null, ordering, Unicode, and numbers; §4 hashes final messages, payload, request shape, schema/tools, mode, generation semantics, and language. |
| Cache identity safe | YES | §11 binds A1/A2/A3/validation policy; observational fields are excluded; FLOATING is cross-run cache-ineligible. |
| Payload authority safe | YES | §3 application-constructs the closed allowlist and prohibits transcript object/repository/path/Vault/callback access by adapters. |
| Consent/scope safe | YES | §3 binds scope and consent identity into A2/A3/cache/provenance; FULL_TRANSCRIPT cannot collide with selected-only. |
| Cloud-mode semantics safe | YES | §7 specifies authority, provider, scope, credential profile, fallback, interaction, and headless outcome for all four modes. |
| Fallback safe | NO | Failure-class admission is closed, but R1-P1-1 leaves graph termination open. |
| Credential execution identity safe | YES | §5 binds a non-secret account/project/region/deployment/policy identity into A3 and excludes secrets/references/headers/derivatives. |
| Floating-model policy safe | YES | §5 marks FLOATING non-reproducible and disables cross-run cache even if a response echoes a revision. |
| Context authority safe | YES | §6 requires exact or documented bounded admission; unbounded framing/schema/tool overhead makes the profile ineligible. |
| SDK retry semantics safe | YES | §8 disables retries; the exception requires qualified idempotent deduplication, A3 binding, and every-send provenance. |
| Response identity safe | YES | §9 separately defines envelope, exact UTF-8 text, lossless decoded-object, and tool-argument identities. |
| Validation/mint safety | YES | §9 mandates early dispatch binding before parsing and final completeness before the sole application mint. |
| Failure precedence safe | YES | §10 gives first-applicable stage order and overlap outcomes. |
| 016D handoff sufficient | YES | §11 retains protected exact/recoverable revalidation material and full non-secret provenance/attempt evidence. |
| Supersession conflicts resolved | YES | §13, ADR-023, ADR-027, and System Design notices accurately scope supersession/retention. |
| Reference-provider qualification ready | YES | §12's 16 evidence gates cover identity, A2/A3, context, credentials, consent, retry, extraction, validation, provenance, cache, and privacy. |

## 6. Adversarial scenario matrix

| Scenario | Deterministic safe outcome | Result |
| --- | --- | --- |
| A. `local_only` + local unavailable | `PROVIDER_UNAVAILABLE`; zero cloud dispatch. | PASS |
| B. Pre-authorized free quota exhausted | `QUOTA_EXCEEDED`; STOP, no paid/local advance. | PASS |
| C. Schema-valid fabricated evidence | `GROUNDING_INVALID`; no mint/repair/fallback/cache write. | PASS |
| D. Floating model silently updated | Non-reproducible; cross-run cache disabled. | PASS |
| E. SDK hidden retry after timeout | Adapter ineligible; no dispatch. | PASS |
| F. Adapter has transcript under selected-only scope | Interface/qualification violation; no dispatch. | PASS |
| G. Cache provider/model X, current Y | A3/cache mismatch; miss. | PASS |
| H. Wrong `VerifiedScoringRead` request hash | Provenance failure; no mint. | PASS |
| I. Valid tool data with wrong provider/model | Early `PROVENANCE_INVALID`. | PASS |
| J. Credential profile switches deployment | A3/cache mismatch plus new eligibility/consent check. | PASS |
| K. Provider JSON Schema changes, prompt version unchanged | A2 changes; cache miss. | PASS |
| L. Validation policy version changes | Cache identity changes; cache miss. | PASS |
| M. Two authorized no-send edges form a cycle | No terminal outcome specified. | FAIL — R1-P1-1 |

## 7. Closed-scope confirmation

R1 changes no source, tests, migration, lockfile, or TASK-016B/C authorization
record. It preserves TASK-016B language validation, TASK-016C H1/H2, repair,
lineage, Phase G, and `AuthoritativeScoringReader` semantics. Scoring identity
remains exactly `VerifiedScoringRead.scoring_outcome.result.request_hash`;
`scoring_success_provenance` remains only `PRIMARY | REPAIR_H2C`. No
closed-scope P0 regression was found.

## 8. Implementation-readiness decision

**REQUEST CHANGES.**

Next step: **PROVIDER-NEUTRAL CONTRACT CORRECTION R2**, limited to deterministic
fallback-graph termination/non-reentry semantics and the corresponding
qualification/provenance evidence. Deep Analysis implementation remains
unauthorized. Do not start foundational contracts/domain types, provider
adapters, credentials, runtime dispatch, TASK-016D, TASK-016E, or TASK-016F
until R2 is accepted and independently re-reviewed.

TASK-016B remains closed. TASK-016C remains closed.
