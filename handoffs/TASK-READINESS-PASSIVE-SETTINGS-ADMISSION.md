# TASK-READINESS-PASSIVE-SETTINGS-ADMISSION 交接报告

## 元数据与范围

- Role: Implementer `/root/qa_launch_isolation`; reported 2026-11-05.
- Base: `893909e304c94abbf10eb955207012b514b1b2c5`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-passive-settings-admission`.
- Branch: `codex/readiness-passive-settings-admission`.
- Commit: this scoped commit; exact SHA returned to Root after commit.
- Goal: a single ordinary settings mutation waits for this instance's known passive readiness inspection instead of returning a false model-configuration 409. True maintenance and unknown execution/lock conditions remain fail-closed.
- Files: `backup_restore.py`, `local_intelligence_settings.py`, actual existing `tests/integration/test_local_intelligence_settings.py`, this handoff. The task card's unit settings test path does not exist; Root was informed and the actual integration file is used under its minimal existing-test allowance.

## 实现与锁顺序

`ordinary_admission_lock()` registers an ordinary waiter under the existing maintenance Condition. Only a different thread's known same-instance passive owner permits a timed Condition wait, at most five seconds. Same-thread ownership, true command intent and timeout reject admission. True command intent notifies waiters immediately. New passive reads yield to registered ordinary waiters, preventing a stream of polls from starving one pending request. Waiter accounting is cleaned in `finally`, including exceptions and timeout.

After the passive owner clears, the original nonblocking SH locks are acquired while the Condition still protects ownership transition. The Condition is released before yielding to configuration guards or caller IO. There is no SQLite transaction held by the waiting caller, no condition held across SQLite/caller work, no OS blocking lock and no release/reacquire gap for a new passive owner. Existing EX maintenance, stable machine/database lock identity checks, nested background-work SH, configuration etag/journal checks and restore/restart guards are retained. Real maintenance may start only after the SH acquisition linearization point; it still cannot acquire EX while that request owns SH.

`LocalIntelligenceSettings.admission()` alone uses this helper. Other worker and maintenance locking is unchanged. This does not retry a mutation, model call, claim, fee or external operation.

Reuse decision: **DIRECT** stdlib `threading.Condition`, monotonic time, `ExitStack` and the existing `admission_lock`/`store_lock` contracts. No new dependency, copied third-party source or license obligation. No schema, credentials, production configuration, frontend, GUI harness or model qualification change.

## 验收证据

Owned evidence directory: `.var/passive-settings-admission/` (ignored, retained in this worktree).

| Check | Result | Evidence |
|---|---|---|
| Original source, Event-held real passive EX + actual loopback HTTP app wired with settings | expected RED: 2 failed, 74 deselected, 5.39s | `initial-red.log`; same single PUT returned 409 `CONFIGURATION_APPLYING` before release; original failure preserved |
| Same unchanged regression after fix, normal and exceptional passive release | PASS: 2 passed, 74 deselected, 5.26s | `first-green.log`; pending before release, same request returns 200, setter exactly once; protected SQL/DATA unchanged |
| Additional boundary tests | PASS: 8 passed, 76 deselected, 13.46s | `new-boundaries.log`; bounded timeout/no stale priority, same-thread rejection, priority against four new polls, nested SH, real command interruption, real subprocess EX, stale etag, restore-pending |
| Complete related files | PASS: 319 passed, 1 expected warning, 248.45s | `related-full.log`, exact command below; duplicate ZIP member warning belongs to the existing invalid-backup rejection fixture |
| Strict mypy all `src` | PASS: 131 source files | `strict-full.log` |
| Ruff changed source/test files | PASS | `ruff-final.log` |
| `compileall -q` changed source/test files | PASS | exit 0 |
| `git diff --check` | PASS | exit 0 |

Commands (venv Python is `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`):

```sh
PYTHONPATH=src "$PYTHON" -m pytest tests/integration/test_local_intelligence_settings.py tests/unit/test_backup_restore.py tests/unit/test_qa_launch_isolation.py tests/unit/test_synthesis_runtime.py tests/unit/test_cloud_spending_policy.py tests/unit/test_task016c_phase_h1_admission.py -q
MYPYPATH=src PYTHONPATH=src "$PYTHON" -m mypy --strict src
"$PYTHON" -m ruff check src/youtube_intel/backup_restore.py src/youtube_intel/local_intelligence_settings.py tests/integration/test_local_intelligence_settings.py
"$PYTHON" -m compileall -q src/youtube_intel/backup_restore.py src/youtube_intel/local_intelligence_settings.py tests/integration/test_local_intelligence_settings.py
git diff --check
```

Tests use owned temporary DB/DATA, fake probes/stores and loopback only. Their real subprocess locks and HTTP requests are local safety/concurrency checks, not external service calls.

## Diff 复核、限制与交接

- Only the two scoped product files, new tests and this handoff changed; existing assertions retained. No generated/lock/dependency files.
- Earlier two real headed GUI failures are retained in Root's final-acceptance worktree. No third GUI run was attempted here; no harness change or suppressed 409.
- Full global backend/frontend/build and positive headed macOS GUI are **NOT RUN in this task**; Root will integrate and run the fixed candidate's actual headed harness. This task establishes the minimal server regression and lock boundary, not overall product acceptance.
- No actual keychain, key, model, fee, external network, formal owner data, live 6478 service, final worktree or `main` writes.
- Five seconds intentionally bounds this narrow passive-only wait. A slow/hung inspection still refuses the mutation; unrelated external contention and actual maintenance remain explicit blockers.
- `DECISION NEEDED`: none. Recommended state: `IN_REVIEW`. No merge/push/deployment and no next task started.

Root reviewer verdict and integration remain for Root; no implementer self-approval is claimed.
