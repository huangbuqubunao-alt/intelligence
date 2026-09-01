# Frontend Product Architecture — Local-first YouTube Intelligence Workspace

Status: **PRODUCT OWNER PAGE APPROVAL REQUIRED**
Baseline audited: `main@3675912` (`0.1.0`)
Scope: planning only; no frontend, HTTP API, production code, tests, or dependencies are changed by this document.

## Decision summary

The product should be a desktop-first local workspace that explains the state
of video intelligence work, rather than a generic administrator dashboard or a
marketing surface. Its authoritative data stays in the Python application
services and SQLite/managed-artifact boundary. The frontend is a presentation
and command-request client only; it never reads SQLite, the Vault, internal
Python objects, provider SDKs, or credentials directly.

There is **no frontend or HTTP/API layer today**. The only runtime entry point
is `youtube-intel` / `python -m youtube_intel`, with `check`, `process`,
`retry`, `weekly`, `doctor`, and the restricted release-QA
`smoke-public-subtitles` command. The proposed frontend therefore remains
blocked on a future, explicitly approved application-service API task. It must
not make the release look ready: the current release posture is **NO-GO**.

### Current capability classification

| Class | Capability and honest product consequence |
| --- | --- |
| A — currently usable in code | CLI parsing and local application composition; video/job/artifact/provider-call state; scoring lineage; Deep Analysis contracts, validation, persistence/cache revalidation; deterministic Note V2 and Weekly V2 builders; JSONL operation logs; static launchd examples. Usability in a real environment still depends on configuration and authorization. |
| B — read-only usable | `doctor` is read-only and exposes safe check names/status/messages; repository reads expose video, job, attempt, provider-call/dispatch, report, and integrity-checked Deep Analysis data to Python application services. A configured `doctor` is operationally PO-controlled because it reads local resources and performs a bounded loopback Ollama check. |
| C — implemented, but requires explicit PO side-effect authorization | `check`, `process`, `retry`, `weekly`, real/temporary Vault use, configured doctor execution, backup/recovery drills, public smoke phases, and launchd installation/loading. A UI must request these operations through a future backend command boundary and must not present them as harmless clicks. |
| D — blocked by provider qualification | Deep Analysis live output, real qualified-provider Note V2/Weekly V2 output, and PO product acceptance. OpenAI is offline-adapter qualified but live `0/2` and credential blocked; no live provider is qualified. |
| E — future / unauthorized | TASK-016G; Kimi retry (production adapter `1/2`, Case 2 `SCHEMA_INVALID`); Local retry/search (closed and unqualified); provider/model fallback, automatic retry, output repair, credential provisioning in the UI, and release/push/tag actions. |

### Authority and trust rules

- `VideoRecord`, `JobRecord`, `ArtifactRecord`, `ProviderCallRecord`,
  `ProviderDispatchRecord`, `ReportRecord`, `VerifiedScoringRead`, verified
  persisted Deep Analysis reads, and runtime-admitted `VerifiedNoteV2Artifact`
  are backend authority-bound data. Frontend copies are display DTOs, never
  authority tokens.
- `NoteV2` is a deterministic presentation artifact, not authority. It may be
  shown only after the backend has established its source is a runtime-verified
  Deep Analysis success or an integrity-verified persisted read.
- `WeeklyV2` accepts only process-admitted `VerifiedNoteV2Artifact` values.
  The UI must not aggregate Notes, scores, or raw rows itself.
- The Deep Analysis finalizer is the only trusted-success boundary. Provider
  responses, SQLite rows before revalidation, hashes, request IDs, and client
  supplied JSON remain untrusted.
- Exact error/state values must be displayed; the UI may add explanatory text
  but may not collapse `UNKNOWN`, `AMBIGUOUS`, `FAILED_KNOWN`, or
  `FAILED_FINAL` into a green or retryable state.

## Information architecture

### Proposed MVP navigation

```text
Dashboard
Videos
  └─ Video Detail
       ├─ Overview
       ├─ Scoring
       ├─ Note
       ├─ Intelligence
       └─ History
Weekly
Activity
System
  ├─ Provider & qualification
  ├─ Health / Doctor
  └─ Storage / backup posture
Settings & About
```

`Video Detail` is the core work page. It uses tabs, not separate top-level
Scoring, Notes, or Deep Analysis pages: the video is the user's mental model,
and each result must remain visibly tied to its source, score, evidence, and
processing history. `System` contains operational surfaces that are not part
of normal video work. This prevents the product from becoming a large admin
console while keeping failures and trust state discoverable.

### Page inventory disposition

| Candidate | Decision | Reason |
| --- | --- | --- |
| Dashboard | Keep | Five-second operational orientation. |
| Videos | Keep | Primary inventory and entry to work. |
| Video Detail | Keep | The authoritative context for state, scoring, Note, intelligence, errors, and history. |
| Jobs / Processing Queue | Merge into Activity | Job queue and run history are one operational timeline. |
| Scoring | Merge into Video Detail / Scoring | A score is meaningful only for its video and verified lineage. |
| Notes | Merge into Video Detail / Note | Avoids an ungrounded document library and preserves Vault/privacy boundary. |
| Weekly Intelligence | Keep | A distinct time-windowed output and top-N review task. |
| Deep Analysis | Merge into Video Detail / Intelligence and System / Providers | Result context belongs to the video; global availability belongs to System. |
| Providers | Merge into System | Qualification is operational trust posture, not daily navigation. |
| Provider Qualification | Merge into System / Providers | Same source and decision context as provider state. |
| System Health / Doctor | Merge into System | One health view, keeping doctor status and prerequisites together. |
| Activity / Run History | Keep | Cross-video execution, failures, attempts, and safe logs require one focused page. |
| Errors / Failure Center | Merge into Activity | A saved filtered failure view, not a duplicate database. |
| Settings | Keep, read-only in MVP | Configuration visibility is valuable; writes and credentials are not currently a safe frontend capability. |
| Storage / Backup Status | Merge into System | Shows posture only; there is no current backup service/status model. |
| About / Version / Release Status | Merge into Settings & About and Dashboard | Version and NO-GO are context, not a destination by themselves. |

## Page specifications

All fields below are either concrete repository fields or safe, clearly marked
derived status. A proposed API must omit any field it cannot source without
breaking the stated authority/privacy boundary.

### 1. Dashboard

**User goal.** Know within five seconds whether the workspace is healthy, what
recently changed, what failed, whether Weekly exists, and whether Deep Analysis
is available.

**Primary story / entry.** On application launch, the operator lands here or
returns through the product logo.

**Layout and components.** A compact desktop two-column layout: a persistent
top release ribbon; a left `System posture` column; a wider `Recent work`
column. No charts. Use count cards only where a count is sourced from a defined
query.

| Module | Exact fields | Source / state |
| --- | --- | --- |
| Release ribbon | application version (`0.1.0` initially), release posture `NO-GO`, Git hosting posture `GitHub PRIVATE`, concise blocker link | package/version and release-signoff document/config endpoint; `NO-GO` is not inferred from UI health. |
| System posture | doctor overall status; Config, Data directory, SQLite, Vault, yt-dlp, MLX Whisper, Ollama, Local scoring model, Cloud tokenizer when enabled, Cloud ON/OFF | future safe `DoctorReport` projection; absent until configured doctor is authorized/run. |
| Provider posture | `available`, `configured`, `qualified`, and `blocked` labels for OpenAI, Kimi, Local; qualification count/reason | controlled provider-gate status, never connection probing by the browser. |
| Video work | total video count; count by `pipeline_status`; most recently `updated_at` videos | new read projection over `VideoRecord`; counts are derived server-side. |
| Recent activity | timestamp, level, event, `run_id`, `stage`, optional `video_id`, `job_id`, error code, duration | redacted `operations.jsonl` projection; no raw logs/tracebacks. |
| Attention needed | final job failures: `job_id`, `video_id`, `target_stage`, `last_error_code`, `last_error_message`, `updated_at`; ambiguous dispatch count | `list_failed_video_jobs` and provider-dispatch read service. |
| Weekly | requested ISO week, timezone, report `status`, `relative_path` only when authorized to expose, `updated_at` | `ReportRecord`; do not claim a Weekly V2 result merely because a V1 report row exists. |

**Status / empty / loading / error / blocked.** The initial screen is
`UNCONFIGURED` when no approved backend connection/configuration exists;
`LOADING` shows skeleton rows, not zeroes; `EMPTY` says no videos have been
recorded; an API error says status cannot be read. The Deep Analysis module is
currently `UNAVAILABLE — no qualified live provider`; it explicitly shows
OpenAI `0/2 / credential blocked`, Kimi `1/2 / SCHEMA_INVALID`, and Local
`unqualified / search closed`. There is no action to retry, auto-fallback, or
use an unqualified provider.

**Actions / classification.** Navigate to Videos, Activity failures, Weekly,
System, and Settings. All are read-only. No dashboard execution button in MVP.

**Read/write classification.** Read-only. The dashboard submits no command and
cannot change a job, provider, Vault, configuration, or release state.

**Navigation.** In: launch, logo. Out: the destination links above. Small
window: stack posture before recent work; preserve the release ribbon.

**MVP required:** YES.

### 2. Videos

**User goal.** Find a video and understand its durable processing state without
opening a raw database.

**Primary story / entry.** Dashboard `Video work`, top navigation, or a weekly
item opens the list; selecting a row opens Video Detail.

**Layout and components.** Search by title/channel/video ID; status filters;
a compact sortable table with a detail drawer only on small windows. Pagination
and query parameters are server-owned.

**Fields.** `video_id`, `channel_id`, `channel_name`, `title`, `source_url`,
`published_at`, `duration_seconds`, `default_language`,
`available_languages`, `live_status`, `availability`, `pipeline_status`,
`pipeline_version`, `score`, `should_summarize`, `discovered_at`, `updated_at`,
`completed_at`, and `authoritative_scoring_job_id`. Derived display statuses
are limited to transcript/scoring/note/intelligence availability derived by a
backend query from stage/job/artifact authority; the browser must not guess
them from null values.

**Status / empty / loading / error / blocked.** Retain all actual
`PipelineStatus` values, including `DEFERRED`, `LOW_VALUE_READY`, and
`SKIPPED_DURATION_LIMIT`. `Availability` shows `public`, `unavailable`,
`private`, `deleted`, or `restricted` verbatim. Empty means no stored videos;
not “YouTube has no videos.” Loading uses table skeletons; an API failure says
that the local video inventory could not be read and links to System. A
provider-related intelligence field may be blocked, but the video itself stays
visible and its exact pipeline state is never replaced with that blocked label.

**Actions / classification.** Open Video Detail, copy a video ID, and open a
source URL only through an ordinary browser link. Filtering/sorting are
read-only. A future `Process` request is PO-authorized and omitted from MVP.

**Read/write classification.** Read-only list/query surface. Any process or
retry request is a future Category-C command request, never an optimistic row
state change.

**Navigation.** In: Dashboard, Weekly, Activity. Out: Video Detail. Small
window: title/channel first; metadata moves into the row drawer.

**MVP required:** YES.

### 3. Video Detail

**User goal.** Inspect one video's evidence-backed intelligence lifecycle in
one place and understand exactly why a result is missing.

**Primary story / entry.** Open a video from Videos, a failure from Activity,
or a Weekly item.

**Layout.** Header with title, channel, source URL, `pipeline_status`, score
when available, `updated_at`, and a visible trust/release note. Below it, five
tabs: **Overview**, **Scoring**, **Note**, **Intelligence**, and **History**.
On a small window use a horizontal tab strip; do not hide failed states behind
an overflow menu.

| Tab | Components and concrete fields | Backend source | State behavior |
| --- | --- | --- | --- |
| Overview | Metadata: `video_id`, `channel_id`, `channel_name`, `title`, `description` (only through a bounded presentation field), `source_url`, `published_at`, `duration_seconds`, language list, `live_status`, `availability`; pipeline timeline: exact `pipeline_status`, `pipeline_version`, `discovered_at`, `updated_at`, `completed_at` | `VideoRecord` projection | `CONTENT_UNAVAILABLE`, private/deleted/restricted availability, `DEFERRED`, and duration skip remain visible. |
| Scoring | `score`, `should_summarize`; verified scoring only: `schema_version`, `reason`, `topics`, `dimensions` (`technical`, `business`, `product`, `originality`, `practicality`, `industry_impact`) when present, `provider`, `model`, `prompt_version`, `request_hash`, `output_language`, plus `scoring_success_provenance` (`PRIMARY` or `REPAIR_H2C`) and authoritative scoring job/artifact identifiers | Future projection from `AuthoritativeScoringReader.read()` / `VerifiedScoringRead`, never a raw scoring artifact | `NOT_AVAILABLE` if no verified scoring read; a legacy/raw artifact must never be styled as verified. |
| Note | V1 managed-note metadata, if a backend can safely prove and expose it; Note V2: `schema_version`, `identity`, `video_id`, `language`, fixed sections, cited evidence references (`evidence_id`, source, excerpt, start/end seconds), provenance identities, provider/model IDs | Controlled managed-artifact renderer for V1; `build_note_v2` only from verified Deep Analysis input for V2 | **Current Note V2 status: not materialized as a persisted product view and no qualified live output exists.** Show this truth rather than a blank fake note. Never crawl the Vault from the browser. |
| Intelligence | Deep Analysis availability card; verified persisted result metadata if present: `result_identity`, cache eligibility, A1/A2/A3, validation-policy identity, provider/adapter/model identity, payload scope, scoring request hash/provenance, content/provenance identity, `created_at`, `validated_at`; output only after backend revalidation | `DeepAnalysisPersistenceStore.read_persisted_deep_analysis_result`, which returns a verified read or cache miss | Current default is `UNAVAILABLE`. Raw provider response, raw DB row, and cache key are never viewable as a trusted answer. |
| History | Jobs and attempts: `job_id`, `job_type`, `target_stage`, status, `attempt_count`, `max_attempts`, availability/lease/created/updated/finished timestamps, `last_error_code`, `last_error_message`; provider calls and dispatch: request hash, operation, provider/model, call status, token/cost observations when present, dispatch status and update time | `JobRecord`, `JobAttemptRecord`, `ProviderCallRecord`, `ProviderDispatchRecord` projections | A `FAILED_FINAL` job and `AMBIGUOUS` dispatch are never merged. `AMBIGUOUS` says the provider may have received the request; automatic retry is prohibited. |

**Actions / classification.** Read-only tab navigation, copy non-secret IDs,
and controlled opening of a known source URL are MVP-safe. `retry`, `process`,
or writing a note/report are PO-authorized side effects and absent. The detail
page must never submit provider output, construct a trusted score/note, or
change dispatch/cache state.

**Status / empty / loading / error / blocked.** A missing video is `NOT_FOUND`;
an absent tab source is rendered as its precise absence reason, not as an empty
success. Each tab uses a compact skeleton while its read DTO loads. An API or
integrity failure shows a safe error plus Activity/System navigation; it does
not reveal raw data. Intelligence is currently blocked globally by no qualified
live provider, while an existing per-video `AMBIGUOUS` dispatch is terminal for
automatic recovery and remains separately visible in History.

**Read/write classification.** Read-only, except normal external source-link
navigation. All pipeline, artifact, provider, cache, Note, report, and job
mutations are outside this page's MVP contract.

**Navigation.** In: Videos, Dashboard, Weekly, Activity. Out: related job in
Activity, related weekly report, System provider state, and back to its list.

**MVP required:** YES.

### 4. Weekly

**User goal.** Review the recorded weekly report for a configured ISO week and
trace every displayed item back to its video.

**Primary story / entry.** Dashboard Weekly module or top navigation.

**Layout and fields.** Week selector (read-only query parameter), timezone,
ISO year/week, report `status` (`PENDING`/`WRITTEN`), `report_id`,
`relative_path` only when safely exposed, content hash, created/updated time.
For a verified Weekly V2 rendering: `schema_version`, `identity`, `top_n`,
period start/end, and each item’s `video_id`, `title`, `source_url`, language,
`ranking_score`, `ranking_reason`, one-sentence summary, and themes. Items
link to Video Detail.

**Critical distinction.** The existing reports table and V1 weekly renderer
are not proof of a Weekly V2 object. Weekly V2 is deterministic only over
runtime-admitted `VerifiedNoteV2Artifact`; a UI does not recompute it and does
not label V1 as V2.

**Status / actions.** Empty: no report record for the requested configured
week. `PENDING` is visible. `WRITTEN` may link to a controlled backend rendering
when safe. Generating a week calls the CLI's write path and is PO-authorized,
so no button in MVP. Current real qualified-provider Weekly V2 output is
`BLOCKED — no qualified live provider`; this is not a failure of the pure
Weekly V2 implementation. Loading uses report/header and item skeletons; an
API/read-integrity error states that the requested weekly view cannot be
verified and must not fall back to raw Vault content.

**Read/write classification.** Read-only. `weekly` generation writes a report
and potentially a managed Vault artifact, so it is a future Category-C command
only after explicit authorization.

**Navigation / small window.** In: Dashboard, Video Detail. Out: Video Detail
and Activity run. On narrow windows, item cards replace the table.

**MVP required:** YES, as a report/status reader; verified V2 content remains
conditional on a safe backend read projection.

### 5. Activity

**User goal.** Investigate work that ran, is pending, or failed without losing
the video and trust context.

**Primary story / entry.** Dashboard attention card, Video Detail History, or
top navigation.

**Layout and components.** A status/filter bar; a job table; an expandable
attempt timeline; a redacted run-event panel; and a prominent `Failures`
saved filter. Separate visual tokens distinguish job status, provider-call
status, and dispatch status.

**Fields.** Job fields from `JobRecord`; attempt fields from
`JobAttemptRecord`; provider-call fields from `ProviderCallRecord`; dispatch
fields `request_hash`, `status`, `updated_at`; log fields are only the
redacted JSONL contract: timestamp, level, event, run ID, stage, safe message,
optional video/job IDs, error code, duration. The page must not enumerate raw
artifact bytes, credentials, configuration values, subtitles, model responses,
notes, absolute paths, or tracebacks.

**Error and trust UX.** Display exact domain codes including
`CONTENT_UNAVAILABLE`, `INVALID_RESPONSE`, `CAPABILITY_UNAVAILABLE`,
`CONFIG_INVALID`, `PERMISSION_DENIED`, `LOCAL_RESOURCE`, and
`TRUST_INTEGRITY_INVALID`. Provider-specific failures retain their stage/code
(for example `SCHEMA_INVALID`, `TIMEOUT`, `NETWORK_FAILURE`, `AUTH_REQUIRED`).
For `UNKNOWN` show “outcome could not be established.” For `FAILED_KNOWN`, show
the known failure. For `AMBIGUOUS`, state: “The request may already have been
received by the provider. The system will not automatically retry; an operator
must make an explicit future decision.” For `FAILED_FINAL`, state that its job
is terminal. Do not show automatic Retry for any of these states.

**Actions / classification.** Filter, inspect, copy IDs, and navigate to the
video are read-only. Future retry/process controls belong behind an explicit
PO-authorized command request, required confirmation, scope display, and
backend revalidation; they are excluded from MVP.

**Status / empty / loading / error / blocked.** Empty distinguishes “no events
match this filter” from “log source not configured.” Loading is a timeline/table
skeleton. A log/API failure says only that activity cannot be read. A final or
ambiguous operation remains a visible terminal/decision-needed state, never a
disabled-but-implicitly-safe Retry action.

**Read/write classification.** Read-only. The page has no in-place mutation,
automatic recovery, provider redispatch, or operational-log deletion.

**Navigation / small window.** In: Dashboard, Video Detail. Out: Video Detail,
System Providers. Small window uses an event timeline rather than a wide table.

**MVP required:** YES.

### 6. System

**User goal.** See system health, provider qualification, storage posture, and
operational boundaries without mistaking a diagnostic for a release approval.

**Primary story / entry.** Dashboard system card or top navigation.

**Layout.** Three fixed sections: **Health**, **Providers & qualification**,
and **Storage & operations**. It is one page because all sections answer
“Can this local workspace safely do what I am asking?”

| Section | Fields / components | Current product state |
| --- | --- | --- |
| Health | Doctor check name, `PASS`/`FAIL`/`ON`/`OFF`, safe message, blocking flag, last observation timestamp and observation source | No configured doctor evidence is assumed. `doctor` is a backend operation, not browser probing. |
| Providers & qualification | provider ID/kind, adapter ID/version, configured flag, available flag, qualified flag, qualification cases completed/required, qualification state, reason, provider/model/fallback policy, payload scope, latest dispatch state when it exists | OpenAI: configured profile/offline adapter qualified, live `0/2`, credential blocked. Kimi: production adapter live unqualified, `1/2`, Case 2 `SCHEMA_INVALID`; not default/fallback. Local: unqualified; search closed; future offline/privacy only. |
| Storage & operations | data/SQLite health status; managed Vault boundary status; artifact retention classes (`EPHEMERAL_AUDIO`, `RAW_RESPONSE_30D`, `LONG_LIVED`); reports status; JSONL logs posture (30-day policy, no automatic deletion); backup/recovery posture; static launchd example status | No backup/recovery status service or completed real drill exists. Display `NOT RUN / requires explicit PO authorization`, not “protected.” launchd examples are static only and no service is installed. |

**Provider/Deep Analysis blocked state.** The global card must say:

> Deep Analysis is unavailable. No live provider is qualified. OpenAI is live
> qualification `0/2` and credential blocked; Kimi is `1/2` with
> `SCHEMA_INVALID`; Local is unqualified and its search is closed.

It contains no `Try again`, `Auto fallback`, `Use anyway`, provider switch, or
credential field. A future authorized two-case OpenAI qualification package is
not an in-product user action until the PO separately attests an approved
ephemeral credential mechanism and authorizes its bounded execution.

**Actions / classification.** All MVP system actions are read-only navigation
and refresh by GET. A future `Run doctor` is Category C, because the configured
command accesses local resources and loopback Ollama. Backup/recovery,
launchd, smoke, credential, or provider qualification requests are not MVP
controls.

**Status / empty / loading / error / blocked.** Before a safe observation the
Health section says `NOT OBSERVED`, not healthy. Loading retains previous
observation time or uses skeletons; an API failure says system posture is
unknown. Each unavailable resource/provider has its reason alongside the badge.
Operational actions and all unqualified providers are explicit blocked states,
not empty cards.

**Read/write classification.** Read-only. No browser-triggered health probe,
backup, recovery, launchd action, provider dispatch, or qualification attempt.

**Navigation / small window.** In: Dashboard, Video Detail, Activity. Out:
Activity filtered to a provider/job; Settings. Stack the three sections and
keep qualification reason adjacent to every colored state badge.

**MVP required:** YES.

### 7. Settings & About

**User goal.** Inspect effective, non-secret configuration and understand the
current local/release posture.

**Primary story / entry.** Top navigation or Dashboard release ribbon.

**Layout.** Five read-only groups plus an About footer. Values come from a
backend redacted configuration projection, never a client-side YAML read.

| Group | Safe visible fields | Write posture |
| --- | --- | --- |
| General | timezone, output language, transcript-language preference | Read-only in MVP. |
| Processing | worker concurrency (fixed V1 value), maximum video duration, summary score threshold, weekly top N, retry timing/attempt policy, HTTP/local/cloud timeout policy | Read-only in MVP; changes alter processing behavior and need a separately designed config-validation/apply path. |
| Storage | relative data/log/template directory labels; managed Vault availability/boundary status; retention policy labels | Do not show absolute Vault path in ordinary UI. No browser filesystem picker or direct Vault write. |
| Providers | cloud enabled/disabled, provider/model identifiers, tokenizer readiness, selected-evidence/privacy policy, local scoring/analysis model identifiers and digest readiness | Show `api_key_env` only as a redacted mechanism label if needed; never read/display a key. Credential provisioning is external/future. |
| Advanced | schema version, configuration validation outcome, static launchd-example availability, release posture | No config-editor, raw YAML editor, launchctl button, or database repair action. |

**About.** Version, local-first description, GitHub PRIVATE controlled-source
posture, `NO-GO`, and a concise list of release blockers: no qualified live
provider, no PO acceptance of real qualified-provider output, and unrun
authorized operational gates. The page never claims production readiness.

**Status / actions.** Missing configuration is a clear `CONFIG_INVALID`/
unconfigured state, not a blank form. View-only in MVP. Small window uses
accordions with value/reason text always exposed. Loading uses group-level
skeletons; a redacted-config API failure preserves the distinction between
“cannot inspect configuration” and “configuration invalid.” Credential editing,
ordinary YAML editing, and filesystem selection are blocked/future, not hidden
form controls.

**Read/write classification.** Read-only. No config save, secret entry,
localStorage credential persistence, raw YAML write, database repair, or
launchd mutation.

**MVP required:** YES.

## Core video workflow

```text
Dashboard → Videos → Video Detail
                       ├─ Scoring (VerifiedScoringRead only)
                       ├─ Note (controlled V1 metadata / verified Note V2 only)
                       ├─ Intelligence (verified persisted result or unavailable)
                       └─ History → Activity
Dashboard / Video Detail → Weekly → Video Detail
Dashboard / Activity / Video Detail → System → Settings & About
```

The authoritative layer is the runtime/application service plus its verified
read boundaries. The presentation layer is every route, table, badge, summary,
and tab described above. The frontend can format a known enum or timestamp; it
cannot infer trust, validate an untrusted provider response, derive a Weekly,
write an artifact, or choose a retry/fallback strategy.

## Backend integration boundary

### Existing status

**No HTTP/API layer exists.** There is no existing React, TypeScript, Vite,
Next.js, `package.json`, frontend route, or Python web framework. The frontend
must therefore not be connected to SQLite or Python modules directly. A new
local API must be a separate, authorized backend/application-service task.

### Proposed minimal local API (not implemented)

All endpoints are loopback/local-session only, versioned, and return explicit
DTOs. A query service owns joins, pagination, integrity checks, redaction, and
field allowlists. It is the only API component allowed to call repositories or
application services. It returns no raw provider request/response bodies,
credentials, absolute paths, Vault contents, internal Python objects, or
unverified artifacts.

| Class | Proposed route | Contract |
| --- | --- | --- |
| GET | `/api/v1/overview` | Dashboard aggregate: explicit observation timestamps, video/job counts, recent safe activity, weekly report status, release/provider posture. |
| GET | `/api/v1/videos?query=&pipeline_status=&availability=&cursor=` | Paginated `VideoRecord` display DTO, with server-derived display statuses and no transcript body. |
| GET | `/api/v1/videos/{video_id}` | Video Detail header/overview DTO. |
| GET | `/api/v1/videos/{video_id}/scoring` | Either `verified: true` plus verified scoring DTO/provenance or `verified: false` with an absence reason; never raw scoring JSON. |
| GET | `/api/v1/videos/{video_id}/note` | Controlled note metadata/rendering only after backend ownership/integrity checks; distinguishes V1, verified Note V2, absent, and blocked. |
| GET | `/api/v1/videos/{video_id}/intelligence` | Verified persisted Deep Analysis DTO or explicit unavailable/cache-miss/trust-invalid state; never raw response bytes. |
| GET | `/api/v1/videos/{video_id}/history` | Job/attempt/provider-call/dispatch display DTOs with redacted errors. |
| GET | `/api/v1/weekly/{iso_year}-W{iso_week}` | Report record plus a separately typed `weekly_version`/availability; never relabel V1 as Weekly V2. |
| GET | `/api/v1/activity?status=&stage=&video_id=&cursor=` | Paginated jobs, attempts, dispatch states, and redacted events. |
| GET | `/api/v1/system` | Last safe DoctorReport observation, provider qualification record, storage/backup/launchd posture, capability reasons. |
| GET | `/api/v1/settings` | Safe, redacted effective configuration and version/release DTO. |
| Safe POST | **None in MVP.** Refresh is GET; no current state-changing CLI action is unconditionally safe. |
| PO-authorized POST (future) | `/api/v1/commands/check`, `/process`, `/retry`, `/weekly`, `/doctor`, `/qualification/openai` | Separate command-request resources only. Each must require explicit authorization context, validated finite scope, confirmation, audit record, backend revalidation, and no automatic retry/fallback. Their designs are out of scope here. |
| Forbidden | Direct SQLite/Vault/filesystem access; provider-SDK calls; credential entry/storage; raw `Trusted*` object serialization; raw provider output submission; dispatch/call/cache state mutations; auto-retry/fallback; release/push/tag/launchd/backup actions | The API returns `403`/capability reason rather than inventing an unsafe workaround. |

### Error contract for the frontend

Every response should carry a stable `state` and, when applicable, a redacted
`code`, `message`, `retryable` flag, `run_id`, `job_id`, `video_id`, and stage.
`retryable: true` is informational only; it does not authorize a UI retry
button. For a v4 dispatch `AMBIGUOUS`, use a dedicated semantic state rather
than mapping it to a generic 5xx or `FAILED_KNOWN`.

## Recommended frontend technical architecture

**Recommendation: React + TypeScript + Vite.** This is a local desktop/local
web UI with a Python backend, not a public SEO/SaaS product. Vite keeps the
renderer lightweight, avoids Next.js server/runtime duplication, and cleanly
separates the future Python loopback API from the UI bundle.

- Use an approved, future local loopback API adapter with generated-or-handheld
  TypeScript DTOs that mirror the explicit API schemas, not Python internals.
- Use a small router (six top-level navigation entries plus Video Detail
  tabs), native fetch/query caching with request cancellation, and URL-backed
  filters. Do not add a global client store for authoritative state.
- Use a small accessible component primitive set (navigation, table/list,
  tabs, badges, alert, empty/loading/error panels, drawer, confirmation
  dialog). Select/install any component library only in its own dependency
  approval task; this audit adds none.
- Test API client state mapping and routes with unit/component tests; test
  browser flows against a fake local API; add contract tests in Python for
  DTO redaction, enum preservation, and authority rejection. Do not use live
  providers, real Vaults, or credentials for UI tests.
- Build integration should package the static UI with the local runtime only
  after a separate packaging/security review. No network-hosted frontend or
  public SaaS assumptions are part of this proposal.

## Visual direction

Professional, calm, and dense enough for investigation: a MacBook-first
workspace rather than an AI landing page or enterprise admin console.

- Left navigation, a narrow top release/status bar, and one 1120–1280px
  reading-width content column; wide tables may use the remaining desktop
  space but must collapse into cards/timelines on smaller windows.
- Neutral paper/charcoal surfaces, restrained blue for navigation/selection,
  and semantic status colors paired with explicit text. `NO-GO`, blocked,
  ambiguous, and failed must not rely on color alone.
- Use cards only for bounded orientation modules (Dashboard/system posture);
  use aligned tables for videos/jobs and readable sections for the detail page.
  Avoid decorative charts, inflated KPIs, animated counters, and fake trends.
- Typography: one clear page title, compact section titles, monospace only for
  IDs/hashes/schema values, and full explanatory text alongside status badges.
- Empty states explain what data is absent and the legitimate next context;
  blocked states explain the exact gate and prohibited automatic action. Error
  states retain safe code/reason and a navigation path to System/Activity.
- Support light and dark mode from the first design-system pass; desktop-first
  does not mean desktop-only. Maintain keyboard-visible focus, semantic table
  headers, tab keyboard behavior, and text contrast. Screenshot review alone
  cannot certify accessibility; implementer must test it separately.

A separate `DESIGN.md` is deliberately deferred: no frontend implementation or
visual-token decision has PO approval yet. This section is the persistent
visual direction for the approval round and should be converted into a
design-system reference only after page scope is approved.

## Recommended implementation plan after page approval

### Phase 1 — shell and contracts

Create the Vite/React shell, local routing, visual tokens, status components,
and typed read DTO boundary. This requires a separate dependency/API/packaging
approval and does not expose a real database or provider.

### Phase 2 — read-only core

Implement Dashboard, Videos, Video Detail overview/scoring/history, Weekly
report status, Activity, System, and Settings against a fake API first, then a
new redacted Python query-service API. Keep Notes/Intelligence truthful when
the backend returns absent or blocked.

### Phase 3 — safe interactions

Only after PO approves a command boundary: add non-destructive in-app
navigation, copy IDs, local source opening, and any explicitly authorized
command-request UI. `check`, `process`, `retry`, `weekly`, and doctor are not
implicitly safe simply because they are CLI commands.

### Phase 4 — blocked/provider/system UX

Finish exact provider qualification, v4 dispatch `AMBIGUOUS`, unavailable
Deep Analysis, doctor-observation age, backup/recovery-not-run, and `NO-GO`
surfaces. Do not add provider fallback, credential forms, or TASK-016G.

### Phase 5 — integration tests and polish

Run API redaction/contract tests, UI state tests for every enum/error/empty/
loading/blocked state, keyboard/small-window checks, and fake-API browser
flows. Re-run a trust-boundary review before any real-environment integration.

One implementation task can reasonably combine Phases 1–2 and the read-only
parts of Phase 4 once the API boundary and dependencies are explicitly
authorized. Phase 3 command requests, real Vault display, configured doctor,
provider qualification, and all real-output flows should remain separately
approved/blockable work because they cross actual side-effect or provider gates.

## Product Owner page approval table

| PAGE | PURPOSE | MVP | CURRENT BACKEND SUPPORT | BLOCKERS | RECOMMENDATION | PO DECISION |
| --- | --- | --- | --- | --- | --- | --- |
| Dashboard | Five-second system/work/release orientation | Yes | Partial: state/log/doctor/provider records exist; no API or aggregate query | No HTTP API; configured observations require authorized environment | APPROVE | APPROVE / MODIFY / REMOVE |
| Videos | Searchable inventory and state overview | Yes | Partial: `VideoRecord` and processing list exist; no general list API | No HTTP API; add read projection | APPROVE | APPROVE / MODIFY / REMOVE |
| Video Detail | Single authoritative work context with tabs | Yes | Partial: video/job/attempt/verified scoring/Deep Analysis/Note contracts exist; no composite API | No HTTP API; Note V2 not materialized; live Deep Analysis unavailable | APPROVE | APPROVE / MODIFY / REMOVE |
| Weekly | Review weekly record and trace items to videos | Yes | Partial: reports/V1 weekly and pure Weekly V2 exist; no UI/read API | No HTTP API; no real qualified-provider Weekly V2 output | APPROVE | APPROVE / MODIFY / REMOVE |
| Activity | Queue, attempts, failures, safe run history | Yes | Partial: job/attempt/call/dispatch/log records exist | No HTTP API; preserve redaction and AMBIGUOUS semantics | APPROVE | APPROVE / MODIFY / REMOVE |
| System | Health, provider qualification, storage/operations posture | Yes | Partial: doctor/provider gate/storage artifacts/static launchd evidence exist | No HTTP API; doctor/operational actions are PO-controlled | APPROVE | APPROVE / MODIFY / REMOVE |
| Settings & About | Safe config visibility, version, NO-GO explanation | Yes | Partial: typed config/version/release records exist | No HTTP API; credential/config editing unsafe/unapproved | APPROVE as read-only | APPROVE / MODIFY / REMOVE |
| Standalone Scoring | Separate scoring destination | No — merge | Exists only as authority-bound per-video result | Would split score from its video/lineage | REMOVE; use Video Detail tab | APPROVE / MODIFY / REMOVE |
| Standalone Notes | Separate note library | No — merge | V1 managed artifact / deterministic Note V2 contracts; no safe browser read API | Vault/privacy and V2 materialization | REMOVE; use Video Detail tab | APPROVE / MODIFY / REMOVE |
| Standalone Deep Analysis | Global Deep Analysis destination | No — merge | Contracts/persistence exist; no qualified live provider | Would suggest availability and duplicate provider state | REMOVE; use detail tab + System | APPROVE / MODIFY / REMOVE |
| Standalone Providers/Qualification | Separate admin page | No — merge | Provider records/gate exist | Duplicate System and encourages unsafe action | REMOVE; use System section | APPROVE / MODIFY / REMOVE |
| Standalone Errors / Backup / About | Multiple narrow admin pages | No — merge | Error records; no backup service; version/release docs | Page explosion and possible overclaim | REMOVE; use Activity/System/Settings | APPROVE / MODIFY / REMOVE |

## Product Owner decisions required

1. Approve, modify, or remove each row in the table, especially the seven-page
   MVP navigation and Video Detail tab model.
2. Approve the frontend as a **read-only first** product. Decide separately if
   any future command-request controls may enter scope.
3. Approve or reject the proposed local loopback API as a new, separate backend
   boundary; it does not exist now and will require dependency/security/
   packaging review before implementation.
4. Confirm whether a controlled managed-note preview is acceptable only through
   a backend allowlist/integrity check, or should remain metadata/external-open
   only in Phase 1.
5. Confirm React + TypeScript + Vite as the single proposed UI stack.
6. Confirm that Deep Analysis/qualification stays blocked UX only until a
   qualified live provider, real qualified-provider output, and explicit PO
   acceptance exist. This approval does not request, expose, or authorize a
   credential or live provider call.

## Adversarial review

| Risk checked | Result |
| --- | --- |
| Invented backend capability | None proposed as existing. Every API route is labeled proposed; current capabilities and absences are explicit. |
| Excessive pages / admin-dashboard drift | Reduced sixteen candidates to seven pages, with detail tabs and System sections. |
| Hidden trust states | Exact pipeline/job/provider/dispatch and error states, notably `AMBIGUOUS`, remain first-class. |
| Provider made to look usable | Rejected. All providers are shown with actual qualification state; Deep Analysis is unavailable. |
| Unsafe retry/fallback | Rejected. No Try again, auto fallback, Use anyway, repair, or provider switch. |
| Credential exposure | Rejected. Credentials remain external/runtime-only; no client storage, full key display, ordinary config write, or log exposure. |
| Frontend confused with authority | Rejected. Verified backend DTOs only; no SQLite/Python/provider/Vault direct access or client trust minting. |
| Over-engineered stack | Rejected. Vite + React + TypeScript with small routing/query/component boundaries; no SSR/SaaS architecture. |
| TASK-016G pulled forward | Rejected. It is marked future/unauthorized and has no UI action. |
| Release posture misrepresented | Rejected. `NO-GO` is persistent dashboard/About context and independent from health checks. |

Audit result: **P0 = 0; release-critical P1 = 0.** The remaining items are
explicit PO decisions and already-recorded external/operational gates, not
hidden frontend implementation work.
