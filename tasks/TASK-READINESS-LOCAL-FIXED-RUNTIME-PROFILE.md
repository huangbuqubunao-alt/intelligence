# TASK-READINESS-LOCAL-FIXED-RUNTIME-PROFILE

Status: BLOCKED_ON_R13_INDEPENDENT_ACCEPTANCE. No product writing before root dispatches the exact accepted base. Next serial engineering slice, no real model generation.

## Goal

Remove reliance on automatic runtime batch selection with a new immutable, unqualified profile. Keep existing profile/history bytes intact. This is the engineering basis for a bounded8192-budget evaluation, not an adoption of the old invalid LOCAL8 chain or permission to reroll its failed cases.

New ID: `local-grounding-qwen35-9b-fixed-runtime-v2`. Model/digest/Ollama0.40.1/prompt/schema/native thinking/sampler/seed/ctx16384 unchanged from existing v1; explicitly fix `num_batch=512`, output cap8192, keep timeout300 seconds and response limit1,000,000 bytes. Complete input bound must be≤8191; with current framing+90, cap content bytes at8101, retaining existing12288 request-byte cap. No per-case overrides, context shifts or truncation. Budget does not guarantee completion within300s: timeout remains a genuine failure. All exact new limits belong in the new projection/hash. Old v1 projection/options/capacity/6144 limit must be byte-identical.

## Scope and isolation

Expected files: local_distillation_profile.py (new immutable allowlisted variant), local_model_capacity.py (trusted per-session profile binding instead of hardcoded old ID), distillation.py (response validates the resolved profile output cap; no relaxed finish conditions), focused profile/capacity/transport/history tests, own report. No state/Schema/authorization reader/resource/harness/factory/UI/dependency/config changes in this slice. Old v1 qualification reader and harness must refuse new variant receipts; do not make generic external values authoritative. Production factory selection stays unchanged and unqualified. New variant may only be used for offline engineering or separately reviewed load-only capacity diagnostics; zero generation.

Reuse DIRECT installed stdlib/current request builder and profile resolver/session/strict runner observer. Official fixed commit cf2a313a298066d572c36812e5ad30a21c0db13b: server/routes.go explicit num_batch disables auto; sched.go explicit change triggers reload; llm/llama_server.go maps to-b/-ub. Sources and hashes in independent OpenCode handover audit. Do not widen runner acceptance or require service restarts per task.

## Done criteria

- Golden v1 projection/request/execution/history compatibility, unknown IDs reject; new v2 deterministic distinct identity and full contract,0qualification. Existing failed records retained.
- Exact same new options in request/load probe/host validation/ready/arm/consume. Reject cross-profile/value/request reuse, expired proof, changed host/runtime, concurrent heavy activity, unknown runner, wrong batch/context, foreign thread and consumed claims before any generation. Existing lease/restore/quiescence constraints unchanged; do not derive model eligibility from options.
- Strict response gate uses trusted fixed profile cap: old outputs6144 still reject; v2 cap8192 rejects exact8192/length/timeout/donefalse/unknown; missing/forged/boolean/negative metadata rejected, R13 durable failure intact, no response repair. No new receipt/qualification authority; V1harness still cannot run new variant.
- Author tests/compile/Ruff/strictmypy/affected old+new profiles, legacyCloud/no-new/history/restore invariants and diff check; independent review. Genuine cold/warm/reload load-only proof requires freshly verified resources and separate frozen protocol; not inferred from fake transports or official source. Root currently RAM6.213GiB below old~8.1–8.7GiB gates, so0load/0generation until safe resources exist.

After clean reviewed integration: finish full long-input persistence/closure protocol already specified, freeze original4+unseen holdouts and substantive LOCAL positives, create version-specific qualification/harness path, then strictly bounded once-firstFAIL real validation. No automatic reuse of old case1 receipt, no skipping first failed case. Real model qualification and all ordinaryGUI/BackupRestore/full regression gates remain mandatory before main adoption.
