# V1X-DR-003: Phase 1C Deep Analysis qualification, consent and cost

Status: Accepted implementation of the Owner-frozen Phase 1C goal.
Date: 2026-10-03.
Predecessors: [Phase 1A](V1X-DR-001-content-deep-analysis.md) and
[Phase 1B](V1X-DR-002-durable-deep-analysis-evidence.md).
Starting HEAD: `432f085d76824dfa51a447622aa2dba23ff8bfc8`.

## Context and scope

Deep Analysis remains an explicit Content action. Qualification governs
production activation after the five-role and durable Evidence trust boundaries.
It never grants a model authority to author Evidence, replace Summary, or bypass
Phase 1B promotion, memberships, same-Content checks, atomic persistence, restart
verification or result-specific Note eligibility. Basic Content functionality
continues when no Deep Analysis route qualifies.

This is a narrow registry of the existing pinned Ollama and OpenAI profiles,
not a generic router. No account system, model manager, Knowledge Delta,
Research, DA on Intelligence/Topic, cloud sync or DA Obsidian publishing is added.
Phase 2 may proceed independently of production model availability once this
authority and governance layer is complete.

## Separate configuration, availability, qualification and activation

`CONFIGURED != REACHABLE != CONTRACT_CAPABLE != QUALIFIED != PRODUCTION_ELIGIBLE`.
These are separate facts, not a single readiness boolean. Candidate API entries
report each fact and a stable machine reason code, including missing credential,
not checked, unavailable, unsupported contract, not tested, failed and stale.

The production composition always supplies `QualificationAuthority`. A local
route is eligible only with configuration, matching model digest, reachability,
the Phase 1B schema and a current reviewed **LIVE_MODEL** PASS record. A cloud
route additionally requires its runtime credential and a safe reachability
check; its supported selected-Evidence preflight and cost disclosure are fixed
parts of this composition. Eligibility permits requesting an execution; it
does not authorize cloud dispatch.

Local discovery reads only loopback `/api/tags`, checks the pinned name and
digest and caches UI probes for at most 30 seconds. Production execution checks
that digest again immediately before generation. Cloud reachability uses a
bounded, non-generating model-read GET with no Content/body. It runs only for
a route with a current live record and a credential. UNKNOWN/not-checked or a
rejected credential never becomes reachable. Composition never pulls a model
or generates a response.

The historical authority-free local developer injection remains for Phase 1A/B
fixtures. It is absent from production composition and reports no production
eligibility. Cloud cannot use this seam. Availability of an injected fixture,
model installation, a health check and retired environment flags cannot mint
reviewed production authority.

## Qualification record and reviewed authority

`deep_analysis_qualification.py` defines record contract
`v1x-deep-analysis-qualification-record-v1` and policy
`v1x-deep-analysis-qualification-policy-v1`. A frozen, inspectable record binds:

- provider kind/id, model id, route id and complete provider/capability profile;
- model schema, prompt, validation policy, input budget and local/cloud class;
- record/policy versions and the complete source/expectation fixture identity;
- source digests of qualification-critical runtime, adapters, validation,
  Evidence/persistence, candidate generation and repository code;
- aware generation time, every fixture/language check, mode, limitations and
  an integrity digest over the record.

The registry is the literal packaged, repository-reviewed resource
`src/youtube_intel/resources/v1x_phase1c_qualification.json`. No env, YAML,
SQLite, frontend setting, upload endpoint or configurable receipt path populates
it. Constructor inputs are defensively copied. Digests detect corruption and
invalidate changes; they are not signatures and do not protect against an
engineer modifying trusted application code.

The latest reviewed record for an exact route is NOT_TESTED when absent, STALE
when its binding differs, FAILED when integrity/completeness/checks fail,
CONTRACT_VERIFIED for a complete fixture-only PASS, and QUALIFIED only for a
complete current LIVE_MODEL PASS. A material profile/model/schema/prompt,
validation/Evidence/runtime/fixture/policy change therefore fails closed even
if a developer forgets to change a named version. A route id change has no
matching record and is NOT_TESTED. There is no time-based expiration policy;
current contract/profile identity and current reachability are checked separately.

Evaluation produces a proposal and cannot register itself. To activate a route,
an engineering change must inspect every actual model case and its semantic
adequacy, current identities, limitations and provenance, then review and commit
the exact record. Ordinary model/credential selection cannot alter PASS.
Historical KnowledgeContent records prove a different contract and are not
imported as Phase 1C authority.

## Bounded evaluation policy

Seven repository-owned synthetic source fixtures run with both `en` and `zh-CN`
output (14 checks): straightforward, conflicting, several real candidates,
multilingual, limited Evidence, misleading metadata and a quoted fabricated-ref
instruction. The several-candidates fixture must actually prepare at least three
different real candidates. Metadata supplies a tempting unsupported profit claim;
only transcript-derived original Evidence can support claims.

Every case must pass the actual request preparation/adapter, five-role admission,
bounded canonical text and cardinality, required relevance, no deferred fields,
issued-candidate grounding, no unsupported citation, output-language validation,
atomic durable Evidence binding and an identical verified read after restart.
Policy additionally requires next-question behavior, an energy-specific conclusion,
uncertainty on designated inputs and rejection of the tempting unsupported claim.
All 14 checks must pass. No average score can hide one safety failure. Automated
semantic checks are deliberately bounded; manual source-specific semantic review
is required before placing a live PASS in production authority.

`scripts/qualify_v1x_deep_analysis.py` is local-only, checks the pinned digest
before every generation,
requires fresh isolated output/data paths, and stops after the first failed case
with the remaining checks explicitly NOT_RUN_AFTER_FAILURE. It emits a proposal,
not an activation. The harness supports caller-injected cloud adapters but rejects
cloud evaluation in either mode without a separate explicit authorization argument.
Calling a real adapter a fixture cannot bypass the cloud authorization gate.
The normal suite uses deterministic fakes and never obtains cloud credentials.

## Credentials and M13 integration boundary

Cloud reuses the committed `EnvironmentCredentialResolver` for `OPENAI_API_KEY`
and the existing isolated OpenAI SDK adapter with zero automatic retries. The
secret is resolved at dispatch and passed solely to the transport. API state
exposes a boolean, not the value. Receipts, SQLite, YAML, browser storage, logs
and snapshots carry no credential. Provider failures are converted to stable
safe codes without raw exception detail. Secret sentinel tests inspect request
projections, capability/preflight/error output, logs and the actual SQLite dump.

M13's dirty model-configuration/credential work is neither copied nor modified.
A user-facing credential manager must arrive through normal reviewed forward
integration after M13 is committed. Phase 1C adds no competing credential store.

## Per-execution consent and minimum egress

The Content action first requests
`POST /api/v1/videos/{id}/deep-analysis/preflight` with an eligible cloud route id.
No model generation occurs. The response discloses provider/model, explicit cloud
selection, credential and live qualification state, selected-original-Evidence
egress, bounded input character volume, UNKNOWN monetary cost, absence of a hard
cap and the requirement for this execution's authorization.

The server creates an unpredictable execution id, a ten-minute in-memory entry
and a prepared immutable envelope. Its authorization identity binds the execution,
operation, Content, current A1/A2/A3 input/profile identities, provider/model,
selected-Evidence scope and the pre-consent cost/volume disclosure. The pending
set is bounded at 256; restart invalidates unused entries. UI cancellation sends
no execution POST. Prior use, connectivity, credentials and a bare approval
boolean are insufficient.

The final prepared envelope is also compared directly with the disclosure
preview, so an input change between reads cannot authorize an undisclosed payload.
Comparison includes the complete input/request/execution/budget/timeout/fallback
semantics, normalizing only the preview-versus-execution consent digest and its
derived A2 link. Actual runtime A1/A2/A3 and consent validation remain unchanged.

Only the exact preflight route/execution, explicit `authorize_cloud=true`, explicit
UNKNOWN-cost acknowledgement, unchanged context/profile, unexpired entry and
`SELECTED_EVIDENCE_ONLY` can dispatch. Changed provider, model, Content, language,
profile, expiry or egress is rejected before transport. No reusable blanket
authorization exists. The successful Phase 1B immutable result audit retains the
non-secret authorization identity and admitted envelope.

Only bounded selected original Evidence and the necessary contract context are
sent. Cloud title/channel/publication metadata uses generic placeholders.
Transcript text/hash/normalization fields remain absent/null. Output language is
requested separately and Evidence stays in its original language. FULL_TRANSCRIPT
is unavailable, with no switch, alternate consent path or silent fallback.

## Honest cost and durable dispatch ledger

The four stable cost states are KNOWN, ESTIMATED, FREE and UNKNOWN. This milestone
emits FREE for local (no cloud model charge) and UNKNOWN for cloud; it implements
no dollar estimate or maintained pricing calculation. Character volume is input
size, not actual token usage or a monetary estimate. No hard monetary cap is
claimed. Explicit per-run approval despite UNKNOWN is the governing choice.

Cloud reuses existing `provider_calls` and `provider_dispatch_states` reservations
and M12 fail-closed dispatch semantics. Before transport it records durable intent
under the exact execution-derived request hash and owner/lease. Concurrent or
repeated POSTs cannot acquire a second paid dispatch. The SDK retries zero times;
there is no provider/model substitution or local fallback.

Reliable nonnegative integer provider input/output token counts are recorded on
that same row; missing or invalid counts remain unknown/NULL. `cost_microusd`
remains NULL. Estimates are never written as actual usage or cost, and duplicate
executions create no duplicate accounting entry.

After a provider response, the unchanged Phase 1B pipeline validates and atomically
persists all Evidence/result authority. Only a durably present result matching
provider/model and exact authorization can complete the dispatch ledger. The DA
result audit is its result authority; no competing response artifact is required.
The ledger and result are separate commits: a crash between them is conservatively
ambiguous and cannot cause re-dispatch.

Any network, parsing, validation or local persistence failure after intent is
DISPATCH_AMBIGUOUS. A duplicate completed execution is EXECUTION_ALREADY_DISPATCHED.
The UI disables re-dispatch for ambiguous/unknown response failures and directs the
user to inspect provider records. Reloading cannot retry the old execution; any
new execution requires a fresh preflight and explicit approval, with potential
duplicate semantic work disclosed by the ambiguous warning. This is at-most-once
transport per execution, not a guarantee that a provider processed a request.

## UI, schema and Backup/Restore

Capability and Content API projections expose configuration, credential,
reachability, contract capability, qualification, production eligibility, consent,
egress and cost using stable machine fields. Chinese and English UI localize these
states; backend prose and internal enums are not rendered as explanations.
An already-qualified route with missing credentials or reachability reports
UNAVAILABLE with CREDENTIAL_MISSING or ROUTE_UNREACHABLE, retaining qualified=true
and production_eligible=false. Neither the API nor localized copy labels this
as missing qualification.
Preflight, cost acknowledgement, authorize/cancel and ambiguity stay inside the
existing Content Deep Analysis panel. The six primary destinations are preserved.

No migration is added. Schema remains **30**, with Phase 1B migration **030** and
M13's in-flight **029** unchanged. Existing audit columns suffice for usage and
dispatch. Reviewed qualification authority travels with reviewed application code,
not product SQLite or a Backup archive. Reachability/credentials/pending consent
are machine-local and are never backed up as portable authority. The existing
Backup/Restore durable Evidence graph validation remains unchanged.

## Actual activation and review evidence

The available pinned `ollama-local / qwen2.5-coder:7b` model with digest
`sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`
failed the first actual English straightforward case: VALIDATION_FAILED. Thirteen
remaining cases are explicitly not run after failure. Reviewed negative record
identity is `821e7658c72e3359ffd3f95eea970ca7c79ab62dacf0998f34cc20518657cc3b`.
It is FAILED, not live-qualified, despite being reachable and contract-capable.
Other installed models are discovery only and are not new qualified routes.

The existing OpenAI profile `gpt-5.4-mini-2026-03-17` is structurally supported but
NOT_TESTED, without a configured credential in this execution environment and
with reachability NOT_CHECKED. No live cloud generation or cloud connectivity
probe occurred during this work. **Currently production-eligible routes: NONE.**
This truthful disabled state completes governance without weakening qualification.

Review pass 1 corrected missing A2/A3/profile and cost-volume consent binding,
required an explicit cloud route for execution identity, and bound ledger
completion to the actual durable result/authorization. Pass 2 closed the legacy
cloud injection seam, blocked retries on unclassified frontend response loss,
failed closed on context revalidation errors and corrected narrow-screen checkbox
layout. Fresh acceptance review added real multiple-candidate coverage and a local
digest check immediately before dispatch. Adversarial tests cover tampered/stale
records, retired flags, absent/fake credentials, denial/substitution, UNKNOWN cost,
concurrent/repeated POSTs, ambiguous transport and failed local response storage.
An interleaved-language regression also proves that input changes between
preflight preparation reads produce zero transport calls.
The final status review separately tested qualified-but-unavailable Content
states in both languages. A cloud-result Backup/Restore test verifies trusted
Evidence, token observations and the completed-execution dispatch barrier.

Validation includes Phase 1C fixtures and governance; Phase 1A/B schema, durable
promotion, membership, same-Content, rollback, restart, Note and Backup/Restore;
full backend/static checks; frontend typecheck/tests/build; and both-language
browser scenarios at 320/768/1024/1440px. Final counts, clean commits and read-only
M13 before/after verification are in the completion report. No paid call, push,
PR, merge, dependency/toolchain change or M13 mutation is part of this milestone.
