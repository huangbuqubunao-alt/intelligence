# M13 — Real 7-Day Owner Dogfood

**Status: M13_DOGFOOD_IN_PROGRESS; Day 1 / 7 complete, P1 remediation open.** M13 requires one meaningful normal-user Owner session on each of seven distinct local calendar days. Codex setup, health checks, and historical M12 use do not count.

## Starting authority

- Starting main: `22d138e8c20d6ef7be59f89907d61bf83bd5aa9e` (M12 acceptance-status PR #49 merge).
- M12 Golden UI: PASS, PR #48, merge `6841c96288cd5c4714593831cc2de8388d38895a`.
- Product version: `youtube-intel 0.1.0` / frontend `youtube-intel-workspace 0.1.0`, using the M12 Golden UI production tree.
- Product profile: local-first; local Scoring, Summary/Video Notes, and Evidence authority; selected optional Intelligence cloud route `moonshot / kimi-k2.6`, thinking disabled, non-streaming, with explicit UI consent for every execution. No K3 qualification or model-strategy change is part of M13.
- Dogfood workspace: `/Users/hua/Library/Application Support/Intelligence-M13-Dogfood` (one persistent task-owned workspace; runtime data outside Git). Initial GUI Following state is empty. The disabled legacy CLI sample channel in local configuration is not a Following or dogfood data.
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

## Final reconciliation

Pending seven real dated Owner sessions and Day 7 validation. No M13 PASS or merge is claimed.
