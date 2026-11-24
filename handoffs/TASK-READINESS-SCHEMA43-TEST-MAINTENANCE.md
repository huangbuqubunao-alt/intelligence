# TASK-READINESS-SCHEMA43-TEST-MAINTENANCE — Implementer

- Date2026-10-29; sole Implementer `/root/cloud_preview_writer`; base `78d727aadb1a2283e0225efd622327320b5c5756`.
- WT `/Users/developer/Documents/yia-worktrees/readiness-schema43-test-maintenance`; branch `codex/task-readiness-schema43-test-maintenance`.
- Task/prompt read directly from Root's absolute `tasks/` and `agent-prompts/` paths, as assigned; they are intentionally not cherry-picked into this WT. Standing authorization covers these exact test-only corrections. No main integration.
- DIRECT reuse of existing tests/fixtures/explicit assertions; no new framework, dependency or product behavior.

## Scope and audit

The original frozen full-backend diagnostic is **349 PASS /15 FAIL /302.09s, interrupted** after repeated43==42 failures. It is not a full pass. Root's original `pytest.log` and `first-run-interrupted-proof.json` are preserved at `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/full-backend-20261029/`. This task does not overwrite either.

Reviewed all tests'42/43 literals and their enclosing AST/function purpose. Changed30 necessary test files:

-65 current-version assertions now require exact43; two current packaged migration metadata assertions name `043_add_cloud_wait_zero_cancellation.sql`.
- Four exact current-history checks retain every earlier migration entry and append only43. Three suffix lengths27→28 preserve the same starting015 entry. The historical042 row remains42.
- Only the two explicit unknown-future/doctor tests use fictional44 instead of the now-supported43; the doctor test's name/current restored value now say43. Older1/40 failure cases remain unchanged. The fabricated future row is deleted as44, preserving the real43 history.
- No current table count required changing. The existing `migration_count == 42` is correct because029 is absent and remains unchanged. Old34–42 archives, raw42 tracked stock,42 rollback targets/checksum corruption guards, all row/DATA comparisons, immutable/source/auth/payment/privacy assertions are preserved. No >=, tautological latest-version lookup, assertion deletion, skip or coverage reduction.

An AST audit across all30 changed files proves **1850 assertions preserved in count,1779 unchanged assertions identical**,65 current-version,2 current-metadata and4 history-prefix assertion changes only. At this test-maintenance stage all non-assert code was AST identical except the expressly authorized future SQL literals and doctor name. No existing fixture/setup/validator implementation was changed in that stage. The separately authorized doctor repair below adds one legacy-version assertion and a local offline provider stub.

## Verification

All Python uses `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, explicit `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-schema43-test-maintenance/src`. Own temp SQLite/DATA only; no actual case/model/key/native/network/liveQA access.

- Changed test files compile in memory; Ruff PASS (`.var/schema43-test-maintenance/ruff.log`); `git diff --check` PASS.
- Before the doctor repair, the protected-byte check directly hashed working bytes with Git blob headers against base objects: **341 source/script/frontend/config/dependency files, including all42 SQL files001–043, exactly equal**. Manifest digest `8d79281236761290b3bfad7261b3c948866bdbc5cedb246da218d850ede83b76`; evidence `.var/schema43-test-maintenance/production-byte-proof.json`.
- `.var/schema43-test-maintenance/assertion-inventory.json`, `edited-assertions.json`, `assertion-proof.json` and `preserved42.json` record discovery and exact classification. Evidence is ignored local QA material, not new production/test fixture data.
- Full affected group is30 changed files plus the two original cascading caller files `tests/integration/test_dogfood_day1_intelligence.py` and `tests/integration/test_final_capability_presentation.py` (**32 complete files**), listed in `.var/schema43-test-maintenance/affected-files.txt`. No full6000, former629 group or frontend rerun.

Reproduce the precise group from this maintenance commit (use the environment above):

```sh
python -m pytest $(git diff --name-only 78d727aadb1a2283e0225efd622327320b5c5756 HEAD -- tests) \
  tests/integration/test_dogfood_day1_intelligence.py \
  tests/integration/test_final_capability_presentation.py -q
```

The complete32-file run finished **898 PASS /1 FAIL /859.43s**, `affected.log`. The only failure is the correctly updated fresh43 doctor expectation; the production health checker still required42. A precise single-case reproduction is preserved in `doctor-failure.log`. This is an actual product defect, not a reason to weaken the test.

## Authorized single-function doctor repair

After the32-file run had completed and its actual FAIL was preserved, Root explicitly extended this same task to the minimal necessary product correction. `src/youtube_intel/runtime.py::_database_check` changes only `version != 42` to **`version != 43`**. Its read-only URI, integrity check, exceptions/messages, and every other runtime byte remain unchanged. There is no already-imported database latest constant; the existing SCHEMA_VERSION is a scoring contract, so no unrelated import/cycle or version-system refactor was introduced.

The existing doctor test explicitly verifies fresh43 PASS, old1/42/40 FAIL, unknown future44 FAIL and restored43 PASS. Its additional42 rejection assertion strengthens strict current-version acceptance. For complete runtime-composition testing under the task's zero-network rule, the existing missing-first-run doctor test now locally replaces only `urlopen` with a controlled URLError: it also asserts the attempted operation is GET `/api/tags`, while preserving all original no-directory/no-log/no-Vault/missing-SQLite assertions. No owner's Ollama tags or model/credential endpoint is contacted.

Only the two complete doctor-related files were rerun after this repair:

```text
tests/integration/test_runtime_composition.py
tests/integration/test_task016c_phase_h2c_lineage_schema.py
```

**47 PASS /48.24s**, `doctor-affected.log`; no repeat of the32-file group. This includes the original failure regression. Strict mypy on runtime.py PASS (`doctor-type.log`); changed source/tests compile and Ruff PASS; final diff-check clean. Added assertions total3 (legacy42 rejection, offline GET/method checks); no original assertion was removed. Across the final31 changed test files the count is2073 original→2076 final.

Final protection (`doctor-final-proof.json`): **340 other protected files byte identical**; runtime.py outside `_database_check` byte identical; the function differs in exactly the authorized42→43 constant; all42 old SQL files unchanged. The earlier341-file proof is explicitly pre-repair evidence, not a claim that runtime.py remained unmodified.

## Boundaries / disposition

The sole src edit is the explicitly authorized doctor constant above. No migration/scripts/config/dependency/toolchain/old fixture/oracle/actual model package edits. No model qualification, semantic review, account/billing claim, real request, credential read or main action. The Chinese actual-case review is Root's separate work and was not read here. Root independently reviews the precise expectation maintenance, single doctor function delta and actual logs; no separate whole-code review requested. No remaining failure from this task is known; source/runtime health is fixed without weakening strict version refusal. Suggested status IN_REVIEW, clean STOP after the commit containing this handoff. The full Goal backend run remains Root's later integration check; this report never promotes the interrupted349/15 run to a full pass.
