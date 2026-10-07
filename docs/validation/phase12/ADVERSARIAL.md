# Phase 12 adversarial acceptance map

Tracking tests are in `tests/integration/test_youtube_following.py`. Abbreviations
below identify their test names; browser JSON and raw gate logs are in this folder.
Provider retrieval alone is simulated in browser fixtures; API, SQLite, Source Runs,
ordinary captions/Summary/Evidence, Research and Backup/Restore are real local code.
The real public request failed NETWORK_UNAVAILABLE; no live success is claimed.

| # | Required case | Evidence |
|---|---|---|
| 1 | Channel-id URL | `test_channel_inputs` |
| 2 | Handle URL | `test_channel_inputs`, online browser |
| 3 | Trusted Content follow | `test_full_incremental_normal_ingestion_restart_dedupe`, browser |
| 4 | Malformed input | `test_channel_inputs_reject_arbitrary_urls` |
| 5 | Non-YouTube URL | Same rejection test |
| 6 | Handle/id dedupe | Baseline and full incremental tests |
| 7 | Changed handle | Full incremental test |
| 8 | Changed display name | Full incremental test |
| 9 | Initial baseline | `test_youtube_baseline_reuses_shared_tracking_without_history` |
| 10 | Zero historical Content | Same baseline test and browser |
| 11 | Zero false update | Same baseline test and browser |
| 12 | No-change check | Full incremental test and browser |
| 13 | New video once | Lost-overlap and empty-channel tests |
| 14 | Multiple deterministic videos | Full incremental and bounded pending tests |
| 15 | Repeat idempotency | Full incremental restart test |
| 16 | Reordered list | Full incremental test |
| 17 | Duplicate entries | Full incremental test |
| 18 | Resurfaced history | `test_lost_overlap_partial_retry_and_historical_resurfacing` |
| 19 | Existing manual Content reused | Full incremental test |
| 20 | Partial coverage cannot skip | Lost-overlap and bounded pending tests |
| 21 | Partial retry recovery | Same tests; initial caption retry test |
| 22 | Network preserves frontier | `test_youtube_failure_preserves_frontier` |
| 23 | Rate limit preserves frontier | Same parametrized test |
| 24 | Truthful incomplete check | Lost-overlap test |
| 25 | Rapid checks bounded | `rapid-check-browser.json`: twelve commands/provider, one run each |
| 26 | Pause blocks checks | Pause and queued cancellation tests; shared browser |
| 27 | Resume preserves frontier | Pause/atomic enrollment tests; shared browser |
| 28 | Restart no history rediscovery | Full incremental test; offline browser |
| 29 | YouTube restore | Mixed-provider backup test; database-restore.json |
| 30 | Simultaneous Bilibili restore | Same test and exact five-table restore |
| 31 | Forged provider/channel links | `test_forged_tracking_relationships_rejected`; stable-id rebinding test |
| 32 | Removed remote item retained | `test_enrollment_bounded_pending_retry_and_removed_authority` |
| 33 | Captions → Summary/Evidence | Full incremental test; caption browser views |
| 34 | Missing transcript honest | Pause/no-transcript test; missing-caption browser views |
| 35 | No acoustic fallback | Denied model factories in tracking tests; no acoustic action in browser |
| 36 | No cloud/Deep Analysis | Denied factories and zero dispatch transport calls in fixture shutdown |
| 37 | Followed YouTube Research | Mixed-provider backup/Research test and browser |
| 38 | Followed Bilibili Research | Same test and browser |
| 39 | Local + both network providers | Same test and browser |
| 40 | Mixed Intelligence provenance | Sealed evidence revision and dependency assertions in mixed-provider test |
| 41 | No polling Delta noise | `test_healthy_polling_has_no_knowledge_delta_and_empty_channel_is_safe` |
| 42 | Truthful source health | Failure, initial caption retry and invalid metadata recovery tests |
| 43 | Phase 11 | Creator Following and Bilibili creator regressions |
| 44 | Phase 10B manual Bilibili | Bilibili content/provider/three-provider regressions |
| 45 | Local Provider | Local content/adversarial/offline mixed regressions |
| 46 | Manual YouTube ingestion | Discovery adapter, runtime composition and pipeline regressions |
| 47 | Chinese UI | Unit form test and browser matrices |
| 48 | English UI | Unit form test and browser matrices |
| 49 | 320px layout | Online/offline/restored/shared browser, overflow assertions and screenshots |
| 50 | No primary navigation added | Browser asserts six buttons; full diff review |
| 51 | No account/OAuth | Public adapter diff review; live attempt without credentials |
| 52 | No browser cookies | Metadata-only yt-dlp options, public feed and live-attempt record |
| 53 | Acoustic qualification failed | Acoustic qualification/remediation/boundary/scoring regressions |
| 54 | Production Deep Analysis NONE | Deep Analysis closure/boundary regressions and no new dispatch path |
| 55 | Schema/migrations | Schema 34, three PRAGMAs, unchanged SQL checksums and state lineage tests |
| 56 | Protected worktrees | `protected-worktrees.json`: exact HEAD/status/diff comparisons for 22 |

Additional adversarial cases cover malicious/huge/changed XML, entity declarations,
provider-level concurrency/cooldown, live/upcoming rejection, atomic pause during
metadata, empty channels, initial caption retry, terminal offline runs permitting
Backup, fair bounded stale scheduling, same-day date-only metadata and malformed
metadata recovery. None use cookies, account mutations or unqualified inference.
