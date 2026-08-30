# TASK-016 — Local Reference Qualification, 2026-08-30

Status: **CLOSED — CURRENT LOCAL REFERENCE UNQUALIFIED**

## Scope and preservation

This is a bounded Local-only acceptance preflight on `main` at
`8111cdd50aa7b981a15db5b362dbc5b288a9ef72`. It does not rewrite the historical
`QUALIFIED_LOCAL_MODEL=NONE` record or change frozen Deep Analysis, scoring,
persistence, Note V2, or Weekly V2 contracts.

No Local Deep Analysis adapter was added. Therefore no application-owned Local
context authority, qualified Local capability profile, or real Local-only
end-to-end acceptance artifact exists. No cloud request, cloud credential,
cloud fallback, output repair, or TASK-016G code was used.

## Readiness audit

| Required Local-path element | Status | Evidence |
| --- | --- | --- |
| Provider-neutral Local provider profile | MISSING | Only the qualified `CLOUD_USER_KEY/openai` reference profile exists in production code. |
| Qualified Local model profile | BLOCKED | Both bounded candidate attempts below failed a mandatory property. |
| Concrete Local adapter | MISSING | No Deep Analysis Local adapter exists; the existing Ollama adapter is scoring-only. |
| Adapter returns only `UntrustedDeepAnalysisResponseV1` | MISSING | No Local Deep Analysis adapter exists. |
| Local context authority | BLOCKED | No candidate passed to an accepted exact profile; post-response token counts are not pre-dispatch authority. |
| Exact model identity | READY (observed) | Ollama `/api/tags` supplied the exact digests recorded below. |
| Local structured-output mode/profile | BLOCKED | Ollama rejected application JSON Schema conversion; JSON mode did not yield a valid KnowledgeContent result. |
| No hidden output repair | READY | Both responses were evaluated whole and unchanged; no extraction, trimming, repair, or quality retry occurred. |
| No automatic cloud fallback | READY | Attempts were loopback `http://127.0.0.1:11434` only; no cloud provider was configured or contacted. |
| Real Local path to the provider-neutral finalizer | MISSING | The adapter/profile gate did not qualify, so no finalizer/persistence/Note/Weekly execution was introduced. |

## Environment and bounded candidate sequence

- Ollama: `0.32.1`, loopback-only `http://127.0.0.1:11434`.
- No model was acquired.
- The selection used installed models only and stopped after the two bounded
  profile checks below. It is not a model shootout.

### Candidate A — `qwen3.5:4b`

- Exact digest: `sha256:2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`.
- Native JSON Schema attempt: Ollama rejected the application schema before
  generation with `HTTP 400`: its schema converter requires every pattern to
  be anchored. The provider-neutral application schema was not changed.
- Actual supported structured-output profile attempt: `format: "json"`,
  `stream: false`, `think: false`, `temperature: 0`, `seed: 0`,
  `num_ctx: 8192`, `num_predict: 1024`.
- Result: the real model response failed strict whole-document JSON parsing.
  Classification: `STRUCTURED_OUTPUT_INVALID`.
- Decision: **REJECTED** for this exact digest/profile. No output repair or
  additional quality attempt was made.

### Candidate B — `qwen2.5:7b`

- Exact digest: `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
- This was a materially distinct `format: "json"` profile from the historical
  raw/no-format rejection; it was not a retry of that frozen profile.
- Profile: `format: "json"`, `stream: false`, `think: false`,
  `temperature: 0`, `seed: 0`, `num_ctx: 8192`, `num_predict: 1024`.
- Real response observations: `done=true`, `prompt_eval_count=856`,
  `eval_count=182`. Those usage values are observational only and were not
  treated as context-admission authority.
- Result: strict JSON parsing passed, but `KnowledgeContent` validation failed:
  `why_it_matters.kind` was `fact`, whereas the frozen contract permits only
  `inference` for that field.
- Classification: `SCHEMA_INVALID` / frozen domain-kind invariant failure.
- Decision: **REJECTED** for this exact digest/profile. No prompt tuning,
  output repair, or retry-until-valid sequence was performed.

## Technical adversarial review

| Review question | Result |
| --- | --- |
| Any cloud provider or credential used? | PASS — zero; only loopback Ollama calls were made. |
| Any fallback or second provider attempt? | PASS — none. |
| Any application-side output repair or quality retry? | PASS — none. |
| Could a Local adapter mint trust or bypass finalization? | PASS — no Local adapter was created or imported. |
| Could malformed/provider output bypass strict parsing or application validation? | PASS — no; Qwen3.5 stopped at strict JSON and Qwen2.5 stopped at `KnowledgeContent` validation. |
| Could unselected transcript/private content leak? | PASS — the controlled probes contained only one selected evidence statement; no real acceptance input or transcript was recorded. |
| Could 016D, Note V2, or Weekly V2 reanalyze/persist untrusted output? | PASS — none was invoked because no trusted success was minted. |
| Did normal deterministic tests become dependent on Ollama? | PASS — no tests or production code changed. |
| Did this alter OpenAI qualification or add TASK-016G? | PASS — no; OpenAI remains `PENDING / CREDENTIAL BLOCKED` and the diff is documentation-only. |

Technical review result: **BLOCKED, not APPROVE**. There are no new
implementation P0/P1 findings, but the required Local qualification and real
acceptance artifacts do not exist, so product-owner acceptance cannot begin.

## Consequences

The required two successful Local qualification cases were not obtained.
Because a Local provider/model/adapter is not qualified, there is no real
`TrustedDeepAnalysisSuccess`, no 016D persisted verified read, no Note V2,
no `VerifiedNoteV2Artifact`, no Weekly V2, and no product-owner acceptance
package to present. Fabricating any of those would violate the Local-only
real-output gate.

OpenAI live qualification remains `PENDING / CREDENTIAL BLOCKED` and was not
changed by these Local-only checks.

## Next required decision

`TASK-016G` remains **NOT AUTHORIZED**. A product-owner/local-provider decision
is needed before another Local profile or model may be qualified; the current
bounded sequence is closed.

## Final bounded Local candidate — profile frozen before dispatch

This section is the one additional candidate authorized by the TASK-016 final
decision.  It was written before any decisive request for this candidate.  No
other Local candidate may be acquired or dispatched by this task.

### Selection record

- **Selected candidate:** `qwen2.5-coder:7b`, already installed; no model
  acquisition is required.
- **Why this one:** it is a distinct exact tag/digest from the rejected
  `qwen2.5:7b`, remains within the already-observed 7B Q4 local footprint, and
  exposes the same 32,768-token runtime declaration needed for a conservative
  pre-dispatch budget.  The previously deferred `gemma3:4b` and `llama3.1:8b`
  lack the required tokenizer-identity evidence; `phi4-mini:latest`,
  `qwen3:8b`, `qwen3.5:4b`, and `qwen2.5:7b` are prior definitive semantic or
  structured-output failures.  The installed 12B Gemma artifacts have less
  memory margin on this 16 GiB M1 Pro and no stronger approved identity proof.
- **Reuse decision:** `DIRECT` — existing Ollama `0.32.1`, loopback runtime,
  frozen provider-neutral validation, and the installed candidate.  No
  dependency, lockfile, schema, production adapter, credential, or cloud use.

### Frozen qualification profile `task016-local-reference-final-v1`

| Field | Frozen value |
| --- | --- |
| Model ID / exact digest | `qwen2.5-coder:7b` / `sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364` |
| Runtime / endpoint | Ollama `0.32.1`; loopback `http://127.0.0.1:11434/api/chat` only |
| Provider kind / operation | `LOCAL`; `task016-local-reference-final-v1` |
| Structured-output mode | `PROVIDER_JSON_MODE`; Ollama `format: "json"`; no schema conversion, extraction, fence stripping, or repair |
| Generation settings | `stream: false`, `think: false`, `temperature: 0`, `seed: 0`, `num_ctx: 8192`, `num_predict: 1024` |
| Context authority | `CONSERVATIVE_PROVIDER_CONTRACT`, identity `ollama-qwen25-coder-7b-local-tags-context-v1`: current local `/api/tags` reports `context_length=32768`; qualification admits at most 8,192 input tokens plus 1,024 requested output and a 2,048-token structured/runtime reserve.  This is a pre-dispatch conservative bound, never inferred from returned usage. |
| Timeout / retry | 120 seconds per request; semantic qualification retry count `0` |
| Prompt versions | Stage 2 `task016-local-json-probe-v1`; Stage 3/5 `task016-local-knowledgecontent-probe-v1` |
| Schema / validation | `KnowledgeContent` current frozen domain schema; application strict whole-document UTF-8 JSON parse, Pydantic/domain, grounding, KG2, language, and provenance checks; no changed semantics |

The tiny Stage 2 prompt requires one whole JSON object for a selected evidence
statement; it has no alternate response or quality attempt.  The Stage 3
prompt requires a Chinese `KnowledgeContent`-shaped value based only on the
single authorized evidence ID `ev-0001`, with `why_it_matters.kind` explicitly
required to be `inference`; all other finite semantic kinds remain frozen.
The exact executable prompt bodies and unchanged outputs are captured with the
stage results below, without recording a real user transcript.

### Stage results — case 1

| Stage | Result | Evidence |
| --- | --- | --- |
| 1 — load / identity | PASS | One loopback non-streaming load completed in 7.1 s: HTTP `200`, response model `qwen2.5-coder:7b`, `done=true`, `prompt_eval_count=40`, `eval_count=6`.  The pre-dispatch tag digest and 32,768-token context declaration match the frozen profile. |
| 2 — strict structured output | PASS | One `format: "json"` probe completed in 10.0 s: HTTP `200`, `done=true`, `prompt_eval_count=162`, `eval_count=66`.  The original response was strict-whole-document JSON with no Markdown/fence/trailing text; it parsed once without mutation. |
| 3 — frozen KnowledgeContent | PASS | One contract-shaped `format: "json"` call completed in 16.0 s: HTTP `200`, `done=true`, `prompt_eval_count=416`, `eval_count=258`.  The original whole response passed strict parsing and `KnowledgeContent` Pydantic/domain validation.  `why_it_matters.kind` was exactly `inference`; `key_facts.kind` was exactly `fact`. |

Case 1 has used exactly one response for each stage.  These were distinct
stage probes, not retries or quality attempts.  Stage 4 now validates the
unchanged Stage 3 raw payload through the application-owned trust finalizer;
it does not contact the model again.

### Case 1 Stage 4 and case 2 outcome

- Case 1 Stage 4: **PASS**. The unchanged Stage 3 payload passed the actual
  application finalizer's strict parse, `KnowledgeContent`, grounding, KG2,
  `zh-CN` language and final provenance checks, producing a runtime-bound
  trusted success. Its content identity was
  `9752b6bd7dda638ac7ac83d91b0cd7fa8c33ddd66839cd0ebcb6956295737050`.
- Case 2: **PASS**. One independent selected-evidence case (`ev-0002`) used
  the same frozen profile and one model call only; HTTP `200`, exact model
  echo, `done=true`, `prompt_eval_count=377`, `eval_count=319`. The unchanged
  output passed the same finalizer path. Initial bounded model qualification:
  **2/2 PASS**.

## Adapter qualification and final decision

The candidate's initial 2/2 model qualification authorized one local adapter
implementation. The adapter is intentionally untrusted-output-only: it binds
the frozen LOCAL/Ollama/profile/digest/context/generation settings, makes one
loopback `/api/chat` attempt with a 120-second timeout, has no retry/fallback
or cloud path, and leaves strict parse, schema/domain, grounding, KG2, language
and trust minting to the existing application finalizer.

Deterministic mock-transport tests cover A2/A3 projection, exact model/digest,
timeout, zero retry, malformed response, no repair, no cloud fallback and
finalizer ownership.

**Real adapter qualification case 1: FAIL.** The first real local adapter
dispatch used the exact frozen candidate/profile and reached the application
finalizer as an `UntrustedDeepAnalysisResponseV1`. The response model was
`qwen2.5-coder:7b`; reported usage was `979` input and `175` output tokens.
The finalizer returned `SCHEMA_INVALID`. No output mutation, repair, semantic
retry, prompt change, provider/model switch, cloud call or fallback occurred.

The required real-adapter target is 2/2. A first-case failure makes that target
unattainable without an unauthorized semantic retry, so case 2 was not sent.

### Closure

**LOCAL REFERENCE: CURRENTLY UNQUALIFIED.** This finding is bounded to the
tested frozen profiles and exact digests. It does not claim that Local models
cannot support the product, and retains Local as a future offline/privacy
capability.

- `CONTRACT WEAKENED: NO`
- `OUTPUT REPAIR: NO`
- `CLOUD SUBSTITUTION: NO`
- `TASK-016G: NOT AUTHORIZED`
- `ADDITIONAL LOCAL MODEL SEARCH: STOPPED FOR CURRENT TASK-016 CRITICAL PATH`

The next critical-path gate is **OPENAI LIVE REFERENCE QUALIFICATION 2/2 +
CLOUD PRODUCT-OWNER ACCEPTANCE**. The existing OpenAI adapter remains
offline/fake-transport qualified, but live qualification remains
`PENDING / CREDENTIAL BLOCKED`; no credential was read, requested, persisted,
or used here. Cloud stays explicit `CLOUD_USER_KEY` only—there is no automatic
Local-to-cloud fallback.
