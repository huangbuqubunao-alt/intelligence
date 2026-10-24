# TASK-READINESS-CONFIGURABLE-MODEL-BINDING

Base: 8cff49769d9cc648a9c96971b85fc3cbabe80d1a. Implementer /root/configurable_model_binding; isolated worktree only.

## Contract and bounded implementation plan

Goal: fixed business framework, central immutable model/runtime binding, exact real 0.40.9 version/binary pairing. Configuration is not qualification. Done requires preserved historical profile bytes/catalog hashes; exact finite dispatch and per-profile qualification isolation; no changes to cloud, storage, lifecycle, budgets or evidence rules; affected tests and static checks passing; independent review remains required.

DIRECT reuse existing AppSettings, InstalledCandidate/catalog, profile resolvers, Ollama transport, LocalCapacitySession, qualification authority, manual execution, cancellation and Backup. No new dependency, Schema, scheduler or business framework. Official source reference: Ollama 5e31438d5d2223d8338595b366b7434ef3539708 (MIT), llama.cpp a37cc46104eb50900d5ab4a9ba02a0abdac039db (MIT); previously reviewed qwen3.5 renderer/parser behavior, no copied new third-party implementation. Runtime observation: root ACTUAL_RUNTIME_IDENTITY_CORRECTION_2026_10_24.md and actual-runtime-0409/runtime-contract.json.

1. Keep 0.40.1 and nominal 0.40.6 profile descriptors, wire, IDs and catalog entries unchanged. The old nominal 0.40.6/new binary mixture is explicitly unavailable for real host verification; do not invent its missing historical dylib hash.
2. Add finite independent 0.40.9 short/long IDs, deriving unchanged prompt/schema/budgets/options. Add an immutable central runtime/model binding, exact version + daemon/runner/library hashes, profile pairing and finite compatibility resolver in local_distillation_profile.py. No executable 4b profile before root decision.
3. Substitute narrow profile-family and pairing checks in long_distillation_profile.py, local_native_capacity.py, local_model_capacity.py, local_distillation_qualification.py, runtime_composition.py, distillation.py, long_distillation_execution.py, long_distillation_persistence.py and local_api.py. New catalog entry only; InstalledCandidate shape/hash serialization unchanged. Use candidate runtime at production construction, never let unrelated qualification replace user configuration.
4. Preserve unknown/missing identity refusal, actual native full-token/slot capacity, one-shot TTL/lease/claim and per-model qualification binding. No real model load/generation or external provider request in this task.
5. Add focused engineering tests for real-version/binary mismatch, exact historical hashes, new finite dispatch, model/runtime isolation, current TTL/claim and catalog compatibility. Run syntax/types before affected regression. Full frontend checks only if UI changes are necessary. Freeze source/hash and retain failures/logs. Reviewer/root integrate after scoped clean commit; no main/release actions.

Status: plan published before product edits. Root confirms rejecting old mixed real execution while preserving historical readers.

## Continuation writer /root/model_diagnostic_qa_writer

Original preflight bytes retained under `.var/resume-snapshot-20261024/`; this continuation appends only. Confirmed actual4b original-positive diagnostic FAIL/NO_NEW; no executable4b profile will be added. Scope remains central immutable9b runtime binding plus narrow resolver substitutions. Necessary exact API pairing belongs in existing LocalCapacitySession: carry configured base_url, verify observed server PID owns its loopback listener and mapped executable identity, read exact version with unchanged HostObservation around it. No business queue/state/Schema/Backup change. Plan uses incremental implementation and test-driven-development skills; freeze original profile/catalog goldens before edits, reproduce missing actual0409 binding, then implement pure dispatch first.

### Increment 1 — pure finite identity

New immutable `ModelRuntimeBinding` centralizes exact model/digest/runtime, paired short/long identities, binary hashes and official source commits. Added independent0409 shortv4/longv3; old0401/0406 descriptors remain unchanged. Nominal0406 binding is explicitly history-only and `runtime_binary_hashes` denies it rather than inventing an old dylib identity. No factory/session execution changes in this increment.

Evidence `.var/model-binding/`: historical-freeze.json captured all prior short projections/long wire/catalog fields+hashes before edits; pure-red.log6 actual missing-resolver failures; pure-green-initial.log79PASS13.09s including entire original current-profile and long-profile suites. Strict mypy121PASS; focused Ruff PASS after only new test import/layout fixes; diff check PASS. No models/network/registry/owner actions. Followup adapter/session/qualification/UI substitutions still pending; this incremental commit is not acceptance or execution authority.
