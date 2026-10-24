# TASK-READINESS-CONFIGURABLE-MODEL-BINDING

Status: INTEGRATED_ENGINEERING_SCOPE, root integration checks passed. Same ordinary-user remediation Goal; no new product phase.
Dependency: accepted b6adac2 core and accepted R2 product fix 0f1e194, independent c0df0ac APPROVE. Root whole5940 run remains on frozen pre-fix source; this task uses a separate worktree and cannot mutate that source.
Base: latest root documentation baseline plus the exact accepted 0f1e194 cherry-pick, supplied by root in the execution package.

## Goal and done criteria

Correct the observed 0.40.9 disk/API versus nominal 0.40.6 binding error, and centralize model/runtime selection so compatible models share the existing execution lifecycle. User explicitly accepts necessary smaller models and configurable local/cloud providers, forbids large redevelopment, and authorizes necessary isolated fixes without repeated file approvals. Configuration never grants qualification or paid-cloud permission.

Deliver one immutable, finite, central model/runtime descriptor and narrow resolver/adapter substitutions. New actual runtime identities receive new profile IDs and independent qualification. The previously persisted profiles, wire/hashes, receipts and old reader behavior remain intact; never relabel old 0.40.6 proofs as 0.40.9. Unsupported or unverified configurations remain usable for reading/importing existing data and receive precise setup/compatibility/resource/qualification feedback. They cannot execute under another model's authority.

## Bounded implementation

- DIRECT reuse existing AppSettings/local_analysis, provider adapters, InstalledCandidate/catalog, profile resolvers, native capacity, qualification cache, execution/lease/cancel/Backup framework. No parallel lifecycle, scheduler, framework, dependency, Schema, storage-table or codec changes.
- Centralize metadata/resolution in existing local_distillation_profile.py (or one narrowly named pure sibling if cleaner): resolve model binding from provider/model/digest/runtime; derive supported execution profile, paired-long profile and actual runtime descriptor. Do not add fields to old profile serialization or InstalledCandidate/asdict/catalog_hash that change old bytes.
- Preserve old short/long IDs including historical 0.40.1 and nominal 0.40.6 profiles. New 0.40.9 execution must bind actual API version AND exact daemon/runner/binary bytes from the same observation, not an old server version plus new disk files. Unknown versions, changed binaries, metadata/slot mismatch remain fail-closed before execution.
- Exact current bytes and official sources are recorded in ACTUAL_RUNTIME_IDENTITY_CORRECTION_2026_10_24.md and root ignored qwen35-4b-once-20261024/actual-runtime-0409/runtime-contract.json. Source Ollama5e31438d5d2223d8338595b366b7434ef3539708 / llama.cpp a37cc46104eb50900d5ab4a9ba02a0abdac039db. Renderer/parser bytes equal prior source; actual native evidence remains mandatory.
- Fixed request semantics remain: complete genuine input, original schema/semantic standards, short context16384/output8192/300s and long32768/output6144/300s, batch512, current original sampling, native full true/true tokenization and N+P+2<=actualC, one-shot lease/claim/consume. No budget tuning, output repair, prompt rewrite or new model calls.
- Cloud routes/auth/privacy/budget/cost are preserved. Do not generalize cloud execution or add new providers in this task. Existing configuration is the model-independent boundary; installation alone is not quality proof.
- Root's 4b diagnostic is pending. It is diagnostic only. You may correct actual runtime and central metadata now; do not add an executable 4b profile until root supplies its actual diagnostic decision. A failed model stays unqualified. If approved for further original qualification later, only add its independent metadata/profiles through this central adapter; do not copy business flows.
- Initial expected files: local_distillation_profile.py, long_distillation_profile.py, local_intelligence_catalog.py, local_native_capacity.py, local_model_capacity.py, local_distillation_qualification.py, runtime_composition.py, distillation.py, long_distillation_execution.py, long_distillation_persistence.py, local_api.py, local_intelligence_settings.py; only necessary minimal frontend App.tsx/types/copy and corresponding focused tests. Report an additional necessary boundary to root, not repeated user approval. No broad formatting/refactor. If this needs a business/state/Backup rewrite, stop and return a narrower proposal.

## Verification and handoff

First publish a bounded file/contract plan in your own handoff; inspect graph/source and original evidence. Syntax/type first; meaningful failing tests for observed old-version/new-binary mixing and configuration isolation. Preserve all failing evidence.

Prove actual version/binary pairing, old/current/unknown dispatch, per-model qualification isolation, model change affecting only new requests, old profile/hash compatibility, exact installed catalog hashes, capacity/lease/TTL/one-shot guards, unchanged cloud and WAIT cancellation/Backup semantics. No genuine model/network/cloud calls in implementation tests; all data isolated. Do not rewrite old tests merely to assert a new default: historical fixtures must remain historical, while current fixtures explicitly bind the actual new identity. Missing evidence stays denied.

Freeze source and run the complete affected backend group; frontend full/TS/build for UI edits; compile, Ruff src/tests/scripts, strict mypy and diff check. Preserve original checks, failures, source hashes and exact commands. Independent reviewer and root integration remain mandatory. Do not claim affected checks equal final whole-Goal regression or qualification.

Only own handoff may be written outside this task's product/test files. Commit scoped changes, report full SHA/cleanSTOP/limitations. No main merge, push, formal owner/config/credentials, qualification registry record, schema or dependencies.

## Acceptance checkpoint, 2026-10-24

Final author88374923b29bc5d08b08dac597272b2f617d71fb independently reviewed
at67d45de55d40963a76082992f4c2a30484755dcc:9 complete affected files279PASS,
compile/Ruff/strictmypy121/diffPASS,547 source bindings and40 migrations intact,
registry empty. Earlier unconditional x86 implementation-library finding was
withdrawn using actual Mach-O/ARM64 evidence. Final runtime guard proves actual
ARM64 process/main mapping and handles real PS padding without changing complete
identity comparisons. This accepts the final corrected range, not the rejected
intermediate guard as an execution baseline. No model/04010 qualification or
Goal/publication acceptance follows. Both4b candidates failed; Q3 diagnostic is
separate and still requires independent preflight and one actual result.
