# TASK-022D Handoff — NVIDIA NIM / Kimi K3 V1 Production Authorization

## Metadata

- Task: `TASK-022D — Authorize NVIDIA NIM / Kimi K3 for Normal V1 Production`
- Role: `Implementer / adversarial reviewer`
- START_HEAD: `13c45bc4fcb379dbdbf81b667dee00a3ff140c29`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-022d-authorize-nvidia-kimi-production`
- Branch: `codex/task-022d-authorize-nvidia-kimi-production`
- Date: `2026-09-13`
- Reuse decision: `ADAPT` the existing TASK-022A NVIDIA adapter,
  TASK-022B verified input, TASK-023B reservation/continue seam, TASK-024
  orchestrator, m010/m016 Resource Ledger, and TASK-019 trusted reader.

## Qualification anchor

Both anchor checks returned exit `0`: the exact START_HEAD is a commit, and
`d9d72c06856270b5a55dab94ef8f426e89767fc9` is its ancestor. Mechanical review
of `handoffs/TASK-022A.md` passed all 12 required assertions: Phase 1, Case 2,
and Case 3 pass; schema, authoritative read, Evidence scope, and Evidence
support are `3/3`; unsupported accepted claims, semantic retries, provider
fallback, and model fallback are `0`; at-most-once is `PASS`.

The historical first `BLOCKED_AMBIGUOUS` attempt remains present, terminal,
and non-retryable. No qualification execution, request, budget, or credential
was reused by the normal-production tests.

## Delivered authorization

`NormalV1ProductionAuthorizationAuthority` is the backend source of truth for
one exact tuple only:

```text
nvidia_nim + moonshotai/kimi-k3 + V1_VIDEO_DISTILLATION
```

It mints a non-caller-constructible eligibility record. `QUALIFIED` and
`AUTHORIZED` are derived from the exact allowlist; `PRODUCTION_ELIGIBLE` also
requires runtime availability. `CloudDistillationAuthorization` no longer
accepts caller-provided `qualified`, `authorized`, or `production_eligible`
arguments. The local settings mutation rejects all three as extra frontend
fields.

Normal cloud continuation requires the adapter's distinct
`is_authorized_for_normal_production()` gate. Qualification exact-hash
authority cannot satisfy it. Conversely, the legacy direct cloud `distill()`
entry accepts only qualification authority, so normal production cannot bypass
TASK-023B canonical reservation/continue identities. Qualification hashes must
be explicit 64-character lowercase hexadecimal identities; absent/malformed
identity cannot compare equal.

## Acceptance matrix

| Requirement | Result | Evidence |
| --- | --- | --- |
| Exact NVIDIA/Kimi/V1 tuple | PASS | Exact matrix resolves qualified, authorized, and eligible. |
| Other provider/model/capability | PASS | OpenAI, other NVIDIA/Kimi model, Deep Analysis, Investigation, Ask, Daily, Evidence Expansion, TASK-016G, V2, display-name and prefix variants all resolve false. |
| Frontend/caller forgery | PASS | Constructor and local API tests reject forged derived states. |
| AVAILABLE false | PASS | Normal Source Run reaches existing model-unavailable Needs Attention; credential and wire calls `0`. |
| QUALIFIED/AUTHORIZED false | PASS | Exact authority resolves false and normal adapter permission fails closed. |
| Cloud disabled | PASS | Needs Attention; credential and wire calls `0`; default remains off. |
| Credential unavailable | PASS | Indirect availability gate blocks before resolver/network; calls `0`. |
| Budget denied | PASS | Budget blocks before credential resolution/transport; calls `0`. |
| Reservation / verified input / identity | PASS | Normal success uses TASK-023B reserve/bind/continue and TASK-022B exact reconstruction; existing mismatch/missing tests remain green. |
| Normal Source Run | PASS | One fake NVIDIA invocation, TASK-022 admission, TASK-019 authoritative read, truthful ledger. |
| Successful continuation/restart | PASS | Additional invocations `0`. |
| AMBIGUOUS continuation/restart | PASS | Durable Needs Attention; additional invocations `0`. |
| Invalid output | PASS | Semantic retries `0`; one invocation; no admission. |
| Provider/model fallback | PASS | `0`; exact adapter identity and existing mismatch rejection retained. |
| Timeout | PASS | Normal fake wire observes `120.0`; qualification-only `300` cannot enter normal factory. |
| Resource Ledger / disclosure | PASS | Selected/actual exact identity and invocation count recorded; no secret, payload, transcript, Evidence excerpt, local path, or raw personalization added. |

## Verification

| Check | Result |
| --- | --- |
| TASK-022D/TASK-022/TASK-024 focused after hardening | `91 passed` |
| TASK-018B→025A, dispatch-v4, orchestration/API, PO-demo regression after hardening | `282 passed` |
| Full pytest (once) | `2255 passed, 1 skipped, 1 existing Pydantic warning` in `142.53s` |
| `uv run --offline mypy src` | PASS; `54` source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; wheel and sdist built; existing uv build-system-version warning |
| Fresh SQLite probe | `initialize_version=16`, `user_version=16`, `migration_rows=16` |
| Migration files | m015 present; m016 present; m017 absent |
| `git diff --check START_HEAD..HEAD` | PASS before handoff |
| Canonical security scanner | EXIT `1`; exactly `11` accepted historical synthetic-fixture findings; `0` new; not scanner PASS |

## Adversarial review

Initial findings fixed before the final regression:

1. P1: qualification exact-hash permission could be supplied to normal
   continuation. Fixed with a distinct normal-production adapter gate.
2. P1: absent qualification and verified hashes could compare equal. Fixed by
   strict explicit hash validation.
3. P1: normal production authority could enter the legacy unreserved
   `distill()` path. Fixed by reserving that cloud path for qualification and
   moving normal tests to TASK-023B continuation.

Final result: `P0=0`, `P1=0`, `P2=0`. Review also found no wildcard authority,
Deep Analysis/TASK-016G/V2 leakage, caller trust flag, credential/budget bypass,
fallback, semantic retry, success or AMBIGUOUS redispatch, qualification
history rewrite, transcript disclosure, m017, silent cloud/spending enablement,
or main/tag/remote mutation.

## Scope and closeout

- Database/schema: unchanged at v016; no migration.
- TASK-018B, TASK-022B, TASK-022C: unchanged.
- TASK-022A: unchanged except the bounded authorization integration.
- Deep Analysis: `BLOCKED`; its historical Kimi qualification is unchanged.
- TASK-016G: `UNAUTHORIZED`.
- V2: not started; leakage `0`.
- Real provider/YouTube calls in TASK-022D: `0`.
- Secrets committed: `NO`.
- Dependencies/lockfiles/toolchain: unchanged.
- UI polish, broad real-user RC trial, main integration, push, tag, release,
  and public distribution: not performed and not authorized.

Recommended verdict: `APPROVE`. NVIDIA NIM / `moonshotai/kimi-k3` is legally
production-eligible for normal V1 Video Distillation only when every existing
runtime/user/credential/budget/source/reservation/input/at-most-once gate also
passes. Product Owner may next authorize Real-Data UX Polish and then separately
decide main integration or new private RC preparation.
