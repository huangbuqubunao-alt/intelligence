# Phase 10B — public Bilibili video Content

Authoritative user assignment: sole executor, accepted baseline
`7e3638c0d776dcd66a343f6d2dd9b9a80d046424`, dedicated
`chatgpt/v1x-bilibili-provider` worktree. The explicit Phase 10B assignment
supersedes historical YouTube-only task scope and multi-role handoff rules.
No release, merge, push, credentials, dependencies, or real Vault writes.

## Done criteria and increments

1. Audit accepted provider/source authority, record protected worktree state.
2. Cookie-free public adapter with deterministic BV identity, strict URL/DNS
   policy, bounded responses/concurrency/retries, metadata/caption fixtures.
3. Extend existing provider constraints in migration 033: schema 32 explicitly
   excludes Bilibili in videos, Following and source snapshots. No new domain.
4. Reuse source publication, timed candidates, Summary and durable Evidence.
   Store acquired metadata and exact captions/provenance immutably. Metadata-only
   Content has no transcript, Summary or fabricated Evidence. No media/ASR route.
5. Following Add and shared Content UX, retry, bilingual status/provenance.
6. Validate three-provider Intelligence/Topic/Research and ordinary Content Delta;
   offline/restart/backup integrity and immutable repeated import semantics.
7. Adversarial tests, three self-reviews/remediation, full regression/static/build,
   actual browser flows and responsive layouts, fresh acceptance, local commits.

## Reuse decision

DIRECT: Python standard library HTTPS/TLS, DNS/IP validation, strict JSON, SQLite;
existing snapshot/artifact publisher, timed authority and Summary, Evidence,
Research/Intelligence/Topic/Delta contracts. No new production dependency.
REJECT: browser scraping/login/cookies, yt-dlp Bilibili extraction, audio/video
download and unqualified acoustic fallback. Creator polling/authenticated content
deferred. Agent Reach doctor identified browser-login OpenCLI as active Bilibili
backend; user no-cookie instructions prohibit that acquisition route.

## Input and authority policy

HTTPS video URLs on exactly www.bilibili.com, bilibili.com, m.bilibili.com,
or direct valid BV id. Only first/single video part; other parts are unsupported
instead of silently deduping different caption material. Short/share links deferred.
No redirects are followed (redirect chain bound zero). Caption URLs accepted only
on explicitly approved HTTPS subtitle CDN hosts/paths. Public metadata/player
endpoints only; denial/rate limiting stops bounded retrieval honestly.

Canonical content id `bilibili-<BV>`; Following is one VIDEO_URL per Content,
never a creator subscription. Ready acquired authority is never overwritten.
Phase 10B does not refresh display metadata. A future explicit refresh may change
display fields only; historical snapshot, caption language/text/timing and Evidence stay fixed. Caption acquisition can be
retried before READY, bound to the original snapshot's BV/CID/duration.
The accepted source-snapshot duration contract limits this slice to two hours.
Other parts, longer videos and creator monitoring are deferred explicitly.

## Qualification invariant

large-v3-turbo MODEL_NOT_QUALIFIED; offline ASR production qualification NONE;
production Deep Analysis route NONE. Phase 9/9R failed records stay unchanged.

## Validation record

Evidence lives under `docs/validation/phase10b/`. Tests use fakes; public live
validation is bounded and never required for routine tests. No completion claim
without command results, persisted authority verification and browser evidence.
