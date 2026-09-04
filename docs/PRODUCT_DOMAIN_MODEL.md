# Product Domain Model — Frozen Product Contract

Status: **APPROVED PRODUCT CONTRACT**
Scope: conceptual model and future persistence boundary; no migration is
specified or authorized here.

## 1. Boundary rules

1. **Evidence is separate from Intelligence.** Evidence is source-bound,
   immutable material or a precise reference to it. Intelligence is a
   revisable system interpretation that cites Evidence.
2. **Business content is separate from execution state.** Source, Video,
   Evidence, Intelligence, Topic, Brief, Investigation, Preference, and
   Feedback do not double as queue/lease/provider-call records.
3. **Current state is separate from history.** Mutable current views point to
   append-only revisions/state transitions; no consumer needs copied text to
   know what version/evidence it used.
4. Stable opaque IDs, revision IDs, evidence IDs, and dependency edges are the
   only product relationship currency for Daily, Weekly, Topic,
   Investigation, and Ask.

## 2. Objects and ownership

| Object | Ownership and cardinality | Current versus history semantics |
| --- | --- | --- |
| **Source** | User-owned subscription; `1 Source → 0..n SourceVideoLink`; external discovery never creates one | Mutable configuration revision; source profile observations append historically |
| **Video** | Canonical YouTube raw-material record; `1 Video → 0..n Evidence`, `0..n Intelligence` | Metadata refresh changes current projection; original fetched artifacts remain independently identified |
| **Evidence** | Immutable evidence item owned by a Video or bounded external original source; `1..n` may support an Intelligence revision | Original, translation, extraction, and provenance are distinct; evidence content is never altered by correction |
| **Intelligence** | `1 Intelligence → 1..n IntelligenceRevision`; `0..n` Video/evidence links, `0..n` Topics | Current revision is a pointer; revisions and state history are immutable |
| **IntelligenceRevision / StateHistory** | Belongs to exactly one Intelligence; a state event cites reason/evidence/prior state | Append-only NEW/PENDING_CONFIRMATION/CONFIRMED/DISPUTED/UPDATED/INVALIDATED-or-OVERTURNED semantics |
| **Topic** | User-manageable live knowledge object; `0..n` Intelligence associations, timeline events, and relations | Current topic state points to supported intelligence revisions; timeline is historical |
| **TopicTimelineEvent** | Belongs to one Topic; cites at least one evidence/intelligence revision | Event does not mutate history; later correction creates a supersession reference |
| **TopicRelation** | Directed or normalized symmetric relation between two Topics | Lightweight V1 relation; source/evidence-backed and revisioned rather than a free graph assertion |
| **Preference** | User-owned long-term, recent, or temporary record; temporary requires expiry | Explicit rules retain user-origin/confirmation; learned observations remain separately auditable |
| **Feedback** | User action linked to an Intelligence, Topic, Video, or preference context | Preference feedback and factual correction are disjoint types; never rewrite input material |
| **Brief** | Historical Daily or Weekly snapshot; `1 Brief → 0..n BriefItem` references | Snapshot is immutable; a later supersession marker points to newer current state |
| **Investigation** | V2 first-class inquiry linked to `0..n` Topics and `1..n` Questions | Current lifecycle state points to state history; result is structured Intelligence, not an isolated report |
| **InvestigationQuestion** | Belongs to exactly one Investigation and may link evidence/intelligence answers | Question/answer confidence and unresolved status are revisioned |
| **Task / Execution** | Operational request/run; may target Source, Video, Intelligence, Brief, or Investigation | Queue state, priority, lease, trigger, safe resume point, and failure classification are operational history |
| **ResourceUsage / Ledger** | One or more records per high-resource Execution | Immutable account of why invoked, actual provider/model, calls, duration, reliable usage/cost or UNKNOWN |
| **DependencyEdge** | Derived-asset dependency: consumer revision/snapshot → input Intelligence revision/Evidence | Enables correction/deletion impact analysis; content copying is not a substitute |

## 3. Relationship map

```text
Source ──< SourceVideoLink >── Video ──< Evidence
                                  │          │
                                  └──< Intelligence ──< IntelligenceRevision
                                               │                 │
                                               ├──< TopicAssociation >── Topic ──< TimelineEvent
                                               ├──< BriefItem >── Brief snapshot
                                               ├──< InvestigationQuestion >── Investigation
                                               └──< AskAsset / saved answer

Feedback ──> Preference observations or Correction request
Task / Execution ──> target object; ResourceUsage / Ledger ──> Execution
DependencyEdge records every derived-current and snapshot dependency.
```

An Intelligence revision may cite many Evidence items; an Evidence item may
support many revisions. Topic membership is an association, not ownership:
merging/splitting Topics must not rewrite Intelligence or Evidence identity.
One Source can link to one Video and a Video can be linked by many Sources.

## 4. Evidence, provenance, and deletion dependencies

Evidence has immutable identity, source role, language/original-versus-
translation lineage, retrieval/provenance record, and availability state. An
Intelligence revision stores exact evidence IDs plus the interpretation kind;
it never owns a mutable embedded substitute for its source.

Deletion is a policy-driven dependency operation:

- **Stop future monitoring** disables a Source but preserves existing content
  and evidence links.
- **Full historical deletion** removes the selected transcript/evidence and
  walks DependencyEdge inbound links. Current Intelligence/Topic state is
  recomputed or marked unsupported/disputed/unavailable; it cannot remain a
  ghost claim.
- Historical Briefs stay immutable but gain a marker that some evidence was
  later removed. They are not silently rewritten.
- Delete-all-local-data is a high-risk, explicit second-confirmation operation.

## 5. V1 persistence needs

V1 implementation planning must persist or safely derive the following
semantics, even where a UI is initially narrow:

- Source configuration revisions: initial-history count, per-run cap,
  focus/ignore overrides, distillation style, enabled state, and schedule;
- Video-to-Source provenance, filtering disposition/reason, and manual
  analysis override audit;
- Evidence identity/lineage sufficient to distinguish source material from
  translation and derived interpretation;
- Intelligence Card plus immutable revision/state history and evidence links;
- basic Topic, Topic association, pin, and evidence-backed timeline foundation;
- feedback separated from explicit preference and correction; long/recent/
  temporary preference with expiry and explicit-rule confirmation;
- Brief snapshot items that reference exact Intelligence revision/evidence
  state, not pasted text;
- queue/Execution priority, trigger, state, safe-resume marker, and resource
  ledger that remain separate from business content.

Existing authoritative `videos`, `artifacts`, `jobs`, `job_attempts`,
`provider_calls`, `provider_dispatch_states`, `reports`, source subscriptions,
automation schedules/runs, and verified scoring reads remain their existing
authority owners. New records must reference them; they may not recreate their
trust meaning.

## 6. V2 reserved boundaries

V2 activates EarlySignal, Investigation, InvestigationQuestion, external
Evidence Expansion, independent-evidence-chain observations, Daily, Ask asset
save, and richer correction/dependency UX. V1 must reserve their IDs and
edges, but must not synthesize an Investigation result, signal authority, or
external-source discovery before V2 authorization.

## 7. Migration-risk analysis

Risk: **MEDIUM**. The existing schema has useful separations for source
subscription/automation versus videos/jobs/artifacts, but it has no native
Intelligence, Evidence graph, Topic, Preference, revision, dependency, or
resource-ledger model. The highest risks are copying text into reports,
overloading `VideoRecord`/job state as knowledge state, and treating provider
metadata as user model policy.

Mitigations for later design (not a migration plan): append new product tables
and foreign-key/reference edges; keep existing trusted scoring/dispatch keys
opaque; use immutable revisions and link tables; migrate display projections
behind application services; test deletion/correction impact before exposing
destructive controls. No existing migration is to be rewritten.
