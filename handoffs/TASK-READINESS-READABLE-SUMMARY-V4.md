# TASK-READINESS-READABLE-SUMMARY-V4 交接报告

## 元数据

- Task `TASK-READINESS-READABLE-SUMMARY-V4`
- Role `Implementer`, session `/root/readable_summary_v4`
- Base `6fe094912457856fc6dea311f196baf1f64deef8`
- Worktree `/Users/hua/Documents/yia-worktrees/readiness-readable-summary-v4`
- Branch `codex/readiness-readable-summary-v4`
- Reported 2026-11-07
- Head is the task-scoped commit containing this handoff. The exact SHA is returned to Root.
- Authoritative task card is in the controlling worktree at `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/tasks/TASK-READINESS-READABLE-SUMMARY-V4.md`.

## 目标与实际范围

Added the finite pure `system-synthesis-v4-readable-summary` policy identity and transport `moonshot-k31-system-synthesis-v4-readable-summary-20261107`. Its system policy is byte-identical to the accepted v3 source-level policy. Only its final existing `UNTRUSTED_CURRENT_SUMMARY_BASELINE` user DATA body restores every typed Summary text position through `restore_summary_baseline`. The authoritative original Summary proof projection retains its codec, metadata, source binding and semantic hash.

Seven existing Python seams implement the bounded extension. They are `system_synthesis.py`, `system_synthesis_profile.py`, `system_synthesis_qualification.py`, `synthesis_runtime.py`, `distillation.py`, `runtime_composition.py` and `local_api.py`. `summary_baseline.py` and `system_synthesis_persistence.py` have no delta. The separate fixed v4 qualification resource contains `records=[]`. Normal eligibility uses the existing reviewed package authority and exact-language service gate.

The v4 transport alone has a 40,960-byte request ceiling. The original three transports retain 32,768 bytes. The domain ceiling, model identity, output limit, deadline, retries, price arithmetic and provider HTTP implementation retain their accepted values. Price acknowledgement remains profile-specific and the shared journal preserves old holds/events.

Minimal Content and spending selectors expose the fourth profile as “Complete Summary comparison” / “完整摘要对照”. Spending catalog decoding accepts the four finite identities and rejects unknown, duplicate and excess entries. One existing backend assertion now explicitly expects the new fifth entry including legacy.

## Reuse evidence

`DIRECT` project-owned baseline restoration, pure synthesis, persistence/proof verifier, finite adapter inheritance, package qualification, normal factory/API, spending journal, trusted reader, Save, Topic and Backup/Restore. Source is the accepted base commit above under the repository NOTICE. Test fixtures and lifecycle assertions reuse existing owned tests. Python standard-library JSON/dataclasses/pathlib and existing locked Pydantic remain the implementation components. The existing DESIGN.md guided the label-only UI extension. No external code or dependency was introduced.

## 验收证据

| Item | Result | Evidence |
| --- | --- | --- |
| All ten literal Summary fields | PASS | New pointer and literal fixtures compare the entire outgoing semantic object with all ten stored fields, including point kinds, IDs and keywords. E05/core_points[4] parameter-inspection text is present literally. |
| Untrusted input and exact Source message | PASS | Original source/task messages compare byte-for-byte. Injection stays in user DATA. Original Summary proof projection compares exactly and input objects are preserved. |
| Old byte meaning and profile separation | PASS | Existing v1/v2 golden tests passed in the affected group. New pre-change v3 projection, wire, descriptor, origin and reserve goldens passed. Cross-version transport and origin mixtures reject. |
| Bounded capacity | PASS | Exact 40,960-byte v4 wire succeeds, 40,961 rejects. Reserve is recomputed from every literal message byte. Original transport ceiling assertions remain exact. Oversized domain input rejects. |
| Independent qualification and gates | PASS | Empty production resource stays closed. Structural fake package requires the full live/independent-review matrix and separate identity. Missing records, wrong versions/profiles, fixture runs, false controls, missing positives and failed review reject. Raw data cannot seal authority. Normal qualification/credential/execution/budget/price/consent failures create zero execution claims and zero sends. |
| Scope and revalidation | PASS | Rehashed LOCAL scope, Bilibili provider, private availability and changed Summary capture reject before credentials. Current source mutation prevents confirm/claim. Authority mutation after credential resolution rejects before wire. |
| Normal no-new persistence | PASS | Both output languages pass the normal factory/API with fake wire. Exact literal baseline, once-only execution, conservative hold, unchanged DATA/Evidence and persisted proof verification pass. |
| Positive trusted lifecycle | PASS | Existing v3 positive lifecycle assertions run with only the finite v4 factory/profile selected, covering trusted result reader, Save, Topic, Backup/Restore, once-only invocation and held cost. |
| Price reacknowledgement | PASS | A new v4 hash is required. Existing journal events, held request count and held amounts are preserved exactly. |
| Four-profile UI | PASS | Full frontend suite plus real-browser controlled-response inspection described below. |

## 检查结果

Python executable for all commands is `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`.

- Initial affected backend command used `PYTHONPATH=src` and `python -m pytest -q` with `test_synthesis_readable_summary_v4.py`, `test_synthesis_source_level_v3.py`, `test_synthesis_attribution_v2.py`, `test_synthesis_reviewed_authority.py`, `test_system_synthesis.py`, `test_summary_baseline.py`, `test_system_synthesis_persistence.py`, `test_synthesis_runtime.py` and `test_cloud_spending_policy.py`. Result was **340 passed, 1 failed in 211.29s**.
- The sole group failure was `test_actual_factory_declares_finite_profiles_and_keeps_synthesis_unqualified` at `tests/unit/test_synthesis_attribution_v2.py:247`, with `Left contains one more item` identifying the new v4 profile. The expected finite list was extended explicitly. Focused rerun passed **1 test in 2.66s**. Root requested this focused rerun rather than repeating the whole group.
- Full new v4 file before the final focused lifecycle additions passed **26 tests in 22.36s**. Its strengthened existing bilingual no-new test then passed **2 tests in 3.43s**, including unchanged DATA/Evidence and persisted proof verification.
- The final added positive lifecycle test passed **1 test in 5.46s**. This brings the new file to 27 cases, with each addition or strengthened assertion covered by its focused run.
- Cold typecheck ran with `PYTHONPATH=src MYPYPATH=src:. python -m mypy --strict --explicit-package-bases --cache-dir=/dev/null src`. **Success, 132 source files**.
- `python -m ruff check src tests/unit/test_synthesis_readable_summary_v4.py tests/unit/test_synthesis_attribution_v2.py` passed. `python -m compileall -q src` and `git diff --check` passed.
- `npm test` passed **1,158 tests in 43 files, 22.61s**. `npm run typecheck` and `npm run build` passed. Existing React act warnings appeared in unrelated tests. Vite reported its existing-size warning for the 503.10 kB main chunk.

## Browser evidence and limits

A separate isolated browser rendered the actual `CloudSpendingSettings` component with a temporary local HTML harness and controlled API response containing all four prices. English and Chinese accessible snapshots show all four distinct options. Selecting v4 displays its label and keeps Save disabled until acknowledgement. Browser console error inspection was empty. The harness was removed and the browser/dev server closed.

This browser check uses mock responses. It is distinct from a live normal-factory server and from Root's forthcoming actual-source QA. Screenshots are at `/Users/hua/.agent-browser/tmp/screenshots/screenshot-1794004409154.png` and `/Users/hua/.agent-browser/tmp/screenshots/screenshot-1794004409704.png`.

## Diff 复核与失败记录

The diff is limited to the seven Python seams, one new empty qualification resource, three minimal UI files, relevant frontend tests, one finite-list assertion, one new regression file and this handoff. Existing old resources, Summary codec, persistence codec, migrations, dependencies, operational trial scripts and Root controls have no delta. No credentials, model, network/paid call, formal data or operational package was used by this implementation.

Initial new fixture construction was rejected by existing Summary catalog validation. First it used E05 without earlier aliases (`Summary source aliases differ from the original catalog`). A corrected five-row fixture then exposed its unsorted time/identity ordering (`Summary source reference order is invalid`). The fixture now supplies genuine ordered E01–E05 captures. An initial oversized-domain assertion expected “ceiling” while the earlier parser correctly returned “System analysis JSON is missing or oversized”. The assertion now matches that precise existing error. Implementation validation was retained throughout. Ruff initially identified compact test control statements, which were expanded into ordinary multiline code.

Graph discovery was attempted first but the available indexes returned no relevant finite-profile symbols. Scoped reads followed. The single Jev advisory call returned HTTP451, so execution continued with the assigned safe/default workflow and Root-owned independent review.

## 交接与剩余验证

Suggested status is `IN_REVIEW`. Root owns fixed-delta independent review, actual public-source normal-entry replay, final full-backend integration checks, design acceptance and any future fee decision. The task-card public-case byte measurements are Root's prior offline evidence. This implementation independently proves the exact ceiling and arithmetic, and uses owned synthetic fixtures for normal-factory language/lifecycle verification. No actual model semantic qualification is claimed. The new package resource remains empty.
