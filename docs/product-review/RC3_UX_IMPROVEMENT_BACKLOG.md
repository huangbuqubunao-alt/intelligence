# RC3 UX Improvement Backlog

This backlog records product and UX recommendations only. It does not authorize implementation and does not change any rc.3 behavior, trust rule, provider/model scope, database contract, or information architecture.

## Summary

| ID | Title | Root cause | Severity | Impact | Effort | Release | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UX-001 | Complete the ordinary-user readiness and Source execution path | PRODUCT_MODEL | P1 | High | L | RC4 | OPEN |
| UX-002 | Make Source configuration dialog keyboard-operable | ACCESSIBILITY | P1 | High | S | RC4 | OPEN |
| UX-003 | Reduce first-Source decisions and summarize recurring work | ONBOARDING | P2 | High | M | RC4 | OPEN |
| UX-004 | Put blockers and orientation above expanded Dashboard detail | INFORMATION_HIERARCHY | P2 | High | M | RC4 | OPEN |
| UX-005 | Replace generic Source URL errors with field guidance | ERROR_RECOVERY | P2 | Medium | S | RC4 | OPEN |
| UX-006 | Show durable Source-check stage, outcome, and next expectation | PERFORMANCE_PERCEPTION | P2 | High | M | RC4 | OPEN |
| UX-007 | Explain claim kinds in plain language | TRUST_EXPLANATION | P2 | High | S | RC4 | OPEN |
| UX-008 | Make Weekly a prioritized synthesis with readable evidence | PRODUCT_MODEL | P2 | High | L | RC4 | OPEN |
| UX-009 | Define Save as a personal reference action | COPY_TERMINOLOGY | P2 | Medium | S | POST_V1 | OPEN |
| UX-010 | Make Topics explain evolution, disagreement, and uncertainty | PRODUCT_MODEL | P2 | High | L | POST_V1 | OPEN |
| UX-011 | Give Needs Attention a direct, safe resolution path | ERROR_RECOVERY | P2 | High | M | RC4 | OPEN |
| UX-012 | Make Resource Usage attributable and explain unknown cost | TRUST_EXPLANATION | P2 | High | M | RC4 | OPEN |
| UX-013 | Remove the expectation cost of unavailable Investigations | INFORMATION_ARCHITECTURE | P3 | Low | S | V2 | OPEN |
| UX-014 | Give repeated Save actions item-specific accessible names | ACCESSIBILITY | P3 | Medium | XS | POST_V1 | OPEN |
| UX-015 | Translate technical provenance before showing identifiers | COPY_TERMINOLOGY | P3 | Medium | S | POST_V1 | OPEN |
| UX-016 | Provide one accurate rc.3 user documentation set | DOCUMENTATION | P1 | High | M | DOCUMENTATION_ONLY | ADDRESSED_IN_THIS_REVIEW |

Severity totals: **P0 0 · P1 3 · P2 10 · P3 3**.

## Evidence Labels

- **OBSERVED FACT:** directly seen in the running rc.3 UI, current projections, or repository-supported startup.
- **USER-RISK INFERENCE:** a likely usability consequence; it is not claimed as observed user behavior.
- **DESIGN RECOMMENDATION:** a proposed response that preserves current semantics unless explicitly marked future/strategic.
- **PERSONAL DESIGN PREFERENCE:** taste without sufficient product evidence; not treated as a defect.

## A. MUST ADDRESS

### UX-001 — Complete the ordinary-user readiness and Source execution path

- **ISSUE_ID:** UX-001
- **TITLE:** Complete the ordinary-user readiness and Source execution path
- **SCREEN / FLOW:** Start Product → Settings readiness → Add Source → Check Now
- **OBSERVATION:** **Observed fact:** rc.3 has an authorized and qualified NVIDIA NIM / `moonshotai/kimi-k3` V1 Video Distillation path, and a normal-production Source Run is confirmed passed. The repository-supported `youtube-intel serve-api` composition instantiates the Source orchestration service without a Source check executor, so `Check Now` remains guarded. The UI has no credential input and the current repository documentation does not provide one consolidated ordinary-user production launcher/readiness procedure.
- **USER_PROBLEM:** a capable first-time user can configure a Source yet cannot predict or complete the path to real Intelligence without an operator who knows the runtime composition and indirect credential setup.
- **ROOT_CAUSE:** PRODUCT_MODEL
- **EVIDENCE:** running Sources/Source detail flow (E06–E07); safe blocked Check Now result; `docs/LOCAL_PRODUCT_ORCHESTRATION.md`; current `serve-api` composition; authoritative rc.3 provider state.
- **SEVERITY:** P1
- **FREQUENCY:** HIGH for new installations
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** provide one supported, documented production UI startup composition and a read-only readiness checklist covering Source execution availability, exact approved provider/model scope, credential presence without value exposure, and budget availability. `Check Now` should run only when every existing gate passes and should otherwise name the unresolved prerequisite.
- **WHY_THIS_CHANGE:** it closes the core value loop without weakening any trust or security boundary.
- **ALTERNATIVES_CONSIDERED:** document an engineer-only manual composition (insufficient for normal users); add API-key entry in the browser (rejected due credential risk); present demo fixtures as production (misleading).
- **RISKS:** a launcher could accidentally enable cloud use or imply spending consent; readiness state could expose secret metadata if designed poorly.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** L
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** Product Owner decision on supported local installation/launch contract; existing production Source Run adapter; backend-owned indirect credential mechanism; budget gates.
- **DO_NOT_CHANGE:** no credential value in the UI/logs; no provider/model fallback; no automatic cloud enablement; no retry of unconfirmed outcomes; exact V1 Video Distillation scope only.

### UX-002 — Make Source configuration dialog keyboard-operable

- **ISSUE_ID:** UX-002
- **TITLE:** Make Source configuration dialog keyboard-operable
- **SCREEN / FLOW:** Sources → Source detail → Edit configuration
- **OBSERVATION:** **Observed fact:** the nested edit dialog was visible, but it did not appear in the accessibility tree. Pressing Tab moved focus to “Stop future monitoring” behind the dialog, and Escape did not close the visible dialog.
- **USER_PROBLEM:** a keyboard or assistive-technology user may be unable to edit or leave Source configuration reliably.
- **ROOT_CAUSE:** ACCESSIBILITY
- **EVIDENCE:** direct keyboard test in Chrome against rc.3 Source detail; Add Source dialog served as a comparison and did appear in the accessibility tree.
- **SEVERITY:** P1
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** ensure only one active modal context, expose the edit dialog with a programmatic name, move focus into it, contain focus, support Escape/Cancel, and restore focus to Edit configuration on close.
- **WHY_THIS_CHANGE:** Source configuration is a core control and cannot depend on pointer input.
- **ALTERNATIVES_CONSIDERED:** keep nested visual dialogs with a skip link (does not solve focus); move edit to a separate page (larger change, unnecessary for rc.4).
- **RISKS:** focus restoration can regress if detail panels are conditionally removed; modal changes must not alter Source semantics.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** S
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** existing dialog component behavior and focused keyboard regression tests.
- **DO_NOT_CHANGE:** configuration values, monitoring future-only semantics, save/cancel behavior, or trust gates.

## B. HIGH-VALUE RC4

### UX-003 — Reduce first-Source decisions and summarize recurring work

- **ISSUE_ID:** UX-003
- **TITLE:** Reduce first-Source decisions and summarize recurring work
- **SCREEN / FLOW:** Add Source
- **OBSERVATION:** **Observed fact:** the form presents URL, processing level, monitoring, Initial history, Per-run limit, Focus, Ignore, Distillation style, frequency, time, and schedule enablement in one modal. The default schedule is Daily at 09:00 and enabled.
- **USER_PROBLEM:** a new user must make or ignore many unfamiliar choices before value and may create recurring external work without a clear final summary.
- **ROOT_CAUSE:** ONBOARDING
- **EVIDENCE:** E06 and E13.
- **SEVERITY:** P2
- **FREQUENCY:** HIGH
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** show an essentials layer (YouTube URL, monitor on/off, simple “Turn relevant videos into Intelligence” preset), summarize starter defaults, and place history limits, filters, style, and schedule behind a clearly named Customize section. Before save, state the selected cadence and that eligible checks may use the external model and available budget.
- **WHY_THIS_CHANGE:** it reduces decision cost while retaining control and truthful resource implications.
- **ALTERNATIVES_CONSIDERED:** remove controls (reject; power users need them); build a long multi-step wizard (adds navigation cost); default everything without disclosure (weak consent).
- **RISKS:** progressive disclosure can hide important recurring-work consequences; the summary must remain visible.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** M
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** UX-001 readiness language; existing Source policy defaults.
- **DO_NOT_CHANGE:** Initial history/Per-run semantics, future-only monitoring behavior, schedule authority, budget/provider gates.

### UX-004 — Put blockers and orientation above expanded Dashboard detail

- **ISSUE_ID:** UX-004
- **TITLE:** Put blockers and orientation above expanded Dashboard detail
- **SCREEN / FLOW:** Dashboard return visit
- **OBSERVATION:** **Observed fact:** three full Intelligence cards, including Evidence, precede Topic changes, Weekly, and Needs Attention. At 768 × 900, one card occupies most of the first viewport.
- **USER_PROBLEM:** returning users may not see a blocker or weekly orientation until after several screens of reading.
- **ROOT_CAUSE:** INFORMATION_HIERARCHY
- **EVIDENCE:** E01, E11, E12.
- **SEVERITY:** P2
- **FREQUENCY:** HIGH
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** place unresolved Needs Attention and a compact “since your last visit” summary before the feed. Show conclusions, relevance, novelty, claim/state, and a compact evidence cue by default; expand details and excerpt in place.
- **WHY_THIS_CHANGE:** it makes the Dashboard answer “what matters now?” rather than requiring the user to reconstruct system activity.
- **ALTERNATIVES_CONSIDERED:** show only one card (may hide useful breadth); remove Evidence (rejected); reduce font/spacing only (does not fix priority).
- **RISKS:** excessive collapsing could weaken trust or hide material qualifiers.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** M
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** content-priority rules; accessible disclosure behavior.
- **DO_NOT_CHANGE:** conclusion-first order, claim kind/state, one-step source/evidence reachability, fail-closed content.

### UX-005 — Replace generic Source URL errors with field guidance

- **ISSUE_ID:** UX-005
- **TITLE:** Replace generic Source URL errors with field guidance
- **SCREEN / FLOW:** Add Source validation
- **OBSERVATION:** **Observed fact:** an empty URL uses native required-field feedback, while `not-a-youtube-url` returns the generic banner “Request values are invalid or unavailable.”
- **USER_PROBLEM:** the user does not know which YouTube URL formats are accepted or how to correct the input.
- **ROOT_CAUSE:** ERROR_RECOVERY
- **EVIDENCE:** direct form submission in E06 flow.
- **SEVERITY:** P2
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** MEDIUM
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** associate the error with Source URL and show accepted examples (channel handle, channel URL, or individual video URL where supported) without echoing unsafe input.
- **WHY_THIS_CHANGE:** recovery becomes immediate and does not require technical knowledge.
- **ALTERNATIVES_CONSIDERED:** accept arbitrary URLs (unsafe/ambiguous); link only to external docs (slower recovery).
- **RISKS:** examples must match backend normalization exactly and stay current.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** S
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** current URL validation contract and safe error projection.
- **DO_NOT_CHANGE:** backend validation, canonicalization, safe error redaction.

### UX-006 — Show durable Source-check stage, outcome, and next expectation

- **ISSUE_ID:** UX-006
- **TITLE:** Show durable Source-check stage, outcome, and next expectation
- **SCREEN / FLOW:** Check Now; Analyze this Video; scheduled Source check
- **OBSERVATION:** **Observed fact:** Source detail shows Check Now and a Source Run status area. The reviewed composition returned a safe block. After Analyze this Video, the product acknowledged a relevance override while the visible row remained Skipped. Current waiting/completion projections do not provide a user-oriented time or stage expectation.
- **USER_PROBLEM:** users cannot tell whether work is queued, processing, blocked, finished with no relevant videos, or awaiting a later refresh.
- **ROOT_CAUSE:** PERFORMANCE_PERCEPTION
- **EVIDENCE:** E07, E09; current Source Run projections.
- **SEVERITY:** P2
- **FREQUENCY:** HIGH
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** MEDIUM because a live production run was not repeated in this review
- **RECOMMENDED_CHANGE:** show a durable, user-facing state sequence such as Checking source → Reviewing relevant videos → Creating Intelligence → Complete/No relevant changes/Needs Attention, with last update time and a clear “you can leave this page” expectation. After relevance override, show its resulting queued/blocked/completed state.
- **WHY_THIS_CHANGE:** perceived reliability depends on understanding waiting and completion, not on a fabricated ETA.
- **ALTERNATIVES_CONSIDERED:** exact progress percentage (likely false precision); indefinite spinner (current ambiguity); expose internal checkpoints (too technical).
- **RISKS:** stages must reflect real durable states and never imply a retry or success that has not occurred.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** M
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** UX-001 execution composition; current Source Run state projections.
- **DO_NOT_CHANGE:** at-most-once behavior, terminal unconfirmed outcome, budget/model/provider blocks, relevance-only override.

### UX-007 — Explain claim kinds in plain language

- **ISSUE_ID:** UX-007
- **TITLE:** Explain claim kinds in plain language
- **SCREEN / FLOW:** Intelligence card, Evidence, manual/glossary
- **OBSERVATION:** **Observed fact:** rc.3 shows human labels such as “Supported statement” and “Attributed opinion,” but no visible definition. The legal kinds include Fact, Evidence-backed statement, Opinion, Prediction, Rumor, and System inference.
- **USER_PROBLEM:** “Supported statement” can be read as a verified fact, while Fact can be read as absolute truth. Opinion or prediction can lose attribution during scanning.
- **ROOT_CAUSE:** TRUST_EXPLANATION
- **EVIDENCE:** E01–E02; current legal claim-kind mapping.
- **SEVERITY:** P2
- **FREQUENCY:** HIGH
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** add short definitions/tooltips and preserve attribution in the label: “Fact reported in the source,” “Statement supported by this video’s evidence,” “Attributed opinion,” “Prediction,” “Unverified rumor,” and “AI/system inference.” Keep the legal enum unchanged.
- **WHY_THIS_CHANGE:** it improves trust calibration without changing admission semantics.
- **ALTERNATIVES_CONSIDERED:** hide claim kinds (reject); merge Fact and supported statement (changes semantics); rely only on color (inaccessible).
- **RISKS:** wording can overstate external verification; definitions must say the cited source remains the authority.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** S
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** product/legal review of human labels; RC3 manual definitions.
- **DO_NOT_CHANGE:** underlying claim kinds, evidence requirements, attribution, lifecycle state separation.

### UX-008 — Make Weekly a prioritized synthesis with readable evidence

- **ISSUE_ID:** UX-008
- **TITLE:** Make Weekly a prioritized synthesis with readable evidence
- **SCREEN / FLOW:** Intelligence → Weekly; Dashboard This week
- **OBSERVATION:** **Observed fact:** the reviewed Weekly contains one historical item, Topic, claim/state, correction disclosure, and an opaque reference hash. It does not explain why the item outranked alternatives or synthesize multiple changes.
- **USER_PROBLEM:** the page can feel like an archive entry rather than an answer to “What mattered this week?” and the user cannot directly verify hash-only evidence.
- **ROOT_CAUSE:** PRODUCT_MODEL
- **EVIDENCE:** E04.
- **SEVERITY:** P2
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH for the observed state; MEDIUM for long-term variety
- **RECOMMENDED_CHANGE:** lead with a short week-level synthesis, then 1–3 prioritized changes with “why it mattered/what changed” and readable Source/video/timestamp evidence. If nothing important changed, state that confidently without filler. Preserve historical corrections and immutability.
- **WHY_THIS_CHANGE:** Weekly should compress attention, not merely list processed items.
- **ALTERNATIVES_CONSIDERED:** list every video (noise); generate a weekly narrative regardless of change (filler); hide historical corrections (trust loss).
- **RISKS:** synthesis may over-compress disagreement or imply certainty.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** L
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** current trusted Weekly authority and evidence linkage; no V2 dependency should be introduced.
- **DO_NOT_CHANGE:** honest no-change state, correction disclosure, immutable history, trusted-source requirements.

### UX-011 — Give Needs Attention a direct, safe resolution path

- **ISSUE_ID:** UX-011
- **TITLE:** Give Needs Attention a direct, safe resolution path
- **SCREEN / FLOW:** Dashboard and Source detail
- **OBSERVATION:** **Observed fact:** model unavailable copy explains that work is paused and existing data is unchanged, but the Dashboard card is below the main feed and provides no direct button. Budget, decision-required, and unconfirmed-outcome copy follows the same safe but mostly textual pattern.
- **USER_PROBLEM:** the user understands that something is wrong but may not know the affected Source, exact prerequisite, or safe next action.
- **ROOT_CAUSE:** ERROR_RECOVERY
- **EVIDENCE:** E01, E07; current attention-copy mappings.
- **SEVERITY:** P2
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH for copy; MEDIUM for unexercised states
- **RECOMMENDED_CHANGE:** use a four-part layout—what happened, impact, user action, system behavior—and provide safe deep links to exact Settings readiness, Resource Usage, or Source configuration. For unconfirmed external results, show status only and explicitly omit Retry.
- **WHY_THIS_CHANGE:** it turns safe messaging into recoverable messaging.
- **ALTERNATIVES_CONSIDERED:** automatic retry (rejected); generic Settings link (current); expose internal error enums (too technical).
- **RISKS:** action labels could accidentally imply authority to override a blocked gate.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** M
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** stable attention reason mapping; section anchors/routes.
- **DO_NOT_CHANGE:** existing data preservation, fail-closed gates, no illegal retry, no override of provider/budget authority.

### UX-012 — Make Resource Usage attributable and explain unknown cost

- **ISSUE_ID:** UX-012
- **TITLE:** Make Resource Usage attributable and explain unknown cost
- **SCREEN / FLOW:** Settings → Resource Usage; budget-related Needs Attention
- **OBSERVATION:** **Observed fact:** multiple rows are titled “Recorded work” and show calls, duration, token/cost availability, status, and technical detail, but not a useful date/Source/video/purpose. Cost unavailable is truthful but lacks the adjacent warning that unknown is not zero.
- **USER_PROBLEM:** a cost-conscious user cannot reconcile usage with product actions and may mistake unavailable cost for free usage.
- **ROOT_CAUSE:** TRUST_EXPLANATION
- **EVIDENCE:** E10.
- **SEVERITY:** P2
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** label each record with time, Source/video or task purpose where safely available; add daily/weekly grouping; display “Cost unavailable — this does not mean zero or free” next to the value; link budget blocks to the relevant range.
- **WHY_THIS_CHANGE:** resource truth becomes actionable without fabricating a price.
- **ALTERNATIVES_CONSIDERED:** calculate estimated cost without authority (misleading); hide unknown rows (weakens cost truth); show only raw ledger identifiers (not user-facing).
- **RISKS:** attribution must not leak private paths, credentials, payloads, or full transcripts.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** M
- **RECOMMENDED_RELEASE:** RC4
- **DEPENDENCIES:** safe ledger projection and cost authority.
- **DO_NOT_CHANGE:** UNKNOWN remains unknown; no cost inference, secret exposure, or mutable ledger history.

## C. POST-V1

### UX-009 — Define Save as a personal reference action

- **ISSUE_ID:** UX-009
- **TITLE:** Define Save as a personal reference action
- **SCREEN / FLOW:** Intelligence → Save → Saved
- **OBSERVATION:** **Observed fact:** Save persists a reference shown under Saved; unavailable trusted content remains unavailable and can be Unsaved. No copy defines whether Save means bookmark, read later, or knowledge base.
- **USER_PROBLEM:** users cannot predict why or when to Save, or what permanence it provides.
- **ROOT_CAUSE:** COPY_TERMINOLOGY
- **EVIDENCE:** E02–E03.
- **SEVERITY:** P2
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** MEDIUM
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** define Saved as “your personal reference list for Intelligence you want to return to,” add a brief confirmation, and explain that trusted detail can become unavailable rather than falling back to stale content.
- **WHY_THIS_CHANGE:** it sets the right expectation without expanding the data model.
- **ALTERNATIVES_CONSIDERED:** rename to Read later (too narrow); make Saved a knowledge base (new semantics); show stale snapshot (rejected).
- **RISKS:** stronger permanence language may conflict with fail-closed availability.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** S
- **RECOMMENDED_RELEASE:** POST_V1
- **DEPENDENCIES:** none beyond current Saved behavior.
- **DO_NOT_CHANGE:** fail-closed unavailable state; Unsave control; no stale fallback.

### UX-010 — Make Topics explain evolution, disagreement, and uncertainty

- **ISSUE_ID:** UX-010
- **TITLE:** Make Topics explain evolution, disagreement, and uncertainty
- **SCREEN / FLOW:** Topics list/detail; Pin Topic
- **OBSERVATION:** **Observed fact:** Topic detail leads with current understanding and includes an unavailable-support state, a single disagreement timeline entry, technical evidence references, and no related Topics. Pin Topic returns to the list.
- **USER_PROBLEM:** users cannot reconstruct which sources disagree, what changed, how confident the product is, or why the current understanding should be revisited.
- **ROOT_CAUSE:** PRODUCT_MODEL
- **EVIDENCE:** E05 and direct Pin interaction.
- **SEVERITY:** P2
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH for current presentation
- **RECOMMENDED_CHANGE:** show current understanding, latest change, explicit uncertainty, supporting and contradicting Intelligence, and a readable timeline of revisions. Keep the user on the Topic after Pin and explain whether Pin means follow/priority.
- **WHY_THIS_CHANGE:** it makes Topic a persistent intelligence object rather than a collection label.
- **ALTERNATIVES_CONSIDERED:** reduce Topic to tags/folders (loses product value); auto-resolve disagreement (unsafe); add V2 investigation features now (out of scope).
- **RISKS:** synthesis may conceal unresolved evidence or overstate independence of sources.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** L
- **RECOMMENDED_RELEASE:** POST_V1
- **DEPENDENCIES:** current Topic/trusted Intelligence authority; later data volume research.
- **DO_NOT_CHANGE:** explicit disagreement/uncertainty; fail-closed unavailable evidence; no invented consensus.

### UX-014 — Give repeated Save actions item-specific accessible names

- **ISSUE_ID:** UX-014
- **TITLE:** Give repeated Save actions item-specific accessible names
- **SCREEN / FLOW:** Dashboard and Intelligence lists
- **OBSERVATION:** **Observed fact:** multiple cards expose the same accessible button name, “Save.”
- **USER_PROBLEM:** assistive-technology users navigating by controls cannot tell which Intelligence item each Save action affects.
- **ROOT_CAUSE:** ACCESSIBILITY
- **EVIDENCE:** Dashboard and Intelligence accessibility trees.
- **SEVERITY:** P3
- **FREQUENCY:** HIGH when several cards are present
- **USER_IMPACT:** MEDIUM
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** retain the visual label but use an accessible name such as “Save: [short conclusion]”; announce saved/unsaved state.
- **WHY_THIS_CHANGE:** improves nonvisual navigation with no visual redesign.
- **ALTERNATIVES_CONSIDERED:** number buttons (unstable and meaningless); rely on DOM context (inconsistent screen-reader experience).
- **RISKS:** full conclusions may create overly long names; use a bounded meaningful label.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** XS
- **RECOMMENDED_RELEASE:** POST_V1
- **DEPENDENCIES:** card identifier/short title availability.
- **DO_NOT_CHANGE:** Save/Saved semantics or fail-closed behavior.

### UX-015 — Translate technical provenance before showing identifiers

- **ISSUE_ID:** UX-015
- **TITLE:** Translate technical provenance before showing identifiers
- **SCREEN / FLOW:** Intelligence, Weekly, Topic Evidence disclosures
- **OBSERVATION:** **Observed fact:** Technical provenance can expose opaque source/revision/video identifiers or a hash without explaining what they verify.
- **USER_PROBLEM:** normal users receive cognitive load without a usable verification action; power users still lack labeled meaning.
- **ROOT_CAUSE:** COPY_TERMINOLOGY
- **EVIDENCE:** E02, E04, E05.
- **SEVERITY:** P3
- **FREQUENCY:** MEDIUM
- **USER_IMPACT:** MEDIUM
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** first state what provenance confirms in plain language, label provider/model/version/date where safe, and place raw identifiers in a second advanced disclosure or copyable diagnostic block.
- **WHY_THIS_CHANGE:** technical truth remains available but no longer interrupts comprehension.
- **ALTERNATIVES_CONSIDERED:** remove identifiers (reject); show all ledger fields (overload/privacy risk).
- **RISKS:** friendly wording must not claim verification beyond actual authority.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** S
- **RECOMMENDED_RELEASE:** POST_V1
- **DEPENDENCIES:** safe projection labels.
- **DO_NOT_CHANGE:** provenance retention, immutable IDs, privacy redaction, evidence reachability.

## D. V2 / STRATEGIC

### UX-013 — Remove the expectation cost of unavailable Investigations

- **ISSUE_ID:** UX-013
- **TITLE:** Remove the expectation cost of unavailable Investigations
- **SCREEN / FLOW:** Top-level navigation → Investigations
- **OBSERVATION:** **Observed fact:** Investigations is a top-level item, but the page says the capability is unavailable in V1 and offers no action.
- **USER_PROBLEM:** the navigation promises a core workflow that does not exist and makes the product feel incomplete.
- **ROOT_CAUSE:** INFORMATION_ARCHITECTURE
- **EVIDENCE:** E08.
- **SEVERITY:** P3
- **FREQUENCY:** LOW after first discovery
- **USER_IMPACT:** LOW
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** because rc.3 IA is frozen, make no current change. In a future IA decision, omit the destination until usable or label it unavailable in navigation before the user enters it.
- **WHY_THIS_CHANGE:** top-level navigation should map to current user goals.
- **ALTERNATIVES_CONSIDERED:** fill the page with roadmap content (creates false expectations); activate Deep Analysis (unauthorized); repurpose it as Topics (overlap).
- **RISKS:** hiding the item may reduce roadmap visibility for internal stakeholders; roadmap belongs in release notes, not core navigation.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** S
- **RECOMMENDED_RELEASE:** V2
- **DEPENDENCIES:** future IA/Product Owner decision and real investigation capability.
- **DO_NOT_CHANGE:** frozen rc.3 IA; do not imply Deep Analysis or V2 availability.

## E. DOCUMENTATION-ONLY

### UX-016 — Provide one accurate rc.3 user documentation set

- **ISSUE_ID:** UX-016
- **TITLE:** Provide one accurate rc.3 user documentation set
- **SCREEN / FLOW:** Before Start through troubleshooting
- **OBSERVATION:** **Observed fact:** existing repository documents are fragmented and include historical provider/release states that conflict with current rc.3 authority. The primary README and local orchestration document are operator/engineering oriented and do not form a normal-user manual.
- **USER_PROBLEM:** a user cannot reliably learn current rc.3 behavior, vocabulary, setup boundaries, claim types, evidence, failures, costs, or limitations from one source.
- **ROOT_CAUSE:** DOCUMENTATION
- **EVIDENCE:** current README, local orchestration/operations documents, rc.3 candidate record, and running product.
- **SEVERITY:** P1
- **FREQUENCY:** HIGH for first use and troubleshooting
- **USER_IMPACT:** HIGH
- **CONFIDENCE:** HIGH
- **RECOMMENDED_CHANGE:** publish the rc.3 Quick Start and User Manual created by this review, clearly distinguishing current user behavior, operator prerequisites, verified provider capability, and unavailable features.
- **WHY_THIS_CHANGE:** accurate guidance reduces onboarding risk immediately without changing product semantics.
- **ALTERNATIVES_CONSIDERED:** update every historical engineering document (out of scope and risks rewriting evidence); rely on inline copy only (insufficient for setup/troubleshooting).
- **RISKS:** documentation can become stale; every release should verify capability and startup claims.
- **ESTIMATED_IMPLEMENTATION_SCOPE:** M
- **RECOMMENDED_RELEASE:** DOCUMENTATION_ONLY
- **DEPENDENCIES:** Product Owner acceptance of these review artifacts.
- **DO_NOT_CHANGE:** do not present planned features as current; do not expose credentials, internal task IDs, private data, or unsupported privacy guarantees.

## DO NOT IMPLEMENT

The following suggestions were considered and rejected:

1. **Hide Evidence to make cards shorter.** Rejected because source traceability is a product red line. Compacting by default is acceptable only when the complete Source/video/timestamp/excerpt chain remains one interaction away.
2. **Automatically retry an unconfirmed external result.** Rejected because it can duplicate provider work/cost and violates the terminal safety model.
3. **Show the last known Saved content when current trust is unavailable.** Rejected because stale fallback would weaken fail-closed semantics.
4. **Add a browser API-key form.** Rejected for rc.4 unless a separately approved backend/OS credential design exists; never store keys in frontend state, local storage, logs, or tracked files.
5. **Merge Fact, Opinion, Prediction, Rumor, and System inference into one confidence score.** Rejected because it obscures the nature and attribution of claims.
6. **Make Fact visually absolute.** Rejected because a fact label does not replace verification against the original source.
7. **Enable Deep Analysis or Investigations to fill an empty navigation page.** Rejected; those capabilities are unavailable and outside V1.
8. **Estimate unknown cost as zero or a guessed price.** Rejected; UNKNOWN is not free.
9. **List every processed video on Dashboard/Weekly.** Rejected because the product should prioritize information gain, not processing volume.
10. **Change the frozen top-level IA during this review.** Rejected; IA observations are recommendations for a later Product Owner decision.
11. **Remove provider/model scope and resource truth to simplify Settings.** Rejected; progressive disclosure is appropriate, concealment is not.
12. **Treat Analyze this Video as a universal override.** Rejected; it overrides relevance only, never safety, trust, budget, model, or provider restrictions.
