# TASK-016-LOCAL-DEEP-ANALYSIS — M1 Pro Feasibility Authorization, Amendment R3

Status: **EXACT RAW-PROFILE BENCHMARK MAY PROCEED — NOT PROVIDER IMPLEMENTATION AUTHORIZATION**

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

## Final statement

**LOCAL DEEP ANALYSIS M1 PRO FEASIBILITY GATE MAY PROCEED FOR THE FROZEN 0.32.1 RAW PROFILE ONLY**

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED**
