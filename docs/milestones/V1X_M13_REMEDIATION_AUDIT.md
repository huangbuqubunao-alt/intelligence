# M13 remediation audit for V1.x milestone closure

Audit date: 2026-10-03. M13 is immutable source evidence, not merge authority.
All 35 actual status entries were inspected as diffs or untracked file contents.
Mixed files use the dominant action class; intent/action columns explicitly separate
compatible product requirements from obsolete sub-implementations. No critical UNKNOWN.

Historical owner feedback remains valid where it asks for usable preferences,
independent interface/output language, understandable Following, secure credential
setup and local model discovery/preferences. Language and Following explanation
are already accepted. Configuration/reachability do not establish qualification.
The old Keychain shell implementation and hardcoded qualification are not reused.
The fixed reviewed Moonshot video-distillation profile needs no duplicate selector
or metadata row; it cannot serve Deep Analysis. Cloud connectivity/generation is
not tested against a real provider. Discovery is bounded loopback metadata only.

The historical local Summary INVALID_RESPONSE finding is not erased: accepted
Summary/Evidence authority and hardened local distillation paths supersede that
implementation; this closure uses fixtures, makes no live inference, and does not
claim the owner's real model output has been requalified. Seven-day M13 PASS and
M14/Gate B remain unexecuted. No owner sessions are manufactured.

| Path | Intent | Classification | Closure action | Current authority |
|---|---|---|---|---|
| docs/M13_7_DAY_DOGFOOD.md | Day 2 owner feedback and historical dogfood evidence | TEST-DOC-ONLY | Preserve as read-only evidence; record requirement/implementation distinction here; do not count new owner days | M13 journal and closure audit |
| frontend/m13-preday2.e2e.mjs | Select Following override explicitly in old smoke | TEST-DOC-ONLY | Adapt equivalent current UI scenario, preserve existing assertions | Closure Following/browser tests |
| frontend/src/workspace/App.test.tsx | Interest/config UX fixtures, old model route assumptions | TEST-DOC-ONLY | Add current requirement tests; no blanket replacement or weakened checks | Current workspace tests, closure interests/model tests |
| frontend/src/workspace/App.tsx | Editable global interests, Following inheritance, model/credential UX; language separation already accepted | STILL_REQUIRED | Forward-port interests/inheritance and compatible configuration UX; discard obsolete qualification/DA-later copy | Existing source policy, global_model_preferences, Phase 1C, closure ModelSettings |
| frontend/src/workspace/styles.css | Settings grouping and compact credential checkbox | STILL_REQUIRED | Reuse current panels; forward-port compact credential control only | Current DESIGN.md and closure credential-confirm styling |
| frontend/src/workspace/uiLanguage.tsx | Chinese interest/configuration labels; old model claims | STILL_REQUIRED | Forward-port relevant labels with current authority; reject old qualification assertions | Current zh-CN/en dictionary and closure ModelSettings |
| src/youtube_intel/backup_restore.py | Change expected schema to 29 | SUPERSEDED | No import; existing schema31 coverage includes DA/Research; no model metadata table needed | Accepted Backup/Restore schema31 and existing global_model_preferences |
| src/youtube_intel/local_api.py | Following inheritance projection and UI model/credential endpoints | STILL_REQUIRED | Forward-port policy_modes and machine-local secure credentials/discovery; retain current DA services | Current source-policy API, closure model_settings, V1X-DR-003 |
| src/youtube_intel/runtime.py | Doctor schema28 to29 | SUPERSEDED | No import; current Doctor validates31 | Accepted runtime schema31 |
| src/youtube_intel/runtime_composition.py | Resolve Moonshot credentials through secure store | STILL_REQUIRED | Forward-port resolver and refresh only; keep accepted M12 scoped distillation and Phase1C DA authority | M12QualifiedCloudProductionAuthorizationAuthority and V1X-DR-003 |
| src/youtube_intel/state.py | Persist separate fixed cloud profile/local candidate metadata; append029 | SUPERSEDED | Reuse existing global_model_preferences for non-authoritative preferences; fixed reviewed route needs no new row | Existing m005 preferences and Phase1C reviewed code authority |
| tests/integration/test_deep_analysis_persistence.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_provider_dispatch_crash_recovery.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_state_store.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task016c_phase_h2c_lineage_schema.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task018_domain_persistence.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task018a_claim_classification.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task018b_timed_evidence.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task020_preference_feedback.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task021_source_policy_filtering.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task022_personalized_distillation.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task022b_verified_outbound_input.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task023_topic_timeline.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task023a_source_run_persistence.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task023b_distillation_reservation.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task024_processing_orchestration.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task025_weekly_foundation.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/integration/test_task025a_saved_intelligence.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/unit/test_backup_restore.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| tests/unit/test_evidence_translation.py | Schema28→29 expected versions, migration-list tails/checksums | TEST-DOC-ONLY | Do not import schema29 assertions; accepted schema31 regressions already stronger | Current migration/authority/backend suites |
| frontend/m13-day2-settings.e2e.mjs | Historical Day2 interest/candidate/credential browser tests | TEST-DOC-ONLY | Use as requirements evidence; replace old route/qualification expectations with current closure browser acceptance | Closure frontend tests and real fixture browser audit |
| frontend/node_modules | Untracked symlink to M12 dependency directory | TEST-DOC-ONLY | Do not import symlink; isolated copy of existing accepted locked tooling in closure only | Accepted unchanged frontend package/lock files |
| src/youtube_intel/migrations/029_add_v1_model_configuration.sql | Historical/in-flight schema29 for competing model metadata | CONFLICTS_WITH_NEW_AUTHORITY | Never import or rename; no032 needed | Accepted 030 durable DA Evidence,031 Research; model preferences already persisted |
| src/youtube_intel/model_configuration.py | Discovery-derived active/qualified state, hardcoded cloud qualified, Keychain/probe implementation | CONFLICTS_WITH_NEW_AUTHORITY | Reject implementation; preserve compatible configuration requirement through new service; no external balance probe | Phase1C qualification authority, existing model preference; closure model_settings |
| tests/unit/test_model_configuration.py | Old model metadata/credential/probe tests | TEST-DOC-ONLY | Replace useful credential safety/discovery checks; reject hardcoded qualification expectations | test_closure_model_settings.py and Phase1C suites |

Counts: {"TEST-DOC-ONLY": 25, "STILL_REQUIRED": 5, "SUPERSEDED": 3, "CONFLICTS_WITH_NEW_AUTHORITY": 2}.

Preservation evidence: [before](../../handoffs/V1X-CLOSURE-PRESERVATION-BEFORE.json).
