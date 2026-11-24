# TASK-READINESS-Q4-STANDALONE-WINDOW independent review

Verdict: **APPROVE_DIAGNOSTIC_WINDOW_ONLY**. No unresolved P0/P1/P2 findings in this bounded controller/package review. This is not model qualification, product acceptance, permission for retries, or main/merge authority.

## Identity and scope

- Reviewer: `/root/q4_window_independent_review`, independent of implementer; no delegated agents.
- Review worktree: `/Users/developer/Documents/yia-worktrees/readiness-model-diagnostic`; base `7624b52f758506c3b39f4990374adf895d1fed41`.
- Implementer: `/Users/developer/Documents/yia-worktrees/readiness-q4-standalone-window`, clean HEAD `64065313dcd8e83dd2e40352188f60ae208669fa`; its commit adds only its new handoff. Private implementation artifacts reviewed directly by full SHA/bytes.
- Read root AGENTS, collaboration, status, PRD, system design, reuse register, task and matching prompt; applied code-review-and-quality/Git workflow skills. Graph lookup returned unindexed private QA worktree, so read assigned files directly. No Jev tool available; safe default review retained.
- Reviewer writes only this new handoff and own ignored `.var/q4-standalone-window-review/`. No existing/bound files modified, no task status changes.

## Fixed artifacts reviewed

| Artifact | SHA256 | Bytes |
|---|---|---|
| New concrete package `end-to-end-user-readiness/.var/end-to-end-user-readiness/qwen35-9b-text-q4km-20261025/diagnostic-freeze-q4km-text-terminal-v2.json` | `4c324a55fae37bac56f54c778e75be9b4492f0d1cf97080a9d6cd5a79dd99a92` | 407911 |
| Controller `.var/q4-standalone-window/controller.py` | `761c603af96a85d0d24edeb2fcdf708bc1c43bfa921dba284b12a66ca739dc8d` | 12205 |
| Controller tests | `edd3ae785fb13c62a01e97b00eaf5462c278b83d10ff2231605a0491a20f9946` | 9692 |
| Command template | `8a6b3540667d8d716407aeff06238eb5a1c3dda94c846b3d891e05b80852dc42` | 1119 |
| README | `cc76276b593b848349180f27cb03b2fae4a592272de27b3d4367366d62828b92` | 2365 |
| Unchanged Q4 harness | `d510aef83346bf1706f69a14fc7e9e10148d2e0614591f6b333c24a28f91e1ef` | 26018 |
| New Terminal daemon-owner JSON | `29de94e843e129b9699c3c8b4f8840608dcddbf98edaea63a4023aeb698dcd62` | 343 |

All 1610 unique concrete bindings passed independent complete SHA256, size, absolute canonical-path and before/after file-identity verification. All 990 unique prior-package bindings remain exactly present, including old owner/evidence. Only top-level `daemon_owner` and `frozen_inputs` changed; original/candidate/prior requests, case, experiment and harness identity are unchanged. Author 591 and original Q4 605 source hashes independently matched before and after checks. All author artifact bindings matched. Final stat identities of all 1610 still matched after supplemental review. The first assembly's pytest-fixture symlink refusal is preserved; excluding ephemeral fixture outputs changed no executable-input canonical-path guard or assertion.

DIRECT reuse: unchanged internal Q4 harness/141 guards, original capacity observation, existing standard library/pytest/Ruff. No dependency, third-party code or license change. `h.package()` and `h.artifacts()` independently passed as read-only validation; no harness execution or HTTP. Four text payloads total **5629120653 B**; original +2GiB gate remains **7776604301 B**, disk **10GiB**. Manifest `cfc17e6f6530e659b95f467e069dbca236b75fdde37dec861b51e13fd15f2f4f`/794 B and config `69de2371ea22c5b1053d3197f5c55e721109e1f3f0848d45608d6be992ed5bd8`/177 B passed. Original official manifest `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`/1088 B retained. Original installed 5629109120 B text weight was separately fully hashed to `02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d`, with its original frozen inode/timestamps unchanged. Removing unused projector from this text package does not alter the old full-model gate or reset quality history.

## Independent checks and findings

| Check | Result |
|---|---|
| Six Python files compiled to own evidence outputs | PASS; no bound bytecode overwritten |
| New 23 tests + unchanged Q4 141, root venv Python, fixed Q4 `PYTHONPATH`, no bytecode/cache and own basetemp | **164 passed in 0.72s**, no skips |
| Scoped Ruff from author's exact command list | PASS; inherited compact `test_diagnostic.py` 106 E701/E702 remain disclosed and excluded |
| zsh template syntax; actual placeholder refusal | PASS; refusal exit 64, no controller launch |
| Additional independently injected SIGINT/SIGTERM/SIGHUP while waiting | 3 PASS: zero child, one fake cleanup, marker retained, false qualification; no real signals |
| Full package/file hashes, original source weight, frozen reference and payloads | PASS |
| Root product paths `src/tests/frontend/scripts/config` versus `a2076db` | Empty diff; no new full product run required |
| Implementer commit scope/status | Handoff only, clean |

Commands/env and full logs are in reviewer evidence `checks.json`, `pytest.log`, `ruff.log`, `template_syntax.log`, `template_refusal.log`; reproducible read-only validation scripts and all result JSON are retained there. Author RED evidence was retained and bound; this reviewer reran GREEN checks independently rather than relying on its output.

Static and injected review confirms: fixed interpreter/harness/path/hash/scope; exclusive launch marker precedes waiting; duplicate cannot validate/run/cleanup the first launch; exact current-user main-app path observation; unknown app/resource readings fail closed; both gates repeated after full source/owner validation; at most one unchanged child, bounded wait/child deadlines and no retry. Raw child stdout/stderr preserved. Cancellation terminates only its Popen child normally and cleanup signals only the revalidated exact private daemon with SIGTERM; no force, groups, app-close calls or unrelated processes. Changed/unknown owner refuses signalling; native IDLE/PROCESSING/UNKNOWN and uncertain exit remain explicit. All outcomes remain DIAGNOSTIC_ONLY/qualification=false/AWAITING_REVIEW. Existing native ARM64/main/PID/start/argv/listener/runner-parent/flags, new native N/slot/context, lease, global once and original 300-second generation checks remain unchanged; no x86 mapping requirement was introduced.

Read-only `h.daemon()` independently confirmed owner **36223**, start **Sun Oct 25 17:27:46 2026**, exact pinned runtime argv, ARM64 mapped binary and isolated listener. No runner exists. Recorded metadata is 0.40.9, one exact Q4 tag and empty model `/ps`. Recorded Python→zsh→login→Terminal ancestry is coherent, contains no Codex/ChatGPT ancestor, and Terminal 36172 still has the recorded executable. No reviewer HTTP was made. Main protected app is currently open. Observed RAM **6210633728 B < 7776604301 B**; this is not a resource PASS and says nothing about resources after a manual exit. Actual new native N remains unobserved.

The old resource-denied output still contains only precheck/error, and the new launch/output/global-generation markers are absent. Historical 0401/different request and actual IQ2/Q3 quality failures remain bound; no quality verdict is reset. No real controller launch, model HTTP/load/generation, real signal, app closure, Terminal opening, formal data/config/credentials/Schema/dependency/launchd change occurred in this review. Prior full product 6003/1026 evidence is neither rerun nor reclassified.

## Conditions before root may start this one window

1. Root may mechanically substitute only the reviewed concrete package absolute path, package SHA and controller SHA into the reviewed template, creating a NEW actual `.command`. Preserve all existing artifacts/markers. Recheck zsh syntax, full launcher/controller/package hashes and canonical paths; any changed executable input needs review again.
2. Root opens that launcher normally in external Terminal, verifies actual controller ancestry includes Terminal and excludes Codex/ChatGPT, and confirms waiting/zero-child state while Codex is still open. No automated closure of Codex/ChatGPT/Jimmm is allowed. Only after that evidence may the user be told to manually quit Codex/ChatGPT; Jimmm stays open.
3. Model execution remains conditional on actual main-app absence and fresh original RAM/disk gates, exact owner/source revalidation and all unchanged child guards, including actual native N. One outcome then STOP; no retry, lower thresholds, output repair, parameter/prompt change, qualification or product test authority.
4. Reopen Codex for independent raw semantic and cleanup review afterwards. RAM after manual exit, actual app-quit survival, one real diagnostic, its native capacity/quality, and complete positive user chain remain **untested/unproven** in this phase. Cleanup UNKNOWN requires inspection; it does not authorize force or retry.

## Evidence seal and stop

Own evidence root: `/Users/developer/Documents/yia-worktrees/readiness-model-diagnostic/.var/q4-standalone-window-review/`.

- `summary.json`: SHA256 `0b672c8661bbd49a65a22ab2dbc25108d24ba0e08f5783b17c2b205f59735227` (3441 B).
- `verified-bindings.json`: SHA256 `23e47c11730dc375ef6576cabb0e455f1e69455a00c853fb20d273123adcef62` (589124 B).
- `final-proof.json`: SHA256 `c640ff751f77e624960e5843f3e5a5797add375663e47ad007010d0115f0da74` (363 B).
- Other own report hashes/bytes are in new `evidence-bindings.json`.

No product fix was needed; only this new review handoff is committed. Stop after clean handoff-only commit; root owns acceptance/launch decisions. No merge.
