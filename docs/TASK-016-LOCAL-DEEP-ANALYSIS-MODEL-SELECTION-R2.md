# TASK-016 — Local Deep Analysis model selection, round 2

Status: **CANDIDATE ACQUIRED — TOKENIZER/PARITY, FEASIBILITY, AND IMPLEMENTATION REMAIN UNAUTHORIZED**

This docs-only record follows `main@aeed45994b7752845d626b0bb9244a37ab341d84`.
It selects one next candidate for a future, separately authorized, single-model
acquisition and validation gate. It authorizes no model/tokenizer acquisition,
Ollama contact, generation, benchmark, dependency change, production/test/migration
change, TASK-016D/E/F work, merge, push, tag, or change to TASK-016B/C.

## 1. Preserved contract

The failed profile was exactly `qwen3:8b` at
`sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`,
Ollama `0.32.1`, `raw=true`, omitted `format`, `stream=false`, `think=false`,
`temperature=0`, `seed=0`, `num_ctx=16384`, and `num_predict=2048`.

The trust contract does not change. Raw provider output remains untrusted until
strict whole-response JSON parsing, closed `KnowledgeContent` validation,
semantic validation, and Evidence Registry grounding all pass. Exactly one JSON
object is required: no Markdown/prose, provider provenance, second Judge,
extraction, regex repair, fence stripping, trailing-text truncation, automatic
repair, or retry-until-valid behavior is allowed.

Evidence Registry, A1 semantic input, scoring authority, grounding,
`TrustedLocalDeepAnalysisSuccess`, no-cache/no-persistence, Cloud-off cutover,
and TASK-016D handoff concepts remain unchanged. `raw=true` plus omitted
`format` remains preferred because it keeps the exact rendered prompt
application-owned. A model requiring provider `format` must carry a separate
context-proof amendment; provider format is not reintroduced here.

The existing `num_ctx=16384` and `num_predict=2048` envelope is retained. No
evidence supports lowering either without a design amendment.

## 2. Qwen3 failure classification and decision

The decisive SHORT run had exact tokenizer/Ollama parity (`1303 == 1303`), took
`99.128` seconds, and neither crashed nor OOMed. It began with valid-looking JSON
but then emitted Markdown fences and repeated prose. Strict whole-response parsing
therefore failed; closed schema and grounding could not pass.

| Classification | Finding | Basis |
| --- | --- | --- |
| Model instruction-following | **PRIMARY FAILURE** | Prompt required one JSON object/no Markdown and untrusted evidence; the response continued with Markdown/prose and followed supplied evidence text. |
| Structured-output reliability | **PRIMARY FAILURE** | A required run was malformed; mandatory reliability is 100%, not an average. |
| Raw/no-format behavior | **CONTRIBUTING, NOT PROVEN CAUSAL** | It failed in that profile, but the failure does not establish raw mode as its cause. |
| Prompt contract | **NO OBVIOUS BUG** | The frozen prompt already contains JSON-only, schema, and untrusted-evidence instructions. |
| Resource failure | **NOT DECISIVE** | The request completed below 300 seconds and no crash/OOM occurred. |
| Context failure | **NOT SHOWN** | SHORT parity passed; MAX was not dispatched. |

Decision: **REJECT CURRENT CANDIDATE.** A correction round is not justified:
there is no single obvious request/prompt bug, and stronger wording would be
unauthorized prompt-tuning. The rejection scope is only the exact Qwen3 tag,
digest, Ollama version, and raw/no-format profile above. It does not reject all
Qwen3 or all Qwen models.

## 3. Candidate matrix

Target hardware is Apple M1 Pro with 16 GB unified memory. A single 7–8B Q4
artifact near 4.4–4.9 GB is realistic but tight once runtime, a 16K KV cache,
and OS pressure are included. The closest local evidence is the failed Qwen3
Q4 run: about 6.8 GiB observed worker RSS plus increased compression/swap, not
a portable peak estimate. 12B+ candidates are excluded for inadequate margin.

All fit/latency statements assume a single Q4-class worker at `16384/2048` and
are admission hypotheses only; later controlled evidence is required.

| Candidate | Parameters / artifact | Context / M1 fit / latency | Chinese | JSON / raw compatibility | Tokenizer proof cost | License / availability | Principal risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen2.5:7b` | Qwen2.5 Instruct, 7.61B; 4.7 GB tag artifact. | 32K tag context; **GOOD** fit; expected latency comparable to or modestly better than Qwen3, unmeasured. | **STRONG** — Chinese is among 29+ documented languages. | **GOOD** potential; Qwen documents JSON/instruction improvements. **LIKELY COMPATIBLE** raw/no-format. | Pin Qwen2.5 artifacts/revision, offline engine, and exact raw token-ID parity. Existing proof shape reusable; identity changes. **MEDIUM**. | Apache-2.0; exact Ollama tag. | Claims are not reliability evidence. |
| `gemma3:4b` | Gemma 3, 4B; 3.3 GB Q4 tag artifact. | 128K advertised; **EXCELLENT** fit and likely lower latency. | **ADEQUATE** — 140+ language claim; Chinese grounding unproven. | **GOOD** potential; **LIKELY COMPATIBLE** only after raw parity. | Separate Gemma artifacts/offline engine/raw proof. **MEDIUM**. | Gemma Terms, not permissive OSS; exact Ollama tag. | Requires Ollama 0.6+, unlike frozen 0.32.1 evidence. |
| `phi4-mini:3.8b` | Phi-4-mini-instruct, 3.8B; 2.5 GB Q4 tag artifact. | 128K advertised; **EXCELLENT** fit and likely lower latency. | **ADEQUATE** — Chinese supported but not Chinese-first. | **GOOD** potential; **LIKELY COMPATIBLE** only after raw parity. | Separate Microsoft artifacts/raw proof. **MEDIUM**. | MIT; exact Ollama tag. | Requires Ollama 0.5.13+; smaller capacity may limit synthesis. |
| `llama3.1:8b` | Llama 3.1 Instruct, 8B; 4.9 GB Q4_K_M tag artifact. | 128K advertised; **GOOD** but tight; likely Qwen3-like latency. | **ADEQUATE** at best for Chinese-first use. | **GOOD** potential; **LIKELY COMPATIBLE** after distinct raw proof. | Separate Meta tokenizer/special-token raw proof. **MEDIUM**. | Llama 3.1 Community License; exact Ollama tag. | No Chinese or fit advantage over Qwen2.5. |
| `mistral:7b-instruct-v0.3-q4_K_M` | Mistral 7B v0.3, 7.24B; 4.4 GB Q4_K_M artifact. | 32K advertised; **GOOD** fit; expected Qwen2.5-like latency. | **WEAK** relative to Qwen. | **ACCEPTABLE** potential; raw/no-format unproven. | Mistral's distinct tokenizer needs a new raw proof. **HIGH**. | Apache-2.0; exact Ollama tag. | Chinese quality and proof cost. |

Sources: [Qwen2.5 tag](https://ollama.com/library/qwen2.5:7b),
[Qwen2.5 model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct),
[Gemma 3 tag](https://ollama.com/library/gemma3:4b),
[Phi-4-mini tag](https://ollama.com/library/phi4-mini:3.8b),
[Phi-4-mini model card](https://huggingface.co/microsoft/Phi-4-mini-instruct),
[Llama 3.1 tags](https://ollama.com/library/llama3.1/tags), and
[Mistral 7B v0.3](https://docs.mistral.ai/models/mistral-7b-0-3).

## 4. Ranking and selection

Priority order: structured JSON reliability and M1 feasibility (**very high**);
Chinese analysis, tokenizer/context-proof cost, and general analysis quality
(**high**); license/supply chain (**medium/high**); latency (**medium**).
Potential does not substitute for controlled evidence.

| Order | Candidate | Structured JSON | M1 fit | Chinese | Proof cost | Analysis | License | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `qwen2.5:7b` | **GOOD** | **GOOD** | **EXCELLENT** | **GOOD** | **GOOD** | **EXCELLENT** | **SELECT** |
| 2 | `gemma3:4b` | **GOOD** | **EXCELLENT** | **ACCEPTABLE** | **ACCEPTABLE** | **GOOD** | **POOR** | Runner-up |
| 3 | `phi4-mini:3.8b` | **GOOD** | **EXCELLENT** | **ACCEPTABLE** | **ACCEPTABLE** | **ACCEPTABLE** | **EXCELLENT** | Reserve |
| 4 | `llama3.1:8b` | **GOOD** | **GOOD** | **ACCEPTABLE** | **ACCEPTABLE** | **GOOD** | **ACCEPTABLE** | Not preferred |
| 5 | `mistral:7b-instruct-v0.3-q4_K_M` | **ACCEPTABLE** | **GOOD** | **POOR** | **POOR** | **ACCEPTABLE** | **EXCELLENT** | Not preferred |

Selected candidate: **`qwen2.5:7b`**. It is a separate 7.61B Qwen2.5 Instruct
model, not an attempt to repair Qwen3. It is smaller in Q4-class form and has
documented Chinese/structured-output strengths. It defeats runner-up `gemma3:4b`
because it keeps a permissive license, avoids a necessary runtime upgrade, and
has more direct Chinese evidence. This is selection for one gate, not reliability
or implementation approval.

## 5. Byte bounds and forbidden rescue

The MAX diagnostic is **NEED RECONCILIATION**, not the selection blocker. The
`8905`-token partial prefix was below the `14336` token predicate but its
`32,380`-byte prompt and `33,520`-byte body exceed frozen `8,192` / `32,768`
resource bounds. Token proof remains context authority; bytes remain transport
protection. Before the new MAX benchmark, either select a source prefix meeting
both predicates or separately amend byte limits with evidence.

Fence stripping, trailing-text truncation, first-object extraction, regex JSON
recovery, second-LLM repair, and retrying until valid JSON are rejected. Any
future use requires separate architecture authorization. If format becomes
necessary, **PROVIDER FORMAT REINTRODUCTION WOULD REQUIRE CONTEXT-PROOF AMENDMENT**.

## 6. Next authorization and gate sequence

### Acquisition outcome (2026-08-28)

The separately authorized acquisition of only `qwen2.5:7b` passed. Its frozen
local identity is Ollama `0.32.1`, tag `qwen2.5:7b`, digest
`sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
The complete evidence record is
[Qwen2.5 model acquisition](TASK-016-LOCAL-DEEP-ANALYSIS-QWEN25-MODEL-ACQUISITION.md).
This does not approve tokenizer reuse/parity, raw-profile parity, feasibility,
or implementation.

**MODEL ACQUISITION: COMPLETE.** The later single-model authorization named only
this exact tag/source, prohibited fallback, and captured disk/resource, full
digest, and license evidence. Its outcome is frozen above and in the acquisition
record; no further model acquisition is authorized by this document.

**TOKENIZER ACQUISITION: YES.** Qwen3 artifacts cannot be reused. Freeze exact
Qwen2.5 tokenizer revision/artifact hashes, offline engine/distribution
hash/license, and expected pairing; forbid network/cache fallback.

Reusable contracts: Evidence Registry, A1, scoring authority, KnowledgeContent,
strict parser/grounding/KG2, TrustedLocalDeepAnalysisSuccess, no persistence,
Cloud-off cutover, TASK-016D handoff concepts, and 16K/2048. Candidate proof
migration is **MEDIUM**: model/tag/digest, tokenizer identity, template/token
policy, raw parity, runtime evidence, A3/provenance values, and local fixtures.

1. Separately authorize and acquire only `qwen2.5:7b`; capture disk/resource,
   tag/digest, source, and license evidence.
2. Freeze exact Qwen2.5 tokenizer/offline engine and its new identity.
3. Prove raw-text token-ID parity for the acquired digest, `raw=true`, omitted
   `format`, and one exact Ollama version. **Raw-profile parity: YES.**
4. Reconcile MAX token/byte bounds before any MAX dispatch.
5. Separately authorize M1 Pro feasibility. **Feasibility gate: YES.**
6. A complete pass can inform a later implementation decision only; it cannot
   begin TASK-016D/E/F.

Early-fail sequence: tiny strict-JSON smoke; SHORT 2/2; MEDIUM 2/2; MAX 3/3.
Stop before the next tier after structural failure. Success is 100% required
whole-response JSON, closed schema, grounding, KG2, raw/no-format identity,
full-prompt token proof, and byte/resource gates; no malformed run is averaged.

## 7. Preserved state

`qwen3:8b` remains rejected only in the exact scope above. Implementation remains
unauthorized. TASK-016B remains closed and unchanged. TASK-016C remains closed
and unchanged.

**LOCAL DEEP ANALYSIS MODEL SELECTION ROUND 2 COMPLETE**

**NEXT MODEL CANDIDATE: qwen2.5:7b**

**NEXT MODEL ACQUISITION / VALIDATION GATE IDENTIFIED**

**LOCAL DEEP ANALYSIS IMPLEMENTATION REMAINS UNAUTHORIZED**

**TASK-016B REMAINS CLOSED**

**TASK-016C REMAINS CLOSED**
