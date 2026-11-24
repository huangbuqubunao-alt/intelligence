# M13 — Real 7-Day Owner Dogfood

**Status: M13_DOGFOOD_IN_PROGRESS; Day 1 / 7 complete, automated P1 rechecks passed, Owner recheck pending.** M13 requires one meaningful normal-user Owner session on each of seven distinct local calendar days. Codex setup, health checks, and historical M12 use do not count.

## Starting authority

- Starting main: `22d138e8c20d6ef7be59f89907d61bf83bd5aa9e` (M12 acceptance-status PR #49 merge).
- M12 Golden UI: PASS, PR #48, merge `6841c96288cd5c4714593831cc2de8388d38895a`.
- Product version: `youtube-intel 0.1.0` / frontend `youtube-intel-workspace 0.1.0`, using the M12 Golden UI production tree.
- Product profile: local-first; local Scoring, Summary/Video Notes, and Evidence authority; selected optional Intelligence cloud route `moonshot / kimi-k2.6`, thinking disabled, non-streaming, with explicit UI consent for every execution. No K3 qualification or model-strategy change is part of M13.
- Dogfood workspace: `/Users/developer/Library/Application Support/Intelligence-M13-Dogfood` (one persistent task-owned workspace; runtime data outside Git). Initial GUI Following state is empty. The disabled legacy CLI sample channel in local configuration is not a Following or dogfood data.
- Local timezone: `Asia/Shanghai`.
- Actual Day 1 calendar date: **2026-09-27**, based on the real Owner-added Following persisted at 20:12:42 Asia/Shanghai, after setup. Feedback was reported on 2026-09-28; the date is grounded in the actual user action, not the app preparation date.
- Earliest seven-day window: **2026-09-27–2026-10-03**, subject to one meaningful Owner session on each distinct local calendar day. Day 2 has not been counted.
- Historical M12 interactions, demo fixtures, automated browser actions, and Codex interaction contribute **zero** M13 sessions or usage counts.

## Setup verification — 2026-09-27

- M13 backend runs from this worktree's source on `127.0.0.1:8791`; the frontend runs on `127.0.0.1:5191`. Both returned HTTP 200 via read-only GETs. The backend reports version `0.1.0`, `STANDARD_LOCAL`, and `demo_data=false`.
- Fresh task-owned SQLite passed `PRAGMA quick_check`; initial counts were zero for source subscriptions, videos, artifacts, Evidence, Intelligence, Topics, and distillation resource usage. No sample Following or M12 database was imported. Runtime data, logs, and process IDs are under the workspace path above.
- The task-owned backend started without `MOONSHOT_API_KEY`; its read-only system status reports cloud credential `Blocked`. Local use can begin, but cloud Intelligence cannot be intentionally authorized/executed until the Owner supplies the credential to this task-owned backend environment and it is restarted. No key value was read or stored, and no cloud execution occurred in setup.
- This launch and health check are **not** an Owner dogfood session. Day 1 remains pending.

## Evidence rules

- Count only genuine Owner use in this workspace. Approximate breadth targets are 6–8 real Followings, 30–50 Contents, 20–30 Summaries/Video Notes, 5–8 admitted Intelligence items when justified, and 2–3 Topics. Never manufacture an admission to reach a count.
- Preserve original Evidence provenance and translation as presentation only. Record positive-zero and truthful source/caption failures. Record user-visible friction even when checks pass.
- Record cloud executions from the durable ledger and actual cost only when reliably known; otherwise write `UNKNOWN`. This journal grants no cloud consent. Every paid execution still needs the Owner's separate product UI action.
- Stop normal dogfood for a P0. Resolve any core P1 before PASS. Reassess the seven-day window if a core authority change invalidates earlier evidence. M13 does not claim Public Distribution Ready.

## Daily Owner sessions

### Day 1 — 2026-09-27

- Session happened: **YES**. The Owner added a real enabled channel Following at 20:12:42 local time and reported the following normal-use feedback on 2026-09-28. The persisted Following action establishes the Day 1 date.
- Original Owner feedback, preserved before fixes:

```text
1. Settings → language currently appears to expose only one output-language setting.

Owner expected the product language model to distinguish:

- UI/interface language
- preferred generated/output language
- source/content language

2. Preferences / Settings Center is effectively not configurable.

Owner can enter Settings but says almost nothing useful can actually be changed.

3. Add Following → Processing level contains wording similar to:

“将相关视频处理为情报”

Owner does not understand what this means.

4. Owner wants a usable Chinese interface.

5. Owner added a real Following but no Intelligence/洞察 was generated.
```

- Severity at report: **P1** — core Settings preferences cannot be configured; Chinese UI unavailable; the Following has no visible Intelligence and the Owner cannot tell why. **P2** — Processing level wording is unclear.
- Approximate actions: Add Following, inspect Settings/language and Processing level, look for Intelligence. Followings added/used: **1**. Contents encountered in persisted state: **0**; new Summaries: **0**; admitted Intelligence: **0**; positive-zero: **0**; Topic changes: **0**; source traces: **0**. Restart: **NO evidence of Owner restart**. Backup: **NO evidence of Owner Backup**. Cloud executions: **0** in the M13 ledger; cost: **UNKNOWN** (no monetary amount asserted).
- Initial read-only state before remediation: the Following is enabled with `DISCOVER_ONLY` processing policy, no last check, and no source run; Videos, Artifacts, Evidence, Intelligence, Topics, and distillation usage are all zero. The task backend's cloud credential status was `Blocked` at setup. Root-cause analysis and any fixes belong in a separate dated remediation note below; this feedback record must remain intact.

After each later Owner session, append a dated section with actions, new and cumulative counts, source traces, restarts, Backup, cloud executions/cost, friction, failures, severity, interventions, and bounded fixes. Do not include credentials, raw transcripts, private unrelated content, or model reasoning text.

### Day 1 remediation — 2026-09-28 (Codex work; not a Day 2 Owner session)

- Read-only diagnosis confirmed the Day 1 Following is enabled with `DISCOVER_ONLY`, has **no Source Run**, and has **no Content, Transcript, Summary, verified Evidence, Intelligence execution/reservation, or Topic**. Scoring and local Intelligence were not attempted. No `SUCCEEDED_NO_NEW_INTELLIGENCE` result exists. The first scheduled check is 2026-09-29 09:00 local; the Owner had not used Check Now. Thus the immediate reason for no Intelligence is that discovery/processing never began, with discovery-only policy also excluding insight extraction. This was not an admission failure or a lawful positive-zero result.
- The task backend's read-only Settings response reports Moonshot K2.6 qualified for V1 video analysis but `credential_status=BLOCKED`, `production_eligible=false`; `MOONSHOT_API_KEY` is absent from both the running task backend and the current task shell. Cloud Intelligence is additionally unavailable. No credential was read, entered, stored, or changed; no model call was made. Every future cloud execution still requires its normal UI review and explicit consent. Cost: **UNKNOWN**; cloud executions: **0**.
- UX fixes: separate persisted interface language (Simplified Chinese / English, in this browser profile) from the existing backend-persisted default output language; explain per-Content source language as detected factual metadata. Localize the normal V1 navigation, Following, Content, Summary, Evidence trace, Intelligence, Topic, Settings, consent disclosure, empty/blocked states, and Backup controls. Preserve original transcript/Evidence text and existing generated artifacts. Mark history, source-policy defaults, model/cost status, resource usage, and privacy status as read-only. Change the processing choice to “从相关视频中提炼洞察” with a short evidence-threshold explanation. The Home/Following screens now explain unchecked and discovery-only states; Content distinguishes positive-zero, cloud unavailable, consent required, and processing failures when those states actually occur. No admission threshold, provider/model semantics, consent boundary, ledger, source contract, schema, or Evidence authority changed.
- Focused verification: workspace App Vitest **46 passed**; frontend TypeScript typecheck **passed**; production build **passed**; backend output-language focused pytest **2 passed, 26 deselected**; `git diff --check` **passed**. A read-only workspace count remained one Following and zero Source Runs, Content, Artifacts, Evidence, Intelligence, Topics, and resource-usage entries; SQLite `quick_check=ok`.
- Severity remains **P1 pending Owner recheck** for Chinese UI, real Settings edits/persistence, and clarity of the no-Intelligence explanation. The **P2** wording change also awaits Owner comprehension. This remediation work and its automated tests do not count as Day 2. The seven-day window does not reset because the changes affect UI/settings/copy/presentation only.

### Pre-Day-2 automated product self-test — 2026-09-28

- **Not an Owner dogfood day.** Day 1 remains complete; Day 2 remains pending real Owner use.
- Disposable self-test root: `/Users/developer/Library/Application Support/Intelligence-M13-PreDay2-SelfTest.QllBan` with separate fixture and fresh real-source databases. The Owner's persistent M13 database was read only; before counts were 1 Following and 0 Source Runs, Content, Artifacts, Evidence, Intelligence, Topics, and resource-usage entries. No paid cloud request was authorized or sent.
- Initial broad checks: full backend pytest 2504 passed, 1 skipped, 0 failed; Ruff, mypy, compileall, frontend Vitest 78 passed, and production build passed. Fixture Playwright passed at 1440×900 and 768×900 after updating its English-language selectors to match the Day 1 localization.
- Real-source self-test evidence: a separate public 3Blue1Brown Following ingested one real Content item and its transcript. With no focus terms, the source relevance decision was `UNCERTAIN` / `NO_FOCUS_RULES`, so Scoring and Summary were not attempted and no Evidence or Intelligence was fabricated. The Source Run incorrectly reported `MODEL_UNAVAILABLE` despite the configured local model and matching digest being available. This is a **P1 truthful-state/recovery defect** in the normal Following loop. Preserve this finding while fixing it.
- Visual review at desktop and 768px found a **P2** mixed-language Settings card and untranslated processing status labels. These copy/presentation fixes are in progress. The isolated Settings language switch and backend output-language save worked independently, and the disposable Backup produced a ZIP whose manifest counts and database SHA-256 matched.
- Findings and bounded fixes, completed on **2026-09-29**: an uncertain relevance decision and a failed local preparation were both falsely classified as `MODEL_UNAVAILABLE`. The Source Run now uses the existing `EXECUTION_CONDITION_UNRESOLVED` state for those cases, without changing source, Evidence, admission, schema, ledger, or consent authority. New insight-extraction Followings require at least one focus word in the UI, and historical focus-less uncertain Content explains why it was left unprocessed. Chinese Settings/model wording, processing status, local Summary failure, and the remaining page/status/date labels seen in the narrow screenshot were clarified. The normal copy uses “洞察”; original source language remains untouched.
- Isolated browser coverage: fresh onboarding in three steps with a UI-only sample; all six production navigation destinations; Chinese and English UI switching; backend output-language save independent of UI language; Add Following processing copy and focus validation; active/pause/resume and Check Now; Content, original transcript/Evidence and timestamped source links; admitted, positive-zero, ineligible, consent-needed, credential-unavailable, provider-unavailable and failed Intelligence states; mocked Moonshot K2.6 disclosure/review/explicit confirmation; Topic creation and Intelligence linking; Settings and Backup. Production Search is absent by V1 design and was not enabled. Both 1440px and 768px fixture Playwright runs passed without blank routes or horizontal overflow. Cloud cancellation and reload caused zero dispatch; one explicit confirmation reached only the intercepted test transport. **Real paid cloud calls: 0.**
- A second, focused public 3Blue1Brown self-test Following with focus `puzzle` ingested a real English video and transcript. Local Scoring succeeded (score 8), and the local quality step succeeded. Two canonical transcript Evidence records were present with original English source text. Local Summary returned `INVALID_RESPONSE` after one completed local model response; no Summary or Intelligence was admitted. This is a bounded **P2 local-model output failure observed on one video**, with a truthful Chinese failure explanation and preserved transcript/Evidence. Structured local Summary succeeds in deterministic unit/integration coverage; this single live result does not prove it will succeed for every real video. The historical focus-less uncertain video remains unprocessed; its explanation is visible, with no automatic retroactive processing or fabricated Evidence.
- Persistence and Backup: isolated backend restarts retained settings, Followings, Content, Summary/Evidence/Intelligence fixture records, and Topics; no new dispatch or duplicate resource usage appeared solely from restart. The disposable Backup action succeeded; the ZIP passed integrity, manifest count, database hash/size, and credential-exclusion checks. Backup preview and cancel were exercised; no destructive Restore was run. The real M13 backend was relaunched with the current code and its existing credential-absent environment; real app health checks returned HTTP 200. Moonshot remains blocked without a runtime credential, and no key was read or stored.
- Final broad confirmation: backend pytest **2505 passed, 1 skipped, 0 failed**; Ruff **passed**; mypy **passed** for 61 source files; compileall **passed**; frontend typecheck **passed**; Vitest **79 passed**; production build **passed**; normal-user Playwright plus isolated cloud/Topic/Backup/restart flows **passed**. The one real-video local Summary failure above remains recorded rather than hidden. Final `git diff --check` passed.
- Owner workspace protection: read-only before and after counts stayed at **1 Following; 0** Source Runs, Content, Artifacts, Evidence, Intelligence, Topics, and resource-usage rows; SQLite `quick_check=ok`. No fixture data entered it. No P0 or unresolved core P1 was found in automated checks. Day 1 remains valid; Day 2 still requires real Owner use. Since no Owner session was recorded on 2026-09-28, the earliest possible Day 2 is **2026-09-29** and the earliest possible Day 7 is **2026-10-04**, assuming one meaningful Owner session on each subsequent local calendar day. This self-test does not increment the Owner-day count or reset the window.

## Final reconciliation

Pending seven real dated Owner sessions and Day 7 validation. No M13 PASS or merge is claimed.
