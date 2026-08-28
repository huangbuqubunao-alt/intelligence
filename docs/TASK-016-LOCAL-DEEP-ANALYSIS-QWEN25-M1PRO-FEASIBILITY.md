# TASK-016 — Qwen2.5:7B strict-JSON / M1 Pro feasibility gate

Status: **FAILED — DECISIVE TINY STRICT-JSON FAILURE**

## Scope and baseline

This is a docs-only record for the separately authorized Qwen2.5 feasibility
gate.  It does not reopen TASK-016B, TASK-016C, Phase G, or H1; it does not
alter `PROJECT_STATUS.md`.  No production code, test, migration, dependency,
lockfile, model artifact, cache, or task state was changed.

The executor preflight accepted the requested local baseline:

| Field | Observed value |
| --- | --- |
| Repository branch | `main` |
| HEAD | `013137e8f5b6024e140eea147e6802951acfffb0` |
| Worktree | clean before this evidence record |

## Frozen identity verification

| Identity | Required value | Observed evidence |
| --- | --- | --- |
| Ollama version | `0.32.1` | `GET http://127.0.0.1:11434/api/version` returned `{"version":"0.32.1"}` through a direct no-proxy loopback transport. |
| Model tag | `qwen2.5:7b` | `/api/tags` returned exactly one entry with that name. |
| Manifest digest | `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | The unique tag entry reported bare digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`. |
| Model details | `qwen2` / `Q4_K_M` / `gguf` / 32,768 context | The same local tag record reported family `qwen2`, quantization `Q4_K_M`, format `gguf`, and context `32768`. |
| `TokenizerIdentityV2` | `037a4818fa3fd530f5f9f7754faf6af1f92be77964b8271dac8ebb17ddf2d53d` | Matches the frozen tokenizer record.  The retained local files independently re-hashed to the four recorded SHA-256 values below. |
| `RawProfileIdentityV1` | `dba3cbdb83e16c0111659fea988ced972277a1d1d78b820cff3b2ca0f9c11682` | Matches the frozen raw profile: raw true, omitted format, stream false, think false, temperature 0, seed 0, num_ctx 16,384, and production num_predict 2,048. |

The retained, already-frozen tokenizer evidence directory contains no model
weights and was not modified:

| Artifact | SHA-256 recheck |
| --- | --- |
| `tokenizer.json` | `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539` |
| `tokenizer_config.json` | `5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583` |
| `vocab.json` | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` |
| `merges.txt` | `599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3` |

## M1 Pro environment facts

| Field | Observed value |
| --- | --- |
| Mac | `MacBookPro18,3` / `MKGQ3CH/A` |
| Chip | Apple M1 Pro |
| Unified memory | 16 GB / `17,179,869,184` bytes (`system_profiler`, `sysctl hw.memsize`) |
| macOS | 26.3.1, build `25D2128` |
| Endpoint | `http://127.0.0.1:11434` only |
| Runtime process observation | One `ollama serve` process was present; no `llama-server` worker existed before any generation request. |
| Memory observation | At collection, 16,384-byte pages: free `478,625,792` bytes; inactive `5,825,183,744` bytes; speculative `135,905,280` bytes; their sum was `6,439,714,816` bytes.  This is not a peak-RSS measurement. |

## Original pre-dispatch blocker

The raw-profile gate requires the pre-dispatch exact token-ID sequence and
count for the complete rendered candidate, using the frozen direct engine
`tokenizers==0.22.2` and `add_special_tokens=False`.  This is required before
the first tiny request, not merely for a later MAX request.

The retained evidence directory contains only the four hash-verified tokenizer
artifacts above.  It contains neither the isolated execution environment nor
the frozen Apple-Silicon wheel.  The current project environment, system
Python interpreters, known local Python site-packages, and the local uv cache
contain no importable `tokenizers` package and no
`tokenizers-0.22.2-*.whl`.  Consequently, the runner cannot reproduce the
required exact complete-prompt token count or special-token-ID rejection.

The frozen byte constraints remain `8,192` prompt bytes, `4,096` schema bytes,
and `32,768` serialized request bytes.  They are independent resource bounds,
not a substitute for the required token proof.  Without the exact tokenizer
engine, byte-only construction cannot truthfully reconcile a dispatchable
candidate, so no new tiny/SHORT/MEDIUM/MAX corpus or prompt was invented.

No `POST /api/generate` request was sent during this first attempt.  Therefore
no model was loaded, no strict-JSON result existed, and no SHORT, MEDIUM, or
MAX attempt was made.  This was not a model failure; it was a pre-dispatch
evidence-environment blocker.

## Temporary tokenizer environment restoration — 2026-08-28

The exact frozen runtime was restored under `/tmp` only; no project, global,
or persistent dependency state was modified.

| Field | Verified value |
| --- | --- |
| Frozen wheel | `tokenizers-0.22.2-cp39-abi3-macosx_11_0_arm64.whl` |
| Wheel source | Exact `tokenizers==0.22.2` PyPI release artifact only |
| Wheel bytes / SHA-256 | `2,981,472` / `1e418a55456beedca4621dbab65a318981467a2b188e982a23e117f115ce5001` |
| Verified wheel location | `/tmp/task016-qwen25-feasibility-tokenizer/tokenizers-0.22.2-cp39-abi3-macosx_11_0_arm64.whl` |
| Active temporary environment | `/tmp/task016-qwen25-feasibility-venv-py312` |
| Active Python | `/tmp/task016-qwen25-feasibility-venv-py312/bin/python`, Python `3.12.11` |
| Installed distribution | `tokenizers==0.22.2`, installed only from the verified local wheel with `--no-deps --no-index` |

The retained artifact directory was re-hashed against the four frozen values.
The direct `Tokenizer.from_file(tokenizer.json)` path then passed the frozen
ASCII, Chinese, and JSON fixture count/token-ID hashes.  It encoded `plain`
as `[20772]` with both `add_special_tokens=False` and `True`, demonstrating no
automatic BOS/EOS insertion for that ordinary input.  The literal special
fixture encoded as `[151643, 220, 151644, 220, 151645, 220, 151654]`; it
therefore mechanically supports mandatory pre-dispatch rejection of IDs
`151643..151656` and was not sent to Ollama.

The exact 1,768-byte canonical `TokenizerIdentityV2` JSON was re-parsed,
canonicalized, and SHA-256 re-computed as
`037a4818fa3fd530f5f9f7754faf6af1f92be77964b8271dac8ebb17ddf2d53d`.

**QWEN2.5 FEASIBILITY TOKENIZER PREFLIGHT UNBLOCKED.**

## Tiny strict-JSON smoke — stopped without a verifiable result

The one frozen tiny candidate was constructed from the exact
`knowledge-prompt-v3-raw` template and the exact canonical 2,429-byte schema.
It passed all pre-dispatch checks:

| Metric | Value |
| --- | --- |
| Prompt bytes / SHA-256 | `4,181` / `60ae04fc0a264f386147b7862ebea37be42ecbeaca4c0c4cbb9392770a684621` |
| Complete raw request bytes / SHA-256 | `4,827` / `a584b8370bf64085ef070a9bb7b3b99fa23d0292178009ab4898665accca92c2` |
| Schema bytes / SHA-256 | `2,429` / `3fdb078b85611a1b4c68e5276362dbee405bf98eaa8093cc8438c8e7e1a42015` |
| Exact tokenizer input tokens | `1,235` |
| Token-ID SHA-256 | `a0699e646aaa351b0cce06da44d39a296de93433e6c197c7fe214bc5ddc5b8ff` |
| Limits | `1,235 <= 14,336`; `4,181 <= 8,192`; `2,429 <= 4,096`; `4,827 <= 32,768`; no special ID |

Exactly one local `POST /api/generate` was initiated with the frozen
raw/no-format profile after those checks.  The process hosting the one request
returned no captured stdout/stderr after 30 seconds; a subsequent process check
found neither the runner nor a `llama-server` worker.  No response envelope,
raw model response, HTTP status, `prompt_eval_count`, wall-clock completion,
strict JSON parse, schema result, grounding result, or KG2 result is available
as evidence.

This is an **UNVERIFIED TRANSPORT / EVIDENCE CAPTURE OUTCOME**, not a valid PASS
and not an evidenced model structural failure.  It was excluded from quality
scoring and was not averaged with any later result.  SHORT, MEDIUM, and MAX
were not dispatched.

## Narrow tiny outcome-recovery authorization and decisive redispatch — 2026-08-28

After the unverified first outcome, a narrow authorization permitted exactly one
additional tiny dispatch solely to recover a durable transport/response result.
It did not authorize prompt/profile changes, a retry loop, output repair, or a
second redispatch.  The recovery execution began from
`main@29d43c43f3b10b365599946875f699995e0ec0b4` and reused the same tiny
request exactly: body SHA-256
`a584b8370bf64085ef070a9bb7b3b99fa23d0292178009ab4898665accca92c2`, prompt
SHA-256 `60ae04fc0a264f386147b7862ebea37be42ecbeaca4c0c4cbb9392770a684621`,
token count `1,235`, and token-ID SHA-256
`a0699e646aaa351b0cce06da44d39a296de93433e6c197c7fe214bc5ddc5b8ff`.

Before dispatch, the same temporary `tokenizers==0.22.2` Python 3.12.11
environment, all frozen tokenizer artifact hashes, `TokenizerIdentityV2`,
Ollama `0.32.1`, and the exact unique `qwen2.5:7b` digest were reverified.
The request passed its byte, input-token, and special-token-ID gates.

The one decisive request used a durable local capture directory under `/tmp`.
It flushed the exact request body, preflight metrics, status, response headers,
complete envelope body, transport timing, stderr, and client exit code before
evaluation.  Those raw local-only evidence files are not repository artifacts.

| Transport field | Decisive observed value |
| --- | --- |
| Redispatch count | `1` |
| HTTP status / client exit code | `200 OK` / `0` |
| Envelope bytes / complete parse | `3,031` / yes |
| `done` / `done_reason` | `true` / `stop` |
| Wall-clock transport duration | `32,407.2365` ms |
| Ollama `prompt_eval_count` / application count | `1,235` / `1,235` (**PASS**) |
| `eval_count` | `618` |
| Exact model response bytes / SHA-256 | `2,528` / `02be6baa4c6bfe8aaace037c377f66840b7c6e5b7b8855221f87b911f36020d3` |

The raw Ollama `response` field was decoded as strict UTF-8 and supplied
unchanged to the strict whole-document JSON parser.  It failed with
`JSONDecodeError: Extra data: line 40 column 3 (char 988)`.  No fence stripping,
trailing-text removal, first-object extraction, regex repair, second-model
repair, or retry was attempted.  Because strict JSON is a prerequisite, schema,
domain, grounding, KG2, and output-language validation were not evaluated.

**DECISIVE TINY: 1/1 FAIL — STRUCTURED OUTPUT.**

The previous outcome remains unverified and is not counted as a model failure;
the single fully captured recovery dispatch is the decisive failure.  SHORT,
MEDIUM, and MAX remain not run.

**QWEN2.5:7B IS REJECTED FOR THE CURRENT FROZEN RAW / NO-FORMAT PROFILE.**

**MODEL SELECTION ROUND 3 REQUIRED.**

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED.**
