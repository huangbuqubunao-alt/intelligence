# Phase 12 — one continuous Following authority

Accepted baseline: a81b8e90a662eab72dda28fdc2140362649d9544. Schema 34.
Owner-authorized implementation in an independent Phase 12 worktree.

## Audit and smallest boundary

REUSE: migration 034's provider-scoped source_tracking_state, immutable identity
observations and source_checks; ordinary source_subscriptions/source_video_links;
Source Run leases, deduplication, worker and app-lifecycle scheduling; Backup/Restore
inner tracking verification; canonical YouTube video ids; yt-dlp metadata and
subtitle acquisition; accepted Atom parser; normal timed transcripts, extractive
Summary and durable Evidence; provider-neutral Research, Topic, Intelligence and
Knowledge Delta. No admission threshold or capability state changes.

ADAPT: FollowingTrackingService's old Bilibili publisher calls become a small
FollowingProvider seam (resolve/enumerate/enroll). The Bilibili adapter preserves
accepted bounded page/offset behavior. YouTube resolves aliases and enumerates a
public feed. Shared lifecycle owns all persistence, baseline decisions, pending
identities, transactional enrollment links, leases, cooldown, health and frontier.

GENERALIZE: CREATOR-only dispatch in Local API, source-run orchestration and frontend
now tests the durable tracking ledger. Restore's existing validator verifies both
provider/kind pairs, canonical identities and channel-to-Content relationships.
Verified YouTube caption timings enter the shared Content transcript view.

DEMO-ONLY: historical seeded channel Following and demo health. Legacy configured
channel discovery's timestamp cursor is not accepted Phase 12 frontier authority.
Existing untracked configurations remain compatible, but new channel follow uses
the shared tracker; Add one video rejects channel inputs. OBSOLETE for continuous
tracking: CREATOR-only dispatch and scalar cursor coverage. UNSAFE: display-name
or handle authority, cookies/login, list-position watermark, trusting feed items
without metadata membership verification, and unqualified acoustic fallback.

## Identity and enrollment

provider=YOUTUBE, kind=CHANNEL, stable UC plus 22 characters. Supported inputs:
HTTPS youtube.com or www.youtube.com /channel/UC… and /@handle, bare stable id,
or ASCII @handle. Strict allowlist rejects video URLs, arbitrary hosts/schemes,
ports, credentials, query/fragment, control characters and malformed identities.
No custom/legacy URL expansion. Handles are resolved using the accepted public
metadata-only yt-dlp stack, with flat listing limited to one entry and no retries.
Stable ids and verified Content can reuse a stored source offline. Channel id URL,
handle changes and display-name changes deduplicate by canonical channel URL/id.
Existing canonical legacy configuration without historical membership may be
adopted; forged/incompatible authority is rejected rather than reset.

Follow from Content uses its accepted public YouTube metadata row, canonical
watch URL/id and authoritative UC channel id. Feed enumeration verifies channel
identity; enrollment independently checks ordinary provider metadata membership,
public availability, publication after follow, accepted duration and live status.
Existing manually imported video id is reused, with its artifacts preserved.
Unsupported live/upcoming/nonpublic/duration items do not acquire Content and
retain explicit terminal observation states. Ordinary supported Shorts keep their
existing canonical video behavior. Removed remote items never delete local data.

The ordinary RuntimeOperations transcript-only ingestion boundary performs
metadata/subtitle acquisition. Existing ExtractiveSummaryService creates Summary
and durable Evidence from trusted timed captions. Its pipeline stop boundary now
stops job scheduling as well as execution, avoiding orphan scoring jobs. No
Following-specific ingestion artifacts or model pipeline is introduced. Missing
captions retain honest failed/unavailable acquisition without Summary/Evidence.
No media download, acoustic inference, scoring model or Deep Analysis call occurs.

## Baseline, bounded discovery and verified frontier

FOLLOW FROM NOW ON. First successful bounded public Atom window (at most 15
entries/256 KiB) records baseline identities, creates zero historical Content and
zero update events. Older resurfaced videos remain baseline by publication time.
No historical backfill, all-history import or caption-refresh operation is added.

After baseline, the newest three identities from the last verified state must
reappear with unchanged publication times before a window closes its gap. Empty
channels have an explicit empty verified boundary. Reordering and exact duplicate
entries are harmless; contradictory duplicates, malformed feed shape/channel or
oversized response fail closed. Shared tracking reads at most 90 verified identities
for the provider seam and enrolls at most five pending videos per check, ordered by
publication/id. Pending identities are durable before acquisition; retries do not
forget observations or duplicate ordinary Content.

A lost overlap yields UPDATE_GAP (check incomplete), preserves verified frontier
and last complete successful check, and can safely enroll individually verified
pending items. Later overlapping coverage closes the gap. Network/rate/access/
provider failures preserve prior trusted state. No scalar publication timestamp or
list position alone proves coverage. The rolling public feed cannot prove a gap
larger than its window; it intentionally remains incomplete, with no silent reset
or automatic history crawl. This is a truthful bounded public-only limitation.

## Shared orchestration, health and provider budgets

Both providers use the same source_runs worker and source_checks ledger. Provider
identities are scoped; YouTube and Bilibili do not share rate semaphores. YouTube
allows one public operation, 0.5-second start pacing and a 15-minute rate/access
cooldown, with no retry storm. Fixed-host feed retrieval uses accepted public DNS,
pinned TLS, no redirects, 10-second deadline and response bounds. Existing yt-dlp
security remains in force; no credential configuration or dependency is added.

Check Now reuses active Source Runs and a 15-minute source cooldown. Application
Following lifecycle refresh schedules at most three stale sources per event.
Paused sources receive no automatic checks/enrollment; atomic Content insertion
rechecks pause and channel authority. Resume preserves the prior frontier. Source
health uses accepted HEALTHY/OFFLINE/RATE_LIMITED/ACCESS_DENIED/PROVIDER_ERROR/
UPDATE_GAP/STATE_INVALID vocabulary. Polling is not a knowledge change.

## Portable and downstream authority

Restart and offline retain source identity, baseline, observations, memberships,
update counts, health and last trusted timestamps. Backup/Restore preserves the
same schema-34 rows and verifies both provider relationships without network.
Forged cross-provider/wrong-channel/unobserved memberships fail safely. Stored
Content, Summary and Evidence survive remote removal and offline checks.

YouTube-discovered, Bilibili-discovered and Local Content use ordinary selected
Research and sealed Intelligence provenance. Following provides context, never
proof or lower admission thresholds. No automatic Topic creation. Knowledge Delta
uses ordinary Content/health semantics and emits no healthy-polling noise.

## Migration, frozen capabilities and deferred scope

NO MIGRATION: schema 34 already expresses durable multi-provider tracking. Migration
034 bytes and all historical migrations (including 029) remain untouched. No 035.
Frozen large-v3-turbo remains ACOUSTIC_QUALIFICATION_FAILED; production acoustic
ASR NONE and production Deep Analysis NONE. No account, OAuth, cookies/browser
cookie reading, required API key, private/membership access or bypass is introduced.
No primary navigation, notification system, system daemon, cron/login item or
always-on helper. Historical backfill, versioned caption refresh and further
providers remain deferred.

Initial caption acquisition retries remain ordinary pipeline jobs. A retry-pending
job leaves the discovery observation PENDING, preserving the same Content id for
a later bounded source check. Permanent caption absence is enrolled as honest
Content without transcript/Summary/Evidence. This is recovery of initial
acquisition, not the deferred versioned caption-refresh feature. A check that
fails acquisition preserves the last successful check timestamp even when its
individual enumeration coverage was safely verified.

Bounded tracked-source retrieval failures terminate their ordinary Source Run as
FAILED, preserving the source health/identity ledger and pending Content. They do
not create an unresolved model-execution attention state that would indefinitely
block offline Backup. A queued tracking check whose source was paused terminates
as CANCELLED without a provider call. Ordinary untracked processing and ambiguous
model-dispatch attention semantics remain unchanged. Existing pre-upgrade attention
runs are preserved; no historical run-state repair or migration is performed.

Stale scheduling orders enabled tracking sources by next_check_at/source id rather
than Following display creation order. At most three due sources are admitted per
lifecycle event; later events drain the remaining due set. This prevents newer
channels from repeatedly displacing an older creator/channel and keeps provider
neutrality observable in automatic checks as well as Check Now.

The existing YouTube metadata adapter may fall back to a date-only upload_date at
midnight UTC. A same-day post-follow video uses its already-persisted, verified
feed publication time to resolve that ambiguity. Ordinary Content metadata is
preserved. An older metadata date or precise pre-follow time remains historical;
this does not admit resurfaced history. Both cases have focused regressions.

Nonterminal metadata/acquisition failures retain PENDING and propagate source
health failure, without manufacturing a successful check or last-success timestamp.
Only explicitly unsupported/unavailable individual items become terminal
observations. A subsequent bounded check recovers the same pending identity.

## 2026-10-07 resume and baseline precedence

The owner-authorized resume preserves the complete paused state at 4d0cb5e5 and
its dirty/untracked WIP in checkpoint 97d2a73, then semantically merges validated
Phase 11R.1 8ebdf282 from shared ancestor a81b8e9. The earlier Bilibili availability
statements in this historical decision do not reactivate its live capability.

Bilibili Creator Following is WITHDRAWN. Generic architecture, stored identities,
observations, relationships and history remain valid. API enrollment/manual/stale
checks and the production tracking provider gate prevent live creator requests,
including previously queued work. Tests explicitly enable only injected historical
provider fixtures to verify retained architecture; production availability stays
false. Public captions also remain unclaimed; manual public videos remain available.

The single active Source Run definition and settled NEEDS_ATTENTION Backup rules
come from 11R.1. YouTube provider slots and fair due-source order come from Phase 12.
Withdrawn creators cannot consume the three live stale-check admission slots.
Settings projects YouTube channel capability separately from Bilibili capability.
Current unavailable status is separate from preserved historical health.

No migration, dependency, model, cloud route, provider, daemon or scheduler is added.
UI cooldown expiry only refreshes read-only detail. Bounded public NASA and Google
Developers handle attempts returned NETWORK_UNAVAILABLE; successful real baseline
is not claimed. Deterministic provider replay separately validates enrollment and
restart/offline/restore. Fresh evidence is in docs/validation/phase12-resume.
