# TASK-016C Phase H2-B — Runtime REPAIR Control-Flow Authorization

## Status, scope, and precedence

**Status:** `REOPENED AFTER IMPLEMENTATION REVIEW — READY FOR H2-B AUTHORIZATION AMENDMENT ROUND 4 INDEPENDENT REVIEW`.

This is a documentation-only authorization amendment. It authorizes no implementation in this task and does not authorize H2-C, persistence, schema or migration work, dependency work, a real network call, or a public REPAIR API. It amends only the H2-B runtime control-flow contract for one actually received eligible PRIMARY failure, one REPAIR scoring provider attempt, and one REPAIR Judge provider attempt.

The accepted H2 authorization remains authoritative for H2 evidence schemas, H2 JCS, identities, and H1 semantics. This document freezes the narrower H2-B execution, provider-contact, terminalization, and H2-C handoff contracts. It does not amend `docs/TASK-016C-PHASE-H2-AUTHORIZATION.md`.

## 1. Frozen H2-B boundary

```text
actual PRIMARY execution
  -> runtime observes a closed eligible failure
  -> constructs and re-verifies PrimaryFailureEvidence (PFE) with H2-A
  -> derives RepairNormalizedInput (RNI)
  -> derives exact REPAIR request identity and payload locally
  -> atomically admits and dispatches REPAIR under that exact identity
  -> captures and validates REPAIR raw/candidate/language evidence
  -> derives exact REPAIR Judge identity locally
  -> atomically admits and dispatches REPAIR_JUDGE under that exact identity
  -> pure-replays exact Judge raw and requires PASS
  -> PhaseH2BValidatedRepairResult evidence aggregate only
  -> STOP H2-B
```

H2-B never mints `PhaseHTrustedRepairSuccess`; calls neither `TrustedPersistenceEntry.persist_success()` nor `persist_repair()`; and makes no ProviderCall/Artifact registration, filesystem write, write plan, score or stage update, SQLite success registration, cache entry, or recovery marker. H2-C alone may mint the repair persistence authority and use the existing Phase G ingress.

H2-C is not a general verifier endpoint over `PhaseH2BValidatedRepairResult`.
It is entered only as the immediate private, runtime-owned continuation of an
already-admitted H2-B PASS branch. There is no caller break between H2-B PASS
and H2-C invocation.

## 2. Runtime entry and closed eligibility

REPAIR is a private branch in `RuntimeOperations`' actual PRIMARY execution; it is not callable with a claimed failure class, PFE, RNI, identity, admission, candidate, raw response, or request payload. The branch may begin only when, in the same live runtime execution:

1. the runtime owns the active, unexpired `SCORING` lease;
2. H1 shows PRIMARY consumed exactly once, REPAIR unused, and no conflicting ProviderCall exists for the freshly derived REPAIR request hash;
3. runtime-owned inputs rebuild `PrimaryTrustedContext`, `verify_primary_failure_evidence(...)` succeeds, and the PFE was produced while classifying the PRIMARY attempt actually dispatched by this runtime;
4. the replayed `PrimaryFailureClass` is exactly one of `SCHEMA_OR_PARSE_INVALID`, `LANGUAGE_INVALID`, `JUDGE_REJECT`, or `JUDGE_UNCERTAIN`; and
5. it is not `UNKNOWN_PROVIDER_STATE`, a deterministic-quality rejection, pre-capture/protocol failure, timeout, authority/config mismatch, arbitrary string, or future enum value.

Failure of any predicate is fail-closed before a REPAIR provider contact. It does not let a caller reconstruct repair eligibility from a DB row, cache, restart record, or attacker-created evidence.

## 3. Universal external-contact boundary

**EXTERNAL CONTACT begins at the first transport invocation that can leave the process and communicate with the configured Ollama endpoint.** The boundary is transport invocation, never an endpoint name. It includes every attempt's first and subsequent HTTP invocation, including `GET /api/tags`, `POST /api/generate`, a health request, model probe, provider preflight, lazy remote initialization, or a future request made by the same provider attempt.

The current Ollama seams prove why this is required: scoring and Judge model verification call `/api/tags` before `/api/generate`. The authorization never describes contact as beginning only at `/api/generate`.

The following are **LOCAL ONLY** if, and only if, inspection of the concrete factory proves that they do not invoke transport:

- Python object construction and local URL/client setup;
- validation of `LocalScoringSettings`, model/digest shape, loopback URL, and frozen prompt/schema literals;
- revalidation/serialization of PFE, RNI, identities, Judge inputs, and raw evidence; and
- deterministic prompt and request-body construction plus strict-UTF-8 hashing.

If the current or future provider factory, constructor, lazy initialization, or configuration check can perform any network I/O, admission must occur before that operation. An implementer may not assume that a factory is local.

## 4. Admission before contact and same-identity dispatch

For both REPAIR and REPAIR_JUDGE the mandatory sequence is:

```text
derive complete immutable expected identity and exact request locally
  -> perform only deterministic local validation/factory work
  -> atomically consume the relevant H1 role for that same identity
  -> immediately invoke the provider attempt with those same local values
  -> first transport may be /api/tags
  -> later transport may be /api/generate
```

No `/api/tags`, health request, model probe, remote preflight, or lazy remote initialization may occur before the relevant admission. If a factory can contact the endpoint, it moves after admission and is invoked inside the same private admission-and-dispatch closure.

### REPAIR invariant

The runtime derives immutable local REPAIR identity `A`, the exact RNI, exact payload bytes, payload SHA-256, prompt string, and provider closure before admission. One private operation consumes `REPAIR` for `A` and immediately invokes that closure with the same lexical values. It may not return an admission token, continuation, or mutable request object to a caller.

```text
derive A + payload A locally
  -> private admit-and-dispatch(A, closure using exactly A + payload A)
  -> consume REPAIR for A
  -> first transport for exactly A + payload A
```

It is forbidden to consume REPAIR for A and later replace the request, identity, payload, role, RNI, request hash, or closure input to dispatch B. The equality guarantee arises from the same function-local immutable values, not a caller assertion that A equals B.

### REPAIR_JUDGE invariant

The same private structure applies to the immutable expected REPAIR Judge identity `J` (`attempt_role=REPAIR`, expected H1, expected H2, exact `QualityJudgeOperationInput`, exact `ContentQualityInput`, and provider closure): consume `REPAIR_JUDGE` for J, then immediately invoke exactly J. PRIMARY Judge identity, REPAIR scoring identity, J1/J2 substitution, later role mutation, or candidate/request substitution is rejected before Judge contact.

### H1 implementation shape

H1's existing execution key, lease proof, shared lock, role budget, ProviderCall-existence check, and terminal-release semantics remain reused. There is no durable identity registry, DB column, persistent receipt, token, capability object, mutable global mapping, or schema migration.

`src/youtube_intel/scoring_admission.py` is authorized to change only if a minimal **private** `RuntimeOperations`-only admission-and-dispatch operation is needed to make the above closure structural. Its sole purpose may be to verify the live lease, check the exact derived request hash, consume the role, and invoke the same locally derived closure. It must not persist identities, return a reusable token/receipt/capability, expose public REPAIR admission, or allow caller-provided identity after role consumption. If this can be achieved with the existing private composition, `scoring_admission.py` remains frozen. The existing public `ScoringDispatchAdmission.admit()` continues to reject caller attempts to consume `REPAIR` or `REPAIR_JUDGE`.

## 5. Exact REPAIR request construction

The legacy `_repair_saved_primary_response()` / `_render_repair_prompt()` is not an authority for H2-B: it derives from incompatible PRIMARY request inputs and has a non-role-distinct legacy repair hash. H2-B must use this one source:

```text
runtime-owned trusted PRIMARY state
  + verified PrimaryFailureEvidence
  + validated LocalScoringSettings
  -> build_repair_normalized_input(...)
  -> exact RepairNormalizedInput (role=REPAIR)
  -> H2 JCS bytes and RNI SHA-256
  -> build_provider_request_hash(
       operation="local-scoring-repair-v1",
       normalized_input_hash=RNI SHA-256,
       provider="ollama", model=settings.model,
       prompt_version="scoring-prompt-v2", schema_version="score-result-v2")
  -> exact RNI-bound REPAIR prompt and Ollama request payload
```

Every derived value is revalidated before admission. No caller override, legacy request hash, PRIMARY identity, cache value, raw Artifact, or arbitrary prompt fragment is an input.

`RepairNormalizedInput.schema_version` remains exactly
`task016c-repair-normalized-input-v1`; its role is exactly `REPAIR`; its
normalized-input hash is H2-JCS SHA-256; and its request hash is the
role-distinct `local-scoring-repair-v1` result above. PRIMARY scoring identity,
PRIMARY Judge H2, and REPAIR Judge H2 cannot substitute for this REPAIR identity.

### Frozen prompt

The prompt version literal is **`scoring-prompt-v2`**. The H2-B template source is the new fixed, private literal `TASK016C_REPAIR_PROMPT_V2`; it is not the legacy helper. It is assembled exactly in this order, with each bracketed value supplied by the trusted inputs above and no caller-supplied addition:

```text
prompt_version: scoring-prompt-v2
You are repairing one invalid local-scoring result.
Return exactly one JSON object and no commentary.
The object MUST satisfy the supplied score-result-v2 JSON schema.
The reason field MUST use output language: <RNI.output_language>.
REPAIR request hash: <derived REPAIR request hash>
REPAIR normalized input: <H2-JCS exact RNI bytes decoded as strict UTF-8>
PRIMARY failure evidence: <H2-JCS exact verified PFE bytes decoded as strict UTF-8>
ORIGINAL scoring input: <H2-JCS exact RNI.scoring_input bytes decoded as strict UTF-8>
PRIMARY raw body: <exact PFE primary raw body, untrimmed>
PRIMARY candidate evidence: <H2-JCS exact PFE candidate evidence, or literal null>
Invalid PRIMARY model content follows:
<exact extracted invalid PRIMARY model content when PFE has it; otherwise literal null>
Required JSON schema follows:
<H2-JCS exact score-result-v2 schema literal>
```

The fixed text, line breaks, block order, `null` spelling, schema literal, and strict UTF-8 encoding are part of the payload provenance. The primary raw, extracted model content, and candidate block are included only as PFE-derived evidence; they are never reparsed or supplied by the caller. Thus schema/parse and language failures include their applicable invalid raw/candidate evidence, while Judge failures include the PFE's exact Judge evidence. The original scoring input is always included through the validated RNI binding.

### Frozen Ollama payload

The exact outbound `/api/generate` JSON object has no keys other than these:

| Field | Exact value/source |
|---|---|
| `model` | `validated_settings.model`, equal to RNI `repair_model` |
| `prompt` | exact `TASK016C_REPAIR_PROMPT_V2` result above |
| `stream` | literal `false` |
| `format` | frozen `score-result-v2` schema literal, the current accepted `_SCORE_RESULT_FORMAT` object |
| `think` | literal `false` |
| `options.temperature` | `validated_settings.temperature`, equal to RNI `temperature` |
| `options.num_predict` | `validated_settings.max_output_tokens`, equal to RNI `max_output_tokens` |

The body is `json.dumps` of precisely that object with `ensure_ascii=False`, `separators=(",", ":")`, then strict UTF-8 encoded. It uses the existing `Content-Type: application/json`, `Accept: application/json`, and `POST` transport metadata. `max_description_chars` is already bound by RNI and the original scoring input/prompt evidence; it is not an outbound generation key. There are no caller headers, options, generation keys, schema substitutions, or prompt fragments.

Before admission, the runtime calculates the SHA-256 and byte length of those exact payload bytes and binds them to the private dispatch values and H2-B aggregate. Immediately before transport it recomputes the body from the same trusted values and requires byte-for-byte equality, hash equality, and identity equality. It is forbidden to hash payload A and send/mutate payload B.

## 6. External-contact outcome classification

Once a role is consumed and **any** external transport invocation begins, ambiguous outcome is `UNKNOWN_PROVIDER_STATE`: `/api/tags` timeout, connection reset, interrupted response, ambiguous exception after send/start, cancellation after invocation, incomplete external response, `/api/generate` timeout or interruption, or any outcome whose exact external state cannot be established. There is no retry of that REPAIR role and no second provider attempt.

In particular:

```text
REPAIR admission -> /api/tags succeeds -> /api/generate ambiguous/fails
  => UNKNOWN_PROVIDER_STATE, terminal, no second REPAIR

REPAIR_JUDGE admission -> /api/tags succeeds -> Judge /api/generate ambiguous
  => UNKNOWN_PROVIDER_STATE, terminal, no second Judge
```

Pre-contact local rejection (including identity/payload mismatch, factory failure proven local, invalid trusted inputs, admission denial, or lease loss) has zero `/api/tags`, zero `/api/generate`, and zero Judge transport. A post-admission pre-contact lease proof failure consumes its one-shot role but still makes no contact.

### Judge UNKNOWN versus UNCERTAIN

H2-B must not use the live `OllamaQualityJudgeProvider.judge()` legacy behavior that collapses provider/preflight/transport failures to `UNCERTAIN`. For REPAIR_JUDGE:

- if transport/provider state occurred but valid exact Judge model-content raw was not established, the result is `UNKNOWN_PROVIDER_STATE`;
- only after a successful external response has yielded valid exact Judge raw evidence may the pure H2-A verifier deterministically return `UNCERTAIN`. That semantic result is `REPAIR_JUDGE_UNCERTAIN`.

A minimal provider-seam change is explicitly authorized to expose this distinction to the runtime. It must preserve raw evidence and does not authorize another Judge algorithm, policy, parser, or fallback.

## 7. REPAIR raw, candidate, language, and Judge flow

REPAIR uses the PRIMARY candidate transport boundary: full `/api/generate` HTTP body, at most 1,000,000 bytes, strict UTF-8, strict outer Ollama object and `response` extraction, strict re-encode, full-body SHA-256/byte length, then the shared strict raw-to-`ScoringCandidate` parser. No trimmed, pretty-printed, reserialized, or `payload["response"]` substitute is raw authority. Outer duplicate key/protocol/raw capture failure after contact is UNKNOWN; malformed inner candidate JSON, duplicate inner key, extra field, or candidate schema failure after a trustworthy outer capture is known `REPAIR_SCHEMA_OR_PARSE_INVALID`.

After a valid candidate, run exactly the TASK-016B language validator bound to the RNI output language. `INVALID` and `UNCERTAIN` are known terminal `REPAIR_LANGUAGE_INVALID` outcomes; neither dispatches a Judge.

For a valid language result, derive—not accept—from trusted candidate, RNI, validated settings, and current quality authority:

```text
ContentQualityInput + QualityJudgeOperationInput(attempt_role=REPAIR)
  -> expected REPAIR Judge H1 and H2
  -> local-only Judge construction if proven local
  -> atomic REPAIR_JUDGE admission + same-J dispatch
  -> possibly /api/tags then possibly /api/generate
  -> H2-A exact raw capture and pure replay
```

H1's budget is unchanged: at most one `PRIMARY_JUDGE` and one `REPAIR_JUDGE`. Judge raw is H2-A's extracted `response` string, strict UTF-8, at most 20,000 bytes inclusive, exact SHA-256/length, and never normalized or reserialized. `PASS` may produce the evidence aggregate; `REJECT` is known `REPAIR_JUDGE_REJECT`; pure semantic `UNCERTAIN` is known `REPAIR_JUDGE_UNCERTAIN`; any contact ambiguity is UNKNOWN.

## 8. Terminal routes and exact error mapping

Known H2-B failures must use the existing non-retryable repository route:

```text
PipelineRepository.fail_job(
  job_id, owner=runtime_owner,
  error_code=ErrorCode.INVALID_RESPONSE,
  error_message=<fixed mapping below>,
  retry_at=None, now=utc_now)
  -> SQLiteStateRepository.fail_job(...)
  -> JobStatus.FAILED_FINAL
```

`retry_at=None` is mandatory. The existing route writes the job attempt and job with `FAILED_FINAL`, clears the lease, and releases terminal H1 admission; the generic reclaim/retry path cannot revive `FAILED_FINAL`. No new ErrorCode enum or job state is authorized. The exact persisted error mapping is:

| H2-B outcome | `last_error_code` | fixed safe `last_error_message` | Follow-up |
|---|---|---|---|
| `REPAIR_SCHEMA_OR_PARSE_INVALID` | `INVALID_RESPONSE` | `REPAIR_SCHEMA_OR_PARSE_INVALID` | no Judge, no second REPAIR, no persistence |
| `REPAIR_LANGUAGE_INVALID` | `INVALID_RESPONSE` | `REPAIR_LANGUAGE_INVALID` | no Judge, no second REPAIR, no persistence |
| `REPAIR_JUDGE_REJECT` | `INVALID_RESPONSE` | `REPAIR_JUDGE_REJECT` | no second Judge/REPAIR, no persistence |
| `REPAIR_JUDGE_UNCERTAIN` | `INVALID_RESPONSE` | `REPAIR_JUDGE_UNCERTAIN` | no second Judge/REPAIR, no persistence |

`UNKNOWN_PROVIDER_STATE` is distinct. It must use the existing H1-owned `PipelineRepository.finalize_unknown_provider_state(...)`, which stores `UNKNOWN_PROVIDER_STATE` and `JobStatus.FAILED_FINAL`; it must never pass through the known-failure mapping. Both classes are terminal and non-retryable, but retain their different provenance semantics.

### Known-terminal orchestration disposition

The existing `PipelineOrchestrator._execute()` runs `_run_stage(...)`, then
currently requires the saved job to be `SUCCEEDED`; otherwise it calls generic
`_fail()`. H2-B known terminal failure has already used `fail_job(...,
retry_at=None)`, so that existing post-handler check would otherwise attempt a
second failure transition.

H2-B must reuse the existing `StageDisposition.TERMINAL` as the exact
ordinary control-flow disposition **`TERMINAL_ALREADY_HANDLED`**; it does not
introduce a new enum, authority, identity capability, persistence callback, or
admission proof. Initially only the runtime/H2-B known-failure path may emit
that existing disposition.

For every known H2-B failure—REPAIR schema/parse invalid, language invalid,
Judge REJECT, or Judge UNCERTAIN—the exact flow is:

```text
detect deterministic known failure
  -> PipelineRepository.fail_job(..., ErrorCode.INVALID_RESPONSE,
       exact frozen message, retry_at=None)
  -> verify returned/current job is JobStatus.FAILED_FINAL
  -> return StageDisposition.TERMINAL  (TERMINAL_ALREADY_HANDLED)
  -> PipelineOrchestrator._execute() verifies FAILED_FINAL and returns
  -> no generic _fail(), retry, second REPAIR/Judge, persistence, or second state mutation
```

The minimal `PipelineOrchestrator._execute()` integration point is immediately
after `_run_stage(...)` returns and before its current `SUCCEEDED` check:

```text
if disposition is StageDisposition.TERMINAL:
    saved_job = repository.get_job(job.job_id)
    if saved_job exists and saved_job.status is FAILED_FINAL:
        return
    existing generic _fail(invalid-job error) path
    return
```

The state read is a required, side-effect-free defensive check. A fake or
unrelated `TERMINAL` disposition therefore never suppresses generic failure
unless the repository already records `FAILED_FINAL`. The disposition itself
is not authority and grants neither persistence nor REPAIR capability.

UNKNOWN remains separate. The current `_execute()` `except
UnknownProviderState` path calls `finalize_unknown_provider_state(...)` and
returns without generic `_fail()`; H2-B must preserve that H1-owned behavior
rather than relabel UNKNOWN as `INVALID_RESPONSE` or return the known-terminal
disposition. If a crash occurs after known `fail_job(..., retry_at=None)`
commits but before the disposition returns, the durable job is already
`FAILED_FINAL`, is not reclaimed/retried on restart, and the disposition has
no durable meaning.

## 9. PhaseH2BValidatedRepairResult: evidence, not authority

`PhaseH2BValidatedRepairResult` is an **IN-MEMORY EVIDENCE AGGREGATE ONLY**. It is untrusted input to H2-C. Its type, private construction, frozen dataclass shape, intended non-serialization, exact schema, immutability, or non-copyability may be useful implementation hygiene, but none confers trust or persistence authority. H2-C must assume an attacker can construct, mutate, copy, deepcopy, or deserialize an equivalent aggregate.

It must carry sufficient evidence for independent replay, at least:

- PRIMARY rederivable trusted input/provenance, `PrimaryFailureEvidence`, failure class, PRIMARY raw/candidate/request bindings and hashes;
- exact RNI, its H2-JCS bytes/hash, REPAIR request hash, exact request payload bytes or exact payload provenance plus payload SHA-256/length;
- exact REPAIR outer raw body, strict UTF-8 SHA-256/length, extracted model content, reparsed `ScoringCandidate`, and candidate hash;
- TASK-016B language result and evidence;
- exact REPAIR Judge operation input, role `REPAIR`, expected H1, expected H2, `JudgeEvidence`, exact Judge raw content/hash/length, and final `PASS`; and
- finalizer-produced `TrustedScoreResult`, its sealed structured bytes/hash/length, and exact model/digest/prompt/schema/policy/settings provenance required to replay all bindings against current runtime authority.

A score-only result is insufficient. H2-B may not define or mint `PhaseHTrustedRepairSuccess`, and direct passage of even a valid H2-B aggregate to `TrustedPersistenceEntry.persist_success(...)` must reject before any read or side effect.

Possession of this aggregate provides no route to invoke H2-C. In particular,
there is no public or caller-independently reachable
`h2c_finalize(result)`, `finalize_repair(result)`,
`mint_phase_h_success(result)`, `persist_validated_repair(result)`,
`verify_h2b_result(result)`, or equivalent aggregate-ingress API capable of
minting persistence authority.

## 10. H2-C independent replay obligation

### Runtime-only continuation and trusted inputs

H2-C is entered only from the same runtime-owned lexical/control-flow chain
that has just consumed H1 REPAIR, dispatched the exact REPAIR identity, obtained
a valid REPAIR candidate/language result, consumed H1 REPAIR_JUDGE, dispatched
the exact Judge identity, and pure-replayed Judge PASS:

```text
actual runtime PRIMARY failure
  -> H1 REPAIR admission -> exact REPAIR dispatch -> valid REPAIR response
  -> candidate/schema PASS -> TASK-016B PASS
  -> H1 REPAIR_JUDGE admission -> exact Judge dispatch -> valid Judge raw/PASS
  -> construct untrusted H2-B evidence aggregate
  -> immediate private runtime continuation
  -> H2-C independent replay -> PhaseHTrustedRepairSuccess
  -> existing TrustedPersistenceEntry.persist_success()
```

Conceptually, one private runtime method performs this chain and invokes an
internal `_h2c_revalidate_and_mint(...)` before returning to any caller. The
exact helper shape may differ, but it cannot be independently reachable by
caller code through an aggregate parameter. This is achieved by eliminating
caller ingress, not by a repair execution token, receipt, nonce, sentinel,
registry entry, object identity, secret closure capability, or serialized
admission claim.

H2-C receives directly from that same runtime frame: runtime-owned
`ScoringInput`/PRIMARY source state, validated `LocalScoringSettings`, the
trusted job/lease execution context required by the current runtime, and the
untrusted H2-B aggregate. It must derive trusted context/settings from those
runtime inputs, never from aggregate fields.

Two independent truths are mandatory:

1. **Control-flow authenticity:** H2-C is reachable only after the actual
   already-consumed H1 REPAIR and REPAIR_JUDGE operations in this runtime path.
2. **Evidence authenticity:** H2-C treats the aggregate as untrusted and
   independently replays every security-significant claim.

The aggregate cannot prove actual H1 admission/execution from its evidence
fields, admission flags, role strings, request hashes, timestamps, Python type,
private minting, token/receipt, or serialized claims. Control-flow placement,
not aggregate material, supplies execution provenance.

H2-C makes no new policy choice about eligible failure classes: that closed policy remains frozen. It **must**, however, independently prove that the untrusted evidence satisfies that frozen policy. Before minting `PhaseHTrustedRepairSuccess`, H2-C must:

1. fresh-revalidate the aggregate and every nested schema;
2. rederive `PrimaryTrustedContext` from runtime-owned trusted `ScoringInput`/settings;
3. replay the PFE;
4. re-prove PRIMARY failure eligibility under the closed policy;
5. rederive RNI from trusted runtime inputs and verified PFE;
6. reserialize RNI under H2 JCS and recompute its hash;
7. rederive the REPAIR provider request hash;
8. rederive the exact REPAIR payload/provenance, payload bytes/hash/length;
9. verify sealed REPAIR outer raw: strict UTF-8, duplicate-key rule, byte length, SHA-256, and outer protocol extraction;
10. replay the inner REPAIR candidate parser/schema validation;
11. recompute candidate hash;
12. rederive the finalizer-produced `TrustedScoreResult` and its sealed structured bytes/hash/length from the trusted candidate/context;
13. rerun TASK-016B language validation and match its evidence/result;
14. derive expected REPAIR Judge context from trusted candidate/request/settings;
15. rederive Judge H1;
16. rederive Judge H2;
17. verify Judge raw strict UTF-8, bounds, hash, and length;
18. pure-replay Judge raw;
19. require Judge result exactly `PASS`;
20. verify all PRIMARY -> REPAIR -> Judge cross-bindings; and
21. verify current runtime settings/provenance equal the sealed evidence.

Only after every check passes may H2-C mint `PhaseHTrustedRepairSuccess`, then use the sole frozen route:

```text
PhaseHTrustedRepairSuccess
  -> TrustedPersistenceEntry.persist_success()
  -> Phase G PREWRITE_VALIDATE
  -> shared filesystem protocol
  -> SQLite atomic registration
```

H2-C may bind H2-B admission/budget metadata as evidence where authorized, but may not trust it merely because the object came from H2-B or has the expected Python type. It may not dispatch a provider/Judge, invent an identity rule, or use `persist_repair`, an alternate writer, SQLite path, or Artifact namespace.

H2-C remains separately reviewed and authorized. Its future architecture must
be a private runtime composition continuation, with at most a pure replay helper
in an H2 evidence/finalization module and, only if separately authorized,
`scoring.py` support for `PhaseHTrustedRepairSuccess` / its accepted
persistence type. It is not a repository-level service accepting arbitrary
aggregate input.

## 11. Concurrency, restart, and crash contract

H1's shared lock and lease proof permit one concurrent runtime to execute the private REPAIR closure. The losing runtime cannot use the winner's consumed role to dispatch a different identity; it rejects before contact. There is at most one REPAIR contact and one REPAIR Judge contact, and H2-B makes no persistence write.

Admission/PFE/RNI/raw/Judge evidence/H2-B aggregate are memory-only and never restored. H1's existing interrupted-SCORING recovery finalizes interrupted work as `UNKNOWN_PROVIDER_STATE` before generic reclaim/retry. The matrix is:

| Event | Required result |
|---|---|
| Crash before any external contact | no unauthorized retry beyond frozen lease/admission semantics; no contact replay |
| Crash after `/api/tags` or `/api/generate` | H1 UNKNOWN fail-closed terminalization; no REPAIR/Judge retry |
| Valid REPAIR response then crash before Judge | no REPAIR redispatch or evidence reuse; UNKNOWN fail-closed recovery |
| Judge transport started then crash | UNKNOWN fail-closed; no second Judge |
| Judge PASS then crash before H2-C | no automatic REPAIR/Judge redispatch and no H2-B persistence |

## 12. Side-effect accounting

Pre-contact rejection means zero `/api/tags`, zero `/api/generate`, zero Judge transport, zero filesystem/Artifact writes, and zero SQLite success writes.

Post-contact UNKNOWN means no additional transport retry, no second REPAIR or Judge, no success persistence, and only the existing H1 UNKNOWN terminal job/error update. Known REPAIR terminal failure means no provider/Judge call beyond the completed legitimate baseline, the exact non-retryable `FAILED_FINAL` transition above, and no persistence.

## 13. Required future RED behavioral and attack matrix

The implementation must preserve these prior 22 cases:

1. caller invokes REPAIR without an actual PRIMARY failure;
2. forged otherwise eligible PFE;
3. `UNKNOWN_PROVIDER_STATE` relabeled as eligible;
4. duplicate REPAIR admission;
5. two concurrent runtimes attempting the same REPAIR;
6. caller-supplied attacker `RepairNormalizedInput`;
7. caller model/digest/temperature/limit override;
8. PRIMARY identity substituted as REPAIR identity;
9. REPAIR identity substituted as PRIMARY identity;
10. provider factory/configuration failure before contact;
11. timeout/interruption after REPAIR contact;
12. valid captured raw with malformed/duplicate-key REPAIR candidate;
13. REPAIR candidate failing TASK-016B language validation;
14. duplicate REPAIR Judge admission;
15. PRIMARY Judge evidence substituted into REPAIR Judge;
16. REPAIR Judge context/candidate/request substitution;
17. REPAIR Judge `REJECT`;
18. REPAIR Judge `UNCERTAIN`;
19. REPAIR Judge `UNKNOWN_PROVIDER_STATE`;
20. a second REPAIR attempt after every possible repair failure;
21. direct passage of `PhaseH2BValidatedRepairResult` to `TrustedPersistenceEntry`; and
22. every attempted REPAIR persistence/write/ProviderCall/Artifact registration before H2-C.

It must additionally include explicit RED tests for:

1. REPAIR `/api/tags` before admission: forbidden/fails implementation.
2. Admission denied: zero `/api/tags` and `/api/generate` calls.
3. REPAIR `/api/tags` timeout after admission: UNKNOWN, no generate retry or second REPAIR.
4. REPAIR `/api/tags` success then `/api/generate` timeout: UNKNOWN, no second REPAIR.
5. REPAIR_JUDGE `/api/tags` timeout: UNKNOWN, not `JUDGE_UNCERTAIN`, no second Judge.
6. REPAIR_JUDGE `/api/tags` success then `/api/generate` timeout: UNKNOWN, not `JUDGE_UNCERTAIN`.
7. derived REPAIR A then attempted dispatch B: reject before contact.
8. consumed REPAIR then mutable request/identity mutation: impossible or reject before contact.
9. PRIMARY identity substituted as REPAIR, or correct RNI with altered final provider request hash: reject before contact.
10. concurrent loser attempts to use winner's consumed slot for another identity: reject before contact.
11. Judge J1 admission then J2 dispatch; PRIMARY Judge identity as REPAIR Judge; changed role after admission; changed candidate/request after Judge admission: each rejects before Judge contact.
12. hash payload A then send/mutate payload B: reject before external contact.
13. REPAIR parse failure: `FAILED_FINAL`, non-retryable, no Judge/no second REPAIR/no persistence; generic retry/reclaim cannot revive it.
14. REPAIR language failure: `FAILED_FINAL`, no Judge/no second REPAIR/no persistence; generic retry/reclaim cannot revive it.
15. REPAIR Judge REJECT and separately UNCERTAIN: `FAILED_FINAL`, no second Judge/no second REPAIR/no persistence; generic retry/reclaim cannot revive.
16. `object.__new__` forged aggregate; `object.__setattr__` mutation of PRIMARY request hash, PFE, RNI/request hash, REPAIR raw/hash/length, candidate/hash, language evidence, Judge H1/H2/raw/hash/length/result PASS.
17. forged/mutated `copy.copy`, `copy.deepcopy`, and pickle/serialization reconstructed aggregates.
18. a semantically self-consistent attacker aggregate B against runtime trusted context A.

For every case in 16–18, H2-C replay rejects before `PhaseHTrustedRepairSuccess` minting or persistence. Direct H2-B aggregate persistence rejects even for a fully valid aggregate.

The amendment additionally requires:

19. a fully self-consistent offline aggregate with valid-looking PRIMARY/PFE,
    RNI/hash, REPAIR request/raw/candidate, language evidence, and REPAIR Judge
    H1/H2/raw/PASS, but without actual runtime H1 REPAIR/REPAIR_JUDGE flow:
    no caller-facing ingress exists and it cannot mint;
20. aggregate mutation/replacement inside a legitimate H2-B PASS continuation:
    H2-C's 21 replay checks reject;
21. each known H2-B terminal failure: `fail_job` exactly once,
    `FAILED_FINAL`, zero extra outer `_fail()`, no duplicate error/state
    transition;
22. an ordinary unrelated handler failure: existing generic `_fail()`
    behavior remains unchanged;
23. UNKNOWN: existing dedicated UNKNOWN handling and zero generic second
    `_fail()`;
24. crash after `FAILED_FINAL` write before disposition return: restart does
    not reclaim or retry; and
25. fake `StageDisposition.TERMINAL` with a non-terminal job: the required
    repository-state check fails and existing generic failure behavior is not
    suppressed.

## 14. Narrow future implementation scope

Only a separate H2-B implementation authorization may allow the minimum edits:

- `runtime.py`: private PRIMARY-failure branch and the private lexical admission-and-dispatch closures;
- `pipeline.py`: only recognize the existing `StageDisposition.TERMINAL`
  from the H2-B known-terminal path, verify `FAILED_FINAL`, and stop before a
  duplicate generic `_fail()`; all unrelated handler/outcome behavior remains
  unchanged;
- `scoring_admission.py`: only the conditional private operation described in section 4;
- `providers/ollama.py`: only admission-before-first-transport integration, `/api/tags`/`/api/generate` outcome exposure, raw preservation, UNKNOWN vs semantic UNCERTAIN split, and RNI-bound REPAIR request construction;
- `h2_evidence.py`: non-persistence `PhaseH2BValidatedRepairResult` schema and pure evidence helpers only; and
- focused H2-B/H1/H2-A/H2-C future tests and handoff documentation.

`scoring.py`, `state.py`, migrations, and Phase G persistence machinery are
frozen for H2-B. In particular, no H2-B change may touch
`TrustedPersistenceEntry`, `persist_success()`, PREWRITE verification,
artifact write plans, filesystem writers, SQLite registration, or Phase G
idempotency. There is no broad pipeline state-machine redesign, retry-policy
refactor, unrelated stage change, new DB state/retry semantics, broad provider
refactor, second Judge algorithm, identity algorithm change, H2 JCS change,
TASK-016B language change, public repair API, schema or migration,
dependency/config/lockfile change, cache/recovery/H3 work, real
provider/model/network/Vault use, or H2-C implementation.

## 15. Completion boundary and discretion audit

An H2-B implementation agent has no discretion over whether `/api/tags` is contact; admission timing; ambiguity classification; Judge UNKNOWN versus UNCERTAIN; A-to-A or J-to-J binding; request/prompt/payload construction; retryability or terminal state; whether H2-C accepts arbitrary aggregate input; whether replay-valid evidence proves H1 admission; H2-C's direct trusted inputs; mandatory replay; the already-terminal pipeline disposition; terminal-state verification before suppression; aggregate trust; H2-C replay; or low-level aggregate forgery rejection. Any required behavior not frozen here is a `DECISION NEEDED`, not an implementation choice.

| Capability | H2-B status |
|---|---|
| REPAIR runtime control flow and one provider attempt | Authorized only by a later implementation task |
| REPAIR Judge and evidence aggregate | Authorized only by a later implementation task |
| Known/UNKNOWN terminal job route | Frozen here |
| H2-B owns | actual admitted REPAIR and REPAIR_JUDGE execution, plus construction of untrusted evidence |
| H2-C owns | immediate private runtime continuation, 21-step replay, `PhaseHTrustedRepairSuccess`, and existing Phase G `persist_success()` ingress |
| H2-C does not own | arbitrary aggregate ingress, inferred H1 admission, provider/Judge replay, or new eligibility/config policy |
| H2-B implementation in this task | Not authorized |

Until a future implementation and independent review satisfy this authorization, H2-B remains design-only.

## 16. Round 3 normative reconciliation and precedence

This Round 3 amendment is control-plane only.  It supersedes every conflicting
H2-B statement in sections 1, 2, 4, 7, 8, 9, 10, 13, 14, and 15.  In
particular, the previous references to a private
``admit-and-dispatch(A, closure)`` shape are withdrawn; a leading underscore
does not make an authority boundary.  The frozen parent H2 authorization is
unchanged.

The parent requires both items that the prior H2-B text/implementation failed
to make operative:

| Parent requirement | Round 3 reconciliation | Required order |
|---|---|---|
| deterministic Content Quality gate | H2-B reuses the accepted TASK-016C gate, with no REPAIR-specific algorithm or normalization | schema -> language -> deterministic gate -> REPAIR Judge |
| trusted finalization and structured value | H2-B performs a REPAIR-aware, side-effect-free finalization before it constructs its evidence aggregate | Judge PASS -> Quality PASS attestation -> finalizer -> aggregate |

These are H2-B requirements, not optional H2-C work.  The parent remains
consistent because a REPAIR-aware finalizer must prove the REPAIR transport
identity while the semantic score remains a score for the original PRIMARY
scoring request.  Thus `TrustedScoreResult.result.request_hash` and its sealed
structured score bytes retain the parent-required PRIMARY scoring request hash;
the separately sealed finalization binding proves the exact REPAIR request hash.
Using the PRIMARY hash in the *REPAIR binding* is forbidden.  This is not a
parent amendment and must not be misread as permission to relabel REPAIR as
PRIMARY.

## 17. RuntimeOperations-only authority and actual-PRIMARY continuity

The sole authoritative H2-B home is the existing `RuntimeOperations` SCORING
stage function that performs the actual PRIMARY attempt.  That one lexical
runtime branch owns, in order: PRIMARY dispatch and received result capture;
PFE construction and immediate verification; eligibility; RNI/request/payload
derivation; REPAIR role consumption and dispatch; REPAIR raw/candidate/language
validation; deterministic gate; REPAIR_JUDGE role consumption and dispatch;
Judge replay; attestation; REPAIR-aware finalization; and aggregate
construction.  It stops at H2-B.  It does not invoke H2-C or persistence.

The corrected implementation must structurally nest/combine the repair branch
with the actual PRIMARY result-handling branch.  It must remove the
authoritative helper shape equivalent to:

```text
_h2b_execute_repair(scoring_input, admission, primary_failure_evidence)
```

whenever those values can independently be supplied by another caller.  A
private spelling does not change this rule.  Pure PFE/RNI/raw/evidence parsing
and replay helpers may remain independently callable because they grant no
provider contact.

The only eligible continuity is:

```text
actual PRIMARY dispatch under this runtime's active lease
  -> runtime captures that attempt's exact result/failure
  -> runtime locally constructs PFE from that captured attempt
  -> runtime immediately verifies PFE against the same runtime-owned
     PrimaryTrustedContext and settings
  -> eligible failure only -> same branch enters H2-B
```

`PrimaryFailureEvidence` remains forgeable data for replay; it is never an H2-B
entry capability.  In particular, after a genuine PRIMARY consumption an
attacker may build internally self-consistent eligible PFE B, but there is no
caller-facing H2-B ingress through which B can cause REPAIR.  This must reject
before contact even though PRIMARY really was consumed.

## 18. Admission is state checking only; no callback dispatch authority

`ScoringDispatchAdmission` remains an internal H1 policy/state checker.  It
may only check/mutate live lease ownership, predecessor ordering, duplicate
rejection, ProviderCall conflict, and one-shot role budget.  Its REPAIR-role
operation, if needed, has no callback/closure parameter and returns `None`.
It may not contact a provider, execute caller code, return a repair capability,
continuation, token, receipt, or arbitrary admitted identity.

The corrected implementation must **remove**
`ScoringDispatchAdmission._consume_runtime_role_and_dispatch` and every
equivalent production API.  It must not rename it, make it double-underscore,
or retain it for tests.  The following surfaces are expressly forbidden,
whether public or underscore-prefixed:

```text
consume_runtime_role_and_dispatch(role, identity, callback)
admit_and_dispatch(identity, closure)
consume_repair(identity, continuation)
dispatch_after_admission(identity, caller_callback)
```

More generally, no production primitive may accept both a caller-selected
identity and executable work to run after admission.  Direct import of a
private method is an attack to defend against, not a privacy boundary.

Within the RuntimeOperations branch, the narrow allowed shape is equivalent
to the following; the values are lexical, runtime-owned values, not parameters
to a general dispatcher:

```text
repair_request = derive_from_actual_primary_state(...)
repair_identity = derive(repair_request)
admission.consume_repair_role(runtime-owned job/lease/predecessor state,
                              repair_identity)
recompute exact identity and payload from the same runtime-owned values
require identity, payload bytes, payload SHA-256, and payload length equal
dispatch the already-derived repair_request immediately
```

`consume_repair_role` and the matching Judge operation are only names for the
permitted state-mutating check; an implementation may use a differently named
non-dispatch method with the same restricted contract.  They must require the
frozen role/operation/predecessor (`REPAIR` after `PRIMARY`, `REPAIR_JUDGE`
after `REPAIR`) and may inspect the internally derived identity to perform the
existing ProviderCall conflict check.  They must not save that identity as a
durable registry or return it to a caller.

Immediately before first transport, the runtime recomputes the identity from
the exact RNI/request/payload and requires equality with the pre-admission
local identity, exact strict-UTF-8 payload bytes, SHA-256, and byte length.  A
post-admission request or payload change rejects before contact; there is no
second admission.  The identical rule applies to the REPAIR Judge: runtime
derives the repaired candidate, REPAIR request identity, expected Judge input,
H1, H2, and exact Judge outbound request; consumes `REPAIR_JUDGE`; recomputes
and confirms the same local Judge identity/request; then contacts the provider.

## 19. REPAIR deterministic Content Quality gate

After trustworthy REPAIR outer capture, canonical candidate schema parsing,
and TASK-016B language `VALID`, H2-B must construct exactly the accepted
`ContentQualityInput`/candidate binding used by the existing REPAIR Judge
context (`attempt_role=REPAIR`, REPAIR scoring request hash).  It then invokes
the accepted `DeterministicContentQualityGate` unchanged, with the candidate
reason and the exact candidate hash, quality-input hash, and REPAIR request
hash from that construction.  No REPAIR-only trim, normalization, evidence
registry, heuristic, entity/acronym judgment, or second gate is authorized.

The complete H2-B validation chain is now exactly:

```text
actual runtime PRIMARY failure
  -> verified eligible PFE
  -> derive RNI / exact REPAIR request
  -> consume H1 REPAIR -> same-identity REPAIR dispatch
  -> REPAIR outer raw capture -> candidate schema parse -> TASK-016B language PASS
  -> TASK-016C deterministic Content Quality gate PASS
  -> derive REPAIR Judge context
  -> consume H1 REPAIR_JUDGE -> same-identity Judge dispatch
  -> valid Judge raw -> pure replay PASS -> Quality PASS attestation
  -> REPAIR-aware trusted finalization -> TrustedScoreResult
  -> sealed structured bytes/hash/length -> PhaseH2BValidatedRepairResult
  -> STOP H2-B
```

The closed deterministic reject classes are exactly `EMPTY_CONTENT`,
`CONTROL_CHARACTER_INVALID`, and `EXACT_REPETITION`.  A rejection is a known,
local H2-B terminal failure: no REPAIR Judge `/api/tags` or `/api/generate`, no
second REPAIR, no persistence, and no outer duplicate `_fail()`.

Its exact repository mapping is:

```text
PipelineRepository.fail_job(
  job_id, owner=runtime_owner,
  error_code=ErrorCode.INVALID_RESPONSE,
  error_message="REPAIR_DETERMINISTIC_GATE_REJECT:<reason>",
  retry_at=None, now=utc_now)
-> JobStatus.FAILED_FINAL
-> StageDisposition.TERMINAL (TERMINAL_ALREADY_HANDLED)
```

`<reason>` is exactly one of `EMPTY_CONTENT`, `CONTROL_CHARACTER_INVALID`, or
`EXACT_REPETITION`, with no whitespace, prose, dynamic provider text, or other
literal.  The section 8 terminal-state read and no-duplicate-`_fail()` rule
applies unchanged.  This is not `UNKNOWN_PROVIDER_STATE`, because no ambiguous
Judge contact occurred.  Deterministic failures in finalization use the same
known-terminal route with exact message `REPAIR_FINALIZATION_INVALID`.

H2-C must independently rerun this exact gate against the replayed repaired
candidate and reconstructed REPAIR `ContentQualityInput` before a Judge PASS
is relevant.  A replay-valid Judge PASS, attestation, or finalizer output
attached to any of the three deterministic rejects is rejected.

## 20. REPAIR-aware finalization contract and exact scope

The authorized implementation choice is **B: a narrowly separate
`RepairTrustedScoringFinalizer` in `src/youtube_intel/quality.py`**, reusing a
private pure candidate-validation/final-score construction core extracted from
the current `TrustedScoringFinalizer`.  The existing PRIMARY
`TrustedScoringFinalizer.finalize()` must retain byte-for-byte equivalent
behavior and its PRIMARY-only public contract.  The repair finalizer is
side-effect-free and has no persistence or H2-C ingress.

It must consume only runtime-derived/replayed values: repaired exact
`ScoringCandidate`; original validated `ScoringInput`; original
`TrustedScoringContext`/validated `LocalScoringSettings`; role literal
`REPAIR`; exact RNI plus JCS bytes/hash; exact REPAIR provider request hash;
REPAIR `ContentQualityInput`, `ContentQualityResult(PASS)`, and
`QualityJudgeOperationInput(attempt_role=REPAIR)`; current
`QualityProvenanceAuthority`; verified `QualityPassAttestation`; and the
existing output limits/schema constraints.  It must rederive all values before
using the supplied data.

The finalizer must require all of these bindings:

1. exact `role == REPAIR`, RNI schema/operation, RNI JCS bytes/hash, and
   `build_provider_request_hash(...) == repair_request_hash`;
2. repaired candidate hash equals the Quality input/result/Judge/attestation
   candidate bindings;
3. Quality input, result, Judge operation, H1/H2, and attestation all bind the
   exact REPAIR request hash and `attempt_role=REPAIR`;
4. attestation is rebuilt/verified with the current runtime-owned authority;
   a caller-created or substituted attestation cannot self-authenticate; and
5. original scoring input/context rebuild the parent-required PRIMARY scoring
   identity, which remains the semantic `ScoreResult.request_hash`.

The repair request hash must never be replaced by the PRIMARY request hash in
items 1--4.  Conversely, its presence does not permit changing the semantic
score request hash in item 5.  This dual binding is the exact reconciliation:
REPAIR provenance controls the repair finalization evidence, while the score
continues to belong to the original PRIMARY job.

The finalizer produces an exact `TrustedScoreResult`, then the unchanged
exact-type sealed serializer produces canonical structured UTF-8 bytes.  H2-B
records those exact bytes, `SHA-256(bytes)` in lowercase hexadecimal, and
`len(bytes)`.  It also records the existing structured schema/version metadata
needed to reproduce the bytes.  No reserialization of a mapping, bare
`ScoreResult`, or aggregate-supplied byte sequence is permitted.

`quality.py` is the only allowed home for the new repair finalizer and its
pure shared core.  Its deterministic gate and existing attestation semantics
remain otherwise frozen.  `scoring.py` remains frozen, including
`TrustedPersistenceEntry`, `persist_success`, PREWRITE, write plans,
filesystem/SQLite logic, Phase G ProviderCall/Artifact logic, and the existing
sealed serializer.  H2-B may call that existing pure exact-type serializer to
obtain the parent-required sealed bytes, but may not modify it or use it as an
H2-C/persistence entry.  No new `scoring.py` change is authorized.

Explicit P0 prohibitions are: wrapping a repaired candidate in
`PhaseFTrustedScoringSuccess`; substituting the PRIMARY request hash for the
REPAIR binding; relabeling REPAIR as PRIMARY; calling the PRIMARY finalizer by
lying about role or quality context; creating a fake PRIMARY `ProviderCall`
identity; and minting a persistence-ready success aggregate in H2-B.

Local mismatch, malformed structured sealed bytes, structured hash/length
mismatch, failed sealing verification, candidate/finalizer binding mismatch,
attestation mismatch, or request-hash mismatch fails closed as
`REPAIR_FINALIZATION_INVALID`: no second REPAIR/Judge, no persistence, and the
known-terminal `FAILED_FINAL` route exactly once.  `UNKNOWN_PROVIDER_STATE`
remains reserved for an actual ambiguous external contact.

## 21. Amended PhaseH2BValidatedRepairResult and H2-C replay

`PhaseH2BValidatedRepairResult` remains untrusted evidence data and not a
persistence capability.  Its minimum replay-complete contents are:

- PRIMARY provenance, exact verified PFE/failure class, raw/candidate/request
  bindings, and all settings needed to reconstruct `PrimaryTrustedContext`;
- RNI, H2-JCS bytes/hash, REPAIR request hash, exact prompt/payload and strict
  UTF-8 payload SHA-256/length;
- REPAIR outer raw/hash/length, extracted content, candidate and candidate hash;
- TASK-016B evidence/result; exact deterministic-gate input/provenance and
  PASS evidence sufficient to rerun it;
- REPAIR Judge input/context, role, H1/H2, raw/hash/length, `PASS`, and exact
  Quality PASS attestation/bindings;
- repair-finalizer input provenance including both REPAIR transport and PRIMARY
  semantic identity rules, `TrustedScoreResult`, sealed structured UTF-8 bytes,
  structured SHA-256, structured byte length, and schema/version metadata; and
- model/digest/prompt/schema/policy/options/settings required for every replay.

H2-C must, with no provider calls and only from the immediate runtime-owned
continuation, replay: PRIMARY and eligibility; RNI/request/payload; REPAIR
raw/candidate; TASK-016B; deterministic gate PASS; REPAIR Judge H1/H2/raw
PASS; Quality PASS attestation; REPAIR-aware finalization including both
identity bindings; exact `TrustedScoreResult` equality; byte-for-byte
structured equality; structured SHA-256 equality; structured byte-length
equality; and every cross-binding.  Only then may the separately authorized
H2-C code mint `PhaseHTrustedRepairSuccess`.  Neither a perfect
`TrustedScoreResult`, sealed bytes, nor an aggregate provides an H2-C ingress.

## 22. Required correction tests and final discretion audit

The future correction must remove tests that demonstrate a generic admission
callback (for example, calling `_consume_runtime_role_and_dispatch` and
expecting a callback result).  It must not test that `_` means private.
Instead, it must exercise the actual RuntimeOperations path and include these
RED attacks in addition to the existing matrix:

1. after actual PRIMARY consumption, an obtained admission object cannot
   dispatch arbitrary REPAIR work, caller identity plus closure, or a
   REPAIR_JUDGE callback; no such API exists;
2. after genuine PRIMARY consumption, forged self-consistent PFE B cannot
   trigger H2-B; no caller-facing executor exists;
3. repaired `EMPTY_CONTENT`, `CONTROL_CHARACTER_INVALID`, and
   `EXACT_REPETITION` each terminalize with the frozen message, make zero Judge
   calls, and reach `FAILED_FINAL`; semantic/forged Judge PASS cannot rescue;
4. a gate-pass repaired candidate may proceed to the REPAIR Judge;
5. valid gate PASS/Judge PASS/REPAIR finalization yields an aggregate containing
   `TrustedScoreResult` and sealed bytes/hash/length;
6. PRIMARY request hash in a REPAIR finalizer binding, a different REPAIR
   request identity, or forged Quality PASS attestation each reject;
7. mutated structured bytes, hash, or length; malformed sealed bytes; and
   `object.__new__`/`object.__setattr__` result mutation cannot become future
   persistence authority; and
8. each finalizer local failure terminalizes once with no duplicate outer
   failure route.

Before implementation review, the correction executor must be able to answer
without discretion: no underscore/private authority boundary; no caller
identity-plus-callback dispatch; no caller PFE ingress; the exact
PRIMARY-to-PFE continuity point; gate applicability/order/failure mapping;
no Judge after a gate reject; H2-B finalizer ownership and dual identity
binding; exact structured evidence; and the mandatory H2-C gate/finalizer
replay.  Any unresolved item is `DECISION NEEDED`.

## 23. Round 4: EMPTY_CONTENT reachability and finalizer gate replay

This Round 4 amendment supersedes conflicting Round 3 gate reachability,
terminal-reason, aggregate, H2-C, finalizer, and RED-test wording in sections
19--22.  It changes neither the frozen parent ordering nor the Round 3
authority, dual-binding, scope, or persistence prohibitions.

The parent requires this order:

```text
REPAIR outer protocol capture
  -> inner candidate parse/schema
  -> TASK-016B language
  -> deterministic Content Quality gate
  -> REPAIR Judge
```

The accepted `ScoringCandidate` schema requires a non-empty `reason` and
rejects a `reason` that becomes empty after strip.  Consequently, under that
frozen schema and order, extracted REPAIR content that is empty or
whitespace-only cannot become a valid `ScoringCandidate` which reaches the
post-schema deterministic gate.  H2-B must not change the schema, reorder the
gate before schema, or manufacture a partly invalid candidate to manufacture a
gate test.

`EMPTY_CONTENT` remains a closed classification of the accepted pure TASK-016C
`DeterministicContentQualityGate`, alongside `CONTROL_CHARACTER_INVALID` and
`EXACT_REPETITION`.  It is not removed or weakened.  It is instead
**unreachable as a post-schema H2-B REPAIR runtime gate-terminal reason** under
the current accepted candidate schema.

## 24. Exact empty-content and reachable-gate terminal rules

An outer-valid REPAIR response whose inner candidate has empty or
whitespace-only required textual content follows the already frozen candidate
parse/schema path, not the gate path:

```text
outer capture succeeds
  -> parse/ScoringCandidate schema rejects empty or stripped-whitespace content
  -> REPAIR_SCHEMA_OR_PARSE_INVALID
  -> PipelineRepository.fail_job(
       ErrorCode.INVALID_RESPONSE,
       error_message="REPAIR_SCHEMA_OR_PARSE_INVALID",
       retry_at=None)
  -> FAILED_FINAL -> StageDisposition.TERMINAL
  -> no duplicate _fail(), deterministic-gate progression, Judge contact,
     second REPAIR, or persistence
```

This uses the existing H2-B schema/parse mapping verbatim; no EMPTY-specific
persistent error code or detail is authorized.

The only reachable deterministic-gate terminal reasons in the valid,
post-schema H2-B REPAIR path are exactly:

```text
CONTROL_CHARACTER_INVALID
EXACT_REPETITION
```

For either reachable reason the exact mapping remains:

```text
ErrorCode.INVALID_RESPONSE
error_message="REPAIR_DETERMINISTIC_GATE_REJECT:<reason>"
retry_at=None
  -> FAILED_FINAL -> StageDisposition.TERMINAL
  -> no duplicate _fail(), zero REPAIR Judge contact, no second REPAIR,
     no persistence
```

`<reason>` in this runtime mapping is therefore only one of the two literals
above.  The general pure gate can still return `EMPTY_CONTENT`; its unit
contract is not a claim that all its outcomes are reachable after every
caller’s preceding schema.

## 25. Aggregate and H2-C reachability semantics

A successful `PhaseH2BValidatedRepairResult` carries evidence that the repaired
candidate passed schema, TASK-016B, and the deterministic gate.  It carries no
successful-path or terminal-success representation of an `EMPTY_CONTENT` gate
result.  Failed H2-B paths construct no such aggregate.

H2-C first replays REPAIR candidate parsing/schema.  An empty/whitespace
required field fails that schema replay, invalidates the alleged successful
aggregate, and rejects immediately.  Only after schema replay succeeds does it
rerun TASK-016B and the deterministic gate.  A successful aggregate requires
that gate replay to PASS; H2-C must not expect or accept a successful aggregate
with a post-schema `EMPTY_CONTENT` gate result.

## 26. RepairTrustedScoringFinalizer independently requires gate PASS

`RepairTrustedScoringFinalizer` is an independent trust boundary.  It must not
trust a runtime assertion that the gate passed, a stored gate result, Judge
PASS, or `QualityPassAttestation` as a substitute for its own gate replay.
Before it validates the attestation or produces `TrustedScoreResult`, it must
freshly reconstruct the candidate/input/provenance and use the **same accepted
REPAIR `ContentQualityInput` construction and normalization as Runtime H2-B**:
the repaired candidate reason, exact candidate hash, exact quality-input hash,
and REPAIR request hash (`attempt_role=REPAIR`).  No caller-supplied gate
result, reason, precomputed hash, or REPAIR-only normalization is authority.

The finalizer’s local order is exactly:

```text
fresh schema revalidation of candidate/input/provenance
  -> reconstruct accepted REPAIR deterministic-gate input
  -> run accepted deterministic gate and require PASS
  -> derive/revalidate REPAIR Judge bindings and replay/require Judge PASS
  -> revalidate QualityPassAttestation
  -> validate RNI/REPAIR request identity and dual-binding provenance
  -> shared pure finalization core -> TrustedScoreResult
  -> unchanged exact-type serializer -> structured bytes/hash/length
```

No finalizer output is permitted before gate PASS.  The attestation proves the
Judge PASS binding; it does not prove or replace deterministic-gate PASS.

For a schema-valid direct finalizer input, any gate result other than PASS,
including `CONTROL_CHARACTER_INVALID` or `EXACT_REPETITION`, rejects
finalization even if the caller supplies valid-looking REPAIR Judge PASS,
attestation, RNI, and request provenance.  It produces no `TrustedScoreResult`,
sealed structured bytes, or H2-B aggregate component.

For a low-level forged/bypassed candidate whose reason is empty or whitespace,
the required fresh schema revalidation rejects it before gate input exists.
That is the frozen-order finalizer defense and is mapped as a local
finalization rejection; a test must not assert the impossible claim that a
freshly schema-valid finalizer candidate then obtains post-schema
`EMPTY_CONTENT`.  The pure-gate regression separately proves that direct gate
input containing empty content returns `EMPTY_CONTENT`.  This preserves both
schema integrity and the general gate contract without weakening either.

If a finalizer gate replay or any other local finalization predicate rejects
inside actual H2-B runtime control flow, the runtime maps it exactly to
`REPAIR_FINALIZATION_INVALID`, `ErrorCode.INVALID_RESPONSE`, `retry_at=None`,
`FAILED_FINAL`, and `StageDisposition.TERMINAL`, with no duplicate `_fail()`,
second REPAIR/Judge, persistence, or `UNKNOWN_PROVIDER_STATE`.  A pure
adversarial unit invocation may raise the exact local finalization exception;
it has no job-state side effect.

H2-C intentionally has two gate defenses: its evidence-graph replay reruns
the gate after schema/language, and its REPAIR-aware finalizer replay itself
requires gate PASS.  Neither may be optimized away.

## 27. Round 4 required future RED matrix and reconciliation

The future correction must include these distinct cases:

1. empty REPAIR content on the production path -> schema/parse invalid,
   `FAILED_FINAL`, zero gate-to-Judge progression, zero Judge;
2. whitespace-only REPAIR content -> the same schema/parse terminal path;
3. schema-valid `CONTROL_CHARACTER_INVALID` -> deterministic-gate terminal,
   `FAILED_FINAL`, zero Judge;
4. schema-valid `EXACT_REPETITION` -> the same deterministic-gate terminal;
5. gate PASS -> may proceed to Judge;
6. direct pure-gate empty-content input valid for the pure gate’s own contract
   -> `EMPTY_CONTENT`;
7. direct finalizer with a schema-valid gate-invalid candidate plus forged or
   valid-looking Judge PASS/attestation -> gate replay rejects, no trusted or
   sealed result;
8. direct finalizer `CONTROL_CHARACTER_INVALID` and `EXACT_REPETITION` cases
   -> reject even with valid-looking Judge PASS/attestation;
9. low-level/model-constructed empty finalizer input -> fresh schema
   revalidation rejects, no trusted or sealed result; and
10. valid schema/language/gate/Judge/attestation chain -> may produce the
    `TrustedScoreResult` and sealed evidence.

Parent compatibility was rechecked.  The parent requires schema -> language
-> deterministic gate -> Judge and says the gate may reject before Judge; it
does not mandate that `EMPTY_CONTENT` be observable as a post-schema REPAIR
runtime gate error.  It also does not prohibit redundant finalizer-side gate
verification.  Therefore no parent authorization amendment is required.

The Round 3 dual binding is unchanged: the semantic score remains bound to the
PRIMARY request hash, while RNI, REPAIR request/payload/raw/candidate/Judge/
attestation/finalizer provenance and aggregate/H2-C replay bind REPAIR.  The
RuntimeOperations-only branch, no callback admission authority, no PFE ingress,
state-only admission correction, A-to-A/J-to-J checks, `quality.py`-only
finalizer scope, frozen `scoring.py`, and all Phase G/H2-C/persistence
prohibitions are unchanged.

After this amendment an implementation agent has no discretion over whether
EMPTY_CONTENT is schema or runtime-gate failure, whether schema/gate order may
change, the empty-content mapping, the reachable post-schema reasons, whether
the finalizer reruns the gate, whether Judge/attestation rescues a gate failure,
or the H2-C EMPTY replay rule.  Any different requirement is `DECISION NEEDED`.
