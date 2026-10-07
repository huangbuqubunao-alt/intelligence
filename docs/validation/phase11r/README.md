# Phase 11R — Bilibili Real-World Remediation Validation

Evidence produced by the DeepSeek Phase 11R task against its own candidate.
This is **self-validation**: it shows the candidate behaves as this task
believed. It does **not** replace independent revalidation.

Runtime artifacts live under the task-owned, git-ignored `.var/phase11r/`
directory. Only this index is committed.

## What was decided

See [`docs/decisions/V1X-PHASE11R-BILIBILI-REALWORLD-REMEDIATION.md`](../../decisions/V1X-PHASE11R-BILIBILI-REALWORLD-REMEDIATION.md).

In short: Bilibili **creator Following is withdrawn** (OUTCOME B), public
**captions remain unavailable** (0/8 in a bounded live sample), and public
**video metadata works** (8/8).

## Bounded live sample

| Result | Value |
| --- | --- |
| Videos sampled | 8 |
| Public metadata succeeded | 8 / 8 |
| Public captions observed | 0 / 8 (`CAPTION_UNAVAILABLE`) |
| Largest `/x/web-interface/view` response | 371 359 bytes |
| `MAX_METADATA` bound | 524 288 bytes (1.41× headroom) |
| Creator listing accepted | 0 / 3 fair probe, all raw `-412 request was banned` |

Policy held throughout: no login, no cookies, no authorization, no referer,
no proxy rotation, no CAPTCHA workaround, no media download, no ASR.

Evidence: `.var/phase11r/evidence/r2_video_metadata_captions.json`,
`.var/phase11r/evidence/r2_response_sizes.json`.

## Runtime checks

| Check | Result |
| --- | --- |
| Database health | `user_version 34`, `quick_check ok`, `integrity_check ok`, `foreign_key_check []`, no frontier or identity violations |
| Runtime stability | 40 rounds / 187 s, PID stable, 0 transport errors, 0 running checks, 0 active runs, 0 accumulated `NEEDS_ATTENTION` |
| Security / privacy | no cookies, no authorization, no local library data, no path leaks, no transcript in logs, vault excluded, secret scan clean |
| Backup / Restore | two round trips, schema 34, restore `APPLIED`, portable authority preserved, corrupt archive still refused |
| Browser | 31/31 checks, zh-CN and en at 320 / 768 / 1024 / 1440 |
| Backend | 3594 passed, 1 skipped |
| Frontend | 189 passed, typecheck and production build clean |

Evidence: `.var/phase11r/out/*.json`, `.var/phase11r/screenshots/`.

## Known limitations

- RSS grew 112 288 → 116 768 kB over 40 rounds (~112 kB/round). That is
  step-wise allocator behaviour on a bounded set of requests, not evidence of a
  leak, and it is recorded as an observation only.
- Provider code `62002` (`稿件不可见`) is classified truthfully by the provider
  layer but still projects to the generic `PROVIDER_ERROR` health in the
  Following view. Deferred as P2.
- A `NEEDS_ATTENTION` run is now *resolvable* in the state machine
  (`NEEDS_ATTENTION → CANCELLED | FAILED`), but no operator-facing control to
  do so is shipped. Deferred.

## Independent revalidation still required

Rerun the OpenCode recon harness
(`/Users/hua/Documents/yia-worktrees/online-validation-recon/harness/`) and an
owner-led real-world pass against this candidate before any pilot. Creator
listing may become available again at any time; the withdrawal is a single
constant (`CREATOR_FOLLOWING_AVAILABLE`) and re-enabling it does not require
re-implementing Following.