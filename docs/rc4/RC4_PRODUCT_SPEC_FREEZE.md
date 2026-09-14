# RC4 Product Specification Freeze

## Status

**PROPOSED_FREEZE**

This document proposes one bounded RC4 scope for Product Owner approval. It
does not authorize implementation, a database migration, provider calls, a
push, a tag, or a release.

Predecessor: `effeaa9e76ddf09f18f2d721862fbfe363886d51`

Product reviewed: `v0.1.0-rc.3` / `9422c08761eb5cb996758edee26d698dadfd901a`

## Product Goal

Make the existing V1 Video Distillation product usable and trustworthy for its
private-RC target user from first startup through the first Source Run. RC4 is
successful when the user can understand the product, determine whether the
current installation can execute, resolve allowed prerequisites, add a Source
with safe starter settings, follow a truthful run, read Intelligence, verify
Evidence, and handle an actionable failure without repository knowledge.

This is a production-readiness repair, not a capability expansion.

## Target User

### TARGET_USER

A single-user, Mac-first, AI-comfortable product or technology knowledge worker
who follows YouTube for professional information. They are comfortable using
one documented local startup command or launcher and following a one-time
credential setup guide. They do not understand repository internals, provider
qualification, execution reservations, task IDs, database concepts, or runtime
architecture.

### NON_TARGET_USER

- A mass-market user expecting App Store installation and no terminal use.
- A hosted, multi-user, or team-administration customer.
- A user unwilling to provide the supported external model credential or allow
  approved evidence-bounded cloud processing.
- A user who requires every operation to remain offline.

### TECHNICAL_COMFORT_ASSUMPTION

The user can copy an exact command, configure an environment variable using
guided instructions, and restart the local product. They must never compose an
executor, edit application code, inspect SQLite, or interpret provider
eligibility to use the product.

### SETUP_TOLERANCE

One-time local setup may take 10–15 minutes. Adding the first Source should take
about 5 minutes of active work. Discovery and model-processing time are separate
and must be described as variable.

### COST_CONTROL_EXPECTATION

Recurring cloud work and spending are opt-in and visible. The user can inspect
the active provider/model, processing limits, current budget condition, and
observed usage. Unknown cost is never presented as zero or free.

### PRIVACY_EXPECTATION

Persistence is local by default. The UI never reveals or accepts the credential
value. Before cloud processing, the product explains that the minimum approved,
evidence-bounded distillation input is sent to NVIDIA NIM; it does not claim that
all processing is local or promise guarantees not established by rc.3.

## Problem Statement

The intended product is “AI watches relevant YouTube for me and turns it into
traceable Intelligence.” The rc.3 consumption and Evidence experience supports
that promise once trusted data exists. The ordinary first-run product does not:

1. The documented `serve-api` startup creates a safe read/configuration UI but
   does not attach the production Source Run executor. `Check Now` is guarded.
2. Settings presents static provider eligibility but does not prove current
   executor, credential, provider, or budget readiness.
3. The Source editor asks for many decisions simultaneously and defaults a new
   automatic schedule to Daily at 09:00.
4. The nested Source editor does not satisfy keyboard/modal behavior.
5. `Check Now` acknowledges a run but does not expose enough of the already-
   persisted run/checkpoint truth to support leaving and returning.
6. Needs Attention copy is safe but does not provide direct, condition-specific
   navigation.

These gaps make rc.3 unsuitable for a broader self-guided private trial even
though its trust and provider contracts are strong.

## Non-Goals

- Deep Analysis, Investigation execution, TASK-016G, or V2.
- New providers, models, fallback, provider marketplace, or qualification work.
- New Topic, Weekly, Save, Daily, Ask, or recommendation semantics.
- A broad top-level IA redesign or design-system rewrite.
- A telemetry platform, billing system, cost estimator, or new AI calls for UX.
- An in-app credential manager, keychain integration, or credential vault.
- Automatic cloud enablement, automatic budget increase, or automatic spending.
- General packaging/distribution work beyond the one supported private-RC local
  startup path.

## Frozen Trust Constraints

RC4 must preserve all of the following:

- Source → Video → Timestamp → verified excerpt Evidence traceability.
- Fail-closed trusted reads for Intelligence, Saved, Topic, and Evidence.
- Durable at-most-once behavior and no automatic/manual Retry for AMBIGUOUS.
- No provider fallback, model fallback, or hidden quality downgrade.
- Budget enforcement before dispatch and credential access.
- `UNKNOWN` cost remains unknown; it does not mean free.
- Deep Analysis remains unavailable.
- Analyze this Video overrides relevance only.
- Production authority remains exactly NVIDIA NIM / `moonshotai/kimi-k3` /
  `V1_VIDEO_DISTILLATION_ONLY`.
- Credential values never enter UI, API payloads, logs, documentation examples,
  repository content, or error messages.
- Frontend readiness and permissions are projections of backend authority; the
  frontend cannot mint them.

## End-to-End First-Run Target Experience

A first-time target user can:

1. Launch one supported local product composition and open the Dashboard.
2. Understand within five seconds that the product turns relevant YouTube into
   traceable Intelligence.
3. See a compact readiness summary plus independent prerequisite states.
4. Follow approved instructions for any missing local startup or NVIDIA
   credential prerequisite and verify the result after restart.
5. Add a Source using only a YouTube URL and a visible recommended-settings
   summary; saving alone performs no external work.
6. See that new Sources are manual by default and explicitly opt into recurring
   work if desired.
7. Select `Check Now`, receive a durable run identity, and see a truthful named
   stage without a fabricated percentage.
8. Leave the Source view, return or reload, and recover the same orientation.
9. Distinguish completion with Intelligence, completion with no important
   change, partial completion, safe failure, and Needs Attention.
10. Open produced Intelligence and verify its Evidence at the original source.
11. Follow a safe direct action for a recoverable prerequisite and never see an
   illegal Retry for an ambiguous external outcome.

“Read useful Intelligence” is not guaranteed for every Source Run. The product
must confidently report “no important change” when that is the truthful result.

## Scope

### MUST

| Item | Classification | Frozen boundary |
| --- | --- | --- |
| UX-001 Production readiness | PRODUCT_FIX + DOCUMENTATION | Supported production composition; backend-derived readiness dimensions; no secret storage. |
| UX-002 Accessible Source configuration | PRODUCT_FIX_REQUIRED | Keyboard, accessibility-tree, focus, error-association contract for the Source dialog only. |
| UX-006 Source Run feedback | PRODUCT_FIX + DOCUMENTATION | Project existing durable run/checkpoint/child truth; no new state or percentage. |
| UX-011 Safe recovery actions | PRODUCT_FIX + DOCUMENTATION | Finite messages and navigation/action mapping; no generic Retry. |
| Documentation reconciliation | DOCUMENTATION_ONLY after verified behavior | Update RC3 Quick Start/User Manual for actual RC4 startup, readiness, onboarding, progress, and recovery. |

### SHOULD

| Item | Classification | Frozen boundary |
| --- | --- | --- |
| UX-003 Starter Source onboarding | PRODUCT_FIX + DOCUMENTATION | One required URL, visible recommended summary, Customize path, manual-by-default for new Sources only. |
| UX-005 Source validation guidance | PRODUCT_FIX_REQUIRED | Safe field-level errors; never expose raw exceptions. |
| UX-004 Dashboard blocker priority | PRODUCT_FIX_REQUIRED | Conditional compact blocker summary only; no general warning-first layout. |
| UX-012 unknown-cost explanation | PRODUCT_FIX + DOCUMENTATION | Adjacent explanation that unavailable cost is not zero/free. |

### STRETCH

- Add human-readable Source/video attribution to Resource Usage only from the
  already-persisted `source_id` and `video_id` associated with the exact
  execution. If an authoritative display label cannot be resolved, show a safe
  stable label or omit attribution; never infer it.

### DEFER

- Full Dashboard Intelligence-card compaction or a permanent new hierarchy.
- Save mental-model expansion and item-specific Save accessible names.
- Topic evolution/disagreement semantics.
- Weekly generation or synthesis changes.
- Broad claim-kind or technical-provenance language redesign.
- Investigations navigation or capability change.
- Resource attribution requiring new durable truth.
- All V2 and strategic product-model work.

### REJECT

- In-app API-key entry/storage or a new credential security subsystem.
- A single frontend-authored `ready` flag.
- Fake progress percentages, timers, or phases not derived from backend facts.
- Retry, redispatch, or “try again” for AMBIGUOUS work.
- Automatic provider/model fallback, cloud enablement, schedule enablement, or
  budget increase.
- Estimated/inferred cost or usage attribution.
- Any `m017` migration for this scope.
- Investigation, Deep Analysis, TASK-016G, or V2 leakage.

## UX-001 Production Readiness

### Exact current problem

| Dimension | rc.3 condition |
| --- | --- |
| Installation | Repository/package setup exists but is not a mass-market installer. This is acceptable for the target user. |
| Application startup | API and frontend require separate startup; standard API starts successfully. |
| Frontend/API connection | When both processes run, the UI can read/write safe projections. Connection failure is not explained as a readiness dimension. |
| Normal Source execution availability | Standard `serve-api` does not attach the durable Source Run submitter/executor; `Check Now` is guarded. This is the P1. |
| Provider availability | Exact NVIDIA/Kimi authority exists, but current UI status is a static qualification projection rather than active runtime availability. |
| Credential availability | Production execution can fail closed when the indirect credential is missing; UI does not show a safe current-presence check. |
| Budget availability | Budget denial is enforced before dispatch, but first-run UI does not show whether budget needs review. |
| Source configuration | Backend validates and persists Sources, but UI readiness does not distinguish absent, disabled, or invalid Source state. |

### Desired user experience

Use a **guided readiness checklist** with two placements:

- A compact first-run/blocked card on Dashboard that states the next user goal.
- A detailed **Run readiness** section in Settings with independent dimensions,
  evidence-backed status, explanation, and safe action.

This is not a full-screen gate. Users may configure Sources and read existing
Intelligence even while execution is unavailable. `Check Now` performs a safe
backend preflight and links directly to the unresolved dimension.

### Frozen product-facing readiness model

| Dimension | User-facing states | Meaning and allowed action |
| --- | --- | --- |
| Local app | Connected / Cannot connect | Frontend has or lacks a successful loopback API response. Show restart/reconnect instructions; do not guess backend state when disconnected. |
| Source processing | Ready to start / Setup required / Temporarily unavailable | A supported Source Run executor is attached; missing composition requires approved startup instructions; unavailable local service is not mislabeled as model failure. |
| Video analysis model | Approved / Temporarily unavailable / Not approved | Exact backend provider/model/capability authority and current provider availability. Only the rc.3 tuple may be Approved. |
| NVIDIA credential | Available / Setup required / Status unavailable | Runtime-owned safe presence check only. Never return or render the value. Link to external setup instructions. |
| Usage budget | Within current limit / Limit reached / Checked when work starts / Status unavailable | Use authoritative budget truth. If the next exact execution cannot be evaluated yet, say so; do not show green. |
| Source | Add a Source / Ready for manual check / Disabled / Fix configuration | Backend-derived Source existence, enabled state, and validation result. |

An overall summary may say **Ready to check a Source**, **Setup required**,
**Review usage limit**, or **Temporarily unavailable**, but must show the
individual dimensions that produced it. “Ready” means preconditions currently
known to the backend pass; it is not a guarantee that a Source contains eligible
videos or that an external request will succeed.

### Credential decision

RC4 freezes a combined **Option A + C**:

- The user configures `NVIDIA_API_KEY` outside the application using guided,
  Mac-first local instructions.
- The running backend exposes only safe presence status.
- The UI does not accept, persist, edit, copy, reveal, or validate the key by
  making a speculative provider call.
- After setup the user restarts the approved local process and selects **Check
  readiness**; detection itself causes no provider call.

Secure in-app storage is deferred because it would require a separately approved
security architecture, lifecycle, permissions, redaction, backup, and recovery
contract.

### Security boundaries

- No secret values or prefixes in frontend/API data, logs, errors, analytics, or
  screenshots.
- Readiness cannot make a network call merely to prove availability unless an
  existing explicitly authorized non-billable probe exists; otherwise report
  the backend's current known availability.
- Missing credential, provider unavailable, and budget denied all cause zero
  model dispatches.
- Readiness never enables cloud processing, recurring schedules, or spending.

### Preferred design and rejected alternatives

**Preferred:** contextual Dashboard summary + detailed Settings checklist +
`Check Now` preflight using the same backend authorities.

Rejected:

- A single red/green badge: hides independent failure and unknown states.
- A blocking setup wizard: prevents local reading/configuration and overstates
  self-service installation.
- In-app credential entry: creates an unauthorized credential subsystem.
- Documentation alone: cannot repair the missing production executor path or
  false-green risk.

### Acceptance criteria

- One repository-supported Mac-first startup path attaches the existing durable
  production Source Run pipeline and serves the loopback UI safely.
- The UI never reports execution ready when the executor is absent.
- Each readiness dimension can be independently exercised and rendered.
- Missing credentials, provider unavailability, and budget denial perform zero
  model calls and show different guidance.
- A user can follow the credential guide without seeing a real key example.
- Existing local content remains readable when production execution is blocked.

## UX-002 Accessible Source Configuration

### Behavior and keyboard contract

- Exactly one active dialog is exposed as modal in the accessibility tree.
- Opening Add Source or Edit configuration moves focus into the active dialog,
  preferably to the dialog heading or first invalid/required field.
- Tab and Shift+Tab traverse all enabled interactive controls in logical order
  and remain within the active dialog.
- Escape closes only the topmost active dialog when dismissal is safe.
- Closing returns focus to the control that opened that dialog. For nested edit
  entry, focus returns to **Edit configuration**; closing Source Detail returns
  focus to its Source trigger.
- Background content and an underlying Source Detail dialog are inert and not
  actionable while SourceForm is active.
- The dialog has an accessible name and, where useful, description.
- Pointer click outside may either do nothing or follow the same safe dismissal
  policy as Escape; it must not silently discard unsaved work.
- Visible focus is maintained on every control.
- Field errors are programmatically associated, announced, and focused or
  summarized after submit.

### Acceptance criteria

- A keyboard-only user can open, complete, submit, cancel, and re-open Add/Edit
  Source without focus entering background UI.
- Accessibility-tree inspection exposes the active dialog, name, fields, and
  errors and does not expose an actionable second modal beneath it.
- Escape and focus restoration pass in both Add and nested Edit paths.
- Browser acceptance passes at 1440×900, 1280×800, and 768×900.
- No component-library or design-system rewrite is required by this contract.

## UX-003 Source Onboarding

### Minimum choices before first value

The only required first-step input is **YouTube Source URL**. The form shows a
plain-language **Recommended settings** summary before save:

- Turn relevant videos into Intelligence.
- Monitor this Source: On.
- Initial history: 5 recent videos.
- Per-run limit: 5 new videos.
- Distillation style: Balanced.
- Automatic schedule: Manual / none.

Saving the Source alone remains local and performs no discovery or model call.

### Starter versus advanced

| Starter/required surface | Advanced under Customize settings |
| --- | --- |
| Source URL | Processing level: discover only or create Intelligence |
| Recommended-settings summary | Monitor Source on/off |
| Explicit “saving does not run it” copy | Initial history |
| Add Source | Per-run limit |
| Customize settings disclosure | Distillation style |
|  | Focus and Ignore terms |
|  | Automatic schedule cadence, day/time, and enablement |

Initial history and per-run limit are visually present in the summary because
they affect work volume. They may be edited under Customize, but are not hidden
from a starter user. Focus and Ignore are advanced because blank values are
valid and examples are more useful than required decisions.

### Defaults

- Retain existing policy values: Initial History 5, Per-run Limit 5,
  Standard Intelligence, and Balanced style.
- Change the **new-Source UI schedule default only** from Daily 09:00 enabled to
  Manual/no schedule. This is an explicit trust and cost-control decision, not a
  silent policy change.
- Existing Source policies and schedules are never rewritten.
- Selecting Daily or Weekly reveals cadence/time and a plain-language notice
  that scheduled eligible work may use NVIDIA and available budget. The user
  explicitly confirms the schedule.

Advanced controls remain discoverable from both **Customize settings** during
creation and **Edit configuration** on Source Detail.

### Acceptance criteria

- A user can add a valid Source after entering one URL and reviewing the visible
  settings summary.
- No automatic schedule is created unless the user explicitly selects and
  confirms one.
- Initial/per-run limits and provider-use implications are visible before any
  recurring schedule is confirmed.
- Customize exposes every existing setting without changing its semantics.
- Existing Sources retain their current schedules and values.
- Invalid fields receive safe, associated, field-specific guidance.

## UX-004 Dashboard Priority

### Conditional hierarchy

Healthy/default Dashboard order remains:

1. What matters now.
2. Topic changes.
3. This week.
4. Non-blocking Attention, if any.

When current work is genuinely blocked, add a compact **Run blocked** summary
above What matters now. It must not expand into full technical detail.

### Blocking versus non-blocking

**BLOCKING** means at least one of:

- The installation cannot start a requested Source Run.
- An enabled Source's current requested/scheduled run cannot continue because
  credential, budget, provider, valid configuration, or a user decision is
  required.
- An external outcome is AMBIGUOUS and the affected run cannot continue.

**NON-BLOCKING** means historical information, a localized issue that does not
prevent current enabled work, or guidance that does not require immediate user
action. Such information stays below Intelligence or in Source/Settings.

Attention rises above Intelligence only while the blocking condition is current.
Use one compact summary with a count when multiple blockers exist and a safe
primary navigation action. Do not render a wall of warnings.

Dashboard may continue to render its existing trustworthy Intelligence cards
in RC4. Full card summarization/compaction is deferred until the external test;
Evidence must remain directly reachable.

### Acceptance criteria

- A healthy Dashboard is never warning-first.
- A current blocker is visible without scrolling past all full Intelligence
  cards.
- At 1440×900 and 1280×800, the compact blocker and first Intelligence conclusion
  remain visible without forcing a long warning section.
- At 768×900, the blocker, next action, and start of value content remain
  reachable in the initial viewport or immediate next scroll.
- Non-blocking/history items do not displace What matters now.

## UX-006 Source Run Feedback

### Truthful state model

RC4 uses only existing authoritative state:

| Existing state/fact | User-facing meaning |
| --- | --- |
| `QUEUED` | Waiting to start |
| `RUNNING` + Discovery | Checking the Source for videos |
| `RUNNING` + Selection/Filtering | Choosing relevant videos |
| `RUNNING` + Source preparation | Preparing selected videos |
| `RUNNING` + Distillation | Creating Intelligence |
| `RUNNING` + Intelligence admission | Verifying Intelligence |
| `RUNNING` + Topic update | Updating Topics |
| `RUNNING` + Finalization | Finishing the Source Run |
| `WAITING` | Waiting to continue; show only an authoritative safe reason if one exists |
| `PARTIAL` | Partially completed; some expected updates could not be finalized |
| `NEEDS_ATTENTION` | Cannot continue without the shown prerequisite or decision |
| `COMPLETED` + admitted Intelligence count > 0 | Complete; show the number of new Intelligence items |
| `COMPLETED` + admitted Intelligence count = 0 | Complete; no important change was found |
| `FAILED` | Did not complete; existing trusted Intelligence is unchanged |
| `AMBIGUOUS` | External result unconfirmed; no Retry |
| `CANCELLED` | Cancelled; no success implied |

The user-facing stage is derived from the next/completed checkpoint and current
run state. No percentage, estimated completion time, or unpersisted “AI is
thinking” state is allowed.

### Persistence expectations

- Run identity, state, checkpoints, children, and execution linkage already
  survive navigation, reload, and process restart.
- RC4 must project these existing facts to Source Detail and the result of Check
  Now. Polling or explicit refresh is acceptable; a websocket is not required.
- Reopening a Source shows the same current run and terminal outcome.
- The UI never converts re-reading/resuming an existing run into Retry.

### Backend implication

**SOURCE_RUN_PROGRESS_STORAGE: BOUNDED_BACKEND_PROJECTION.** The current schema
already contains the necessary durable truth. The API may add a safe projection
of checkpoint progress, child/result counts, and current run identity. No new
durable domain state and no migration are authorized.

### Acceptance criteria

- `Check Now` returns/anchors a durable Source Run and immediately shows Waiting
  to start or the first authoritative stage.
- Stage changes match persisted checkpoint changes.
- Navigation away, reload, and backend restart preserve orientation.
- Completion distinguishes Intelligence created from no important change.
- Ambiguous, partial, failed, waiting, and Needs Attention states remain distinct.
- No state display causes dispatch, Retry, fallback, or new execution.

## UX-011 Recovery Actions

| Condition | User-facing message | Safe action | Forbidden action |
| --- | --- | --- | --- |
| Credential unavailable | Video analysis cannot start because the NVIDIA credential is not available. No model request was sent. | Open Run readiness and external credential setup instructions; re-check readiness after process restart. | Show/accept/store the key; make a test model call; automatic Retry. |
| Budget blocked | This run stopped before a model request because the current usage limit does not allow it. Existing Intelligence is unchanged. | Open Resource Usage and approved budget-configuration guidance. | Raise the limit, spend, downgrade quality, or Retry automatically. |
| Provider unavailable | NVIDIA video analysis is temporarily unavailable. No alternate provider or model was used. | Open model readiness/status; return later. A future explicit new action is allowed only through existing backend authority. | Fallback, automatic redispatch, label as credential failure, or promise a retry time. |
| Source configuration invalid | This Source cannot run until the identified setting is corrected. | Open Edit configuration with the invalid field identified and associated guidance. | Run with partial/guessed configuration or expose raw exceptions. |
| External outcome unconfirmed / AMBIGUOUS | The provider may have received this work, but the result cannot be confirmed. It will not be repeated. | View run/source details and Resource Usage; explain that future unrelated work remains possible under normal rules. | Retry, duplicate, reset, hide, or reinterpret the affected execution. |
| Decision required | The run is waiting for your decision about this Source. Existing Intelligence is unchanged. | Open the exact Source setting or decision context; user explicitly saves a choice. | Choose on the user's behalf, enable a Source/schedule, or start work automatically. |

Actions must be rendered only when the target screen/action exists and is legal.
“Open Settings,” “Review usage,” and “Edit Source” are navigation, not recovery
execution. A new Source Run after a prerequisite is resolved is a new explicit
action governed by existing identity/admission rules; it must never be described
as retrying the ambiguous execution.

### Acceptance criteria

- Each condition shows what happened, why it matters, what the user can do, and
  what the system will not do.
- Each safe action lands at the relevant section or field.
- No AMBIGUOUS item exposes Retry, Try again, Resume, or equivalent dispatch.
- Budget, credential, and provider gates remain independently testable with zero
  forbidden calls.
- Generic unknown conditions fail closed to View details, not a guessed action.

## UX-012 Resource Usage

### Accepted RC4 scope

**SHOULD:** Whenever cost is absent, render “Cost unavailable—this does not mean
the call was free.” Preserve calls, observed tokens, duration, provider, model,
budget state, and outcome without estimates.

**STRETCH:** Show the triggering Source and video using the `source_id` and
`video_id` already stored on the exact Distillation Resource Usage record. Use
authoritative local display names only. No inferred temporal match is allowed.

If implementation discovers that a row lacks a trustworthy existing link, omit
attribution for that row and keep it post-V1. This scope cannot justify a schema
change.

## Documentation Reconciliation

After verified RC4 behavior exists and before release:

- Update the Quick Start to use the supported production startup path and the
  external NVIDIA credential approach.
- Update the User Manual for readiness dimensions, manual-by-default new Source
  setup, Source Run stages/outcomes, safe recovery, and Resource Usage wording.
- Preserve the statement that saving a Source alone has no external side effect.
- Do not document STRETCH behavior unless it ships and passes acceptance.
- Do not modify historical RC3 review documents.

## External User Test

Run five moderated sessions after the hard MUST foundation is usable and before
finalizing inference-heavy P2 polish. Use one pilot participant, adjust only the
test script if necessary, then complete four sessions. Test comprehension,
readiness, credential guidance, starter Source configuration, Check Now
orientation, no-change/failure interpretation, Evidence verification, and safe
recovery. Do not measure raw model calls or use engagement dark patterns.

UX-003 and UX-004 may be narrowed only from observed evidence or an explicit PO
scope decision; the trust constraints cannot be relaxed by test preference.

## Migration Decision

**NO_MIGRATION.** Database version remains `16`; `m017` remains absent.

Current durable Source Run states, checkpoint events, child association,
distillation execution records, and Resource Usage Source/video fields are
sufficient. RC4 needs safe projections and presentation, not new authoritative
truth. If implementation proves otherwise, work stops and returns with
**PO_DECISION_REQUIRED** containing the missing invariant, ownership, backward-
compatibility plan, and trust impact.

## IA Decision

**UNCHANGED.** Keep the frozen top-level navigation, including Investigations.
The current non-executing explanation must remain truthful. The audit evidence
supports only a P3/low-frequency expectation cost, not an RC4 IA change.

Any proposal to hide, disable, rename, or remove Investigations is
**PO_DECISION_REQUIRED** and outside this freeze.

## RC4 Release Gate

A future RC4 candidate may be proposed only when:

- P0 = 0 and all accepted P1 findings = 0.
- UX-001 supported production startup and every readiness branch pass.
- UX-002 keyboard, focus, dialog-tree, and error association pass.
- Starter Source setup and explicit recurring-schedule consent pass.
- Source Run progress, leave/return orientation, all terminal outcomes, and
  recovery mapping pass without fabricated state.
- Evidence traceability, fail-closed reads, budget-before-dispatch, exact
  provider/model/capability authority, no fallback, at-most-once, and AMBIGUOUS
  no-retry regressions pass.
- One governed normal-production Source Run smoke passes with the exact NVIDIA
  NIM / Kimi K3 V1 tuple. No new qualification is required unless provider
  behavior or authority changes.
- Frontend/browser acceptance passes at 1440×900, 1280×800, and 768×900, plus
  the keyboard-only Source flow.
- The five-person moderated test is complete and accepted P2 decisions are
  recorded.
- Quick Start and User Manual match the candidate.
- DB remains version 16 with no `m017`, unless a separate PO-approved migration
  decision supersedes this freeze.
- Diff review shows no Deep Analysis, Investigation execution, V2, credential
  storage, hidden spending, provider fallback, or unrelated system change.

Testing should be proportionate: focused runtime, trust, browser, and real-smoke
evidence is required; unrelated frozen systems need not be requalified.

## Explicitly Rejected Scope

- Secure local credential storage without a separately approved security design.
- Automatic provider health calls, model calls for readiness, or trial calls to
  “verify” a key.
- Any action that changes a budget or schedule without explicit user confirmation.
- New progress tables, execution concepts, or `m017`.
- A Retry control for Source Run AMBIGUOUS or underlying unconfirmed execution.
- Fallback to OpenAI, Local, another NVIDIA model, or a different capability.
- Deep Analysis, Investigation execution, Evidence Expansion, Daily, Ask,
  TASK-016G, or any V2 functionality.
- New Save/Topic/Weekly semantics, broad IA change, broad visual redesign,
  telemetry, billing, or recommendation systems.
