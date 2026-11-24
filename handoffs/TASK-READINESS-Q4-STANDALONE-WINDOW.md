# TASK-READINESS-Q4-STANDALONE-WINDOW QA handoff

- Implementer: `/root/q4_text_preflight_review`, formerly reviewer in a different worktree; this implementation is confined to NEW `readiness-q4-standalone-window`, branch `codex/task-readiness-q4-standalone-window`, base `a77d5ba`.
- Suggested status: `IN_REVIEW`. This is offline QA/controller preparation only; independent concrete-package review and root's Terminal launch remain required. Goal/user chain is not complete and no model qualification or main authority is granted.

Implemented only own ignored `.var/q4-standalone-window/{controller.py,tests/test_controller.py,Start-Q4-Diagnostic.command.template,README.md,checks/*}` and this new handoff. No existing QA file, product source, test, config, dependency, lockfile, Schema, credential, formal data, main or task-status edit. No real model HTTP, load, generation, app closure or Terminal open. The real launch marker/controller output/child output remain absent.

## Fixed behavior

Controller reserves own global `launch-start.json` exclusively before validation/wait; duplicate windows cannot run a child or enter cleanup. Own output is exactly `.var/q4-standalone-window/run-20261025`. It observes only current-user `comm` executable paths for `/Applications/ChatGPT.app/Contents/MacOS/ChatGPT` and `/Applications/Codex.app/Contents/MacOS/Codex`, without logging process arguments or closing any app. Read-only actual `ps` observation confirmed the current ChatGPT main executable is detectable. Jimmm is never targeted.

Wait deadline1800seconds, poll5seconds; both main apps absent AND original RAM7776604301B/disk10GiB must pass. Unknown observations stop. Full package/owner validation and app/resource observations repeat immediately before the sole child launch. The controller checks the supplied concrete SHA, exact nine-field Q4 kind/case/experiment/harness identity, rejects the old resource-denied package SHA, and delegates full request/file/owner/native/capacity/lease/once validation to the unchanged reviewed Q4 harness. It requires a cold exact owner and absent prior real child output/generation marker.

Child command is fixed root Python + unchanged Q4 harness with `--package <root-new-concrete-path> --package-sha256 <root-new-full-SHA> --output /Users/developer/Documents/yia-worktrees/readiness-q4km-text-diagnostic/.var/model-diagnostic-q4km-text/real-once-terminal-window-20261025 --execute`; fixed `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-q4km-text-diagnostic/src`, no bytecode writes. No extra input, model change, sampling change, retry or alternate output. Child deadline720seconds, raw stdout/stderr retained; interruption/timeout uses normal terminate of that Popen child only, never force or a group. No retry if it fails or remains unknown.

Cleanup reuses exact `h.daemon`, frozen identities, `h.observe`, `h.native_runner_request('/slots')` and main-mapping/parent/runner guards. It sends only SIGTERM to the revalidated exact owner PID; no app close, other PID or process-group signal. Slots are retained and IDLE/PROCESSING/UNKNOWN distinguished. Any uncertain identity refuses signalling and records UNKNOWN. Cleanup has a30second absolute bound and checks daemon/runner absence plus closed port after a normal stop. Unknown cleanup or child state stays unqualified; another control session may need to inspect it after Codex reopens. All final outcomes are `DIAGNOSTIC_ONLY`, `qualification=false`, `AWAITING_REVIEW`; completion asks the user to reopen Codex for independent semantic review.

The `.command.template` intentionally refuses placeholders with exit64. Root must supply new concrete package path/hash and controller hash after independent review, generate the actual launcher, use LaunchServices/Terminal and verify its independent ancestry/waiting state while Codex is open. Implementer did not generate an owner/package, launch the real controller or instruct an actual Codex quit. Existing old package/precheck/error/raw/markers are preserved.

## Verification and reuse

DIRECT reuse of exact internal Q4 harness `d510aef83346bf1706f69a14fc7e9e10148d2e0614591f6b333c24a28f91e1ef` and its141 tests, existing stdlib/pytest/Ruff and original capacity observation. No new HTTP implementation, model dependency or license input. Existing frozen Ollama/llama.cpp/Qwen license/source evidence remains with the unchanged harness/model; this private orchestration code adds no third-party component.

| Check | Actual result |
|---|---|
| Meaningful RED→GREEN, injected process/clock/transport boundaries | Initial18 expected failures→18PASS; added post-validation unknown-observation regressions2FAIL/21PASS→23PASS; full RED logs retained |
| Final new23 + unchanged original141 | **164 passed in0.64s**, no skips/removed assertions |
| Syntax | Six controller/test/harness files compiled to own checks; PASS |
| Scoped Ruff | New controller/tests + unchanged harness/mode/quant tests PASS |
| `.command` syntax and actual placeholder refusal under zsh | PASS, refusal exit64; no Terminal opened |
| Source freeze | All591 own tracked-source/Q4-private-input hashes equal before/after; all605 original Q4 source hashes independently rechecked unchanged |
| Git diff/scope | No business diff; only this new tracked handoff; private artifacts ignored |

Tests cover open-app despite enough RAM, closed-app insufficient RAM/disk, exact one unchanged child, concurrent duplicate window refusing child/cleanup, validation/child failures and timeouts without retry, unknown first/second observations, package/harness/owner mismatch, fixed argv/env/raw logs, unknown-owner refusal, exact-owner SIGTERM and native IDLE/PROCESSING/UNKNOWN. No model/network/app boundary was exercised for real. Existing compact `test_diagnostic.py`106 E701/E702 remain inherited/disclosed, excluded from scoped lint; no claim of all-private-QA lint cleanliness. No full-product regression repeated because business code is unchanged; prior6003/1026 product evidence is not reclassified by this QA wrapper.

Full commands/env and all logs are in own `checks/commands.json`, `red.log`, `green-r1.log`, `red-post-validation.log`, `green-r2.log`, `offline-final.log`, `compile-final.log`, `ruff-final.log`, `template-refusal.json`, `source-{before,after}.json`, `verification-summary.json`, and complete SHA/byte bindings in `artifact-bindings.json`.

| Artifact | Full SHA256 | Bytes |
|---|---|---|
| controller.py | `761c603af96a85d0d24edeb2fcdf708bc1c43bfa921dba284b12a66ca739dc8d` | 12205 |
| tests/test_controller.py | `edd3ae785fb13c62a01e97b00eaf5462c278b83d10ff2231605a0491a20f9946` | 9692 |
| Start-Q4-Diagnostic.command.template | `8a6b3540667d8d716407aeff06238eb5a1c3dda94c846b3d891e05b80852dc42` | 1119 |
| README.md | `cc76276b593b848349180f27cb03b2fae4a592272de27b3d4367366d62828b92` | 2365 |

STOP after handoff-only commit. Root supplies new reviewed owner/package/launcher and independent Reviewer; no self-approval. Resource sufficiency after a manual app exit and actual model quality remain unknown. No automated retry or lower gate is authorized by this handoff.
