# TASK-READINESS-BIGMODEL-SETTINGS-REVIEW

## Scope and verdict

- Independent Reviewer: `/root/bigmodel_audit_review`; no subagents.
- Base: `2065e49777ffd83ef1c36f0085c0b936cc4d7f6e`.
- Fixed author: `e9f790a8ad16fbbbc138db6d34857b4a672234f5`.
- Review baseline: `ef16b2b7bdf6221f3c7019c00b602d974eacdb59`, author source plus only Root review task/prompt.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-settings-review`.
- Branch: `codex/task-readiness-bigmodel-settings-review`; date2026-10-27.
- **Verdict: REJECT fixed e9, two confirmed P2 findings.** No new P0/P1 was confirmed in this bounded configuration-only slice. Original writer and Root received both counterexamples. Later repair/WIP is not included in this review.

Only this report was added to tracked files. No business/test changes, credential/native Keychain access, environment secret reads, external HTTP/model requests, owner/Root QA access, schema/data/configuration/main changes occurred. Synthetic keys and MemoryStore were used exclusively. No qualification, connection, free-account entitlement or fee authority is granted by these checks.

## P2-01 — outer Cloud disclosure does not clear the hidden password

`frontend/src/workspace/BigModelSettings.tsx:81` clears its key only when its own details element closes. `frontend/src/workspace/App.tsx:4176` wraps the component in another Cloud setup details element. Closing that parent hides the form without closing the child or unmounting it. The sensitive draft therefore survives an ordinary fold, contrary to the explicit task requirement.

Independent reproduction used JSDOM, the actual unchanged BigModelSettings and UiLanguageProvider, existing React/testing-library, and in-memory esbuild (`write:false`), not a mock implementation or real browser. Render an initially open parent `<details><summary>Cloud parent</summary><BigModelSettings/></details>`; open the candidate; wait for synthetic GET status NONE; type `synthetic-fold-draft`; click the parent summary; flush the toggle event. Actual output:

```json
{"parentOpen":false,"childOpen":true,"passwordDraftLength":20}
```

The probe unmounted the component and closed its JSDOM window after the observation. Its bundled testing-library process retained an idle handle; only that owned process was interrupted (exit130), not a product failure or Root process. No actual credential or network was used. Reproduction and minimal affected source were sent directly to the original writer.

Minimal repair: clear the new password/confirmation on ancestor Cloud collapse as well as child collapse, preserving lazy reads, navigation/unmount cleanup and existing Moonshot behavior. Add an actual parent-fold regression; do not replace the current child-fold test or silently retain a secret in hidden DOM/state.

## P2-02 — candidate settings accept keys the frozen wire always rejects

`src/youtube_intel/model_settings.py:130` and new PUT validation in `local_api.py:1028` reject only code points below33 and127; non-ASCII whitespace/control and arbitrary Unicode pass. The frontend `BigModelSettings.tsx:95` rejects whitespace but still admits non-ASCII characters, so its validation also differs. The separately frozen BigModel wire accepts only visible ASCII33–126. Thus configuration can say saved/configured for a key that cannot ever reach that candidate wire.

Independent actual API-application probe created a fresh temporary SQLite repository, ForbiddenStore for Moonshot and MemoryStore for BigModel. For each literal below it called the real `LocalApiApplication.handle('PUT', '/api/v1/settings/bigmodel-credential', json.dumps({'credential': key}).encode())`:

| Synthetic input | Actual response | Stored shape |
|---|---|---|
| `synthetic\u2003space` |HTTP200, configured=true |Fails visible-ASCII wire predicate |
| `synthetic\u0085control` |HTTP200, configured=true |Fails visible-ASCII wire predicate |
| `synthetic-密钥` |HTTP200, configured=true |Fails visible-ASCII wire predicate |

Direct new service save/status also records `['save','get']` for all three shapes. No old store/factory was called and no native credential was involved. The configuration status itself correctly remains NOT_VERIFIED/CLOSED; the defect is accepting known unsupported key syntax and reporting successful configuration, not an observed quality/fee grant.

Minimal repair: make the new service, new API validation and new UI validation share the candidate's finite accepted character policy (visible ASCII, existing conservative length). Reject before store access, retain actionable redacted feedback and password draft for correction, and leave old Moonshot validation/service/env/route behavior intact. Existing valid synthetic ASCII save/delete and isolation controls must remain.

## Independent checks and exact results

All Python runs use existing `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-settings-review/src`. Compile preceded tests. No packages were installed: the first frontend command exited127 (`vitest: command not found`) because this new worktree lacked dependencies. With Root's explicit permission only the ignored `frontend/node_modules` symlink was created pointing to Root's existing frontend/node_modules. Package files, lockfiles and dependency versions are unchanged.

| Check | Independent result |
|---|---|
| In-memory compile three changed Python product files |3PASS |
| `python -m pytest -p no:cacheprovider tests/unit/test_bigmodel_settings.py tests/unit/test_closure_model_settings.py tests/unit/test_local_api.py tests/integration/test_runtime_composition.py -q --tb=short` |**103PASS**,58.73s |
| `npm --prefix frontend test -- --reporter=dot` |**1065PASS/1FAIL**,40passed/1failed file,26.37s; details below |
| One complete failed-file follow-up: `npm --prefix frontend test -- src/workspace/App.content-status-load.test.tsx --reporter=dot` |**17PASS**,1.43s overall; tests515ms |
| `npm --prefix frontend run typecheck` |PASS |
| `npm --prefix frontend run build` |PASS;53modules,571ms; JS `index-DUioWJVh.js`, CSS `index-CPV_piR3.css` |
| `python -m mypy --strict src` |122files PASS |
| `ruff check --no-cache src tests/unit/test_bigmodel_settings.py tests/integration/test_runtime_composition.py` |PASS |
| `git diff --check 2065e497 e9f790a8` |PASS |
| Parent-fold and unsupported-key counterexamples |Both confirmed as above |

Full frontend failure is preserved, not relabeled by the isolated follow-up:

```text
FAIL src/workspace/App.content-status-load.test.tsx
reads delayed Deep Analysis without inventing a lifecycle or qualification in en
TypeError: finish is not a function
src/workspace/App.content-status-load.test.tsx:41:25
await act(async () => finish(response(...)))
```

The unchanged test waits for an already rendered heading/status before invoking a resolver assigned by the read effect; it does not explicitly wait for that read to begin. Its once-only full-file follow-up passed. This is evidence of a timing-sensitive test, not a demonstrated source regression caused by settings, and not a fully green independent frontend run. No assertion/test was modified, skipped or weakened. A repaired final candidate still needs its full final-source frontend run. Existing React act warnings also appeared; they were not hidden.

Independent AST/source checks confirm old `MacOSKeychainCredentialStore`, `ModelSettingsService` and runtime `cloud_service` source segments byte-identical to base. All45 protected files (41 packaged SQL001–042, state.py, distillation.py, pyproject.toml, frontend/package-lock.json) are byte-identical. All513 tracked `src`, `tests`, `frontend/src` files equal fixed author e9 after verification; sorted path+bytes SHA256 `f2ccde4780e8a968064462526c4257ccb0930cfe45f200271c618b779daab409`.

## Review coverage, reuse and limits

Reviewed all15 changed files, tests first, plus repository collaboration/status/product/system/reuse/DESIGN and task/prompt/handoff. Used code-review-and-quality, security-and-hardening and frontend-ui-engineering skills. Graph-first discovery identified original store/service; new symbols needed current-source fallback. Jev was not exposed, so the existing strong independent review remained in place.

Namespace isolation, trusted-code-only QA injection, lazy constructor/store access, strict method/query/body handling, Origin/X-YIA/no-store/error redaction, save/delete touching only selected store, old factory unchanged, no environment fallback, no arbitrary HTTP namespace/model/service selection and no provider activation were checked. New status remains precisely candidate-only NOT_VERIFIED/CLOSED. Inspected async pending/mounted guards, navigation/unmount and direct child-fold draft cleanup, double submit/delete confirmation, bilingual text, strict internal Content/Evidence return and onboarding skip. The exact cloud-preview href update is consistent with the assigned new deep link; prior disabled-confirm/zero-credential/zero-confirm safety assertions remain intact. The Cloud preview's current provider remains the old runtime; candidate labels explicitly say configuration is not production selection or qualification.

DIRECT existing standard-library Keychain/loopback APIs, React, details/field/button/routing and tests; ADAPT finite existing store/service patterns; REFERENCE existing DESIGN/preflight/provider docs. No new SDK, framework, dependency or license obligation. The production adapter and budget file remain protected; this settings slice cannot inherit Moonshot qualification or paid authorization. No new unrelated functionality was found.

Author's103backend/1066frontend, early162PASS3FAIL hidden-read pollution,1064PASS2FAIL expected-href update, one static type error and wrong GUI selector remain their separate historical evidence. Author's nine fake-key headful checks use a real local API but a zero-Content-DATA fixture: they cannot establish true populated Content reading or Backup/Restore. This review did not rerun a real browser, native Keychain or populated Root QA, and does not claim those passes. Root retains true isolated Content/Evidence return, native QA-only manual key entry, current account/free-policy checks, actual public model semantic qualification and final complete user journey/restart/Backup/Restore/release gates.

**REJECT fixed e9 pending the two P2 corrections and independent fixed-delta verification.** Root owns acceptance/integration. No production adoption or whole-Goal completion is claimed.
