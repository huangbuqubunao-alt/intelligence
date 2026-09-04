# Product Specification Review Report

Status: **APPROVE**
Review type: product-spec freeze and read-only implementation consistency audit
START_HEAD: `8423010a79129cc32c6be08ad84fbf6026f991f2`
FINAL_HEAD: the self-referential docs-only commit recorded in the final delivery
receipt (this report cannot embed that SHA without changing the commit).
EXISTING_IMPLEMENTATION_ASSESSED: **YES**

## Files reviewed

- `AGENTS.md`, `docs/COLLABORATION.md`, `docs/PROJECT_STATUS.md`,
  `docs/PRD.md`, `docs/SYSTEM_DESIGN.md`, `docs/REUSE_REGISTER.md`
- `tasks/TASK-017-fcc-inspired-workspace-presentation.md`,
  `agent-prompts/TASK-017-IMPLEMENTER-CODEX.md`, `handoffs/TASK-017.md`
- `docs/FRONTEND_PRODUCT_ARCHITECTURE.md`,
  `docs/FRONTEND_PRODUCT_ARCHITECTURE_AMENDMENT.md`,
  `docs/PRODUCT_OPERATION_FLOW.md`, `docs/PRODUCT_FUNCTION_MANUAL.md`,
  `docs/FCC_UI_DESIGN_REFERENCE.md`, `docs/LOCAL_PRODUCT_ORCHESTRATION.md`
- `docs/TASK-016-REFERENCE-PROVIDER-GATE-STATUS.md`,
  `docs/TASK-016C-FINAL-FREEZE.md`, `docs/TASK-016B-FINAL-ARCHIVE.md`,
  `docs/TASK-016E-NOTE-V2-CLOSED-LOOP-REVIEW.md`,
  `docs/TASK-016F-WEEKLY-V2-CLOSED-LOOP-REVIEW.md`,
  `docs/SECURITY_SCANNER_FIXTURE_DISPOSITION.md`
- Current source/API/persistence/orchestration/UI: `local_api.py`,
  `orchestration.py`, `orchestration_service.py`, `runtime.py`, `state.py`,
  migrations `001`–`005`, `frontend/src/workspace/App.tsx`, and
  `frontend/src/api/client.ts`.

## Existing implementation assessed

| Classification | Current reality and frozen disposition |
| --- | --- |
| **REUSE** | Loopback local application API and mutation guard; SourceSubscription/SourceVideoLink; AutomationSchedule/AutomationRun and bounded scheduler tick; existing Video/Transcript Artifact/Job/attempt/provider-call persistence; actual provider/model identity; authoritative scoring read; trusted runtime persistence boundary; source/video display projections; local persisted storage boundary. |
| **MODIFY** | Source policy/config must add history cap, per-run cap, focus/ignore, style, filter disposition, and user-controlled depth; API/read DTOs must expose Intelligence-first views without browser authority; scheduler/service must apply priority/budget/safe-resume vocabulary; Settings/Activity/Dashboard/old route shell must conform to frozen IA. |
| **ADD_V1** | Evidence-versus-Intelligence revision model; Intelligence Card; basic Topic/association/timeline; preference center and separated feedback/correction; skip reason/manual override audit; Brief item revision/evidence references; priority/resource ledger; downstream deletion-impact analysis; Needs Attention projection. |
| **RESERVE_V2** | Early Signal, Investigation/Questions/templates/lifecycle, Evidence Expansion and independent-chain reasoning, Daily, Ask asset save, advanced correction propagation UX, advanced confidence/source profile, and qualified Deep Analysis activation. |
| **DO_NOT_TOUCH_FROZEN_CORE** | TASK-016B/016C scoring/lineage and trusted persistence; provider-neutral finalizer; provider dispatch/AMBIGUOUS rules; credentials; Note authority; Weekly V2 admission; production qualification; TASK-016G; migration history; canonical security scanner exit semantics. |

Migration 005 is current product-orchestration persistence (Source,
source/video links, schedule/run, desired model preference). It is useful but
does not supply Intelligence/Topic/Preference/Evidence graph semantics. The
review therefore classifies those as ADD_V1, not existing capability.

## Duplications merged and ambiguities resolved

| Consolidation | Resolution |
| --- | --- |
| Video intelligence versus original-video recommendation | Personalized distillation is primary; raw video is evidence/context. |
| Check Now versus Retry | Check Now is a source-policy discovery run; Retry is governed recovery of a specific execution. |
| Feedback versus correction | Preference feedback changes learned ranking/presentation only; correction creates a new interpretation revision. |
| Weekly/Topic/Daily state | Topic is live; Daily/Weekly are immutable revision-referencing snapshots. |
| Source popularity versus evidence strength | Repetition, attention, and independent evidence are distinct; unknown independence remains unknown. |
| Local-first versus cloud execution | Local persistence default is retained; outbound data scope/provider must be disclosed. |
| Existing frontend IA versus frozen IA | Old primary IA is superseded; its authority and runtime safeguards are preserved. |
| Existing `FULL_INTELLIGENCE` policy versus V1 Deep Analysis | It cannot activate Deep Analysis. V1 uses personal distillation under eligible existing processing; Deep Analysis stays BLOCKED. |

## Conflict review

- **P0 conflicts: 0.**
- **P1 conflicts: 0.**
- **P2 design debts:** existing current code has no native product domain model
  for Intelligence/Evidence/Topic/Preference/revisions/dependency edges; old
  UI routes remain implemented until a future authorized implementation task;
  migration 005 lacks priority/resource/deletion-impact fields. These are
  planned ADD_V1 gaps, not conflicts with the frozen contract.
- **PO decisions still required: none for this product-spec freeze.** Future
  schema/task sequencing, provider qualification, V2 activation, live side
  effects, credential/provider work, and deletion implementation retain their
  existing task-level approval gates.

Canonical scanner posture is preserved exactly: `bash scripts/security_scan.sh`
returns **EXIT 1**, with exactly **11 accepted synthetic fixtures** and **0 new
findings**. It is not reported as scanner PASS.

## Frozen boundary checks

| Review question | Result |
| --- | --- |
| Existing backend contracts preserved? | YES — new records reference rather than reinterpret existing authority owners. |
| TASK-016 trust boundaries preserved? | YES — finalizer, scoring reader, dispatch, credentials, Note/Weekly authority are explicitly retained. |
| Deep Analysis blocked status preserved? | YES — no qualified provider; OpenAI 0/2 credential blocked, Kimi 1/2 SCHEMA_INVALID, Local unqualified/search closed, TASK-016G unauthorized. |
| V1 architecture future-compatible? | YES — IDs/revisions/evidence/dependency edges reserve V2 without activating it. |
| IA future-compatible? | YES — raw Video/Transcript/Evidence remain contextual paths; Investigation is a first-class future domain object. |
| Domain model future-compatible? | YES — current/history, business/execution, and evidence/intelligence separations are mandatory. |
| Token/cost policy internally consistent? | YES — user caps, qualified admission, actual identity, explicit fallback, pause, and ledger agree. |
| Deletion/evidence policy internally consistent? | YES — impact walk avoids ghost claims; snapshots receive markers rather than rewrite. |
| Investigation lifecycle internally consistent? | YES — bounded admission, budgets/frequency, terminal return to Topic monitoring, reopen semantics. |

## Adversarial product review — round 2 (after document fixes)

| Attack | Result |
| --- | --- |
| A. Investigation off but Evidence Expansion still runs | PASS — only enabled module + bounded Investigation admission can execute; external discovery is not a subscription. |
| B. Source full deletion leaves Topic/Weekly unsupported | PASS — dependency walk recomputes/marks current state; snapshots gain markers, not ghost claims. |
| C. Ten relay channels inflate confidence | PASS — independence is tracked; UNKNOWN is not independent and source count is not evidence-chain count. |
| D. System inference renders as source fact | PASS — claim categories and separate original/translation/distillation/synthesis identities are required. |
| E. Less-like-this mutates explicit rules | PASS — feedback is separated and explicit configuration needs user action. |
| F. Later correction rewrites Weekly | PASS — immutable snapshots only gain supersession markers. |
| G. Model unavailable silently falls back/degrades | PASS — execution pauses; fallback requires prior explicit approved setting and actual identity record. |
| H. V1 blocks V2 Investigation model | PASS — Investigation/Question/edges are reserved without active V1 behavior. |
| I. Videos are secondary and transcript vanishes | PASS — every Intelligence/Topic/Source path retains raw context/evidence access. |
| J. Dashboard becomes operations console | PASS — intelligence entry first, operational metrics second, Needs Attention only. |
| K. Daily/Weekly/Topic/Ask copy text and lose revision | PASS — stable revision/evidence references and DependencyEdge are acceptance principles. |
| L. Local-first hides cloud egress | PASS — execution requires plain-language outbound scope/provider disclosure. |
| M. Optimizer changes settings itself | PASS — suggestion only; budget/model/depth/limits require confirmation. |
| N. Check Now behaves as Retry | PASS — separate definitions and orchestration semantics. |
| O. Manual analyze bypasses safety | PASS — only relevance filter is overridden; all runtime/budget/trust/dispatch gates remain. |
| P. Deep Analysis described as V1 available | PASS — V1 list reserves activation and repeatedly marks current status BLOCKED. |

## Final conclusion

**APPROVE**. P0/P1 are zero after the write → review → fix → review cycle.
This result does not claim code implementation, provider qualification, release
readiness, a green canonical security scan, or production capability.
