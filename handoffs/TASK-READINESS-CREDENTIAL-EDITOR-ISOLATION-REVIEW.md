# TASK-READINESS-CREDENTIAL-EDITOR-ISOLATION-REVIEW

- Independent Reviewer `/root/bigmodel_audit_review`;2026-10-28; no subagents.
- Comparison base `b0fab81268090430e41017bee9ecb647875b63e2`; fixed author `92059a1fcfd5aaf5669bbabe2706a6f055eba5ce`.
- Review baseline `6c5d85a8750b8ee0bb710db5250e84ce0ad3793c`, author source plus only Root review task/prompt.
- WT `/Users/hua/Documents/yia-worktrees/readiness-credential-editor-isolation-review`, branch `codex/task-readiness-credential-editor-isolation-review`.
- **Verdict: APPROVE, bounded credential-editor UI isolation only. No confirmed remaining P0/P1/P2 in this fixed slice.** Root owns acceptance/integration and actual populated QA. This does not approve model qualification, fees, private uploads, actual autofill guarantees or whole-Goal/main adoption.

Only this review report is written to tracked files. No business/test repairs, native Keychain or real key/environment reads, Root6178/6179/browser/QA/owner access, actual provider requests, schema/dependency/configuration/main changes. An ignored frontend/node_modules symlink only reuses existing Root dependencies as expressly permitted, with no package installation or lockfile change.

## Scope and findings

Reviewed all10 changed files, original task/prompt/handoff, accepted f9/5bdb context and current product/DESIGN boundaries under code-review-and-quality, security-and-hardening and frontend-ui-engineering guidance. Existing symbol discovery/context was reused; exact current source supplied this finite UI delta.

ModelSettings owns only `bigmodel | moonshot | null` editing selection. Default and legacy closed states mount no password. Exactly one selected editor mounts its service-specific id/name/label/password and delete controls. Selection and both folds clear unsaved drafts/confirmation rather than transfer values, change saved keys or change the runtime provider. Both service/model names and edit-only explanation are explicit. BigModel's exact existing deep link selects only its editor; original internal Content/Evidence return/history semantics remain. API/key namespaces and qualification remain unchanged. Saved values are never copied into fields or localStorage/DB/backup.

Both pending guards are instance refs outside the conditionally mounted editor body, so switch/hide does not reset an already dispatched request or enable a second click. Late results clear drafts and update safe metadata only; nothing labels the request cancelled. BigModel serializes an explicit fresh metadata read on return after settlement. Old Moonshot preserves its original mutation paths/trim/refresh semantics with an immediate once-only ref guard; opening it explicitly refreshes existing metadata. New-provider ASCII/qualification/budget handling remains intact. Hiding does not implicitly delete a saved key.

The two App call changes enable the already existing retainOnRefresh option only for same-path revision-driven Settings and source-policy reads. Independent source comparison proves the shared useRemote hook unchanged. Initial data is still absent/loading; path changes cannot expose another resource's snapshot; read failure still wins through Settings ErrorState. Same-path normal refresh retains the existing mounted guard instead of erasing the editor as soon as old metadata is requested. This does not turn old metadata into new authorization or hide read errors.

Test adaptations track intentional unmount/reselection behavior and fresh GET counts, retaining zero-write, single PUT, exact provider and empty-draft assertions. The two old E2E script changes merely add explicit Moonshot opening and provider-specific labels; all remaining save/delete/DB/no-generation assertions are retained. Their complete E2E scenarios were not run by this review; syntax checks are recorded as such. Native summary controls preserve keyboard interaction, with distinct labels and existing narrow layout/styles. Actual browser autofill remains untested; autocomplete=off and unique ids are not a universal autofill guarantee.

## Independent actual-component negative probe

Used real unchanged ModelSettings/BigModelSettings/UiLanguageProvider with JSDOM, existing React/testing-library and in-memory esbuild (`write:false`), synthetic safe metadata and fake fetch. No backend, browser profile, saved user key, native store or actual request is involved.

Replayed default-zero-password → open BigModel and type → switch Moonshot and type → return BigModel, checking only one password and blank returned drafts. It then submitted BigModel twice while a deferred fake PUT was pending, switched away/back, confirmed the returned input stayed blank/disabled, completed the response, folded the parent and reopened it with no selected password. Actual exit0 output:

```json
{"initialPasswords":0,"switchPasswords":1,"crossDrafts":false,"foldPasswords":0,"writes":[["/api/v1/settings/bigmodel-credential","PUT"]]}
```

Thus the original two-draft family regression is independently covered, including pending switch/return and parent-fold. The complete new test file also exercises old pending saves, both independent save/delete paths, bilingual labels, metadata return, no saved-key transfer/change on selection and unmount during save. Passing these component checks is not a real autofill or populated Content/backend integration claim.

## Independent verification

| Command/check | Actual independent result |
|---|---|
| `npm --prefix frontend run typecheck` |PASS |
| `npm --prefix frontend test -- --reporter=dot` |**1084PASS/42files**,23.28s; existing React act warnings visible |
| `npm --prefix frontend run build` |PASS;53modules/801ms; JS `index-DvbRLqmH.js`, CSS `index-CPV_piR3.css` |
| `node --check frontend/local-provider-regression.e2e.mjs` |PASS, syntax only |
| `node --check frontend/milestone-closure.e2e.mjs` |PASS, syntax only |
| `git diff --check b0fab81 92059a1f` |PASS |
| Real-component fake-key isolation/deferred-save/fold probe |PASS, exact output above |
| Fixed source/test/scripts equality after checks |516 files exact920; sorted path+bytes SHA256 `fc95e54f906d3609248712122f54965eb36e45af4c9d9e19dde08a9618d6bc60` |
| Backend/dependency/toolchain preservation |440 protected files independently compared to Git base; no product backend change |

Initial independent generic preservation check compared438 src/tests/package/lock paths; the exact author's440-path protection manifest was then read only for its public path list and all440 were independently compared to Git base. The shared useRemote byte comparison also passes. No backend tests/mypy/Ruff were rerun for a frontend-only diff with all backend source/tests/dependencies protected; no backend pass is invented.

Author's6RED,19PASS4FAIL,171PASS1FAIL and GUI selector failure remain separately documented historical evidence; they are not erased or added to the independent totals. Changes to assertions were checked against the new explicit-open/unmounted-secret contract. No test skip, safety-assertion removal or weakening was found. Earlier delayed DA timing failure remains historical and its test is unchanged.

DIRECT reuse React/local state/native details, existing form/layout/API client/read hook; ADAPT finite two-provider editors. No new SDK/framework/dependency/license obligation or unrelated redesign. Source remains fixed throughout independent checks; only this report is committed.

Root's future true populated QA/user-key metadata check, actual provider account/entitlement/free-policy/quality/billing and complete user/Backup path remain separate. Author's headful fake-API12checks support UI behavior but are not real backend/credential/Content/Backup proof; this reviewer did not touch that Root live page or claim a new headful run. **APPROVE fixed920 UI isolation only; report commit then clean STOP.**
