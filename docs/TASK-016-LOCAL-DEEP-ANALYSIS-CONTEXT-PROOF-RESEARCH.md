# TASK-016-LOCAL-DEEP-ANALYSIS — Context Accounting / No-Truncation Proof Research

Status: **RESEARCH RECORD ONLY — NO NORMATIVE AUTHORIZATION CHANGE — IMPLEMENTATION UNAUTHORIZED**

This record resolves neither the model/runtime feasibility gate nor provider
implementation authorization. It records the evidence reviewed on 2026-08-27
for the one remaining blocker in
`TASK-016-LOCAL-DEEP-ANALYSIS-AUTHORIZATION.md`: proving, before dispatch,
that the complete Qwen3 request fits `num_ctx=16384` without silent
truncation.

It authorizes no model download, Ollama contact, benchmark, dependency change,
provider implementation, persistence/cache work, or change to TASK-016B/C.

## 1. Evidence

### 1.1 Repository inventory

The only declared tokenization dependency is `tiktoken>=0.13.0,<0.14`
(locked at 0.13.0). `src/youtube_intel/analysis.py` uses it exclusively for the
existing cloud-analysis input budget. Its `_encoding()` loads the packaged,
hash-verified `o200k_base.tiktoken` resource and creates the
`o200k_base-local` encoding. The repository declares no `transformers`,
`tokenizers`, or `sentencepiece` dependency, and contains no Qwen tokenizer
artifact or approved Qwen-to-Ollama token-accounting implementation.

`o200k_base` is an OpenAI tokenizer family, not evidence of Qwen3 vocabulary,
merge, normalizer, special-token, or template equivalence. Therefore:

> **TIKTOKEN IS NOT AN AUTHORIZED QWEN3 CONTEXT PROOF.**

### 1.2 Qwen3 tokenizer evidence

The upstream Qwen3-8B model card directs applications to
`AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")` and to
`apply_chat_template(..., add_generation_prompt=True)`. It requires
Transformers 4.51.0 or later for Qwen3 support. Its published
`tokenizer_config.json` names `Qwen2Tokenizer`, sets `add_bos_token` false,
provides a Jinja chat template, and defines Qwen chat markers such as
`<|im_start|>` and `<|im_end|>` plus `<think>` / `</think>` markers. The
published tokenizer source identifies a byte-level BPE pipeline with
`vocab.json`, `merges.txt`, or `tokenizer.json` as its source artifacts.

Sources:

- [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B)
- [Qwen3-8B tokenizer configuration](https://huggingface.co/Qwen/Qwen3-8B/raw/main/tokenizer_config.json)
- [Hugging Face Qwen2 tokenizer source](https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen2/tokenization_qwen2.py)

This identifies the upstream tokenizer family. It does **not** establish that
the current Ollama `qwen3:8b` manifest, its full digest, and its runtime
prompt renderer use those exact artifacts and rules. A mutable upstream
`main` revision is not an immutable local proof artifact.

### 1.3 Ollama request transformation and observables

Ollama documents `/api/generate` as accepting a text `prompt`, a JSON-schema
`format`, and runtime options. It documents `raw: true` as disabling prompt
templating; the frozen Local Deep Analysis request does not use raw mode.
Consequently, the application-visible prompt is not the documented final
model-visible representation under the present contract. The Qwen template
evidence above shows why template, special-token, and `think=false` handling
are material to a count.

Ollama documents `prompt_eval_count` as the number of input tokens evaluated,
and `eval_count` as output tokens generated. The public generate response has
no documented expected-input-token field, no documented truncation boolean,
and no documented equality relation between a caller-supplied intended prompt
and `prompt_eval_count`. `done_reason` reports why generation stopped; it is
not documented as a no-truncation attestation. A successful response therefore
provides useful observation, not pre-dispatch proof that no intended content
was dropped.

The reviewed public API reference also defines `num_ctx` as a context length
in tokens and `num_predict` as a maximum number of generated tokens. It does
not state a formal allocation equation such as
`prompt_tokens + num_predict <= num_ctx`, nor a fixed `/api/generate`
over-context reject/truncate contract. This research record does not infer one.

Structured-output documentation requires the JSON schema in `format` and
recommends also placing it in the prompt. The latter is counted only after the
exact model-visible prompt is known. The documentation does not specify
whether, or by how many tokens, the runtime's `format` handling adds internal
model context. It cannot currently be treated as zero-cost.

Sources:

- [Ollama generate API](https://docs.ollama.com/api/generate)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama OpenAPI contract](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml)

## 2. Exactness finding

**Current classification: NO — no approved mechanism can independently compute
the exact final model-context token count before dispatch.**

The required quantity is not merely a token count for the canonical prompt
bytes. It would have to count, for the pinned model and exact approved Ollama
version, all of:

1. canonical rendered prompt bytes;
2. the actual prompt-template transformation or an explicitly raw model-visible
   prompt;
3. tokenizer normalizer, byte-level BPE vocabulary/merges, and special tokens;
4. `think=false`-related material; and
5. any context effect of the schema-format mechanism and generation reservation.

No approved local tokenizer supplies this quantity. No reviewed public Ollama
endpoint supplies a pre-generation count of that complete transformed request.
`prompt_eval_count` is only available after the provider has processed the
request and cannot be compared to a trusted expected count under the current
contract.

The frozen byte bounds remain useful wire-size and deterministic selection
controls only:

~~~text
PROMPT_BYTE_LIMIT       = 8,192
SCHEMA_BYTE_LIMIT       = 4,096
FULL_REQUEST_BYTE_LIMIT = 32,768
~~~

They do not form a token proof. In particular, neither a formal bound from
input UTF-8 bytes to Qwen tokens nor fixed upper bounds for template, special,
schema-format, and output-reservation overhead are approved. Thus no truthful
inequality of the following required form is available:

~~~text
exact_model_visible_input_tokens
  + exact_internal_context_overhead
  + required_generation_reservation
<= 16,384
~~~

It follows that 8,192 prompt bytes and 4,096 schema bytes are **not proven
safe** for context, and the 32,768-byte HTTP body limit is **not relevant to a
model-token proof** beyond bounding transport data.

## 3. Strategy comparison

| Strategy | Exact proof under current contract | Dependency / runtime impact | Finding |
|---|---:|---|---|
| 1. Exact local tokenizer | No | Requires a new pinned tokenizer engine/artifact and a reproducible final model-visible representation | The only viable pre-dispatch proof path after a separate authorization. A plain upstream tokenizer count is insufficient while Ollama can template the prompt or transform `format`. |
| 2. Conservative mathematical upper bound | No | No new dependency if possible | Not justified: the required raw-token bound and all internal/template/schema/output overhead bounds are unknown. Byte limits cannot stand in for them. |
| 3. Provider-side count/tokenize API | No | Would rely on a pinned documented Ollama operation | No reviewed public API endpoint performs pre-generation counting of the fully transformed `/api/generate` request. Post-generation `prompt_eval_count` is observation only. |
| 4. Sentinel / observational test | No | Benchmark-only evidence | A unique tail item can show that a particular model response was grounded to a tail item. It cannot prove all input survived, that no middle content was dropped, or that the model did not infer/hallucinate the marker. |
| 5. Much narrower input | No, alone | Reduces operational risk only | A smaller byte envelope still cannot prove a token relation or bound hidden transformation overhead. It becomes a proof only when paired with an approved formal upper bound or strategy 1. |

## 4. Recommended path and required next authorization

**Recommended proof strategy: Strategy 1 — exact local tokenizer plus a
reproducible model-visible request representation.** It is selected because it
is the only reviewed path that can create a deterministic pre-dispatch gate;
it does not make the currently frozen contract implementation-ready.

The next, separate **Context Proof Authorization** must specify before any
implementation or benchmark intended to unlock implementation:

1. one exact offline tokenizer engine, version, package hash, license, and
   Apple-Silicon support statement (the likely minimal class is the
   Hugging Face `tokenizers` engine, not the project’s `tiktoken` encoding);
2. immutable source artifacts for the exact Qwen-compatible tokenizer
   (`tokenizer.json`, or an exactly equivalent vocab/merges/config set), each
   with source revision and SHA-256; acquisition and distribution review are
   separate from this record;
3. proof that those artifacts are the tokenizer used by the full-digest
   `qwen3:8b` Ollama model, not merely by an upstream Hugging Face model;
4. one exact model-visible representation: either an approved `raw:true`
   request containing the complete Qwen template and all special-token rules,
   or a byte-for-byte reproducible pinned Ollama rendering path. Choosing raw
   mode would amend the current request/security contract and is not authorized
   by this record;
5. exact handling and count of BOS/EOS, chat-template, `think=false`, schema
   format, and all other internal additions; the authorization must either
   prove their token contribution or prohibit the unaccounted behavior;
6. a documented, tested relation between the counted input and `num_ctx` /
   `num_predict`, including the exact required generation reserve; and
7. fail-closed pre-dispatch behavior plus A3/provenance binding of tokenizer
   engine identity, tokenizer artifacts, model-visible rendering policy, and
   counted-token policy.

This creates a new dependency/artifact authorization requirement. The
tokenizer identity must enter A3 (and the eventual persisted proof) because a
change to its engine or artifacts changes the admission decision.

## 5. Feasibility-gate effect

A separately approved M1 Pro benchmark may proceed **for performance evidence
only** using the current deterministic byte envelope. It may report that the
maximum accepted envelope produced valid output on an exact recorded
runtime/model. It cannot establish formal no-truncation/context safety or
unlock provider implementation until the Context Proof Authorization supplies
the pre-dispatch proof above.

The M1 Pro feasibility authorization and the main Local Deep Analysis
authorization would each need a later amendment after that authorization is
reviewed: the former for an exact maximum safely countable case and the latter
for the tokenizer/rendering/count gate, A3 fields, tests, and final status.

## Final finding

**LOCAL DEEP ANALYSIS CONTEXT PROOF PATH IDENTIFIED**

**NEXT AUTHORIZATION REQUIRED: Context Proof Authorization for a pinned exact
Qwen tokenizer and reproducible Ollama model-visible request transformation**

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED**
