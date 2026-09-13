# TASK-022D — NVIDIA NIM / Kimi K3 V1 Production Authorization

Status: **PRODUCT OWNER AUTHORIZED**

## Qualification evidence

The authoritative predecessor is
`13c45bc4fcb379dbdbf81b667dee00a3ff140c29`. Its governed
`handoffs/TASK-022A.md` records an immutable historical first attempt of
`BLOCKED_AMBIGUOUS`, followed by three independent successful executions:
Phase 1, Phase 2 Case 2, and Phase 2 Case 3. Across those successful cases the
exact TASK-022 schema, TASK-019 authoritative read, exact outbound Evidence
scope, and Evidence support each passed `3/3`; material unsupported accepted
claims, semantic retries, provider fallback, and model fallback were all `0`;
at-most-once was `PASS`.

The historical ambiguous attempt remains terminal and non-retryable. This
authorization does not rewrite or hide qualification history and does not
reuse any qualification execution, request, budget, or authorization identity.

## Exact authorization

Only this exact tuple is authorized:

| Field | Authorized value |
| --- | --- |
| Provider | `NVIDIA NIM` (canonical runtime ID `nvidia_nim`) |
| Model | `moonshotai/kimi-k3` |
| Capability | `V1_VIDEO_DISTILLATION` |
| AVAILABLE | `YES` when the runtime availability gate confirms it |
| QUALIFIED | `YES` |
| Product Owner AUTHORIZED | `YES` |
| PRODUCTION_ELIGIBLE | `YES` only while AVAILABLE is also `YES` |

Matching is exact. Prefix, family, wildcard, provider substitution, model
substitution, and capability substitution are forbidden. Other NVIDIA models,
other Kimi models, other providers, Deep Analysis, Investigation, Ask, Daily,
Evidence Expansion, TASK-016G, and V2 are not authorized by this decision.

## Normal production gates

Production eligibility is permission to use this exact tuple, not an order to
call it. A normal V1 Source Run may dispatch only after all existing gates pass:

```text
AVAILABLE + QUALIFIED + AUTHORIZED
+ explicit runtime/user cloud enablement
+ indirect credential availability
+ budget admission
+ legal Source Run eligibility
+ canonical TASK-023B reservation
+ matching TASK-022B VerifiedDistillationInput
+ at-most-once dispatch claim
```

Any missing gate means zero provider calls. Qualification executions are never
normal-production authorities. The frontend and other callers cannot submit
`qualified`, `authorized`, or `production_eligible` facts; the backend derives
them from this bounded authority and runtime facts.

Cloud and spending remain default-off unless explicitly configured by the
user/runtime. Authorization creates no budget bypass, credential persistence,
provider rotation, model downgrade/upgrade, semantic retry, JSON repair, or
silent fallback. A missing credential, denied budget, unavailable provider,
invalid reservation, missing verified input, or request-identity mismatch uses
the existing fail-closed/Needs Attention behavior with zero network calls.

Normal production retains the existing 120-second NVIDIA adapter timeout. The
qualification-only 300-second response wait remains exact-hash and one-call
scoped and cannot expand normal latency.

## Trust, ledger, and persistence boundaries

TASK-022 admission and TASK-019 trusted read remain unchanged. Authorization
does not change Evidence/request trust, disclose a full transcript, or permit
provider payload, credential, Evidence excerpt, transcript, local path, or raw
personalization persistence in the Resource Ledger. The ledger continues to
record only truthful selected/actual identity, invocation count, reliable
duration/tokens/cost when known, and outcome. `AMBIGUOUS` retains TASK-022C's
terminal zero-redispatch semantics with unknown facts remaining unknown.

Database authority remains version `16`: m015 and m016 are present and m017 is
absent. This task creates no migration, new trust root, retry semantics, live
qualification call, broad real-user RC trial, UI redesign, main integration,
tag, push, release, or public distribution authority.

