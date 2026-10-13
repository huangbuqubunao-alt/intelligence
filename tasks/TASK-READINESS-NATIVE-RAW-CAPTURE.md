# TASK-READINESS-NATIVE-RAW-CAPTURE

2026-10-13 补充具体授权已收到：“批准该精确补充范围，继续实施和验收”。
按 NATIVE_RAW_CAPTURE_ADDENDUM.md 将同一 owned pre-stage 边界扩至实际接受的
timed primary 或单次 VTT/SRT winner，每次最多两个 capture。原身份、租约、
CAS、未知文件拒绝、零重复读取、authority rollback 与全部DATA恢复断言保持。
实现者 /root/source_context，Reviewer /root/intel_bounded_review。当前独立树
readiness-native-raw-capture@c5da5e8 保留既有 RED，不重置。

- Status: IN_REVIEW (bounded implementation and checks complete; reviewer/root acceptance pending).
- Implementer: /root/source_context; Reviewer: /root/intel_bounded_review.
- Base: codex/task-end-to-end-user-readiness@c5da5e8.
- Worktree: /Users/hua/Documents/yia-worktrees/readiness-native-raw-capture
- Branch: codex/task-readiness-native-raw-capture

## Goal and precise approval

Fix the actual native-caption Backup/Restore P1: 71 tables identical, DATA4→3 because first accepted JSON3 was not indexed. Preserve original FAIL and old history. User explicitly approved NATIVE_RAW_CAPTURE_PROPOSAL.md on 2026-10-13: “批准该精确隔离捕获与恢复验收范围”. Read the full exact proposal in root docs/validation/end-to-end-user-readiness; it limits this task. Retired known-failure dependency b9bb62c8 and independent 3d63b468 have been integrated and independently approved; current root c5da5e8.

## Allowed scope and reuse

Only transcripts.py, state.py, integration test_subtitle_provider/test_runtime_composition and relevant existing Backup/Restore tests, focused additional test files as needed for these exact contracts, task/handoff and approval proposal copy. DIRECT existing Artifact/SQLite/CAS/owned leases/source identity/raw validation/Backup gates and native format adapters. No new dependencies or Schema. Do not change production BackupRestore/runtime_composition/API/frontend/ASR tuple-bound code, manifest, authorization/fees/Cloud or formal data/config.

## Done criteria

Owned pre-stage capture fixes durable first-raw identity/hash before alternate fetch, with immutable stable capture-role key independent of body hash. Capture grants no provider/job success, timed transcript, Evidence or Summary. Normal/explicit-repair completion accepts only the exact bound extra capture while preserving winner/canonical authority. Do not promote existing unknown unindexed files via expected_hash=None or recalculate them into trusted history. Missing/corrupt files and all unknown states fail closed, preserving history and the original capture hash.

Cover hash-first/not-yet-written windows, same-byte controlled recovery, valid-but-changed bytes, malformed bytes, owner/provider/job/source/policy/path/hash mismatch, concurrency, live/expired leases, 429/unknown alternate, rollback/restart/idempotence, repeat completion and exact full DB + ALL DATA files Backup/Restore. No weakened assertions or indexed-subset-only comparison. Previous successful historical tasks do not revive, and prior lost bytes are not fabricated. Rolling VTT normalization is explicitly outside this scope.

Run focused and expanded relevant tests, syntax/Ruff/strict mypy/diff checks, exact ASR tuple recomputation and local transcript regressions as affected. Then commit bounded code/handoff, stop for independent review; root runs final whole regression and fresh real GUI Backup/Restore acceptance. No main merge, production qualification or final DONE claim.

## Coordination

Parallel now: research-only Qwen35 harness freeze (no production core writes, no generation before root permission), root exact pinned-weight download, and independent review when ready. Waiting: completed raw capture review/integration before final GUI/full backend; no shared core files with the research harness. All tests use isolated temporary DB/DATA.
