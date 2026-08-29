# TASK-016 — Foundational Contracts Independent Code Review

Status: **REQUEST CHANGES**

Date: 2026-08-29

## Review scope and evidence

- Reviewed branch/HEAD: `main@a3bb6f1df1a7ee6c565a3bf0e41a10b677ca78e9` (clean at preflight).
- Reviewed implementation commits:
  `5f320988a701bc2294b02010ba2967432ffdf2c7` and
  `a3bb6f1df1a7ee6c565a3bf0e41a10b677ca78e9`.
- Primary implementation reviewed:
  `src/youtube_intel/deep_analysis_contracts.py` and
  `tests/unit/test_deep_analysis_contracts.py`.
- Contract sources reviewed: the accepted amendment Correction R2, ADR-027,
  both prior independent reviews, the focused fallback review, System Design,
  TASK-016 card, and TASK-016 handoff. `.workbuddy/` was not inspected.
- Scope containment: **PASS**. The implementation diff adds only pure domain
  contracts/tests and task evidence; no adapter, HTTP/network client, provider
  dispatch, credential loading/storage, persistence/cache backend, or
  TASK-016D/E/F code was found. TASK-016B/C code was not changed.

## Decision

**REQUEST CHANGES.**

P0: **4**

P1: **2**

P2: **0**

The strongest finding is P0-1: an ordinary caller can construct an object that
is indistinguishable as a `TrustedDeepAnalysisSuccess` from a finalizer-minted
value, bypassing the advertised sole-mint trust boundary.

## Blocking findings

### P0-1 — `TrustedDeepAnalysisSuccess` is publicly forgeable

`TrustedDeepAnalysisSuccess` is publicly exported and its sentinel protects
only `__init__` ([deep_analysis_contracts.py](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:867)). An ordinary caller can call
`object.__new__(TrustedDeepAnalysisSuccess)` and use `object.__setattr__` to set
`_content_identity`, `_cache_identity`, and `_sealed`. The resulting object
returns the supplied identities and cannot be distinguished by this type from
a finalizer-minted value. The current `__setattr__` guard itself delegates to
`object.__setattr__` ([line 889](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:889)).

This directly violates amendment §9's sole application validator/finalizer
mint requirement and the review gate's anti-forgery criterion. The focused test
checks only a direct constructor with the wrong sentinel; it does not test this
working construction path.

Required correction: define an actual mint-verification boundary for consumers,
not merely a constructor guard. A value accepted as trusted must carry an
unforgeable-by-normal-caller finalizer admission capability or be verified
against finalizer-owned state; add adversarial coverage for `object.__new__`,
`object.__setattr__`, constructor, copy/pickle, and serialization paths.

### P0-2 — A1's supposedly authoritative scoring ingress can be forged

`CanonicalDeepAnalysisInputV1` claims construction only from the authoritative
scoring read, but it accepts any publicly constructible `VerifiedScoringRead`
whose exact runtime type matches ([lines 346–378](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:346)).
`VerifiedScoringRead` is a public frozen dataclass with a public constructor;
the focused test fixture itself directly constructs it. Further,
`CanonicalDeepAnalysisInputV1.model_construct(...)` is inherited and skips the
pre-validator entirely, allowing an arbitrary `scoring_request_hash` (including
`"PRIMARY"`) to produce an A1 hash.

The isolated review construction accepted both a manually constructed
`VerifiedScoringRead` carrying `f...f` as the request hash and an unchecked
`model_construct` input carrying `"PRIMARY"`. Thus the code correctly avoids
substituting provenance in the normal factory, but it does not enforce the
contract's required trusted ownership of
`VerifiedScoringRead.scoring_outcome.result.request_hash`.

Required correction: make the A1 admission path verify reader/finalizer-owned
authority rather than only nominal type, disable or contain unchecked
`model_construct`, and revalidate at the identity-consumption boundary. Add
tests for manually constructed `VerifiedScoringRead`, `model_construct`, copy
/ update, and provenance-as-hash injection.

### P0-3 — Credential execution identity can contain and expose secret material

`CredentialExecutionProfileIdentityV1` stores raw arbitrary strings in
`project_identity`, `organization_identity`, endpoint, and policy fields
([lines 236–249](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:236)). It rejects an *extra* field named `api_key`,
but it accepts `project_identity="sk-live-super-secret"`; that value is retained
by the model and shown by `repr`/`model_dump`.

This contradicts the amendment's opaque non-secret identity requirement and
allows a credential to enter a serializable/loggable contract through normal
intended API fields. Hashing it in `.identity` does not repair retention by the
object itself.

Required correction: make this contract carry only structurally non-secret,
opaque execution identities generated at a trusted configuration boundary; do
not retain raw project/organization/policy values in the contract. Add tests
for secret-shaped values in every generic string field and for repr/dump error
redaction.

### P0-4 — Consent and fallback authorization fields can contradict their targets

`DeepAnalysisDispatchEnvelopeV1` checks A1/A2 and payload scope, but does not
bind `payload_consent.named_provider_id`/`provider_kind` to the execution
profile's actual provider ([lines 753–782](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:753)). A locally authorized
consent for `provider-a` and an otherwise valid execution profile for
`provider-b` are accepted together.

Likewise `DeepAnalysisFallbackPolicyV1` validates graph topology but never
compares an edge's declared source/destination scopes or destination credential
identity with its referenced nodes ([lines 563–588](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:563)). A policy accepted an edge that
declared `SELECTED_EVIDENCE_ONLY` for a destination node whose semantic identity
specified `FULL_TRANSCRIPT`.

These contradictions can authorize data egress to a different provider or
under a narrower scope/credential identity than the one that would execute;
they are privacy/trust boundary failures, not mere cache fragmentation.

Required correction: derive duplicated authorization fields from one source or
reject every mismatch. At minimum bind envelope consent provider/kind/model and
context/prompt/schema identities to the selected execution/request objects;
bind each fallback edge's source/destination scopes and destination credential
identity to the referenced nodes. Add negative tests for every mismatched pair.

### P1-1 — Structured-output mode invariants are incomplete

`DeepAnalysisStructuredOutputV1` rejects schema/tools only for
`RAW_JSON_PROMPT` and requires tools only for
`TOOL_STRUCTURED_RETURN` ([lines 414–420](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:414)). It accepts a
`PROVIDER_JSON_SCHEMA` request with `schema=None`, and permits incompatible
schema/tool fields in the other modes. It also does not enforce the required
single user-message shape for `RAW_JSON_PROMPT`.

The values that are supplied still hash into A2, but invalid/mode-contradictory
provider-semantic projections are admitted. The next dispatch implementation
would have to invent mode semantics instead of relying on the foundational
contract.

Required correction: encode and validate the exact per-mode shape required by
amendment §4.1 (including raw role/message rules, schema presence for JSON
Schema mode, tool declarations and choice semantics for tool mode, and null
versus omitted fields). Add a negative/positive matrix for all four modes.

### P1-2 — Failure taxonomy cannot represent one normative pre-dispatch leaf

The contract requires invalid/empty/ambiguous provider selection to terminate
as `PRE_DISPATCH/PROVIDER_UNAVAILABLE`, but the frozen mapping forces
`PROVIDER_UNAVAILABLE` to `PROVIDER_MODEL`
([lines 111–152](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:111)). `DeepAnalysisFailureV1` rejects
the normative pre-dispatch combination ([lines 479–488](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:479)).

Required correction: make the code/stage taxonomy faithfully represent the
normative leaf and precedence, or adopt an approved distinct pre-dispatch leaf
without changing the contract's observable semantics. Add precedence and
stage/leaf matrix tests.

## Non-blocking areas that passed review

| Review area | Result | Evidence |
| --- | --- | --- |
| DACS-1 | PASS | Uses the existing RFC-8785 serializer; preserves UTF-8, key ordering, arrays, null/omitted distinction, numeric rejection, and no text normalization. Mutation/golden tests and isolated prompt/schema checks changed identities as required. |
| A1 normal-path scoring field selection | PASS with P0-2 exception | The normal factory derives `result.request_hash`, never provenance; mismatched caller-supplied values are rejected. |
| A2 exact projection / observational exclusion | PASS with P1-1 exception | Prompt, request shape, schema/settings and generation semantics are in the projection; provider request ID is absent. |
| A3/cache/floating safety | PASS | Provider/deployment/client/profile fields participate in A3; cache binds A1/A2/A3/validation policy; FLOATING returns no cache identity. |
| Untrusted response / response identities | PASS | No conversion/mint method exists; text payload bytes, tool-object canonicalization, and envelope bytes have separate identities. |
| DAG topology / edge matching / policy identity | PASS with P0-4 exception | Missing/start/duplicate/cycle/ambiguous-edge validation and order-independent policy hashing work; zero or one selected edge behavior is deterministic. |
| Consent finite domain / context authority / capabilities | PASS | Closed enums reject `auto`/unknown values; provider-reported usage is observational only; declared capability is distinct from qualification. |
| TASK-016B/C preservation | PASS | No code changes touch scoring admission, repair, lineage, Phase G, or `AuthoritativeScoringReader`; normal A1 path retains the exact scoring request-hash rule. |

## Adversarial construction evidence

| Scenario | Result |
| --- | --- |
| Different exact prompt / different JSON schema | A2 changes: PASS. |
| Same semantics with observational request ID | Cache identity unchanged: PASS. |
| Different deployment | A3 and cache identity change: PASS. |
| FLOATING unresolved model | Cache identity is absent: PASS. |
| `A -> B -> A`, long cycle, duplicate nodes, ambiguous edges | Rejected: PASS. |
| Direct trusted-success constructor / copy / model APIs | Direct constructor and copy reject; no Pydantic APIs exist. Insufficient because `object.__new__` forge succeeds: FAIL (P0-1). |
| Wrong normal-path scoring hash / provenance used as hash | Normal factory rejects: PASS; unchecked/public authority paths succeed: FAIL (P0-2). |
| Generic credential field containing secret material | Accepted and exposed: FAIL (P0-3). |
| Consent provider vs execution provider, edge scope vs destination node | Contradictions accepted: FAIL (P0-4). |

## Verification

| Command | Result |
| --- | --- |
| `uv run pytest tests/unit/test_deep_analysis_contracts.py` | PASS — 22 passed. |
| `MYPYPATH=src uv run mypy tests/unit/test_deep_analysis_contracts.py` | PASS — no issues. |
| `uv run mypy src` | PASS — no issues in 32 source files. |
| `uv run ruff check src tests` | PASS. |
| `git diff --check` | PASS. |

The historical repository-wide `uv run mypy .` baseline was not treated as a
TASK-016 blocker. No production or test code was changed during this review.

## Required correction gate

Before the provider-neutral dispatch/validation boundary can proceed, resolve
P0-1 through P0-4 and P1-1 through P1-2, add the corresponding anti-forgery,
credential-redaction, cross-object-consistency, mode, and taxonomy tests, then
obtain a new independent review. No provider adapter, credential
implementation, persistence, or TASK-016D/E/F work is authorized by this
report.

Push/tag: **NO**
