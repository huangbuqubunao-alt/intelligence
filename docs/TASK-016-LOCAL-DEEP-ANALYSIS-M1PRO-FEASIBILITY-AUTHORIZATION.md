# TASK-016-LOCAL-DEEP-ANALYSIS — M1 Pro Feasibility Authorization, Amendment R3

Status: **MODEL SELECTION BLOCKER — qwen3:8b RAW / NO-FORMAT PROFILE NOT IMPLEMENTATION-READY**

This authorizes only the controlled local M1 Pro benchmark/smoke under the exact
profile recorded below. It authorizes no production code, test/migration change,
model download, model fallback, remote service, telemetry, persistence/cache
work, or TASK-016D/E/F.

## 1. Exact candidate and environment record

The only candidate is qwen3:8b with exact tag qwen3:8b and full digest sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41. The runner manually proves the unique exact local tag/digest before testing; it must not pull, alter, or substitute a model.

The benchmark report must record these observed environment facts:

| Field | Required report value |
|---|---|
| Mac model identifier | exact system model identifier when available; otherwise explicit unavailable |
| chip | Apple M1 Pro; any other chip is FAIL |
| total unified memory | exact detected bytes/GiB and detection source |
| macOS | exact version and build |
| Ollama | exact accepted canonical SemVer source string |
| model | exact tag and full digest |
| free/available memory before run | exact value and collection method when mechanically available; otherwise explicit unavailable |
| runtime launch mode | exact command/service mode, process count, and confirmation of one local generation worker |
| endpoint | exactly http://127.0.0.1:11434 |

No remote service, parallel generation, or secret-bearing corpus is permitted.

## 2. Exact requests and corpus

Use the context-proof authorization’s hash-verified `tokenizers==0.22.2`, exact
`TokenizerIdentityV1`
`598d4c936d655112f7323d71d5653ba4cfa490b82c403d76f789cc22eee2060f`,
exact canonical SCHEMA_BYTES, and exact `knowledge-prompt-v3-raw`
application-rendering/substitution rules. The frozen runtime profile is Ollama
**0.32.1 only**, model tag `qwen3:8b`, digest
`sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`,
`raw=true`, omitted `format`, `stream=false`, `think=false`, `temperature=0`,
`seed=0`, `num_ctx=16384`, and `num_predict=2048`. It must use the exact
pre-dispatch complete-candidate token count, require `input_tokens <= 14336`,
perform full-candidate recount during prefix selection, and perform a final
pre-dispatch recount of the exact application-rendered prompt. No runtime
version range is approved.

The local parity gate established exact local/provider token-count equality for
nine structurally different below-context raw fixtures and found a 175-versus-
191 raw/non-raw control difference. Its mechanically available local
tokenizer/model pairing classification is **strongly evidenced but not
cryptographically proven**. Run short, medium, and a complete-token-predicate-
passing maximum request; each must record its prompt/token-proof hashes and
measured request/prompt/schema bytes. Corpus cases include dense ASCII, Han,
and multibyte Unicode evidence and contain no personal secrets.

## 3. Required measurements

For every run record wall-clock duration using a monotonic clock immediately before the single generation transport call and immediately after completed response read; record duration in milliseconds. Record HTTP status, bounded raw envelope bytes, done, prompt_eval_count when the documented response includes it, eval_count, strict envelope parse, strict generated JSON parse, KnowledgeContent schema validation, point grounding against supplied registry, KG2 label validation, and coverage fields.

Record model-load success. Record peak/observed memory and collection method whenever approved tooling can observe it; absence of a reliable peak metric must be reported as unavailable, not invented.

## 4. Objective pass/fail

A benchmark case PASS requires all of:

1. the exact preflight version/tags/digest proof succeeds;
2. model load succeeds, no OOM, no model/runtime process termination, and no kernel/system memory-failure symptom attributable to the run is observed;
3. the complete maximum accepted request completes within 300 seconds by the monotonic-clock method;
4. HTTP success, valid Ollama envelope, strict generated JSON, exact KnowledgeContent schema, deterministic point grounding, and KG2 graph-label validation all pass; and
5. think=false, stream=false, seed=0, raw=true, omitted format, and the application-owned prompt occur together without extra content or transport-contract violation.

The PRD sets no lower latency SLO; no arbitrary threshold is added. Any failure, missing required evidence, wrong model identity, or unsupported environment is a **MODEL SELECTION BLOCKER**. There is no fallback model.

## 5. No-truncation rule and version approval

The benchmark must not claim formal no-truncation merely because a response succeeds or prompt_eval_count is present. prompt_eval_count records provider-observed evaluated prompt tokens but, without an approved exact expected-token counter, cannot prove no input was discarded. The only permissible statement without that proof is: the maximum accepted T1 byte-envelope request was accepted and produced validated output under the recorded exact runtime/model.

Formal no-truncation/context safety remains an implementation-authorization blocker until a later authorization supplies an exact qwen3-compatible tokenizer/accounting proof or an authoritative provider observable that compares expected full-prompt tokens with evaluated tokens.

A passing Ollama version authorizes only that exact canonical version string after explicit follow-up approval. One passing version never authorizes a range; a broader range needs separate compatibility evidence. qwen3:8b becomes a frozen implementation model only after exact tag/digest, at least one explicitly approved exact Ollama version, required M1 Pro environment, all benchmark PASS conditions, and the separate formal no-truncation proof are present. Otherwise it remains a MODEL SELECTION BLOCKER.

## 6. Controlled M1 Pro feasibility execution — 2026-08-27

The controlled benchmark contacted only `http://127.0.0.1:11434`; it did not
pull/download a model, contact a remote endpoint, or modify production code,
tests, migrations, dependencies, or model artifacts. Environment capture:

| Field | Observed evidence |
| --- | --- |
| Mac | `MacBookPro18,3` / `MKGQ3CH/A`; Apple M1 Pro; 10 cores (8 performance, 2 efficiency) |
| Unified memory | 16 GB / `17179869184` bytes (`system_profiler` / `sysctl hw.memsize`) |
| macOS | 26.3.1, build `25D2128` |
| Python evidence runtime | Python 3.12.13, isolated `tokenizers==0.22.2` |
| Ollama | exact `0.32.1` |
| Model | exact `qwen3:8b`, digest `sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`; `qwen3` / GGUF / `Q4_K_M` / 8.2B; model metadata context 40,960 |
| TokenizerIdentityV1 | `598d4c936d655112f7323d71d5653ba4cfa490b82c403d76f789cc22eee2060f` |
| Runtime mode | local Ollama service plus one `llama-server` generation worker; battery power observed, 58% and discharging |
| Memory before first harness attempt | `vm_stat`: 16,384-byte pages; free 293,949 pages = 4,816,060,416 bytes; inactive + speculative = 9,138,274,304 bytes. This is an observation, not a peak-RSS guarantee. |

Preflight re-proved the exact loopback endpoint, Ollama version, unique exact
tag/digest, family/quantization, frozen tokenizer artifact hash, and the raw
body shape (`model`, `prompt`, `raw`, `stream`, `think`, `options` only; no
`format`). It loaded the pinned tokenizer with automatic special-token insertion
disabled and re-rendered/re-hashed/re-tokenized immediately before dispatch.

The deadline-controlled required SHORT trial was a valid application-owned
`knowledge-prompt-v3-raw` request with a one-item Evidence Registry:

| Metric | Observed value |
| --- | --- |
| Input tokens / Ollama `prompt_eval_count` | `1303 / 1303` (exact parity) |
| Prompt SHA-256 | `d994897d8e3c33f591d196de656409aabbfc081463fa888eb28c5b0552607e30` |
| Token-ID SHA-256 | `203bd2dd8a95e7f24f8f0714cdba4c93b2dd81be08edc2c2b1510d742e266792` |
| Prompt / request bytes | `4205 / 4849` |
| Monotonic wall-clock | `99128.194875` ms |
| Envelope | HTTP 200; `done=true`; `done_reason=length`; `eval_count=2048`; no `<think>` marker |
| JSON / schema / grounding | **FAIL**: response began with JSON but then contained Markdown fences and repeated Chinese prose; strict whole-response JSON parse therefore failed, so closed-schema and grounding validation could not pass. |

This is one structurally invalid required run. It is sufficient to violate the
mandatory 100% structural-validity threshold. The remaining SHORT repeat and
all MEDIUM/MAX generations were deliberately not dispatched: repeating a
profile that already fails a mandatory non-recoverable gate cannot establish
implementation eligibility, and this authorization permits no fallback or
profile change.

For diagnostic preparation only (not dispatched benchmark evidence), the
deterministic application renderer produced MEDIUM `3829` tokens and a
32-selected-of-64 MAX partial prefix of `8905` tokens (`5431` below the
`14336` ceiling), with stable final recount hashes. The latter preserved
`coverage_complete=false`, but its 32,380-byte prompt / 33,520-byte serialized
body exceeded the still-frozen 8,192 / 32,768 independent resource bounds and
was not an authorized dispatch. No near-ceiling context-parity or
no-silent-context-loss claim is made.

No OOM, Ollama crash, model-worker crash, or system termination was observed.
The live model worker was observed around 6.8 GiB RSS and memory compression /
swap counters increased under load; this is a stability/performance observation
only, not a precise peak-memory measurement. Transport and token-count parity
passed for the sole dispatched trial, but structured-output reliability,
strict JSON, schema, and grounding did not.

**MODEL SELECTION BLOCKER: qwen3:8b at the exact digest and Ollama 0.32.1 raw /
no-format profile is not implementation-ready.**

## Final statement

**LOCAL DEEP ANALYSIS M1 PRO FEASIBILITY GATE FAILED**

**MODEL SELECTION BLOCKER**

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED**
