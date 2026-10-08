# Required deterministic coverage

Production composition, SQLite and Source Run orchestration are exercised by
`tests/integration/test_background_following.py`; external acquisition boundaries
are controlled. Model factories fail if invoked. Current focused suite has 39
passing cases. Existing accepted suites supplement transport/parser/provider and
Backup authority coverage; no required check is claimed from a fixture as real
source success.

| Owner requirement | Evidence |
| --- | --- |
| 1 due checked | due_following_is_checked_without_a_ui_event |
| 2 future not checked | not_due_source_is_not_checked |
| 3 paused excluded | pause_and_resume_reenter_durable_scheduling |
| 4 resume reenters | pause_and_resume_reenter_durable_scheduling; API wake test |
| 5 manual/background race | manual_and_background_admission_reuse_one_run; accepted active-run admission regressions |
| 6 no automatic overlap | overlapping_worker_ticks_and_backup_are_bounded |
| 7 bounded multiple sources | many_due_sources_drain_serially_and_startup_does_not_flood |
| 8 verified success state | due_following_is_checked_without_a_ui_event |
| 9 failure no fabricated frontier | automatic_failures_back_off_without_fabricating_frontier, five categories |
| 10 bounded network retry | network_backoff_grows_and_recovery_needs_no_restart |
| 11 recovery | network recovery; transient_not_found_recovers_on_later_automatic_check |
| 12 provider cooldown | RATE_LIMITED backoff case; accepted Phase 12/network provider-budget tests |
| 13 parser/provider no hot loop | METADATA_FAILED, RESPONSE_TOO_LARGE, NOT_FOUND backoff; failed_sources_stay_bounded |
| 14 restart due | restart_preserves_next_check_and_paused_state |
| 15 startup no flood | many_due_sources_drain_serially_and_startup_does_not_flood |
| 16 baseline semantics | initial_baseline_failure_later_recovers_without_historical_content |
| 17 no historical baseline Content | above; background_enrollment_is_once_and_has_no_model_work |
| 18 new item enrolls once | background_enrollment_is_once_and_has_no_model_work |
| 19 duplicate suppressed | repeat check in same enrollment test; accepted Phase 12 parser/tracking regressions |
| 20 paused restart | restart_preserves_next_check_and_paused_state |
| 21 Backup readiness | protected/overlap/shutdown/local failure tests; idle_schedule_read_does_not_make_backup_unavailable |
| 22 protected window | protected_backup_window_does_not_admit_automatic_work; confirmed Restore gate |
| 23 restored authority | restored_authority_replaces_all_pre_restore_scheduling |
| 24 no stale jobs | same test; no job cache exists; actual CLI Restore rebuild evidence |
| 25 zero-config networking | test_youtube_network.py, test_youtube_final_p1.py; frozen 45-file hash proof |
| 26 withdrawn Bilibili | withdrawn_bilibili_capability_remains_unavailable; Phase 11R.1/manual import suites |
| 27 zero model work | denied model factories, timed transcript + extractive Summary + zero distillation checkpoint proof |
| 28 clean shutdown | shutdown_waits_for_the_current_bounded_check; actual child CLI SIGTERM test |
| 29 no idle polling | idle_wait_is_a_deadline; idle_worker_waits_and_api_resume_wakes_it_then_shutdown_drains |
| 30 truthful API/UI | checking/health/manual_check_at/next_check_at assertions; frontend deadline/Retry tests; bilingual real-API browser |

Additional review regressions cover BUSY slot deferral, STATE_INVALID admission,
local exceptions, exponential network cap/restart, synchronous automatic origin,
interrupted Source Run identity and stale RUNNING check lease recovery. Three
lifecycle refresh cases cannot bypass untrusted/risk/access refusal.

Real/local evidence is separate: normal Mac public alias/feed requests, one
normal automatic NASA attempt, actual HTTP manual/offline/pause/resume/readiness,
actual archive stage/confirm/CLI rebuild, process restart and responsive browser
views. The successful real NASA baseline/frontier gate remains unfulfilled by
current NOT_FOUND responses; fixture successes do not substitute for it.
