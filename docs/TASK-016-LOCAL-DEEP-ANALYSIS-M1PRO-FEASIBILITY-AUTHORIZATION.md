# TASK-016-LOCAL-DEEP-ANALYSIS — M1 Pro Feasibility Authorization

Status: **FUTURE BENCHMARK ONLY — NOT PROVIDER IMPLEMENTATION AUTHORIZATION**

This permits a later, separately approved, local benchmark/smoke only. It does not permit production code, migrations, a model fallback, cloud calls, telemetry, persistence, cache work, or TASK-016D/E/F.

## Candidate and prerequisites

The target is one Apple M1 Pro machine class with one local Ollama process and no parallel generation. Its only candidate is qwen3:8b with full manifest digest sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41. The runner must manually prove that exact tag/digest before testing; it must not pull, alter, or substitute a model. Record the strict normalized Ollama SemVer and use the loopback-only API contract in the main authorization.

## Required request and corpus

Use exactly the frozen endpoint, POST /api/generate, JSON-schema format, temperature=0, seed=0, stream=false, think=false, num_ctx=16384, num_predict=2048, 300-second deadline, and no tools. Run short, medium, and maximum-envelope prompts where composed prompt plus format schema equals 12,288 UTF-8 bytes. Include dense ASCII, Han, and multi-byte Unicode evidence. Inputs must contain no personal secrets and may not invoke cloud or remote services.

## Measurements and pass/fail

Record runtime version, tag/digest proof, model-load success, peak/observed memory when mechanically available, prompt acceptance, wall-clock duration, response bytes, done value, and strict KnowledgeContent schema plus deterministic semantic/grounding outcome.

PASS requires all:

1. no OOM, process death, or provider-side context truncation at maximum envelope;
2. short, medium, and maximum inputs each finish within 300 seconds with a completed response that passes strict schema and deterministic validation; and
3. think=false, structured format, seed, and stream=false work together for this exact model/runtime pair without extra output or transport-contract violation.

The PRD has no latency SLO, so none is guessed. Any failure, missing evidence, wrong digest, or incompatibility is a **MODEL SELECTION BLOCKER**. It authorizes no fallback. A pass alone does not authorize provider implementation: a later design amendment must freeze the exact accepted Ollama SemVer set/range and record the evidence.
