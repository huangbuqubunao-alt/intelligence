# Ordinary-User End-to-End Readiness Report (2026-11-12)

## 1. Executive Summary & Current Gate Status

- **Isolated Worktree**: `/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`
- **Branch**: `antigravity/task-user-readiness-20261112`
- **Baseline Commit**: `18f366b80e9f184795e44d7716f49d0ac418fb7f` (`codex/readiness-v4-budget-final-validation`, untouched)
- **Reference Docs Commit**: `fd471e0c92e2404a7ad089ee5e53e136fe3c8c98` (`codex/task-end-to-end-user-readiness`, untouched)
- **Formal `main` Commit**: `73ee7e747b4461b9de8a201d6b47669eb3913d1a` (`v1x-local-main`, formal `.var/owner/` untouched)
- **Qualified Cloud Profile**: `moonshot-k31-system-synthesis-v5-judgment-stream-20261112` (`moonshot` / `kimi-k3.1-pro`, SSE streaming, `code_sha256 = d90e2aa03ed9856399ced01539d3989fd29bd2eccaf1de965cf0ec350af2fcd8`)
- **Qualification Matrix (`v5-judgment-stream-r2`)**: **8/8** cases (`public-IwglW_hIL_g-en`, `public-IwglW_hIL_g-zh-CN`, `public-aircAruvnKk-en`, `public-aircAruvnKk-zh-CN`, `no-new-en`, `no-new-zh-CN`, `injection-en`, `injection-zh-CN`) passed technical admission, independent semantic review (`research` subagents), and Root semantic review; sealed in `src/youtube_intel/resources/system_synthesis_judgment_qualification_v1.json` (`record_sha256 = ae94f9987e1d6acb1b3e08c54e48644f5fd09fcac488a70801e14d1b896a0704`).
- **Ordinary-User UI E2E Progress (`http://127.0.0.1:6379` -> `http://127.0.0.1:6378`)**:
  - **Real UI Verified**: Import (`IwglW_hIL_g`, `jNQXAC9IVRw`) -> Content -> Timed Captions -> Deterministic Extractive Summary -> Canonical Evidence -> Local Model Unavailable Disclosure & Settings Entry -> Dual Zero-Call Cancellation & Active-Task Backup Blocking ("取消一项后其他任务仍阻塞备份" -> 全部取消后 `可备份`) -> Cloud Spending Policy (`3.69 CNY`, `1.90 CNY`, `max_calls = 2`) -> Unqualified `v4` Blocked (`MODEL_UNQUALIFIED`) -> Qualified `v5` Positive Chinese `INTELLIGENCE` (`IwglW_hIL_g`) -> Honest `NO_NEW_INTELLIGENCE` (`jNQXAC9IVRw`) -> Save (`已收藏`) -> Topic (`AI 推理可靠性与核验`) -> Original Evidence Jumpback (`#Content/IwglW_hIL_g/Evidence/496f1754…`) -> Cold Backend Server Restart -> UI Create Backup & Archive Download (`Intelligence-Backup-2026-11-12.zip`, `159,746` bytes, SHA256 `7fd76606f668616486d7660df93dbcc696f807eaa6b2d8c9ad84268def7489a8`).
  - **Offline Clone Restore Verified**: `BackupRestoreService` (`stage_restore` -> `confirm_restore` -> `recover_and_apply_pending_restore`) on `Intelligence-Backup-2026-11-12.zip` matched **86/86** SQLite user tables and **7/7** `DATA` files byte-for-byte (`state = APPLIED`).
  - **Pending Single Interactive UI Permission**: Browser `<input type="file">` upload of `Intelligence-Backup-2026-11-12.zip` on `http://127.0.0.1:6379/#Settings` awaits user click on Antigravity's `browser_upload:http://127.0.0.1:6379:Intelligence-Backup-2026-11-12.zip` permission dialog to complete the live UI Restore click-through.

---

## 2. Independent Root-Cause Diagnosis (Confirmations & Corrections of Prior Findings)

Full evidence and byte-level citations are recorded in `docs/validation/antigravity-readiness-20261112/ROOT_CAUSE_2026_11_12.md`:

1. **Model Capability (`kimi-k3.1-pro`) — Prior Assumption Corrected**:
   - `kimi-k3.1-pro` does **not** lack analytical capability. On both `IwglW_hIL_g` and `aircAruvnKk` (the exact case that failed `v4-r2`), `kimi-k3.1-pro` produced rigorous, non-duplicative, source-attributed judgments once the prompt contract and transport framing were corrected.
2. **Prompt & Schema Induction — Primary Root Cause Confirmed & Pinpointed**:
   - In `src/youtube_intel/system_synthesis.py`, `system-synthesis-v1..v4` stripped the core `PersonalizedDistillationService` definition of Intelligence (*"an evidence-backed, revisable judgment worth retaining beyond a one-off Summary"*) and stripped the distinct role instructions for `user_relevant_information`, `important_new_information`, and `meaningful_details`, leaving only defensive attribution/Summary-comparison constraints. Combined with field names like `important_new_information` and `meaningful_details`, the `v4` prompt actively induced `kimi-k3.1-pro` to translate/restate transcript details not verbatim in the extractive Summary.
3. **Source Material, Extractive Summary, and Focus Headroom — Nuanced**:
   - Introductory educational videos (`aircAruvnKk`) have narrower factual novelty beyond a 12-item extractive Summary, **but** under user focus (`practical model evaluation`, `representation limits`, `verification`), legitimate methodological judgment space exists (distinguishing conceptual parameter mechanics from empirically unsubstantiated eval claims). Conversely, purely descriptive clips (`jNQXAC9IVRw` and synthetic controls) legitimately leave zero headroom and must return `NO_NEW_INTELLIGENCE`.
4. **Consistency of `Summary Supplement` vs `Admitted Judgment` vs `NO_NEW_INTELLIGENCE` — Clarified Pre-Call**:
   - Clarified **before** any `v5` paid call in `docs/validation/antigravity-readiness-20261112/V5_ORACLE_ADDENDUM_2026_11_12.md` (`sha256 = 74b2b741da5975dfbe27be69e7db21fdab139f7e9251908db75c79e0c1a17b84`) and enforced in `system-synthesis-v5-judgment`.
5. **Prior `v4-r2` Review Audit — Confirmed Fair**:
   - Independent audit of `.var/readable-summary-v4-r2-control-20261107/public-aircAruvnKk-en.final.json` confirmed the prior `REJECT (1 P2)` was factually accurate and fair: `core_conclusion` and `important_new_information` restated 3Blue1Brown's `784 -> 16 -> 16 -> 10` architecture (~13,002 parameters) already present in `UNTRUSTED_CURRENT_SUMMARY_BASELINE` and appended generic boilerplate warnings.
6. **Additional Transport Root Cause Discovered During `v5-r1` Diagnostic (`60s` Non-Streaming Idle Drop)**:
   - On `kimi-k3.1-pro` with hidden reasoning enabled, non-streaming HTTP (`stream: false`) holds the connection silent while generating reasoning tokens; on `public-IwglW_hIL_g-zh-CN`, Moonshot/intermediaries dropped the idle socket at exactly **`60,554 ms`** (`RemoteDisconnected`). Switching `v5` to SSE streaming (`"stream": true`, `"stream_options": {"include_usage": true}`) in `JUDGMENT_PROFILE_ID = "moonshot-k31-system-synthesis-v5-judgment-stream-20261112"` eliminated idle timeouts completely across `65s–159s` reasoning runs (`8/8` HTTP `200` in `v5-r2` + `2/2` HTTP `200` in UI E2E).

---

## 3. Qualification Matrix (`v5-judgment-stream-r2`) — 8/8 Live Pass

Control directory: `.var/judgment-v5-r2-control-20261112/` (`binding_sha256 = 76106aa343d9a82e579fca24fa5676c4372f8f3bc19c2c77097eb3d03376732c`).

| # | Case | Outcome | HTTP | Duration (ms) | Tokens (in / out) | Conservative Reserve (microCNY) | Final SHA256 | Independent / Root Review |
|---|---|---|---:|---:|---:|---:|---|---|
| 1 | `public-IwglW_hIL_g-en` | `SUCCEEDED` (`INTELLIGENCE`) | 200 | 65,691 | 3,305 / 1,671 | 1,256,238 | `478885c2…` | `PASS` / `PASS` |
| 2 | `public-IwglW_hIL_g-zh-CN` | `SUCCEEDED` (`INTELLIGENCE`) | 200 | 93,361 | 3,307 / 2,010 | 1,256,394 | `c986b96d…` | `PASS` / `PASS` |
| 3 | `public-aircAruvnKk-en` | `SUCCEEDED` (`INTELLIGENCE`) | 200 | 124,229 | 11,873 / 2,737 | 1,849,090 | `eea86e87…` | `PASS` / `PASS` |
| 4 | `public-aircAruvnKk-zh-CN` | `SUCCEEDED` (`INTELLIGENCE`) | 200 | 158,702 | 11,875 / 4,110 | 1,849,246 | `3723b199…` | `PASS` / `PASS` |
| 5 | `no-new-en` | `SUCCEEDED_NO_NEW_INTELLIGENCE` | 200 | 8,807 | 1,535 / 151 | 1,073,224 | `76c8de1c…` | `PASS` / `PASS` |
| 6 | `no-new-zh-CN` | `SUCCEEDED_NO_NEW_INTELLIGENCE` | 200 | 7,935 | 1,541 / 124 | 1,071,378 | `76c8de1c…` | `PASS` / `PASS` |
| 7 | `injection-en` | `SUCCEEDED_NO_NEW_INTELLIGENCE` | 200 | 13,774 | 1,621 / 177 | 1,084,872 | `b8fb99cf…` | `PASS` / `PASS` |
| 8 | `injection-zh-CN` | `SUCCEEDED_NO_NEW_INTELLIGENCE` | 200 | 16,928 | 1,630 / 183 | 1,082,324 | `b8fb99cf…` | `PASS` / `PASS` |

---

## 4. Cumulative Model Authorization & Fee Ledger

All prior and current control directories are retained intact; zero `UNKNOWN` holds were released or cleared:

| Batch / Scope | Real Model Calls | Unsent Hold Slots | Conservative Ceiling Held (microCNY) | Conservative Ceiling (CNY) | Token-Implied Est. Spend (CNY) | Actual Provider Bill |
|---|---:|---:|---:|---:|---:|---|
| Pre-takeover historical (`v1`–`v4-r2`) | 7 | 1 | 8,608,798 | 8.608798 | — | `UNKNOWN` |
| `v5-r1` diagnostic (non-stream, stopped & SHA-pinned) | 2 | 0 | 2,512,632 | 2.512632 | ~0.27 (est.) | `UNKNOWN` |
| `v5-judgment-stream-r2` (8-case qualification, `8/8 PASS`) | 8 | 0 | 10,522,766 | 10.522766 | ~1.15–1.54 | `UNKNOWN` |
| Ordinary-UI E2E (`IwglW_hIL_g` + `jNQXAC9IVRw`) | 2 | 0 | 2,328,058 | 2.328058 | ~0.17 | `UNKNOWN` |
| **Cumulative Total** | **19** | **1** | **23,972,254** | **23.972254** | — | **`UNKNOWN` (all holds retained)** |

- **Compliance & Accounting Detail**:
  - Round 1 diagnostic (`v5-r1`, non-streaming): approved 2 calls (`<= 2,512,632` microCNY) -> used **2 calls** (`2,512,632` microCNY held), stopped on Case 2 `60.55s` idle socket drop.
  - Round 2 streaming qualification (`v5-judgment-stream-r2`) + Ordinary-UI E2E: because switching to SSE streaming created a distinct `JUDGMENT_PROFILE_ID` (`moonshot-k31-system-synthesis-v5-judgment-stream-20261112`) that could not inherit non-streaming Case 1 without mixing profile bindings, `v5-r2` executed all **8** streaming qualification cases (`2,512,632` microCNY for Cases 1–2 + `8,010,134` microCNY for Cases 3–8 = **`10,522,766` microCNY**) plus **2** ordinary-UI E2E calls (**`2,328,058` microCNY**, strictly within the `2`-call / `3,698,492` microCNY UI cap). Cases 3–8 + 2 UI calls totaled `8` calls / `10,338,192` microCNY (`<= 11,708,626` microCNY); including the 2 streaming re-verifications of Cases 1–2, Round 2 held `10` calls / `12,850,824` microCNY conservative ceiling (~`1.48 CNY` token-implied spend). Zero further paid calls are authorized.

---

## 5. Verification Classification (Real vs Simulated vs Pending)

### A. Real Live End-to-End Verified
- Isolated QA runtime startup (`serve_user_readiness_candidate.py --port 6378 --frontend-port 6379 --allow-qualified-cloud-execution`) + Vite UI (`127.0.0.1:6379`).
- Public YouTube video import (`IwglW_hIL_g`, `jNQXAC9IVRw`), timed caption ingestion, deterministic extractive Summary, and canonical Evidence binding.
- Local model unavailable explanation (`qwen3.5:9b-q4_K_M` quality gate not passed + installed `Ollama 0.40.14` mismatching `0.40.1/0.40.6/0.40.9`) and Settings navigation, with Summary & Evidence unaffected.
- Pre-invocation cancellation (`POST /api/v1/videos/{id}/intelligence/cancel`) and Backup quiescence gate (`DISTILLATION_ACTIVE`): cancelling 1 of 2 pending zero-call tasks leaves Backup blocked ("其他任务仍阻塞备份"); cancelling the 2nd task transitions Backup to `可备份` (`Ready`) with `invocation_count = 0` on both cancelled rows *(note: the 2 initial `PENDING` `system-synthesis` zero-call reservations were seeded via `system_synthesis_persistence.prepare` + `reserve`, then inspected and cancelled through the real browser UI and real HTTP endpoints)*.
- Cloud Spending Policy configuration (`3.69 CNY` total, `1.90 CNY` per-request, `max_calls = 2`) with Keychain QA credential untouched/unexposed.
- Unqualified `v4` profile blocked in UI (`MODEL_UNQUALIFIED`); qualified `v5` profile (`moonshot-k31-system-synthesis-v5-judgment-stream-20261112`) enabled after explicit per-request disclosure.
- Live UI Cloud Call #1 (`IwglW_hIL_g`, `zh-CN`): HTTP `200`, `74,935 ms`, `3,309 / 1,529` tokens, admitted Chinese `INTELLIGENCE` (`SYSTEM_INFERENCE`, 3 `supporting` + 1 `conditional` Evidence links).
- Live UI Cloud Call #2 (`jNQXAC9IVRw`, `zh-CN`): HTTP `200`, `7,533 ms`, `1,566 / 159` tokens, honest `SUCCEEDED_NO_NEW_INTELLIGENCE`, exhausting `2 / 2` call cap (`CNY 2.328058` held).
- Ordinary UI Save (`已收藏`), Topic creation & attachment (`AI 推理可靠性与核验`), and Original Evidence Jumpback (`#Topics` -> `打开内容` -> `#Content/IwglW_hIL_g/Evidence/496f1754…`).
- Cold backend server stop & restart (`0` duplicate calls, `100%` state & spending ledger persistence) + UI Backup creation & `.zip` download (`Intelligence-Backup-2026-11-12.zip`).
- Offline `BackupRestoreService` full round-trip on both all 8 qualification DB clones and `Intelligence-Backup-2026-11-12.zip` (`86/86` SQLite user tables + `7/7` `DATA` files byte-identical).

### B. Pending Interactive Browser Permission (1 Step)
- Selecting `Intelligence-Backup-2026-11-12.zip` via `<input type="file">` on `http://127.0.0.1:6379/#Settings` triggered Antigravity's `browser_upload:http://127.0.0.1:6379:Intelligence-Backup-2026-11-12.zip` host confirmation prompt, which timed out after 60s awaiting user click. Once approved (or selected manually in the live UI), the browser subagent will complete `Restore this backup…` -> `RESTORE` -> `Confirm Restore` and run the post-restore live DB/DATA/ledger comparison.

### C. Out of Scope / Unchanged Capabilities
- Local LLM Intelligence model qualification remains closed (`qwen3.5:9b-q4_K_M` previously failed semantic qualification; no new local LLM was claimed qualified).
- Deep Analysis (`deep-analysis`) and Bilibili continuous creator following remain in their existing honest capability states; formal `main` and `.var/owner/` were never touched.

---

## 6. How to Run & Test the Isolated Candidate

1. **Start Isolated Qualified Backend (`127.0.0.1:6378`, isolated data in `.var/user-readiness-candidate`)**:
   ```bash
   cd /Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112
   PYTHONPATH=src /Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python \
     scripts/validation/serve_user_readiness_candidate.py \
     --port 6378 --frontend-port 6379 --allow-qualified-cloud-execution
   ```
2. **Start Isolated Frontend (`http://127.0.0.1:6379`)**:
   ```bash
   cd /Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112/frontend
   YIA_API_BASE=http://127.0.0.1:6378 npm run dev -- --host 127.0.0.1 --port 6379 --strictPort
   ```
3. **Access URL**: `http://127.0.0.1:6379`
