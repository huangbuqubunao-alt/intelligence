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

The frozen parent H2 direct-forged-success test wording is reconciled as
follows: it continues to require rejection of an aggregate, wrong type,
subclass, malformed, inconsistent, or pre-mint forged repair-success value.
To the extent it could be read to require rejection of a fully self-consistent
exact trusted-success value directly submitted inside the same process, this
Round 3 system-level Phase G assumption controls. The parent document is not
retroactively edited; no implementation may claim both properties.

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

Legacy/PRIMARY shared artifacts remain `scoring/<P>/raw` and
`scoring/<P>/structured`; the repair graph paths are superseded by section
12.1. Exact raw bytes are the repaired composite envelope; structured bytes are
replayed finalizer bytes and must never be reserialized. REPAIR creates exactly two
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

For repaired structured data, section 12.1's G-derived path procedure applies:
after it validates the claimed P/G grammar and recomputes G from the raw
envelope, the reader derives P from `TrustedScoreResult`, reads R only from
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

## 12. Round 3 amendments — graph identity, evidence v2, and stale lease

This section supersedes only conflicting Round 2 persistence-path, nested
`RepairProviderEvidence`, settings-bound, stale-lease, reader, orphan, and
implementation-scope wording. It does not reopen any accepted Round 2 decision.

### 12.1 Repair persistence graph identity and physical paths

P remains the PRIMARY semantic scoring identity and may remain the top-level
directory namespace. It is not a complete REPAIR persistence identity. The
physical repair graph must distinguish a PRIMARY graph from a REPAIR graph and
must distinguish any two repair graphs with a different R, REPAIR Judge H2, or
settings provenance hash, even if P and the semantic `TrustedScoreResult` are
identical.

The exact typed graph identity is:

```text
RepairPersistenceGraphIdentity, extra="forbid"

schema_version: Literal["task016c-repair-persistence-graph-v1"]
primary_request_hash: lowercase 64-character SHA-256 P
repair_request_hash: lowercase 64-character SHA-256 R
repair_judge_request_hash: lowercase 64-character SHA-256 J
settings_provenance_sha256: lowercase 64-character SHA-256
raw_producer_version: Literal["scoring-raw-content-quality-repair-v1"]
structured_producer_version: Literal["scoring-structured-content-quality-repair-v1"]
envelope_schema: Literal["trusted-scoring-repair-envelope-v1"]
repair_provider_evidence_schema: Literal["task016c-repair-provider-evidence-v2"]
quality_policy_version: Literal["content-quality-policy-v1"]
quality_prompt_version: Literal["content-quality-prompt-v1"]
quality_schema_version: Literal["content-quality-result-v1"]
```

All fields are non-null. The key is exactly:

```text
typed RepairPersistenceGraphIdentity
  -> H2 Canonical JSON v1 / RFC 8785 JCS strict UTF-8 bytes
  -> SHA-256 lower hexadecimal = G
```

`G` is a fixed 64-character lowercase SHA-256 value. The exact REPAIR keys and
relative paths are:

```text
raw artifact_key:           scoring/<P>/repair/<G>/raw
raw relative_path:          scoring/<P>/repair/<G>/raw.json
structured artifact_key:    scoring/<P>/repair/<G>/structured
structured relative_path:   scoring/<P>/repair/<G>/structured.json
```

`P` and `G` are only fixed lower-hex hashes; no caller path fragment,
provider/model name, separator, `..`, or evidence string can influence a path.
Phase F and every legacy/PRIMARY path remain exactly
`scoring/<P>/raw(.json)` and `scoring/<P>/structured(.json)`.

ProviderCall identity remains R and J; G is persistence identity only and is
never substituted into a ProviderCall request hash. The REPAIR raw ProviderCall
uses the G-based raw `artifact_key` as its deterministic artifact key, and both
truthful REPAIR ProviderCalls bind to that raw Artifact ID. The corresponding
Artifact IDs retain Phase G's existing `sha256(artifact_key + content_hash)`
derivation, now over the G-based keys.

The SQLite audit is positive: `artifacts.artifact_key` is the sole relevant
unique key (`001_initial.sql`), while `video_id`, `kind`, P, relative path,
content hash, and producer version have no uniqueness constraint that would
prevent distinct keys. Therefore the same P may have multiple repair raw and
structured Artifact records with different G values, and no migration is
required. A DB row's exact `artifact_key`, `relative_path`, producer version,
content hash, and Artifact ID must equal the expected P/G plan; any mismatch
fails closed.

The invariants are exact:

```text
same P/R/J/settings/producers/envelope schema/v2/quality versions
  -> same G, paths, and bytes -> same-plan idempotency

same P and (different R or J or settings provenance hash)
  -> different G -> different raw and structured paths
```

This relies on SHA-256 collision resistance. If an implementation ever observes
the same G for non-equal typed graph-identity bytes, it must fail closed and
must not write, adopt, or register either graph.

Same G with differing bytes is hash collision, implementation corruption, or a
graph inconsistency: fail closed and never overwrite. This is the physical-path
realization of the already accepted parent complete-graph idempotency rule; it
does not weaken parent H2 semantics.

The runtime repaired reader starts from the existing repository-selected
structured Artifact record, selects the repaired 33,554,432-byte bound before
reading it, validates its repaired producer and the exact
`scoring/<P>/repair/<G>/structured` grammar, then uses that claimed fixed-hex G
only to load `scoring/<P>/repair/<G>/raw` from the repository under the same
repaired bound. It parses the sealed raw envelope, obtains P/R/J/settings/version
commitments and the two truthful ProviderCalls, rebuilds the typed identity,
recomputes G, and requires both Artifact DB keys and paths to equal the
recomputed values before accepting either file. It must not scan `scoring/<P>`
or choose a filesystem "latest" directory. Legacy producer dispatch remains
P-only and retains its 1,000,000-byte bound; producer version plus the distinct
path family prevents a REPAIR artifact from being interpreted as legacy.

`reporting.py` is also a current production structured-score reader. It must
gain a narrow repaired-producer branch so a repaired successful score remains
usable by weekly reporting: select the repaired bound, validate the P/G
structured-path grammar, read only the matching G raw path (never scan), parse
the repaired envelope, recompute G, and require equality before using the
existing sealed `ScoreResult`. Full ProviderCall graph validation remains the
runtime scoring-provenance reader's trust responsibility; the reporting branch
must not claim to replace it.

Consequently, an R1 orphan later retried as the exact R1 graph has the same G1
and remains adoptable. A legitimate R2/J2/settings2 graph has G2 distinct from
G1 and proceeds at its own paths without deleting, overwriting, or being blocked
by the R1 orphan.

### 12.2 Complete `RepairProviderEvidence` v2

For clarity, the accepted parent v1 has exactly these 14 non-null fields, under
H2 JCS strict typed/canonical reserialize equality:

| v1 field | Exact type / rule / bound |
|---|---|
| `schema_version` | literal `"task016c-repair-provider-evidence-v1"` |
| `operation` | literal `"local-scoring-repair-v1"` |
| `normalized_input` | exact non-null `RepairNormalizedInput`; its canonical bytes are subject to the H2-C repair-provider component limit |
| `normalized_input_hash` | non-null lowercase 64-character SHA-256 of canonical RNI |
| `request_hash` | non-null lowercase 64-character six-dimensional provider request hash |
| `provider` | non-empty string, bounded by the repair-provider canonical subtree admission cap |
| `model` | non-empty string, bounded by that same cap |
| `model_digest` | non-null `sha256:` plus 64 lowercase hex characters |
| `prompt_version` | non-empty string, bounded by that same cap |
| `operation_schema_version` | non-empty string, bounded by that same cap |
| `output_language` | non-null enum `"zh-CN" | "en"` |
| `temperature` | non-null finite IEEE-754 binary64 JSON number |
| `max_output_tokens` | non-null positive JSON integer |
| `max_description_chars` | non-null non-negative JSON integer; zero is explicit, never absent/default/null |

`RepairProviderEvidence` v2 is an exact, `extra="forbid"`, non-null schema
with these **16** fields:

| v2 field | Exact type / rule / bound |
|---|---|
| `schema_version` | literal `"task016c-repair-provider-evidence-v2"` |
| `operation` | literal `"local-scoring-repair-v1"` |
| `normalized_input` | exact `RepairNormalizedInput`, non-null; its canonical bytes `<= 393216` and all enclosing material remains within the 8,388,608-byte repair-provider subtree cap |
| `normalized_input_hash` | lowercase 64-character SHA-256, non-null, exact RNI canonical hash |
| `request_hash` | lowercase 64-character SHA-256, non-null, exact REPAIR provider request hash R |
| `provider` | non-empty string, non-null, within repair-provider subtree cap |
| `model` | non-empty string, non-null, within repair-provider subtree cap |
| `model_digest` | non-null `sha256:` plus 64 lowercase hex characters |
| `prompt_version` | non-empty string, non-null, within repair-provider subtree cap |
| `operation_schema_version` | non-empty string, non-null, within repair-provider subtree cap |
| `output_language` | non-null enum `"zh-CN" | "en"` |
| `temperature` | non-null finite IEEE-754 binary64 JSON number |
| `max_output_tokens` | non-null positive JSON integer |
| `max_description_chars` | non-null non-negative JSON integer, zero explicit |
| `settings_provenance` | non-null exact `H2CSettingsProvenance`, `extra="forbid"`, canonical bytes `<= 8192` |
| `settings_provenance_sha256` | non-null lowercase 64-character SHA-256 |

Every v2 field is serialized as part of its containing typed envelope through
H2 JCS strict UTF-8; no alternate serializer, absent/null equivalence, or
unknown field is permitted. Its inherited RNI/provider/model/digest/prompt/
schema/language/temperature/output/description cross-bindings remain exactly
the accepted v1 rules. It additionally requires:

```text
SHA256(H2-JCS(settings_provenance)) == settings_provenance_sha256
```

The sole durable settings source is
`repair_provider_evidence.settings_provenance` and
`repair_provider_evidence.settings_provenance_sha256`; no duplicate settings
copy is authoritative. G binds this exact v2 hash.

v1 remains the unmodified H2-B evidence contract. Round 3 amends only the
H2-C persisted repaired-success representation: a live H2-C repaired producer
requires v2; a repaired v1 or unknown evidence version rejects fail closed.
Pre-H2-C/H2-B material continues to use and interpret v1 exactly as frozen.

### 12.3 Settings admission ceiling disposition

`max_transcript_chars <= 131072` is an H2-C persistence admission rule, not a
general configuration error. The inclusive boundary is exact: 131071 and
131072 are allowed; 131073 and above are rejected before mint, envelope
construction, network, filesystem, or persistence.

The mapping is exactly one owner-authoritative:

```text
PipelineRepository.fail_job(
  job_id, owner=runtime_owner,
  error_code=ErrorCode.TRUST_INTEGRITY_INVALID,
  error_message="H2C_REPLAY_INVALID:SETTINGS_BOUND_EXCEEDED",
  retry_at=None)
-> FAILED_FINAL -> StageDisposition.TERMINAL
```

`SETTINGS_BOUND_EXCEEDED` is added to the closed diagnostic set and is
diagnostic only; retry remains code-only. The same reason covers every other
explicit H2-C settings admission limit that current general configuration can
otherwise exceed: `max_output_tokens <= 2147483647` and canonical settings
provenance bytes `<= 8192`. Existing configuration bounds already cover
temperature, description length, output language, and digest syntax. Any
non-settings evidence-component/root-size excess remains
`H2C_REPLAY_INVALID:ENVELOPE_OVERSIZE`.

### 12.4 Narrow stale-lease propagation

The current pipeline catches `ScoringDispatchDenied` through generic
`except Exception` and calls `_fail`; that is not safe for the specific H2-C
pre-persistence loss of ownership. It cannot catch all
`ScoringDispatchDenied`: current uses also mean provider construction failed
before contact, identity collision, post-admission payload/Judge drift, role
misuse, duplicate role, ProviderCall conflict, and existing H1 lease/admission
denial. Those retain their established generic pipeline behavior.

Authorize one narrow internal exception in `scoring.py`:
`H2CStaleScoringLease`. It is raised **only** when the repair PREWRITE
repository-owned check proves this runtime is no longer the active owner of the
current RUNNING SCORING job. It carries no caller capability and is not used for
any evidence/replay mismatch or any existing `ScoringDispatchDenied` source.

`pipeline.py` is authorized to import and catch exactly
`H2CStaleScoringLease` before generic `Exception`. The handler performs one
side-effect-free `repository.get_job(job.job_id)` read and has this exact path:

| Current durable job state | Pipeline action |
|---|---|
| missing | return from `_execute`; no disposition, no mutation |
| `RUNNING` with a different owner or expired/non-active lease | return from `_execute`; no disposition, no mutation |
| `FAILED_FINAL` | return from `_execute`; no duplicate terminal |
| `SUCCEEDED` | return from `_execute`; no mutation |
| any other state, or RUNNING still actively owned by this worker | raise `PipelineInterrupted`; no generic `_fail` |

No `fail_job`, generic `_fail`, retry, REPAIR/Judge dispatch, or persistence is
performed by the stale runtime. The owner-authoritative H0/H1 recovery process
remains responsible for a still-running expired/abandoned job; a state already
terminalized is merely observed. This is a safe no-op, not a new
`StageDisposition`; the pipeline `_execute` returns before disposition handling.

### 12.5 Repair orphan reconciliation and required tests

For a single exact G, Round 2 raw-only exact, structured-only exact, paired
exact, mismatching, and corrupt orphan rules remain unchanged. A verified exact
orphan is material only and can never establish success without the current
lease and SQLite transaction. An old R1 orphan may remain indefinitely: it is
not registered, cannot be read as a registered artifact, cannot establish
success, and G separation means it cannot block R2. Cleanup is not required for
correctness and remains out of scope.

Required additions to the future test matrix are:

1. legacy PRIMARY P-only paths unchanged;
2. same P/R/J/settings gives the same G/path;
3. same P with changed R, changed J, or changed settings hash gives a distinct G/path;
4. exact R1 orphan adopts for R1; R1 orphan does not block R2; mismatching G1 file fails closed; no traversal;
5. exact v2 accepts; missing/altered inherited field, missing/mutated settings,
   settings-hash mismatch, null, extra, repaired v1 downgrade, and unknown
   version reject;
6. 131071/131072 accept; 131073 yields exact trust code/detail with zero
   network/files/persistence; altered diagnostic detail does not affect retry;
7. H2-C stale prewrite creates zero files and invokes neither `fail_job` nor
   generic `_fail`; changed-owner RUNNING, `FAILED_FINAL`, and `SUCCEEDED` all
   safely return; valid owner proceeds; all existing non-H2-C
   `ScoringDispatchDenied` tests remain correct; and
8. DB permits same-P R1/R2 G-based artifact records; reader recomputes G,
   rejects wrong DB key/path/G, and never scans directories.

### 12.6 Round 3 implementation scope and discretion closure

The authorized future production scope is unchanged except for the required
narrow pipeline propagation handling:

```text
src/youtube_intel/runtime.py
src/youtube_intel/h2_evidence.py
src/youtube_intel/quality.py
src/youtube_intel/scoring.py
src/youtube_intel/domain.py
src/youtube_intel/providers/subtitles.py
src/youtube_intel/transcripts.py
src/youtube_intel/pipeline.py
src/youtube_intel/reporting.py
```

`pipeline.py` changes are limited to the exact
`H2CStaleScoringLease` pre-generic handler and read-only state table above.
`reporting.py` changes are limited to the repaired producer P/G path/envelope
validation above; they add no cache, repository writer, or alternate trust path.
`state.py` and migrations remain frozen. The implementation executor has no
remaining choice over graph fields/key/path, v2 schema/version handling,
settings-bound reason, stale-owner propagation, reader validation, or orphan
availability. Any deviation is `DECISION NEEDED`.

## 13. Round 4 amendment — sealed artifact commitments, durable selection, and directory safety

This amendment supersedes the conflicting H2-C portions of §12.1 and §12.6.
It does **not** alter a parent H2 contract or a legacy/PRIMARY producer. It
first freezes the otherwise-required repair graph and filesystem rules, then
records the decisive state-schema audit. That audit is a blocking result: the
existing schema has no durable authoritative-repaired-graph relation. H2-C
implementation remains unauthorized.

### 13.1 `RepairPersistenceGraphIdentity` v2 and sealed artifact commitments

`task016c-repair-persistence-graph-v1` remains the Round 3 historical design
record; no H2-C producer may emit it. A live H2-C REPAIR producer must use this
exact non-null, `extra="forbid"` typed value:

```text
RepairPersistenceGraphIdentityV2

schema_version: Literal["task016c-repair-persistence-graph-v2"]
primary_request_hash: Sha256LowerHex                         # P
repair_request_hash: Sha256LowerHex                          # R
repair_judge_request_hash: Sha256LowerHex                    # J / Judge H2
settings_provenance_sha256: Sha256LowerHex
repair_envelope_sha256: Sha256LowerHex                       # E
structured_result_sha256: Sha256LowerHex                     # S
raw_producer_version: Literal["scoring-raw-content-quality-repair-v1"]
structured_producer_version: Literal["scoring-structured-content-quality-repair-v1"]
envelope_schema: Literal["trusted-scoring-repair-envelope-v1"]
repair_provider_evidence_schema: Literal["task016c-repair-provider-evidence-v2"]
quality_policy_version: Literal["content-quality-policy-v1"]
quality_prompt_version: Literal["content-quality-prompt-v1"]
quality_schema_version: Literal["content-quality-result-v1"]
```

`Sha256LowerHex` means exactly 64 lowercase ASCII hexadecimal characters. No
field is nullable and no field may be defaulted, inferred, or supplied by an
artifact path. The value uses H2 Canonical JSON v1 / RFC 8785 JCS strict UTF-8
bytes; its SHA-256 lowercase hexadecimal digest is `G`:

```text
envelope_bytes = H2-JCS(complete RepairCompositeEnvelope), strict UTF-8
E = SHA256(envelope_bytes)

structured_bytes = exact sealed RepairTrustedScoringFinalizer output
S = SHA256(structured_bytes)

identity = RepairPersistenceGraphIdentityV2(..., E, S, ...)
G = SHA256(H2-JCS(identity), strict UTF-8)
```

The sequence is mandatory: (1) finish the local 23-step replay and finalizer,
(2) obtain the exact sealed structured bytes and S, (3) reconstruct all repair
evidence, (4) build the complete six-field `RepairCompositeEnvelope`, (5)
canonicalize it and obtain E, (6) construct the v2 identity, (7) obtain G, and
only then (8) derive Artifact keys and filesystem paths. The envelope contains
neither G nor an artifact key/path nor identity bytes/digest; the sealed
structured result also contains none of them. Hence neither E nor S requires G
and this construction has no circular dependency.

The repaired raw Artifact content hash is exactly E; its bytes are exactly
`envelope_bytes`. The repaired structured Artifact content hash is exactly S;
its bytes are exactly `structured_bytes`. Therefore every serialized field of
the persisted envelope, including exact REPAIR outer raw and exact REPAIR Judge
raw, is committed by E, and both persisted Artifact byte streams are committed
by G. With the SHA-256 collision-resistance assumption:

```text
different envelope bytes -> different E -> different G
different structured bytes -> different S -> different G
same E and S -> the only permitted same-G byte pair
```

Thus same P/R/J/settings/policy may still have different captured valid raw
bytes, but the different envelope bytes produce distinct G-specific paths.
Same G with unequal envelope or structured bytes is corruption, an
implementation inconsistency, forged metadata, or a SHA-256 collision: fail
closed; never overwrite, adopt, register, or select it.

### 13.2 Exact repaired keys, Artifact mapping, and registration invariant

P and G are fixed lower-hex SHA-256 components only. A v2 REPAIR graph has
exactly these keys and paths:

```text
raw artifact_key:           scoring/<P>/repair/<G>/raw
raw relative_path:          scoring/<P>/repair/<G>/raw.json
structured artifact_key:    scoring/<P>/repair/<G>/structured
structured relative_path:   scoring/<P>/repair/<G>/structured.json
```

The legacy PRIMARY family is unchanged exactly:
`scoring/<P>/raw(.json)` and `scoring/<P>/structured(.json)`. No REPAIR
producer may write a P-only final path. Phase G's existing Artifact ID rule
continues to apply to the G-based keys: raw ID is
`scoring-raw-` + `SHA256(raw_artifact_key + E)` and structured ID is
`scoring-structured-` + `SHA256(structured_artifact_key + S)`.

ProviderCall identity is independent of G: the truthful REPAIR call has
request hash R and operation `local-scoring-repair-v1`; the truthful REPAIR
Judge call has request hash J and operation `local-content-quality-v1`. Both
bind the one G-specific raw Artifact ID. G is never substituted for R or J.

For one successful H2-C **scoring job**, the intended complete registration is
exactly one G-specific `SCORING_RAW` Artifact, one G-specific
`SCORING_STRUCTURED` Artifact, one R ProviderCall, one J ProviderCall, and one
`TRANSCRIPT_READY -> SCORED`/job-success transaction. A same-G, complete,
already-registered graph follows Phase G's existing no-write idempotent result
path. A different G after that same job is not a second success: repair
PREWRITE must observe that the job is no longer this worker's active RUNNING
SCORING lease and take the already-frozen `H2CStaleScoringLease` no-mutation
path before filesystem work. Unregistered G directories are merely material
and may coexist; they are never authoritative.

The Artifact schema audit is positive only for physical coexistence:
`artifacts.artifact_key` is the sole relevant unique key, so same P may hold
multiple G-specific raw/structured records with distinct keys. It does not
provide an authoritative selection relation; §13.4 records that separate
blocking conclusion. No migration is authorized by this positive coexistence
fact.

### 13.3 Repair-only nested-directory and no-clobber contract

When and only when the authoritative-selection blocker in §13.4 is resolved by
separate authorization, a REPAIR write must use this repair-only directory
algorithm before the existing Phase G temporary-file/no-clobber protocol. It
does not weaken Phase F's existing P-only directory behavior.

Starting from the configured DATA artifact root, open and retain an anchored
directory descriptor using `os.open` with
`O_RDONLY | O_DIRECTORY | O_NOFOLLOW`. On the supported V1 macOS/Linux
platforms, absence of any required no-follow/dir-fd primitive is a
`LOCAL_RESOURCE` fail-closed condition; there is no insecure pathname
fallback. Every pre-existing component is first `lstat`-verified and then
opened through its parent descriptor: it must be a directory, must not be a
symlink, and must not be a FIFO, socket, device, or any other special file.

The components are processed one level at a time in this exact order:

```text
DATA root -> scoring -> <P> -> repair -> <G>
```

For a missing component, call `os.mkdir(component, 0o700, dir_fd=parent_fd)`.
On `FileExistsError`, re-`lstat` and re-open the resulting component under the
same parent descriptor; it must meet the exact safe-directory rule. After each
successful new directory creation, (a) `fsync(parent_fd)`, (b) open the child
with the no-follow directory flags, and (c) `fsync(child_fd)` before creating a
descendant. Existing safe ancestors are not recreated but are still checked.
P and G are validated fixed lower-hex values before use, and `repair` and
`scoring` are literals; no evidence/provider/model string is a path component.

Within the verified G descriptor, final names are literal `raw.json` and
`structured.json`. Create each corresponding literal temporary name with
`O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW`, mode `0o600`, relative to that
descriptor; write, `fsync`, and exact hash/length-verify the temporary file.
Use the existing atomic no-clobber link promotion into the G descriptor. After
each successful promotion `fsync(G_fd)`, remove the temporary name, `fsync(G_fd)`
again, reopen the final through `O_NOFOLLOW`, require a regular file, and
recheck exact length and hash. An existing final is never overwritten: it must
be a regular non-symlink whose exact expected bytes/hash/length are verified
for the already-frozen identical-orphan adoption rule, or the write fails
closed. SQLite ownership/transaction verification remains the only authority
that registers a materialized file.

Same-G writers may race at `mkdir` and final promotion but must converge only
on the same verified descriptors and exact bytes; SQLite ownership/transaction
selects whether a success is authoritative. Different-G writers may share the
safe `<P>/repair` ancestor but receive distinct G descriptors and never block
one another. A symlink or special-file fixture at DATA-root descendants
`scoring`, P, `repair`, G, a temporary name, or a final name fails closed with
no traversal outside DATA. Directory creation and descriptor handling are
repair-only; the final file promotion/fsync/no-clobber semantics remain the
Phase G contract.

For an exact graph, raw-only, structured-only, paired, and corrupt orphan cases
retain the Round 2 outcome. Exact orphan adoption requires a fresh current
owner/lease PREWRITE check and exact E/S bytes. R1-orphan followed by an exact
R1/E1/S1 graph adopts at G1; an R2/J2/settings2/raw-variant graph has G2 and
uses different paths, so it neither removes, overwrites, nor is blocked by G1.
Orphans remain non-authoritative and no cleanup is required for correctness.

### 13.4 Authoritative repaired-graph selection audit — BLOCKER

**H2-C AUTHORITATIVE GRAPH SELECTION SCHEMA BLOCKER**

The blocker-resolution decision is recorded separately in
`docs/TASK-016C-PHASE-H2C-AUTHORITATIVE-G-SCHEMA-AUTHORIZATION.md`. It selects
a repair-only, job-owned exact structured-Artifact-key relation, but grants no
implementation authority until independent review accepts that document.

The frozen V1 schema can persist G-specific Artifact rows but cannot durably
state which one is the authoritative repaired graph for a video after the
SCORING job has completed. The exact audit result is:

| Required relation | Actual V1 durable state | Why it is insufficient |
|---|---|---|
| video/job -> authoritative structured Artifact or G | `artifacts.job_id` points from each Artifact to a Job | Neither `videos` nor `jobs` points back to one scoring Artifact/G; more than one historical scoring Artifact/job may exist for a video. |
| runtime repaired-score starting point | `RuntimeOperations._load_scoring(video_id)` calls `latest_artifact(video_id, SCORING_STRUCTURED)` | `latest_artifact` orders by `created_at DESC, artifact_id DESC`; this is explicitly forbidden for repaired producers. |
| weekly-report starting point | `SQLiteStateRepository.list_weekly_candidates` calls `_latest_weekly_artifact` | That query also orders by artifact creation time; `WeeklyReportService` receives only the selected structured Artifact. |
| exact matching raw lookup after G is known | `get_artifact_by_key(artifact_key)` | This existing exact lookup is sufficient only *after* an authoritative P/G has been selected. It cannot select G. |

`videos.score`, `videos.should_summarize`, pipeline status, timestamps, and a
Job's `scope_key` are not an Artifact/G reference. In particular,
`videos.updated_at` is later changed by downstream stages and cannot be
repurposed as an identity. An added read-only query over the present tables
cannot create the missing relation: it would either return several valid rows
or select one by ordering/heuristic. Both are prohibited.

Consequently, no repaired runtime reader or reporting reader is authorized to
start from “latest”, `MAX`, creation time, artifact ID, lexicographic G, a
directory scan, or a first matching P. No `reporting.py` raw-read branch, no
shared repaired-artifact verifier, and no `state.py` selection API is
authorized in this task. The existing `get_artifact_by_key` remains unchanged;
there is no `state.py` thaw merely to disguise the absent selector.

The minimum later decision must introduce a durable, transactionally maintained
authoritative relation (for example an explicit successful-scoring Artifact/G
reference owned by the video/job state) and define its exact update/read
semantics. That is a schema/state-contract change, remains frozen here, and
requires separate review and authorization. It must then specify a reader that
starts from that exact registered structured Artifact, derives
`scoring/<P>/repair/<G>/raw`, uses `get_artifact_by_key` for the matching raw,
requires raw hash E and structured hash S, rebuilds v2 identity/G, and looks up
only ProviderCalls R and J by exact request hash. It must fail closed on a
missing, duplicate, conflicting, unknown-producer, wrong-key/path, wrong E/S,
or wrong-G graph. No directory scan or latest-order fallback may be introduced.

Because this selection relation is absent, the Round 3 claim that a repaired
reader can begin from an “existing repository-selected structured Artifact” is
not an implementation authorization. It is superseded by this blocker. The
legacy PRIMARY reader and reporting path remain unchanged; no repair producer
may be enabled until the blocker is resolved.

### 13.5 Required post-blocker verification matrix and discretion closure

After separate authoritative-selection authorization, future RED/acceptance
tests must cover all of the following before H2-C can be implemented:

1. same P/R/J/settings but differing valid REPAIR outer raw, differing valid
   Judge raw, or any other envelope field changes E and G; differing structured
   bytes change S and G; identical envelope/structured bytes retain E/S/G; the
   builder has no circular dependency;
2. legacy PRIMARY paths remain unchanged; same complete graph has the same
   paths; changed R, J, settings, E, or S changes G/path; same-G unequal bytes
   reject; R1 orphan does not block G2 and exact G1 orphan adopts;
3. exact same registered G returns the existing Phase G idempotent result with
   no writes; a distinct G for an already-successful job performs no second
   registration or success transition; unregistered G material is never
   selected;
4. the reader starts from the new DB-authoritative structured-Artifact/G
   relation, never latest ordering; it derives raw key from P/G, fetches raw by
   exact key, validates E/S and recomputed G, and rejects missing/wrong/duplicate
   raw or R/J ProviderCalls, wrong producer, path, hash, or graph;
5. reporting receives the same exact repository read accessor as the runtime
   and validates the matching raw graph; it performs neither hidden filesystem
   discovery nor cache/retry/resume/cross-job selection; legacy reporting stays
   unchanged;
6. P/repair/G creation is one-level/dir-fd/no-follow safe; safe existing
   directories work; a symlink or special file at every component or final file
   rejects; parent/child directory `fsync` order is observed; same-G and
   different-G races are safe; and
7. no migration is attempted in this task. The authoritative relation is
   separately reviewed before any state/schema or implementation work begins.

No implementation executor may choose a selector, a reporting accessor, a
shared verifier input shape, or a state API while this blocker stands. The
security-discretion audit is therefore closed by **stopping**, not by assigning
that discretion to the implementation executor.

### 13.6 Lineage and reporting supersession

Round 1 of `docs/TASK-016C-PHASE-H2C-SCORING-LINEAGE-AUTHORIZATION.md` supersedes only
the repaired downstream-selection and reporting contract: the
repository-selected-reader premise in §12.1, the repaired reporting raw-graph
branch in §12.1, and §13.5 items 4–5. The final design starts at the durable
Video-to-scoring-Job relation, uses the Job-to-structured-Artifact relation,
and returns a pre-verified `VerifiedScoringRead` to reporting. Round 1 replaces
its earlier repair discriminator, rerun/CAS, cross-job-convergence, and
graph-conflict wording. Legacy PRIMARY behavior and all frozen H2-C graph/replay,
filesystem, P/R/J/E/S/G, and stale-lease rules remain unchanged except where
that document explicitly resolves their selector dependency.

### 13.7 Round 1 lineage amendment

Round 1 replaces the rejected Round 0 rerun/predecessor, cross-job-convergence,
and non-unique-pointer clauses. The final authority chain is Video → exact
initial successful SCORING Job → exact structured Artifact key. It permits only
`Video.authoritative_scoring_job_id` `NULL -> current Job`; it does not
authorize a SCORING rerun, J1→J2 replacement, downstream invalidation, or
cross-job same-G convergence. H1 global ProviderCall admission and existing
Artifact `job_id` ownership remain frozen and make such convergence unavailable.

Every new post-migration SCORING Job is marked
`task016c-scoring-lineage-v1` at creation; only a NULL-marked pre-lineage Job
(including a recovered pre-v2 PRIMARY success) may use the legacy branch. New
PRIMARY and REPAIR_H2C successes atomically
record provenance, exact structured key, and the Video pointer. The one future
migration is `002_add_scoring_lineage.sql`, advances schema version to 2, and
uses a partial-unique Job artifact-pointer index. Shared Phase-G completion
gains only this additive lineage bookkeeping for new PRIMARY Jobs; frozen
PRIMARY request, bytes, ProviderCall, and Artifact semantics remain unchanged.

The final reporting interface remains pre-verified `VerifiedScoringRead`; no
reporting repository/raw-graph selector is authorized. Round 1 also freezes
CAS read-back classification and `TRUST_INTEGRITY_INVALID` terminal details for
active-owned lineage conflicts. All other H2-C graph/replay/filesystem and
stale-lease contracts remain unchanged.

### 13.8 Round 2 cutover and transaction-local read-back amendment

Round 2 clarifies that a NULL `scoring_lineage_version` is the immutable
pre-lineage generation for every migrated Job, including nonterminal SCORING
Jobs. Same-Job H0/H1 recovery remains available under the old PRIMARY contract,
but no pre-lineage Job may enter H2-C or be upgraded to v1. A pre-lineage H2-B
PASS that would require H2-C retains the frozen
`CAPABILITY_UNAVAILABLE` / `H2B_PASS_AWAITING_H2C` / `FAILED_FINAL` terminal
route. Newly created post-migration SCORING Jobs alone receive v1.

All failed Job/Video lineage CAS diagnosis must use private state readers on
the same `BEGIN IMMEDIATE` connection, validate the frozen identity/lease/
pointer fields before classification, classify before rollback, then re-prove
the lease before any separate terminal `fail_job`. Public `get_job()` and
`get_video()` are not permitted as these diagnostic reads. Round 2's exact
orders and details in the lineage authorization supersede Round 1's generic
separate-read wording.
