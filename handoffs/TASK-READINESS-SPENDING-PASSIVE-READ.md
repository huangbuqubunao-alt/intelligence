# Spending settings passive-read admission

Implementer `/root/v3_price_label`, task assigned by Root on 2026-11-07. Worktree `/Users/hua/Documents/yia-worktrees/readiness-spending-passive-read`, branch `codex/readiness-spending-passive-read`, base `18a2121c3364899febf9ff6214afd427ee279e80`. Root owns review, integration and actual browser verification.

## Goal and diagnosis

The real settings page saved its policy, then full reload twice displayed unverifiable history. Serial API inspection still showed the saved revision. Deterministic Event tests reproduced both status and update failing while the same `BackupRestoreService` held its known passive readiness inspection.

`CloudSpendingPolicy._locked` used the direct shared admission lock, which immediately conflicts with that passive inspection's exclusive lock. The repository already provides `ordinary_admission_lock` to wait within a fixed bound for this known local reader and reserve admission ahead of another passive poll. Actual maintenance, unknown OS holders and unsafe lock identities still reject admission through that existing implementation.

DIRECT reuse of `BackupRestoreService.ordinary_admission_lock`, journal verification, ordinary API routes, existing synthetic runtime fixture, and existing deterministic Event test helpers. No third-party code or dependency additions.

## Changes

Production change is one line in `cloud_spending_policy.py`, routing the existing `_locked` context through `ordinary_admission_lock`. Journal lock, verification, writes, revisions and reservations retain their existing logic.

Six regression cases in `test_cloud_spending_policy.py` exercise HTTP status and update following passive inspection, exactly one update append, preserved draft accounting and unknown held cost, timeout with no replay, actual maintenance, an external process holding the OS lock, and a hard-linked unsafe admission inode. The test fixture uses its existing fake wire. Worker actual model, credential, network and fee operations total zero.

## Verification

| Check | Result |
|---|---|
| New status/update Event regressions against original code | 2 FAIL, 46 deselected, 9.80s. `.var/spending-passive-read/red.log`. |
| Six new regression cases after the one-line fix | 6 PASS, 46 deselected, 5.52s. `.var/spending-passive-read/focused-green.log`. |
| Complete cloud-policy and Backup/Restore unit files | 165 PASS, 95.82s. One expected duplicate-path ZIP warning. `.var/spending-passive-read/policy-backup.log`. |
| Existing relevant passive/readiness/settings integration cases | 19 PASS, 65 deselected, 36.37s. `.var/spending-passive-read/passive-settings.log`. |
| Cold strict `src` with `PYTHONPATH=src MYPYPATH=src:.`, explicit package bases and `/dev/null` cache | PASS, 132 source files. `.var/spending-passive-read/strict.log`. |
| Ruff for changed Python files | PASS. |
| Python compilation for changed Python files | PASS. |
| `git diff --check` | PASS. |

Actual browser reload and final combined regression belong to Root's integrated candidate. The focused integration selection deliberately covers the existing passive/ordinary/maintenance boundary cases; the other 65 settings cases were outside this check. No failing check remains after the fix.

## Scope review

Only the assigned production module, its existing unit test and this handoff changed. The initial RED records the actual missing passive wait. All existing tests and assertions remain. Suggested state `IN_REVIEW`; scoped commit SHA is reported separately. Root independently determines acceptance.
