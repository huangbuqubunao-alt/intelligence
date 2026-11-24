# TASK-READINESS-LOCAL-REJECTION-ACCOUNTING

Status: DONE_ON_CANDIDATE. Root integrated as91b7f8c/418d7d5/b94f13f; root44PASS/38.77s, compile/Ruff/strict117/diff and exact reviewed source SHA all PASS. No main adoption. Implementer /root/local_rejection_accounting is clean STOP at 62ed4307690cab7d2bbecca5b475695f2e922784 (core ac2ea9d4585f3215b9f2330da4062f6fed95b1f5); Independent reviewer /root/local_budget_evidence_audit APPROVE e807c6b5038509c382db51626be952e014bd34ed; root reviewed full diff and evidence, accepts this narrow engineering scope only. Integration checks still required. Orchestrator: Codex root, resumed by explicit user handover 2026-10-20 19:23 CST. OpenCode run is paused; never execute its old permits or mutate its prepared databases.

## Goal and acceptance

Fix the genuine R13 local rejected-response accounting crash without changing model qualification or generation budgets. A completed but inadmissible response must produce honest durable failure accounting; unknown identity/usage/execution remains unknown and fail-closed. No invented provider/model, zero tokens, success, Evidence, receipt or cost. One claimed invocation is irreversible and never automatically re-dispatched. Restart, repeat request and backup/restore preserve these facts.

Base: a989873773c0f4018cc696930789566925e88c7c. Worktree: /Users/developer/Documents/yia-worktrees/readiness-local-rejection-accounting. Branch: codex/task-readiness-local-rejection-accounting. Implementer assigned by root; independent reviewer after clean submitted commit.

## Scope

src/youtube_intel/distillation.py, scripts/qualify_local_grounding_v1.py if needed for honest exclusive failure diagnostics, focused new/affected tests, own handoff and validation summary. Do not edit state.py, Schema, qualification resource, profile/budget, capacity gates, dependency/config/credentials, historical frozen inputs/results or production data. If the current state API truly cannot represent the safe outcome, report concrete invariant before expanding; do not weaken _validate_observed_usage. Reuse DIRECT existing transport-result, AMBIGUOUS accounting, SQLite transaction/claim, once audit writer and test fixtures; no dependency.

## Reproduction

Read .var/end-to-end-user-readiness/exec-plc-local-timed-zh-r4.log in root. validate_local_grounding_response raises KnownLocalDistillationResponseError without result at line2874. _dispatch_and_admit then finishes REJECTED_OUTPUT/invocation1/identitiesNone; state._validate_observed_usage correctly refuses. Same defect exists for malformed/oversize/nonmapping local HTTP responses. Preserve both original failed inv1 databases/logs untouched. Escalation JSON SHA256 09547fb436080db3e7c6760ce66b678f1b108a9a5c8da939677c419b951d3ba9.

## Required proof

Write failing regression first without changing assertions later: valid response identity+real counters with length/6144 cap, malformed/no identity, different actual model, missing/boolean/negative/unpaired usage, malformed JSON/oversize response, timeout/pre-dispatch ambiguity. Use fake local HTTP/transport in isolated tests, zero real generation. Known actual observed identity and reliable paired counters may be retained on rejected output, never copied from selection. Unknown observations use existing safe durable representation; ambiguity must not become success/zero invocation/cancellable/retryable. Test public result diagnostics are persisted and exclusive, raw thinking never read, no duplicate POST on continuation/restart/concurrent finish, no new Insight/Evidence, originals preserved. Test terminal known rejection vs unknown Backup behavior and exact all-row/all-DATA restore where applicable; cloud authorization/cost paths and existing no-new/wait cancellation unchanged.

Compile/type before test debugging. Run focused/new and affected local/Cloud/ledger/harness/restore tests, Ruff, strict mypy and diff check. Record exact commands/failures/results/source SHA. Product budget remains6144 and registryempty. No real HTTP/model/owner access. Commit scoped changes and own handoff, clean STOP; no main merge/task DONE/self approval. Root performs independent review and integration.
