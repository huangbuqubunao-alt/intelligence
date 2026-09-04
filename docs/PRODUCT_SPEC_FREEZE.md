# Product Specification Freeze — YouTube Intelligence Agent

Status: **APPROVED PRODUCT CONTRACT**
Freeze date: 2026-09-04
Scope: product contract and implementation planning only; this document authorizes no runtime, provider, schema, credential, or release change.

## 1. North star

The primary product is **personalized video distillation**. The agent consumes
YouTube videos on the user's behalf and turns source material into the
personalized intelligence the user needs, using long-term preferences, recent
preferences, temporary focus, and explicit feedback. The original video is
evidence and source context, not the default consumption destination.

The secondary product is **domain investigation**. It detects important,
high-relevance changes from distilled intelligence and early signals, then
runs a bounded, evidence-led Investigation that answers the user's questions.
It is not a news-feed popularity feature.

The capability chain is:

```text
CONFIGURE → SUBSCRIBE → SCHEDULE → DISCOVER → FILTER → PROCESS → DISTILL
→ EVIDENCE → INTELLIGENCE → TOPIC → FEEDBACK → LEARN → SIGNAL
→ INVESTIGATE → VERIFY → UPDATE → DAILY/WEEKLY → ASK
```

## 2. Product principles

1. **Compress information, never erase its source.** Every substantive
   Intelligence, Topic conclusion, timeline event, Brief item, Investigation
   answer, and saved Ask answer retains revision and evidence references.
2. **Personalization is user-controlled.** Feedback can change learned
   preference weights and presentation/ranking, but never silently changes an
   explicit interest, explicit ignore rule, enabled state, schedule, limit, or
   model selection.
3. **Evidence and interpretation are separate.** A source statement,
   translation, distillation, and system inference are distinct objects and
   visibly distinct in UI.
4. **Truthful absence beats fabricated completion.** Unknown, unavailable,
   blocked, disputed, or ambiguous states remain visible and are not repaired
   by inference, fallback, retry, or UI copy.
5. **Automation is bounded delegation.** All automated work has a trigger,
   priority, budget, frequency limit, execution record, safe resumption rule,
   and application-service/runtime owner.
6. **User controls depth and spend.** High-resource features are modular and
   actually stop executing when off; recommendations never alter spend or
   configuration without confirmation.
7. **Local-first means locally persisted by default, not never sent off
   device.** Every cloud-backed execution declares what data leaves the device
   and to which provider; credentials remain indirect runtime references.

## 3. Capability model

### Intake and distillation

`Check Now` checks a Source, discovers new videos, applies that Source's
current processing policy, processes eligible new videos, and updates Videos,
Activity, and Intelligence. It is not Retry. Source configuration includes:

- initial history: none, recent 1/3/5/10 (default 5);
- per-run maximum new videos: configurable, default 5, including 1/3/5/10;
- global focus/ignore rules with Source override;
- global distillation style with Source override: balanced,
  technical-detail-first, product/case-first, or trend/opinion-first.

Filtering is staged: inexpensive metadata decides clear relevance or clear
skip first; only ambiguous candidates receive more content inspection. Skipped
videos remain visible with their reason. A user may explicitly Analyze this
video, which overrides automatic relevance filtering only; it does not bypass
runtime, qualification, budget, evidence, or AMBIGUOUS safeguards.

Completed work produces an **Intelligence Card**, not a recommendation about
whether to watch the original. It contains personalized core conclusions,
relevant new information, important details/data/cases, filtered noise,
evidence/source links, and original transcript context when needed.

### Preference and feedback

Preference memory is partitioned into long-term, recent, and expiring
temporary focus. Temporary focus has an explicit expiry (for example 7 days,
30 days, or a user-defined time) and must not pollute long-term preference.
The Content Preference Center lets users view, edit, and delete long/recent
preferences. AI may suggest promotion to long-term, but the user confirms any
permanent rule.

Quick feedback is More like this, Less like this, and This is important; a
natural-language feedback channel is also available. Factual correction is a
separate workflow from preference feedback.

### Knowledge and intelligence

The information hierarchy is `Video → Intelligence → Topic → Brief /
Investigation / Ask`. Video remains raw material and evidence context; it is
not the final knowledge unit. Topics are live, long-lived objects with current
state, light related-topic links, source-backed timeline events, user-managed
create/rename/merge/split/pin operations, and AI assistance under user control.
Cross-video clustering, association, deduplication, and source linking do not
depend on blocked Deep Analysis.

Confidence labels are High, Medium, Low, and Insufficient Evidence. The system
may say which position current evidence better supports and why, but never
uses invented percentage precision. Conflicting sources are consensus,
disagreement, or unresolved—not silently collapsed into one fact.

### Briefs, dashboard, and Ask

Dashboard is an Intelligence entry point: what is worth knowing today, changes
to pinned Topics, key weekly changes, and genuine Needs Attention. Operational
metrics are secondary. Notifications are conservative: Critical Only is the
default; Critical + Important and Off are alternatives. V1 channels are only
in-app and desktop system notification.

Weekly is cross-video, deduplicated personalized intelligence by Intelligence
and Topic, not a video list. Daily is the prior 24 hours' genuine information
gain; an empty daily may explicitly say there was nothing worth interrupting
the user for. Daily generation aggregates existing Intelligence rather than
forcing a full Source check. Daily and Weekly are immutable historical
snapshots; later corrections add supersession markers rather than rewriting
history. Save Intelligence and Pin Topic are V1; folders/tags are not.

Ask defaults to the user's own trusted Intelligence/evidence assets only,
without automatic public-web search. Results are read-only until an explicit
save confirmation creates a new intelligence asset with inherited provenance.

### Investigation and signals

Early Signal is separate from confirmed Intelligence and can be upgraded,
watched, downgraded, invalidated, or archived. It is V2-active only. Evidence
Expansion may use bounded, original external sources (official site/docs/
GitHub/paper) for important claims, signals, and disagreements; an externally
discovered source never becomes a subscribed Source.

An Investigation is a first-class active inquiry—not a Topic alias—with goals,
questions, source scope, budget, frequency ceiling, and exit conditions. Auto
creation requires high relevance, important change, explicit unanswered
questions, and minimum evidence. Its lifecycle is `CANDIDATE → ACTIVE →
WAITING → NEEDS_ATTENTION → COMPLETED | ARCHIVED`, and it may be reopened.
Completed results are structured Intelligence assets with answer status,
evidence, unresolved questions, confidence/reasons, timeline, monitoring
decision, linked Topics, Brief projection, and what it means for this user.

## 4. Frozen V1 and reserved V2

| V1 active product contract | V2 reserved, not active in V1 |
| --- | --- |
| Source configuration, configurable history/per-run cap, Source focus/ignore and style | Advanced confidence evolution and deeper source profiles |
| Check Now definition, two-stage filtering, skipped visibility, manual analyze override | Early Signal, automatic Investigation, Evidence Expansion, original-source validation |
| Personalized Intelligence Card, evidence/provenance, basic Topic clustering/current state/timeline foundation | Daily Brief, Ask, advanced correction-impact UI and stronger cross-source synthesis |
| Feedback, preference center, long/recent/temporary preferences, Save/Pin | Advanced resource optimization suggestions |
| Weekly foundation, schedule foundation, priority queue, budget/model policy, ledger, Needs Attention, safe resume | Deep Analysis only after genuine provider qualification and authorization |
| Frozen primary IA | Investigation depth and templates become executable only with V2 authorization |

V2 reservation requires extendable IDs, revisions, evidence references, and
dependency edges in V1; it does not authorize placeholder execution, invented
claims, provider calls, or schema changes.

## 5. Non-goals and prohibited behavior

- Current distribution posture remains private/proprietary and controlled. This
  product freeze does not authorize public distribution, hosting, release,
  package publication, tag, or provider qualification work.
- The product does not optimize for "should I watch this video?" or make the
  original video its primary destination.
- V1 does not become an unbounded web-search product, multi-user SaaS, public
  deployment, credential console, or direct provider/browser integration.
- No silent provider/model fallback, quality downgrade, spending increase,
  auto-redispatch of AMBIGUOUS work, retry-until-valid, app-side JSON repair,
  first-JSON extraction, fence stripping, or second-LLM repair.
- No claim that Deep Analysis is V1-available. It remains BLOCKED while no
  provider is AVAILABLE + QUALIFIED + AUTHORIZED/PRODUCTION_ELIGIBLE.
- No inference of Note authority from filename/frontmatter/video ID; Note V1
  and V2 remain UNAVAILABLE without their authoritative association.
- No rewriting historical Daily/Weekly, no unsupported ghost intelligence
  after evidence deletion, and no fabricated cost/token/certainty precision.

## 6. Acceptance principles

An implementation slice is product-acceptable only when it proves all of the
following for its scope:

1. Stable IDs/revisions/evidence links, not copied conclusion text, connect
   derived assets to their source state.
2. User intent, business content, execution state, and immutable history are
   independently represented.
3. Trust, credentials, qualified-provider identity, authoritative scoring,
   Note, Weekly, and AMBIGUOUS runtime contracts are preserved without UI or
   orchestration bypass.
4. A disabled high-cost feature produces no corresponding execution; a budget
   stop pauses the relevant step rather than changing quality silently.
5. Destructive deletion presents downstream impact and never leaves a current
   unsupported claim as if it were evidenced.
6. The UI makes raw video/transcript/evidence naturally reachable as context
   while keeping Intelligence as the primary consumption layer.

## 7. Supersession statement

For product IA and product priority, this freeze supersedes the old primary
navigation in `FRONTEND_PRODUCT_ARCHITECTURE.md` and
`FRONTEND_PRODUCT_ARCHITECTURE_AMENDMENT.md` (Dashboard / Sources / Videos /
Weekly / Automation / Activity / Settings). Their application-service,
local-only, authority, credential, scheduler, scoring, Note, Weekly, Deep
Analysis, and dispatch safeguards remain in force unless this freeze repeats
or strengthens them.
