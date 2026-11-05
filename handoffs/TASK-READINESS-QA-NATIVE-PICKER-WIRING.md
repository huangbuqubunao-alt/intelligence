# TASK-READINESS-QA-NATIVE-PICKER-WIRING 交接报告

## 元数据与范围

- Role: Implementer `/root/qa_launch_isolation`, reported 2026-11-05.
- Base: `1259f81365eb955b21311cc007365f49e767c1c5` (accepted passive-admission and bounded-trial dependencies).
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-qa-native-picker-wiring`.
- Branch: `codex/readiness-qa-native-picker-wiring`.
- Commit: this scoped commit; exact SHA returned to Root after committing.
- Actual changes: `scripts/validation/serve_user_readiness_candidate.py`, `tests/unit/test_qa_launch_isolation.py`, this handoff only.
- Goal: the owned QA launcher uses the existing real macOS selector and native import service, including after restore restart. This does not change the formal owner launcher or the import engine.

## 原因与最小修复

Root's actual screenshot `.var/final-checks/gui-native-unavailable.png` was read visually: Following → Add local files showed the explicit unavailable warning and disabled chooser. The QA launcher omitted existing native wiring. The formal launcher already calls `prepare_native_picker()` from `scripts/owner_launcher.py` and the CLI enables native import; that existing formal path is unchanged.

The QA launcher validates API and frontend ports as integer 1024–65535 values, requiring distinct ports, before creating state, preparing helpers or constructing credential stores. New `--frontend-port` defaults to 6379; API default remains 6378. Only the paired exact origins `http://127.0.0.1:<frontend-port>` and `http://localhost:<frontend-port>` are enabled. No arbitrary origin, host or executable override is added.

Under the existing single-owner lock, the launcher calls `prepare_native_picker()` with the tracked checkout root, before credential construction and SQLite composition. This uses the existing installed Apple compiler and tracked `.m` source, writing only this checkout's `.var/native-picker`. Each normal or restore-restart composition calls its existing `enable_native_import()` before serving. The cleanup now also covers native enable, bind and worker-start failure; successful rounds retain native shutdown, worker stop, signal-handler restoration and the owner lock across restart. Missing macOS/compiler/build tools refuse startup with exit 2 and an explicit native-tools startup message, rather than claiming available capability.

Cloud execution stays false, environment fallback false, fixed QA Keychain namespaces unchanged, owned path/link checks unchanged. Tests use fake credential stores/frameworks and fake helper preparation. No actual keys, model calls, fees, external network, formal data/configuration or deployment were used.

Reuse decision: **DIRECT** existing `native_picker_build.prepare_native_picker`, `LocalApiApplication.enable_native_import`, existing native service/worker/Backup lifecycle, and stdlib port validation/subprocess errors. No new engine, provider, browser upload fallback, dependency, schema or copied third-party code.

For Root's 6478/6479 GUI pair:

```sh
PYTHONPATH=src "$PYTHON" scripts/validation/serve_user_readiness_candidate.py --port 6478 --frontend-port 6479
```

## 实际验证

Evidence directory: own ignored `.var/qa-native-picker-wiring/`.

| Check | Actual result | Evidence |
|---|---|---|
| New deterministic checks against original launcher | expected RED: 7 failed, 15 deselected, 1.09s | `initial-red.log`; missing frontend-port/native hookup/failed-start cleanup |
| Complete existing launcher test file, enhanced assertions retained | PASS: 22 passed, 2.95s | `launcher-full.log` |
| Strict mypy all src plus launcher | PASS: 132 source files | `strict-final.log` |
| Ruff launcher and test | PASS | `ruff-final.log` |
| compileall launcher and test | PASS | exit 0 |
| Real installed-tool native helper compilation in owned worktree | PASS, executable exists; chooser NOT opened | `native-build.log` |
| `git diff --check` | PASS | exit 0 |

The 22-test file proves fixed QA namespaces, disabled fee gate/direct API and service refusal, environment isolation, symlink/hardlink refusal, both invalid ports rejected before helper/credentials/DB, exact default and custom frontend origins, one owner across two restore rounds, native enable/shutdown each round, failed enable/bind/start cleanup, and a real loopback HTTP composition with fake stores returning native capability true. It never invokes the native chooser or a model.

Commands (Python: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`):

```sh
PYTHONPATH=src "$PYTHON" -m pytest tests/unit/test_qa_launch_isolation.py -q
MYPYPATH=src PYTHONPATH=src "$PYTHON" -m mypy --strict src scripts/validation/serve_user_readiness_candidate.py
"$PYTHON" -m ruff check scripts/validation/serve_user_readiness_candidate.py tests/unit/test_qa_launch_isolation.py
"$PYTHON" -m compileall -q scripts/validation/serve_user_readiness_candidate.py tests/unit/test_qa_launch_isolation.py
git diff --check
```

Actual compiled executable SHA256: `a79d2fc4e169717bf7b697c8679472801c5b9b67e661272d7807531ba529ba0f`; source SHA256: `d06b77d6092c7a3ffeaac750bfd912c5e11ab5adb90ff88b4d8be331bfd1416b`. The real helper build called the existing installed compiler/registration only, not the picker executable.

## D2-02 复用边界

All four relevant implementation files were SHA256-compared to adopted `73ee7e747b4461b9de8a201d6b47669eb3913d1a`, whose report records unchanged 2 GiB APFS receipts. All four are byte-identical; full comparison is `d2-source-comparison.json`:

| File under `src/youtube_intel/` | Current and adopted SHA256 |
|---|---|
| `native_import.py` | `949b51a8d255d8c10e641ee59ed3465b4a247ab21f87e17724f5adf2e65e048b` |
| `local_content.py` | `136195242ab8c2e9240e7e4f8ac63d2de21b7564b8f8fa71e0d2edc1b98ab85b` |
| `native_picker.m` | `d06b77d6092c7a3ffeaac750bfd912c5e11ab5adb90ff88b4d8be331bfd1416b` |
| `native_picker_build.py` | `e5c93bb8aa86f3ecf4cbfe580fd0267825f613bc759140fc82d45d337e178859` |

This establishes the implementation condition for Root's permitted old APFS evidence reuse. It is not a new 2 GiB import or GUI acceptance claim.

## Diff 复核、限制与交接

- Only assigned launcher/test/handoff changed. No product source, frontend, generated files, schema, toolchain, lockfiles, credentials or model/fee qualification change. Existing tests were extended for required native setup; no assertions were skipped or weakened.
- Root's positive headed macOS chooser → overlong rejection → text import → route notice cleanup → Content deep link/retry/cancel → Backup acceptance is **NOT RUN by this task**. Root will run it once on the integrated candidate. No live 6478/final worktree interaction occurred here.
- Full global backend/frontend are not repeated for this launcher seam; full assigned test file and static checks pass. Earlier RED evidence remains.
- `DECISION NEEDED`: none. Suggested state: `IN_REVIEW`. Fixed commit, clean worktree, STOP; no merge, push, deployment or new task.
- Reviewer verdict and integration remain Root's responsibility; no implementer self-approval claimed.
