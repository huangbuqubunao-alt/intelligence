# Frontend Product Architecture Amendment — Configurable Sources and Automation

Status: **PRODUCT OWNER FINAL APPROVAL REQUIRED**

Baseline preserved: [Frontend Product Architecture](FRONTEND_PRODUCT_ARCHITECTURE.md) at main@71f9328; repository version 0.1.0; GitHub PRIVATE; release posture **NO-GO**; frontend implementation **NOT STARTED**.

Scope: planning only. This amendment changes no frontend, HTTP API, Python code, SQLite migration, runtime behavior, provider adapter, configuration semantics, dependency, test, scheduled service, or side effect.

## Amendment decision

Revise the product positioning to **“a local-first, configurable, automatically running YouTube Intelligence workspace.”**

    CONFIGURE → SUBSCRIBE → SCHEDULE → DISCOVER → PROCESS → ANALYZE → ORGANIZE → REVIEW

This is an extension of the existing architecture, not a rewrite. It must use new application-service commands and persistent user-intent records; it must not turn the browser, scheduler, or configuration table into a way around the existing pipeline, scoring authority, provider gate, or v4 dispatch state machine.

The amendment preserves the existing non-negotiable boundaries:

- AuthoritativeScoringReader and VerifiedScoringRead remain the only persisted-scoring authority.
- The Deep Analysis finalizer remains the only trusted-success boundary.
- v4 dispatch remains fail-closed. AMBIGUOUS never gets an automatic scheduler retry.
- No silent fallback, semantic retry, repair, provider/model switch, or Use anyway.
- Credentials remain runtime-only and outside browser storage, YAML plaintext, SQLite provenance, logs, and DTOs.
- Note V2 and Weekly V2 keep their existing verification/admission boundaries.
- Configuring a source or schedule is not a release approval; the release remains NO-GO.

## Current facts and gap conclusion

| Capability | Existing fact | Gap / effect |
| --- | --- | --- |
| Channel configuration | channels.yaml contains ordered channel_id, enabled, priority only | Static bootstrap configuration; no source identity, URL, schedule, policy, source/video relation, or UI write path. |
| Discovery | DiscoveryService uses RSS plus a CAS cursor and atomically stores DiscoveryBatch | Reuse it, but bind it to a new source/run command rather than direct scheduling. |
| Video metadata | MetadataProvider fetches a known video_id and persists VideoRecord | No public Video URL parse/normalize/ingest command. |
| Pipeline/jobs | RuntimeOperations.process and PipelineOrchestrator.resume_video use jobs, attempts, leases, errors | Reuse it; automation must delegate rather than recreate stages. |
| CLI | check, process, retry, weekly, doctor, restricted smoke | Existing operations, not a browser API. check discovers YAML channels only; process needs a known video. |
| Scheduling | Two static, mutually exclusive launchd example plists | No schedule persistence, due calculation, run record, missed-run rule, or UI management. |
| Configuration | Typed YAML has global model/processing/cloud/storage values and an environment-variable name | No safe config-write/apply API. |
| Deep Analysis | OpenAI live 0/2 credential blocked; Kimi 1/2 SCHEMA_INVALID; Local unqualified/search closed | Configuration cannot make an unqualified model eligible or authorize TASK-016G. |

### YAML-only versus persistent sources

**Recommendation: use new SQLite/persistent Source records, not YAML-only.**

YAML remains suitable for static bootstrap settings. It cannot safely represent UI-created source identity, enable history, source policy, next/last run, source/video provenance, concurrent UI/scheduler updates, or execution identity. Browser-written YAML would add file atomicity, path, restart, validation, merge, and credential-adjacency risk without solving scheduling.

A future explicit import may seed persistent CHANNEL sources from channels.yaml. It must not silently create two competing source authorities or change existing CLI semantics.

## Source subscription model

MVP source types are CHANNEL and VIDEO_URL. PLAYLIST is future only and has no MVP parser, schedule, or UI route.

| Field | CHANNEL | VIDEO_URL | Status |
| --- | --- | --- | --- |
| source_id | opaque immutable UUID | opaque immutable UUID | NEW |
| source_type | CHANNEL | VIDEO_URL | NEW |
| display_name | user label or safe metadata label | user label or safe metadata label | NEW; label is not identity |
| canonical_url | normalized channel URL | normalized watch URL | NEW, backend-owned normalization |
| channel_id | required | filled only if metadata establishes it | Existing domain value, NEW source field |
| video_id | null | required after parse/confirmation | Existing domain value, NEW source field |
| enabled, created_at, updated_at | required | required | NEW |
| last_checked_at, next_check_at, last_success_at, error | applicable | one-shot intake/manual refresh only | NEW source projection |
| processing_policy_id, schedule_id | required / nullable schedule | required / nullable schedule | NEW |
| discovered_video_count, new_video_count | derived from links/runs | derived 0/1 | NEW derived values |

SourceSubscription is user intent and operational ownership; it is not a trusted video, score, provider result, or authority token. Canonical identity is immutable. Label, enabled state, policy, and schedule association use optimistic concurrency.

### Add Source UX

The user sees a single Add Source URL field. The backend, not browser JavaScript, validates allowed YouTube URL forms, normalizes identity, determines source type, and rejects unsupported/ambiguous forms.

    Paste URL
    → syntax validation and identity normalization
    → CHANNEL or VIDEO_URL preview
    → choose preset and schedule
    → Save source
    → optional separately confirmed Check now

**Save Source and Check now are two actions.** Save is a pure configuration write. It does not contact YouTube, call a provider, construct trusted state, or auto-run a pipeline. Check now is a network side effect: CHANNEL delegates to existing discovery; VIDEO_URL needs a new ingest command that uses existing metadata only after a source exists.

Under current governance, Check now remains PO-controlled. A later product authorization may make it a normal user-confirmed operation only after scope, audit, stop, and operational controls are approved.

### Sources page and source detail

Sources is a top-level page. It provides Add Source, search, Active/Disabled/Error filters, and a table with display name, type, channel/video identity, enabled, preset, schedule summary, last checked, next check, new-video count, and latest safe error.

**Source Detail recommendation: DRAWER.** A row opens a drawer with Identity, Processing, Schedule, Model (inherited read-only status), Recent Videos, and Activity. This avoids a top-level page. Promote it to a route only if future source history or permissions outgrow a drawer.

## Processing policy

Use named, versioned safe presets and two bounded product toggles. Do not offer an arbitrary pipeline builder.

| Control | MVP behavior | Dependency / boundary |
| --- | --- | --- |
| auto_process_new_videos | ON/OFF; ON asks the existing runtime to process newly source-linked video IDs | NEW orchestration policy; it does not create stage state directly |
| weekly_eligibility | Include/exclude this source's eligible completed videos from a future weekly selection | NEW membership filter; it cannot prove Weekly V2 eligibility |
| Discovery and metadata | mandatory when a source is checked | Existing discovery / pipeline predecessor |
| Transcript | not a user toggle | Required predecessor for scoring |
| Scoring | mandatory if automatic processing is ON | Existing single scoring stage and verified reader |
| Note | not independently configurable | Follows frozen high-value pipeline and authority rules |
| Deep Analysis | read-only capability status in MVP | No qualified live provider |
| Retry/fallback | no policy control | Existing no-silent-retry/no-fallback rule |

Initial presets:

- **Discover only:** record newly discovered videos; no automatic processing.
- **Standard processing:** discovery plus automatic processing of eligible new video IDs, only when the command scope is authorized.

The backend rejects illegal combinations. It cannot accept Note on / Scoring off, Deep Analysis on / Scoring off, or a source flag that turns an arbitrary row into a Weekly V2 candidate.

## Models, providers, and credentials

Provider UI has to distinguish configuration from authority.

| Field | Meaning | Current truth |
| --- | --- | --- |
| configured | non-secret profile/model setting is valid | Global typed YAML exists; no UI write today |
| credential available | backend can attest a provisioning mechanism, without value exposure | OpenAI gate is credential blocked |
| adapter available | adapter/profile can be composed | OpenAI fake-boundary qualified; Kimi implemented but isolated |
| qualified | frozen live protocol has passed | None: OpenAI 0/2; Kimi 1/2 SCHEMA_INVALID; Local unqualified |
| production eligible | qualified and selected by future authorized policy | None for Deep Analysis |
| authorized | current PO/run scope permits execution | No qualification or TASK-016G authorization |

The Settings → Models & Providers panel must show provider, model, provider kind,
configured, credential available, adapter available, qualification status,
production eligible, authorized, and a safe reason for each. It must not offer
a force-run, Use anyway, fallback, or direct SDK control.

**Recommendation: global model defaults, read-only in MVP; defer source-specific model override.** Existing models are global typed configuration and trusted scoring context. Per-source selection multiplies qualification, A3/cache/provenance, privacy/consent, scheduler, and test combinations. It cannot be a simple dropdown.

**Credential configuration: DEFER.** MVP shows only Configured, Not configured, Blocked, or Unavailable plus a reason. It never displays full/partial keys, uses localStorage, writes YAML plaintext, writes SQLite secrets, logs values, or invokes provider SDKs. Post-MVP credential provisioning needs a separately approved backend-owned OS/runtime mechanism.

## Automation and scheduler boundary

Maintain two distinct automation targets:

1. **Source Check** observes a CHANNEL for new video IDs, or performs the defined VIDEO_URL one-shot intake/metadata refresh.
2. **Weekly Generation** invokes the existing weekly command for the configured ISO week. It does not claim a verified Weekly V2 result.

MVP schedule controls are MANUAL, DAILY, and WEEKLY—not cron expressions. Source Check supports Manual/Daily; Weekly Generation supports Manual/Weekly. The Automation page shows name, target, schedule, enabled, last run, next run, status, and safe error. Future Edit, Enable/Disable, and Run now controls remain classified by side effect.

### Scheduler recommendation

**Choose A: keep launchd as the macOS trigger runtime, with a new persistent application-owned schedule projection and one due-work tick command.**

Do not build a resident internal scheduler daemon. Do not let the frontend edit plists or call launchctl. Current launchd examples are static and insufficient for dynamic Sources; a future operational layer may install one controlled tick trigger only after separate PO authorization.

    launchd tick or approved manual Run Now
    → SchedulerApplicationService.claim_due_work()
    → SourceCheckCommand or WeeklyGenerationCommand
    → existing RuntimeOperations / DiscoveryService / PipelineOrchestrator
    → existing Job, attempt, provider-dispatch, artifact, and logging boundaries

Forbidden paths:

    Scheduler → direct SQLite pipeline mutation
    Scheduler → YouTube transport or provider SDK
    Scheduler → direct trusted score/note/deep-analysis construction
    Frontend  → launchd plist / launchctl / credentials / SQLite

### Missed run, duplicate execution, and retry semantics

**Recommendation: RUN ONCE on the next eligible tick; do not replay every missed interval.** A sleeping/offline Mac produces one OVERDUE nominal run. The next tick claims it once and advances the schedule. This is useful for cursor-based discovery and avoids a burst of duplicate work.

Each execution receives a new immutable AutomationRun identity, unique on schedule_id plus nominal_due_at, with claim/lease. Source discovery and video processing are distinct:

- SourceDiscoveryRun records source, schedule, nominal due time, safe summary, and discovered IDs.
- Each selected new video gets a VideoProcessingRun linked to that source run and delegates to existing video-stage Jobs.

The scheduler may recover a schedule claim only before an external boundary. It never reclaims AMBIGUOUS v4 dispatch, silently reruns a terminal provider action, or turns FAILED_FINAL into a retry. Existing job leases, active-job uniqueness, idempotent discovery cursor, and dispatch state remain authoritative.

## Updated information architecture

### Final navigation recommendation

    Dashboard
    Sources
    Videos
      └─ Video Detail: Overview / Scoring / Note / Intelligence / History
    Weekly
    Automation
    Activity
    Settings
      ├─ General
      ├─ Processing Defaults
      ├─ Models & Providers
      ├─ Storage
      ├─ Advanced: Health, Doctor, qualification, backup/recovery, release
      └─ About

**Standalone System: MERGE into Settings → Advanced.** Health, Doctor, provider qualification, storage/backup posture, and release status matter, but are not normal primary navigation. Dashboard retains a concise summary and links to Advanced.

### Dashboard amendment

Dashboard becomes a personal intelligence workbench. The primary next action is review new intelligence or add a source, not inspect engineering metrics.

- This Week: ISO week/status and latest actual weekly record, labeled V1, verified V2, or unavailable.
- Recent Intelligence: recent completed video display DTOs; never fake Deep Analysis output.
- New Videos: source-linked new videos with actual pipeline states.
- Needs Attention: source/run/job failures and AMBIGUOUS dispatch.
- Sources Status: enabled, overdue/error counts, and freshness from server projections.
- Next Scheduled Run: next AutomationSchedule projection plus timezone, never a browser timer promise.
- Recent Processing: redacted activity/run summaries.
- Deep Analysis: OpenAI 0/2 credential blocked; Kimi 1/2 SCHEMA_INVALID; Local unqualified/search closed; no action button.

## API and application-service gap analysis

No HTTP API exists. Proposed routes are loopback/local-session API routes only. A backend boundary owns DTO validation, redaction, pagination, concurrency tokens, authorization state, and all repository access.

| Endpoint / command | Class | Existing / new work |
| --- | --- | --- |
| GET /dashboard | READ | New aggregate projection over existing and source data |
| GET /sources, GET /sources/{id} | READ | NEW source/read service |
| GET /videos, /videos/{id}, subresources | READ | Existing records partial; new redacted API |
| GET /weekly, /activity, /automation, /settings, /system | READ | New API; source/automation require persistence |
| POST /sources | PURE CONFIG WRITE | NEW normalized source/policy command; no network |
| PATCH /sources/{id} | PURE CONFIG WRITE | NEW optimistic source update; disable does not cancel in-flight external work |
| POST /sources/{id}/check | NETWORK SIDE EFFECT | NEW command reusing discovery/metadata; currently PO-controlled |
| POST/PATCH /automation | PURE CONFIG WRITE | NEW schedule/run configuration; activation does not install launchd |
| POST /automation/{id}/run | NETWORK / PIPELINE SIDE EFFECT | NEW claim/command; currently PO-controlled |
| PATCH processing defaults | FUTURE | New validation/reload/versioning contract; not MVP |
| Provider model selection | READ ONLY MVP | Safe global projection only |
| Credential provisioning | FORBIDDEN / FUTURE | Separate secure backend design |
| Qualification, dispatch mutation, raw output, auto retry/fallback, launchd install, backup/recovery | FORBIDDEN | Existing trust/operational boundaries prevail |

Every side-effect command returns a command/run receipt. The browser never gets a provider SDK call, direct Job/ProviderCall/dispatch mutation, or permission to treat retryable as a Retry button.

## Data model gap analysis

A future SQLite migration beyond current user_version 4 is required. This is a proposal, not an authorization to alter schema.

| Object | Why and fields | Authority / lifecycle / relationship |
| --- | --- | --- |
| SourceSubscription | source_id, type, canonical URL, channel/video ID, display name, enabled, policy ID, schedule ID, revision | New user-intent table. Canonical identity immutable; mutable user settings use concurrency revision. |
| SourceVideoLink | source_id, video_id, first discovery/run ID, timestamps | New unique source/video junction. It never changes VideoRecord authority. |
| ProcessingPolicy | preset, auto_process_new_videos, weekly_eligibility, schema version | New typed/versioned intent record, not an arbitrary pipeline graph or provider permission. |
| AutomationSchedule | target type/ref, MANUAL/DAILY/WEEKLY, weekday, local time, timezone, enabled, last/next due, revision | New application-owned state. launchd is only trigger runtime. |
| AutomationRun | run_id, schedule/source refs, nominal due, trigger kind, lease/status, timestamps, safe error, command/job links | New audit/claim record with unique schedule+nominal slot. It does not replace Jobs, attempts, or provider dispatch. |
| SourceCheckResult | safe counts/outcome | Prefer fields/projection from AutomationRun until an independent query need exists; do not create mutable counters early. |

Reuse unchanged: channel_cursors, videos, jobs, job_attempts, provider_calls, provider_dispatch_states, Deep Analysis persistence, and scoring lineage. New foreign keys may reference them, but no new record writes trusted scoring/provenance or reinterprets v4 dispatch.

## Reuse versus new work matrix

| Capability | Existing | Partial | New | Blocked | Recommended action |
| --- | --- | --- | --- | --- | --- |
| Source config | YAML channel IDs | Yes | persistent subscriptions | No | Add SourceSubscription; preserve YAML bootstrap |
| URL validation | No public URL command | Metadata has source URLs | backend normalizer | No | Add pure validation before persistence |
| Discovery | DiscoveryService/cursor | Yes | source/run binding | Real operation PO-controlled | Delegate through SourceCheckCommand |
| Video processing | runtime/pipeline/jobs | Yes | policy/run linkage | Real operation PO-controlled | Delegate; never recreate stages |
| Scoring | verified reader | Yes | display projection | No | Preserve sole authority reader |
| Note | V1 and deterministic V2 | Yes | safe display projection | V2 real output provider-blocked | Preserve boundaries |
| Weekly | report and pure V2 | Yes | schedule target/membership filter | Real V2 provider-blocked | Separate WeeklyGenerationCommand |
| Deep Analysis | contracts/persistence/gate | Yes | read status projection | no qualified provider/TASK-016G | Blocked UX only |
| Model config | global typed settings | Yes | safe projection/apply contract | Eligibility constrained | MVP read-only |
| Credential config | env-reference isolation | No | secure provisioning | not authorized | Defer |
| Scheduling | static launchd samples | Yes | schedule/tick/run persistence | launchd setup PO-controlled | Trigger plus application scheduler |
| Activity | jobs/logs/dispatch | Yes | source/run API projection | No | Extend read API |
| Doctor/storage/backup | doctor, artifacts, docs | Yes | last-observation model only | drill unauthorized | Show NOT RUN; invent no backup service |
| Frontend / HTTP API | none | No | shell, routes, API | No | Separate approved program |

## Change-size estimate

| Area | Size | Reason |
| --- | --- | --- |
| Frontend | MEDIUM-HIGH | Sources/Automation plus Dashboard and Settings changes |
| Backend API | HIGH | No HTTP layer exists |
| Persistence | MEDIUM-HIGH | source/policy/schedule/run/link migration |
| Scheduling | HIGH | due time, leases, missed runs, tick, concurrency, operations |
| Trust/security | HIGH | no qualification/credential/direct-state bypass |
| Testing | HIGH | migration, clock/DST, lease, duplicate tick, command/API/browser/adversarial cases |
| Operational setup | MEDIUM | controlled launchd tick deployment; no scheduler framework |

**Overall change size: MEDIUM-HIGH.** It is an extension, not a core rewrite. Approximate core backend reuse is **55%**: discovery, metadata, pipeline, jobs, errors, logs, doctor, scoring, Note, Weekly, and provider trust boundaries are reusable; source lifecycle, scheduling, API, and frontend are net-new.

## Five user journeys

### Journey 1 — First use

1. Open Dashboard and see unconfigured workspace plus Add Source.
2. Paste Channel URL; backend validates/normalizes without network.
3. Choose Discover only or Standard processing and Manual/Daily schedule. Deep Analysis remains unavailable.
4. Confirm Save; source configuration persists.
5. Dashboard shows source and projected next run.

**Not executable today:** source persistence, URL command, schedule model, API, and frontend are new. Save must not call YouTube.

### Journey 2 — Automatic discovery

1. A launchd-triggered tick finds one due Source Check.
2. It claims one AutomationRun, calls SourceCheckCommand, then existing RSS discovery/cursor persistence.
3. It records source/video links; Standard processing delegates selected videos to existing runtime/pipeline.
4. User opens Dashboard for New Videos and Recent Processing.
5. Activity shows run, downstream jobs, and safe failures.

**Not executable today:** schedule/run/tick service is new; real network/pipeline work remains PO-controlled.

### Journey 3 — Single video

1. Paste Video URL and confirm normalized config-only save.
2. Explicitly request Check now, or use a future defined one-shot intake.
3. Ingest command uses existing metadata path; pipeline progresses metadata → transcript → scoring only when authorized.
4. Video Detail shows verified scoring, Note availability, and history.
5. Deep Analysis remains unavailable until separate provider/output/PO gates close.

**Not executable today:** URL ingest/source linkage/API are new. No source action can force provider use or fabricate Note V2.

### Journey 4 — Weekly

1. Weekly schedule becomes due and claims one AutomationRun.
2. WeeklyGenerationCommand delegates to existing weekly service with configured timezone/current week.
3. Dashboard shows actual report status; Weekly links items to Video Detail.

**Not executable today:** schedule command/API are new; report/Vault write is PO-controlled. Real qualified-provider Weekly V2 remains blocked.

### Journey 5 — Failure

1. A source/run fails, or a downstream job terminates.
2. Dashboard Needs Attention links to Activity with source/run/video context and redacted reason.
3. User sees configuration/local/content error, FAILED_FINAL, FAILED_KNOWN, or AMBIGUOUS.
4. AMBIGUOUS explains that the provider may have received the request and no automatic retry occurs.
5. Only a future approved command may offer a scoped allowed action.

**Not executable today:** source/automation projection/API are new; existing job/dispatch semantics already support safe terminal distinctions.

## MVP and coordinated roadmap

### MVP include after PO approval

- Amended Dashboard; Sources/Add Channel/Add Video URL/Source Detail drawer.
- Persistent source identity/source-video links; two processing presets; source and weekly schedules.
- Manual/Daily Source Check configuration; Manual/Weekly Generation configuration.
- Videos, Video Detail, Weekly, Activity, Automation, read-only Models & Providers.
- Settings: General, Processing Defaults, Models & Providers, Storage, Advanced, About.
- Launchd-triggered app-owned tick only after separate operational authorization.

### Exclude / blocked

- Credential write UI, plaintext storage, source-specific model override.
- Unqualified model use, Use anyway, provider fallback/retry/repair.
- Cron UI, arbitrary pipeline builder, replay-all missed runs, frontend launchd management.
- TASK-016G, live provider qualification, Kimi/Local retry, real output acceptance, public SaaS/accounts, real Vault/backup/recovery action without approval.

### Implementation program after final approval

1. Persistence/contracts: source/policy/schedule/run schemas, migration, identity, lease/missed-run state machine.
2. Read API: redacted DTO/query boundary and authority/enum/blocked-state tests.
3. Config writes: normalizer and pure source/policy/schedule services with optimistic concurrency.
4. Frontend core: shell plus Dashboard, Sources/drawer, Videos, Detail, Weekly, Activity, Automation, Settings against fake API.
5. Runtime integration: commands delegate to existing discovery/weekly/pipeline boundaries.
6. Scheduler integration: due tick and launchd deployment plan; requires separate PO operational authorization.
7. Adversarial validation: migration, concurrency, DST, duplicate tick, disable/race, redaction, browser E2E, no-direct-SQL/provider review.

Phases 1–4 can be one coordinated program after dependency/API/schema approval. Phases 5–6 cross network/pipeline/operational side effects and remain separately PO-authorized. None authorizes credentials, provider qualification, TASK-016G, or release.

## Product Owner function approval table

| FUNCTION | USER VALUE | MVP | BACKEND SUPPORT | NEW WORK REQUIRED | SIDE EFFECT | TRUST RISK | RECOMMENDATION | PO DECISION |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Add Channel | Subscribe to channel | Yes | YAML only | source/normalizer/API | config write | source ≠ trusted video | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Add Video URL | Track one video | Yes | metadata accepts ID only | ingest/source linkage | config; optional network check | must not auto-process/provider-call | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Enable/Disable Source | Control future intake | Yes | YAML enabled only | persistent update | pure config | never cancels/retries provider | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Manual Check | Refresh source | Design yes | discovery/metadata reusable | command/receipt/API | network | cursor/adapter only; current PO control | DEFER execution | APPROVE / MODIFY / REMOVE / DEFER |
| Daily Check | Automated intake | Design yes | no dynamic scheduler | schedule/run/tick | network/pipeline | duplicate/missed-run | APPROVE design | APPROVE / MODIFY / REMOVE / DEFER |
| Weekly Check | Automated weekly generation | Design yes | weekly service | schedule target/command | Vault/report write | V1/V2 distinction | APPROVE design | APPROVE / MODIFY / REMOVE / DEFER |
| Processing Policy | Predictable automation | Yes | pipeline reusable | preset/policy/orchestration | can cause processing | no arbitrary graph | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Default Model | Explain current model | Partial read-only | typed global config | safe projection | none | configured ≠ qualified | APPROVE read-only | APPROVE / MODIFY / REMOVE / DEFER |
| Source-specific Model Override | Per-source model choice | No | none | major policy/provenance design | provider possibility | eligibility multiplication | DEFER | APPROVE / MODIFY / REMOVE / DEFER |
| Provider Credential Setup | Key provisioning | No | runtime isolation only | secure OS/backend design | credential | high secret risk | DEFER | APPROVE / MODIFY / REMOVE / DEFER |
| Automatic Video Processing | Less manual work | Design yes | pipeline/jobs | source run binding | pipeline/network | preserve job/dispatch | APPROVE design | APPROVE / MODIFY / REMOVE / DEFER |
| Weekly Generation | Produce report | Design yes | weekly service | command/schedule binding | Vault/report write | V1/V2/authorization | APPROVE design | APPROVE / MODIFY / REMOVE / DEFER |
| Run Now | Immediate action | No first button | commands partial | claim/confirmation | network/pipeline/Vault | no duplicate/retry bypass | DEFER | APPROVE / MODIFY / REMOVE / DEFER |
| Dashboard | Personal workbench | Yes | records partial | read API | read | honest blocked state | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Videos | Review inventory | Yes | records exist | read API | read | preserve state | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Video Detail | Inspect lifecycle | Yes | baseline partial | composite API | read | verified data only | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Weekly | Review outputs | Yes | report/pure V2 | read API/version label | read | never relabel V1/V2 | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Activity | Investigate failures | Yes | jobs/logs/dispatch | source/run projection | read | AMBIGUOUS terminal | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| Automation | Manage schedule config | Yes | static launchd only | schedule/run API | config/future I/O | scheduler boundary | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |
| System Health | Diagnose posture | Merge | doctor exists | last observation | read | no browser probe | APPROVE merged | APPROVE / MODIFY / REMOVE / DEFER |
| Settings | Inspect defaults | Yes/read-only | typed config | redacted projection | read | no YAML/secret write | APPROVE | APPROVE / MODIFY / REMOVE / DEFER |

## Final page approval table

| PAGE | CORE FUNCTIONS | MVP | RECOMMENDATION | PO DECISION |
| --- | --- | --- | --- | --- |
| Dashboard | This Week, intelligence, new videos, attention, source freshness, next run, provider summary | Yes | KEEP; make it a workbench | APPROVE / MODIFY / REMOVE |
| Sources | Add/list/filter/enable/policy/schedule/controlled check | Yes | KEEP | APPROVE / MODIFY / REMOVE |
| Source Detail | identity, processing, schedule, model, videos, activity | Yes | DRAWER | APPROVE / MODIFY / REMOVE |
| Videos | search/filter inventory | Yes | KEEP | APPROVE / MODIFY / REMOVE |
| Video Detail | overview, verified scoring, Note, Intelligence, History | Yes | KEEP contextual tabs | APPROVE / MODIFY / REMOVE |
| Weekly | actual weekly record and linked items | Yes | KEEP | APPROVE / MODIFY / REMOVE |
| Automation | schedule status/configuration/future Run now | Yes | KEEP | APPROVE / MODIFY / REMOVE |
| Activity | jobs, attempts, source/automation runs, failures | Yes | KEEP | APPROVE / MODIFY / REMOVE |
| Settings | General, defaults, providers, storage, Advanced, About | Yes | KEEP | APPROVE / MODIFY / REMOVE |
| Standalone System | health, doctor, qualification, backup/release | No | MERGE into Settings → Advanced | APPROVE / MODIFY / REMOVE |

## Adversarial review

| Attack | Correction |
| --- | --- |
| User config bypasses provider qualification | Rejected: configured, available, qualified, eligible, authorized are distinct; no eligible Deep Analysis provider exists. |
| Schedule bypasses runtime | Rejected: formal application commands only; no direct SQLite/transport/provider SDK path. |
| Duplicate provider call | Rejected: due-run claim, separate discovery/processing identity, existing leases/active uniqueness, v4 ambiguity. |
| Source config becomes trusted data | Rejected: source is user intent; video/score/result authority is unchanged. |
| Credential UX leaks | Rejected: masked status only; provisioning deferred. |
| launchd is treated as app scheduler | Rejected: launchd is external tick runtime; UI never edits it. |
| Silent retry / pipeline builder | Rejected: one catch-up run, no automatic retry/fallback, presets only. |
| Page explosion | Rejected: System merges into Settings; Source Detail is drawer; results stay in Video Detail. |
| Blocked Deep Analysis looks usable | Rejected: explicit unavailable reason and no action controls. |
| Current PO-controlled action becomes normal click | Rejected: every I/O command remains explicitly classified. |
| TASK-016 trust architecture is changed | Rejected: orchestration delegates to formal boundaries; no trust-state semantics change. |
| First-use loop absent | Corrected: normalize → config-only save → explicit check → schedule projection → Dashboard. |

Result after correction: **P0 = 0; release-critical P1 = 0.** Remaining gates are visible PO decisions, new implementation work, and existing provider/operational restrictions—not hidden capability claims.
