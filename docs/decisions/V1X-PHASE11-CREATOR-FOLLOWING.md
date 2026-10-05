# Phase 11 — public creator Following

Authority: owner's Phase 11 continuous goal, 2026-10-04.

> **Superseded for Bilibili by
> [V1X-PHASE11R-BILIBILI-REALWORLD-REMEDIATION](V1X-PHASE11R-BILIBILI-REALWORLD-REMEDIATION.md).**
> This record describes a mechanism validated against offline fixtures. Phase 11R
> ran that same mechanism against the real public provider and measured 0 / 10
> reconnaissance checks and 0 / 3 fair single-shot probes accepted — all raw
> `-412 request was banned` — and 0 / 8 public videos exposing any caption.
> Bilibili **creator Following is therefore withdrawn from pilot UX**, and the
> caption acquisition described below did not succeed in the real world. The
> architecture below is retained rather than deleted, and is re-enablable by one
> constant if the provider ever permits it.

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
The immutable video metadata must independently confirm the creator and a
publication time after following; a contradictory list timestamp cannot admit
historical Content.
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
The initial baseline inspects one 30-item page. Later checks inspect at most
three pages / 90 entries and enroll at most five pending videos, oldest-first
with canonical BV as tie-breaker. Every pass revisits the head; recovery offsets
continue deeper coverage but never advance the trusted frontier themselves.
Changed page totals, short pages or contradictory identities fail verification;
overlapping pages cannot claim completeness. A creator list too large for a
complete bounded scan remains explicitly UPDATE_GAP, even when its known pending
items have been enrolled. No assertion of complete historical coverage is made.

Checks have a 180-second work-admission budget; a bounded in-flight acquisition
may finish after that budget. At most 19 logical provider requests / 49 HTTP
attempts can be admitted per check: card plus three pages use one attempt each;
five videos retain inherited metadata/player/caption retries (at most three).
The accepted 10-second HTTP / three-second DNS timeouts, 256-KiB metadata and
2-MiB caption bodies remain. All requests share the provider's two request slots
and 0.5-second pacing; creator checks share one nonblocking check slot. The
durable source cooldown is 15 minutes. HTTP rate/access responses also cool the
shared provider budget; public JSON risk control cools it for 15 minutes.
No request identity rotation, cookies, signature workaround or CAPTCHA path.

## Lifecycle and product

Reuse in-app Source Runs for Check now and stale-source checks when Following is
opened/resumed, with durable cooldown and active-run reuse. Paused sources cannot
check; resume retains baseline. The Following list refreshes local state only
while an existing check is active. No daemon, cron, launchd, notification center,
cloud LLM or paid service requirement. Following shows check time, health,
actual discoveries, pending work and ordinary linked Content. No-op checks do
not produce knowledge changes. UI supports zh-CN/en and 320px.

Tracking state is portable database authority, not an HTTP cache. Restart and
restore retain canonical identity, observations, pending enrollment and last
verified state. Offline failures preserve last successful checks and stored
Content/Summary/Evidence. Restore rejects corrupt tracking rather than resetting
the source to zero. Remote deletion never erases portable historical authority.
An expired ten-minute check lease becomes an INTERRUPTED receipt, preserving
already committed observations and pending enrollment. Backup requires quiescent
checks. Both the source identity/ledger and enrolled Content's immutable uploader
identity are verified; a forged cross-creator association is rejected. Migration
034 is atomic, checksum-verified and preserves every accepted migration, including
the intentional absence of historical 029.

Update counts are cumulative discovered Content, not unread notifications.
The accepted per-video snapshot source remains in persistence for Content
authority. Once associated with creator tracking it is grouped under that
Following in the list, rather than appearing as an additional manual-import
Following row. This is a derived view relationship; Content identity and source
authority are unchanged. Historical/manual videos outside creator discoveries
retain their existing explicit-import presentation.
No acknowledgement inbox is invented. Captionless or unsupported videos expose
processing/attention state. Only verified existing Intelligence powers its
Following filter. Source health enters Knowledge Delta through the accepted
repeated-failure/recovery semantics; a successful no-change check emits no
knowledge event. Public discovery alone never dispatches a model, invents a Topic
or changes Intelligence admission. Research selects discovered Content normally.

Deferred: always-on agent, notifications, explicit recent-history import,
multipart expansion, duration expansion and versioned caption refresh.
