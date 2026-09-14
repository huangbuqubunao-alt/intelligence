# RC3 Product Experience Audit

## Executive Summary

YouTube Intelligence Agent v0.1.0-rc.3 has a credible trust foundation and a partially successful product experience. Its strongest product idea is already visible: the Dashboard leads with conclusions, explains why they matter and what is new, distinguishes claim types, and keeps the original video evidence reachable. The product is more mature than a video-processing console, but it still exposes enough execution and provider machinery that it does not yet feel like a self-explanatory personalized intelligence product for a new user.

**Overall product maturity:** technically credible private release candidate; product experience is suitable for expert-guided evaluation, not yet for an unsupported broader trial.

**Core value clarity:** **PARTIAL.** With Intelligence already present, the product communicates “what matters now” reasonably well. On first open it does not plainly say “AI watches relevant YouTube for you,” and it does not make the path from Source to useful Intelligence obvious without exploration.

**First-time user readiness:** **LOW.** Adding a Source is possible, but the user must understand several settings, an automatic schedule, model readiness, and an indirect credential requirement. More importantly, the repository-supported loopback UI composition starts `serve-api` without a Source execution adapter, so its normal `Check Now` path remains guarded. A normal-production Source Run has been independently confirmed, but that verified capability is not packaged as a complete ordinary-user startup path in rc.3.

**Repeat-use readiness:** **MEDIUM.** New/Updated states, Topics, Saved, Weekly, and Needs Attention provide the right ingredients. Returning users must scan three fully expanded, evidence-heavy Dashboard cards before reaching weekly context and blockers, and the Topic/Weekly synthesis is still shallow.

**Trust/readability quality:** **HIGH for preservation, MEDIUM for usability.** Claim kinds, timestamps, excerpts, source links, fail-closed unavailable content, exact model scope, and no automatic retry after an unconfirmed external result are strong. Opaque hashes, technical labels, and evidence-heavy default density add avoidable cognitive load.

Main strengths:

- Intelligence is presented before video-processing detail.
- Evidence remains adjacent and traceable to a source, video, timestamp, and excerpt.
- Opinion is visibly separated from supported statements.
- Saved and Topic surfaces fail closed instead of showing stale trusted content.
- Deep Analysis is truthfully unavailable; NVIDIA NIM / `moonshotai/kimi-k3` is scoped to V1 Video Distillation.
- Needs Attention copy protects existing data and does not offer an unsafe retry for an unconfirmed external outcome.

Main weaknesses:

- A first-time user cannot complete the supported UI path from local startup to a real Source Run without operator-level setup outside the product.
- The Source edit dialog has a reproducible keyboard/accessibility-tree failure.
- Source onboarding asks for too many decisions before first value and enables a recurring schedule by default without a clear final activity/cost summary.
- The Dashboard is vertically long; high-priority Needs Attention is below lower-priority content.
- Weekly, Topics, Saved, Resource Usage, and claim-kind language need stronger user mental models.

**RC4_RECOMMENDATION: RC4_REQUIRED_BEFORE_BROADER_TRIAL.** No P0 was found. Two open P1 findings affect the core first-run journey and keyboard access, and a cluster of high-impact P2 findings materially weakens first-time comprehension and repeat-use orientation. This recommendation is not based on visual polish.

## Review Scope

### Version and authority

- Reviewed version: `v0.1.0-rc.3`
- Reviewed SHA: `9422c08761eb5cb996758edee26d698dadfd901a`
- Historical `v0.1.0-rc.2`: `41233ee9aac647c99ef3c847130ef06624bbeaa5` (not moved or modified)
- Database authority: version 16; migration 017 absent
- Current qualified production tuple: NVIDIA NIM / `moonshotai/kimi-k3` / V1 Video Distillation only
- Deep Analysis: unavailable

### Screens reviewed

Dashboard, Intelligence Current, Saved, Weekly, Topics list, Topic detail, Sources list, Add Source, Source detail, Source configuration, recent/skipped videos, Analyze this Video, Investigations, Settings, Resource Usage, Evidence, and Needs Attention.

### Flows reviewed

- First open and five-second comprehension
- Add Source, validation, default processing policy, and scheduling
- Check Now in the repository-supported local UI composition
- Intelligence scanning, claim type, Save/Unsave, and evidence expansion
- Topic open, Pin Topic, timeline, unavailable support, and return behavior
- Weekly reading and historical correction disclosure
- Skipped video and Analyze this Video relevance override
- Settings model scope, Deep Analysis state, privacy, and Resource Usage
- Keyboard traversal and nested Source edit dialog
- Narrow and desktop responsive behavior

### Viewports

- 1440 × 900
- 1280 × 800
- 768 × 900

The two desktop sizes and the narrow size were exercised in Chrome responsive mode. The narrow layout replaces the left rail with a horizontal top navigation and preserves a single-column reading flow without observed horizontal clipping.

### Data states

Representative local state included five Sources, three current Intelligence items, Saved current and unavailable references, one Topic with unavailable support and disagreement history, one historical Weekly item, Resource Usage records, a skipped video, and a model-unavailable Needs Attention item. The local review composition intentionally blocked execution.

### Evidence method

Important observations are referenced as `E01`–`E13`:

| Evidence | Surface | What was captured or verified |
| --- | --- | --- |
| E01 | Dashboard | Three full Intelligence cards, Topic changes, Weekly, and Needs Attention |
| E02 | Intelligence | Current list, claim labels, full inline Evidence, Save actions |
| E03 | Saved | Current saved item plus fail-closed unavailable saved reference |
| E04 | Weekly | Historical item, correction disclosure, technical Evidence reference |
| E05 | Topic detail | Current understanding, unavailable support, timeline, related Topics |
| E06 | Add Source | Full configuration form and default automatic schedule |
| E07 | Source detail | Monitoring, processing policy, schedule, Check Now, recent videos |
| E08 | Investigations | V1 unavailable state in a top-level destination |
| E09 | Skipped video | Analyze this Video helper and relevance-only override result |
| E10 | Settings | Provider/model scope, Deep Analysis, Resource Usage, privacy |
| E11 | Responsive | Dashboard at 1440 × 900 and 1280 × 800 |
| E12 | Responsive | Dashboard at 768 × 900 |
| E13 | Responsive form | Add Source at 768 × 900 with internal scrolling |

Screenshots were retained only as ignored local review evidence because the browser frame contained unrelated personal browser chrome. They are not committed and are not required to use the documentation.

### Limitations of review

- One expert reviewer is not a substitute for representative usability participants.
- The review used representative synthetic local data, not weeks of naturally accumulated use.
- No provider call was made during this review. The normal-production Source Run pass is an authoritative prior result supplied for rc.3, not a new qualification claim.
- The repository-supported local UI composition intentionally blocked `Check Now`; processing, waiting, completion, provider-unavailable, budget-blocked, and unconfirmed-outcome states were therefore reviewed through current projections, copy, and tests rather than fresh live executions.
- A destructive reset was not used to manufacture a pristine empty database. Empty-state behavior was inspected in the current product source and existing projections, not by deleting user data.
- Device coverage was limited to Chrome desktop responsive emulation; there was no physical mobile-device study.
- This was a bounded accessibility review, not WCAG certification. No full screen-reader or contrast audit was performed.
- Browser auto-translation appeared during part of the review and was excluded from product findings; the product’s source language is English.

## Product Mental Model

### What the product appears to be

**Observed fact:** the Dashboard headline says “What changed that matters to you,” and each primary card leads with a conclusion, “Why this matters,” and “What is new.” Video title, timestamp, excerpt, and technical provenance follow inside Evidence.

**User-risk inference:** with populated data, the product can be understood as a personal intelligence reader. During setup and failure recovery, terms such as Source Run, Distillation style, provider/model readiness, Resource Usage, and execution guard make it feel like a video-processing/admin dashboard.

### What the intended product is

The intended product is an assistant that watches relevant YouTube on the user’s behalf and turns meaningful changes into useful, traceable intelligence. Video remains evidence, not the final product. The governing product principle is: information may be compressed, but its source must not be compressed away.

### Gap analysis

The consumption experience is closer to the intended product than the setup and operational experience. The conclusion-first card model is directionally right. The gap is the unsupported transition from “I want AI to watch this channel” to “I have my first useful Intelligence,” plus insufficient synthesis for returning users.

**Design recommendation:** make the default user journey read as `Add a YouTube Source → choose what matters → run/monitor → read new Intelligence → verify Evidence`, while keeping provider, scheduling, and execution detail available progressively.

**Personal design preference:** a somewhat denser visual style might feel more polished, but density alone is not a product defect. The product issue is prioritization and comprehension, not personal taste.

## First-Time User Journey

### 1. First open

The populated Dashboard answers “what should I look at first?” through “What matters now,” but the brand and subtitle do not explicitly explain the product’s job. A true empty-state projection does instruct the user to add a Source and says that conclusions will appear with Evidence; this is a good foundation.

Five-second comprehension result:

| Question | Result |
| --- | --- |
| What is this product for? | Partial; inferable from cards, not directly stated |
| What has changed? | Good; New/Updated and “What is new” are visible |
| What should I look at first? | Good; “What matters now” is the clear primary section |
| What can I do next? | Partial; Save and See all Intelligence exist, but first-use guidance is absent |
| Is anything blocking me? | Weak; Needs Attention is below three long cards and Weekly |

### 2. Add the first Source

The form explains Initial history and Per-run limit better than their labels alone. However, it presents URL, processing level, monitoring, Initial history, Per-run limit, Focus, Ignore, Distillation style, automatic schedule, time, and enablement in one pass. The default is a daily enabled schedule.

**User-risk inference:** Persona A may treat every field as required, may not know what useful Focus terms look like, and may not realize that saving the default creates recurring future work once all gates are available.

### 3. Become ready to run

The UI contains no credential entry and Settings correctly never reveals credential values. That security posture should remain. The missing product layer is a plain readiness checklist that tells the user whether the installed product has an approved provider, credential, budget, and runnable Source execution path.

### 4. Run now and wait

`Check Now` is correctly separated from adding or editing a Source. In the reviewed local composition it returned a safe blocked message and did not create a Source Run. The source helper says this is not a retry action. Current product projections support queued/running/completed/attention states, but the UI offers little expectation about elapsed time or next stage.

### 5. Understand first output

Once Intelligence exists, a user can answer “What did I learn?”, “Why do I care?”, “Is it new?”, “Can I trust it?”, and “Where did it come from?” within one card. This is the strongest portion of the journey.

### Time to value

Active setup can fit within 5–10 minutes for an operator who already has a running rc.3 workspace, a valid YouTube Source, an indirectly provisioned NVIDIA credential, available budget, and a runnable production composition. Processing time is variable and excluded from this estimate.

Friction before first value:

1. installation/startup is operator-oriented;
2. provider credential cannot be configured or checked from a guided setup;
3. the Source form exposes many choices;
4. validation errors are generic;
5. waiting lacks a clear progress expectation;
6. a blocked state may send the user to Settings without a direct anchor or resolution action.

Useful value could be delivered with fewer initial choices: URL, monitoring on/off, and a simple outcome preset. History, per-run limit, filters, style, and schedule can be summarized with safe defaults and expanded on request.

## Repeat User Journey

The product provides New/Updated badges, topic change, Weekly, Saved, and Needs Attention, which are the right recurring-use signals. A returning user can see that something changed but cannot easily distinguish “new information” from a reformulation across many items. Three fully expanded cards create substantial scrolling before Topics, Weekly, and blockers.

Saved behaves as a durable reference rather than a stale cache, which is correct. Topics hold a current understanding and history rather than acting as plain folders, but the current page does not yet expose enough competing positions, change explanation, or evidence relationships to support sustained sense-making. Weekly shows an honest historical snapshot and correction, but one item reads more like an archived Intelligence card than a weekly synthesis.

## Screen-by-Screen Audit

### Dashboard

- **SCREEN:** Dashboard
- **PURPOSE:** orient the user to what matters now, what changed, and what needs action.
- **WHAT USER EXPECTS:** prioritized changes, a clear next step, and visible blockers.
- **WHAT USER ACTUALLY SEES:** three vertically stacked full Intelligence cards, then Topic changes, This week, and Needs Attention. `E01`, `E11`, `E12`.
- **PRIMARY ACTION:** read the first Intelligence conclusion.
- **SECONDARY ACTIONS:** Save, open all Intelligence, open Weekly, open Evidence links.
- **FIRST-GLANCE CLARITY:** strong for a populated repeat-user state; partial for product purpose and first use.
- **INFORMATION HIERARCHY:** conclusion-first is strong; the three expanded Evidence blocks dominate lower sections.
- **TERMINOLOGY:** mostly human; claim labels require explanation.
- **TRUST CLARITY:** high because Evidence is adjacent.
- **EMPTY STATE:** helpful Add Source direction in the current projection; not exercised after destructive reset.
- **ERROR STATE:** Needs Attention is truthful but visually late.
- **RESPONSIVE QUALITY:** no observed horizontal clipping; vertical cost becomes substantial at 768 × 900.
- **ACCESSIBILITY OBSERVATIONS:** heading structure and text status labels are present; repeated `Save` controls lack item-specific accessible names.
- **MAIN PROBLEMS:** blockers are buried; first-use value proposition and action are not explicit; excessive default expansion.
- **SEVERITY:** P2.
- **RECOMMENDATION:** surface blockers/status above the feed and show compact evidence summaries with one-step expansion, never removing source traceability.

### Intelligence

- **SCREEN:** Intelligence — Current
- **PURPOSE:** provide a verified, evidence-linked feed.
- **WHAT USER EXPECTS:** quickly scan what was learned and open detail when needed.
- **WHAT USER ACTUALLY SEES:** three complete cards with conclusion, relevance, novelty, details, claim type/state, Evidence, and Save. `E02`.
- **PRIMARY ACTION:** read a conclusion.
- **SECONDARY ACTIONS:** verify Evidence, Save, expand technical provenance.
- **FIRST-GLANCE CLARITY:** high at card level.
- **INFORMATION HIERARCHY:** semantically strong but physically dense.
- **TERMINOLOGY:** “Supported statement” is not self-defining; “Technical provenance” exposes identifiers rather than an explanation.
- **TRUST CLARITY:** high.
- **EMPTY STATE:** truthful no-current-intelligence state in the projection.
- **ERROR STATE:** unavailable content fails closed.
- **RESPONSIVE QUALITY:** readable single column; long at narrow height.
- **ACCESSIBILITY OBSERVATIONS:** headings are meaningful; repeated Save labels are ambiguous out of context.
- **MAIN PROBLEMS:** scan density, claim-kind comprehension, and repeated action naming.
- **SEVERITY:** P2.
- **RECOMMENDATION:** preserve the semantic hierarchy, shorten collapsed cards, add plain-language claim definitions, and give actions item-specific accessible names.

### Topics

- **SCREEN:** Topics list and Topic detail
- **PURPOSE:** maintain an evolving understanding rather than a folder of items.
- **WHAT USER EXPECTS:** current view, what changed, confidence/disagreement, timeline, and linked evidence.
- **WHAT USER ACTUALLY SEES:** one Topic with current understanding, an unavailable-support state, one disagreement timeline row, technical evidence references, and no related Topics. `E05`.
- **PRIMARY ACTION:** open or Pin Topic.
- **SECONDARY ACTIONS:** inspect Evidence and history.
- **FIRST-GLANCE CLARITY:** medium; “current understanding” is promising but thin.
- **INFORMATION HIERARCHY:** current understanding leads appropriately.
- **TERMINOLOGY:** Pin is not explained as follow/return behavior.
- **TRUST CLARITY:** truthful unavailability, weak source-level trace from the timeline.
- **EMPTY STATE:** clear when no Topics exist.
- **ERROR STATE:** fail-closed support state is strong.
- **RESPONSIVE QUALITY:** compact and readable.
- **ACCESSIBILITY OBSERVATIONS:** headings are clear; no color-only status observed.
- **MAIN PROBLEMS:** the page does not yet reveal the competing positions or why understanding changed; Pin returns the user to the list, causing orientation loss.
- **SEVERITY:** P2.
- **RECOMMENDATION:** keep the persistent-object model but show a concise change summary, confidence/uncertainty, named supporting/contradicting Intelligence, and remain on the Topic after Pin.

### Sources

- **SCREEN:** Sources list and Add Source
- **PURPOSE:** choose what the product monitors and how.
- **WHAT USER EXPECTS:** paste a channel/video URL and start with safe defaults.
- **WHAT USER ACTUALLY SEES:** friendly source names and status rows; the form exposes all policy and schedule controls at once. `E06`, `E13`.
- **PRIMARY ACTION:** Add Source.
- **SECONDARY ACTIONS:** open Source, open original channel.
- **FIRST-GLANCE CLARITY:** list is clear; setup is decision-heavy.
- **INFORMATION HIERARCHY:** processing and schedule groups help, but essentials and advanced controls are not separated.
- **TERMINOLOGY:** Initial history and Per-run limit are explained; Distillation style and Source Run remain technical.
- **TRUST CLARITY:** monitoring copy preserves existing Intelligence; recurring external work/cost implications are not summarized before save.
- **EMPTY STATE:** Add Source is an obvious action.
- **ERROR STATE:** invalid URL produced a generic “Request values are invalid or unavailable” banner rather than a field-specific example.
- **RESPONSIVE QUALITY:** form fits at 768 × 900 using internal scroll; long but usable.
- **ACCESSIBILITY OBSERVATIONS:** the Add Source dialog appears in the accessibility tree and required URL validation focuses the field.
- **MAIN PROBLEMS:** too many first-use decisions, generic URL recovery, and implicit daily scheduling.
- **SEVERITY:** P2.
- **RECOMMENDATION:** use a starter preset and progressive disclosure; show a final summary of monitoring cadence and possible external-model usage.

### Source detail

- **SCREEN:** Source detail
- **PURPOSE:** inspect and control one monitored source.
- **WHAT USER EXPECTS:** status, next/last run, recent videos, and clear actions.
- **WHAT USER ACTUALLY SEES:** monitoring state, policy summary, schedule, Check Now, recent videos, skipped state, and Source Run status. `E07`, `E09`.
- **PRIMARY ACTION:** Check Now.
- **SECONDARY ACTIONS:** edit configuration, stop future monitoring, open source, Analyze this Video.
- **FIRST-GLANCE CLARITY:** medium; the detail is comprehensive but operational.
- **INFORMATION HIERARCHY:** controls lead; result/progress and next expected outcome are less prominent.
- **TERMINOLOGY:** “safe processing path,” “Source Run,” and “not a retry action” require system knowledge.
- **TRUST CLARITY:** strong on future-only monitoring changes and relevance-only override boundaries.
- **EMPTY STATE:** recent-video and no-run states are explicit.
- **ERROR STATE:** safe block message preserves data but does not always give a resolvable next action.
- **RESPONSIVE QUALITY:** long modal/detail scroll.
- **ACCESSIBILITY OBSERVATIONS:** opening Edit configuration inside Source detail produced a visual nested dialog that was absent from the accessibility tree; Tab moved focus to a control behind it and Escape did not close it.
- **MAIN PROBLEMS:** keyboard blocker, weak progress expectations, operational language.
- **SEVERITY:** P1.
- **RECOMMENDATION:** fix dialog focus containment/semantics in rc.4; present processing stages and next action in user language without weakening execution gates.

### Skipped videos / Analyze this Video

- **SCREEN:** Recent videos within Source detail
- **PURPOSE:** explain why a video was skipped and allow an intentional relevance override.
- **WHAT USER EXPECTS:** reason, consequence, and whether manual analysis is safe.
- **WHAT USER ACTUALLY SEES:** Skipped, an ignore-rule reason, Analyze this Video, and exact copy that other safety, budget, and model rules still apply. `E09`.
- **PRIMARY ACTION:** Analyze this Video.
- **SECONDARY ACTIONS:** none in the row.
- **FIRST-GLANCE CLARITY:** high.
- **INFORMATION HIERARCHY:** reason precedes override.
- **TERMINOLOGY:** “relevance” is understandable with the helper.
- **TRUST CLARITY:** excellent boundary copy.
- **EMPTY STATE:** not applicable.
- **ERROR STATE:** the local demo acknowledged the override while the visible row remained Skipped, making completion status unclear.
- **RESPONSIVE QUALITY:** readable.
- **ACCESSIBILITY OBSERVATIONS:** button name is descriptive.
- **MAIN PROBLEMS:** post-action state/progress is ambiguous in the reviewed composition.
- **SEVERITY:** P2 as part of run feedback.
- **RECOMMENDATION:** preserve the exact safety boundary and show a durable queued/running/blocked result after the override.

### Investigations

- **SCREEN:** Investigations
- **PURPOSE:** none in current V1; the page reserves a future capability.
- **WHAT USER EXPECTS:** an investigation workflow because it is top-level navigation.
- **WHAT USER ACTUALLY SEES:** Unavailable and a list of non-V1 capabilities. `E08`.
- **PRIMARY ACTION:** none.
- **SECONDARY ACTIONS:** none.
- **FIRST-GLANCE CLARITY:** clear that it is unavailable, unclear why it occupies primary navigation.
- **INFORMATION HIERARCHY:** simple.
- **TERMINOLOGY:** “Reserved V2 capability” is roadmap/internal language.
- **TRUST CLARITY:** high; no false availability.
- **EMPTY STATE:** the entire page is an unavailable state.
- **ERROR STATE:** not applicable.
- **RESPONSIVE QUALITY:** good.
- **ACCESSIBILITY OBSERVATIONS:** simple heading and text.
- **MAIN PROBLEMS:** expectation cost and future-roadmap leakage.
- **SEVERITY:** P3 under the frozen rc.3 IA; strategic for future IA.
- **RECOMMENDATION:** do not change frozen IA in this review; for a later release, mark the nav item unavailable before entry or omit it until there is a user action.

### Settings

- **SCREEN:** Settings
- **PURPOSE:** show preferences, model readiness, resource truth, and privacy.
- **WHAT USER EXPECTS:** know whether the product is ready, what it uses externally, and what it may cost.
- **WHAT USER ACTUALLY SEES:** Preference Center, Source defaults, NVIDIA NIM/Kimi availability and scope, Deep Analysis unavailable, other unavailable models, Resource Usage, and local-first privacy copy. `E10`.
- **PRIMARY ACTION:** review preferences/readiness.
- **SECONDARY ACTIONS:** expand provider/model and technical details.
- **FIRST-GLANCE CLARITY:** medium; preference controls precede the readiness information referenced by failure messages.
- **INFORMATION HIERARCHY:** technical truth is present but resolution-critical model readiness is not anchored from Needs Attention.
- **TERMINOLOGY:** provider versus model, Video Distillation, production availability, and Resource Usage need plain definitions.
- **TRUST CLARITY:** high; exact scope and unavailable capabilities are not hidden.
- **EMPTY STATE:** not applicable.
- **ERROR STATE:** unavailable capabilities are explicit and non-actionable.
- **RESPONSIVE QUALITY:** long but stable.
- **ACCESSIBILITY OBSERVATIONS:** disclosure controls are named; no formal contrast assessment.
- **MAIN PROBLEMS:** readiness/resolution hierarchy and technical terminology.
- **SEVERITY:** P2.
- **RECOMMENDATION:** add a user-facing readiness summary and direct anchors; keep exact provider/model and scope as advanced disclosure.

### Saved

- **SCREEN:** Intelligence — Saved
- **PURPOSE:** return to important Intelligence.
- **WHAT USER EXPECTS:** a stable bookmark/read-later/reference collection.
- **WHAT USER ACTUALLY SEES:** a current saved item and an unavailable saved reference with Unsave. Stale detail is not rendered. `E03`.
- **PRIMARY ACTION:** open/read saved Intelligence.
- **SECONDARY ACTIONS:** Unsave, verify Evidence.
- **FIRST-GLANCE CLARITY:** medium; the collection works but Save is not defined.
- **INFORMATION HIERARCHY:** fail-closed message is appropriately prominent.
- **TERMINOLOGY:** Save could mean bookmark, read later, or knowledge-base inclusion.
- **TRUST CLARITY:** high; unavailable trusted content remains unavailable.
- **EMPTY STATE:** clear but should define what belongs here.
- **ERROR STATE:** strong fail-closed behavior.
- **RESPONSIVE QUALITY:** consistent with Intelligence.
- **ACCESSIBILITY OBSERVATIONS:** Unsave is clear; repeated Save naming elsewhere is not contextual.
- **MAIN PROBLEMS:** mental model and success feedback.
- **SEVERITY:** P2.
- **RECOMMENDATION:** define Saved as a personal reference list; show a brief saved confirmation and retain fail-closed behavior.

### Weekly

- **SCREEN:** Intelligence — Weekly
- **PURPOSE:** answer “What mattered this week?”
- **WHAT USER EXPECTS:** prioritized synthesis, change emphasis, and confidence that no filler was added.
- **WHAT USER ACTUALLY SEES:** one historical weekly item, a Topic, claim/state, correction notice, and a technical reference hash. `E04`.
- **PRIMARY ACTION:** read the weekly summary.
- **SECONDARY ACTIONS:** expand Evidence references.
- **FIRST-GLANCE CLARITY:** medium.
- **INFORMATION HIERARCHY:** correction is clear; prioritization rationale and cross-item synthesis are absent.
- **TERMINOLOGY:** historical snapshot and correction are understandable; hash is not.
- **TRUST CLARITY:** immutable history is honest, direct source/video/timestamp trace is weak.
- **EMPTY STATE:** current product has an honest “no important changes” state; not visually exercised during this review.
- **ERROR STATE:** corrected state is explicit.
- **RESPONSIVE QUALITY:** compact.
- **ACCESSIBILITY OBSERVATIONS:** disclosure is named; technical reference has little spoken meaning.
- **MAIN PROBLEMS:** reads as a single archived card rather than a synthesized week; evidence reference is not user-actionable.
- **SEVERITY:** P2.
- **RECOMMENDATION:** lead with 1–3 prioritized changes and why they mattered, preserve honest no-change output, and link each point to readable Evidence.

### Evidence

- **SCREEN:** Evidence block inside Intelligence/Topic/Weekly
- **PURPOSE:** let the user verify what was said and where.
- **WHAT USER EXPECTS:** Source → Video → Timestamp → Excerpt with optional technical provenance.
- **WHAT USER ACTUALLY SEES:** the complete chain on Intelligence; Topics/Weekly may fall back to unavailable or opaque technical references. `E02`, `E04`, `E05`.
- **PRIMARY ACTION:** open the timestamped video.
- **SECONDARY ACTIONS:** open Source, expand technical provenance.
- **FIRST-GLANCE CLARITY:** high on Intelligence, low for hash-only references.
- **INFORMATION HIERARCHY:** user evidence correctly precedes technical provenance.
- **TERMINOLOGY:** Evidence is appropriate; technical provenance needs translation.
- **TRUST CLARITY:** high when the full chain exists.
- **EMPTY STATE:** fails closed rather than inventing evidence.
- **ERROR STATE:** unavailability is explicit.
- **RESPONSIVE QUALITY:** excerpts wrap without observed horizontal overflow.
- **ACCESSIBILITY OBSERVATIONS:** timestamp links include time in accessible description.
- **MAIN PROBLEMS:** default evidence bulk and hash-only secondary surfaces.
- **SEVERITY:** P2/P3 depending on surface.
- **RECOMMENDATION:** keep provenance reachable, show a one-line evidence summary by default, and explain technical identifiers only in advanced detail.

### Needs Attention

- **SCREEN:** Dashboard and Source detail attention states
- **PURPOSE:** explain blockers without unsafe automatic recovery.
- **WHAT USER EXPECTS:** what happened, impact, action, and what the system will not do.
- **WHAT USER ACTUALLY SEES:** model unavailable was visually exercised; current copy for credential/model unavailable, budget blocked, unconfirmed external result, and user decision required was inspected in the current product. The unconfirmed state explicitly has no Retry action.
- **PRIMARY ACTION:** resolve the stated prerequisite.
- **SECONDARY ACTIONS:** inspect Source or Settings.
- **FIRST-GLANCE CLARITY:** copy is calm and safe; resolution path is often indirect.
- **INFORMATION HIERARCHY:** Dashboard placement is too low.
- **TERMINOLOGY:** generally human-facing; “model availability” still assumes provider knowledge.
- **TRUST CLARITY:** high; existing Sources/Intelligence are said to remain unchanged.
- **EMPTY STATE:** not applicable.
- **ERROR STATE:** this is the error/recovery surface.
- **RESPONSIVE QUALITY:** readable but easy to miss below the feed.
- **ACCESSIBILITY OBSERVATIONS:** status is text, not color-only.
- **MAIN PROBLEMS:** no direct anchored action, no consolidated source/status context, and low Dashboard priority.
- **SEVERITY:** P2.
- **RECOMMENDATION:** use a consistent four-part pattern—what happened, why it matters, what to do, what will not happen—and add safe deep links. Never add automatic retry to an unconfirmed external outcome.

### Resource Usage

- **SCREEN:** Settings — Resource Usage
- **PURPOSE:** show calls, tokens, duration, cost availability, and status.
- **WHAT USER EXPECTS:** know what work incurred usage and whether cost is known.
- **WHAT USER ACTUALLY SEES:** several nearly identical “Recorded work” rows with call count, 0 ms or unavailable measures, Completed, and technical provider/model details. `E10`.
- **PRIMARY ACTION:** inspect a record.
- **SECONDARY ACTIONS:** expand technical details.
- **FIRST-GLANCE CLARITY:** low for comparison.
- **INFORMATION HIERARCHY:** values exist but lack date, Source/video, purpose, or grouping.
- **TERMINOLOGY:** “Cost unavailable” can be misread as free unless explicitly explained.
- **TRUST CLARITY:** data is not fabricated; identity and meaning are weak.
- **EMPTY STATE:** truthful when no records exist.
- **ERROR STATE:** unknown values are shown as unavailable.
- **RESPONSIVE QUALITY:** rows stack correctly.
- **ACCESSIBILITY OBSERVATIONS:** disclosures are named but repetitive.
- **MAIN PROBLEMS:** indistinguishable records and insufficient UNKNOWN-cost explanation.
- **SEVERITY:** P2.
- **RECOMMENDATION:** label work by date/source/purpose, group totals, and state next to the value that unknown cost is not zero or free.

## Information Architecture

The frozen top-level IA was not changed.

- Dashboard has a distinct orientation job.
- Intelligence is the primary reading archive; Saved and Weekly are tabs and are discoverable after entering Intelligence. Dashboard’s Weekly link helps.
- Topics is directionally distinct, though the current object is still too thin.
- Sources is clearly configuration/monitoring.
- Investigations is confusing because its top-level position implies an active workflow.
- Settings is the right home for Resource Usage and advanced provider details, but resolution links should target specific sections.

### FUTURE_IA_RECOMMENDATIONS

1. Keep the user-goal order Dashboard → Intelligence → Topics → Sources.
2. Do not expose Investigations as an equal destination until it has a real V1/V2 user action; if contractual navigation must remain, show an unavailable badge in the nav.
3. Keep Saved and Weekly under Intelligence unless user testing shows retrieval problems; add visible counts or Dashboard entry points before creating more top-level destinations.
4. Keep Resource Usage in Settings, with a direct link from budget-related Needs Attention.

## Terminology

| Current term | User likely interpretation | Problem | Recommended product language |
| --- | --- | --- | --- |
| Source | a website or citation | In this product it means a monitored YouTube channel or video | “YouTube Source” on first use; define Source thereafter |
| Intelligence | secret/official intelligence or AI output | Value is unclear until a card is seen | “Useful, evidence-linked finding” in onboarding |
| Topic | folder/tag | Current product intends an evolving understanding | “Topic — an understanding that updates over time” |
| Evidence | proof | One video excerpt supports traceability, not universal truth | “Evidence from the source video” |
| Initial history | all back catalog | Actually a bounded number of recent existing videos on first add | “Recent videos to check first” |
| Per-run limit | technical job constraint | User cannot predict backlog behavior | “Maximum new videos per check” |
| Focus | highlight words | It changes automatic relevance selection | “Prefer videos about…” with examples |
| Ignore | mute words | It excludes automatic relevance selection | “Skip videos about…” with examples |
| Distillation style | model compression format | Technical and academic | “Intelligence style” or “Summary emphasis”; keep Distillation in advanced detail |
| Check Now | refresh UI | It starts a new safe Source check when gates allow | “Check for new videos now” |
| Analyze this Video | bypass every rule | It overrides relevance only | “Analyze despite relevance skip” plus current safety copy |
| Needs Attention | generic alert | Good umbrella label, but action is not inherent | Keep; add direct action and affected Source |
| Resource Usage | device resources | Actually model calls/tokens/duration/cost truth | “AI usage and cost” with Resource Usage as advanced term |
| Deep Analysis | more thorough version of current card | It is unavailable and might imply an upsell | “Deep Analysis — unavailable in this version” |
| Supported statement | verified fact | Evidence support can be mistaken for universal truth | “Statement supported by the cited video” |
| Source Run | technical batch/job | Not meaningful to normal users | “Source check”; reserve Source Run for technical details |
| Pin Topic | pin layout item | Intended persistence/following is unclear | “Follow Topic” if the semantics match; otherwise explain Pin |

## Trust & Evidence Experience

The strongest trust sequence is visible on Intelligence:

`Source → Video → Timestamp → Transcript excerpt → optional technical provenance`

This supports verification without requiring architecture knowledge. Timestamp links are intuitive and excerpts are readable. Claim type and lifecycle state are separate, which prevents “New” from being mistaken for “True.”

Risks:

- “Fact” or “Supported statement” may receive more authority than a single cited source warrants.
- Full Evidence on every card interrupts scanning.
- Weekly and Topic references can degrade to opaque hashes.
- Technical provenance is discoverable but not meaningful to most users.

Recommended balance: keep Source, video, timestamp, and a short excerpt one interaction away; collapse repeated detail after a readable evidence summary; never hide or remove provenance entirely.

## Error / Recovery Experience

The product’s recovery posture is safer than average. It says existing Intelligence remains unchanged, blocks work before unsupported model/provider/budget conditions, and does not automatically retry an external result that could not be confirmed. Analyze this Video overrides relevance only.

The UX gap is actionability. Attention items should consistently state:

1. what happened;
2. why it matters;
3. what the user can do;
4. what the system will and will not do.

Missing credential and model unavailable should lead to readiness guidance, budget blocked to the relevant Resource Usage context, decision required to the precise Source setting, and unconfirmed external outcome to a read-only status explanation with no retry.

## Responsive / Accessibility Review

### Responsive observations

- 1440 × 900: left navigation and content hierarchy are stable; three full cards still create a long Dashboard.
- 1280 × 800: no observed clipping; the same vertical prioritization issue remains.
- 768 × 900: navigation becomes a horizontal top bar, cards become single-column, long text wraps, and Evidence remains within width. One Intelligence card occupies most of the first viewport. Add Source uses internal scrolling and remains operable.

The previously accepted “three cards can remain vertically long” P3 judgment should be revised to P2 for repeat use: the cost is not mere polish when Weekly and Needs Attention are several screens below the first decision point.

### Accessibility observations

Positive:

- visible heading hierarchy;
- text labels accompany status colors;
- timestamp links name the target time;
- Add Source inputs have labels;
- keyboard focus is visibly styled on standard controls.

Risks:

- **High:** nested Edit configuration dialog was not represented in the accessibility tree; focus moved behind it and Escape did not close it.
- **Medium:** repeated `Save` buttons do not name their Intelligence item.
- **Medium:** long modal and card content requires substantial keyboard/scroll traversal.
- **Unknown:** color contrast and full screen-reader behavior were not formally measured.

**ACCESSIBILITY_RISK: HIGH**, driven by the reproducible modal focus/accessibility-tree failure. This is not a WCAG certification statement.

## Product Consistency

Verified consistencies:

- Save/Unsave maps consistently to the Saved tab.
- Source versus Open Source is consistently used for the monitored object versus external link.
- Evidence consistently names provenance areas.
- New/Updated/Unavailable states use text, not only color.

Verified inconsistencies or mental-model gaps:

- User action is `Check Now`, while descriptions use Source Run and safe processing path.
- Source setup says “Turn relevant videos into Intelligence,” while Settings calls the same provider scope “Video Distillation.”
- Topic uses Pin while first-use expectations are closer to Follow.
- “Supported statement” has no visible relationship to the legal claim kind `EVIDENCE_BACKED_STATEMENT` or to Fact.

## Top 10 Product Problems

| Rank | Issue | Root cause | Severity |
| ---: | --- | --- | --- |
| 1 | Standard local UI startup does not provide an ordinary-user path to a normal production Source Run or credential readiness | PRODUCT_MODEL | P1 |
| 2 | Nested Source edit dialog is not keyboard/accessibility-tree operable | ACCESSIBILITY | P1 |
| 3 | Add Source exposes too many decisions and silently defaults to enabled daily work | ONBOARDING | P2 |
| 4 | Dashboard card expansion buries Weekly and Needs Attention | INFORMATION_HIERARCHY | P2 |
| 5 | Run/override progress and completion feedback lacks a clear stage and next expectation | PERFORMANCE_PERCEPTION | P2 |
| 6 | Weekly is not yet a strong “what mattered” synthesis and its Evidence can be an opaque hash | PRODUCT_MODEL | P2 |
| 7 | Topics do not yet explain why understanding changed or show disagreement clearly | PRODUCT_MODEL | P2 |
| 8 | Needs Attention is safe but not directly actionable | ERROR_RECOVERY | P2 |
| 9 | Resource Usage rows are indistinguishable and UNKNOWN cost can be misread | TRUST_EXPLANATION | P2 |
| 10 | Claim kinds and operational terms require technical knowledge | COPY_TERMINOLOGY | P2 |

The complete issue records, alternatives, constraints, effort, and release recommendation are in [RC3_UX_IMPROVEMENT_BACKLOG.md](RC3_UX_IMPROVEMENT_BACKLOG.md).

## Strengths That Should NOT Be Accidentally Removed

1. Keep Intelligence conclusion-first; do not turn the feed into a video list.
2. Keep original Source, video, timestamp, and excerpt reachable.
3. Keep claim type separate from lifecycle state.
4. Keep opinion/prediction/rumor visibly attributed; do not style Fact as absolute truth.
5. Keep unavailable trusted content fail-closed; never show stale saved detail as current truth.
6. Keep unconfirmed external outcomes terminal and visible; do not add automatic retry.
7. Keep provider/model fallback absent and exact V1 scope visible.
8. Keep Deep Analysis unavailable until it is actually authorized and usable.
9. Keep cost unknown as unknown; never render unavailable cost as zero/free.
10. Keep monitoring changes future-only and preserve existing Intelligence.
11. Keep Analyze this Video limited to relevance override; all safety, budget, model, and provider rules must remain.
12. Keep historical Weekly corrections explicit rather than rewriting history silently.

## Product Success Hypotheses and Metrics

Future measurement should test useful outcomes, not raw call volume:

- median time from first open to first useful Intelligence;
- percentage of configured Sources that produce user-rated useful Intelligence;
- Evidence-open rate for high-impact claims;
- Save rate and later return-to-Saved rate;
- Topic return rate and percentage of Topic visits that include a meaningful change;
- Weekly return/read rate and “this helped me catch up” rating;
- Needs Attention resolution rate and time to resolution;
- percentage of cards rated useful/new versus repetitive;
- week-2 and week-4 repeat usage;
- user-reported trust and ability to verify an important claim.

No recommendation here requires telemetry in rc.3, and no metric should be optimized through dark patterns or unnecessary model calls.

## Persona Assessment

- **Persona A — AI-curious normal user:** low readiness without an operator. The consumption cards are understandable, but startup, credential readiness, and Source choices require help.
- **Persona B — product/technology professional:** medium-to-high value once data exists. Conclusion/relevance/novelty/Evidence is a strong structure; Weekly and Topic synthesis need more depth.
- **Persona C — power/trust-conscious user:** high confidence in preservation rules, medium usability. Provenance, claim types, scope, cost uncertainty, and fail-closed states are present, but Resource Usage and technical identifiers are difficult to reconcile.
- **Persona D — returning user:** medium readiness. New/Updated, Saved, Topics, and Weekly support return use, while Dashboard length and shallow change synthesis slow re-orientation.

## Independent Critique Answers

- **WHAT IS ALREADY GOOD?** The product leads with conclusions, distinguishes claim kind from lifecycle, keeps timestamps/excerpts reachable, names unavailable capabilities honestly, and protects existing trusted content.
- **WHAT SHOULD NOT BE CHANGED?** Evidence reachability, fail-closed Saved/Topic states, exact provider/model scope, no fallback, no unconfirmed-result retry, UNKNOWN cost truth, and relevance-only manual override.
- **WHAT IS CONFUSING?** Source Run versus Check Now, Video Distillation versus Intelligence, Supported statement versus Fact, Pin versus Follow, and how an installed UI becomes production-ready.
- **WHAT IS UNNECESSARILY COMPLEX?** The first Source form and the amount of provider/execution language required before first value.
- **WHAT IS MISSING?** A supported ordinary-user production startup/readiness path, durable progress expectations, direct recovery links, weekly prioritization, and a richer Topic change explanation.
- **WHAT COULD BE REMOVED?** For a future IA decision, the unavailable Investigations destination should not occupy equal top-level attention before it has a current action. No trust or Evidence content should be removed.
- **WHAT SHOULD BE PROGRESSIVELY DISCLOSED?** History limits, filters, style, schedule detail, provider/model identifiers, raw provenance IDs, and full repeated excerpts.
- **WHAT SHOULD BE DOCUMENTED RATHER THAN REDESIGNED?** Claim definitions, Save semantics, cost-unknown meaning, Analyze this Video boundaries, and current Deep Analysis/Investigations limitations all benefit immediately from documentation; the execution-path and modal-accessibility findings require product changes.

## External User Test Recommendation

Conduct a five-person moderated usability test **after the P1 rc.4 fixes and before a broader private trial**. Include at least first Source setup, readiness diagnosis, Check Now/waiting, reading and verifying one Intelligence item, saving/following, returning via Weekly, and resolving one Needs Attention state. Recruit by workflow needs represented by the four review personas, not demographics.

## Release Recommendation

**RC4_RECOMMENDATION: RC4_REQUIRED_BEFORE_BROADER_TRIAL**

Rationale:

- P0: 0
- P1: 3 total findings, including two open product issues and one documentation gap addressed by this review artifact
- P2: 10
- P3: 3
- core value is visible but first-time viability is low without expert/operator help;
- trust semantics are strong and should not be changed;
- the rc.4 gate should be limited to the ordinary-user execution/readiness path, the Source edit accessibility failure, and the highest-impact onboarding/recovery hierarchy cluster.

This recommendation does not authorize implementation. Product Owner decides which findings are accepted, rejected, documentation-only, rc.4, post-V1, or V2.
