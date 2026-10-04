# Phase 11 adversarial validation

All claims distinguish deterministic fixtures from live public provider evidence. The final complete regression and browser logs supply execution results; static rows cite inspected boundaries.

| # | Requirement | Evidence |
| --- | --- | --- |
| 1 | Valid profile URL | test_bilibili_creator.py: creator_forms; real public creator record; browser |
| 2 | Canonical numeric input | creator_forms; numeric automatic browser scenario |
| 3 | Creator from trusted Content | test_creator_following.py: follow_content; browser |
| 4 | Malformed profile URL rejected | test_bilibili_creator.py: rejects_crawling_and_unsafe_inputs |
| 5 | Non-Bilibili URL rejected | rejects_crawling_and_unsafe_inputs |
| 6 | Arbitrary profile path rejected | rejects_crawling_and_unsafe_inputs |
| 7 | Equivalent forms dedupe | baseline_repeat_new_and_reorder_are_idempotent; browser follow-from-Content reuse |
| 8 | Display-name change retains identity | baseline_repeat_new_and_reorder_are_idempotent |
| 9 | Initial follow establishes baseline | baseline_repeat_new_and_reorder_are_idempotent; live baseline |
| 10 | Initial history produces zero updates | baseline_repeat_new_and_reorder_are_idempotent; browser baseline |
| 11 | Unchanged check produces zero updates | baseline_repeat_new_and_reorder_are_idempotent; Delta test |
| 12 | One new video produces one discovery | baseline_repeat_new_and_reorder_are_idempotent |
| 13 | Multiple new videos bounded and deterministic | partial_page_failure; gap_deep_recovery; browser caption/no-caption pair |
| 14 | Pinned old video is not a new update | pinned_unobserved_history_and_equal_timestamp; historical metadata admission test |
| 15 | Reordered list does not duplicate | baseline_repeat_new_and_reorder_are_idempotent |
| 16 | Repeated checks are idempotent | baseline_repeat; restart/manual dedupe; browser no-op |
| 17 | Manual import reuses canonical Content | restart_pause_cooldown_and_manual_dedupe; browser |
| 18 | Public caption creates normal transcript | follow_content; three_provider; browser |
| 19 | Absent caption is honest | follow_content; Bilibili no-caption regressions; browser |
| 20 | No acoustic fallback | test_bilibili_content.py: no_media_or_unqualified_executor_route; worker fixture asserts zero model transport calls |
| 21 | Partial page failure retains frontier | partial_page_failure_retries_without_advancing_or_losing_content |
| 22 | Retry recovers unseen Content | partial_page_failure; enrollment_failure_keeps_pending_identity |
| 23 | Timeout/network failure preserves state | failure_preserves_verified_baseline; provider finite retry/timeout boundary |
| 24 | Rate limit preserves state | failure_preserves_verified_baseline; live repeat RATE_LIMITED |
| 25 | Risk control is not bypassed | creator_risk_control; shared_direct_video_budget; fixed public request path |
| 26 | Offline preserves last success | failure_preserves_verified_baseline; restarted offline browser |
| 27 | Restart preserves baseline | restart_pause_cooldown_and_manual_dedupe; restarted browser SQLite |
| 28 | Restart does not rediscover history | restart/manual dedupe; offline update_count stays two |
| 29 | Backup/Restore preserves incremental state | backup_restore_preserves_tracking; whole database authority |
| 30 | Restore does not manufacture updates | backup_restore_preserves_tracking repeat check with same identities |
| 31 | Corrupt state fails safely | corrupt baseline; wrong_creator_relationship; receipt and schema validation |
| 32 | Pause prevents automatic checks | API stale paused; pausing during fetch; metadata admission guard |
| 33 | Resume retains frontier | restart_pause_cooldown; browser pause/resume |
| 34 | Rapid Check Now is bounded | queued_check_is_visible_and_rapid_commands_reuse_one_source_run: ten commands, one run, zero provider calls |
| 35 | Creators share provider concurrency | provider_budget_prevents_concurrent_creator_checks: two distinct creators; inherited network slots test |
| 36 | Remote deletion preserves historical authority | remote_deletion_and_unavailable_creator_preserve_trusted_history |
| 37 | Unavailable creator preserves Content | same remote deletion/unavailable test |
| 38 | Routine check never rewrites trusted captions | follow_content caption immutability; publisher READY reuse |
| 39 | Normal Summary/Evidence path | creator-discovered three-provider test; browser timed transcript/evidence |
| 40 | Cross-Content Evidence rejected | test_bilibili_content.py: evidence_cannot_bind_another_content; integrated authority regressions |
| 41 | Three-provider Intelligence remains valid | test_bilibili_three_provider.py: discovered Content in ordinary sealed Intelligence |
| 42 | Discovered Content works in Research | four Content / three-provider Research test and browser packet |
| 43 | No-op polling is absent from Delta | delta_reports_repeated_health_failure_and_recovery_without_polling_noise |
| 44 | Source health is truthful | five provider failure categories, unavailable creator, gap, corrupt state, live rate limit |
| 45 | Chinese UI complete | real browser matrix and frontend tests |
| 46 | English UI complete | real browser matrix and frontend tests |
| 47 | 320px layout safe | browser zero overflow; screenshot inspection |
| 48 | No primary navigation added | browser asserts six destinations; App diff |
| 49 | No browser-cookie reads | static provider/creator call-path review: fixed cookie-free HTTP; no browser integration in provider |
| 50 | No authentication bypass | static network review; public risk responses terminal; no account fields/dependencies |
| 51 | No redirects or SSRF | creator input rejection; inherited redirect/private DNS/host/body/TLS tests |
| 52 | Production Deep Analysis remains NONE | unchanged activation code; runtime capability execution_route None; Settings browser |
| 53 | Acoustic qualification remains failed/unqualified | unchanged qualification/remediation/executor code and accepted records; Phase 9/9R boundary regression |
| 54 | Schema and lineage valid | 034 rollback/upgrade, exact migration history, doctor rejects 35; database PRAGMAs/checksums |
| 55 | Protected worktrees unchanged | protected-preservation.json: 21 starting HEAD/status/diffs unchanged |
