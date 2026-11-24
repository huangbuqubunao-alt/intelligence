# TASK-READINESS-LOCAL-FIXED-RUNTIME — Independent Review

## Verdict and identity

**APPROVE** for the bounded R14 engineering slice. P0: none; P1: none; P2: none. No unresolved implementation finding. This is not model qualification, root acceptance, main integration, release, or completion of the ordinary-user readiness Goal.

- Reviewer: `/root/local_fixed_review`, independent conversation/worktree.
- Base: `b3410a489f06d17ea8c62d2f27d637d3bbe25cc2`.
- Complete reviewed candidate: `900332030fb12409a22d0a53c1dd63a97e715f03`.
- Product/test core: `e021fb5646acfa09caef0819eab52610fa964524`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-local-fixed-runtime-review`.
- Branch: `codex/review-readiness-local-fixed-runtime`.
- Report UTC: `2026-10-20T16:50:32.501226+00:00` (Asia/Shanghai +08:00).
- Only review output tracked: this handoff. No product, test, public task/status, or author-worktree writes.
- Existing root `.venv` symlink reused; no installation or dependency change.

## Authority and scope

Read repository AGENTS, COLLABORATION, PRD, SYSTEM_DESIGN, REUSE_REGISTER and current root PROJECT_STATUS, plus the newer authoritative task/package at `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/tasks/TASK-READINESS-LOCAL-FIXED-RUNTIME-PROFILE.md` and `agent-prompts/TASK-READINESS-LOCAL-FIXED-RUNTIME-PROFILE.md`. Read the candidate's author handoff and JSON summary, then reviewed actual source, full base-to-candidate diff, tests and independent command output. Read the root fixed-version handover audit as reference; did not infer real runtime success from its official-source argument. Used code-review-and-quality five axes. Indexed this new worktree with graph MCP fast/no persistence before discovery; excluded integration tests were read directly as known diff/test paths. Jev routing returned HTTP 451; retained strong independent review, no downgrade.

The full candidate contains two commits and seven changed files: the allowed three product files, one new profile test, exactly two necessary R13 fake-session additions in one existing test file, author handoff and JSON evidence. All original R13 assert AST nodes are identical. There is no unrelated refactor, dependency/config/Schema change or generated client change.

## Five-axis findings and acceptance evidence

| Axis | Result and evidence |
|---|---|
| Correctness | PASS. Independent complete specified 14-file group: **396 passed in 138.89s**, no deselection/skip. Old three-scope projections/request golden and exact 6144 behavior remain. New resolved profile freezes batch512/output8192/content8101/request12288/context16384/300s/1MB; input bound8191 leaves 8192+1 output reserve. Exact8192, non-stop/donefalse/missing/bool/negative/overflow metadata remain rejected. |
| Readability/simplicity | PASS. Existing profile/session/strict observer reused. The separate load-only1024 helper is explicit and never becomes a ready observation. Shared runner parsing retains original v1 acceptance; v2 requires paired explicit512. No generic profile override/configuration introduced. |
| Architecture | PASS. Resolver allowlists only fixed v1/v2 values; constructed dataclass/options are not eligibility. Qualification reader/resource, harness, factory, state, source authority, backup and long-profile files are byte-identical. The old reader/harness refuse resealed v2 receipts. Registry remains `records=[]`. |
| Security/authority | PASS. v2 qualification refusal and generate refusal precede arm/consume/POST, including recomputed generic permit and manually attached ready session. Backend session binds profile/full value/canonical request/actual wire/execution/host/thread/lease/TTL-before-arm and one-shot consume. Cross-value/profile/request reuse, mutation during probe, foreign thread, expired proof, changed runtime, concurrent heavy lease and consumed claim are covered. |
| Performance/resources | PASS within engineering scope. No unbounded new fetch/generation/retry. Strict manifest/blob/binary hashing remains bounded and mandatory. Fallback re-observes the complete fixed install/known argv plus full cold reserve; it cannot inherit a failed ordinary observation. Genuine cold/warm/reload latency and RAM behavior were not measured and remain a separate load-only gate. |

Critical source review: `local_model_capacity.py:407` keeps normal v2 host fixed512; `:418` is only the load-only1024 preflight; `:427` rechecks installation, unique server, exact runner and disk/full cold RAM. `:827` catches ordinary host failure but reruns that complete stricter legacy gate. `:836` rechecks current observation/lease/unresolved work before the sole empty probe. `:878` requires final ordinary strict512 and `:882` retains installed-files/references/server identity across the probe. Legacy matching requires the complete known argv including fixed binary/model/mmproj, loopback,16384 context, parallel1, paired1024 and every known flag; unknown/missing/extra/asymmetric variants reject. No kill/unload/restart or runner-generation acceptance widening exists.

R13 regression coverage includes reliable observed responding model/usage, honest durable unknown terminal when identity is absent, invocation protection/no resend, diagnostic reset, exact all-table/all-DATA restart/BackupRestore round trips and other-pending-task backup blocking. The complete 14-file run also includes legacy Cloud adapters/dispatch, NO_NEW/history/proof/wire behavior and capacity composition. No response repair or thinking inspection was added.

## Independently executed checks

Working directory for these commands is the review worktree above. Output logs are retained locally under `.var/local-fixed-runtime-review/` (ignored validation evidence, no private contents).

```sh
PYTHONPATH=src:tests:. .venv/bin/python -m compileall -q src tests/unit/test_local_fixed_runtime_profile.py tests/integration/test_local_rejection_accounting.py
.venv/bin/ruff check src tests scripts
PYTHONPATH=src:tests:. .venv/bin/mypy --strict src scripts/qualify_local_grounding_v1.py
PYTHONPATH=src:tests:. .venv/bin/pytest -q tests/unit/test_local_fixed_runtime_profile.py tests/unit/test_local_model_capacity.py tests/unit/test_capacity_host_manifest.py tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_qualification.py tests/unit/test_local_grounding_harness.py tests/integration/test_local_capacity_composition.py tests/integration/test_local_rejection_accounting.py tests/unit/test_ollama_local_distillation.py tests/unit/test_distillation_dispatch.py tests/unit/test_openai_distillation_adapter.py tests/unit/test_moonshot_distillation_adapter.py tests/integration/test_local_grounding_proof.py tests/integration/test_local_distillation_wire_branches.py
git diff --check b3410a489f06d17ea8c62d2f27d637d3bbe25cc2 HEAD
```

- Compile: exit0.
- Required Ruff src/tests/scripts: exit0, `All checks passed!`.
- Strict mypy src plus unchanged original harness: exit0, `Success: no issues found in 117 source files`.
- Exact original complete 14-file group, at final candidate SHA: exit0, **396 passed in 138.89s (0:02:18)**. This independently resolves the author's five old fake failures; the author's earlier 391PASS/5FAIL and subsequent44+7 targeted reruns are historical evidence, not relabelled as their final full run.
- Base-to-candidate diff check: exit0.
- Extra `.venv/bin/ruff check . --output-format concise`: exit1, **40 pre-existing errors in five docs scripts**. Each flagged file was compared byte-for-byte with base. First example: `docs/dogfood/opencode-user-pilot/build_manual_html.py:5:8 F401 sys imported but unused`; other files are `docs/validation/phase13/{fingerprint-protected,real-automatic-check,restart-probe,restore-runtime-validation}.py`. Required src/tests/scripts gate is green; no unrelated docs were changed or failure hidden.

Independent Python heredocs also executed:

1. `PYTHONPATH=src:tests:. .venv/bin/python -`: AST comparison with `git show <base>:<path>` for four Cloud classes, original LocalText class, all R13 assert nodes, and four request/execution/history helpers; exact actual source hashes; all protected file bytes; empty registry. Executed the baseline profile module in a distinct in-memory module and compared canonical bytes of all three v1 projections against current preserved schemas. Recomputed both profile projection/request hashes. Checked core-to-complete product/test diff is empty.
2. `PYTHONPATH=src:tests:. .venv/bin/python -`: real strict observer/session with tiny pinned-byte installation fixtures and fake send, **one valid legacy positive control plus ten bounded negative probes**. Cases: warm512 RAM<2GiB; legacy full cold RAM minus1 byte; cold disk<10GiB; legacy disk<10GiB; tampered binary; extra known `--load-mode none`; missing mmproj; missing log flag; server changed after empty probe; binary changed after empty probe. First eight negatives issue zero fake loads; last two issue exactly one empty fake load then reject. All negatives release lease and have no readiness. Positive control issues one empty fake load and reaches final512 readiness. No generation in any case. Results:11/11 PASS.

Probe setup failure preserved: initial heredoc used `Path(TemporaryDirectory())` under macOS `/var` alias. Existing lease `machine.resolve() != machine` guard rejected before IO, making the after-probe request-count assertion fail (`<stdin>:41 AssertionError: server-changed-after-probe`). A single diagnostic run showed `LEASE False`, `PREPARED False`, `CALL PATHS []` while standalone legacy observation succeeded. Corrected only the review scaffold to `Path(name).resolve()`, added a valid positive control, and reran once to the11PASS result above. No product/test was changed; the initial eight apparent negatives were not counted as final probe evidence. Initial stdout and diagnostic logs are retained below.

## Frozen identities

Actual candidate source/test bytes (all independently equal to author summary and core):

| File | SHA256 |
|---|---|
| `src/youtube_intel/local_distillation_profile.py` | `8f72d3820980f3e900b4fce98d370babb75dad44369b37e056cc92d194f040fb` |
| `src/youtube_intel/local_model_capacity.py` | `4ad223f9e29be91a53df80ddb7ff55a82f6a0c8e237263e816f1b571f922c38d` |
| `src/youtube_intel/distillation.py` | `4cfc1655c8a702621bda9057c594a1447d9dbd894cb6d8d43ea21fb6f8ef8fc3` |
| `tests/unit/test_local_fixed_runtime_profile.py` | `f97af8be210f0c34476cf03976047cb8146f1971c5be416ee14a6596c84fa10e` |
| `tests/integration/test_local_rejection_accounting.py` | `a691604c8601c145554425660b4f61a54b045620f7028fa797e3335a85daa6bb` |

Golden projection/request identities, independently recomputed:

| Profile | Scope/object | SHA256 |
|---|---|---|
| `local-grounding-qwen35-9b-thinking-v1` | `YT_TIMED` | `908575e9dbbdc6c0fa68c6ba0f2754ce1a463cc342202e09301abb79176389b7` |
| `local-grounding-qwen35-9b-thinking-v1` | `LOCAL_TIMED` | `da0b574bc10225da1c8fc99e491bdb7d292ba259c8b7729d6d065d9ecc58e69b` |
| `local-grounding-qwen35-9b-thinking-v1` | `LOCAL_TEXT` | `832f1243c1c25dddeb69f521e750fc0cfd352beecbcc643c15042370ea4d21d2` |
| `local-grounding-qwen35-9b-thinking-v1` | `REQUEST` | `c9959904b49362ad8f4f6caef4cad67478547390843b9aaaf0226bc0b2259be1` |
| `local-grounding-qwen35-9b-fixed-runtime-v2` | `YT_TIMED` | `78d0404f8ccfd6a39bcdfdaeb7a5a9c67c45b6800f1d65da6e61ab97bb5ef750` |
| `local-grounding-qwen35-9b-fixed-runtime-v2` | `LOCAL_TIMED` | `3669defc5ca12c2002d4066ababdc96168136408b9c86be4461d1e76dff69703` |
| `local-grounding-qwen35-9b-fixed-runtime-v2` | `LOCAL_TEXT` | `65a7c14c25741a950bf4d84b19f0e4cfe20a1e59d8d833d75cab65f0c09b7ae6` |
| `local-grounding-qwen35-9b-fixed-runtime-v2` | `REQUEST` | `9a451b14fda68cbddc26ffbd496a47e5e5def0530c8504d23b38f5f6f597349e` |

Protected whole-file identities, equal to base bytes:

| File | SHA256 |
|---|---|
| `src/youtube_intel/local_distillation_qualification.py` | `9fe4059fc0c1d5be6af5586cb84f11b51bd8f4a1ed9cdf0d65a251adef78fe9d` |
| `scripts/qualify_local_grounding_v1.py` | `9478d79f46fad8cea4065f851ba503682ef315557a966bd91830264e5dabd5b9` |
| `src/youtube_intel/runtime_composition.py` | `04862780154b9e1c31698c3ec227e24ef86827df4bb117c2de5cb532ffe8f96a` |
| `src/youtube_intel/state.py` | `71b2e3a5b4fc00153ea4ada604676221916517be84938b8fcf4dffc91da9aa63` |
| `src/youtube_intel/backup_restore.py` | `7a65d287a660c02762d806a1f19d122833a0195c174ebc93e74cd012b2d42b5e` |
| `src/youtube_intel/source_authority.py` | `72f769e4ced5f3a3c0f71241d6fbe04e6ec7f3d99b2a2a52dc717987488dcfe9` |
| `src/youtube_intel/resources/local_distillation_qualification_v1.json` | `0bf8f9526727d0c6f3c217ab3caf5630dc23cd97b6d1bcee525512a043d20347` |

All other tracked files under `src`, `scripts`, dependency/config paths are unchanged; only the three allowed product paths appear in that diff. Baseline/current AST equality was checked for `build_local_distillation_request`, `local_profile_projection`, `verified_distillation_input_projection`, `local_profile_for_scope`, four Cloud classes and the original LocalText class. This preserves current/history projections rather than inferring compatibility from an author's summary.

Local independent logs and SHA256:

| Log | SHA256 |
|---|---|
| `affected-final.log` | `a1e47bfa0a2f471721d529de8bd82fbeb7b45648ed119f147ed9559e29b989b9` |
| `compatibility.log` | `13518300305577492d14e6dc869cdc7c730fec955707c7a0399b26651538e61b` |
| `fallback-probes-resolved.log` | `320e0c4b8f6ca4419e5fe5da5535a24e448d670da711eb98d7c25e3cac0b0b62` |
| `fallback-probes.log` | `12513998207c49bfeaca483c34dc108c866b6df72312be0fdc85a5de81f6ed6c` |
| `mypy.log` | `b7ee2c0bfb540427b2b4b941da1f3c080ce42fa8a487523ebdd76f6f53fea9f2` |
| `probe-diagnostic.log` | `4d153569dd7648707cfcc87106ffa187a21482bff88bbecd625bd008c714944a` |
| `ruff-extra-all.log` | `942257fcfbbecf902c5d457fb41a38a01a09cf0242976e8a096a128796f427fb` |
| `ruff.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |

## Reuse, limits and handoff

DIRECT: existing stdlib canonical/hash/dataclass, profile/request/resolver, strict observer, session/lease, SQLite and installed test tools. REFERENCE: existing independent root audit of official Ollama MIT commit `cf2a313a298066d572c36812e5ad30a21c0db13b`; no third-party implementation copied or dependency added. This review did not repeat internet retrieval or claim official-source behavior as a genuine transition receipt.

Real HTTP=0; real model load=0; real generation=0; Cloud/paid calls=0; owner database/config/credentials/Vault access=0; kill/unload/restart=0. Fake HTTP and temporary SQLite/pinned tiny installation fixtures prove engineering boundaries only. Full backend/UI/actual-model/real-resource qualification and true ordinary-user end-to-end adoption are outside this narrow review; no fresh genuine cold/warm/1024→512 receipt was minted. Model registry remains empty and generation remains closed. The separately frozen safe-resource load-only diagnostic, version-specific qualification/harness, full long-input persistence/closure, original4+unseen holdouts and substantive LOCAL positives, final GUI/BackupRestore/full regression gates remain mandatory.

No implementation correction requested. Return this independent **APPROVE** to root for its own acceptance/integration; reviewer clean STOP after the handoff-only scoped commit. No self-signed DONE, main merge or release.
