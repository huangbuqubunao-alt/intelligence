# Phase 11 — public creator Following

Authority: owner's Phase 11 continuous goal, 2026-10-04.

## Infrastructure audit

| Existing component | Classification | Phase 11 use |
| --- | --- | --- |
| source_subscriptions, timestamps, enabled | REUSE / ADAPT | Canonical creator source and pause |
| source_video_links | REUSE | Discovered Content membership |
| DurableProcessingOrchestrator / Source Runs | REUSE / ADAPT | Existing queue, active-run reuse and restart |
| DurableSourceRunWorker | REUSE | Application-owned worker; no second scheduler |
| Source policy / Intelligence / Topic | REUSE | Preserve admission, never infer Topic from creator |
| channel_cursors | REUSE for YouTube | Channel identity and scalar cursor lack observed-identity ledger |
| BilibiliContentProvider / SourceContentPublisher | REUSE | Canonical BV, immutable captions, extractive Summary/Evidence |
| BackupRestoreService | REUSE / ADAPT | Whole database, tracking validation |
| Knowledge Delta | REUSE / ADAPT | Normal completed Content, significant source health only |
| demo-v1 source statuses / filters | DEMO-ONLY | Cannot confer production tracking authority |
| blanket Bilibili check rejection | OBSOLETE for creators | Retain manual VIDEO_URL semantics |
| page position as watermark / unsigned remote URLs | UNSAFE | Never use as verified authority |

## Contract

Provider BILIBILI, kind CREATOR, positive numeric mid; source id
`bilibili-creator-<mid>`, canonical `https://space.bilibili.com/<mid>`.
Display name is separate mutable public metadata. Profile inputs are narrow
HTTPS space URLs (root or /video, permitted tracking queries), or numeric ids.
Follow-from-Content reads the verified immutable metadata snapshot's uploader id.

Following establishes a bounded baseline without importing history. Publication
timestamps at/before follow time never become new events merely through pinning,
reordering or restore. Canonical BV identities are observed durably. New videos
automatically create/reuse normal Content; acquisition uses the Phase 10B path.
No routine refresh rewrites READY captions or Evidence. No caption is honest
unavailability, never acoustic fallback. Multipart first-part and two-hour bounds
remain inherited. Production acoustic ASR and Deep Analysis remain NONE.

## Incremental safety and bounds

Generic tracking state, check receipts and observations need migration 034.
Only a successfully parsed bounded discovery scan may advance verified state;
partial network failure retains the previous verified watermark. Observed items
and pending enrollment persist atomically. Enrollment can retry independently;
one BV remains one Content even after crashes or manual import.
Pagination offsets are traversal hints, never proof of completeness. Exceeding
safe coverage reports UPDATE_GAP / CHECK_INCOMPLETE and preserves the verified
frontier. Later checks process durable pending items within their normal budget.
Exact network/page/enrollment/cooldown bounds will be recorded with implementation
evidence. Provider requests share Phase 10B TLS/DNS/allowlist/body/retry/concurrency
limits. Risk control is surfaced and cooled down, never bypassed.

## Lifecycle and product

Reuse in-app Source Runs for Check now and stale-source checks when Following is
opened/resumed, with durable cooldown and active-run reuse. Paused sources cannot
check; resume retains baseline. No daemon, cron, launchd, notification center,
cloud LLM or paid service requirement. Following shows check time, health,
actual discoveries, pending work and ordinary linked Content. No-op checks do
not produce knowledge changes. UI supports zh-CN/en and 320px.

Tracking state is portable database authority, not an HTTP cache. Restart and
restore retain canonical identity, observations, pending enrollment and last
verified state. Offline failures preserve last successful checks and stored
Content/Summary/Evidence. Restore rejects corrupt tracking rather than resetting
the source to zero. Remote deletion never erases portable historical authority.

Deferred: always-on agent, notifications, explicit recent-history import,
multipart expansion, duration expansion and versioned caption refresh.
