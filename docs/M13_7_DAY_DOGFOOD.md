# M13 — Real 7-Day Owner Dogfood

**Status: SETUP READY; Day 1 has not been counted.** M13 requires one meaningful normal-user Owner session on each of seven distinct local calendar days. Codex setup, health checks, and historical M12 use do not count.

## Starting authority

- Starting main: `22d138e8c20d6ef7be59f89907d61bf83bd5aa9e` (M12 acceptance-status PR #49 merge).
- M12 Golden UI: PASS, PR #48, merge `6841c96288cd5c4714593831cc2de8388d38895a`.
- Product version: `youtube-intel 0.1.0` / frontend `youtube-intel-workspace 0.1.0`, using the M12 Golden UI production tree.
- Product profile: local-first; local Scoring, Summary/Video Notes, and Evidence authority; selected optional Intelligence cloud route `moonshot / kimi-k2.6`, thinking disabled, non-streaming, with explicit UI consent for every execution. No K3 qualification or model-strategy change is part of M13.
- Dogfood workspace: `/Users/hua/Library/Application Support/Intelligence-M13-Dogfood` (one persistent task-owned workspace; runtime data outside Git). Initial GUI Following state is empty. The disabled legacy CLI sample channel in local configuration is not a Following or dogfood data.
- Local timezone: `Asia/Shanghai`.
- Actual Day 1 calendar date: **PENDING first real Owner session**.
- Intended Day 1–Day 7 window: **PENDING**. If the first real Owner session occurs on 2026-09-27, the earliest Day 7 is 2026-10-03; otherwise derive the window from the actual first session and never backdate it.
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

No Day 1 session has been reported. After the Owner finishes each day's natural use, append a dated section with the session, approximate actions, new and cumulative counts, source traces, restarts, Backup, cloud executions/cost, friction, failures, severity, interventions, and bounded fixes. Do not include credentials, raw transcripts, private unrelated content, or model reasoning text.

## Final reconciliation

Pending seven real dated Owner sessions and Day 7 validation. No M13 PASS or merge is claimed.
