# TASK-READINESS-TRIAL-DEVICE-CONTINUITY

## Metadata

- Role: Implementer, sole writer `/root/v4_r2_finish`.
- Base: `320e4b821e1568fcbf47f9bc86ac29606ea838a4`.
- Branch: `codex/readiness-trial-device-continuity`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-trial-device-continuity`.
- Date: 2026-11-07.
- Root owns independent review, acceptance, integration, actual preparation and fee decisions.
- Reuse: DIRECT existing finite r2 controller, normal factory/proof reconstruction, immutable holds, ancestry verification and ordered locks; repository-owned code and Python standard library under the existing repository license/NOTICE. No new dependency or external adaptation.

## Goal and scope

Recover verification of the immutable historical parent after APFS changed device16777231 to16777232, preserving every historical source binding, grant, anchor, witness and result. This metadata view confers no new fee authorization or qualification.

Allowed and actual changes are the validation controller, new portable continuity tests, this handoff, and the explicitly authorized one-line `device_continuity=None` override in the existing r2 owned synthetic fixture. The two materializers, product/backend/frontend code, existing assertions, Schema, dependencies, lockfile and configuration are unchanged. Prior worktrees and all operational state are preserved.

## Implementation and review

`HistoricalMetadata` is an immutable tuple containing only a fixed witness path and immutable bytes. The production finite r2 specification fixes Root's witness path/SHA, transition31→32 and decision identity. No new CLI override or general migration path exists. The helper first validates the exact current physical identities for every pinned file and control directory, before interpreting anchors. It checks SHA/bytes/inode/device/owner/mode/nlink/mtime, exact control contents, original anchor inode/device and supporting report hashes. The witness itself and supporting reports remain on the current device and cannot be projected through this context.

The context is passed explicitly from `stopped_preclaim_parent` into historical `package_binding`, `parent_binding` and stopped-v2/v3 ancestry comparisons. Every historical device lookup rechecks the named current pin before returning its historical value; unlisted paths are refused. DefaultNone leaves older entrypoints using their physical identities and preserves their failure on an unapproved transition. No `Path`, `os`, SQLite API or process-global metadata source is replaced.

The original34→31 location witness remains exact, as do saved legacy binding hashes and frozen469/6fe/7203 source inventories. The r1 outer anchor is compared in its historical31 frame. The new r2 parent separately carries actual current32 file/control identities and the new continuity witness SHA/identity. Complete continuity validation is repeated at the beginning and end of each parent verification and at existing key/claim/wire boundaries through the original grant and lock checks. New r2 anchors continue to record their actual physical device.

Root witness: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/fee-device-continuity-20261107.json`, SHA `0a1744f92194421d2ba36adda89fad02fd4325f84f47558a1a6cff3cb2217e85`, private0600,109 file records and4 control directories. Fresh r1 per-file inode pins are Root's current observations; they are not described as a pre-restart audit. The old94-file snapshot and comparison support the witness but are not independent permission. Original witness `041db3e008b5a5f97f3640cbbb715f2b17dd832a2e8c4cafe8e36ff85e88a84b` remains unchanged.

## Verification evidence

Approved Python: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`. Logs are retained under this worktree's `.var/device-continuity-checks/`.

| Check | Result / evidence |
|---|---|
| Cold strict: `PYTHONPATH=src MYPYPATH=src:. python -m mypy --strict --explicit-package-bases --cache-dir=/dev/null src scripts/validation/bounded_synthesis_trial.py scripts/validation/materialize_synthesis_inputs.py scripts/validation/materialize_synthesis_v2_inputs.py` | PASS,135 source files; `cold-final-fixed.log` |
| Ruff on controller, new continuity test and existing r2 owned test | PASS |
| Compilation of3 scoped Python files and finite CLI `--help` | PASS; `cli.log` |
| Protected materializers/product/frontend/dependency/configuration comparison against320 | Identical |
| Initial actual readonly parent verification with109-file/4-directory metadata snapshots before/after | PASS; `actual-readonly-preflight.log` |
| Final fixed-source focused group:23 new cases and4 directly affected existing cases | PASS,27 tests in668.92s; `focused-final-fixed.log` |
| Final fixed-source actual readonly preflight: all109 pinned files,4 control directories, new witness and supporting report metadata before/after | PASS, all identities equal, currentouter32/historicalnested31; `actual-readonly-preflight-final.log` |
| Five scoped source/test/materializer SHA256 values across the final test run | Unchanged; `stable-source-sha256.txt` |

Focused command, from this worktree using the approved Python and `PYTHONPATH=src`:

```text
python -m pytest -q
  tests/unit/test_bounded_trial_device_continuity.py
  tests/unit/test_bounded_synthesis_v4_r2_trial.py::test_old_preclaim_slot_is_not_an_invocation_or_new_consent
  tests/unit/test_bounded_synthesis_v4_r2_trial.py::test_actual_public_request_above_one_cny_reaches_normal_claim_and_fake_wire
  tests/unit/test_bounded_synthesis_v2_trial.py::test_location_only_proof_preserves_original_history_and_requires_child_fee_grant
  tests/unit/test_bounded_synthesis_v2_trial.py::test_location_proof_cannot_accept_another_device_transition
```

Portable tests use only owned synthetic history and an explicit module-local physical-identity boundary. Unit tests model31→32 exactly; the full owned history test uses its actual synthetic initial device and the next simulated device, keeping all real file bytes and inodes unchanged. No global filesystem/stat API is patched. Tests cover immutable/unlisted context, all pinned identity fields, missing/wrong/changed witness, control extras, anchor and supporting report corruption, current witness device, byte-exact nested history, separate current binding, unchanged fee-slot accounting, new grant/semantic requirements, old no-context refusal and drift before claim/after key with zero wire calls. The focused existing tests cover the one owned-fixture override, normal >1M v4 entry and the original finite location-witness behavior.

## Preserved failures and interrupted evidence

`helper-initial.log`:16 passed,1 failed. A corrupt owned anchor was interpreted before its file pin was checked, raising `KeyError: 'control_device'` at the continuity control check. All pinned file validation was moved ahead of control-anchor interpretation; the test assertion was retained. `helper-fixed.log`:17 passed in0.79s. This order also ensures that changed files fail on their pinned identity before JSON interpretation.

The first focused group was deliberately interrupted during fixture setup after17 unit tests when final source review identified the missing explicit current-device check for the continuity witness itself. `focused-before-witness-device-check-interrupted.log` is preserved and is not a complete pass. The explicit check and its new regression test were added before starting the final fixed-source focused group.

No completed75 compatibility group or full36 r2 suite was repeated. The prior320 complete dedicated run remains35PASS/1FAIL, followed by the corrected targeted1PASS; it is not relabeled as complete36PASS. Root owns the single complete backend run after final combined source freeze.

## Boundaries and remaining review

No actual key, network/model invocation, fee operation, control/package/grant/witness creation or modification was performed. All operational109-file metadata and control identities are checked read-only. Seven fee slots still hold7238380microCNY, representing six known real invocations and one preclaim stop. Original r1 remains stopped; future9 slots/16M cap remain unapproved and model qualification remains closed.

Final diff review contains only the four allowed files, with no unrelated change, generated artifact, removed assertion or weakened test. No implementation blocker remains; recommend `IN_REVIEW`. Root's independent review and complete backend run remain pending. Worker does not merge, approve operational fees or set the public task DONE. Final commit SHA and clean-stop confirmation are reported after commit creation.
