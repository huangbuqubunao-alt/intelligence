# Phase 13 self-review and fixes

The owner explicitly designated one sole engineering executor. These are four
self-reviews, not independent-agent sign-off. No agent was spawned.

## Product

The backend now schedules enabled, eligible, due Following sources without any
UI event. One existing worker owns execution; window closure is supported while
serve-api lives. No new settings, provider, capability, cron, notification or
product surface was introduced. Manual Check Now, pause/resume and existing
health remain. Next automatic check is visible and OFFLINE manual Retry retains
five-second eligibility. Root and workspace DESIGN.md describe this narrow
behavior; both designmd lint runs have zero errors/warnings. Eight bilingual
real-API responsive detail views and two Backup readiness views passed.

The required successful real NASA baseline/check is **not proved**: current
normal Mac SYSTEM_NETWORK feed acquisition returns NOT_FOUND. Alias resolution
succeeded for NASA and Google Developers; both feed attempts failed truthfully.
A bounded later comparison returned the same NOT_FOUND from candidate and
accepted main, with identical transport bytes. The owner confirmed the current
VPN/proxy path is the normal environment and instructed no settings changes.
No Phase 12 provider/network/parser change was made to bypass this condition.
This is an external live acceptance blocker, not evidence of a candidate-caused
regression. No failed baseline is presented as successful.

## Reliability

Reviewed worker admission/execution, durable due authority, active source-run
constraints, tracking claim/frontier/observations, failure settlement, startup,
Backup protection and CLI replacement/shutdown. Fixes from review/real runtime:

| Finding | Correction / external evidence |
| --- | --- |
| Provider slot BUSY could leave a past due deadline | durable one-minute deferral, subsequent success; red-review.txt |
| Corrupt tracking could keep due admission retrying | fail closed with STATE_INVALID health; red-reliability.txt |
| Unexpected tracking exception could strand RUNNING | settle tracking check/run FAILED and retry after one hour, without frontier fabrication; red-reliability.txt |
| Automatic network backoff disabled manual five-second Retry | derived manual_check_at and UI timer; frontend-red.txt |
| SIGTERM killed active CLI check without normal drain | signal-driven normal shutdown; child-process test now exits 0 with completed check; red-sigterm.txt |
| Synchronous tracking seam dropped automatic origin | propagate automatic flag; red-final-review.txt |
| Transient feed NOT_FOUND could permanently stop automatic checks | bounded provider-error retry and later recovery; red-transient-not-found.txt |
| UI lifecycle refresh could bypass automatic risk refusal | shared refusal policy in due admission/tracking, with three regression cases; red-automatic-refusal.txt |
| Idle schedule read could falsely block Backup | preflight durable work before active gate; deterministic slow-read/Backup test plus actual API archive/Restore pass; red-idle-backup.txt |

At most one worker run executes; manual and automatic admission reuse existing
active-run authority. Paused sources are excluded and rechecked during tracking.
Restart retains future deadlines and pause state; stale check recovery records
INTERRUPTED. Failure category delays grow/cap and persist; risk/untrusted states
stop automatic calls across every automatic entry point. NOT_FOUND retains
bounded provider-error retry because a trusted channel feed 404 can be transient. No timer/source job cache crosses Restore. The actual API
Restore rebuilt the runtime and restored its full saved scheduling projection.
A separate SIGTERM/relaunch preserved all source authority/counts and schema-34
integrity. Idle wait uses Event/deadline, never a continuous short scan.

Earlier in-flight full backend runs were superseded after the real idle Backup
finding and the transient/refusal policy review. The final full run is against
the corrected worker and shared policy. No tests,
assertions, coverage thresholds or CI commands were removed/weakened. Setup
errors (shared editable import path, fresh required legacy config, asynchronous
UI readiness/Source Run settlement, symlink fingerprint encoding) were corrected
in task-owned validation harnesses. Product configuration, secrets and system
network settings were not changed. The brief health-before-run-settlement view
was correctly marked checking, not falsely settled.

## Cost

Traced tracked discovery through runtime ingestion, tracker enumeration and
existing YouTube enrollment. Tracked Source Run discovery yields no scoring or
model-processing candidates. Enrollment uses verified public transcript and
extractive Summary. Denied model factories prove that baseline/new item/repeat
checks do not construct Scoring, Deep Analysis or quality models. One new item
has a timed transcript and current local Summary; subsequent checks retain one
Content and zero distillation checkpoints. Real runtime uses an empty task-only
CredentialStore, never reading/writing real credentials. No automatic Cloud,
Research, Deep Analysis or expensive routing authority was added. Existing
explicit model consent/dispatch recovery rules remain unchanged.

## Phase 12 security and accepted capabilities

Forty-five frozen files have matching starting-main/current SHA-256, including
YouTube transport/provider/parser, source trust, accepted enrollment runtime,
Source Run/state constraints, Bilibili import, production dependency manifests
and all SQL migrations. TLS, SSRF, Fake-IP, system proxy discovery, no environment
proxy authority and no cookie/login behavior were untouched. Phase 12/network/
parser/final-P1 suites pass. Bilibili creator/public captions remain unavailable;
manual public-video import and Local regressions pass. Production ASR and Deep
Analysis remain NONE. No migration or dependency/lockfile change occurred.

All eight protected worktrees match before/after HEAD, status, content hash,
metadata hash and entry count, including dirty M13. The first apparent M13
mismatch was a calculation error: its symlink target must be hashed raw under
the original rule. Repeating the original rule matched all fields; nothing was
repaired or written in a protected worktree.

## Acceptance decision

All implementation findings above are fixed and retested. Main adoption and
completion/freeze declaration remain gated on every required acceptance check,
including successful real-source acquisition. No waiver, fabricated baseline,
network redesign or alternative merge strategy is allowed. Phase 14 is not
started. Following successful acceptance/adoption, the next activity is
real-user daily usage/pilot; no further feature-development phase is proposed.

Final queue/cost review also traced existing model-unavailable, consent and
budget waits: child waits become NEEDS_ATTENTION, so they are not an automatic
model retry authority. Tracked checks create no such children. No model queue,
topic processing or consent machinery was rewritten for this phase.
