# TASK-016C Phase H2-C — Trusted Repair Success Minting and Phase G Re-entry

## Status and scope

Status: **READY FOR H2-C AUTHORIZATION AMENDMENT ROUND 2 INDEPENDENT REVIEW**.

This is documentation/design authorization only. It authorizes no source or
test change in this commit, no provider/Judge contact, no Phase I work, no
schema or migration, and no merge/push/tag/rebase/reset/squash. It is
subordinate to accepted H2/H2-B contracts and baseline `c6626ab` / `487a1e4`.
It replaces only the future live H2-B-PASS transition from
`CAPABILITY_UNAVAILABLE/H2B_PASS_AWAITING_H2C`; historical rows stay unchanged.

Reuse decision: **DIRECT** — use accepted H2 evidence, finalizer, deterministic
gate, Phase G plan/writer, SQLite schema, and standard-library UTF-8/SHA-256.
No dependency or third-party component is added.

## 1. Frozen H2-C entry and distinct predicates

H2-C exists only immediately after local construction of
`aggregate = PhaseH2BValidatedRepairResult(...)`, in the same actual
`RuntimeOperations` SCORING-stage branch that performed PRIMARY, admitted and
consumed REPAIR and REPAIR_JUDGE, and completed H2-B:

```text
actual RuntimeOperations SCORING continuation
  -> local H2-B aggregate
  -> H2-C 23-step replay
  -> PhaseHTrustedRepairSuccess data
  -> trusted Phase G persist_success data ingress
```

There is no caller-facing H2-C finalizer, verifier, mint, aggregate ingress,
retry/resume route, cache route, or historical-row reconstruction. This
forbids, including underscore aliases: `h2c_finalize`, `finalize_repair`,
`verify_h2b_result`, `mint_repair_success`, `persist_validated_repair`,
`persist_repair`, `persist_h2c`, `repair_writer`, and
`repair_repository_success`. Possession of an aggregate never authorizes H2-C.
No `repair_consumed`, `judge_consumed`, `admitted` boolean, token, receipt,
registry key, nonce, sentinel, callback, or returned continuation is authorized.

These predicates are separate:

1. **Data integrity** — fields, hashes, envelope, and sealed structured bytes
   agree internally.
2. **Semantic validity** — independent H2-C replay derives expected values and
   all 23 checks pass.
3. **Execution authority** — the operation belongs to actual live runtime work
   for an owned SCORING job.

The first two are evidence properties. They do not by themselves create the
third.

## 2. Persistence-authority feasibility resolution

### 2.1 Formal result

Let `S` be identical, fully self-consistent `PhaseHTrustedRepairSuccess` data.
The legitimate path holds `S` after actual H2-C replay; the attack path holds
the same `S` and directly calls a reachable trusted-success writer. No field
of `S` can distinguish the calls.

Under the requested constraints no mechanically enforceable `A` remains: the
attacker may import private APIs and construct values; object identity and
private construction are not authority; mutable runtime state, globals,
`ContextVar`/thread-local state, tokens/nonces/sentinels, registries/receipts,
callbacks/closures, and stack/code-object identity are all excluded; and the
writer is reachable. A repository lease proves current job state, not that this
particular `S` traversed H2-C. The former active-frame guard is therefore not
authorized and must not be implemented.

**H2-C PERSISTENCE AUTHORITY CONSTRAINT INCOMPATIBILITY:** requiring a reachable
writer to reject identical self-consistent data while excluding every non-data
distinction is jointly unsatisfiable in the same Python process.

### 2.2 Authority-class audit

| Class | Permitted? | Reproducible by stated attacker? | Resolution |
|---|---:|---:|---|
| Success-object data | data only | yes | integrity/validity, never authority |
| Mutable `RuntimeOperations` state | no | yes | forbidden and insufficient |
| Global / `ContextVar` / thread-local | no | yes | forbidden and insufficient |
| Token / nonce / sentinel | no | yes if reachable | forbidden |
| Registry / receipt | no | yes if reachable | forbidden |
| Callback / closure | no | private import/call is possible | forbidden |
| Python stack / code object | no | direct invocation can reproduce it | insufficient |
| Durable repository state | lease only | observable/reusable | no proof of prior H2-C |
| Non-exported lexical operation | organization only | yes via private import | not a primitive |
| External process/OS capability | absent | n/a | unapproved/unavailable |
| Threat-model exclusion | yes if explicit | n/a | selected below |

### 2.3 Selected option — Option 1, explicit Phase G assumption

This amendment selects **Option 1: align H2-C with the accepted Phase G / Phase
F trusted-success boundary assumption**. This is a material threat-model
clarification requiring independent review.

`TrustedPersistenceEntry.persist_success(success)` remains the sole Phase G
trusted-success data ingress and accepts the exact closed union:

```text
type(success) is PhaseFTrustedScoringSuccess -> existing PRIMARY verifier
type(success) is PhaseHTrustedRepairSuccess  -> REPAIR verifier defined here
otherwise                                     -> reject before field access
```

The API accepts no plan, raw hash, artifact path, ProviderCall object, settings
object, runtime context, capability, or repair-specific method. It is an
internal trusted-success boundary despite being directly callable in a
same-process test/import environment. Exact type is necessary for dispatch but
is not authority; neither are frozen dataclasses, private constructors, object
identity, envelope/hash equality, subclass rejection, or secret-looking fields.

The same-process model protects all untrusted evidence ingress up to the
trusted-success mint boundary: aggregate cannot mint; H2-C runs only in the
actual lexical branch; data is independently replayed; and the writer rejects
wrong exact type, subclass, malformed/inconsistent graph, and wrong repository
job/lease state before filesystem work. **Once an exact
`PhaseFTrustedScoringSuccess` or `PhaseHTrustedRepairSuccess` has been produced
by that trusted runtime boundary, arbitrary direct invocation of the internal
Phase G trusted-success API with an independently fully self-consistent forged
exact success is outside this threat model.**

Thus a future test must not claim that an identical self-consistent same-process
forged `S` directly calling `persist_success` rejects. Required tests instead
prove aggregate cannot mint, inconsistent forged success rejects, wrong
job/owner/lease rejects before files, and no alternate untrusted-data ingress
exists. No token, receipt, registry, sentinel, callback, closure, or
caller-submittable context is introduced.

Calling the public runtime SCORING workflow directly is not a forged-success
bypass if it acquires/verifies the actual lease, performs actual PRIMARY,
H2-B, H2-C replay, and persistence; it is a legitimate full execution. The
target is bypassing that preceding workflow with success data, not blocking the
whole legitimate runtime workflow.

This exposes a **PHASE G PRE-EXISTING AUTHORITY ASSUMPTION**: Phase F already
uses this trusted-success boundary. H2-C neither cures nor silently worsens
that assumption; it applies it to the closed union while retaining the stronger
H2-C no-aggregate-ingress controls.

**Final authority sentence:** An attacker with identical repair-success data
cannot obtain repaired-success persistence within this authorization's
protected boundary because only the live runtime may mint trusted success;
arbitrary direct calls with a fully self-consistent forged trusted-success
object are explicitly outside the inherited Phase G boundary threat model.

## 3. Runtime roots, replay, and failure eligibility

The runtime trust roots are exactly: current `job_id`; current owner and active
SCORING lease; original validated `ScoringInput`; rebuilt
`PrimaryTrustedContext`; current validated `LocalScoringSettings`; current
general/threshold settings named in section 5; runtime quality authority; and
the local H2-B aggregate as untrusted material. No aggregate duplicate, caller
settings/context/job/owner/Judge context, or semantic PRIMARY identity is a
root. Python object identity is irrelevant.

Every security-significant nested object is freshly parsed/rebuilt from strict
primitive or sealed bytes and expected runtime context before comparison.
`object.__new__`, `object.__setattr__`, `model_construct`, fake subclasses,
extra attributes, copy/deepcopy, pickle, frozen models, and private construction
have no trust effect.

The normative no-network replay sequence is exactly:

1. verify current job/owner/active lease;
2. rebuild `PrimaryTrustedContext` from original input and settings;
3. strictly reconstruct and verify PRIMARY evidence / `PrimaryFailureEvidence`;
4. require eligible exact failure class;
5. rebuild `RepairNormalizedInput` using
   `build_repair_normalized_input(job_id, primary_trusted_context,
   failure_evidence, validated_settings)`;
6. recompute exact H2-JCS RNI bytes;
7. recompute RNI SHA-256;
8. recompute REPAIR request hash;
9. render `render_task016c_repair_prompt_v2` and exact payload;
10. compare model, prompt, `stream=false`, format, `think=false`, temperature,
    `num_predict`, UTF-8 bytes, hash, and length;
11. replay strict REPAIR raw/hash/length/protocol and extract response;
12. parse candidate again and compare candidate/hash;
13. rerun only TASK-016B and require exact `VALID` evidence;
14. reconstruct quality input, rerun deterministic gate, require PASS;
15. rebuild REPAIR Judge context/operation input with `attempt_role=REPAIR`;
16. recompute Judge H1 and H2;
17. replay strict Judge raw/hash/length and pure-verify PASS;
18. revalidate exact REPAIR `QualityPassAttestation`;
19. independently invoke `RepairTrustedScoringFinalizer`;
20. require exact `TrustedScoreResult` field equality;
21. recompute sealed structured bytes/hash/length/schema/prompt equality;
22. recheck settings and complete PRIMARY/REPAIR cross-bindings; and
23. only then mint `PhaseHTrustedRepairSuccess` data.

The H2-B 21-step contract is preserved: old 1–4 map to 1–4; 5–8 to 5–10; 9 to
11; 10–11 to 12; 12 to 19–21; 13 to 13; 14–16 to 15–16; 17–19 to 17; 20 to 18
and 22; and 21 to 1–2 and 22. It makes finalizer/gate/sealed-byte redundancy
explicit rather than replacing a frozen check.

Replay makes zero `/api/tags`, zero `/api/generate`, zero provider-factory
contact, and zero Judge network call on success or failure. A network
dependency is a design blocker.

Eligible PRIMARY classes are exactly `SCHEMA_OR_PARSE_INVALID`,
`LANGUAGE_INVALID`, `JUDGE_REJECT`, and `JUDGE_UNCERTAIN`; every other class,
including `UNKNOWN_PROVIDER_STATE`, rejects. Schema/parse requires PRIMARY raw
and approved parser diagnostic; language requires replayed TASK-016B INVALID;
Judge reject/uncertain requires captured PRIMARY Judge raw to pure-replay to
that semantic. PRIMARY replay always binds original input, expected context, P,
applicable PRIMARY raw/candidate, PFE/classification, and applicable Judge
evidence/raw.

Let P be PRIMARY semantic request hash, R REPAIR scoring request hash, and J
REPAIR Judge H2. `P != R`; R binds RNI/payload/raw/candidate/gate/Judge/
attestation/finalizer provenance; J binds the same R and replayed candidate;
the trusted semantic result retains P. A same-candidate R1/R2 substitution
rejects unless the entire deterministic graph is R2-consistent, which it cannot
be when runtime-derived R is R1.

## 4. H2-C trust result and Phase G mapping

`PhaseHTrustedRepairSuccess` is a narrow immutable data carrier in
`src/youtube_intel/scoring.py` next to `PhaseFTrustedScoringSuccess` and
`TrustedPersistenceEntry`. It has no persistence behavior and no public
mint/factory. It is not a capability.

Its exact fields are:

```text
job_id: str
owner: str
pipeline_version: str
primary_request_hash: lower-hex SHA-256 P
primary_normalized_input_hash: lower-hex SHA-256
scoring_input_sha256: lower-hex SHA-256
repair_composite_envelope_bytes: strict UTF-8 H2-JCS bytes
repair_composite_envelope_sha256: lower-hex SHA-256
repair_composite_envelope_length: non-negative int
trusted_result: exact TrustedScoreResult
structured_bytes: exact sealed UTF-8 finalizer bytes
structured_sha256: lower-hex SHA-256
structured_length: non-negative int
prompt_version: "scoring-prompt-v2"
schema_version: "score-result-v2"
```

It also carries parsed exact six-field `RepairCompositeEnvelope` only as a
redundant in-memory verifier input; sealed bytes are authoritative. It contains
no caller plan/scatter fields and no settings object.

The root envelope has exactly these ordered logical fields and no extras:
`envelope_schema`, `primary_failure_evidence`, `repair_provider_evidence`,
`repair_candidate_evidence`, `repair_quality_evidence`, and
`finalizer_binding`; `envelope_schema` is
`"trusted-scoring-repair-envelope-v1"`. H2 Canonical JSON v1 / RFC 8785 JCS,
strict UTF-8, duplicate-key rejection, and canonical-reserialize equality are
the parent-frozen representation. Raw captures are strict UTF-8 strings as JCS
JSON strings—not base64 or another application encoding.

Shared artifacts remain `scoring/<P>/raw` and `scoring/<P>/structured`. Exact
raw bytes are the repaired composite envelope; structured bytes are replayed
finalizer bytes and must never be reserialized. REPAIR creates exactly two
truthful successful ProviderCall rows: R with `operation="local-scoring-repair-v1"`,
repair provider/model, RNI hash, repair prompt/schema and raw Artifact ID; and
J with `operation="local-content-quality-v1"`, actual Judge provider/model,
Judge H1, quality prompt/schema and the same raw Artifact ID. No synthetic
successful PRIMARY ProviderCall is written. Failed PRIMARY P/PFE/raw/candidate/
Judge provenance survives in the envelope.

`SCORING_RAW` is compatible because Phase G already stores a versioned
provenance envelope under that kind. No migration, table, column, or ArtifactKind
is required. PREWRITE/no-clobber/fsync/promotion, atomic SQLite registration,
and `SUCCEEDED` transition remain Phase G behavior.

## 5. Exact semantic settings provenance

`H2CSettingsProvenance` is exact typed, `extra="forbid"`, and versioned:

```text
schema_version: Literal["task016c-h2c-settings-provenance-v1"]
scoring_provider: Literal["ollama"]
scoring_base_url: non-empty validated loopback HTTP origin
scoring_model: non-empty trimmed str
scoring_model_digest: str matching sha256:[0-9a-f]{64}
temperature: finite IEEE-754 binary64, 0 <= value <= 2
max_output_tokens: integer, 1 <= value <= 2147483647
max_transcript_chars: integer, 3 <= value <= 131072
max_description_chars: integer, 0 <= value <= 20000
output_language: Literal["zh-CN", "en"]
summary_score_threshold: finite IEEE-754 binary64, 0 <= value <= 10
scoring_operation: Literal["local-scoring"]
scoring_prompt_version: Literal["scoring-prompt-v2"]
scoring_schema_version: Literal["score-result-v2"]
repair_operation: Literal["local-scoring-repair-v1"]
repair_prompt_version: Literal["scoring-prompt-v2"]
repair_schema_version: Literal["score-result-v2"]
repair_stream: Literal[false]
repair_think: Literal[false]
repair_format_schema_sha256: lower-hex SHA-256 of frozen score-result-v2 schema JCS
repair_num_predict: integer exactly equal to max_output_tokens
judge_operation: Literal["local-content-quality-v1"]
judge_provider: Literal["ollama"]
judge_base_url: non-empty validated loopback HTTP origin, exactly scoring_base_url
judge_model: non-empty trimmed str
judge_model_digest: str matching sha256:[0-9a-f]{64}
quality_policy_version: Literal["content-quality-policy-v1"]
quality_prompt_version: Literal["content-quality-prompt-v1"]
quality_schema_version: Literal["content-quality-result-v1"]
language_validator_contract: Literal["task016b-scoring-language-validator-v1"]
```

Strings are validated stored strings with no trim, case, Unicode, URL, or
default substitution during construction. Booleans are JSON literals; integers
satisfy stated bounds before H2 JCS; floats are finite and use frozen JCS
numeric rules (`-0.0` becomes `0`); null is forbidden in every field.

`general.output_language` is explicitly bound. `thresholds.summary_score` is
**BOUND**: it changes Phase G persisted `should_summarize`, even though it does
not change model score. `max_transcript_chars` is not assumed globally bounded;
the 131072 ceiling is a repair-persistence admission condition. A current config
above it terminally rejects H2-C before mint/persistence.

Canonical provenance is exact typed value -> H2 JCS strict UTF-8 -> SHA-256
lower hex. Bytes/hash are durable at
`repair_provider_evidence.settings_provenance` and
`repair_provider_evidence.settings_provenance_sha256`. This amends only that
nested schema to `"task016c-repair-provider-evidence-v2"`; the parent envelope
remains exactly six fields. The nested hash equals the JCS bytes of the nested
typed provenance.

Live H2-C derives current provenance and compares exact bytes/hash. Historical
repaired readers load the durable nested value, canonicalize/hash/validate it
and P/R/J links, but must not compare it to current application settings.
Complete graph identity includes P, R, J, envelope version/hash, structured
version/hash, and settings-provenance version/hash.

## 6. Bounded repair-envelope admission

This chooses **bounded admission (Option A)**. Domain-valid unbounded metadata
or transcript data cannot enter H2-C persistence unless it meets these
repair-only serialized-component limits. Oversize is not truncation or retry.

Every variable-size value is bounded by its containing canonical subtree; no
inner value bypasses that cap. External captures are additionally bounded:

| Component / contained variable material | Exact max bytes |
|---|---:|
| `primary_failure_evidence` canonical subtree (original input, metadata, sample, PFE diagnostic, PRIMARY raw/candidate/Judge evidence) | 8,388,608 |
| PRIMARY outer raw within it | 1,000,000 |
| PRIMARY Judge raw within it, if applicable | 20,000 |
| `repair_provider_evidence` canonical subtree (RNI, RNI bytes/hash, prompt/payload bytes/hash, settings provenance/hash) | 8,388,608 |
| RNI canonical bytes within it | 393,216 |
| REPAIR prompt bytes within it | 393,216 |
| REPAIR payload bytes within it | 393,216 |
| settings provenance bytes within it | 8,192 |
| `repair_candidate_evidence` canonical subtree (REPAIR raw, extracted content, candidate/hash, language evidence) | 7,340,032 |
| REPAIR outer raw within it | 1,000,000 |
| extracted content/candidate/language evidence collectively | 1,340,032 |
| `repair_quality_evidence` canonical subtree (quality input/gate, Judge input/H1/H2/raw/evidence, attestation) | 8,388,608 |
| REPAIR Judge raw within it | 20,000 |
| `finalizer_binding` canonical subtree (trusted result, structured binding, P/R/J commitment) | 1,044,480 |
| root schema, field names, JCS punctuation, enclosing syntax | 4,096 |

The subtree limit is the exact bound for all nested variable fields not named
separately: title, description, channel, URL/id, transcript sample, candidate
strings/topics, parser/PFE diagnostics, quality evidence excerpts, settings
bytes, hashes, and version literals. The narrower explicit row wins. Nothing is
normalized, silently abbreviated, or replaced to fit.

Worst-case JCS escaping is six emitted ASCII bytes per control-character input
UTF-8 byte; non-control UTF-8 emits at most source bytes. Serialize each typed
subtree and enforce its cap, then root-serialize and enforce:

```text
8,388,608 + 8,388,608 + 7,340,032 + 8,388,608 + 1,044,480 + 4,096
= 33,554,432 bytes
```

The exact repaired-envelope maximum is **33,554,432 bytes**. This proves a
persistence-admission bound, not that every domain-valid input fits. A
maximum-valid fixture must put every component at its admitted boundary with
schema-valid evidence/captures and show its root remains within total; separate
fixtures prove each external raw maximum. Reader/writer accept `<= 33,554,432`,
including max-1/max; max+1 rejects. Legacy PRIMARY raw readers keep 1,000,000.

Oversize maps exactly to `ErrorCode.TRUST_INTEGRITY_INVALID`, diagnostic
`H2C_REPLAY_INVALID:ENVELOPE_OVERSIZE`, `retry_at=None`, `FAILED_FINAL`, and
`TERMINAL`: zero network, filesystem, or persistence.

## 7. Reader compatibility and graph identity

Approved repaired producers are exactly:

```text
raw producer:        scoring-raw-content-quality-repair-v1
structured producer: scoring-structured-content-quality-repair-v1
envelope schema:     trusted-scoring-repair-envelope-v1
```

Dispatch is exact producer version only, never heuristic. Legacy PRIMARY
producers preserve P-keyed successful `local-scoring` lookup and 1,000,000-byte
raw bound. Unknown, mixed, or repaired producer paired with legacy-shaped raw
rejects fail closed.

For repaired structured data the reader validates `scoring/<P>/structured`,
loads paired repaired `scoring/<P>/raw`, parses/re-canonicalizes the envelope,
derives P from `TrustedScoreResult`, reads R only from
`repair_provider_evidence.request_hash`, reads J only from replayed REPAIR
Judge H2 in `repair_quality_evidence`, loads exactly those two successful
ProviderCalls, validates operation/provider/model/input/prompt/schema/raw
Artifact ID and full P/R/J/settings bindings, and returns the same trusted
result interface. It never searches successful ProviderCall by P for repair.
It loads settings only from `repair_provider_evidence.settings_provenance`.

Existing `SCORING_RAW` semantics are correct because it already stores a
provenance envelope. The runtime scoring-provenance reader must branch; other
readers must branch by producer version or safely reject. This is compatibility,
not cache reuse/trust/recovery/cross-job lookup/historical continuation/Phase I.

## 8. Repair-only PREWRITE, lease races, and orphan adoption

Only REPAIR gains these rules; Phase F ordering/orphan behavior stay frozen.
Exact REPAIR PREWRITE order:

1. exact union/type dispatch (not authority);
2. repair data-shape check;
3. composite version/JCS/hash/length/admission-bound replay;
4. trusted-result and sealed structured replay;
5. P/R/J/settings-provenance cross-binding;
6. repository-owned current job/owner/RUNNING-SCORING/active-lease check;
7. committed-graph/idempotency check and repair orphan disposition;
8. temp/write/fsync/hash/no-clobber promotion/reopen verification;
9. final owned-running-job/SQLite transaction recheck;
10. artifact and two truthful ProviderCall registrations; and
11. success transition.

Step 6 uses entry/repository context, never success-object claims alone. A
stale runtime raises `ScoringDispatchDenied`, performs no `fail_job` because it
no longer owns the job, makes zero filesystem changes, records no error code or
detail, leaves retry/status unchanged, and returns no stale-owner disposition.
Owner-authoritative interrupted-SCORING lease recovery retains its established
`UNKNOWN_PROVIDER_STATE` outcome.

The repair-only availability rule is **verified identical orphan adoption
(Option A)**. After step 6 and before writing, adoption is allowed only if the
valid lease holds, neither Artifact row nor either ProviderCall row exists, job
is not successful, and each existing final is a safe regular file whose bytes,
length, SHA-256, expected producer/path, and planned artifact identity match.
Bytes are material only; the later SQLite transaction is authoritative.

| State after valid precheck | Exact repair behavior |
|---|---|
| neither final / no DB graph | write both through existing no-clobber path |
| raw only exact orphan / no DB graph | adopt raw; write structured only |
| structured only exact orphan / no DB graph | adopt structured; write raw only |
| both exact orphans / no DB graph | adopt both; register under current lease |
| mismatch, unsafe/corrupt file, or partial DB row/call | fail closed; no overwrite/adoption |
| complete exact committed graph | existing same-plan idempotent return |

No final is deleted or overwritten. A post-precheck lease change makes final
SQLite validation reject and cannot mark success; a promoted file is
non-authoritative but later adoptable only under this table. This prevents known
stale writes and permanent no-clobber blockage while retaining no overwrite.

## 9. Error, retry, crash, and capability policy

`ErrorCode.TRUST_INTEGRITY_INVALID = "TRUST_INTEGRITY_INVALID"` is the tenth
durable system error code. It means local trusted replay, provenance, or
integrity verification failed after external attempts; it is neither provider
`INVALID_RESPONSE`, capability absence, nor `LOCAL_RESOURCE`. It is terminal,
non-retryable automatically/manually, no infrastructure alert, no unrelated
work stop, and requires trust-boundary review.

The sole retry exclusion predicate is:

```text
failed_job.last_error_code == ErrorCode.TRUST_INTEGRITY_INVALID.value
```

Detail is diagnostic only. The closed set is:

```text
PRIMARY_EVIDENCE_MISMATCH, PFE_INVALID, FAILURE_CLASS_INELIGIBLE,
RNI_MISMATCH, REPAIR_REQUEST_MISMATCH, REPAIR_PAYLOAD_MISMATCH,
REPAIR_RAW_INVALID, CANDIDATE_MISMATCH, LANGUAGE_INVALID,
DETERMINISTIC_GATE_INVALID, JUDGE_EVIDENCE_INVALID, ATTESTATION_INVALID,
FINALIZER_INVALID, TRUSTED_RESULT_MISMATCH, STRUCTURED_RESULT_MISMATCH,
SETTINGS_MISMATCH, PROVENANCE_MISMATCH, ENVELOPE_OVERSIZE
```

Each is only `H2C_REPLAY_INVALID:<REASON>`. Settings mismatch is exactly trust
code plus `H2C_REPLAY_INVALID:SETTINGS_MISMATCH`; replay failures use one
owner-authoritative `fail_job`, `retry_at=None`, `FAILED_FINAL`, `TERMINAL`.
Trust code remains excluded if detail changes; ordinary retry-eligible code
with this prefix remains ordinarily eligible. `CAPABILITY_UNAVAILABLE` remains
build-without-H2-C only; historical rows remain terminal/manual-retry-excluded.

Exact new safe mappings:

```text
providers/subtitles.py::_safe_boundary_error:
  ErrorCode.TRUST_INTEGRITY_INVALID ->
  f"{subject} trust integrity verification failed"

transcripts.py::_adapter_boundary_error:
  ErrorCode.TRUST_INTEGRITY_INVALID -> detail =
  "trust integrity verification failed"
  -> f"subtitle adapter {detail} during {operation}"
```

Prior-code mappings, including `CAPABILITY_UNAVAILABLE` and `LOCAL_RESOURCE`,
stay unchanged. Required audit: `domain.py`, `runtime.py`,
`providers/subtitles.py`, `transcripts.py`, and
`tests/unit/test_contracts.py` exact-ten contract; repeat full production
`ErrorCode` search and permit no unknown-to-local fallback.

Crash before mint or after mint/before persistence retains no durable aggregate
and follows H1 interrupted-SCORING/lease recovery; never reconstruct H2-C or
redispatch REPAIR/Judge. Once persistence begins, Phase G filesystem/SQLite
crash behavior applies, supplemented only by repair orphan adoption. H2-C adds
no cache/recovery writer.

## 10. Required tests and narrow future scope

Future tests must prove:

- no H2-C aggregate/finalize/mint API, token/receipt/registry/callback authority,
  and no aggregate/runtime-object caller ingress;
- inconsistent object-new/setattr/model-construct/copy/deepcopy/pickle/fake
  subclass/extra-attribute successes reject; wrong job/owner/expired lease
  rejects before files; fully self-consistent direct success is explicitly
  outside the selected Phase G trusted-success assumption;
- mutation rejection for PFE/class/RNI/JCS/R/payload/raw/candidate/language/gate/
  Judge H1-H2-raw/attestation/finalizer/result/structured/settings; same-
  candidate R1/R2 substitution; zero provider/Judge network success/failure;
- semantic-equal distinct settings accept; mutate output language, repair/Judge
  model/digest, temperature, output limit, prompt/schema, policy, and summary
  threshold to reject with settings detail;
- schema-valid maximum-component envelope, raw maxima, max-1/max/max+1, and
  oversize zero network/files/persistence;
- legacy P reader unchanged; repaired R/J reader/durable settings validation;
  wrong/missing/colliding P/R/J, mixed/unknown producer, raw shape/bound reject;
  two ProviderCalls truthful;
- invalid-before-write zero files; post-precheck race no DB success; raw-only,
  structured-only, paired exact, mismatch, and corrupt orphan cases; Phase F
  unchanged; and
- code-only retry attacks, primary Phase F regression, repaired byte equality,
  no-clobber/idempotency, and exact successful job/video state.

Authorized production scope in a later implementation is exactly:

```text
src/youtube_intel/runtime.py
src/youtube_intel/h2_evidence.py
src/youtube_intel/quality.py
src/youtube_intel/scoring.py
src/youtube_intel/domain.py
src/youtube_intel/providers/subtitles.py
src/youtube_intel/transcripts.py
```

`scoring.py` may define carrier/union/repair verifier/bound/precheck/adoption/
producer mapping and reuse existing plan/writer; no new public writer, scatter
plan, H2 SQLite writer/path, or PRIMARY semantic change. `runtime.py` may add
lexical continuation, failure/retry mapping, and minimum repaired reader branch.
`h2_evidence.py`/`quality.py` only typed replay helpers. `domain.py` and error
consumers only tenth code/mappings. `state.py` and migrations remain frozen;
schema represents R/J and producer metadata. Phase I is out of scope.

## 11. Security-discretion audit and implementation gate

No executor may choose: direct-forged-success scope (explicitly outside inherited
trusted-success boundary), API shape, token/receipt use, replay order, settings
schema/output-language/threshold/storage, admission bounds/total, oversize
mapping, P/R/J reader rules, orphan adoption, lease failure, error/retry/detail,
safe messages, consumer scope, Phase F asymmetry, schema/migration, or Phase I.
Any deviation is `DECISION NEEDED`.

Before implementation an independent reviewer must accept the material Phase G
threat-model clarification, settings/envelope contracts, repair-only orphan
adoption, and code-only error policy. H2-C implementation remains unauthorized.
