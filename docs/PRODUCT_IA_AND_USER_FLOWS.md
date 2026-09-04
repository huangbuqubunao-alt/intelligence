# Product IA and User Flows — Frozen

Status: **APPROVED PRODUCT CONTRACT**

## 1. Primary navigation

The only frozen primary navigation is:

```text
Dashboard | Intelligence | Topics | Sources | Investigations | Settings
```

`Videos` is raw-material/context navigation under Source and Intelligence
contexts, not a primary destination. `Activity` is operational/supporting
context under Needs Attention, Source, Intelligence, or Settings. The earlier
Dashboard / Sources / Videos / Weekly / Automation / Activity / Settings IA is
superseded for all future product work.

## 2. Page responsibilities

| Page | V1 visible responsibility | V2 reserved affordance |
| --- | --- | --- |
| Dashboard | Personalized entry: today's meaningful intelligence, pinned Topic changes, weekly changes, genuine Needs Attention; operations second | Conservative notification center, Daily projection |
| Intelligence | Feed, Intelligence Card, Daily/Weekly foundation, Saved, and Video/original context | Ask answer save, richer cross-source synthesis |
| Topics | List/detail, current state, evidence, confidence, light related Topics, timeline, Pin | Advanced relations/confidence evolution |
| Sources | Channel/video subscriptions, initial history, cap, focus/ignore, style, schedule, source profile/activity/recent videos | Expanded source profiling and external-source boundary display |
| Investigations | V1 reserved, non-executing explanation of unavailable/future capability only | Candidate/active/waiting/needs-attention/completed/archived Investigation workflow |
| Settings | Content Preference Center; Model & Cost; Automation; Notifications; Data/Privacy; Advanced/System; resource history/activity as context | Deep Investigation controls once separately authorized |

Raw transcript, source video, timestamps, skip reason, and evidence remain
reachable from an Intelligence Card, Topic conclusion, or Source context. The
reduced prominence of Videos must never hide primary source material.

## 3. V1 user flows

### First run and preferences

```text
Choose VIDEO_DISTILLATION profile
→ review defaults / data-leaving-device disclosure
→ set interests, ignore rules, and optional temporary focus
→ confirm high-consumption modules remain off by default
→ arrive at Dashboard
```

The first-run profile does not qualify models, provision credentials, or start
Investigation/Deep Analysis.

### Add a Source

```text
Sources → Add Source → backend normalizes Channel or Video URL
→ choose history count, per-run cap, focus/ignore/style overrides, schedule
→ Save Source (local configuration only)
→ optional explicit Check Now command preview/confirmation
```

Saving never calls YouTube or a model. Check Now is separately audited and
runs only through the application-service/runtime boundary.

### Check Now and Intelligence consumption

```text
Check Source → discover candidates → low-cost filter → ambiguity inspection
→ skip-with-reason or process eligible candidates → Intelligence Card
→ user reads distilled content, opens evidence/original context when needed
```

Manual Analyze this video can override automatic relevance skip, but cannot
override model gate, budget, trust, qualification, at-most-once, or AMBIGUOUS
rules. The user may Save an Intelligence Card or give quick/natural feedback.

### Feedback and preferences

```text
More / Less / Important or natural-language feedback
→ store feedback distinct from explicit rules
→ affect learned priority, depth, presentation, Weekly selection, duplicate suppression
→ optional AI recommendation to promote a preference
→ user confirms any long-term rule
```

Factual correction enters the trust/correction workflow, not preference
learning.

### Topic and Weekly

```text
Intelligence association → live Topic current state / evidence / timeline
→ user pin/manage Topic
→ Weekly snapshot references exact Intelligence revision/evidence state
→ later correction adds supersession marker, never rewrites snapshot
```

Weekly has no quota-filling minimum. The future Daily flow aggregates existing
Intelligence on its configured time rather than initiating a blanket Source
check.

### Needs Attention

Dashboard and contextual surfaces show only decisions requiring a user: budget
choice, model availability, authorization need, safe known failure, or
AMBIGUOUS. AMBIGUOUS says a provider may have received work and has no normal
Retry control. Normal task completion/new video does not notify by default.

## 4. V2 Investigation flow

```text
high-relevance important change + unanswered questions + evidence threshold
→ CANDIDATE → approved/automatic bounded activation → ACTIVE
→ answers/evidence/confidence/timeline → WAITING or NEEDS_ATTENTION
→ COMPLETED / ARCHIVED → Topic monitoring; reopen only when needed
```

Weak signals remain watched; they do not auto-upgrade to cost-bearing
Investigation. Evidence Expansion is explicitly bounded and external
discoveries stay distinct from subscriptions.

## 5. Notification policy

Global levels are Critical Only (default), Critical + Important, and Off;
Topic/Investigation may override later. V1 sends only in-app and desktop
system notifications. Allowed proactive subjects are major high-value
intelligence, key Investigation progress, important Early Signal upgrade, and
Needs Attention/user intervention. Ordinary videos, normal Intelligence, and
ordinary completion do not interrupt the user.

## 6. Data/privacy and destructive flows

Settings presents view/export/delete capabilities and a plain-language
local-first disclosure. It explains cloud execution before it occurs. Source
delete offers Stop future monitoring only versus Full historical deletion; the
latter previews/requires downstream impact handling. Delete all local data
requires a second confirmation. No view makes credential values visible or
editable, and no browser path accesses a provider SDK, database, Vault, or
runtime internals directly.
