# TASK-READINESS-CLOUD-PREVIEW-UI — Implementer handoff

- Base: `2e5df5b4afb633464a3480c097b3f7f58b5dec56`; branch `codex/task-readiness-cloud-preview-ui`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-cloud-preview-ui`; sole frontend writer. Head is the commit containing this report. Recommendation **IN_REVIEW**, not DONE/accepted/merged.
- Scope: `App.tsx`, `uiLanguage.tsx`, existing App tests, new `App.cloud-preview.test.tsx`, existing mocked consent browser fixture. No backend/DTO/Schema/configuration/dependency/lockfile/credential/model/owner-data/main changes. No new provider or provider selector.

## Behavior

A small `CloudIntelligencePreview` component inside App.tsx replaces the existing disclosure only. Explicit YOUTUBE + available Summary/transcript can prepare review without `cloud_intelligence_available` or a key when WAITING_MODEL, or when fresh NOT_PROCESSED with backend `manual_intelligence_eligible===true`. Backend remains responsible for public/eligible source and canonical Evidence; missing authority produces a localized error while Content stays readable. LOCAL/BILIBILI show no operative preview action.

Opening shows a neutral scope explanation, with no provider request or automatic preview/confirmation. Explicit preparation uses the accepted read-only route. Provider/model, cost status, output language/limit, exact Evidence excerpts, personalization/focus/ignore/style and optional raw request details come from that response. Hardcoded K2.6 identity/rates/high-quality cloud button are removed. Existing DESIGN.md/styles are reused; no design-system/styling changes.

Runtime checks reject malformed/mismatched ticket, expiry, data/Evidence or output bounds. Missing/malformed readiness and every blocker fail closed; unknown blockers receive neutral localized guidance. Backend `can_confirm===true`, empty blockers, supported bounded request and a live ticket are all required. A real expiry timer disables the control; the click handler rechecks actual time. The Settings link uses existing `#Settings`; no settings component changes were necessary.

A synchronous busy ref prevents duplicate clicks. Confirmation submits the opaque review_hash, consumes local ticket state before awaiting response and never retries automatically. Refusal/uncertainty retains Content and offers new review/settings; local manual command identity remains stable across reviews within the same Content view. Close, navigation/hash change, unmount/reload and new preparation invalidate local state. Request-generation guards prevent late review/confirmation responses or feedback crossing into a closed/new Content. Original extraction/cancellation, Source links and Deep Analysis behavior are preserved.

## Evidence

| Check | Result |
|---|---|
| Meaningful RED, keyless bilingual entry tests | Original UI failed: `Unable to find role=button name=Review cloud Intelligence`; preparation was gated by credential availability. |
| Final App + model-readiness + new preview tests | **187 passed**, 10.62s: 148 existing App, 12 model readiness, 27 focused preview cases. Existing React act warnings remain. |
| TypeScript `tsc -p frontend/tsconfig.json --pretty false` | PASS |
| Vite production build | PASS, 52 modules, 569ms |
| Existing mocked consent browser fixture `node --check` | PASS; updated to valid distinct input/ticket hashes, actual DTO fields, blocked no-key stage and explicitly offline positive admission. Whole fixture not launched. |
| `git diff --check`, scoped diff review | PASS; no unrelated changes or weakened safety assertions. |

Focused tests include both languages/keyless preparation and exact data, every known/unknown blocker, malformed readiness/identity/expiry, actual timer expiration, opaque ticket and double click, dismissal with late response, old-content late response, pending confirmation navigation, remount clearing, preparation/confirmation failures preserving Content, explicit new review and LOCAL/BILIBILI denial. Old tests requiring fixed paid disclosure were intentionally updated to stronger data-scope/no-hardcoded-rate/no-opening-write assertions; the ticket test now supplies a valid **offline-only** readiness DTO rather than bypassing validation.

Development issues fixed: one TypeScript unknown-array narrowing error; duplicate dictionary keys; selectors that also matched collapsed raw details or existing Settings links. No tests were deleted/skipped or implementation guards weakened.

## GUI boundary / remaining acceptance

Only an isolated **in-memory synthetic API** and the built frontend ran at port5193. No product backend, SQLite, Keychain, account or provider transport was loaded. The page title and data explicitly identify simulated UI acceptance. Initial agent-browser calls encountered an opaque/about:blank document, unknown refs and `Resource temporarily unavailable (os error 35)`; local doctor passed. These were retained rather than called a UI success.

The final bounded probe (already started before Root requested stop) used documented scroll-into-view and completed the simulated preview: snapshot showed confirmation disabled; DOM checks `confirmDisabled=true`, `hasMissingCredential=true`, `hasExactExcerpt=true`; fixture counters **reviews=1, confirms=0, credentialRequests=0**. Screenshot: `.var/cloud-preview-ui-qa/keyless-zh-scroll-simulated.png`, visually inspected. Earlier `.var/cloud-preview-ui-qa/keyless-zh-simulated.png` shows only the disclosure, not a successful review. Fixture source is the ignored `.var/cloud-preview-ui-qa/fixture-server.mjs`. Owned browser and fixture server stopped. No further GUI attempts after Root's stop request.

This is **simulated backend GUI evidence only**. Real accepted backend/headful, narrow viewport/keyboard, cancellation/Backup and whole-feature acceptance remain for Root's prepared isolated6179 QA and independent reviewer. The minimal fixture's unrelated Deep Analysis read-error state is not a real backend finding. No model qualification, real cloud availability/free quota, Backup readiness or whole Goal completion is claimed.

## Reuse / review

DIRECT: accepted cloud DTO/routes, existing api/post, Settings/hash navigation, React state/effects/refs, bilingual dictionary and existing UI classes/Design reference. Existing React/Vitest/TypeScript/Vite dependencies reused through ignored symlink to root worktree node_modules; nothing installed. No external code copied; internal base/NOTICE preserved. Graph-first lookup had no matching frontend symbol, so current source was read. Jev unavailable; safe/default workflow retained. Applied frontend-ui-engineering, agent-browser runtime core and Git/TDD/incremental workflow.

Independent review/Root acceptance pending. Commit clean and STOP; no integration or task status change by Implementer.


## Minimal repair after Root real-API finding — 2026-10-27

Root's actual isolated6179 DTO for public `IwglW_hIL_g` has Summary/transcript AVAILABLE, manual eligibility true, Intelligence NOT_PROCESSED, cloud availability false and local NOT_QUALIFIED/CONFIGURATION_REQUIRED. Commit7353's WAITING_MODEL-only entry was unreachable because local extraction was correctly disabled. That is a real product gap; the earlier simulated WAITING_MODEL screenshot did not establish the fresh-user path. Evidence read-only: `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/cloud-preview-real-api-20261026/IwglW_hIL_g-before.json`.

Repair changes only that display condition: retain the existing WAITING_MODEL entry and add NOT_PROCESSED **only with backend manual eligibility true**, retaining explicit YOUTUBE and trusted Summary/transcript checks. Local extraction remains disabled; no artificial wait/qualification, new running/ambiguous/completed entry, automatic preview, backend contract or execution gate was introduced.

Meaningful RED reproduced both English and Chinese missing-preview buttons with the exact above state, including the actual closed local capability shape. GREEN now proves disabled local extraction remains disabled; opening makes no write; the only POST is read-only review; cloud confirmation stays disabled; Summary remains and no extraction/confirmation route is called. These are offline UI assertions, not a new database acceptance claim.

Final repair checks: **189 passed**, 10.36s (the original187 plus two bilingual regression cases); TypeScript PASS; Vite build PASS, 52 modules/607ms; scoped diff check PASS. The only source edit is one rendering predicate; related regression and this handoff accompany it. No assertions removed or weakened. Commit7353 history is preserved; this repair is a new commit pending independent review and Root's real API/headful rerun. No browser, Root service/database, key, provider or model operation occurred during repair. STOP after the new commit.
