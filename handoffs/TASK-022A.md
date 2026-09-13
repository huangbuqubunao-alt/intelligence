# TASK-022A Handoff — V1 Production Cloud Transport Amendment

## Delivered boundary

START_HEAD: `86e24588c753a529113e1886dd6c165dfb95feea`.

V1 Distillation now recognizes only `OFFLINE_TEST` and `CLOUD_PRODUCTION`.
Cloud remains denied by default.  The single OpenAI seam accepts only the
TASK-022B `VerifiedDistillationInput`, has a fixed endpoint identity, requires
an explicit provider/model plus indirect credential availability and either
normal qualified+authorized state or exact-hash one-call qualification scope.
Its mockable wire seam receives `max_retries=0`; no live transport was called.

TASK-022C m016 remains the durable outcome authority for a future ambiguous
post-dispatch result.  This amendment neither creates a provider qualification
result nor changes Cloud defaults, Deep Analysis, TASK-016G, V2, migrations,
main, the RC tag, remote state, or release state.

## Verification

- Focused TASK-022/022B/023B: `49 passed`.
- Full pytest: `2211 passed, 1 skipped, 1 existing Pydantic warning`.
- `mypy src`, Ruff, `uv build --offline`, and `git diff --check`: passed.
- Fresh temporary DB: v016; m015/m016 present; m017 absent.
- Scanner: exit `1`, 11 accepted historical synthetic-fixture findings, 0 new;
  this is baseline evidence, not scanner PASS.

## Next authorized action

Product Owner may decide whether to configure exactly one provider/model and
start separate real YouTube/provider qualification from this approved anchor.

## NVIDIA NIM adapter preservation closeout — 2026-09-13

This addendum preserves the bounded NVIDIA NIM Video Distillation adapter from
`a7531557542974aa05e7b9f5e4cbfe803a05e6a4` as implementation commit
`7b5018a`.  It does not supersede the historical delivery record above and
does not grant provider qualification or normal production eligibility.

- `PHASE1_RESULT: BLOCKED_AMBIGUOUS`
- `REAL_PROVIDER_CALLS: 1`
- `CONFIRMED_RESPONSES: 0`
- `REDISPATCH: 0`
- `PROVIDER_QUALIFIED: NO`
- `PRODUCTION_ELIGIBLE: NO`

The isolated qualification ledger and checkpoint both remain terminal
`AMBIGUOUS` with `TRANSPORT_OUTCOME_UNKNOWN`, invocation count `1`, and
selected identity `nvidia_nim / moonshotai/kimi-k3`.  Actual provider/model,
token usage, and cost remain unknown; no Intelligence or revision was admitted.
That execution is permanently non-retryable.

The preserved adapter accepts only TASK-022B `VerifiedDistillationInput`,
uses the fixed official NVIDIA authority and exact model, resolves credentials
only at the transport boundary, and has zero SDK/HTTP retry, semantic retry,
provider fallback, model fallback, or JSON repair.  The existing OpenAI adapter
also gained an adapter-local provider guard so an NVIDIA authorization cannot
cross-dispatch through it.  Cloud remains default-off.

Preservation verification was entirely offline:

- NVIDIA adapter focused tests: `10 passed`.
- TASK-018B/019/022/022B/023B regressions: `80 passed`.
- Full pytest: `2222 passed, 1 skipped, 1 existing Pydantic warning`.
- `mypy src`, Ruff, `uv build --offline`, and `git diff --check`: passed.
- Isolated DB: user version `16`; m015/m016 present; m017 absent.
- Canonical scanner: exit `1`, exactly 11 accepted historical synthetic
  fixture findings, 0 new.  This is not a scanner PASS.
- Network/provider/YouTube calls during this preservation task: `0`.
- Credentials, provider payloads, full transcripts, downloaded media, and the
  qualification database are absent from Git.

The next action requires a Product Owner decision about whether to authorize a
completely new, independent NVIDIA NIM qualification execution.  The prior
`AMBIGUOUS` execution must never be retried.

## NVIDIA NIM / Kimi K3 independent Phase 1 attempt 2 — 2026-09-13

This independent attempt started from `f1454ba1db61b01589811ec8986e1269473ab318`.
Commit `b60c835` adds a qualification-scoped 300-second response wait while
preserving the normal 120-second default.  The 300-second wait applies only to
the same one-call qualification request and does not add retries, redispatch,
provider fallback, or model fallback.

- `PHASE1_RESULT: PHASE1_PASS`
- `PREVIOUS_AMBIGUOUS_EXECUTION_REUSED: NO`
- `NEW_EXECUTION_ID: distillation:reservation:v2:58d27c5d747c6276fc7ae178cc03831ac11ba31df2d0a844da0bc32c2c516155`
- `VIDEO_ID: aircAruvnKk`
- `VIDEO_TITLE: But what is a neural network? | Deep learning chapter 1`
- `TRANSCRIPT_SOURCE: manual_subtitle`
- `TIMED_TRANSCRIPT_CUES: 286`
- `BOUND_EVIDENCE_COUNT: 4`
- `VERIFIED_INPUT_HASH: ecc54dc08dfd2d1614ab893ebac391ee0a6ed9fc94ddc2e712fd39e0fb1898ec`
- `PROVIDER: NVIDIA NIM`
- `REQUESTED_MODEL: moonshotai/kimi-k3`
- `ACTUAL_MODEL: moonshotai/kimi-k3`
- `REAL_PROVIDER_CALLS: 1`
- `CONFIRMED_RESPONSES: 1`
- `REDISPATCH: 0`
- `TRANSPORT_OUTCOME: ADMITTED`
- `PROVIDER_QUALIFIED: NO / PENDING_PHASE2`
- `PRODUCTION_ELIGIBLE: NO`

The exact TASK-022 schema passed without repair or extraction, the accepted
claims were supported by the exact outbound Evidence set, and TASK-019
`AuthoritativeIntelligenceReader` returned the admitted Intelligence.  The
immutable Resource Ledger records one invocation, 1,657 input tokens and 692
output tokens.  Cost and duration remain truthfully unknown.  It contains no
credential, Evidence excerpt, transcript, provider payload, or raw
personalization.

The isolated real-data UI showed the admitted Intelligence, its four Evidence
rows, the enabled Source, and truthful Resource Usage.  Provider/model details
remain less discoverable behind the collapsed technical-details control, and
the Source list displays the canonical channel URL when no friendly display
name is stored.  No redesign was made.

Verification for the bounded timeout change and attempt:

- NVIDIA/timeout focused tests: `13 passed`.
- TASK-018B/019/022/022B/023B regressions: `83 passed`.
- Full pytest: `2225 passed, 1 skipped, 1 existing Pydantic warning`.
- `mypy src`, Ruff, `uv build --offline`, and `git diff --check`: passed.
- Isolated DB: user version `16`; m015/m016 present; m017 absent.
- Canonical scanner: exit `1`, exactly 11 accepted historical synthetic
  fixture findings, 0 new.  This is not a scanner PASS.

The historical `BLOCKED_AMBIGUOUS` execution remains unchanged and permanently
non-retryable.  Normal production remains disabled; Deep Analysis remains
blocked; TASK-016G remains unauthorized.  No Phase 2, push, tag, release, main
change, or RC-tag movement was performed.  Product Owner must separately
authorize Phase 2.
