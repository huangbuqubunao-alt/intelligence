# TASK-016 — Qwen2.5:7B model acquisition and exact identity freeze

Status: **ACQUISITION PASSED — TOKENIZER/PARITY, RAW-PROFILE PARITY, AND M1
FEASIBILITY REMAIN SEPARATE GATES**

## Purpose and selection anchor

This record closes the separately authorized acquisition gate for the candidate
selected in [model selection round 2](TASK-016-LOCAL-DEEP-ANALYSIS-MODEL-SELECTION-R2.md).
It freezes local model identity only. It does not establish tokenizer parity,
raw-profile parity, structured-output reliability, M1 Pro feasibility, or
implementation authorization.

`qwen3:8b` remains rejected for its previously tested exact profile; this is a
new candidate and inherits no Qwen3 approval. TASK-016B and TASK-016C remain
closed.

## Acquisition and environment restoration

The first acquisition route through local xray was rejected after the real R2
blob transfer produced TLS-handshake timeouts. Bounded diagnostics established
**DIRECT R2 STABLE / XRAY R2 UNSTABLE**. The sole successful command used a
temporary full-direct Ollama daemon with all upper- and lower-case proxy
variables removed, `OLLAMA_HOST=127.0.0.1:11434`, and loopback `NO_PROXY`.

The one authorized `ollama pull qwen2.5:7b` completed with exit code zero:
`verifying sha256 digest` -> `writing manifest` -> `success`. No second pull,
alternate model, mirror, TLS-verification bypass, generation, tokenizer
acquisition, or benchmark occurred.

The temporary direct daemon was stopped cleanly. Ollama GUI was restored and
again exposes the same model/digest on `127.0.0.1:11434`. Its inherited proxy
variables still point at the stale `http://127.0.0.1:9674`; this is recorded as
**PERSISTENT GUI PROXY CONFIGURATION ISSUE**. It did not invalidate the
completed direct acquisition and was not changed here.

## Canonical local candidate identity

| Field | Observed local value |
| --- | --- |
| Ollama version | `0.32.1` |
| Exact tag | `qwen2.5:7b` (one exact local entry) |
| Full digest | `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` |
| Model size | `4,683,087,332` bytes (Ollama `/api/tags`) |
| Architecture / family | `qwen2` / `qwen2` |
| Parameter count | `7,615,616,512` (`7.6B` label) |
| Quantization | `Q4_K_M` (GGUF file type `15`) |
| Model format | `gguf` |
| Local reported context | `32768` tokens |
| Capabilities | `completion`, `tools` |
| Local license metadata | `apache-2.0` |

The local non-raw template is present only as parity-difference evidence. It
uses Qwen chat markers including `<|im_start|>` and `<|im_end|>`, and has
tool-call branches. It is not authority for the future target architecture,
which remains application-owned rendering with `raw=true` and omitted `format`.

## Upstream identity and license evidence

The corresponding upstream identity is
[`Qwen/Qwen2.5-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct).
The local GGUF metadata identifies base model `Qwen2.5 7B` from Qwen, finetune
`Instruct`, and links that repository. No immutable upstream revision was
observed or frozen in this gate; the Ollama digest is a distinct local manifest
identity and must not be treated as an upstream artifact hash.

The official model card identifies 7.61B parameters and Apache-2.0; its
published configuration explains a 32,768-token default configuration with
YaRN for longer contexts, while the local Ollama artifact reports 32,768. The
official Ollama tag page independently records this tag/digest as a 4.7 GB,
32K-context Q4_K_M `qwen2` artifact. Sources:

- [Qwen upstream model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
- [upstream Apache-2.0 license](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/blob/main/LICENSE)
- [Ollama qwen2.5:7b tag](https://ollama.com/library/qwen2.5:7b)

Apache-2.0 requires preserving applicable license/copyright and NOTICE terms
when redistribution applies. This evidence is not public-release or
redistribution clearance; those project/legal gates remain separate.

## Tokenizer-family finding and reuse decision

Local GGUF tokenizer metadata reports `tokenizer.ggml.model=gpt2`,
`tokenizer.ggml.pre=qwen2`, 152,064 tokenizer tokens, and Qwen special-token
metadata. The upstream model card uses Qwen's `AutoTokenizer` path. This is
evidence of Qwen/Qwen2 tokenizer lineage, not artifact identity.

**Qwen3 tokenizer cryptographic reuse: NOT PROVEN.** Qwen2.5 tokenizer.json
and tokenizer_config.json were not downloaded or hash-frozen here, so their
artifact identities cannot be compared with Qwen3's frozen hashes
`aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` and
`d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101`.
Family/name similarity is insufficient.

## Explicit next gates

1. **Tokenizer artifact/parity gate required:** acquire and hash exact Qwen2.5
   tokenizer artifacts; freeze engine/version, special tokens, and
   `TokenizerIdentity`; prove raw-text token-ID parity.
2. **Raw-profile parity gate required:** use this exact local digest, Ollama
   `0.32.1`, `raw=true`, omitted `format`, local tokenizer count, and Ollama
   `prompt_eval_count`; require equality across fixtures.
3. **M1 Pro feasibility gate required:** begin only after the above, with tiny
   strict-JSON smoke before SHORT 2/2, MEDIUM 2/2, and MAX 3/3.
4. **Byte-bound reconciliation remains required** before a MAX benchmark:
   token count remains context authority; byte limits remain transport/resource
   protection.

LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED.
