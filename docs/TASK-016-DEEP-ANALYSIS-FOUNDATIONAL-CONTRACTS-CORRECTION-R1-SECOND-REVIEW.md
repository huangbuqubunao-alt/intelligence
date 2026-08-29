# TASK-016 — Foundational Contracts Correction R1 Second Independent Review

Status: **REQUEST CHANGES**

Date: 2026-08-30

## Scope and decision

- Reviewed HEAD: `main@c018b864159c0454f8a770d3df6ca3b91a26d620`.
- Reviewed range: `b66ed1dc9e2375e528dc05d507aaf1dfb13acda6..c018b864159c0454f8a770d3df6ca3b91a26d620`.
- Reviewed production/test focus: `deep_analysis_contracts.py` and its focused
  tests, along with the task card, handoff, accepted amendment, ADR-027, and
  focused fallback review. `.workbuddy/` was not inspected.
- Scope containment: **PASS**. R1 adds foundational contracts, registry state,
  and tests only; it adds no provider adapter, network/SDK code, credential
  storage/loading, database/persistence, fallback runtime, or TASK-016D/E/F.
  TASK-016B/C code is unchanged.

**REQUEST CHANGES.** Original P0 closure is **2/4**; original P1 closure is
**2/2**. R1 introduces no separate new P0 or implementation-critical P1, but
its public admission seam leaves original P0-1 and P0-2 open.

## Original-finding closure table

| Finding | Original issue | R1 mechanism | Result |
| --- | --- | --- | --- |
| P0-1 | `TrustedDeepAnalysisSuccess` trusted by shape/type. | Identity-keyed, weak-reference process-local registry plus `verify_trusted_deep_analysis_success`. | **OPEN** — the production module exposes an unrestricted callable mint/admit path. |
| P0-2 | A1/scoring authority could be forged. | Exact-object A1 admission registry and verifier. | **OPEN** — any caller can admit an arbitrary canonical object, then mint. |
| P0-3 | Credential profile retained raw generic routing fields. | Raw routing fields replaced with `provider_id` plus SHA-256 `execution_profile_identity`; error input hidden. | **CLOSED** for the intended structural contract. |
| P0-4 | Envelope and fallback duplicated authorization fields could disagree. | Provider/kind/model/context/prompt/schema and node-edge scope/credential checks. | **CLOSED**. |
| P1-1 | Structured-output mode matrix was incomplete. | Explicit required/forbidden matrix plus RAW single-user-message check. | **CLOSED**. |
| P1-2 | `PRE_DISPATCH/PROVIDER_UNAVAILABLE` was unrepresentable. | Allowed stage/code-pair matrix. | **CLOSED**. |

## Blocking findings

### P0-1 / P0-2 — The admission registry is not runtime-owned authority

R1 correctly makes a fabricated lookalike fail
`verify_trusted_deep_analysis_success`: an object made with `object.__new__`
and populated with the same fields has no matching weak-reference registry
entry. Copies, pickle serialization, and changed admitted identities are also
rejected.

That does not close the authority boundary. Both functions that create the
registry entries are ordinary module-level production callables:

- `_admit_authoritative_input_for_finalizer` registers *any*
  `CanonicalDeepAnalysisInputV1` without verifying an
  `AuthoritativeScoringReader` provenance, at
  [deep_analysis_contracts.py:970](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:970).
- `_mint_trusted_deep_analysis_success_for_finalizer` accepts arbitrary
  `content_identity` and `cache_identity` once that caller-registered input is
  present, at [deep_analysis_contracts.py:1001](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/src/youtube_intel/deep_analysis_contracts.py:1001).

They are not included in `__all__`, but a leading underscore and `__all__` are
not an execution capability boundary. Normal application code can import the
module and invoke both functions. The focused test itself imports and calls the
same production functions ([test file:42](/Users/hua/Documents/yia-worktrees/task-016c-main-integration/tests/unit/test_deep_analysis_contracts.py:42)).

The isolated review executed this exact caller-controlled sequence:

```python
_admit_authoritative_input_for_finalizer(canonical)
success = _mint_trusted_deep_analysis_success_for_finalizer(
    canonical_input=canonical,
    content_identity="a" * 64,
    cache_identity="b" * 64,
)
assert verify_trusted_deep_analysis_success(success)
```

It returned `True`. The `canonical` test fixture is built from publicly
constructible `VerifiedScoringRead`/scoring domain values, so the registry does
not establish that its request hash came from `AuthoritativeScoringReader`.
This is exactly the caller-controlled admission/mint path the correction claims
to prohibit. R1's registry changes the representation of the forgery but not
the authority available to a caller.

Required correction: move admission and mint authority behind an actual
runtime/finalizer-owned capability that ordinary callers cannot obtain merely
by importing the contracts module. The capability must be required for both
input admission and success minting, bind the verified scoring read and final
validated content/provenance, and be checked by trusted consumers. Tests must
exercise attempted imports/calls of all production mint/register helpers and
prove arbitrary canonical inputs and hashes cannot obtain admission.

## Regression and adversarial results

| Area | Result | Evidence |
| --- | --- | --- |
| Trusted lookalike | PASS narrowly | `object.__new__` + `object.__setattr__` lookalike is rejected by verifier. |
| Admission replay/transfer | PASS narrowly | Same-field second object, `copy.copy`, and pickle do not inherit admission. |
| Mutation safety | PASS narrowly | Changing an admitted identity invalidates verification; restoring the original identity revalidates the same admitted object. |
| A1 authority separation | **FAIL** | Caller can invoke the public module's `_admit_*` function, so A1-looking/caller-created objects become authoritative. |
| Scoring request binding | **FAIL as an authority boundary** | Normal construction still derives `VerifiedScoringRead.scoring_outcome.result.request_hash`, never provenance; public admission does not establish that it came from the authoritative reader. |
| A2 mode matrix | PASS | RAW schema rejected; JSON Schema without schema rejected; tool mode without tools/choice rejected; valid minima work. |
| A2 exact hashing | PASS | Existing and R1 mutation tests cover prompt, schema, tools/choice, payload/output language, and generation semantics. |
| Credential identity | PASS | Removed routing fields/extra secret fields reject; digest format is checked; repr/dump contain only provider ID and opaque identity. A raw secret deliberately placed in `provider_id` remains accepted, but that is misuse of the required provider-ID domain rather than a retained credential field or an authority grant. |
| Envelope cross-binding | PASS | Provider/kind/model/context/prompt/schema and A1/A2/scope/consent mismatches reject. |
| Failure taxonomy | PASS | `PRE_DISPATCH/PROVIDER_UNAVAILABLE` constructs; invalid pairs reject. |
| Fallback edge/node binding | PASS | Source/destination scopes and destination credential identity must match referenced nodes. |
| Fallback DAG regression | PASS | Cycle, duplicate-node, explicit-start, ambiguity, and bounded-attempt invariants remain intact. |
| A3/cache rebaseline | ACCEPTABLE | A3/node/policy/cache goldens change only for the pre-release credential structural correction; A1/A2/DACS-1 remain unchanged and no TASK-016D persisted consumer exists. |
| Registry lifetime | P2 observation | Dead weak references are never removed from either registry, so long-lived processes retain one dictionary entry per admission. Weak-reference identity checking prevents stale-entry transfer, but cleanup should accompany the authority correction. |

## Validation

| Command | Result |
| --- | --- |
| `uv run pytest tests/unit/test_deep_analysis_contracts.py` | PASS — 41 passed. |
| `uv run pytest -q` | PASS — 1823 passed, 1 existing Pydantic warning. |
| `MYPYPATH=src uv run mypy tests/unit/test_deep_analysis_contracts.py` | PASS — no issues. |
| `uv run mypy src` | PASS — no issues in 32 source files. |
| `uv run ruff check src tests` | PASS. |
| `git diff --check` | PASS. |

The historical repository-wide `uv run mypy .` baseline remains outside this
review's blocking result. No reviewed production/test file was modified.

## Required correction gate

Resolve P0-1/P0-2 by replacing the importable admission/mint helpers with an
actual finalizer/runtime-owned capability boundary, then add adversarial tests
for public helper invocation, caller-created `VerifiedScoringRead`, caller
canonical inputs, and arbitrary A1/A2/A3/content/cache hashes. Bound or clean
up dead registry entries while revising the registry. Do not start provider,
credential, persistence, or TASK-016D/E/F work before a further independent
review approves the trust boundary.

Push/tag: **NO**
