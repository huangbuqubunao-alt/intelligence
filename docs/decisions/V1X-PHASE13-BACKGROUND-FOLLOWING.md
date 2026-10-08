# V1.x Phase 13 — backend-owned automatic Following

## Authority and scope

Authority was read in order: PRODUCT_CONSTITUTION, V1_PRODUCT_SPEC,
V1_IMPLEMENTATION_ROADMAP. None defines a formal V1.x Phase 13; historical
M13 is the seven-day dogfood exercise. The owner's current continuous goal
therefore supplies the Phase 13 contract. Its sole-executor, isolated-worktree,
validation and conditional main adoption instructions supersede historical
workflow restrictions. This work adds automatic checks to accepted Following,
without starting Phase 14 or withdrawing any accepted Phase 12 capability.

## One runtime and one durable authority

`serve-api` starts the existing Source Run worker. That worker now also admits
one due Following command. Browser/window closure does not stop checks while
the backend remains alive. Backend termination stops scheduling; the next launch
reloads SQLite and checks only due work. The authority documents do not require
operation without the backend, so no LaunchAgent, second daemon or service
installation was introduced. This lifecycle is stated in the Following detail.

Schema remains **34**. Existing `source_tracking_state.next_check_at` owns the
deadline; enabled state, health, verified frontier, observations, source_checks
and source_runs retain their existing meanings. There is no schedule table,
cron setting, migration, lease framework or timer-job cache. The existing
command identity records automatic origin as `following-auto:<source>:<due>`;
its existing MANUAL_CHECK_NOW trigger is a compatibility implementation detail.
Manual commands retain P0 priority; automatic commands use P1. Both enter the
same atomic active-run admission and trusted tracker.

## Wake and concurrency

The worker clears its Event before reading authority, then drains useful work.
Follow, pause/resume, commands and Backup protection release wake it. With no
eligible source or queued work it parks indefinitely. With future work it waits
until the nearest durable deadline, capped at five minutes to reconcile clock
changes and Mac sleep/wake. There is no one-second/half-second idle scan loop.
An idle authority read does not count as active Backup work. Actual admission
and execution recheck the protected gate.

One worker execution lock gives concurrency **one**, including concurrent
run_once callers. Existing SQLite active-run admission, the unique RUNNING
source-check index and provider slots prevent manual/background overlap.
Per-source observations and existing Content identity uniqueness suppress
repeated enrollment; no new frontier authority is introduced. Pausing is
rechecked inside the claim and before observation/enrollment. A paused source
has no automatic wake deadline. Resume uses its existing deadline: due sources
reenter promptly, future sources wait. Baseline is not reset and no source is
silently unpaused.

## Policy and failures

The accepted normal interval remains **15 minutes**, measured from completion
for automatic checks. Consecutive automatic failures persist future deadlines:

| Outcome | Initial delay | Cap / behavior |
| --- | --- | --- |
| Network unavailable | 1 minute | exponential, capped at 1 hour |
| Provider rate limit | 15 minutes | exponential, capped at 4 hours; provider cooldown still applies |
| Provider/parser contract error, including NOT_FOUND | 1 hour | exponential, capped at 24 hours |
| Unexpected local processing exception | 1 hour | settle RUNNING checks/run as failed, retain proved frontier |
| Slot contention | 1 minute | defer, no fabricated check or success |
| Untrusted/corrupt state, risk/access refusal | needs attention | no automatic provider requests; explicit manual rules remain |
| Success | 15 minutes | normal next check |

Background network failure does not arm an unrelated provider cooldown. The
accepted Phase 12 transport rediscovers the system proxy on each operation, so
later network recovery needs no process restart. Manual OFFLINE retry remains
available after five seconds; `manual_check_at` is a derived API projection,
separate from the durable automatic deadline. Repeated failures remain visible
in source health/check history. Provider enumeration failure never fabricates a
baseline/frontier. A previously verified enumeration may retain its proved
frontier and pending acquisition ledger under the accepted tracker contract.

Startup reloads persisted Source Runs, including interrupted RUNNING work,
through the same gate. Existing ten-minute stale-check recovery records
INTERRUPTED, never success. An unexpected tracking exception settles the owning
run and defers retry. Explicit model-analysis runs retain their existing failure
semantics. SIGTERM/SIGINT use the normal CLI shutdown path; worker stop wakes the
Event and joins the current bounded check before replacement/exit.

## Backup, Restore and cost

Archive transactions and stage/cancel/confirm protection prevent new automatic
execution during protected windows. Active work remains visible to existing
quiescence checks and drains; an idle scheduler does not permanently block
readiness. Confirmed Restore prevents further worker admission. The CLI closes
the old HTTP server, drains/stops its worker, applies Restore before constructing
fresh repositories, then starts a fresh worker. Every scheduling decision reads
that restored authority. No cached source jobs survive replacement.

Automatic tracking uses the accepted feed/observation/enrollment path. New
YouTube Content uses verified transcript acquisition and the local extractive
Summary. Tracked discovery returns no model-processing candidates to Source
Run scoring/distillation stages. No Scoring, Deep Analysis, Research, paid cloud
routing or model factory is enabled by scheduling. Deterministic tests deny
model factories and prove timed transcript/Summary enrollment once with zero
distillation execution checkpoints. No consent or model qualification rule was
changed; production ASR and Deep Analysis remain NONE.

Phase 12 provider/network/parser/trust/enrollment code, all migrations and
production dependency manifests are byte-identical to the starting main. TLS,
SSRF, OS proxy authority, no environment proxy authority, Fake-IP boundaries
and no cookie/login access remain unchanged. Bilibili Creator Following and
public captions remain unavailable; explicit public-video import remains.

## Product boundary and acceptance

Following detail adds next automatic check and explains the running-app
lifecycle. Manual network retry uses its own derived eligibility, so automatic
backoff does not disable the accepted five-second Retry. Existing health,
checking, pause/resume and Content views carry results. No administration
console, settings, cron, notification platform or provider expansion was added.

Acceptance evidence and the live gate are recorded in
[Phase 13 validation](../validation/phase13/REPORT.md). Feature development must
freeze for real-user daily usage after full acceptance and verified main push.
No Phase 14 work is authorized by this decision.
