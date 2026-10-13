# TASK-READINESS-QWEN35-QUALIFICATION

- Status: READY for isolated harness and pre-output freeze only.
- Implementer: /root/caption_resume; Reviewer: /root/intel_bounded_review.
- Base: codex/task-end-to-end-user-readiness@08e02e2.
- Worktree: /Users/hua/Documents/yia-worktrees/readiness-qwen35-qualification
- Branch: codex/task-readiness-qwen35-qualification

## Goal, approval and done criteria

User explicitly approved MODEL_REPLACEMENT_PROPOSAL.md on 2026-10-13: “批准固定权重隔离下载与验收”. Root is downloading only the pinned official qwen3.5:9b-q4_K_M manifest 56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90 using installed Ollama 0.40.1, with >10GiB post-download free-space preflight. This task prepares a truthful research-only actual-model harness, freezes exact code/profile/input/policy before any output and reports readiness for independent review. No inference until root confirms installed manifest and all blobs and pre-output review approves.

## Exact scope

New isolated research script scripts/qualify_readiness_qwen35_intelligence.py, focused research-harness tests if needed, new profile/freeze documents under docs/validation/end-to-end-user-readiness, this task copy and handoffs/TASK-READINESS-QWEN35-QUALIFICATION.md. Reuse existing research setup/strict service/evidence/ledger; do not modify production src, existing frozen corpora/hashes, dependencies, config, old script history or formal data. Private source fixture DB must be the explicit isolated root runtime, not owner data; no credentials or cloud. Never inspect or publish private thinking.

## Reuse decision and fixed profile

DIRECT installed Ollama loopback adapter, ordinary qualification seam, parsers/resolver and existing frozen input. ADAPT a research-only subtype with truthful actual model/tag/digest, unique frozen profile/version; production-qualified remains false. Do not masquerade as qwen3:8b, rewrite model output or bypass production authority.

Use the official consistent non-thinking general-task profile: think=false, temperature .7, top_p .8, top_k 20, min_p 0, presence_penalty 1.5, repeat_penalty 1.0, fixed seed 20261013. Keep actual context8192/output4096 limits. Reuse existing v5 prompt and strict wire schema without synthetic calibration or additional output repairs. Official source: https://huggingface.co/Qwen/Qwen3.5-9B (Sampling Parameters / Best Practices); exact runtime support must be verified without upgrading.

Original real corpus V2 SHA a7c96ee6b84aee6b8e492348b9f4f190d7c9f6f14241b25e533532bc4dcb82cb and original corpus V1 SHA cededc0061c43029e28a867bbaeab5ae5691c3e6a998997ace855eebb6dd37f3 unchanged. Freeze real EN/ZH positive and original no-new15/injection controls, expected semantic policy and ordering. Original non-AI positive applicability conflict is retained and clearly labelled; no altered expectations to obtain a pass.

## Evidence and coordination

Per case fresh directory/DB, one actual call maximum, exact request/final response/raw result retained, repeated service continuation idempotent. No new calls after decisive fail; no reroll or unsupported-runtime upgrade. Protocol success never substitutes semantic acceptance. Test/syntax/Ruff/mypy/diff as applicable without dependency installation; commit bounded harness/freeze and STOP for pre-output review and root download receipt. Only after review and root start instruction may execute real generation. Final ordinary factory qualification, save/topic/source/GUI/restore and adoption remain separate gates.

Parallel now: retired-subtitle reviewer, root weight download (not inference). Waiting: raw-capture writer awaits retired-subtitle integration, then runs separately; no overlapping writes of production core. No main merge, final task DONE or production qualification claim.

## Implementer evidence (2026-10-13, not task DONE)

The parent explicitly approved research-only exact positive marker decoding for truthful pinned9B after discovery of the ordinary8B marker discriminator. The subtype removes only `result`; ordinary claim/Evidence and unchanged complete NO_NEW checks run afterward. No product source changed. Original corpora still retain8B historical metadata and failures; the new external profile records9B rather than aliasing them.

Prepared harness/profile/pre-output freeze with40 passing no-network contract/ordinary Ollama tests, Ruff, strict mypy and diff check. Actual provider inference remains0. Parent reported both installation and independent installed-blob reviewPASS; this does not authorize execution. Script default modes require explicit `--prepare-only` or an externally sealed per-case receipt. Pre-output review must inspect each sealed prepared DB/data/VerifiedInput before root gives that case a start receipt. No preparation of the four actual qualification attempts has run yet.
