# TASK-READINESS-CLOUD-PREVIEW-UI-REVIEW

## Verdict and fixed scope

**APPROVE — bounded frontend engineering slice.** No confirmed P0/P1/P2 finding in this diff. Real accepted-backend/headful acceptance remains a separate Root gate before marking the task DONE; this report does not qualify a model or approve main adoption.

- Reviewer: `/root/cloud_preview_review`, independent of the frontend implementer.
- Author: `7353e7ad3f07aa725c4913569ff54d24c4ebd233`.
- Base: `2e5df5b4afb633464a3480c097b3f7f58b5dec56`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-cloud-preview-ui-review`; branch `codex/task-readiness-cloud-preview-ui-review`.
- Review baseline `a6737675897f5c4e05300ee8b88ca138580215b0` adds only Root's review task/prompt. Product/test equality against the fixed author was independently checked with `git diff --quiet 7353e7ad... -- src frontend/src frontend/m13-cloud-consent.e2e.mjs tests`.
- Reviewed only six changed files: App implementation, translations, existing App tests, new cloud preview tests, mocked consent browser fixture and author handoff. Reviewer writes only this report; no backend, Schema, dependency, credential, production configuration, owner data or main change.

## Review method

Read the assigned task/prompt, original UI task and author handoff, repository instructions/current status and established cloud privacy/cost/Evidence contracts. Applied code-review-and-quality and frontend-ui-engineering. Graph-first discovery found the older Content/guard helpers; new symbols were not indexed, so the fixed current diff and source were read directly. Tests were examined for intended behavior and weakening, then current-source checks were run. Existing installed dependencies were reused through an ignored node_modules symlink; no install or lockfile change. No subagents, account, credential, real provider call, owner database or external upload were used. Jev was unavailable; safe/default independent review retained.

## Five-axis assessment

**Correctness.** Explicit YouTube + available Summary/transcript + WAITING_MODEL exposes preparation without requiring the old cloud-available/key flag. Backend eligibility remains authoritative; LOCAL/BILIBILI do not get operative upload actions. Opening only displays information; explicit preparation calls the accepted read-only route. Missing/malformed response, wrong Content, ticket/hash/expiry, evidence mismatch, unsupported/malformed output bound and invalid context structures do not create a confirmable UI. Backend readiness must have boolean can_confirm, an array of string blockers and a budget state. Every nonempty blocker, including unknown codes, disables confirmation. Null outgoing_request yields no output bound and cannot confirm. Missing/malformed readiness likewise fails closed.

The expiration timer disables the native button, and the click handler independently checks the current time. The synchronous busy ref prevents a rapid duplicate action before React renders. Confirmation copies the exact opaque ticket and removes it locally before awaiting a result; refusal/uncertainty does not automatically retry or reuse it. Content remains readable, with explicit new review and Settings actions. Manual command identity is stable within the Content view.

The component is keyed by Content identity. Generation guards and effect cleanup ignore late responses after close, hash navigation or unmount; closing/remounting discards local preview/consent state. A pending confirmed request is not falsely cancelled by closing its preview. The Settings anchor is the existing `#Settings` route. Evidence links use the existing encoded `#Content/{id}/Evidence/{id}` route, whose parser/focus handling was checked; no source/deep-link protocol changes.

**Security/privacy.** Model/provider, cost status, excerpts, personalization/focus/ignore/style and output limit are rendered from the backend response. The new rendered flow removes hardcoded paid K2.6 rates/identity and the blanket high-quality implication. Unknown costs/unverified budgets are explicitly not presented as free. Source excerpts/context are JSX text, and raw JSON is escaped text in collapsed details; no unsafe HTML injection is used. No credential fetch, account registration or provider request occurs on opening. The UI cannot override backend current authorization, budget, claim or qualification. Old dictionary entries remaining unused are not rendered disclosures and were not broadly cleaned up.

**Architecture/readability.** The change extracts a focused Content preview component and a runtime DTO reader, reusing the existing API helper, translations, navigation and styles. It does not introduce another execution lifecycle, provider selector or generic endpoint configuration. Dense local formatting is consistent with the surrounding file and does not conceal a concrete defect. The backend's accepted immutable authority and at-most-once behavior remain untouched.

**Performance.** The UI stores one current preview, uses one expiry timeout and bounded evidence/context arrays, and invalidates obsolete asynchronous work rather than accumulating responses or retries. No polling, model loading, automatic preview or automatic confirmation was introduced by opening the section.

**Accessibility/design.** Visible bilingual labels, native buttons/disabled state, existing anchors, a named disclosure section, status/error roles and semantic headings/details are present. Existing DESIGN/classes are reused; there is no unreviewed styling redesign. Responsive geometry, actual keyboard traversal and real backend/headful behavior remain Root's pending manual supplement, rather than being inferred from jsdom.

## Independent checks

| Check on fixed author source | Result |
|---|---|
| `npm run typecheck` | PASS |
| `npm run test -- src/workspace/App.test.tsx src/workspace/App.model-readiness.test.tsx src/workspace/App.cloud-preview.test.tsx` | **187 PASS**, 3 files, 10.68s; 148 App +12 readiness +27 preview. Existing React act warnings retained. |
| `npm run build` | PASS; TypeScript and 52 Vite modules, 535ms |
| `node --check frontend/m13-cloud-consent.e2e.mjs` | PASS; browser fixture not launched by reviewer |
| `git diff --check 2e5df5b... 7353e7ad...` | PASS |
| Product/test source equality against author | PASS |
| Additional current-source runtime parser probe | PASS: valid DTO accepted; 13 invalid/mismatched route/identity/hash/expiry/request-model/output-bound/data cases rejected; no fetch/backend/provider |

The independent parser probe transpiled the exact current `readCloudReview` fragment using the already installed TypeScript, executed it in memory with the existing primitive guard semantics and discarded the process; no test or product file was edited. The 187 existing tests separately exercise both languages, no-key exact disclosure, all known/unknown blockers, malformed readiness/identity, actual expiration, duplicate click, dismissal/old-content/confirmation late responses, remount, failures preserving Content, and LOCAL/BILIBILI denial.

Changed old tests intentionally replace fixed-provider/rate assertions with real response-derived disclosure, keyless/no-opening-write and no-hardcoded-rate assertions. The existing browser fixture now supplies the actual DTO and distinct valid hashes, verifies a no-key disabled stage, and labels its separate positive admission as offline-only. No safety assertion was deleted to conceal a failure, no test skipped and no fixture treated as model qualification.

## GUI evidence and remaining gates

Author evidence is accurately bounded: the synthetic in-memory API + built frontend probe showed reviews1/confirms0/credentialRequests0, disabled confirmation and the exact fixture excerpt. Earlier browser errors and the incomplete earlier screenshot are retained in the author handoff, not reclassified as success. This is mocked-backend UI evidence only; it proves neither actual backend side effects nor Backup readiness nor cloud quality.

Root separately owns the accepted-source backend6179/frontend6178 acceptance with NoCredentials, all outbound sockets denied, isolated79-table/19-DATA stock and worker=false. The reviewer did not use, write, shut down or claim results from that database/service/browser session. Root must attach its actual backend/headful screenshot, narrow viewport/keyboard and no-persistence/Backup/cancellation evidence before task DONE and manual update. Incomplete free provider, first-run configuration, monetary policy, model qualification, whole-feature full regression and final adoption remain outside this slice and are not silently approved here.

Reuse: DIRECT accepted DTO/routes/API helper, existing hash navigation, Settings, React primitives, bilingual dictionary, existing UI styles/design reference and installed build/test tools. No third-party code/dependency or new license obligation. No implementation repair is required by this bounded engineering review. Root retains acceptance/integration authority. Report commit, clean STOP.
