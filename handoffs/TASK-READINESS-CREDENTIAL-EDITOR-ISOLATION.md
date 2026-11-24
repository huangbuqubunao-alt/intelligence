# TASK-READINESS-CREDENTIAL-EDITOR-ISOLATION

## Metadata / scope

- Implementer: `/root/bigmodel_audit_writer`, sole writer, no subagents.
- Base: `b0fab81268090430e41017bee9ecb647875b63e2` (accepted f9 settings + Root task/docs).
- WT: `/Users/developer/Documents/yia-worktrees/readiness-credential-editor-isolation`.
- Branch: `codex/task-readiness-credential-editor-isolation`.
- Date: 2026-10-27 start; resumed 2026-10-28 after interruption, retained all WIP/evidence. Head is this scoped commit, reported after commit; clean STOP / IN_REVIEW only.
- No backend, SQL, transport, runtime model/provider choice, credentials, production config, dependency, toolchain, owner or main changes. Root active QA6178/6179/tab/real saved key were never accessed.

## Facts, reuse and change

The prior bounded scout used real f9 React components and two synthetic drafts. Once BigModel was already open, both fields could retain24/24 characters; parent-fold cleared BigModel but retained Moonshot24; saving BigModel left Moonshot24. No old PUT occurred. The Root real page showed a masked old draft, but its value/origin/user action were unknown. This work does not infer user error, a leak or actual browser autofill.

DIRECT existing React18 local state/native details, existing forms and field/button styles, protected API client and read hooks. ADAPT finite existing two-provider editors; REFERENCE DESIGN.md and accepted f9/5bdb review. No third-party code copied, no new component framework, SDK or dependency/license change.

`ModelSettings` now owns a finite `bigmodel | moonshot | null` **editing** selection. Initially neither password is mounted; historical Moonshot is closed. BigModel's existing deep link explicitly selects it and expands the outer disclosure. Provider summaries and old field/save/delete labels name the exact service/model; password fields have fixed service-specific id/name and retain autoComplete=off. This does not claim autofill prevention or switch the executing model.

Only the selected editor mounts its password and deletion controls. Switch/own-close/ancestor-fold/nav/unmount clear both unsaved drafts/confirmation state; closed editors have no live password DOM node. Already saved values are never read into an input, copied between providers or implicitly deleted. Existing API paths/namespaces/qualification/budget and BigModel ASCII33–126/1–2048 rules stay unchanged.

Both operation guards survive hiding an editor; in-flight saves are not retried or claimed cancelled. Late results cannot repopulate drafts. A fresh BigModel metadata read occurs on return, serialized after an already pending request if necessary. Moonshot's existing Settings read refreshes its metadata on explicit opening; successful old writes keep the same original refresh callback. Old input is disabled during its pending write, and the existing old mutation now has an immediate ref guard against duplicate click.

The integrated App reproduction revealed that opening the old editor to refresh metadata cleared Settings data, unmounted the editor and immediately lost the selection/guard. The fix uses the **existing** `retainOnRefresh` option only for the two revision-driven Settings/settings-source-policy reads, preserving already loaded same-path snapshots while rereading. Initial loading and error handling remain unchanged; a failed read still uses existing ErrorState. No global hook or backend behavior was changed.

## Actual files

Products: ModelSettings.tsx, BigModelSettings.tsx, uiLanguage.tsx, App.tsx (two read options only).
Tests: new ModelSettings.test.tsx; BigModelSettings.test.tsx and App.test.tsx adapt to intentional explicit-open/unmounted-closed controls while keeping all route/secret/once/store assertions. Two existing frontend E2E scripts receive the explicit Moonshot-open step and exact provider labels, retaining save/delete/DB assertions. No style or Onboarding modification was needed.

## RED → GREEN / retained failures

All local evidence is `.var/credential-editor-isolation/` in this WT, not Root's QA.

1. Before product edits, `red.log`: **6FAIL** in new real-component file. The default-two-password DOM and lack of explicit old provider editor contradict the new contract. This complements the prior synthetic two-draft scout; no real credentials.
2. Initial implementation `first.log`: **19PASS/4FAIL**, two complete component files. Three old tests referenced detached inputs after intentional unmount and expected a child disclosure to remain open. They now assert no password/confirmation DOM, explicit reselection with blank draft, fresh GETs and unchanged PUT count, rather than weakening safety. The remaining new fixture had a queued initial hashchange from `location.hash` resetting the just-opened editor; new fixtures use history.replaceState for deterministic initial URL without a pending navigation event.
3. `second.log`: **171PASS/1FAIL** across3 complete files. App could not find the newly opened Moonshot field because the metadata refresh immediately unmounted it; fixed product read retention as above. Original old-store write paths, no-generation and no-localStorage assertions remain.
4. `third.log`: **172PASS** across those3 complete files. Added pending old-save/unmount/metadata-return controls then gave **9PASS** in expanded complete new file (`expanded.log`).
5. Final **1084PASS/42files**, `frontend-full.log`,21.41s; no test deleted/skipped/disabled or global timing expectation changed. Existing unrelated React act warnings remain visible. Old delayed DA file is untouched.
6. First headful fake-API run completed key/provider-switch checks but its driver expected an old Chinese status using a full stop, while existing translation uses a comma. `gui-first-failure.log/json/driver.mjs` retained. Corrected driver strings only, no product wording/behavior change; final headful PASS below.

## Checks and exact commands

Existing ignored frontend/node_modules symlink points to Root's previously installed dependencies; no install/upgrade/lockfile edit.

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test -- src/workspace/ModelSettings.test.tsx src/workspace/BigModelSettings.test.tsx src/workspace/App.test.tsx
npm --prefix frontend test
npm --prefix frontend run build
node --check frontend/local-provider-regression.e2e.mjs
node --check frontend/milestone-closure.e2e.mjs
git diff --check
```

- TypeScript PASS before tests and after final source changes (`types-expanded.log`).
- Complete frontend42files / **1084PASS**,21.41s (`frontend-full.log`).
- Production build includes tsc -b PASS; Vite53modules /565ms (`build.log`), JS index-DvbRLqmH.js.
- Both adjusted historical E2E scripts syntax PASS; their entire import/recovery scenarios were **not rerun** in this frontend-only task. No claim of new D2/model/Backup acceptance.
- Diff check PASS. Source hash equality held throughout final tests/GUI for9 changed product/test/script files.
- **440** tracked backend/src/tests/dependency/toolchain files exactly match base, including all backend Python, SQL, transport, existing Python tests and fixtures. No backend tests/Ruff/mypy rerun here: backend is read-only and this task changes only frontend, with full TS/build checks.

## Headful fake-key browser verification

Existing agent-browser skill read; prior Root-recorded CLI about:blank failures were not repeated. DIRECT existing Playwright-core1.62.1 + installed Chrome in a fresh temporary profile, **headless:false**. Own Vite6196 served only this WT. `gui.mjs` intercepts every API route with finite in-memory synthetic stores; no backend/API server, SQLite, nativeKeychain, actual key, external model or Root profile/service is contacted. Other module payloads are placeholders, not capability claims.

`gui-result.json` / `gui-final.log`: **12 actual checks PASS**:

- BigModel deep link mounts only its one empty password; no saved value prefilled.
- Unsupported Unicode has disabled save and actionable Chinese reason.
- Native summary Enter switches services; exactly one password remains; both drafts/delete confirmations reset.
- Switching alone preserves both synthetic saved keys and sends zero mutations.
- Explicit BigModel save affects only BigModel; explicit Moonshot save/delete affects only Moonshot, preserving BigModel.
- Outer fold leaves zero password nodes; reopening the outer family still has zero until explicit selection.
- 320px has no horizontal document overflow; exact Content/Evidence return URL and browser-back leave blank new draft.
- No synthetic key appears in localStorage; no auto model/run/paid fallback path.

Observed requests: **53GET +2PUT +1POST**, with page external=[]; all API requests route-fulfilled in memory. The only mutations are `/settings/bigmodel-credential` PUT, `/settings/cloud-credential` PUT, `/settings/cloud-credential/delete` POST. Dev StrictMode and explicit selections can reread metadata; no duplicated write occurs. Model calls0. This is a real headful UI with fake API, **not** true backend/native/credential/Content/Backup integration.

Screenshots `desktop.png` and `narrow.png` are actual browser captures; desktop visually inspected. Existing local-model/transcription/Backup placeholders in those fake responses do not establish their availability. Target Content is synthetic and unpopulated; only exact route/back/draft behavior is claimed, not a successful real Content read.

Driver: `node .var/credential-editor-isolation/gui.mjs` against own `YIA_API_BASE=http://127.0.0.1:1 npm --prefix frontend run dev -- --host 127.0.0.1 --port 6196 --strictPort`. The unused proxy is deliberately invalid; every browser API request must stay fake. Only synthetic keys are in the driver. Never reuse it for real key entry. Browser closes in finally; own Vite6196 stopped with Ctrl-C after completion. Root live6178/6179 and its profile/key untouched.

## Evidence / handoff boundary

`final-manifest.json` SHA256 **3281b5bbbf9268bf70c59e90d1a6ef8f1aaf7f8fccb9b7405c080939ee735a06** contains9 source SHA,440 protected paths,17 artifact SHA and exact request counts. Original intermediate failure logs remain, not replaced by final green. No production/service startup/config/main action occurred.

Remaining: independent fixed commit review; Root alone may integrate and verify its already-saved QA key via metadata without reading/changing it. Actual autofill, current account eligibility/free limits/quality/billing and complete actual user/Backup chain remain outside this slice. No model qualification, true API readiness, whole-Goal completion or production adoption is claimed. Suggested status IN_REVIEW; commit then clean STOP.
