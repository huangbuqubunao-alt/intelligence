# TASK-016 — Qwen2.5:7B strict-JSON / M1 Pro feasibility gate

Status: **BLOCKED BEFORE TINY DISPATCH — FROZEN TOKENIZER EXECUTION ENGINE UNAVAILABLE**

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

## Pre-dispatch blocker

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

No `POST /api/generate` request was sent.  Therefore no model was loaded, no
strict-JSON result exists, and no SHORT, MEDIUM, or MAX attempt was made.  This
is not a model failure and not a retryable benchmark case; it is a
pre-dispatch evidence-environment blocker.

## Required decision to resume

A narrowly scoped authorization must make the already-frozen
`tokenizers==0.22.2` Apple-Silicon distribution available for local,
hash-verified, non-network use, or must provide an equally exact approved
tokenizer execution environment.  It must not change the model, tokenizer
identity, raw profile, prompt, byte limits, or benchmark sequence.  Once that
prerequisite exists, the next permitted action remains exactly one tiny
strict-JSON smoke; only a pass may advance to SHORT 2/2.

**QWEN2.5 STRICT-JSON / M1 PRO FEASIBILITY REMAINS UNDETERMINED.**

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED.**
