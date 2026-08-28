# TASK-016 — Qwen2.5:7B tokenizer artifact and parity freeze

Status: **PASSED — RAW-PROFILE PARITY, M1 Pro FEASIBILITY, AND IMPLEMENTATION REMAIN SEPARATE GATES**

## A. Purpose and scope

This is a documentation-only freeze of the tokenizer for the already acquired
`qwen2.5:7b` candidate.  It establishes immutable upstream identity, exact
artifact hashes, direct raw-text tokenization, direct/upstream token-ID parity,
special-token handling, and read-only local-GGUF pairing evidence.  It does
not perform generation, an Ollama raw-profile request, a benchmark, model
acquisition, or implementation work.

All upstream artifacts were fetched on 2026-08-28 into the temporary evidence
directory `/tmp/task016-qwen25-tokenizer-evidence.C9h5vz/`; no tokenizer
artifact is stored in this repository.

## B. Exact local model binding

| Field | Frozen value |
| --- | --- |
| Ollama tag | `qwen2.5:7b` |
| Ollama manifest digest | `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` |
| Size | `4,683,087,332` bytes |
| Architecture / family | `qwen2` / `qwen2` |
| Parameters | `7,615,616,512` |
| Quantization / format | `Q4_K_M` / `gguf` |
| Reported context | `32768` |
| Ollama version inspected | `0.32.1` |
| License metadata | `apache-2.0` |

The local Modelfile identifies the GGUF blob
`sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`.
That blob reference is local evidence only; it is not an upstream tokenizer
artifact hash.

## C. Immutable upstream source

| Field | Value |
| --- | --- |
| Repository | [`Qwen/Qwen2.5-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) |
| Immutable revision | `a09a35458c702b33eeacc393d103063234e8bc28` |
| Resolution source | [Hugging Face model API](https://huggingface.co/api/models/Qwen/Qwen2.5-7B-Instruct) and [revision tree API](https://huggingface.co/api/models/Qwen/Qwen2.5-7B-Instruct/tree/a09a35458c702b33eeacc393d103063234e8bc28?recursive=true&expand=true) |
| Retrieval date | 2026-08-28 |
| Upstream license | [Apache-2.0](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/blob/a09a35458c702b33eeacc393d103063234e8bc28/LICENSE) |

`main` was used only to resolve the above API-returned commit.  Every file
below was then downloaded from `/resolve/a09a35458c702b33eeacc393d103063234e8bc28/`.

## D–F. Artifact inventory and tokenizer engine

`tokenizer.json` is the complete, selected runtime artifact: it embeds the
BPE vocabulary, merge list, normalizer, pre-tokenizer, decoder,
post-processor, and added tokens.  `tokenizer_config.json` is required to
freeze Qwen tokenizer metadata and to construct the independent upstream
comparison harness, but is not loaded by the selected direct production path.
`vocab.json` plus `merges.txt` are the authoritative alternate BPE source
representation; they were hashed and inspected but are not a second runtime
input when `tokenizer.json` is used.

| Artifact | Revision-tree bytes | SHA-256 | Role |
| --- | ---: | --- | --- |
| `tokenizer.json` | 7,031,645 | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` | runtime-required and identity-normative |
| `tokenizer_config.json` | 7,305 | `5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583` | identity/parity metadata |
| `vocab.json` | 2,776,833 | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` | alternate upstream BPE representation |
| `merges.txt` | 1,671,839 | `599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3` | alternate upstream BPE representation |

The selected minimal direct engine is Hugging Face
[`tokenizers==0.22.2`](https://pypi.org/project/tokenizers/0.22.2/), loaded in
an isolated temporary virtual environment.  The inspected Apple-Silicon wheel
was `tokenizers-0.22.2-cp39-abi3-macosx_11_0_arm64.whl`, 2,981,472 bytes,
SHA-256 `1e418a55456beedca4621dbab65a318981467a2b188e982a23e117f115ce5001`.
It is Apache-2.0 under the [upstream v0.22.2 license](https://github.com/huggingface/tokenizers/blob/v0.22.2/LICENSE).

The independent upstream-comparison harness was
[`transformers==4.57.1`](https://pypi.org/project/transformers/4.57.1/), using
`Qwen2TokenizerFast.from_pretrained(local_artifact_directory,
local_files_only=True)`.  Its comparison-only distribution was
`transformers-4.57.1-py3-none-any.whl`, 11,990,925 bytes, SHA-256
`b10d05da8fa67dc41644dbbf9bc45a44cb86ae33da6f9295f5fbf5b7890bd267`.
No Hub, cache, `from_pretrained` repository resolution, or network tokenizer
call was permitted after the frozen files were downloaded.

## G. Structural tokenizer facts

| Fact | Observed value |
| --- | --- |
| Model | BPE |
| Normalizer | NFC |
| Pre-tokenizer | `Sequence(Split(Isolated, Qwen/GPT-style regex), ByteLevel(add_prefix_space=false, trim_offsets=false, use_regex=false))` |
| Decoder / post-processor | `ByteLevel(add_prefix_space=false, trim_offsets=false, use_regex=false)` for each |
| Base BPE vocabulary | 151,643 entries |
| Vocabulary including 22 added tokens | 151,665 entries |
| Merge count | 151,387 |
| Added tokens | 22: 14 declared special and 8 non-special tool/FIM/repository tokens |
| Config tokenizer class | `Qwen2Tokenizer` |
| Config BOS / EOS / PAD | `null` / `<|im_end|>` / `<|endoftext|>` |
| Config `add_bos_token` | `false` |
| Config `model_max_length` | 131,072 |
| Chat template | present; SHA-256 of its UTF-8 value: `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f` |

The chat template is metadata, not tokenizer behavior exercised here.  It was
not applied by either parity path and is explicitly outside the later
application-owned `raw=true` prompt profile.

### Declared special-token mapping

| ID | Token |
| ---: | --- |
| 151643 | `<|endoftext|>` |
| 151644 | `<|im_start|>` |
| 151645 | `<|im_end|>` |
| 151646 | `<|object_ref_start|>` |
| 151647 | `<|object_ref_end|>` |
| 151648 | `<|box_start|>` |
| 151649 | `<|box_end|>` |
| 151650 | `<|quad_start|>` |
| 151651 | `<|quad_end|>` |
| 151652 | `<|vision_start|>` |
| 151653 | `<|vision_end|>` |
| 151654 | `<|vision_pad|>` |
| 151655 | `<|image_pad|>` |
| 151656 | `<|video_pad|>` |

## H. Qwen3 reuse decision

| Artifact | Qwen2.5 SHA-256 | Frozen Qwen3 SHA-256 | Equal? |
| --- | --- | --- | --- |
| `tokenizer.json` | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` | No |
| `tokenizer_config.json` | `5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583` | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` | No |

**QWEN3 TOKENIZER REUSE = NO.**  Both required cryptographic comparisons
failed; shared Qwen lineage and matching behavior cannot reverse that result.

## I. Raw text encoding semantics

The frozen direct call is:

```python
tokenizer = tokenizers.Tokenizer.from_file("/operator-approved/tokenizer.json")
encoding = tokenizer.encode(raw_text, add_special_tokens=False)
token_ids = encoding.ids
```

It takes the supplied text unchanged: no Unicode, whitespace, line-ending, or
JSON normalization; no chat-template invocation; and no role, system, BOS, or
EOS insertion.  The direct and upstream paths both encoded `"plain"` as
`[20772]` for `add_special_tokens=False` and for `True`: this tokenizer's
ByteLevel post-processor does not automatically insert BOS/EOS for ordinary
text.  The future Local Deep Analysis path is nevertheless frozen to
`add_special_tokens=False`; automatic special tokens are **disabled** by policy.

## J. Authoritative upstream parity

The direct `Tokenizer.from_file` result was compared exactly with the official
Transformers Qwen implementation, `Qwen2TokenizerFast`, built only from the
same frozen revision files and called with `add_special_tokens=False`.  All
fixtures had exact complete token-ID sequence equality: **11/11 passed; 0
mismatches**.

For each row, `text SHA-256` hashes the fixture's UTF-8 bytes and `token-ID
SHA-256` uses the convention in section L.  Long fixtures are precisely the
shown literal unit repeated 10,000 times.

| Fixture / exact input | Token count | Text SHA-256 | Token-ID SHA-256 |
| --- | ---: | --- | --- |
| ASCII: `Tokenizer parity: plain ASCII text.` | 7 | `f10d5961a5eecdbac3e23ebbbb0fbd0904cc78f80e9bd64ae86c829e0f6114dc` | `6db81886807c7e42306dbfd30dade720b59ee736e446d3addcd76a67278f44da` |
| Chinese: `这是一个用于验证分词器一致性的中文句子。` | 11 | `2b7fcbc333551b8ea97b384ca3da43e315108a21e61792b9eda524ef276d8cdf` | `062806c8d4bc7478377dc503a335bbf87d557c38a2be9679239c2984cd6e964f` |
| Mixed: `Qwen2.5 在 2026 年 supports 中文 + English.` | 19 | `5c26d15773899e2930a7fb9b1a7a713911800300a8569ad9242da5b42e8d74e2` | `59614e9568e699eda083a3128b45a2dc154c8d83728ff8d922bcabae756d925b` |
| Emoji: `Emoji: 👩🏽‍💻🚀✅ — café` | 12 | `757fdedaaaaa766fed71e67b381eee712b2375608d105b438d8da5471c3e7f61` | `a18e709bbe100bee19f37ec00bc40c3f83526ac098d172aaf11d006093d54663` |
| Punctuation: `?!,.;:()[]{}\"'—…` | 10 | `612dac729319dbf7ae84ac52db98039669baf6cd309a9ce01b75ecb02cdc5327` | `f52df111e777188baa16c52764be5ed273c4aeb7e6be80e1fae6f25450182e36` |
| Multiline: `first line\\n第二行\\r\\nthird` | 7 | `0a1363b3f3dfc8436445a352724a78a8e4cea33530a2cdff4c1a261af6746883` | `b43e633f601a5aa58933bf5d56c37cd41310a554831551817a662f6895c65159` |
| JSON: `{"title":"中文","score":7.5,"tags":["AI","测试"]}` | 17 | `1c65d193c9be3176ba33e3a7772edaeec3cfac2683311192a07e057f2533d9b2` | `af72837add87349278f2d77d80f4f5cb1256c14167b6d8f1b77fafd845a50bcd` |
| Delimiters: `[[INPUT_JSON]]\\n[[END_INPUT_JSON]]\\n<|im_start|>user` | 11 | `ebc94139948821de4e37547a306fb972d05a197d71788d5e2d44a4cb809e26e8` | `65aac1d1575ede181b31ee449a9716c969e3904bfdf668c628744909224d81f0` |
| Long Chinese: `深度分析验证。` × 10,000 | 40,000 | `8857a491d742715b7e4b181777561d896f2232412970d39a09dc8021051954f9` | `2fcc36b00b9ff79c5c65063a628a3cba07758bcc60327c7e54a57c2758e6a500` |
| Long mixed: `Qwen2.5 tokenizer 测试 123, ` × 10,000 | 130,001 | `c9a8df009aef53e3e4bcfee561c0b93a2327d00400da9276afedb82eb137f77f` | `5b1e50be863c9bad451a1ce431ffeeb461e6adc2dfa672ace2d23c79820f816d` |
| Literal specials: `<|endoftext|> <|im_start|> <|im_end|> <|vision_pad|>` | 7 | `52257ee3b851242b4aba0314e9acca66982be06ed2faa2298163199b54b9d470` | `5d5d849852052013b511b27d17e6588a6f7a9ad3b4300afbdf688b2779369cc8` |

## K. Special-token safety

Each of the 14 declared literal strings in section G was encoded with both
`add_special_tokens=False` and `True`.  In every case it produced exactly its
declared ID in both modes.  For example, the literal-special fixture produced
`[151643, 220, 151644, 220, 151645, 220, 151654]`.

Therefore literal model-control-looking input is not made safe by disabling
automatic insertion.  **Future runtime special-ID rejection is required: YES.**
After direct encoding and before any dispatch, the application must reject an
input whenever any output ID is one of 151643–151656.  This is a frozen safety
requirement, not an instruction to implement it in this task.

## L. Token-ID hash convention

For each token ID, encode the non-negative integer as exactly four unsigned
big-endian bytes, concatenate in sequence, then SHA-256 the result:

```text
SHA256(b"".join(token_id.to_bytes(4, "big", signed=False) for token_id in token_ids))
```

The fixture matrix records prompt/text SHA-256, token count, and this token-ID
sequence SHA-256.  This convention is frozen as `uint32-big-endian` for the
later Local Deep Analysis context proof.

## M. Read-only local GGUF pairing evidence

Read-only `ollama show --verbose` and `POST /api/show` inspection of the exact
local tag/digest found the following.

| Comparison | Result |
| --- | --- |
| `tokenizer.ggml.model` / `tokenizer.ggml.pre` | `gpt2` / `qwen2` |
| Local `add_bos_token` | `false` |
| Local BOS / EOS / padding IDs | 151643 / 151645 / 151643 |
| Local token array / type array | 152,064 / 152,064 entries |
| Local merge array | 151,387 entries |
| Upstream 151,643 base-vocabulary entries vs local prefix | exact ordered equality |
| Upstream 22 added tokens (through ID 151664) vs local prefix | exact ordered equality |
| Known 151,665-token canonical-array SHA-256, upstream and local prefix | `8f16caacc3cb2c9b7f502ff74306a44ab6cb19e5992dd42120ceda04ba9fb300` |
| Upstream and local merge arrays | exact ordered equality |
| Canonical merge-array SHA-256, upstream and local | `24fa2ae2a398e50784a1fff678482094af4f63e6783d35686726abacda8dc371` |
| Local entries after known upstream prefix | 399, `[PAD151665]` through `[PAD152063]` |
| IDs 151643–151656 locally | the same 14 strings, each GGUF token type `3` |

The 399 GGUF padding entries explain why the local vocabulary array is 152,064
rather than the upstream tokenizer's 151,665 known entries.  The local
container does not expose a hash of an embedded original `tokenizer.json` or
`tokenizer_config.json`, nor a conversion provenance that makes the Ollama
manifest digest an artifact-level hash of those two upstream files.

**Local GGUF pairing classification: STRONGLY EVIDENCED.**  It is deliberately
not called cryptographically proven despite exact normalized vocabulary-prefix
and merge-array comparisons.

## N. Canonical TokenizerIdentity

`TokenizerIdentityV2` is a successor to the earlier Qwen3 V1 record.  V2 makes
the structural fields, complete special-token mapping, explicit
`automatic_special_tokens_enabled`, and `uint32-big-endian` hash encoding
first-class identity semantics; silently adding them to V1 would change its
canonical meaning.  Canonical JSON is UTF-8 with lexicographically sorted
object keys, compact `,`/`:` separators, and `allow_nan=false`.

```json
{"automatic_special_tokens_enabled":false,"base_vocab_size":151643,"identity_schema_version":"TokenizerIdentityV2","merge_count":151387,"model_digest":"sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e","model_tag":"qwen2.5:7b","model_type":"BPE","normative_artifacts":{"tokenizer.json":{"sha256":"c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539","size":7031645},"tokenizer_config.json":{"sha256":"5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583","size":7305}},"pre_tokenizer":"Sequence(Split(regex=\"(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\\r\\n\\p{L}\\p{N}]?\\p{L}+|\\p{N}| ?[^\\s\\p{L}\\p{N}]+[\\r\\n]*|\\s*[\\r\\n]+|\\s+(?!\\S)|\\s+\",behavior=\"Isolated\"),ByteLevel(add_prefix_space=false,trim_offsets=false,use_regex=false))","special_token_mapping":{"<|box_end|>":151649,"<|box_start|>":151648,"<|endoftext|>":151643,"<|im_end|>":151645,"<|im_start|>":151644,"<|image_pad|>":151655,"<|object_ref_end|>":151647,"<|object_ref_start|>":151646,"<|quad_end|>":151651,"<|quad_start|>":151650,"<|video_pad|>":151656,"<|vision_end|>":151653,"<|vision_pad|>":151654,"<|vision_start|>":151652},"token_id_hash_encoding":"uint32-big-endian","tokenizer_config_sha256":"5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583","tokenizer_engine":"tokenizers","tokenizer_engine_distribution_filename":"tokenizers-0.22.2-cp39-abi3-macosx_11_0_arm64.whl","tokenizer_engine_distribution_sha256":"1e418a55456beedca4621dbab65a318981467a2b188e982a23e117f115ce5001","tokenizer_engine_version":"0.22.2","tokenizer_json_sha256":"c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539","upstream_repository":"Qwen/Qwen2.5-7B-Instruct","upstream_revision":"a09a35458c702b33eeacc393d103063234e8bc28","vocab_size":151665}
```

The canonical byte sequence is 1,768 bytes.  Its SHA-256 is:

```text
037a4818fa3fd530f5f9f7754faf6af1f92be77964b8271dac8ebb17ddf2d53d
```

## O. Gate conclusion

The tokenizer artifact/parity gate passes all required conditions:

1. immutable upstream revision and exact artifacts are frozen;
2. direct engine/version/distribution hash are frozen;
3. direct local artifact loading is reproducible with no automatic special-token insertion;
4. all 11 authoritative raw-text parity fixtures match exactly;
5. special-token recognition and the mandatory rejection policy are characterized;
6. the token-ID hash convention and `TokenizerIdentityV2` are frozen; and
7. local-GGUF pairing is at least strongly evidenced.

No ambiguity remains for the next gate's tokenizer side.  This result does not
prove what an Ollama `raw=true` request evaluates; that requires the explicit
runtime request/response parity gate.

## P. Explicit next gate and preserved restrictions

The next permitted evidence gate is **Qwen2.5:7B raw-profile parity** for the
exact local digest and Ollama version, comparing this direct token count with
Ollama `prompt_eval_count` under `raw=true` with no formatting.  M1 Pro
feasibility remains after that gate.  Local Deep Analysis implementation,
TASK-016D/E/F, generation, benchmark execution, model acquisition, project
dependency changes, push, and tag creation remain unauthorized.
