# TASK-READINESS-V4-QUALIFICATION-BUDGET 交接报告

## 元数据

- Role `Implementer`, session `/root/readable_summary_v4`
- Base `469f11a2307c4ed841f533b42e067c0c800ce247`
- Worktree `/Users/developer/Documents/yia-worktrees/readiness-v4-qualification-budget-fix`
- Branch `codex/readiness-v4-qualification-budget-fix`
- Task card `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/tasks/TASK-READINESS-V4-QUALIFICATION-BUDGET.md`
- Reported 2026-11-07. Exact scoped commit SHA is returned to Root.

## 修改与复用

`PersonalizedDistillationService.confirm_synthesis_qualification` now allows an explicitly supplied budget up to 1,500,000 microCNY only after `prepared_input(value)` has validated the exact v4 profile and complete proof. The other profiles retain the 1,000,000 maximum. The method also validates the exact integer types of `prior_calls` and `prior_reserved_microunits` before credentials or reservation. These values still must be zero. The product delta is four inserted lines and one replaced bound, all in this method.

`DIRECT` reuse of the accepted profile/proof validator, normal runtime factory/API preview, owner qualification transport and one-call dispatch, persistence, existing offline network/native-store guards and SQL/DATA inventory functions. Source is the accepted base above and the repository NOTICE. No new dependency or external code is introduced.

Portable regression tests extend `tests/unit/test_synthesis_qualification_entry.py`. They reuse the existing pinned archive `tests/fixtures/bigmodel_public_first_case/stock.zip`, size **723,183 bytes**, SHA256 `f12f59025ef423fb0a3b6b0bd74e33b46846d481879bf8cc431d5c360209065f`. Its existing bounded extractor verifies every member before restoring the public AIRC caption/Summary into a fresh temporary project. The factory migrates that test copy and prepares a real v4 request whose reserve exceeds 1,000,000. Tests never depend on a Root `.var` directory. No archive or stored source fixture was added.

## RED evidence

Before the product fix, the new portable `test_v4_public_request_over_one_cny_uses_explicit_one_and_half_budget` failed with `ValueError: Exact one-call qualification authority or budget differs` at `src/youtube_intel/distillation.py:4050`. The test had asserted the actual assembled reserve exceeded 1,000,000 before confirmation. Command was `PYTHONPATH=src python -m pytest -q tests/unit/test_synthesis_qualification_entry.py::test_v4_public_request_over_one_cny_uses_explicit_one_and_half_budget` using the approved Python executable below. Result was 1 failed in 2.72s.

A separate offline diagnostic cloned the retained actual prepared public AIRC project read-only into this worktree's `.var/qualification-budget/actual-airc-red`. It reconstructed the normal factory/API request and asserted **reserve 1,370,418**. The old method rejected the 1,500,000 budget with the same error, **zero fake credential reads, zero fake wire calls, zero target execution**, and exact local inventory equality. Frozen source inventory remained **87 tables / 19 DATA files**. Evidence is `.var/qualification-budget/red.json`.

## GREEN evidence

The actual prepared public input was independently cloned into `.var/qualification-budget/actual-airc-green-verified`. The normal factory/API again produced **reserve 1,370,418**. With an explicit 1,500,000 budget and synthetic credential/transport boundaries, the seam returned `SUCCEEDED_NO_NEW_INTELLIGENCE`, invocation count 1, fake wire count 1 and fake credential resolver count 2. Normal `can_confirm` and reviewed qualification remained false.

All 19 DATA files were equal. Exactly these five tables changed for the new execution: `distillation_execution_checkpoints`, `system_synthesis_input_proofs`, `system_synthesis_cloud_authorizations`, `system_synthesis_result_receipts`, and `distillation_no_new_intelligence_results`. `distillation_resource_usage` and every other SQL table were equal. The existing persisted-proof/database verifier passed. The original frozen source remained equal across every SQL table and DATA file. Evidence is `.var/qualification-budget/green-verified.json`. The diagnostic script is `.var/qualification-budget/replay.py`. These local diagnostics contain no real credential or model response.

Committed tests cover the 1.5M maximum, over-limit/insufficient/zero/missing budgets before key or reservation, old v1/v2/v3 requests rejecting 1M+1, strict boolean/float counter rejection, strict authority call count, unknown profile, changed current source, exact owner consent/receipt, complete non-target SQL and DATA integrity, duplicate rejection and one-call ambiguous outcome. Existing seam tests retain exact hash/expiry/max-calls checks. Existing v4 core/controller groups provide the remaining normal eligibility and controller coverage.

## 检查结果

Python is `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`.

- Stable focused group uses `PYTHONPATH=src python -m pytest -q tests/unit/test_synthesis_qualification_entry.py tests/unit/test_synthesis_readable_summary_v4.py tests/unit/test_bounded_synthesis_v4_trial.py`. **93 passed in 1,052.40s (17m32s)**. This single stabilized run completed the seam, v4 core and nested-history controller groups.
- Cold `PYTHONPATH=src MYPYPATH=src:. python -m mypy --strict --explicit-package-bases --cache-dir=/dev/null src` passed for 132 source files after the product fix.
- `python -m ruff check src/youtube_intel/distillation.py tests/unit/test_synthesis_qualification_entry.py`, `python -m compileall -q src` and `git diff --check` passed.

## 已解决验证问题

The first post-fix success assertion incorrectly expected both NO_NEW accounting and `distillation_resource_usage` to change. The existing `_observation` contract permits only one accounting outcome. A relevant group was started before that failed result was read, so the same test expectation appeared twice. That group was interrupted after 11 passes and one assertion failure. The exact mutation set was corrected to the five tables above, requiring `distillation_resource_usage` equality. The corrected success test passed in 3.27s before the stabilized group. The local diagnostic also had a phase-label assertion that was corrected before the final `green-verified` run. These changes affect validation expectations and local diagnostic bookkeeping only.

Graph discovery returned no indexed `confirm_synthesis_qualification` symbol. Scoped source reads followed. The single Jev routing advisory returned HTTP451, and work continued under the assigned default reasoning and Root review.

## Diff 复核与交接

The scoped diff contains `distillation.py`, the existing qualification-entry test file and this handoff. There are no changes to transport bytes, prices, qualification resources, Schema, dependencies, production settings, credentials, trial/controller code, fees or operational controls. Actual stopped history and the final-validation worktree at 469f11a remain Root-owned and frozen. All generation in this task used synthetic wire responses.

Suggested status is `IN_REVIEW`. Root owns the fixed-delta review, controlled restoration, final combined-source checks and any later continuation decision. Full backend and frontend suites were outside this task's assigned checks. No new fee approval is claimed.
