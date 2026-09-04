# Decision Traceability Matrix — Product Specification Freeze

Status: **APPROVED PRODUCT CONTRACT**
The 65 confirmed decisions are consolidated into requirement clusters to avoid
duplicated policy. Each listed decision remains individually covered.

| Decision IDs | Frozen requirement | Specification section | Domain object(s) | Scope | Existing implementation impact | Risk if violated |
| --- | --- | --- | --- | --- | --- | --- |
| A1–A3 | Check Now discovers and processes by Source policy; configurable initial history/per-run cap | Product Spec §3 Intake; IA §3 | Source, SourceVideoLink, Task/Execution | V1 | MODIFY Source policy/API/orchestration; REUSE Source/Automation records | Check Now becomes Retry or hard-coded batch processing |
| A4–A7 | Global + Source focus/ignore; two-stage filter; skipped visibility; manual analyze override | Product Spec §3 Intake | Source, Video, Preference, Feedback, Execution | V1 | ADD_V1 filtering disposition/rules; MODIFY UI/API | Wasteful processing, hidden skips, unsafe override |
| B8–B10 | Personalized Intelligence Card; original video is evidence, not watch-decision target | Product Spec §§1,3 | Intelligence, IntelligenceRevision, Evidence, Video | V1 | ADD_V1 Intelligence model/projections; MODIFY Videos-first UI | Product regresses to recommendation/list UI |
| B11–B16 | Feedback learning is bounded; long/recent/temporary preference; explicit confirmation; style override | Product Spec §3; Domain §5; IA §3 | Preference, Feedback, Source | V1 | ADD_V1 preference/feedback persistence; MODIFY settings/source config | Hidden rule/model/config changes or long-term pollution |
| C17–C22 | Video→Intelligence→Topic; live Topic, managed associations/relations, evidence never removed | Product Spec §3; Domain §§2–4 | Intelligence, Topic, TopicRelation, TopicTimelineEvent, Evidence | V1 | ADD_V1 topic/revision/link model and UI | Orphaned conclusions, weekly-only knowledge, source loss |
| C23–C28 | Conflict, confidence, history, limited Save/Pin | Trust §§3–5; Product §3 | Evidence, IntelligenceRevision, StateHistory, Topic, Brief | V1 foundation / V2 advanced | ADD_V1 claim/evidence links; RESERVE_V2 advanced evolution | False consensus, fabricated precision, no audit trail |
| D29–D34 | Intelligence-first Dashboard, restrained notices, grounded Ask, timeline | IA §§1–5; Product §3 | Dashboard projection, Intelligence, TopicTimelineEvent, Brief | Dashboard V1; Ask V2 | MODIFY dashboard/UI; ADD_V1 timelines; RESERVE_V2 Ask | Operations dashboard dominance or ungrounded web answer |
| E35–E39 | Intelligence/Topic Weekly; information-gain Daily; historical snapshots and markers | Product §3; Domain §§2–4; Trust §5 | Brief, BriefItem, DependencyEdge, Topic | Weekly V1 foundation; Daily V2 | MODIFY weekly projection; ADD_V1 revision refs; RESERVE_V2 Daily | Video list mislabeled Brief or historical rewriting |
| F40–F47 | Intelligence lifecycle, factual correction, downstream impact/provenance | Trust §5; Domain §§2–4 | IntelligenceRevision, StateHistory, DependencyEdge, Feedback | V1 foundations / V2 richer UX | ADD_V1 revision/dependency core; RESERVE_V2 impact UX | Corrections mutate evidence or leave stale claims |
| G48–G54 | Source profile is non-numeric input; source roles, independence, claim classification, translation separation, novelty distinction | Trust §§1–4 | SourceProfile observation, Evidence, EvidenceChain, IntelligenceRevision | V1 core labels / V2 reasoning depth | ADD_V1 roles/labels/lineage; RESERVE_V2 deep profiling | Reputation laundering, relay-count inflation, inference-as-fact |
| H55–H59 | Early Signal and bounded evidence expansion; external source ≠ subscription | Product §3; Cost §7 | EarlySignal, Evidence, Source, Execution | V2 | RESERVE_V2 only; DO_NOT_TOUCH current provider runtime | Unbounded web search or silent costly discovery |
| H60–H65 | Investigation object, admission criteria, template/questions/result/lifecycle/frequency | Product §3; Domain §§2,6; Cost §7; IA §4 | Investigation, InvestigationQuestion, Intelligence, Execution, Ledger | V2 | RESERVE_V2 IDs/edges; ADD no active code in V1 | Topic alias, budgetless endless investigation |
| Cost 1–10 | Depth toggles, profiles, budgets/caps, preview, model routing/modes, qualified admission | Cost §§1–3 | Source, Investigation, Task/Execution, ResourceUsage | V1 policy/foundation | MODIFY policy/UI/API; ADD_V1 budget/ledger model | Unconsented spend or use of unqualified model |
| Cost 11–18 | Controlled fallback, pause-on-unavailable, ledger, confirmed optimization | Cost §§3–4 | Execution, ResourceUsage, ModelPolicy | V1 policy/foundation | REUSE provider identity/dispatch; ADD_V1 ledger; MODIFY settings | Silent downgrade/fallback or secret leakage |
| Automation 1–9 | Shared manual/scheduled orchestration, priority queue, failure taxonomy, resume, AMBIGUOUS, Needs Attention | Cost §§5–6; IA §3 | Task/Execution, Source, AutomationRun, ResourceUsage | V1 | REUSE scheduler/application-service/runtime/dispatch; MODIFY automation; ADD_V1 priority/ledger | Direct bypass, duplicate external work, Retry of AMBIGUOUS |
| Data 1–10 | Local persistence, export/delete, downstream impact, cloud disclosure, indirect credentials | Domain §4; Cost §8; IA §6 | Evidence, Intelligence, Brief, Preference, Ledger, DependencyEdge | V1 | REUSE local repository/artifacts; ADD_V1 export/deletion impact graph | Ghost intelligence, unsafe deletion, misleading Local-first |
| IA/notify/scope/model | Frozen IA, notification policy, V1/V2 boundary, mandatory domain boundaries | Product §§4–7; IA §§1–5; Domain §§1–7 | All listed domain objects | V1/V2 as stated | MODIFY frontend routes; ADD_V1 domain model; RESERVE_V2 activation | Scope creep, old IA return, Deep Analysis misrepresentation |

## Implementation-impact legend

- **REUSE:** existing controlled contracts can remain authority owners.
- **MODIFY:** existing projection/configuration/orchestration must gain a
  product-compatible contract without lowering authority.
- **ADD_V1:** absent capability required for the V1 closed loop.
- **RESERVE_V2:** stable boundary/ID/edge needed now; no active behavior.
- **DO_NOT_TOUCH:** frozen TASK-016 trust/runtime/provider/credential core.
