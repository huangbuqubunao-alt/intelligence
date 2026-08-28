# TASK-016 — Qwen2.5:7B raw-profile tokenizer / Ollama parity

Status: **PASSED — STRICT-JSON / FEASIBILITY AND IMPLEMENTATION REMAIN SEPARATE GATES**

## A. Purpose

This documentation-only gate proves exact model-visible prompt-token accounting
for the frozen `qwen2.5:7b` local model.  It compares the frozen direct Qwen2.5
tokenizer with Ollama's `prompt_eval_count` under the application-owned raw
profile.  It is not a quality benchmark, strict-JSON smoke, feasibility test,
model acquisition, or implementation authorization.

All traffic used direct loopback `http://127.0.0.1:11434` with proxy variables
removed and an explicit no-proxy transport.  No model acquisition, remote
endpoint, provider format, retry, repair, or model substitution occurred.

## B. Frozen identities and runtime inspection

| Field | Observed / frozen value |
| --- | --- |
| Ollama version (`GET /api/version`) | `0.32.1` |
| Model tag (`GET /api/tags`) | `qwen2.5:7b` |
| Manifest digest | `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` |
| Architecture / family (`POST /api/show`) | `qwen2` / `qwen2` |
| Parameters | `7,615,616,512` |
| Quantization / format | `Q4_K_M` / `gguf` |
| Model-reported context | `32768` |
| Template present in local metadata | yes (not used in raw profile) |

`/api/tags` returned one exact `qwen2.5:7b` entry with the required bare digest
payload. Prefixing it with `sha256:` gives the frozen manifest digest above.
All version, tag, show, and generation calls returned HTTP 200.

## C. Frozen application tokenizer identity

The application-side path was exactly:

```python
tokenizer = tokenizers.Tokenizer.from_file(".../tokenizer.json")
token_ids = tokenizer.encode(raw_text, add_special_tokens=False).ids
```

It applies no chat template, role marker, BOS, EOS, or automatic special-token
insertion.  The retained temporary evidence artifacts were used; none were
reacquired.  Every required SHA-256 matched the preceding tokenizer freeze.

| Artifact | SHA-256 | Verified |
| --- | --- | --- |
| `tokenizer.json` | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` | yes |
| `tokenizer_config.json` | `5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583` | yes |
| `vocab.json` | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` | yes |
| `merges.txt` | `599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3` | yes |

| Tokenizer field | Frozen value |
| --- | --- |
| Upstream | `Qwen/Qwen2.5-7B-Instruct@a09a35458c702b33eeacc393d103063234e8bc28` |
| Engine | `tokenizers==0.22.2` |
| `TokenizerIdentityV2` | `037a4818fa3fd530f5f9f7754faf6af1f92be77964b8271dac8ebb17ddf2d53d` |
| Token-ID sequence hash encoding | unsigned `uint32` big-endian, concatenated, SHA-256 |
| Declared special IDs | `151643` through `151656` |

Qwen3 tokenizer reuse remains **NO**.

## D. Tested raw request profile

Each parity fixture sent exactly the following request semantics to
`POST /api/generate`:

```json
{"model":"qwen2.5:7b","prompt":"<exact fixture UTF-8 text>","raw":true,"stream":false,"think":false,"options":{"temperature":0,"seed":0,"num_ctx":16384,"num_predict":1}}
```

`format` was omitted, not set to JSON or a schema.  `num_predict:1` is the
small bounded parity probe value only; it is not the production output budget.
All returned `done:true` with `done_reason:"length"`, so the probe did not
evaluate output quality.

`think:false` was accepted on every raw request (HTTP 200).  No raw response
contained a `thinking` field, and the emitted one-token response contained no
observable thinking content.  The runtime does not report a separate parameter
acknowledgement, so this records the actual observable behavior as
`accepted_no_thinking_field_observed`, not a claim that Qwen3 thinking semantics
apply to Qwen2.5.

## E. Exact fixture parity

Every fixture was direct-tokenized before dispatch and was rejected if any ID
was in `151643..151656`.  None of these nine safe fixtures contained such an
ID.  “KnowledgeContent schema” is a representative frozen canonical-schema
fixture with all top-level `KnowledgeContent` fields; “Evidence Registry” is a
representative two-item registry fixture.  The delimiter fixture uses only
application delimiters, not a literal model special token.

| Fixture | UTF-8 bytes | Text SHA-256 | Application tokens | Token-ID SHA-256 | Ollama `prompt_eval_count` | Match |
| --- | ---: | --- | ---: | --- | ---: | --- |
| `ascii_short` | 37 | `5b595c6f691f93435baf77d3f8023e3a490059a67ecd9c30fa3f3d4b511288dd` | 8 | `61078169744b97286cd21072827fe96d36dc39aeab5a1729cf496b3756fe2baf` | 8 | yes |
| `simplified_chinese` | 78 | `17af98116b6308e27b427984e4642808b858184bac8b9555af77df11fcee6926` | 15 | `5f7b76ffd0f9593e40a11be2d331d778ae5f82d54b69f311bbc1e5d57d2c83e9` | 15 | yes |
| `mixed_zh_en` | 64 | `da5e2eb0fd6b3700a8aac4e50a90577d4609ed5ef09327bc4b168ceaf7c02b50` | 21 | `dc8a77647b4b5bdafbb70c072e797915a6355c386978accced9bb69176ef5465` | 21 | yes |
| `emoji` | 47 | `4d30500cddef0472b60e6ec094885b12891885172a576d27074edcbc7565ae4c` | 13 | `983c31e2c9959d97332b5faf7cca881c6408d1dd812570934380fd04ddc165f2` | 13 | yes |
| `multiline` | 35 | `3f2c5ef8f8660bd264aa74ca4d970b9e266d7ba87e226c454802021a38bbb945` | 9 | `cbeab192e64f8fb6f66ecab0801516feb92db9979db01cce33c69e78e001d1c9` | 9 | yes |
| `json_heavy` | 87 | `044b6e1f4571591d1048367ae197a14adba554485db2f58518b55b6a31a2d854` | 29 | `7a01ec3cbadaa00edae28958303b02b42905710b6c9f5b6f50e558f9511938b0` | 29 | yes |
| `local_deep_analysis_delimiters` | 116 | `cf64154086a49799b39075567c74f7afaf8e56cf03cc9b047072e04715d453b5` | 31 | `1ddd72d6d30ac5f51da53ad65450d58015fcb2355b185ae0c3c6ab05f9caa57c` | 31 | yes |
| `knowledgecontent_schema_representative` | 581 | `d29530609b98f62d5d40bb31d8fea4d75498271283463a17a12f52cd51a90513` | 135 | `7079824c1cc1dc6a2652ce1dc159c0781902890e4696a2d5b3b13ce30c81666a` | 135 | yes |
| `evidence_registry_representative` | 333 | `bb525fd6a0bd6f238a941f0a41b421313cc8c57c10cbb94f385d070b091b3fcd` | 86 | `ca2c3acf2d888e7df2f59211627f0daf5517d4379b2c0acee04898fccddc0eec` | 86 | yes |

Exact result: **9/9 matches; 0 mismatches.**

## F. Raw/non-raw control

The same `ascii_short` UTF-8 prompt was used for one bounded control with all
other request fields unchanged:

| Path | Application count | Ollama `prompt_eval_count` |
| --- | ---: | ---: |
| `raw:true` | 8 | 8 |
| `raw:false` | 8 | 37 |

The 29-token difference demonstrates that the non-raw path contributes local
template content.  The raw path is therefore the only proven application-owned
prompt-accounting path; the non-raw result is not used for production parity.

## G. Special-token negative control

The local-only literal string
`<|im_start|><|im_end|><|endoftext|>` had 35 UTF-8 bytes, text SHA-256
`d3890a57622ad0895c1bd1e158e228c0732f5009c2aac90b4bb7ebbe3fb09c35`, and
encoded to three IDs: `151644`, `151645`, and `151643`.  It was rejected before
dispatch and was not sent to Ollama.

**LOCAL SPECIAL-TOKEN REJECTION: PASS.**

## H. Context-accounting conclusion

This gate mechanically supports the future raw-profile rule:

```text
model-visible input token count = exact application-side tokenizer count
```

Thus the existing conservative predicate remains:

```text
input_tokens + output_budget <= num_ctx
```

The application profile deliberately remains `num_ctx:16384` with production
`num_predict:2048`, leaving a maximum admissible model-visible input of
`14336` tokens.  This is an accounting proof only: it does not test quality,
latency, memory, or feasibility at 14,336 input tokens.  The local model's
reported 32,768 context is distinct from, and does not alter, that intentional
16,384-token application limit.

## I. Canonical raw-profile identity

Canonical JSON is UTF-8, sorted-key, compact-separator JSON with non-finite
values forbidden:

```json
{"automatic_bos":false,"automatic_chat_template":false,"automatic_eos":false,"format_omitted":true,"model_digest":"sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e","model_tag":"qwen2.5:7b","num_ctx":16384,"ollama_version":"0.32.1","production_num_predict":2048,"raw":true,"schema_version":"RawProfileIdentityV1","seed":0,"special_token_ids_rejected":true,"stream":false,"temperature":0,"think_behavior":"accepted_no_thinking_field_observed","token_id_hash_encoding":"uint32-big-endian","tokenizer_identity":"037a4818fa3fd530f5f9f7754faf6af1f92be77964b8271dac8ebb17ddf2d53d"}
```

`RawProfileIdentityV1` SHA-256:

```text
dba3cbdb83e16c0111659fea988ced972277a1d1d78b820cff3b2ca0f9c11682
```

This Qwen2.5 identity is distinct from and does not reuse any Qwen3 profile
identity.

## J. Gate conclusion and next boundary

All raw-profile parity conditions pass: exact model and tokenizer identities,
accepted raw/no-format request semantics, accepted `num_ctx:16384`, nine exact
safe-fixture matches, zero mismatches, template-bypass control, and pre-dispatch
special-token rejection.  Generation was used only for bounded accounting
fixtures.

The next separately authorized gate must first address any remaining
byte/resource-bound reconciliation and then run a tiny strict-JSON smoke.  Only
after that smoke succeeds may SHORT 2/2, MEDIUM 2/2, and MAX 3/3 be considered.
No Local Deep Analysis implementation is authorized by this evidence.
