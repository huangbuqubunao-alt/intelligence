# TASK-READINESS-BACKUP-PICKER-FILTER 交接报告

## 元数据

- Role: Implementer; agent: `native_scan_resume`.
- Base: `c4a60f42e2a7f9caf6c31f9c02eb72c7792bfa44` (verified before writing).
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-backup-picker-filter`.
- Branch: `codex/task-readiness-backup-picker-filter`.
- Reported: 2026-10-16; implementation commit is the commit containing this report.
- Suggested state: `IN_REVIEW`; author STOP after commit. No main merge/public status update.

## 目标、实际范围与复用

Root's real macOS Chrome154 experiment remains the originating failure: custom
`.zip,application/zip` filter left Open disabled for the valid ZIP; switching the
same panel to All files and reselecting the same ZIP enabled Open and allowed
normal stage with 96 physical DATA files. The prior failure is not rewritten as
a success. Root's real restore/confirmation evidence belongs to its separate
acceptance, not this synthetic engineering check.

- `frontend/src/workspace/App.tsx`: remove only the Backup file input's `accept`;
  associate a short visible `.zip`/rejection/reselection hint using `aria-describedby`.
- `frontend/src/workspace/uiLanguage.tsx`: translate that hint into Chinese.
- `frontend/src/workspace/BackupPickerFilter.test.tsx`: eight EN/ZH regressions.
- This report. No other tracked files changed.

`DIRECT`: installed React18.3.1 (MIT), native HTML input, existing hint style,
translation mechanism and unchanged strict service/upload path. Tests reuse
Testing Library16.1.0 (MIT), Vitest2.1.9 and Playwright-core1.62.1 (Apache-2.0),
without installation or lockfile changes. `REFERENCE`: prior read-only Chromium
source investigation only; no external code copied. Its accept parser adds an
explicit `.zip` extension to the native filter; the Mac bridge delegates to
NSOpenPanel's file-type filter. This is an OS selection hint, not archive authority.

- [Chromium accept parser](https://chromium.googlesource.com/chromium/src/+/HEAD/chrome/browser/file_select_helper.cc), observed blob `4d1dc53d4e96e2942b15658f9ef5543af52d90c6`.
- [Chromium Mac bridge](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/remote_cocoa/app_shim/select_file_dialog_bridge.mm), observed blob `932e070469dc8c0b164d237232b7019f6875c901`.

No new picker/runtime/design system is warranted for this compatibility fix.
Other import pickers, upload handler, archive limits/path/hash/manifest validation,
restore stage/cancel/confirmation, persistence, Schema, credentials, config,
qualification and model work are unchanged.

## 验收与检查证据

All logs/screenshots below are ignored author evidence under
`.var/backup-picker-filter/` in this worktree, retained for independent review.

| Check | Result | Evidence |
|---|---|---|
| TS before changes and with new tests | PASS | `typecheck-before.log`, `typecheck-test.log` |
| New tests before product fix | Expected RED: 2 FAIL / 6 PASS | `red.log`: both languages `input.hasAttribute("accept")` expected false, received true at test line41 |
| New + existing feedback + physical preview | 36 PASS | `focused.log` (8 + 22 + 6), no assertions removed |
| Full frontend | 937 PASS / 34 files | `full-frontend.log`, 21.63s |
| `npm --prefix frontend run typecheck` | PASS | `typecheck.log` |
| `npm --prefix frontend run build` | PASS | `build.log`, TypeScript + Vite production build |
| Real isolated Google Chrome engineering | EN/ZH 14 assertions groups each PASS | `browser.mjs`, `browser.log`, `browser.json`; Chrome155.0.8059.80, headless, port5197, intercepted synthetic API only |
| Screenshots viewed by author | PASS | `en-preview.png`, `en-rejected.png`, `zh-CN-preview.png`, `zh-CN-rejected.png` |
| Diff/scope | PASS | `git diff --check`; no dependency/lockfile/config/backend change |

Reproduction commands from worktree root:

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test -- src/workspace/BackupPickerFilter.test.tsx src/workspace/App.backup-feedback-context.test.tsx src/workspace/BackupPhysicalPreview.test.tsx
npm --prefix frontend test
npm --prefix frontend run build
# Only this isolated frontend server; the script intercepts all /api/ requests.
YIA_API_BASE=http://127.0.0.1:5198 npm --prefix frontend run dev -- --host 127.0.0.1 --port 5197 --strictPort
# Separate shell while that server is running:
node .var/backup-picker-filter/browser.mjs
```

New tests verify cancellation causes zero POST; misleading `.zip.exe`/HTML/TXT
names cause zero stage even with ZIP MIME; untrusted ZIP bytes with text MIME
reach the unchanged archive authority and surface its rejection without preview
or automatic retry; deliberate same-file reselection makes one new request;
uppercase `.ZIP` with empty MIME stages unchanged bytes; confirmation remains
explicit and initially disabled; cancellation and same-file reselection work.
Existing22 feedback tests retain the old-completed-result/bad-next-ZIP controls.

Chrome checks likewise verified keyboard focus, no `accept`, localized visible
hint, zero POST on cancellation/non-ZIP, two deliberate rejected-archive stage
POSTs, two successful synthetic stage POSTs and two explicit cancel POSTs per
language, no confirm POST, no external requests, no page errors/warnings or
unexpected console errors. Each language produced the two expected409 console
entries for deliberate synthetic rejection. Screenshots have legible hints and
error/preview states. Synthetic physical96 is explicitly fixture presentation,
not a second real backup/restore proof.

## Unchanged execution proof

Exact base/current source spans were compared for all three handlers (byte equal):

- `chooseBackup`: SHA256 `a7863d5296310a65277b7f434065f565f0e86fa51d37e16ff15470b267b53ece`.
- `cancelRestore`: SHA256 `b0e2ab292b79376fa2ecd3f85bb10421cefe2051da8cc4603457a94fd49ac5bb`.
- `confirmRestore`: SHA256 `6ff569a9650659cf9efac22cec30e7966a1a51ffc9dde28803c2ba344757f755`.

No existing test/assertion was edited, deleted or skipped. Backend/API files are
absent from the diff. No model HTTP/load/debug/generation or real owner data IO.

## 失败、限制与剩余验收

- The full frontend log contains React `act(...)` warnings in unchanged test
  files (including App.test.tsx and ContentStatusLocalization.test.tsx). They
  remain visible; all937 tests passed. New/focused36 log has no such warning.
- `agent-browser skills get core` failed `command not found`; no install was
  attempted. Used the repository's installed Playwright and standalone Chrome.
- Initial dependency-link/log setup used a frontend-relative path from the
  frontend directory and failed `ln: frontend/node_modules: No such file or
  directory`; corrected cwd to repository root, linked existing node_modules,
  then performed all recorded checks. No dependency was installed or modified.
- Native macOS panel was **not** exercised by the author. Headless file injection
  does not prove NSOpenPanel behavior. Root's Chrome154 must verify ordinary
  selection without manually switching to All files after review/integration.
- Malicious/invalid archive responses here are synthetic. This change preserves
  existing backend guards; it does not claim newly rerun backend ZIP validation.
- No contact with root's Chrome, ports5908/5909, owner API, or actual downloaded ZIP.
- Independent Reviewer `local_text_review_resume` and root acceptance are pending.
- `DECISION NEEDED`: None; final native picker acceptance remains pending.

## Reviewer / 主控验收 / 整合

Pending. Implementer does not self-approve or mark the task DONE.

### Independent Reviewer — APPROVE (2026-10-16)

- Reviewer: `local_text_review_resume`, independent context; author was clean STOP.
- Reviewed exact base `c4a60f42e2a7f9caf6c31f9c02eb72c7792bfa44` through author
  `329794b06d1782ec0436bd18fb047edb4c151dee`, branch
  `codex/task-readiness-backup-picker-filter`. Read task/package and cumulative
  four-path diff; no product/test changes made by Reviewer.
- **APPROVE. No P0/P1/P2 findings.** Correctness, simplicity, architecture,
  security and performance reviewed. Removing the non-authoritative OS hint is
  exactly scoped; the visible localized hint is associated with the input.
  No new handler, dependency, request, persistence or qualification behavior.

Independent executed evidence (not the author's prior runs):

| Check | Actual result / retained evidence |
|---|---|
| Full frontend | **937 PASS / 34 files**, 23.17s; `/tmp/backup-picker-review-front.log` |
| Focused picker + existing feedback context + physical preview | **36 PASS / 3 files** (8 + 22 + 6), 1.97s; `/tmp/backup-picker-review-focused.log` |
| TypeScript / production build | PASS; `/tmp/backup-picker-review-ts.log`, `/tmp/backup-picker-review-build.log` |
| Author Chrome probe independently rerun | **28 assertion groups PASS**, EN/ZH; copied only to `/tmp`, original evidence preserved; `/tmp/backup-picker-review-author-browser.log` and `/tmp/backup-picker-review-author-browser/browser.json` |
| New independent Chrome adverse sequence | **60 assertion groups PASS**, EN/ZH × 1440/360 widths; `/tmp/backup-picker-review-independent.mjs`, `.log`, `.json`; Chrome155.0.8059.80 |
| Handler/scope proof | All three complete handler spans byte-equal to base; exactly the four permitted paths; `/tmp/backup-picker-review-unchanged.json`; `git diff --check` PASS |

The new Chrome sequence starts with a previous APPLIED receipt, verifies empty
file-list cancellation and misleading non-ZIP names produce zero stage POSTs,
rejects invalid bytes with a ZIP extension, then defers a successful stage to
check busy controls and suppression of old success. It confirms no automatic
POST, rejects lowercase `restore`, and sends exactly one confirm only after
explicit exact `RESTORE` plus button click. A new non-ZIP selection and rejected
ZIP both suppress that completed operation's success. Deliberate good-file
reselection uses a new inspection ID, empty confirmation, then explicit cancel
returns to the correctly labelled previous receipt. Each context has exactly
four stage, one confirm and one cancel POST; raw bytes, request headers and
restore IDs are asserted. All API responses are intercepted synthetic fixtures;
external requests are aborted and asserted absent. No page errors or unexpected
console errors. Localized hint, keyboard focus and hint width checked; the
360px Chinese screenshot `/tmp/backup-picker-review-zh-CN-360.png` was visually
inspected and is readable without clipping. Other screenshots remain in `/tmp`.

No existing test or assertion was modified/deleted/skipped. Backend, other file
pickers, upload/cancel/confirm handlers, archive authority, Schema, dependencies,
config and model eligibility are unchanged. Existing full-suite React act
warnings remain visible; no suppression added. Agent-browser CLI is unavailable
as previously recorded, so the installed Playwright-core drove actual isolated
Google Chrome; no software was installed.

**Limits / root acceptance:** headless `setInputFiles` and empty FileList do not
exercise NSOpenPanel or prove native cancellation. Root still must verify its
Chrome154/macOS ordinary picker accepts the real ZIP without an All files
workaround and performs real strict stage/restore validation. This engineering
approval does not substitute synthetic ZIP bytes or preview counts for that
acceptance. No root service/UI, owner/formal data, paid/model/load/debug/generation
IO was used. Only own frontend port5197 was served, then stopped. Reviewer writes
only this handoff and stops after its review commit; root owns final acceptance.
