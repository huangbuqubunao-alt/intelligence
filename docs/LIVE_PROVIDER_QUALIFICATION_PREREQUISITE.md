# Live Provider Qualification Prerequisite — Product Owner Decision Support

## Status and scope

**DECISION SUPPORT ONLY — NO LIVE QUALIFICATION IS AUTHORIZED OR EXECUTED.**
This record recovers the prerequisite referenced by the current release next
action. It does not establish a credential, authorize a provider request,
qualify a provider, change provider selection/fallback, authorize TASK-016G,
or change the current `NO-GO`.

It was prepared from repository evidence at `main@d467ee7`. No environment
variables, shell history, credential stores, live providers, or external
pricing sources were accessed.

The controlling consolidation record is
[`TASK-016-REFERENCE-PROVIDER-GATE-STATUS.md`](TASK-016-REFERENCE-PROVIDER-GATE-STATUS.md).
Its freeze is explicit: provider experimentation is not authorized merely to
move the project forward; it resumes only after a material external change and
the required new authorization.

## Current release facts

| Item | Current state |
| --- | --- |
| Release | **NO-GO** |
| Live Deep Analysis provider | **UNQUALIFIED** |
| Real qualified-provider output acceptance | **NOT YET ELIGIBLE** |
| TASK-016G | **UNAUTHORIZED** |
| Window-1 automatic redispatch | **FORBIDDEN** by the v4 fail-closed protocol |
| Provider selection/fallback | No automatic selection, substitution, or fallback |

The release records require an explicit PO authorization for one bounded live
reference-provider qualification package **only after** its documented material
external prerequisite exists. That wording does not itself authorize a
credential, a request, or a qualification run.

## Provider matrix

| Provider | Kind / implemented state | Adapter technical qualification | Live attempt / result | Currently qualified or default? | Fallback? | Current blocker | Material external prerequisite for reconsideration | Retry currently authorized? | Paid / credit effect of a retry |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Local Ollama `qwen2.5-coder:7b` | `LOCAL`; Deep Analysis adapter is implemented, loopback-only | Deterministic mock-transport boundary suite passes | Initial model profile `2/2`; real adapter case 1 failed at application finalization with `SCHEMA_INVALID`; case 2 was not sent | **UNQUALIFIED**; not a current critical-path reference; remains an optional future offline/privacy capability | No Local-to-cloud fallback | The frozen real-adapter target is `2/2`; a first failure made it unattainable without an unauthorized semantic retry | New external evidence of a materially different eligible local model/runtime capability, plus a new PO/local-provider qualification decision. An internal prompt change or another run of the failed profile is not external evidence. | **NO** | No paid cloud credit; an additional local execution still consumes local machine/model resources and is not authorized. |
| OpenAI `gpt-5.4-mini-2026-03-17` | `CLOUD_USER_KEY`; `openai-deep-analysis-responses` v1, Responses API | **QUALIFIED** offline with fake transport and provider-neutral finalizer | `0/2`; `LIVE CREDENTIAL BLOCKED`; neither `LIVE-1` nor `LIVE-2` was sent | **UNQUALIFIED** live; the current eligible reference route once qualified; not a product-wide mandatory/default provider | No provider/model fallback | No approved ephemeral OpenAI credential was available in the prior approved runtime mechanism; additionally, the proposed direct qualification path has not been wired to Window-1 v4 dispatch persistence (see below) | An **approved ephemeral OpenAI credential** made available for the one bounded package. This is the only concrete OpenAI example named by the controlling gate record. It must still be followed by separate explicit PO execution authorization. | **NO** | Up to one billable/account-visible request per authorized case; repository evidence has no price or spend ceiling. |
| Kimi / Moonshot `kimi-k3` R2 | `CLOUD_USER_KEY`; `kimi-deep-analysis-chat-completions` v1, China endpoint | Deterministic no-network adapter suite passes; raw R2 profile proves capability only | R1 historical: `1/2`, Case 2 `TIMEOUT` at 30 s. R2 raw: `2/2`; R2 production adapter: `1/2`, Case 2 `SCHEMA_INVALID` at `SCHEMA` under the 120 s bound | **IMPLEMENTED / LIVE UNQUALIFIED**; neither default nor registered runtime provider | No fallback | The real R2 adapter failed its second required case. The successful raw result cannot substitute for adapter evidence. | A documented material Kimi provider/model/API capability change that addresses the relevant structured-output behavior, accompanied by new authorization. An identical retry, internal adapter change, or a timeout increase beyond R2 is not an external change. | **NO** | A new cloud request can consume account credit; no repository price/cost bound exists. |

## Meaning of “material external prerequisite”

The phrase was introduced in commit `05ceb22` (`docs(task016): consolidate
reference provider gate status`) and remains controlling. Its exact operative
wording is: a material external change, such as an approved ephemeral OpenAI
credential, a material Kimi provider/model capability change accompanied by a
new authorization, or a future explicitly authorized provider task.

For this gate, an event is both **material** and **external** only when it
changes the provider/credential availability or provider capability evidence
outside this repository in a way that could change the already-recorded live
qualification result. Examples supported by the record are:

- PO-approved availability of an ephemeral OpenAI credential for the bounded
  execution mechanism;
- a provider releasing/changing a model, API, or structured-output capability,
  with documentary evidence relevant to the failed frozen profile; or
- a separately authorized future provider task with a new bounded contract.

The following are not material external changes under the record:

- changing the adapter internally;
- rerunning the same blocked or failed case;
- retrying Kimi Case 2, performing output repair, selecting another provider,
  adding fallback, or increasing timeout again.

The repository does not define a separate prerequisite-verifier role. For
OpenAI, the PO (or an authorized credential custodian acting under PO authority)
must attest that an approved ephemeral mechanism is available without exposing
the credential value. A separate PO authorization is still required before any
one-shot package can use it.

## Provider-specific recovered state

### OpenAI

The frozen OpenAI reference profile is `CLOUD_USER_KEY/openai`, adapter
`openai-deep-analysis-responses` v1, OpenAI Responses `POST /v1/responses`,
versioned snapshot `gpt-5.4-mini-2026-03-17`, and strict
`text.format` JSON Schema. It has a 30-second bound, SDK
`max_retries=0`, selected-evidence-only payloads, `store=false`, no streaming,
and no provider/model fallback. The adapter implementation and fake-transport
boundary are qualified, but there is no completed live result because no
approved temporary credential was present. Repository evidence does not show a
provider capability failure, a failed live request, or a different live
blocker.

**Would a later PO-supplied ephemeral authorized credential satisfy the named
external prerequisite? YES.** It is the exact OpenAI example in the controlling
gate record. This answer does not say that a credential exists now, does not
request one, and does not authorize its use.

**Does that prerequisite exist now? CANNOT BE ESTABLISHED WITHOUT PO INPUT.**
This review intentionally did not inspect environment variables, credential
stores, or any other secret-bearing source. The prior qualification record says
only that no approved temporary credential was available then; it is not proof
of current absence.

### Kimi / Moonshot

Kimi R1 is historical only: its second raw case exhausted the 30-second
transport bound and was not resent. R2 was a single authorized timeout-profile
correction to 120 seconds; the raw profile then passed two independent cases.
The subsequently implemented production adapter passed real case 1 but real
case 2 failed application schema validation (`SCHEMA_INVALID` at `SCHEMA`). The
failed payload was not repaired or retried. Kimi consequently remains live
unqualified, non-default, and ineligible as fallback.

**Kimi material external prerequisite now: DOES NOT EXIST IN REPOSITORY
EVIDENCE.** Reconsideration needs new external evidence of a material
provider/model/API structured-output capability change and new authorization;
an identical retry is expressly outside the freeze.

### Local

The final bounded Local candidate was the installed loopback-only
`qwen2.5-coder:7b` at digest
`sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`.
Its initial model checks passed `2/2`, but its first real adapter case reached
the provider-neutral finalizer and failed `SCHEMA_INVALID`. The required
adapter result is `2/2`; no second semantic attempt, prompt change, model
switch, cloud fallback, or further Local search is authorized. Local remains a
future optional offline/privacy capability, not a requirement for the current
critical path.

**Local material external prerequisite now: DOES NOT EXIST IN REPOSITORY
EVIDENCE.** A new external capability/model/runtime fact plus a new PO
qualification decision would be required; an internal search or rerun is not
enough.

## Reference candidate and bounded package status

**Conditional reference candidate: OpenAI `gpt-5.4-mini-2026-03-17`.** The
TASK-016 card identifies it as the current eligible route after live `2/2`
qualification and explicit cloud consent. Kimi has a recorded production-adapter
failure, and Local is closed for this critical path.

The repository fixes the **number** of OpenAI live cases (`LIVE-1` and
`LIVE-2`, target `2/2`) but does not preserve their complete input manifests,
payload hashes, or an executable live harness. It is therefore not truthful to
claim that an execution-ready exact two-case package already exists. No
unrecorded fixture is substituted here.

If the two prerequisites below are first satisfied, the maximum bounded package
that should be brought back to the PO is:

| Field | Required package value |
| --- | --- |
| Provider / model / kind | OpenAI / `gpt-5.4-mini-2026-03-17` / `CLOUD_USER_KEY` |
| Live cases | Exactly 2, pre-frozen as `LIVE-1` and `LIVE-2`; each one provider request only |
| Input fixtures | Two committed, synthetic, selected-evidence-only fixture manifests with immutable content/request hashes and no real transcript, Vault, user data, or credential. They must be attached to the later PO authorization; repository authority does not yet define them. |
| Structured-output contract | Current OpenAI Responses `text.format` JSON Schema, fixed name `deep_analysis_knowledge_content_v1`, `strict=true`, followed by the existing strict whole-document JSON, schema/domain, grounding, KG2, language, and provenance finalizer. |
| Timeout | 30 seconds per case; no escalation. |
| SDK retries | `0`. |
| Semantic retries | `0`; a failed/unknown case consumes its one authorized attempt. |
| Fallback / substitution | None; no provider/model substitution or automatic provider selection. |
| Maximum provider requests | **2** total, one per pre-frozen case; no retry-until-valid, repair call, fence stripping, or first-JSON extraction. |
| Credential handling | An ephemeral PO-approved credential is supplied only to the isolated child process through its existing pipe mechanism. It must not be requested, stored, printed, committed, put in environment/argv, or persisted in SQLite/cache/provenance/logs/errors. |
| Success | Both cases complete through the existing provider-neutral finalizer as verified trusted successes; exact model echo and all frozen projection/profile checks hold. |
| Failure / stop | Any transport, auth, quota, envelope, schema, grounding, language, provenance, or Window-1 ambiguity failure stops the package. No replacement case, retry, fallback, or inferred success is permitted. |
| Cost exposure | **Boundable by request count, but not price-bounded by repository evidence.** At most two cloud requests may be account-visible/billable. A PO authorization must state a maximum spend exposure or explicitly acknowledge that repository evidence has no monetary estimate. |

This table is a conditional package design, not an authorization. It deliberately
does not select a default provider or alter existing profile policy.

## Window-1 v4 integration check — blocking internal prerequisite

The package above cannot presently be executed while truthfully asserting that
it uses the Window-1 v4 protocol.

- `OpenAIDeepAnalysisProviderAdapter.dispatch()` directly performs one isolated
  transport call on a prepared dispatch and returns an
  `UntrustedDeepAnalysisResponseV1`.
- The TASK-016 persistence tests use that adapter with a fake transport and
  persist only a **post-finalization** trusted success through
  `DeepAnalysisPersistenceStore`.
- The v4 state machine (`NOT_DISPATCHED` →
  `DISPATCH_INTENT_DURABLE` → `DISPATCHED_RESULT_UNKNOWN` →
  `SUCCESS_DURABLY_RECORDED`, with terminal `AMBIGUOUS`) is implemented in
  `SQLiteStateRepository` and is invoked by the legacy
  `RepositoryBackedAnalysisService` path. That path currently constructs the
  legacy `OpenAIResponsesProvider` with its own cloud profile, not the TASK-016
  OpenAI reference adapter.

Accordingly, a direct OpenAI adapter qualification currently has no durable
dispatch intent, unknown-result marker, or v4 recovery path. It cannot prove
that an ambiguous result will be prevented from being re-run by the
qualification harness, nor that cache/persistence cannot be misused. The v4
tests do prove the required fail-closed behavior for the path that uses the
repository protocol; they do not establish it for the separate direct adapter
qualification path.

This is an **internal technical integration prerequisite**, not a material
external change. It cannot be satisfied by treating a credential as proof of
recovery safety. Before any live qualification package is authorized, a
separate non-live architecture/implementation decision must either:

1. wire the TASK-016 OpenAI dispatch/qualification runner through v4 durable
   state transitions and prove the ambiguity/cache/credential properties; or
2. establish, with an equivalent reviewed durable one-shot protocol, why the
   standalone qualification harness provides the same no-auto-redispatch
   guarantee.

Neither path is authorized by this decision-support task. No claim of global
exactly-once provider execution is made.

## Minimum Product Owner input before a future package could execute

1. Attest, without revealing it here, that an approved ephemeral OpenAI
   credential mechanism is available for the one bounded package.
2. After the internal Window-1 integration prerequisite and two immutable
   synthetic fixture manifests are independently established, explicitly
   authorize the named provider/model, exactly two requests, 30-second timeout,
   zero SDK/semantic retries, no fallback/substitution/escalation, and a spend
   ceiling or acknowledged unpriced exposure.
3. Confirm the result will remain qualification evidence only: TASK-016G stays
   unauthorized until separately qualified-provider real-output and PO
   acceptance requirements are met.

No credential value should be supplied to, copied into, or committed with this
document.

## Adversarial review

| Check | Result |
| --- | --- |
| Qualification, live call, or network request executed by this task | **NO** |
| Credential, environment variable, shell history, or credential store accessed | **NO** |
| Material prerequisite fabricated | **NO** — OpenAI availability is unestablished pending PO input; Kimi/Local have no new evidence. |
| Same Kimi/Local failure presented as a new experiment | **NO** |
| Paid exposure, retry, timeout escalation, fallback, or substitution hidden | **NO** — two-request maximum is conditional; price is unknown; retries/fallback/escalation are zero/none. |
| Window-1 protection overstated | **NO** — the missing direct-adapter/v4 integration is recorded as a blocker. |
| Provider marked qualified, TASK-016G authorized, or release changed | **NO** |
| ADR-008, ADR-028, scanner disposition, credential isolation, or distribution posture weakened | **NO** |

## Decision package

```text
CURRENT RECOMMENDED REFERENCE PROVIDER:
OpenAI gpt-5.4-mini-2026-03-17 (conditional; not currently qualified)

CURRENT STATUS:
OpenAI adapter/offline contract qualified; live 0/2 and credential blocked.
No execution-ready live package exists because the two live fixtures and the
TASK-016-to-v4 dispatch integration are not established.

MATERIAL EXTERNAL PREREQUISITE:
An approved ephemeral OpenAI credential made available for one separately
authorized bounded qualification package.

DOES THAT PREREQUISITE CURRENTLY EXIST?
REQUIRES PO INPUT.

WHY:
The repository only proves its prior absence and this task did not access
credentials. A credential does not satisfy the separate internal v4 integration
and fixture-manifest prerequisites.

IF PREREQUISITES ARE SATISFIED, PROPOSED LIVE PACKAGE:
Exactly 2 pre-frozen synthetic selected-evidence-only cases using the frozen
OpenAI Responses strict-JSON-schema profile and provider-neutral finalizer.

MAXIMUM LIVE PROVIDER REQUESTS:
2.

PAID/CREDIT EXPOSURE:
Bounded by two requests; monetary amount unknown from repository evidence and
must be bounded or acknowledged by PO authorization.

CREDENTIAL NEEDED:
YES.

CREDENTIAL PERSISTED:
NO.

RETRIES:
SDK 0; semantic 0.

FALLBACK:
NO.

TIMEOUT ESCALATION:
NO; 30 seconds per case.

WINDOW-1 PROTECTION:
v4 is fail-closed where integrated, but the direct TASK-016 qualification path
is not presently integrated; do not authorize live execution until that
internal prerequisite is independently resolved.

PRODUCT OWNER AUTHORIZATION REQUIRED:
YES.

TASK-016G AFTER THIS PACKAGE:
STILL UNAUTHORIZED UNTIL QUALIFICATION + REAL OUTPUT ACCEPTANCE REQUIREMENTS
ARE SATISFIED.
```

## Evidence

- `docs/TASK-016-REFERENCE-PROVIDER-GATE-STATUS.md`
- `docs/TASK-016-DEEP-ANALYSIS-OPENAI-REFERENCE-PROVIDER-QUALIFICATION.md`
- `docs/TASK-016-DEEP-ANALYSIS-KIMI-REFERENCE-PROVIDER-QUALIFICATION.md`
- `docs/TASK-016-LOCAL-REFERENCE-QUALIFICATION-2026-08-30.md`
- `tasks/TASK-016-intelligence-output.md`
- `docs/AT_MOST_ONCE_RESIDUAL_RISK_PO_DECISION.md`
- `docs/RELEASE_BLOCKERS.md`, `docs/RELEASE_CHECKLIST.md`,
  `docs/RELEASE_SIGNOFF.md`, and `docs/PROJECT_STATUS.md`
- `src/youtube_intel/openai_deep_analysis.py`, `analysis.py`, `state.py`, and
  `migrations/004_add_provider_dispatch_state.sql`
- `tests/unit/test_openai_deep_analysis_adapter.py`,
  `tests/integration/test_deep_analysis_persistence.py`, and
  `tests/integration/test_provider_dispatch_crash_recovery.py`
