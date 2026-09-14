# RC4 Acceptance Plan

## Purpose and Rules

This plan verifies the frozen RC4 product outcome without prescribing an
implementation. It authorizes no code, provider call, credential, migration,
push, tag, or release.

Use controlled local state for failure branches. A single governed real normal-
production smoke is required only at the release gate and must use the existing
exact NVIDIA NIM / `moonshotai/kimi-k3` / V1 Video Distillation authority. Never
print, record, screenshot, or persist the credential value.

For every scenario, observe UI, API-safe projections, durable state, and model-
transport call count where relevant. “No call” means zero model dispatches;
ordinary loopback UI requests are not model calls.

## A. First-Run Usability

- **PRECONDITION:** Fresh local product/runtime state; no Sources, Intelligence,
  Topics, Weekly, or unresolved Attention. Supported RC4 startup prerequisites
  are available.
- **USER ACTION:** Launch the supported product and open the Dashboard without
  repository knowledge.
- **EXPECTED UI:** Within five seconds, the user can state that the product
  watches relevant YouTube and creates traceable Intelligence; Dashboard shows
  readiness and a clear Add Source action.
- **EXPECTED BACKEND EFFECT:** Read-only readiness and empty-state projections;
  no Source, schedule, run, or provider execution is created.
- **FORBIDDEN EFFECT:** Automatic onboarding mutation, cloud enablement, Source
  creation, schedule creation, model call, or invented sample Intelligence.
- **PASS CRITERIA:** A target-user test participant correctly answers what the
  product does, whether it can run, the first action, and whether anything is
  blocking, without facilitator explanation.

## B. Production Readiness

- **PRECONDITION:** Controlled combinations of connected/disconnected local API,
  executor attached/absent, exact model authority available/unavailable,
  credential present/missing, budget allowed/blocked/indeterminate, and Source
  valid/disabled/absent.
- **USER ACTION:** Open Dashboard readiness, then Settings → Run readiness; select
  Check readiness where offered.
- **EXPECTED UI:** Local app, Source processing, model, credential, budget, and
  Source appear as independent dimensions. Overall summary names the current
  next step and exposes why. Indeterminate budget reads “Checked when work
  starts,” not Ready.
- **EXPECTED BACKEND EFFECT:** Safe inspection of existing runtime authorities;
  no credential value leaves the backend and no model dispatch occurs.
- **FORBIDDEN EFFECT:** Frontend-authored readiness, a false-green overall state,
  provider health/model calls solely for readiness, automatic config changes,
  or secret exposure.
- **PASS CRITERIA:** Every controlled combination maps to the frozen state model,
  and changing one gate does not incorrectly change another gate's label.

## C. Credential-Missing Flow

- **PRECONDITION:** Supported Source executor, provider authority, provider
  availability, valid enabled Source, and budget are present; NVIDIA credential
  is absent from the running process.
- **USER ACTION:** Inspect readiness and attempt Check Now.
- **EXPECTED UI:** Credential is “Setup required”; the message says no model
  request was sent and links to external setup instructions. After the user
  follows instructions and restarts, Check readiness can show Available without
  revealing the value.
- **EXPECTED BACKEND EFFECT:** The run/preflight fails or waits closed at the
  credential gate according to existing authority; model invocation count is 0.
- **FORBIDDEN EFFECT:** Credential input in the browser/API, secret logging,
  validation by speculative model call, fallback, automatic Retry, or budget
  consumption for a provider call.
- **PASS CRITERIA:** Zero model calls; safe presence-only status; recovery steps
  are complete enough for the target user and contain no real key.

## D. Budget-Blocked Flow

- **PRECONDITION:** All other readiness gates pass; authoritative budget denies
  the next exact execution.
- **USER ACTION:** Select Check Now and follow the displayed action.
- **EXPECTED UI:** “Usage limit reached” is distinct from credential/provider
  failure; copy says processing stopped before a model request and links to
  Resource Usage and approved budget guidance.
- **EXPECTED BACKEND EFFECT:** Budget denial is recorded/projected through the
  existing legal state; invocation count is 0.
- **FORBIDDEN EFFECT:** Credential resolution before the budget gate, model call,
  automatic budget increase, quality downgrade, fallback, or automatic Retry.
- **PASS CRITERIA:** Zero model calls and credential accesses where instrumented;
  UI identifies budget as the sole blocking dimension and provides no spend-
  increasing action without explicit external configuration.

## E. Provider-Unavailable Flow

- **PRECONDITION:** Exact provider/model/capability authority, credential, budget,
  executor, and Source are otherwise ready; NVIDIA is authoritatively marked
  unavailable before dispatch.
- **USER ACTION:** Inspect readiness and select Check Now.
- **EXPECTED UI:** Video analysis is “Temporarily unavailable”; copy states that
  no alternative provider/model was used and offers model-status/details.
- **EXPECTED BACKEND EFFECT:** Existing model-unavailable/Needs Attention state
  is persisted or projected; invocation count is 0.
- **FORBIDDEN EFFECT:** OpenAI/Local/other NVIDIA fallback, credential error label,
  fabricated recovery time, background retry, or hidden quality reduction.
- **PASS CRITERIA:** Zero model calls; exact independent provider state is shown;
  existing trusted content remains readable.

## F. AMBIGUOUS Safe Behavior

- **PRECONDITION:** A controlled existing Source Run has a durable ambiguous
  external outcome created through the authorized test seam; no real duplicate
  call is needed.
- **USER ACTION:** Open Dashboard blocker, Source Run details, and Resource Usage;
  reload and restart the local service; inspect every action.
- **EXPECTED UI:** The UI says the provider may have received the work, the
  result cannot be confirmed, and the affected work will not be repeated.
  Available actions are view/details navigation only.
- **EXPECTED BACKEND EFFECT:** The same durable AMBIGUOUS execution/run remains
  terminal across reload/restart; additional invocation count is 0.
- **FORBIDDEN EFFECT:** Retry, Try again, Resume, reset, redispatch, new execution
  for the same affected identity, fallback, or reinterpretation as success/fail.
- **PASS CRITERIA:** No dispatch-capable control is present; repeated reads and
  resume attempts create zero additional invocations and preserve identity.

## G. Source Configuration Keyboard Accessibility

- **PRECONDITION:** Dashboard/Sources loaded with one existing Source and one Add
  Source entry; keyboard and accessibility-tree inspection available.
- **USER ACTION:** Keyboard-only open Add Source, traverse forward/backward,
  submit an error, correct it, save/cancel; then open Source Detail → Edit
  configuration and repeat, including Escape.
- **EXPECTED UI:** One named active dialog is exposed; initial focus is inside;
  Tab/Shift+Tab remain contained; focus is visible; errors are associated and
  announced; Escape closes only the top dialog and focus returns to its trigger.
- **EXPECTED BACKEND EFFECT:** No mutation on cancel; exactly the intended Source,
  policy, and optional schedule writes on successful save.
- **FORBIDDEN EFFECT:** Focus/background interaction behind the dialog, two
  actionable modal trees, lost focus, silent error, double submit, or mutation
  from dismissal.
- **PASS CRITERIA:** Entire Add/Edit flow completes without pointer input at all
  three viewports; accessibility-tree and focus-restoration assertions pass.

## H. Starter Source Setup

- **PRECONDITION:** Fresh state; readiness may be ready or safely blocked; no
  Sources exist.
- **USER ACTION:** Choose Add Source, enter one valid YouTube URL, review the
  recommended summary, and save without opening Customize.
- **EXPECTED UI:** The summary shows Standard Intelligence, monitoring on,
  Initial History 5, Per-run Limit 5, Balanced style, and Manual/no automatic
  schedule; copy says saving does not run the Source.
- **EXPECTED BACKEND EFFECT:** One normalized Source plus its existing policy is
  persisted. No automatic schedule and no Source Run/provider call is created.
- **FORBIDDEN EFFECT:** Daily schedule default, implicit Check Now, discovery,
  model call, cloud/spending enablement, or hidden work-volume limits.
- **PASS CRITERIA:** One-URL path succeeds; persisted policy matches the summary;
  schedules = 0; Source Runs = 0; model invocations = 0.

## I. Advanced Source Settings Discovery

- **PRECONDITION:** Add Source is open or an existing Source Detail is available.
- **USER ACTION:** Find Customize/Edit configuration; inspect and change
  processing level, monitoring, Initial History, Per-run Limit, style, Focus,
  Ignore, and optional schedule.
- **EXPECTED UI:** Every existing setting is discoverable and explained; Initial
  History and Per-run Limit are distinguishable; selecting Daily/Weekly reveals
  cadence/time and cloud/resource notice before confirmation.
- **EXPECTED BACKEND EFFECT:** Only explicitly saved policy/source/schedule values
  change; existing Source history and Intelligence remain unchanged.
- **FORBIDDEN EFFECT:** Silent schedule creation, Source check, data deletion,
  implicit budget change, or semantics differing from rc.3 contracts.
- **PASS CRITERIA:** A target user predicts the effect of each changed setting;
  automatic schedule exists only after explicit selection and confirmation.

## J. Check Now Progress

- **PRECONDITION:** One valid enabled manual Source; all readiness gates pass;
  controlled backend can pause at each existing checkpoint.
- **USER ACTION:** Select Check Now and observe the run from queue through each
  checkpoint and terminal state.
- **EXPECTED UI:** Immediate durable acknowledgement with run identity/context;
  named stages map to existing queue/state/checkpoint facts; no percentage or
  estimated completion time.
- **EXPECTED BACKEND EFFECT:** One durable manual Source Run is enqueued under the
  existing command identity and progresses through legal checkpoints only.
- **FORBIDDEN EFFECT:** Duplicate run from double response handling, invented
  state, skipped checkpoint, model call before gates, or Check Now described as
  Retry.
- **PASS CRITERIA:** Every displayed stage is supported by the current persisted
  state; one user action creates at most one admitted run identity.

## K. Leave-and-Return Progress Orientation

- **PRECONDITION:** A Source Run is queued/running and deliberately paused at a
  persisted checkpoint.
- **USER ACTION:** Navigate to Intelligence/Settings, return to Source Detail,
  reload the browser, restart the API process, then return again.
- **EXPECTED UI:** The same Source Run, current stage, start/update time, and next
  expectation are restored; terminal runs remain terminal.
- **EXPECTED BACKEND EFFECT:** Reads and restart-safe resume use existing durable
  state; no duplicate reservation or dispatch.
- **FORBIDDEN EFFECT:** Reset to generic “accepted,” duplicate run, hidden
  AMBIGUOUS, fabricated continuity, or process-memory-only orientation.
- **PASS CRITERIA:** Run identity and checkpoint-derived stage remain stable
  across navigation, reload, and process restart; invocation count does not
  increase merely from viewing.

## L. Completion With Intelligence

- **PRECONDITION:** Controlled eligible Source produces one or more trusted,
  admitted Intelligence items with verified Evidence.
- **USER ACTION:** Follow Source Run to completion, then open the produced item.
- **EXPECTED UI:** Terminal state says Complete and gives the exact new
  Intelligence count; direct navigation reaches current trusted Intelligence.
- **EXPECTED BACKEND EFFECT:** Existing finalization, trusted admission, and
  Source/Intelligence projections complete atomically according to current
  contracts.
- **FORBIDDEN EFFECT:** Completion before finalization, untrusted card, stale
  Saved fallback, fabricated count, or Evidence omission.
- **PASS CRITERIA:** Displayed count equals authoritative admitted items and each
  opened card passes Evidence acceptance scenario P.

## M. Completion With No Important Change

- **PRECONDITION:** Controlled Source Run legally completes with zero newly
  admitted Intelligence items (for example no eligible new videos or all safely
  skipped).
- **USER ACTION:** Follow the run to completion and inspect Dashboard/Source.
- **EXPECTED UI:** “Complete — no important change found” or equivalent confident
  truthful absence; skipped/no-new-video context is reachable without filler.
- **EXPECTED BACKEND EFFECT:** Source Run finalizes through existing checkpoints;
  Intelligence count remains zero.
- **FORBIDDEN EFFECT:** Fake Intelligence, model call merely to fill the page,
  failure label, or ambiguous “nothing happened” state.
- **PASS CRITERIA:** Terminal outcome is clearly distinguishable from failure and
  exactly matches zero authoritative admissions.

## N. Safe Failure and Recovery

- **PRECONDITION:** Controlled Source configuration invalid, decision-required,
  partial, and failed-final conditions, one at a time.
- **USER ACTION:** Open Needs Attention/Source detail and follow the offered safe
  action; correct an editable configuration case explicitly.
- **EXPECTED UI:** Each condition states what happened, impact on existing data,
  user action, and what the system will not do. Unknown cases offer View details
  only.
- **EXPECTED BACKEND EFFECT:** Navigation is read-only; explicit valid Source edit
  changes only intended configuration. A later Check Now is a new governed
  action, not a retry of old work.
- **FORBIDDEN EFFECT:** Raw exception disclosure, guessed fix, automatic config
  mutation, retry, fallback, stale trusted content, or status erasure.
- **PASS CRITERIA:** Recovery reaches the correct field/section; forbidden call
  count is zero; old run history remains unchanged.

## O. Dashboard Blocking Priority

- **PRECONDITION:** Test separately with no blockers, one current blocker, many
  blockers, and historical/non-blocking attention; include populated
  Intelligence/Topic/Weekly data.
- **USER ACTION:** Open Dashboard and identify what matters and any blocker.
- **EXPECTED UI:** Healthy state begins with What matters now. A current blocker
  produces one compact summary above it with safe action/count; non-blocking
  attention remains below value content.
- **EXPECTED BACKEND EFFECT:** Read-only Dashboard projection; blocker
  classification derives from current backend readiness/run facts.
- **FORBIDDEN EFFECT:** Permanent warning-first layout, duplicate warning cards,
  historical issues treated as current blockers, hidden Intelligence, or direct
  recovery execution from rendering.
- **PASS CRITERIA:** In five-second testing the user identifies both current
  value and current blocker correctly; healthy state has no blocker banner.

## P. Evidence Traceability

- **PRECONDITION:** One available trusted Intelligence item with verified timed
  Evidence and one fail-closed/unavailable item.
- **USER ACTION:** Read the available card, open Evidence, timestamp, original
  Source, and technical provenance; then inspect the unavailable item.
- **EXPECTED UI:** Source → Video → exact time range → verified excerpt is clear;
  Open Source reaches the timestamped original where supported; technical IDs
  remain secondary; unavailable content shows no stale claim.
- **EXPECTED BACKEND EFFECT:** Only authoritative trusted readers/projections are
  used; viewing may open the external source by explicit user action.
- **FORBIDDEN EFFECT:** Unbound/fabricated excerpt, source-less claim, stale
  fallback, changed claim kind, or automatic external navigation.
- **PASS CRITERIA:** User can identify origin and reach source context within two
  intentional actions; unavailable item remains fail-closed.

## Q. Resource Usage (If Included)

- **PRECONDITION:** Rows with observed tokens/cost, null cost, zero calls, one
  exact Source/video link, and one row without a resolvable display label.
- **USER ACTION:** Open Settings → Resource Usage and inspect each row.
- **EXPECTED UI:** Calls, observed tokens, duration, provider/model, status, and
  budget/outcome remain truthful. Null cost says it is unavailable and does not
  mean free. If STRETCH attribution ships, it uses exact persisted Source/video
  identity; unresolved labels are omitted safely.
- **EXPECTED BACKEND EFFECT:** Read-only projection of existing Resource Usage and
  exact associated Source/video fields.
- **FORBIDDEN EFFECT:** Estimated cost, zero substitution, temporal/title-based
  inferred attribution, migration, secret/payload/excerpt exposure, or a claim
  that no row means no provider usage outside the ledger's scope.
- **PASS CRITERIA:** Null and zero are visibly different; every displayed
  attribution matches exact authoritative IDs; rows without truth do not invent
  it.

## R. 1440×900

- **PRECONDITION:** First-run, populated, blocking, Source form, long Source name,
  progress, Needs Attention, Evidence, and Resource Usage states.
- **USER ACTION:** Complete the first-run path and inspect each changed surface at
  1440×900.
- **EXPECTED UI:** Primary action, readiness, first value, modal controls, status,
  and Evidence are visible and ordered; no horizontal overflow.
- **EXPECTED BACKEND EFFECT:** Only effects from the scenario's explicit actions.
- **FORBIDDEN EFFECT:** Viewport-specific hidden action, clipped focus ring,
  unreadable wrapping, or warning wall.
- **PASS CRITERIA:** Automated dimensions/overflow checks and manual visual review
  pass with zero console errors and no unexpected external frontend requests.

## S. 1280×800

- **PRECONDITION:** Same representative states as scenario R.
- **USER ACTION:** Repeat the key first-run, Source, progress, and recovery paths
  at 1280×800.
- **EXPECTED UI:** Compact blocker plus first Intelligence conclusion remain
  orienting; dialogs fit or scroll internally without losing heading/actions;
  long content wraps.
- **EXPECTED BACKEND EFFECT:** Same as the corresponding functional scenario.
- **FORBIDDEN EFFECT:** Hidden submit/cancel controls, background page scroll
  stealing focus, overlap, clipping, or horizontal overflow.
- **PASS CRITERIA:** All actions remain reachable by pointer and keyboard; no
  horizontal overflow or unexpected console/network errors.

## T. 768×900

- **PRECONDITION:** Same representative states as scenario R, including the
  longest safe Evidence excerpt and technical disclosure.
- **USER ACTION:** Repeat first-run, Add/Edit Source, Check Now, return, recovery,
  and Evidence verification at 768×900.
- **EXPECTED UI:** Single-column hierarchy; blocker/action and value content are
  easy to find; fields/buttons meet clear target boundaries; modal and long text
  scroll/wrap without loss.
- **EXPECTED BACKEND EFFECT:** Same as the corresponding functional scenario.
- **FORBIDDEN EFFECT:** Blank first viewport, horizontal overflow, off-screen
  trapped actions, truncated status/evidence, or reliance on hover.
- **PASS CRITERIA:** Complete user journey succeeds without resizing; no
  horizontal overflow, console error, or unexpected external frontend request.

## U. Keyboard-Only Path

- **PRECONDITION:** Fresh state through one completed Source Run, with a
  recoverable Needs Attention case available; pointer unused.
- **USER ACTION:** Navigate primary IA, inspect readiness, add Source, customize,
  save, Check Now, leave/return, open Intelligence/Evidence, and follow a safe
  recovery action using keyboard only.
- **EXPECTED UI:** Logical focus order, visible focus, clear accessible names,
  operable disclosures, no focus loss, and correct modal containment/restoration.
- **EXPECTED BACKEND EFFECT:** Same explicit writes/execution as pointer flow;
  focus/navigation alone is read-only.
- **FORBIDDEN EFFECT:** Keyboard trap outside intended modal containment,
  background interaction, unlabeled repeated action that prevents
  identification, or keyboard-only semantic difference.
- **PASS CRITERIA:** End-to-end task completes without pointer input. This is a
  bounded RC4 accessibility acceptance, not a claim of WCAG certification.

## V. Documentation Reconciliation

- **PRECONDITION:** RC4 implementation and functional/browser acceptance are
  complete; exact shipped startup and UI copy are known.
- **USER ACTION:** Follow the Quick Start from a fresh target-user environment,
  then use the Manual for each changed readiness, Source, progress, recovery,
  cost, and troubleshooting behavior.
- **EXPECTED UI:** Product behavior and documented labels/actions match; links
  point to the correct sections; no future capability is presented as current.
- **EXPECTED BACKEND EFFECT:** Only actions explicitly described by the guide;
  saving a Source remains local, and provider work occurs only after explicit
  governed Check Now/schedule execution.
- **FORBIDDEN EFFECT:** Real credential examples, secrets, internal task IDs in
  ordinary guidance, Deep Analysis/Investigation/V2 claims, stale rc.3 guarded-
  startup instructions, copyrighted transcript dumps, or undocumented spend.
- **PASS CRITERIA:** Documentation walkthrough succeeds; content/security scan
  finds no secrets/private data/transcript dump; all shipped and unavailable
  capability statements match the candidate.

## Release-Level Cross-Checks

- P0 = 0; accepted P1 = 0.
- Database remains version 16 and `m017` is absent.
- Source modal accessibility passes.
- First-run readiness and starter Source path pass.
- Source Run progress/recovery and AMBIGUOUS no-retry pass.
- Evidence and fail-closed regressions pass.
- Exact normal-production smoke passes once under separate existing authority;
  no new provider qualification unless provider behavior changes.
- Browser acceptance passes at all three frozen viewports.
- Five-person moderated test is complete before P2 scope is finally accepted.
- Quick Start and User Manual are reconciled before release.
