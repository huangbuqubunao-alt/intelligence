# TASK-016 — Deterministic Local Deep Analysis model qualification

Status: **IN PROGRESS — C3 acquisition in progress**

This record executes the user-supplied candidate order and mandatory gates as a
mechanical conformance protocol. It is not a model recommendation, comparison,
or implementation authorization. `qwen3:8b` and `qwen2.5:7b` were not
retested.

## Fixed protocol and environment

- Preflight: `main@1d8caf39630b1af4fe47212121cf9fc9b9694ab4`, clean.
- Temporary direct Ollama daemon endpoint: `http://127.0.0.1:11435`.
- Ollama: `0.32.1`.
- Generation profile: `raw=true`, omitted `format`, `stream=false`,
  `think=false`, `temperature=0`, `seed=0`, `num_ctx=16384`.
- TINY semantic case: the previously frozen `knowledge-prompt-v3-raw` case,
  unchanged apart from the `model` field. It has a 2,429-byte canonical schema,
  a 4,181-byte prompt, one authorized Evidence Registry item (`ev-0001`), and
  application-side strict JSON, canonical schema, domain, grounding, and KG2
  validation. No repair, extraction, stripping, truncation, retry, or prompt
  change is used.

## Qualification matrix

| Candidate | Exact tag | Digest | Acquisition | Minimal tokenizer proof | Raw parity | TINY | SHORT | MEDIUM | MAX | Failure class | Final mechanical classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | `gemma3:4b` | `sha256:a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a` | already installed | blocked | not run | not run | not run | not run | not run | `TOKENIZER IDENTITY BLOCKED` | `ACQUISITION/PROOF BLOCKED` |
| C2 | `phi4-mini:latest` | `sha256:78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753` | already installed | pass | pass (3/3) | fail | not run | not run | not run | `REJECTED — STRUCTURED OUTPUT` | `REJECTED — STRUCTURED OUTPUT` |
| C3 | `llama3.1:8b` | pending acquisition | one direct no-proxy pull in progress | pending | pending | pending | not run | not run | not run | pending | pending |
| C4 | `mistral:7b-instruct-v0.3` | not yet inspected | not started | not started | not run | not run | not run | not run | not run | pending | pending |

## C1 — `gemma3:4b`

The exact installed identity from `/api/tags` and `/api/show` was:

| Field | Observed value |
| --- | --- |
| Size | `3,338,801,804` bytes |
| Architecture/family | `gemma3` |
| Parameter count | `4,299,915,632` (`4.3B` reported label) |
| Quantization / format | `Q4_K_M` / `gguf` |
| Reported context | `131072` |
| Tokenizer metadata | `tokenizer.ggml.add_bos_token=true`, `bos_token_id=2`; `add_eos_token=false`, `eos_token_id=1` |

The authoritative upstream repository is
[`google/gemma-3-4b-it`](https://huggingface.co/google/gemma-3-4b-it/tree/main).
Its public repository page explicitly states that repository files require
acceptance of the Gemma usage terms before they can be accessed. Therefore the
required immutable tokenizer artifact and its SHA-256 could not be obtained
without an authentication/terms action, which is outside this protocol. The
local metadata also declares automatic BOS insertion. Consequently A2's
required direct raw-text tokenizer proof (artifact, artifact hash,
special-token list, and no-automatic-special-token encoding) could not be
established. No generation was dispatched.

## C2 — `phi4-mini:latest`

### Identity and tokenizer evidence

| Field | Observed value |
| --- | --- |
| Size | `2,491,876,774` bytes |
| Architecture/family | `phi3` |
| Parameter count | `3,836,021,856` (`3.8B` reported label) |
| Quantization / format | `Q4_K_M` / `gguf` |
| Reported context | `131072` |
| Upstream repository / immutable revision | `microsoft/Phi-4-mini-instruct@cfbefacb99257ffa30c83adab238a50856ac3083` |
| Tokenizer engine | `tokenizers==0.22.2`, direct `Tokenizer.from_file`, `add_special_tokens=false` |
| Automatic BOS / EOS | none for ordinary raw text (`plain` encoded identically with `true` and `false`) |
| Declared special IDs | `199999`, `200018`–`200022`, `200028` |

The retained `/tmp/task016-phi4-tokenizer/` artifacts were acquired from that
immutable upstream revision and hashed locally:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `tokenizer.json` | 15,524,095 | `382cc235b56c725945e149cc25f191da667c836655efd0857b004320e90e91ea` |
| `tokenizer_config.json` | 2,932 | `9c9b6bc0c94d95f69f826c41069a3e8b387ac3ced89601d201886e99240ac9db` |
| `special_tokens_map.json` | 587 | `aff38493227d813e29fcf8406e8e90062f1f031aa47d589325e9c31d89ac7cc3` |
| `added_tokens.json` | 249 | `d4f2aceb0f20b71dd1f4bcc7e052e4412946bf281840b8f83d39f259571af486` |
| `vocab.json` | 3,910,310 | `6cb65a857824fa6615bb1782d95d882617a8bbce1da0317118586b36f39e98bd` |
| `merges.txt` | 2,418,348 | `856ce61180bb689282eed6b3a6838bb1f438399be23aefe9d20eb379791fb4ad` |

The canonical TINY prompt encoded without a declared special-token ID:
`1,186` token IDs; its token-ID SHA-256 is
`fd1d80bf96d84dcaf2dd40523a1e692acdcf0189f775e67882bfde3834fa7967`.

### A4 raw parity

All three one-token probes were HTTP 200, `done=true`, and
`done_reason=length`:

| Fixture | Application tokens | Ollama `prompt_eval_count` | Result |
| --- | ---: | ---: | --- |
| ASCII | 4 | 4 | pass |
| Chinese/mixed | 11 | 11 | pass |
| Canonical TINY prompt fragment | 36 | 36 | pass |

### A5/A6 TINY result

The single durable TINY request had request SHA-256
`a2397801d18c91ce6ee3c961dbb7fa35bdfb130f55ccb680a0aded63b0cfca34` and
prompt SHA-256
`60ae04fc0a264f386147b7862ebea37be42ecbeaca4c0c4cbb9392770a684621`.

| Field | Observed value |
| --- | --- |
| HTTP status / client result | `200` / completed |
| Application tokens / `prompt_eval_count` | `1186` / `1186` (pass) |
| `done` / `done_reason` | `true` / `stop` |
| `eval_count` | `142` |
| Model response bytes / SHA-256 | `534` / `ef8ee077b343c8d982e8b9fc23af5495deaed912efd3d8a70241ae26375f5e6a` |
| Strict whole-document JSON | fail: `JSONDecodeError: Expecting ',' delimiter: line 2 column 407 (char 408)` |

The raw `response` field was passed unchanged to the strict parser. No
schema/domain/grounding/KG2 pass could be claimed after the structural parse
failure, and no retry or repair was issued. C2 is mechanically classified
`REJECTED — STRUCTURED OUTPUT`.

## Interim state

No candidate has reached Phase B. `QUALIFIED_LOCAL_MODEL` is not yet assigned:
C3 acquisition is the active fixed-order step.
