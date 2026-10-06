# V1X-PHASE11R — Phase 11R Bilibili Real-World Remediation

- **Status**: Accepted as the disposition of Phase 11R
- **Date**: 2026-10-05
- **Baseline**: Phase 11 accepted commit `a81b8e90a662eab72dda28fdc2140362649d9544`, schema 34
- **Supersedes for Bilibili only**: the Phase 11 claim that public creator Following works
- **Scope**: Bilibili public video ingestion and public creator Following

This record states what Phase 11R measured against the real public Bilibili
provider, what it therefore changed, and what it deliberately did not do.

---

## 1. Why this exists

Phase 11 shipped creator Following on the strength of offline fixtures. Phase
11R ran the shipped product code against the real public provider to find out
whether that claim survives contact with the network. It does not, for creator
Following. This record makes the resulting product decision explicit so nobody
has to re-derive it from logs.

## 2. Evidence

All evidence is reproducible from `.var/phase11r/` in the Phase 11R worktree.

| Probe | Result |
| --- | --- |
| Reconnaissance (read-only, `online-validation-recon` `b8f0031`) | 0 / 10 creator checks accepted |
| `r1_creator_single_shot` | 1 of 3 returned `code 0`; 2 refused (`-799`, HTTP 412) |
| `r1b_creator_fair_probe` (one request per creator, 6 s apart) | **0 / 3 accepted**, all raw `-412 request was banned` |
| `r2_video_metadata_captions` (8 public videos) | 8 / 8 metadata OK, **0 / 8 captions** |

The single `code 0` in `r1` is not a path forward. It was the lucky answer in a
sequence that was already under rate limiting, and pursuing it would mean
re-asking a provider that had already said "request was banned". That is
circumvention, not recovery, so it was deliberately not chased.

### What the provider actually said

- `HTTP 412` with `{"code": -412, "message": "request was banned"}` — risk control.
  Phase 11 reported this as `ACCESS_DENIED`, which describes a *different*
  problem (the resource is not public) and invites the wrong next action.
- `HTTP 200` with `{"code": -799, "message": "请求过于频繁"}` — rate limited.
- Metadata for public videos is served normally and without any refusal.

So public **video** ingestion works against the real provider. Public **creator**
listing does not, for this client, without a session the product will never use.

## 3. Decision P0-01 — Creator Following is withdrawn (OUTCOME B)

**Bilibili creator Following is withdrawn from normal pilot UX.**

- `POST /api/v1/sources/creators` → `409 BILIBILI_CREATOR_TRACKING_UNAVAILABLE`.
  No provider request is made and no source row is created.
- `POST /api/v1/videos/{id}/follow-creator` → the same `409`. "Follow this
  creator" is hidden, and when reached it is disabled rather than failing later.
- `POST /api/v1/sources/{id}/check` on a stored creator → `200` with
  `status: CAPABILITY_UNAVAILABLE`. A withdrawn capability must never answer
  with a silent request.
- `POST /api/v1/sources/check-stale` → records `CAPABILITY_UNAVAILABLE` and
  skips. No automatic creator check is scheduled.
- `GET /api/v1/settings` publishes the same fact under `bilibili.creator_following`,
  so the UI localizes a code instead of parsing backend prose.

User-facing wording, frozen:

> zh-CN：Bilibili UP 主持续关注当前暂不可用。你仍可添加公开 Bilibili 视频。
> en：Continuous Bilibili creator tracking is currently unavailable. You can
> still add public Bilibili videos.

**What is preserved.** Every stored creator row, its Content, its Evidence and
the whole verification frontier remain exactly as they are. Nothing is deleted,
no row is mutated, and the withdrawal is expressed as a capability flag, never as
a deletion. A creator already followed stays readable, with its real health, its
real baseline state and its real Content.

**What was not done.** No cookie, login, QR session, proxy rotation, identity
rotation, CAPTCHA handling or aggressive retry was introduced. No circumvention
of the refusal was attempted. The refusal is treated as evidence.

**Where the check lives.** The withdrawal is enforced at the product boundary
(the API the pilot uses). The library-level `FollowingTrackingService` keeps
working, so the mechanism, its invariants and its tests survive and can be
re-enabled later by flipping one constant if the provider ever permits it.

## 4. Decision P0-03 — Captions stay unavailable

`LIVE_CAPTION_SUCCESS_NOT_OBSERVED` reconfirmed: 8 of 8 sampled public videos
returned an empty `subtitles` list. Phase 11R therefore adds no transcript, no
summary or no Evidence from these videos.

Explicitly not done: no fabricated transcript; no inference from title,
description or danmaku; no ASR fallback; no new acoustic model. `large-v3-turbo`
remains `MODEL_NOT_QUALIFIED` and production Deep Analysis remains `NONE`.

A public video with metadata but no caption still imports, and is stored as
`CAPTION_UNAVAILABLE` — visible, counted, and honestly described.

## 5. Decision P0-02 — A settled run that asks for attention is not "active forever"

Phase 11 backed up behind any source run that was not terminal. A run that
stopped to ask a question therefore blocked data protection forever.

Backup quiescence now blocks only on work that can still change on its own:

- `QUEUED`, `RUNNING`, `WAITING`, `PARTIAL` block outright.
- `NEEDS_ATTENTION` blocks only while it still holds resumable authority — a
  non-terminal child execution, or an open distillation checkpoint on its source.
- A `NEEDS_ATTENTION` run with no live child and no open checkpoint is settled
  history and does not block.
- Anything the database cannot prove stays blocking, so corrupt state fails
  closed.

Retry was already correct and was left alone: it creates a new explicit run and
never rewrites a failed run into a success.

`SourceRunState.NEEDS_ATTENTION` now admits `CANCELLED` and `FAILED`, because a
run that asked for attention must be able to finish its lifecycle.

## 6. Decision P0-04 — A refusal is classified by what it means

| Provider signal | Reported as | HTTP |
| --- | --- | --- |
| `HTTP 412` / `-352` / `-412` / `-509` | `RISK_CONTROLLED` | 429 |
| `HTTP 429` / `-799` | `RATE_LIMITED` | 429 |
| `HTTP 401` / `403` | `ACCESS_DENIED` | 403 |
| `62002`, `62004`, `410002` | `VIDEO_UNAVAILABLE` | 404 |
| `-404` / `-40003` | `NOT_FOUND` | 404 |

Back-off follows the meaning: risk control and rate limiting cool the provider
down for 15 minutes, because re-asking sooner only deepens the refusal. A plain
access denial cools down for 30 seconds. The back-off is armed from whichever
transport produced the refusal, so an injected transport cannot bypass it.

## 7. Decision P0-05 — Response bounds are set from measured bytes

The metadata bound was 256 KiB. Against 8 real public videos:

- `/x/web-interface/view`: 2 084 – **371 358** bytes
- `/x/player/v2`: 2 323 – 4 199 bytes

The old bound rejected a genuine 371 358-byte response — it was refusing real
public videos. `MAX_METADATA` is now 512 KiB: 1.4x headroom over the largest
response actually observed, while staying a hard memory guard. No migration and
no schema change were involved.

## 8. Security posture held

`MAX_RESOLVED_ADDRESSES` was moved off the address-access path. An oversized DNS
answer set is bounded to 512 purely as a memory guard; it is never used to decide
that a *target* is acceptable. Every surviving address is still required to be
global and unicast, so SSRF and DNS-rebinding protection are unchanged. Private,
loopback, link-local, multicast, unspecified and malformed addresses are all
rejected.

## 9. Not done, deliberately

- No migration. Schema stays 34; no historical migration was edited.
- No new or upgraded production dependency.
- No change to the accepted Phase 11 or earlier history.
- No change to the Phase 12 worktree.
- No login, cookie, session, proxy or CAPTCHA capability.

## 10. Consequences a reader should know

- A pilot user cannot follow a new Bilibili creator. This is the intended
  product state, not a defect awaiting a fix.
- The Following list can still contain creators stored before the withdrawal.
  They remain readable and their health stays truthful; they simply stop
  producing new updates, and the UI says so.
- `RISK_CONTROLLED` no longer implies "this creator is private". Any stored
  `health` written before this change may still read `ACCESS_DENIED`; the next
  honest check rewrites it. No history was rewritten by hand.
## 11. What the product must never say again

A withdrawn capability that is still described as working is the same defect in
three different places, so all three are closed the same way:

- The Following list called a stored creator "Monitoring new videos". It now
  reports that continuous creator tracking is unavailable.
- The import dialog offered "Follow a creator" during the moment before the
  service had answered. The entry point is now rendered only once the service
  has confirmed it, so nothing is offered and then taken away.
- The Backup panel rendered the service's own English message, which put
  backend prose into the Chinese UI and hid *what* was still running. Readiness
  is now assembled from the structured reason codes the service already returns.

## 12. One definition of a live Source Run

"Which Source Run states still hold live execution" had been written out as a
literal SQL list in three places, so the definition this record changes could
drift from the call sites that decide whether a Source still holds authority.
It now lives once, as `SOURCE_RUN_ACTIVE_STATES` in `source_run`, and the
Backup quiescence gate, the active-manual-run reuse in `state`, and the
Following projection all derive from it.

## 13. Independent revalidation is still required

This task validated its own fixes. The OpenCode recon harness and an owner-led
real-world pass must be rerun against this candidate before any pilot. See
`docs/validation/phase11r/` for the Phase 11R evidence this task produced.
