# TASK-READINESS-Q4KM-TEXT-DIAGNOSTIC independent review

- Reviewer: `/root/q4_text_preflight_review`; review worktree `readiness-model-diagnostic`, branch `codex/task-readiness-model-diagnostic`, base `c53644bd25cd0c80df2c469579ecb9139b63e692`.
- Reviewed implementer: `readiness-q4km-text-diagnostic`, branch `codex/task-readiness-q4km-text-diagnostic`, commit `fad36b05382f39a57bebaddd106b6d26044ac669`, base `a798d4dbc54ac7e38c0c65507a07e209c50689ff`.
- Verdict: **APPROVE_DIAGNOSTIC_ONLY_WITH_FRESH_RESOURCE_REQUIRED**. No unresolved P0/P1 finding in this diagnostic package. This is conditional diagnostic approval, not a current resource PASS, semantic acceptance, qualification, retry, later case, profile, product integration, or main authorization.

## Concrete binding

Package: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/qwen35-9b-text-q4km-20261025/diagnostic-freeze-q4km-text-v1.json`, SHA256 `3a107e0cb24c2549cfd098b332f18333c9b75b184019c92e987b8894ee062bfe`, 255541 bytes. Harness SHA256 `d510aef83346bf1706f69a14fc7e9e10148d2e0614591f6b333c24a28f91e1ef`, 26018 bytes; experiment `Q4KM_TEXT_NONTHINKING_0409_EN_V1`.

Independently verified every full SHA256, byte count, canonical path and final file identity for 993 binding entries (989 frozen inputs plus four top references, 990 unique paths). All old Q3 v2 335 frozen bindings remain exact. Both 605-entry source maps are equal and all 605 current hashes match; their serialized JSON hashes differ because key order differs, as already disclosed. Final identity checks include ctime as well as the harness's four-field identity. Evidence: own ignored `.var/q4km-text-preflight-review/{binding-verification,binding-hashes,binding-identities}.json`.

Original request `228c663ef083ba771f57bd388f9fc59078b5a081aa2f10ca13a3c60ab975b978` remains true-thinking official9B. Prior prepared Q3 false request `8677a347fc5577c7bf2f399406e11d393e6b330f4e5a099c474e19e78c7a9226` equals original with only model/think changes. Candidate `5ecc84f927518125ac4e6d3fce926824f089534c20e964b45a32425cf5aaccd8` changes only that prior model tag. Messages, schema, original 18-cue/two-Evidence source, exact timestamps/IDs, OPTIONS and semantic requirements remain fixed.

## Independent checks and review

| Check | Result |
|---|---|
| Four files compiled with `py_compile`, output redirected to own review evidence | PASS |
| Root existing Python, `PYTHONPATH` set to implementer `src`, `pytest -q -p no:cacheprovider` on all three private test files | **141 passed in 0.65s** |
| Existing Ruff, `check --no-cache` on harness, `test_mode_guards.py`, `test_quant_guards.py` | PASS |
| Actual IQ2 source SHA `4b82152a2db2a53ac1c9c4c639193241535321be8a1f58c0206db25256403bec` and four copied-original files | Exact match |
| Independently generated IQ2-to-Q4 delta | Scope/tag/store/reference/experiment and actual manifest/config/weight/quant constants only; original135+6 assertions preserved |
| Implementer tracked diff from base | New handoff only; no product change; clean worktree |
| Read-only process/listener/vmmap/mapped-file checks using reviewed guard methods | Bound daemon29391/start/argv/listener match; ARM64 main mapping valid, no x86 impl mapped; no runner, no Q4 generation marker |

Full commands/logs and independently generated delta are under own ignored `.var/q4km-text-preflight-review/`. Tests used no bytecode/cache writes to implementer source; no dependencies installed. Inherited compact `test_diagnostic.py` 106 E701/E702 lint findings remain disclosed; this is not a claim that every private test file is lint-clean. One reviewer audit comparison initially compared a five-field snapshot with the library's four-field tuple; unchanged original SHA/stat confirmed the audit-format mismatch. Corrected comparison checks both formats and passed; no product/harness change or weakened check resulted.

Reviewed guards remain intact: strict nine-field package and old-seven-field rejection; pinned0409 source and binary bindings; ARM64 daemon and runner main mappings and x86 exclusion; exact owner/start/argv/listener/runner parent/flags; actual four payloads; native false renderer with identical common prefix; fresh full native tokenization and actual slot; `N+8192+2<=16384`; lease, freshness, bounded HTTP/no redirects, deadline, once markers, normal complete response, no hidden thinking, and `production_qualified=False`. Actual N remains unknown; prior722 cannot be reused.

## Artifact, history and reuse

Actual manifest `cfc17e6f6530e659b95f467e069dbca236b75fdde37dec861b51e13fd15f2f4f`/794B, config `69de2371ea22c5b1053d3197f5c55e721109e1f3f0848d45608d6be992ed5bd8`/177B/Q4_K_M, exact reference link and four payloads match the recorded metadata. Text layer `02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d`/5629109120B is present in preserved official full manifest `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`; its separate 921704832B projector is absent from this text package. Four payloads total5629120653B plus unchanged2GiB =7776604301B. Original full-model gate is unchanged.

Additionally rehashed that one explicitly identified installed source blob read-only: full SHA matches, its five-field identity remains equal before/after and to root's original proof, and private clone inode differs. See own `installed-source-recheck.json`; no unrelated installed files or credentials read.

Preserved historical failure profile/request/raw/result/started/permit files were independently rehashed. Old request `7e5fceead2c2bf1c8be1f0ac20c9b68cc488c33aa4281adb2fbebd030883f9d6` has different messages and OPTIONS (0401,4096out/8192ctx versus current0409,8192out/16384ctx). Same weights and prior failures remain relevant; packaging does not reset quality. Existing bounded history inspection is not an exhaustive-history claim. IQ2/Q3 failed raw/markers/cleanup remain frozen and provide no Q4 semantic acceptance.

DIRECT reuse of reviewed internal IQ2 harness/tests and existing standard library/pytest/Ruff; fixed Ollama/llama.cpp source, binaries and license evidence retained. Official Qwen text payload's Apache2 license is in the four payloads. No new component, download, cloud call, dependency, lockfile or production authority.

## Execution boundary and remaining risk

At2026-10-25T08:37:03Z, read-only fresh observation was RAM6235586560B **below** required7776604301B; disk179716030464B exceeds10GiB. Old resource snapshots are not current PASS. Root must satisfy the unchanged fresh resource gate and all bound process/file/lease checks immediately before executing this exact package. If resources remain insufficient, zero load/generation and STOP; do not lower gates. Owner changes require rebinding and review.

Only after those gates pass: root may perform at most one empty load, measure the new actual native N/slot, and at most one original-English generation with8192out/16384ctx/300s. Preserve all raw/markers, then STOP for independent semantic review regardless of result. Any preflight or execution failure is preserved; this approval grants no rerun. Model quality and positive user chain remain unproved. Reviewer performed **zero HTTP calls, zero loads and zero generations**, and changed only this new handoff plus own ignored review evidence. No source, owner configuration, credentials, user data, Schema, task status, main or release changes.
