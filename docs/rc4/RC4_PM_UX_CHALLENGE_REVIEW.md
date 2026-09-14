# RC4 PM/UX Challenge Review

## Executive Decision

**Overall Product Owner plan decision: AGREE_WITH_MODIFICATION.**

The Product Owner is correct that rc.3 should not enter a broader, self-guided
private trial. The standard loopback startup cannot execute `Check Now`, and
the Source edit dialog has a verified keyboard-accessibility failure. Those are
real P1 barriers, not polish.

The proposal is too aggressive in treating progressive disclosure (UX-003) as
a third P1 and in committing to all P2 changes before external observation. It
is too conservative in omitting bounded Source URL error guidance (UX-005),
which sits directly in the first-run path. RC4 should repair the hard execution
and accessibility failures, expose truthful existing run state, then test the
onboarding and Dashboard hypotheses before broadening their designs.

**RC4_REQUIRED_BEFORE_BROADER_TRIAL: AGREE_WITH_MODIFICATION.** A small,
moderated, operator-assisted formative study can use rc.3 or an early RC4
candidate before all P2 work. A self-guided or broader private trial must wait
until the accepted RC4 release gates pass.

## Answers to the Required Challenges

### A. Fix before test or test before fix?

RC4 is required before a broader, self-guided private trial. rc.3 may be used in
a small moderated formative session where an operator provides a production-
ready environment and the facilitator explicitly avoids treating setup failure
as a usability discovery. Fix UX-001/002 and the minimum run/recovery loop before
the main five-person task test; test UX-003/004 before broad polish is finalized.

### B. Are UX-001, UX-002, and UX-003 the correct three P1 blockers?

No. UX-001 and UX-002 are verified P1s. UX-003 remains a high-impact P2: users
can complete the form, but with unnecessary decisions. No audit P2 has enough
evidence to be reclassified globally as P1. The minimum UX-006 feedback contract
is nevertheless a MUST acceptance dependency of the repaired core journey.
UX-005, a small first-run validation gap, was omitted from the PO plan and enters
SHOULD.

### C. Should progressive disclosure be RC4 scope?

Yes, only as a bounded SHOULD: one required URL, a visible recommended-settings
summary, and a Customize path. A wizard or deeper restructuring should wait for
external behavior evidence. Limits and schedule implications cannot be hidden.

### D. Should Dashboard priority change now?

Only conditionally. A compact current blocker should rise above Intelligence;
the product should not adopt a permanent warning-first hierarchy. Full card
compaction and a broader reorder wait for user evidence.

### E. Does Source Run progress require durable backend state?

No new durable state is required. rc.3 already persists top-level run state,
eight ordered checkpoints, child outcomes, exact distillation execution links,
and restart-safe identity. RC4 requires a **BOUNDED_BACKEND_PROJECTION** plus UI
refresh/polling. `m017` is neither needed nor authorized.

### F. Can direct recovery remain safe?

Yes, if “direct” means navigation to the authoritative setting/detail and an
explicit user edit. It must not mean Retry, automatic resume, budget increase,
provider fallback, or credential entry. AMBIGUOUS receives view-only actions.

### G. Is UX-012 useful enough for RC4?

Split it. The sentence “cost unavailable does not mean free” is SHOULD. Source/
video attribution is STRETCH because it is useful but not a first-run blocker;
it is allowed only from existing persisted fields. Any need for new linkage
defers the attribution.

### H. Is Investigations navigation actively harmful?

Not on current evidence. It creates a P3 expectation cost, but the page is
truthfully non-executing and frozen IA anticipates it. Leave it unchanged in
RC4. Hiding, disabling, renaming, or removing it requires a separate PO decision.

### I. Does ordinary-user readiness require in-app credential management?

No. For the defined private-RC target, guided external/local secret setup plus
safe presence detection is acceptable. In-app storage would create a new
security subsystem and is explicitly deferred.

### J. Does rc.3 have a viable non-technical first-run path?

It has a viable operator-assisted consumption/configuration path, not a viable
self-guided production path. “Ordinary user” for this RC is an AI-comfortable
knowledge worker able to run one documented local command and configure an
environment variable, but unable and not expected to compose runtime adapters
or understand repository architecture. A mass-market non-technical consumer is
outside the RC4 target.

## Product Owner Proposal Challenge Matrix

| Proposal | PO position | Codex decision | Rationale | Evidence | Recommended change to PO plan | PO decision required |
| --- | --- | --- | --- | --- | --- | --- |
| RC4 required before broader trial | Required | AGREE_WITH_MODIFICATION | The P1 execution and dialog defects block self-guided use, but formative moderated testing can precede P2 polish. | RC3 audit §§Executive Summary, First-Time User Journey; UX-001/002 | Block broader trial; permit a bounded formative test after hard prerequisites are usable. | NO |
| UX-001 | Mandatory | AGREE_WITH_MODIFICATION | The problem is P1, but the boundary is a supported production composition plus readiness projection—not a credential vault or general installer. | Standard `serve-api` creates `ProductOrchestrationService(repository)` without a Source Run submitter; rc.3 Quick Start documents the guard. | Make bounded production startup and independent readiness checks MUST. | NO |
| UX-002 | Mandatory | AGREE | The nested editor was absent from the accessibility tree; Tab escaped behind it and Escape did not close it. | RC3 audit, Source and accessibility sections; current nested dialogs have no focus lifecycle handling. | Keep as a concrete MUST with browser and accessibility-tree acceptance. | NO |
| UX-003 | Mandatory | AGREE_WITH_MODIFICATION | The audit rated it P2, and one expert review is not enough to freeze a broad redesign. The underlying first-run decision load is real. | Source form exposes processing, monitoring, history, limit, focus, ignore, style, schedule, time, and schedule enablement together. | Make a bounded starter-settings path SHOULD, preserve visible cost controls, and validate it with users. | NO |
| UX-004 | High-value RC4 | AGREE_WITH_MODIFICATION | Blocking attention can be hidden below long cards, but a warning-first Dashboard would regress the product's intelligence-first value. | Current Dashboard renders full Intelligence, Topics, Weekly, then Attention. | Add only a conditional compact blocker summary; defer full card compaction/hierarchy redesign until testing. | NO |
| UX-006 | High-value RC4 | AGREE_WITH_MODIFICATION | It is necessary to complete the first-run loop, but no new durable state is needed. | Durable `SourceRunState`, checkpoint events, child state, and restart-safe resume already exist; current API omits checkpoint progress. | Make the minimum truthful run projection MUST; classify as BOUNDED_BACKEND_PROJECTION; no migration. | NO |
| UX-011 | High-value RC4 | AGREE_WITH_MODIFICATION | Direct navigation is useful; generic Retry or automatic recovery would violate trust contracts. | Current copy is safe but has no direct action; AMBIGUOUS is durable and non-redispatchable. | Add condition-specific view/navigation actions only; explicitly forbid Retry for ambiguous outcomes. | NO |
| UX-012 | Optional/stretch | AGREE_WITH_MODIFICATION | Unknown-cost explanation is small and valuable; attribution is safe only from existing records. | UI says “Unavailable”; ledger record already contains Source/video IDs but DTO omits them. | Put plain-language UNKNOWN cost copy in SHOULD; make existing-record attribution STRETCH; no inferred joins or migration. | NO |
| Save defer | Defer | AGREE | The mental-model issue is meaningful but does not block first value or trust. | UX-009 is P2/medium frequency; fail-closed unavailable behavior is already correct. | Defer semantic expansion; preserve fail-closed reads. | NO |
| Topic defer | Defer | AGREE | Deeper evolution/disagreement is valuable but large and not a first-run blocker. | UX-010 is P2/L; current page preserves evidence, uncertainty, and disagreement. | Defer new semantics; preserve current truthful states. | NO |
| Broad provenance translation defer | Defer | AGREE_WITH_MODIFICATION | Broad translation can wait, but readiness and recovery copy in RC4 must be ordinary-user language. | Technical provenance is already secondary; UX-015 is P3. | Defer broad work; require plain language only in changed RC4 surfaces. | NO |
| Investigations defer | Defer capability and IA redesign | AGREE | The current empty explanation is a low-frequency P3 expectation cost, not evidence of active harm. | Frozen IA explicitly reserves a non-executing V1 Investigations explanation; audit rated UX-013 P3/low. | Leave navigation and capability unchanged in RC4. | NO |
| Five-user test timing | After all RC4 fixes | AGREE_WITH_MODIFICATION | Testing only after all P2 designs are committed risks overfitting one expert review. | UX-003/004 are inference-heavy P2 findings; UX-001/002 are mechanically verified P1s. | Repair hard blockers, run the moderated test before final P2 decisions, then finish RC4 and verify. | NO |
| Documentation reconciliation | After RC4 | AGREE | Startup, readiness, onboarding, progress, and recovery guidance will change. | Current manual correctly documents rc.3's guarded startup limitation. | Reconcile Quick Start and Manual against implemented RC4 before release. | NO |

## Detailed Proposal Decisions

### RC4 required before broader private trial

- **PO_PROPOSAL:** RC4 is required before broader private trial.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** The standard rc.3 `serve-api` path constructs an orchestration
  service without a Source Run submitter, so `Check Now` is guarded. The RC3
  audit also reproduced a keyboard trap/escape failure in Source editing.
- **PRODUCT_REASONING:** A broader self-guided trial would mostly measure setup
  failure, not the value of video distillation. A moderated formative session
  can still test language, hierarchy, and expectations without pretending the
  product is self-service.
- **USER_IMPACT:** Self-guided users cannot reliably reach first Intelligence;
  moderated users can still provide evidence about the P2 hypotheses.
- **RISK_IF_ACCEPTED:** Waiting for every P2 change before any testing could
  overfit the expert audit.
- **RISK_IF_REJECTED:** A broader rc.3 trial would create predictable failure,
  support burden, and low-quality product feedback.
- **RECOMMENDED_BOUNDARY:** Fix UX-001, UX-002, and the minimum truthful
  UX-006/011 loop before unassisted testing. Test before finalizing broader
  UX-003/004 polish.
- **CONFIDENCE:** HIGH.

### UX-001 — Ordinary-user production execution and readiness

- **PO_PROPOSAL:** Mandatory RC4 item.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** The UI can save Sources, but the supported standard API startup
  returns a runtime-side-effect guard for `Check Now`. Settings statically marks
  the qualified model as available without proving that the running process has
  an executor, credential, or admissible budget.
- **PRODUCT_REASONING:** The product needs one supported production composition
  and backend-derived readiness dimensions. It does not need to own secrets or
  collapse independent gates into one “Ready” badge.
- **USER_IMPACT:** The target user can tell what is missing and complete an
  approved setup path without learning repository architecture.
- **RISK_IF_ACCEPTED:** Unbounded wording could become an installer, credential
  subsystem, or false readiness signal.
- **RISK_IF_REJECTED:** The core value remains unreachable through the normal UI.
- **RECOMMENDED_BOUNDARY:** Supported Mac-first local startup; safe detection of
  local service, executor, exact model authority, credential presence, provider
  availability, budget status, and Source validity; no secret entry/storage.
- **CONFIDENCE:** HIGH.

### UX-002 — Source dialog accessibility

- **PO_PROPOSAL:** Mandatory RC4 item.
- **YOUR_DECISION:** AGREE.
- **EVIDENCE:** In the rc.3 browser review the nested Edit Source dialog was
  missing from the accessibility tree; focus moved behind it and Escape failed.
  Source Detail and SourceForm are simultaneously rendered as modal dialogs and
  contain no focus containment/restoration behavior.
- **PRODUCT_REASONING:** Keyboard operation is a baseline interaction contract,
  not a visual preference.
- **USER_IMPACT:** Keyboard and assistive-technology users cannot safely complete
  a core configuration task.
- **RISK_IF_ACCEPTED:** A library rewrite could expand scope if acceptance is not
  behavior-based.
- **RISK_IF_REJECTED:** A known P1 remains in the first-run path.
- **RECOMMENDED_BOUNDARY:** Fix semantics and focus lifecycle for this flow only;
  do not authorize a design-system rewrite.
- **CONFIDENCE:** HIGH.

### UX-003 — Progressive Source onboarding

- **PO_PROPOSAL:** Mandatory RC4 item and one of three P1 blockers.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** The form presents approximately ten decisions at once, but the
  independent audit classified the issue P2, not P1. Users can save a Source
  with existing defaults.
- **PRODUCT_REASONING:** Decision reduction is warranted, but progressive
  disclosure is a design hypothesis. The safest thin solution is a visible
  recommended-settings summary plus Customize, not a broad onboarding wizard.
- **USER_IMPACT:** New users can add a Source with one required input while cost-
  relevant limits remain visible.
- **RISK_IF_ACCEPTED:** Hiding schedule or limits could obscure cloud work and
  spending; changing too much before testing could optimize the wrong fields.
- **RISK_IF_REJECTED:** New users face unnecessary choices before first value.
- **RECOMMENDED_BOUNDARY:** SHOULD, not P1/MUST. Default new Sources to manual
  execution, preserve existing Sources, show the 5-video initial/per-run limits
  and Balanced style in the summary, and make automatic schedules explicit.
- **CONFIDENCE:** MEDIUM.

### UX-004 — Dashboard priority

- **PO_PROPOSAL:** High-value RC4 hierarchy led by blocking Attention.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** Current Dashboard puts full Evidence-heavy Intelligence cards
  before Attention; on a narrow viewport one card can occupy most of the screen.
  It otherwise correctly leads with “What matters now.”
- **PRODUCT_REASONING:** Only a blocker that prevents requested or scheduled work
  should rise above Intelligence. A permanent warning-first order would make the
  product feel operational again.
- **USER_IMPACT:** Users see a real blocker promptly without losing the product's
  intelligence-first orientation.
- **RISK_IF_ACCEPTED:** Attention fatigue and regression to an admin dashboard.
- **RISK_IF_REJECTED:** Users may miss a blocker below long content.
- **RECOMMENDED_BOUNDARY:** Conditional compact blocker summary; non-blocking
  Attention remains after value content; defer card compaction pending testing.
- **CONFIDENCE:** MEDIUM.

### UX-006 — Persistent Source Run feedback

- **PO_PROPOSAL:** High-value RC4 item.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** SQLite already stores `QUEUED`, `RUNNING`, `WAITING`, `PARTIAL`,
  `NEEDS_ATTENTION`, `COMPLETED`, `FAILED`, `AMBIGUOUS`, and `CANCELLED`, eight
  ordered checkpoints, child outcomes, and restart-safe identities. The current
  API Source Run DTO exposes only the top-level state and attention reason.
- **PRODUCT_REASONING:** The gap is projection and presentation. A new progress
  table or percentage would duplicate truth and create migration risk.
- **USER_IMPACT:** Users can leave and return while retaining orientation.
- **RISK_IF_ACCEPTED:** Invented phases or percentages could lie; unbounded scope
  could create `m017`.
- **RISK_IF_REJECTED:** `Check Now` still feels like an opaque acknowledgement.
- **RECOMMENDED_BOUNDARY:** MUST as a bounded backend projection over current
  durable state; show named phases and terminal outcomes without percentages.
- **CONFIDENCE:** HIGH.

### UX-011 — Direct recovery actions

- **PO_PROPOSAL:** High-value RC4 item.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** Current copy explains impact and next area but renders no direct
  action. Existing AMBIGUOUS records are terminal and cannot be redispatched.
- **PRODUCT_REASONING:** “Direct” should mean taking the user to the authoritative
  place to inspect or change a prerequisite, not performing a retry.
- **USER_IMPACT:** Recovery takes fewer navigation guesses while preserving safe
  behavior.
- **RISK_IF_ACCEPTED:** A generic Retry or one-click budget/provider bypass would
  violate at-most-once and spending controls.
- **RISK_IF_REJECTED:** Users understand the problem but may not resolve it.
- **RECOMMENDED_BOUNDARY:** Finite condition-to-message/action mapping; navigation
  and explicit prerequisite changes only; no retry for AMBIGUOUS.
- **CONFIDENCE:** HIGH.

### UX-012 — Resource Usage

- **PO_PROPOSAL:** Optional/stretch RC4 item.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** The record already includes Source ID, video ID, provider/model,
  calls, tokens, duration, and nullable cost; the API DTO omits Source/video.
  The UI renders nullable cost as “Unavailable” without saying that this does
  not mean free.
- **PRODUCT_REASONING:** Truthful copy is cheap and broadly useful. Human-readable
  attribution is bounded only when built from existing authoritative IDs.
- **USER_IMPACT:** Users can interpret missing cost and, if included, connect a
  row to the work that caused it.
- **RISK_IF_ACCEPTED:** Inferred attribution or estimated cost would mislead.
- **RISK_IF_REJECTED:** Power users cannot audit spend context; normal users may
  read unavailable cost as zero.
- **RECOMMENDED_BOUNDARY:** UNKNOWN explanation SHOULD; existing-record Source/
  video attribution STRETCH; no estimation and no migration.
- **CONFIDENCE:** HIGH.

### Save mental-model expansion defer

- **PO_PROPOSAL:** Defer Save mental-model expansion.
- **YOUR_DECISION:** AGREE.
- **EVIDENCE:** UX-009 is P2 with medium frequency/impact; current Saved behavior
  remains fail-closed when trusted content becomes unavailable.
- **PRODUCT_REASONING:** Defining Save as bookmark, reference, or knowledge-base
  input is a repeat-use product decision, not a first-run repair.
- **USER_IMPACT:** Current bookmarking remains usable; no stale content is added.
- **RISK_IF_ACCEPTED:** Pulling it into RC4 would expand semantics and testing.
- **RISK_IF_REJECTED:** The label remains somewhat ambiguous for repeat users.
- **RECOMMENDED_BOUNDARY:** Defer semantic expansion; preserve fail-closed reads
  and document Save's current behavior.
- **CONFIDENCE:** HIGH.

### Topic evolution/disagreement deepening defer

- **PO_PROPOSAL:** Defer Topic evolution and disagreement deepening.
- **YOUR_DECISION:** AGREE.
- **EVIDENCE:** UX-010 is P2/L; rc.3 already exposes current understanding,
  Evidence, timeline, single-source uncertainty, and disagreement states.
- **PRODUCT_REASONING:** Better synthesis needs product-model work and long-term
  accumulated data; it does not determine first-run production readiness.
- **USER_IMPACT:** Existing truthful Topic states remain available but shallow.
- **RISK_IF_ACCEPTED:** RC4 becomes a Topic redesign with unclear user evidence.
- **RISK_IF_REJECTED:** Returning-user value improves later, not in this repair.
- **RECOMMENDED_BOUNDARY:** Defer new semantics and preserve all existing
  uncertainty/disagreement truth.
- **CONFIDENCE:** HIGH.

### Broad provenance terminology translation defer

- **PO_PROPOSAL:** Defer broad provenance terminology translation.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** UX-015 is P3; current internal IDs are already secondary behind
  human Source, video, timestamp, and excerpt. RC4 introduces new readiness and
  recovery concepts that must be understandable without runtime vocabulary.
- **PRODUCT_REASONING:** Broad translation is not urgent, but newly changed RC4
  surfaces cannot expose raw enums or architecture as an excuse for deferral.
- **USER_IMPACT:** Trust details remain reachable while first-run guidance stays
  readable.
- **RISK_IF_ACCEPTED:** Deferring all language work would make readiness technical.
- **RISK_IF_REJECTED:** A broad copy rewrite adds churn without solving a blocker.
- **RECOMMENDED_BOUNDARY:** Defer existing provenance redesign; require plain
  language on every changed RC4 surface.
- **CONFIDENCE:** HIGH.

### Investigations capability and IA defer

- **PO_PROPOSAL:** Defer Investigations capability and IA redesign.
- **YOUR_DECISION:** AGREE.
- **EVIDENCE:** The frozen IA explicitly reserves a V1 non-executing explanation;
  the audit rated its expectation cost P3/low frequency and found no execution
  affordance that falsely performs work.
- **PRODUCT_REASONING:** Current evidence does not justify reopening frozen IA,
  and capability implementation would be V2 leakage.
- **USER_IMPACT:** A small expectation cost remains; no unavailable capability is
  falsely enabled.
- **RISK_IF_ACCEPTED:** Changing navigation creates historical-contract and scope
  churn or accidentally markets unavailable work.
- **RISK_IF_REJECTED:** The top-level item remains more prominent than its current
  utility.
- **RECOMMENDED_BOUNDARY:** Leave navigation and explanation unchanged in RC4.
  Any hide/disable/rename proposal is a separate PO decision.
- **CONFIDENCE:** HIGH.

### Five-user test timing

- **PO_PROPOSAL:** Five-person moderated test after all RC4 fixes.
- **YOUR_DECISION:** AGREE_WITH_MODIFICATION.
- **EVIDENCE:** UX-001/002 are mechanical failures with high confidence;
  UX-003/004 are P2 hypotheses from one expert reviewer.
- **PRODUCT_REASONING:** Hard blockers do not need more validation before repair.
  The structure of onboarding and Dashboard priority does.
- **USER_IMPACT:** Test participants can reach value, while their behavior still
  informs the P2 design rather than merely validating a finished design.
- **RISK_IF_ACCEPTED:** Testing too late produces confirmation evidence only.
- **RISK_IF_REJECTED:** Testing rc.3 without repaired execution primarily measures
  known setup failure.
- **RECOMMENDED_BOUNDARY:** Implement hard MUST foundations, run five moderated
  sessions, finish evidence-supported SHOULD items, then run release acceptance.
- **CONFIDENCE:** HIGH.

### Documentation reconciliation

- **PO_PROPOSAL:** Reconcile existing RC3 guides after RC4 implementation.
- **YOUR_DECISION:** AGREE.
- **EVIDENCE:** The current guides accurately warn that standard rc.3 startup
  cannot execute Source Runs. That text will become stale when UX-001 changes.
- **PRODUCT_REASONING:** Documentation must describe the released product, but it
  cannot substitute for a functioning core path.
- **USER_IMPACT:** Users receive one accurate setup and recovery story.
- **RISK_IF_ACCEPTED:** Premature documentation could get ahead of implementation;
  final reconciliation must follow verified behavior.
- **RISK_IF_REJECTED:** Correct rc.3 warnings would misdescribe rc.4.
- **RECOMMENDED_BOUNDARY:** Update Quick Start and Manual only after behavior is
  implemented and verified; make reconciliation a release gate.
- **CONFIDENCE:** HIGH.

## Where the PO Is Correct

- UX-001 and UX-002 are the two verified open P1 defects.
- Broader self-guided testing before repairing them would be low-signal.
- UX-006 and UX-011 belong in the end-to-end first-run outcome.
- Save, Topic semantics, Investigations capability, V2, new providers/models,
  and Deep Analysis do not belong in RC4.
- User documentation must be reconciled after behavior changes.

## Where the PO Is Too Aggressive

- UX-003 is not established as P1. It is a P2 design hypothesis with medium
  confidence and should be bounded and tested.
- A fixed warning-first Dashboard order is broader than the evidence supports.
- “Production readiness” must not imply in-app credential storage, automatic
  cloud activation, or a universal Ready flag.
- Completing every P2 before external testing would overfit one expert review.

## Where the PO Is Too Conservative

- The plan omits UX-005. A bad Source URL is a predictable first-run error, and
  field-specific guidance is a small, bounded product fix.
- Minimum Source Run orientation is not merely high-value polish; it is part of
  proving that the repaired production path works end to end.
- “Cost unavailable does not mean free” is a small trust clarification and
  should not wait behind full Resource Usage attribution.

## Missing Issues in the PO Plan

### UX-005 — Source input error guidance

The current flow can reduce all validation failures to a generic save failure.
RC4 SHOULD associate a safe, field-specific message with Source URL or another
invalid field. This is not permission to expose raw backend exceptions.

### Readiness truth is currently split and partly static

Settings can show the approved provider/model while the active loopback process
still lacks an executor or credential. RC4 must distinguish product authority
from current runtime readiness and must not convert the static qualification
record into false green execution readiness.

## Issues That Should NOT Be in RC4

- Save-as-knowledge-base semantics or stale fallback.
- New Topic synthesis, confidence evolution, or disagreement logic.
- New Weekly generation or prioritization semantics.
- Investigation execution or top-level IA redesign.
- Broad provenance terminology redesign.
- A design-system rewrite, telemetry platform, billing system, recommendation
  engine, credential vault, new provider/model, or new AI calls for UX.
- A database migration solely to support progress or attribution.

## Target User Challenge

### TARGET_USER

A single-user, Mac-first, AI-comfortable product or technology knowledge worker
who follows YouTube for professional information. They can install and start a
local product using one documented command or launcher and can perform a guided,
one-time environment credential setup. They do not know repository internals,
provider qualification machinery, task IDs, or database architecture.

### NON_TARGET_USER

- A mass-market consumer expecting App Store installation and zero terminal use.
- A multi-user/team administrator or hosted-SaaS customer.
- A user who will not provide a supported external model credential or accept
  bounded cloud processing.
- A user requiring a guarantee that no approved input ever leaves the device.

### TECHNICAL_COMFORT_ASSUMPTION

The target user can follow exact setup instructions and restart a local process.
They must not edit application code, compose runtime adapters, inspect SQLite,
or understand provider eligibility to reach first value.

### SETUP_TOLERANCE

Up to 10–15 minutes once for installation, local startup, and credential setup;
approximately 5 minutes of active UI work to add the first Source. Processing
time is excluded and must be communicated honestly.

### COST_CONTROL_EXPECTATION

No automatic schedule or cloud spend without an explicit, visible choice. The
user can see the applicable model, run limits, budget status, usage, and the
truth that unavailable cost is not zero.

### PRIVACY_EXPECTATION

Local persistence by default, credential secrecy, and a plain-language notice
that approved, evidence-bounded distillation input is sent to NVIDIA NIM. No
claim of absolute local-only processing or comprehensive privacy guarantee.

The candidate target is therefore correct only when “comfortable running a
local product” is explicit. “Ordinary user” for this private RC does not mean a
non-technical consumer; it means the target user above without repository or
runtime-architecture knowledge.

## Fix-Before-Test vs Test-Before-Fix

| Item | Sequence | Reason |
| --- | --- | --- |
| UX-001 | Fix before external task testing | The existing path cannot produce the intended outcome. |
| UX-002 | Fix before external task testing | Known keyboard failure needs no preference validation. |
| Minimum UX-006/011 | Fix before test | Participants need truthful orientation and a safe failure path. |
| UX-003 | Test the bounded concept before final polish | Field hierarchy is a user-comprehension hypothesis. |
| UX-004 | Test before full redesign | The current intelligence-first order is already valuable. |
| UX-005 | Implement bounded guidance, then observe | It is small, predictable, and first-run specific. |
| UX-012 attribution | Test demand; keep stretch | Primarily a power-user need and already mechanically possible. |

## Five-User Test Timing

Recommended sequence:

1. Implement and internally verify UX-001, UX-002, minimum UX-006, and safe
   UX-011 contracts.
2. Run a five-person moderated test on that usable candidate, including a
   one-participant pilot before the remaining four sessions.
3. Use observed behavior to confirm or narrow UX-003 and UX-004; implement only
   the frozen bounded scope or record a PO-approved scope change.
4. Reconcile documentation, run the release gate, and only then begin the
   broader private trial.

## Adversarial Spec Review

| Attack | Finding | Frozen response |
| --- | --- | --- |
| A. “Ready” hides provider/budget/credential states | Valid risk | Overall summary is allowed only with all independent dimensions visible. Unknown budget is not green. |
| B. Onboarding silently enables cloud/spending | Valid in rc.3's Daily default | New Sources are Manual by default; recurring work requires explicit confirmation. |
| C. Progressive disclosure hides cost controls | Valid risk | Initial History and Per-run Limit stay in the visible recommended summary; schedule disclosure names possible provider/budget use. |
| D. Recovery creates illegal Retry | Valid risk | Recovery actions are navigation or explicit prerequisite edits; AMBIGUOUS has no dispatch action. |
| E. Progress fabricates backend states | Valid risk | Every label maps to an existing top-level state/checkpoint/result count; percentages and estimates are rejected. |
| F. Progress silently requires `m017` | Rejected after inspection | Existing DB v16 persists run state, checkpoints, children, and execution links; scope is projection only. |
| G. Accessibility expands into design-system rewrite | Valid scope risk | Acceptance is limited to Source dialog behavior; no library/design-system rewrite is prescribed. |
| H. Dashboard becomes warning-first | Valid risk | A compact blocker rises conditionally; healthy state remains intelligence-first. |
| I. Resource Usage invents attribution | Rejected for bounded option | Existing usage records already carry Source/video IDs; rows without resolvable authority omit attribution. |
| J. Credential UX authorizes insecure storage | Valid risk | RC4 freezes external setup + presence-only detection; browser/API secret entry is rejected. |
| K. Investigations scope leaks in | Rejected | IA and non-executing explanation remain unchanged; no capability work. |
| L. V2 leaks in | Rejected | V2 and all related capabilities are explicit non-goals. |
| M. Documentation excuses broken product | Rejected | UX-001/002/006/011 require product fixes; docs follow verified behavior. |
| N. Spec overfits one expert review | Partly valid | Mechanical P1s are fixed; inference-heavy P2 hierarchy is bounded and externally tested before final polish. |
| O. Issues users should validate are fixed first | Partly valid | UX-003/004 are tested after hard foundations; only safe, thin boundaries are frozen now. |

This adversarial pass changed three boundaries from the PO proposal: UX-003 is
SHOULD rather than P1/MUST; Dashboard work is conditional rather than a fixed
warning-first reorder; and Source Run progress is explicitly a no-migration
bounded projection.

## Final Recommended RC4 Scope

### MUST

- UX-001 bounded production startup and independent readiness checks.
- UX-002 accessible Source configuration.
- UX-006 truthful existing-state Source Run projection and return orientation.
- UX-011 finite safe recovery actions.
- RC4 documentation reconciliation and the release gates in the acceptance plan.

### SHOULD

- UX-003 one-input starter path with visible recommended settings and manual-by-
  default scheduling for new Sources only.
- UX-005 field-specific Source configuration errors.
- UX-004 conditional compact blocking-attention summary.
- UX-012 adjacent explanation that unknown/unavailable cost is not zero or free.

### STRETCH

- Human-readable Resource Usage Source/video attribution using already-persisted
  fields only.

### DEFER

- Dashboard card compaction beyond the conditional blocker summary.
- Save, Topic, Weekly, broad provenance, claim-kind education beyond docs,
  Investigations navigation/capability, and item-specific Save labels.

### REJECT

- Credential entry/storage, automatic cloud enablement or spending, generic
  Retry, fake progress, `m017`, inferred cost/attribution, fallback, broad IA or
  design-system rewrites, new AI calls, Deep Analysis, TASK-016G, and V2.

## Decisions Requiring Product Owner

No unresolved product decision prevents this proposed freeze. The Product Owner
must still approve the proposed scope as a whole before implementation. Any
request to add in-app secret storage, change the frozen top-level IA, introduce
`m017`, or reclassify STRETCH work as required is a new **PO_DECISION_REQUIRED**
scope decision.

## Evidence Base and Limits

This review uses the full RC3 Product Experience Audit, improvement backlog,
Quick Start, User Manual, frozen product/IA authorities, RC candidate evidence,
TASK-026A handoff, and direct read-only inspection of current Source Run,
orchestration, API projection, and frontend behavior. No production call was
made.

Observed facts are identified above as evidence. Product reasoning and user
impact are inferences. Recommendations are proposed design contracts, not
implemented behavior. This remains a single-expert review and does not replace
external usability participants.
