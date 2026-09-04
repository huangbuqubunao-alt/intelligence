# Cost, Model, and Automation Policy

Status: **APPROVED PRODUCT CONTRACT**
Scope: product execution rules. No current provider qualification or execution
authorization is created by this policy.

## 1. Capability profiles and switches

First-run profiles are:

| Profile | Default capabilities |
| --- | --- |
| `VIDEO_DISTILLATION` (default) | Source monitoring, transcript, relevance filter, personalized distillation, Intelligence Card, evidence traceability, basic Topic, feedback learning |
| `CONTINUOUS_INTELLIGENCE` | User-selected additional ongoing aggregation within configured budgets |
| `INVESTIGATION_SCOUT` | User-selected, bounded V2 Investigation/Security signal capability |
| `CUSTOM` | Explicitly selected module set and limits |

Every high-consumption module has an on/off state at global, Source-override,
and, where relevant, Investigation-specific depth. Off means no corresponding
execution is admitted; it is not merely hidden UI. Trust/safety mechanisms are
not switches: source binding, original evidence, actual model identity,
inference/source separation, execution records, correction history,
AMBIGUOUS safety, and provenance remain mandatory.

## 2. User-controlled depth and budget

The user configures daily model budget, per-Source maximum videos, per-
Investigation maximum work/calls, evidence-expansion limit, and behavior when
budget is exhausted. Investigation depth is conceptually basic, standard, or
deep. User modes are Cost Priority, Balanced, Quality Priority, and Custom;
they adjust a policy only within the user's explicit caps and never select an
unqualified model.

High-consumption manual work presents a scope/cost preview before execution.
Reliable provider usage/cost may be shown as such. If reliable data is absent,
the only allowed estimate is Low/Medium/High or UNKNOWN; precision is not
invented.

On budget exhaustion the system does not overspend or complete at lesser
quality without disclosure. Priority is:

```text
P0 explicit user work → P1 high-value intelligence → P2 normal automation → P3 deferrable low-value work
```

P2 queues and P3 defers when capacity is tight. P0/P1 priority does not bypass
at-most-once, provider dispatch, qualification, or AMBIGUOUS safety.

## 3. Model admission, routing, and fallback

Routing preference is `rule → cheap model → standard model → strong model`,
but escalation occurs only when policy says it is needed. A model may execute a
task only if it is AVAILABLE, QUALIFIED, and AUTHORIZED/PRODUCTION_ELIGIBLE for
that task. Current Deep Analysis admits none:

- OpenAI live qualification is `0/2`, credential blocked;
- Kimi production adapter is `1/2`, `SCHEMA_INVALID`;
- Local is unqualified and its critical-path search is closed;
- TASK-016G is unauthorized.

Unavailable/quota-exhausted/budget-exhausted conditions pause the matching
step. They do not silently fallback, downgrade quality, or increase spend. A
fallback is legal only when the user preconfigured that exact approved fallback
model; actual provider/model identity is then recorded. Functional pause is
preferred to hidden degradation.

## 4. Resource and execution ledger

Every high-resource task creates a ResourceUsage/Ledger record with reason for
invocation, target stable IDs/revisions, selected and actual provider/model,
call count, duration, reliable token usage, reliable cost, execution state,
and linkage to the queue/execution record. Unknown values are stored/displayed
as `UNKNOWN`. Prompts, credentials, and API keys are never ledger data.

The system may propose optimization based on this ledger. It must obtain user
confirmation before changing model, budget, Source cap, automation depth, or
any other execution policy.

## 5. Single orchestration path

Manual Check Now and scheduled Source Run share a single application-service
orchestration pipeline. Trigger differs; product and safety semantics do not:

```text
manual trigger / scheduler tick
  → application service validates policy, cap, budget, and priority
  → existing runtime / discovery / pipeline boundary
  → queue, jobs, attempts, provider dispatch, artifacts, execution ledger
```

Forbidden paths are browser-to-provider SDK, browser-to-database, scheduler-
to-database pipeline mutation, scheduler-to-YouTube/provider bypass, and
runtime bypass. Current `scheduler-tick`/automation records are reusable
foundation; any expansion delegates to the same boundary.

`Check Now` is source discovery + new-video policy processing; Retry concerns a
specific prior execution according to its failure contract. Neither action may
be disguised as the other.

## 6. Queue, failures, and resume

Queue work records priority, target/revision, trigger, budget decision,
attempt/external-boundary state, and safe next step. Failure states distinguish:

- retry-safe known failure;
- waiting budget;
- waiting model;
- partial completion;
- ambiguous;
- needs user authorization.

Partial completion resumes from the safe next step using identity and existing
artifact/provider-call checks; it does not repeat costly completed work merely
because a higher-level run ended. AMBIGUOUS never displays a normal Retry
button and never auto-redispatches. It remains separately visible in the
unified Needs Attention view.

## 7. Investigation limits

V2 Investigation records goals, questions, source scope, depth, budget, call
limit, frequency ceiling, monitoring state, and exit condition before work can
be admitted. Evidence Expansion consumes its separately configured limit and
only allows bounded original external material; it cannot add subscriptions or
be silently triggered after Investigation is disabled. When its core questions
are answered, active Investigation stops and long-term change returns to Topic
monitoring.

## 8. Privacy and local persistence

Raw transcript/video metadata/evidence; derived Intelligence/Topic/topic
timeline/Brief/Investigation/confidence history; user preferences/feedback/
temporary focus; and model usage/task/error/resource records are locally
persisted by default. Intelligence assets are exportable. Cloud execution must
present the outbound data scope and provider before admission. Credentials
continue to use the existing secure indirect-reference contract and are absent
from configuration plaintext, cache identity, provenance, logs, and UI.
