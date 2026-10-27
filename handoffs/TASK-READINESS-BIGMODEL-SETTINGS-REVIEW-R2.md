# TASK-READINESS-BIGMODEL-SETTINGS-REVIEW-R2

## Fixed scope and verdict

- Independent Reviewer `/root/bigmodel_audit_review`; no subagents;2026-10-27.
- Original author `e9f790a8ad16fbbbc138db6d34857b4a672234f5`; original REJECT `d77889f5778114773cbbdb6491471343976ca8ac` preserved.
- Fixed repair `f9a8cdbae81d4420d32cb2b196ffa707d5a96c86`.
- Review baseline `8d9bb2a320ea833d41e0691f4b828464b4ae0461`, fixed source plus only Root review task/prompt.
- Worktree `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-settings-review-r2`; branch `codex/task-readiness-bigmodel-settings-review-r2`.
- **Verdict: APPROVE cumulative e9+f9, bounded configuration/UI engineering only. Both original P2 findings are closed. No remaining confirmed P0/P1/P2 within this slice.** Root retains acceptance/integration and actual user-key QA. This does not approve the separately rejected transport/audit snapshot path, grant model qualification or declare the whole Goal/production adoption complete.

Only this report was added to tracked files. No product/test edits, native Keychain, environment/actual key reads, external requests, model calls, owner/Root QA data, state/SQL, dependencies/configuration/main modifications occurred. Tests use fake stores and synthetic key strings. The ignored frontend/node_modules symlink only reuses Root's existing dependencies, explicitly authorized; no install/package/lock/toolchain change.

## Two original P2 fixes independently verified

**Ancestor folding.** The component now registers non-bubbling native toggle listeners on enclosing details elements, clears key/confirmation when any ancestor closes and removes the exact listeners on unmount. The original child toggle/navigation/unmount cleanup remains. Pending mutation handling does not restore the cleared draft; it only updates safe configuration status/message on the still-mounted form.

Replayed the original actual-component JSDOM probe with existing React/testing-library and in-memory esbuild (`write:false`, no test/source file added). It rendered an open parent details and real BigModelSettings/UiLanguageProvider, returned synthetic KEYCHAIN status, typed a synthetic password, checked deletion confirmation and folded the parent. Both ordinary and deferred PUT variants passed. It then completed the PUT, reopened the parent, confirmed the draft stayed empty, unmounted and checked callback removal. Actual exit0 output:

```text
{"inflight":false,"passwordLength":0,"confirmed":false,"puts":0}
{"inflight":true,"passwordLength":0,"confirmed":false,"puts":1}
ancestor cleanup paired: 2 2 true
```

The new full component file additionally retains child-fold, exact Content/Evidence return, closed-form lazy reads, navigation/password cleanup, one-write double-submit, explicit independent delete, status errors, invalid response and unverified save handling. No hidden draft resurrection or extra request was observed. JSDOM is explicitly component runtime evidence, not a real macOS browser claim.

**Unsupported key characters.** New-provider `validate_credential` enforces string/length1–2048/visible ASCII33–126, reused before API store access and by direct service save. The frontend uses the same accepted range for button and submit callback, with localized actionable feedback and aria-invalid/description. Values are not silently trimmed by application code. HTML password fields naturally remove pasted CR/LF; the new explicit browser-input test reflects that native behavior, while raw backend newline requests remain denied by retained tests.

Independently replayed all three original actual API-application inputs (`synthetic\u2003space`, `synthetic\u0085control`, `synthetic-密钥`) in a fresh temporary SQLite repository with Moonshot ForbiddenStore and BigModel MemoryStore. Each returns VALIDATION_ERROR before any store call; the direct new settings service likewise rejects each before a write. A valid ASCII synthetic key still returns200/configured=true/NOT_VERIFIED/CLOSED. Actual exit0 output:

```text
API refused: VALIDATION_ERROR store calls []
API refused: VALIDATION_ERROR store calls []
API refused: VALIDATION_ERROR store calls []
Valid ASCII save: 200 configured, NOT_VERIFIED/CLOSED; no old store or model
```

The full backend tests also cover zero-width/surrogate cases and valid `!~`/2048 boundaries. No old Moonshot class, factory, route/env behavior or credential policy was changed to implement the repair.

## Independent complete checks

Existing interpreter `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`; all Python uses `PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-settings-review-r2/src`. API probes additionally include this review's tests/unit import path. Compile preceded pytest; all databases/DATA are separate temporary fixtures, no system credential store.

| Command/check | Independent actual result |
|---|---|
| In-memory compile all source |122PASS |
| `python -m pytest -p no:cacheprovider tests/unit/test_bigmodel_settings.py tests/unit/test_closure_model_settings.py tests/unit/test_local_api.py tests/integration/test_runtime_composition.py -q --tb=short` |**115PASS**,65.21s |
| `npm --prefix frontend test -- --reporter=dot` |**1075PASS/41files**,22.66s |
| `npm --prefix frontend run typecheck` |PASS |
| `npm --prefix frontend run build` |PASS,53modules/574ms; JS `index-b2pAA95g.js`, CSS `index-CPV_piR3.css` |
| `python -m mypy --strict src` |122files PASS |
| `ruff check --no-cache src tests/unit/test_bigmodel_settings.py tests/integration/test_runtime_composition.py` |PASS |
| `git diff --check e9f790a8 f9a8cdba` |PASS |
| Independent parent-fold/in-flight/listener-cleanup and actual API/direct-service probes |PASS as above |
| Fixed source equality after checks |513 src/tests/frontend-source files exactf9; combined sorted path+bytes SHA256 `c387ecd7d3593e9bc69661a9c5c9b6f09168b8905e7235f1c9427d070044e8ff` |

All45 original protected files (41 packaged SQL plus state.py/distillation.py/pyproject.toml/frontend lockfile) remain byte-identical to original accepted2065e497. Old MacOSKeychainCredentialStore, ModelSettingsService and cloud_service AST source segments remain exact. The previous delayed Deep Analysis test `App.content-status-load.test.tsx` is byte-identical toe9. This independent full1075PASS is a new final-source result; it does not erase the original e9 full1065PASS1FAIL `finish is not a function` or its one-file17PASS follow-up. React act warnings still appeared and were not hidden. No existing assertion/test was deleted, skipped or weakened. The author's initial new RED failures and native newline test correction remain documented separately.

## Boundaries and remaining work

Read original task/report/handoff and complete fixed delta under existing code-review-and-quality, security-and-hardening and frontend-ui-engineering guidance, preserving the graph-first discovery/current-source fallback already performed for this code. The repair is finite and minimal: ancestor toggle cleanup, new-provider shared validation, one UI helper/hint and added regressions. DIRECT reuse of React/native details, existing protected local API, Keychain adapter and fake-store tests; no new dependency or framework/license obligation.

Original fixed production/QA namespaces, separate Moonshot service/account/env, explicit finite endpoints, method/body/query/Origin/X-YIA/no-store/error protections, candidate-only status, no inference-on-save, lazy selected-store access, no credential/factory crossover and no arbitrary endpoint/provider selection remain intact. UI onboarding remains optional; exact internal Content/Evidence return links remain, and no provider preference or key presence is presented as model qualification or active runtime selection. Qualification NOT_VERIFIED and budget CLOSED remain authoritative for this candidate slice.

Author's fake-key headful11checks/81-table empty-domain dump are useful configuration evidence but do not establish actual native key operation, true populated Content reading, full Backup/Restore, entitlement/zero bill/quota or model semantic quality. This reviewer did not access those real-key/native/Root populated QA surfaces or make provider requests. Root must use its separate trusted QA-only namespace and protected populated clone for user entry/GUI acceptance, without enabling the separately unaccepted transport or actual model calls. State snapshot P2 remains tracked by the separate transport R2 report and is not waived by this settings approval. Formal main, real data, free-policy/actual public quality qualification and the complete user journey retain all original gates.

**APPROVE e9+f9 settings engineering only; Root alone accepts/integrates. Clean STOP after this scoped report commit.**
