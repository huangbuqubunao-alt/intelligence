# Phase 11 self-review and remediation

Sole executor. Reviewed complete changes against accepted Phase 10B
`bda7e3eeeaf7f71ab243a82bd75dc4995825d06b`, using actual implementation,
tests, HTTP/SQLite/worker browser flows and screenshots. No delegated review.

## Pass 1 — incremental correctness

A partial enumeration commits no observations or verified frontier. A successful
bounded enumeration commits identities and pending enrollment atomically before
Content acquisition. An acquisition failure preserves pending identities; a
crash between Content creation and relationship publication reuses canonical BV
Content on retry. Neither offsets nor a mutable display name are identity.
Initial observations and publications at/before following do not enroll history.
Pinned/reordered identities cannot recreate events. Metadata must independently
confirm creator and publication after following before enrollment. Complete
coverage requires verified list end without page overlap; a deep traversal is a
recovery hint and retains UPDATE_GAP. Restore retains the original followed time,
identity ledger and pending work; corrupt state is rejected rather than reset.

Resolved P1 findings: removed old-page/pinned stopping assumptions; reject short
pages, changing totals and contradictory identities; preserve receipt completion
when enumeration succeeded but acquisition failed; guard Content admission after
pause; verify enrolled uploader identity in both tracking and portable snapshot
validation. Historical metadata contradicting a purported new list item cannot
cause automatic Content admission. Trusted captions remain immutable.

Evidence: 41-video partial-page failure/retry, 101-new-video gap, five-item
oldest-first enrollment, restart/manual dedupe, metadata pause race, wrong creator,
wrong publication date, unavailable creator/deletion, corrupted baseline,
Backup/Restore, and ten rapid commands reusing one queued Source Run.

## Pass 2 — product

Inspected Chinese 320px and English 1440px screenshots and exercised the real
Chromium UI. Existing Add distinguishes one video from creator Following.
Following detail explains from-now-on semantics, last check/success, factual
health, cumulative discoveries, pending/unsupported acquisition and pause.
Captionless Content exposes unavailable transcript-dependent products.

Resolved material P2 findings: automatically discovered videos initially appeared
as additional Following rows labelled manual imports. They are now grouped under
the creator using existing observation/Content relationships; technical snapshot
sources remain in persistence. Existing manual/history items outside discoveries
retain their presentation. Following refreshes only local state while the existing
Source Run is active, including queued work. Completed checks clear transient
checking copy. No new scheduler or provider polling loop is introduced.

Both languages and 320/768/1024/1440 widths exercise manual import, baseline,
follow-from-Content, duplicate discovery, pause/resume, check/cooldown, captions,
Research, Delta and Settings. The extra numeric-input scenario opens stale
Following, discovers updates without Check Now and verifies grouped list refresh.
All assertion waits retain exact expected results after asynchronous rendering.

## Pass 3 — architecture and security

Reusable authority is SourceSubscriptions + existing source-video relationships,
generalized tracking state/observations/receipts, and existing Source Runs/worker.
Bilibili details stay in the provider boundary and public publisher. Content,
transcript, Summary, durable Evidence, Intelligence, Topic and Research authority
remain ordinary domains. No Bilibili feed/subscription/notification authority,
account, cookie extraction, bypass, cloud requirement, OS daemon or dependencies.

A future creator provider can reuse persistence, lifecycle, receipts and Content
relationships by supplying its provider identity/acquisition boundary; no future
provider is implemented. Every backup validates tracking and immutable uploader
metadata, in addition to accepted Content/Evidence authority. Existing approved
hosts, pinned public DNS/TLS, redirect denial, bounded bodies, finite retries,
shared concurrency/pacing and rate/risk backoff remain enforced.

Resolved P2 migration integration: runtime doctor now requires schema 34; exact
history assertions append 034, keep historical 033 and intentional missing 029,
and reject unknown 035. Failure-injection tests still test their original 033;
a separate 034 atomic rollback/upgrade test preserves Bilibili captions/Evidence.

## Failure evidence and corrections

- `pytest ...test_bilibili_three_provider.py`: injected `migrations[-1]` now meant
  034 while the test expected `failed to apply migration 33`. It now explicitly
  selects 033; separate 034 coverage was added.
- Initial full backend: 10 failures, 3,536 passes, one inherited skip. Nine were
  exact latest migration/name/tail or doctor expectations; the tenth was
  `BrokenBarrierError` in `test_concurrency_bound_across_adapters`, caused by
  preceding access-denial backoff leaking across tests. The network test isolates
  its shared cooldown and asserts that denial activates it; concurrency coverage
  remains intact. Remediated groups passed 255, 237 and 116 checks.
- Wrong-creator snapshot test first asserted shallow `readiness()` performed
  artifact validation. Readiness checks quiescence/schema; the authoritative
  operation is `create_backup()`. The corrected assertion requires that operation
  to reject the forged relationship before producing a portable backup.
- Browser harness: missing injected public adapter, missing required local mutation
  header, localized fixture-label mismatches and premature dialog count. Fixed the
  harness and awaited actual DOM results; no security guard or assertion removed.
- Production review fixes prompted interrupted full runs. Their logs are retained;
  no interrupted run is claimed as complete. Final full-suite evidence is the
  post-remediation complete acceptance run.

Fresh final acceptance is gated on the complete backend run, frontend/static/
database checks, final browser flows and a clean scoped diff. No unresolved
P0/P1/material Phase 11 P2 finding remains in the reviewed implementation.

Final gates passed: 3,550 backend tests, one inherited provisioning skip; 181
frontend tests; typecheck/build/Ruff/strict mypy/compileall/design checks; five
verified schema-34 databases; nine online and eight restart/offline creator
browser scenarios; 32 prior-phase browser scenarios; 21 protected worktrees.
Final screenshot review also awaited the rendered offline health message, avoiding
an asynchronous loading frame. Complete implementation hashes are recorded in
`reviewed-code-manifest.json`; subsequent edits are browser waits and evidence.
