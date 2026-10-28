# REVIEW-READINESS-GROUNDED-PROMPT-V2

- Independent Reviewer `/root/bigmodel_audit_review`, no subagents;2026-10-28.
- Base `6a55e1c7f711d7aa97db98c85f73a4df65f098a7`; fixed author `86ea0d0668c0bbfaea3f534d277ba177b24873a7`.
- Worktree `/Users/hua/Documents/yia-worktrees/readiness-grounded-prompt-v2-review`; branch `codex/task-readiness-grounded-prompt-v2-review`.
- **Verdict: REJECT fixed86 for one confirmed P2 backward-compatibility defect with two independently verified manifestations.** No additional confirmed P0/P1. Root was notified and returned repair to the original writer; reviewer does not repair product code or review moving changes.

Only this report is written. No product/test/oracle/actual spent package/source-D edits, real key/native/environment/liveQA/owner access, provider/network/model call, schema/dependency/configuration/main action. All executions below are pure synthetic/offline or test fixtures. The independent unseen oracle was neither used to tune code nor sent to the writer/model.

## P2-01 — adding a None field changes old direct-asdict contracts

Location `src/youtube_intel/distillation.py:254`, newly added `VerifiedDistillationInput.cloud_profile_id`. The modified public projection helper correctly omits None for this key, but existing consumers do not all use that helper. A cloud-only change therefore alters the raw shape of every old verified input, even when no new profile was chosen.

**A. Historical timed export now always rejects a default old input.** `scripts/qualify_readiness_qwen35_intelligence.py:83` calls asdict and validates an explicit original field set. The new key makes its strict set mismatch. The unchanged existing test actually fails:

```text
tests/unit/test_local_grounding_harness.py:74
test_historical_export_is_explicitly_separate_from_current_proof_export
research.historical_timed_input_projection(value)
scripts/qualify_readiness_qwen35_intelligence.py:92
ValueError: historical research export requires the original YT timed contract
1 failed,130 passed in10.91s
```

This is not an unknown/future-input refusal: the caller supplied the same ordinary default YT input as before, with the new marker None. Historical strict future-field rejection must remain, rather than being widened to arbitrary extra keys.

**B. Existing local long projection changes its semantic snapshot hash under the same version/profile.** `src/youtube_intel/long_grounding_projection.py:208` returns asdict(value) directly. Its model/messages bytes do not contain this optional cloud marker, but its side-bound semantic snapshot now does. Independently loaded the actual base VerifiedDistillationInput class from6a55 AST, supplied identical synthetic field values/packet to the unchanged long projection, and compared with current default class. Only the global input type check was temporarily bound to the original class inside that isolated process; no source/file changed.

```text
Same local profile/version, model_context_wire and messages_wire identical
Base semantic_snapshot_hash:
4f6bdfc09fd434eac242f9daef4bfe9c568d6d7fe793d1f5bac8e0d159b25027
New semantic_snapshot_hash:
be4b25fbd854955184be326b52058419c219918ed23f5aa740512cebd2a07965
Only extra side.value key: cloud_profile_id:null
```

The old long module itself is byte-unchanged. Existing roundtrip tests passing do not detect this base-to-current drift. This is a backward-compatibility/unchanged-identity requirement violation in the older preview/side-binding contract; no real production model call, data corruption or extra spending was observed.

Minimum repair should preserve the original base input's field layout/serialization for all old consumers, rather than only filtering the two discovered callers or relaxing strict unknown-field validation. Root has proposed a finite v2-specific frozen input type/marker with explicit trusted construction/validation, keeping all old types and fields exact. Review must verify the actual fixed design and old default exports/side hashes, not infer compatibility from only the canonical projection golden. No broad refactor, changed old version identity or actual spent package mutation is needed.

## Other bounded review observations

Read exact three-file diff, new tests, task/decision/handoff under code-review-and-quality/security guidance, using existing discovery context plus actual current callers. Shared v1 prompt source and13 old transport/protocol symbols remain byte-identical. The generic added contract contains role attribution, modality/uncertainty/conditions, approximate quantities/measurement/comparison, revisable classified own inference and legal NO_NEW; no source-specific names/numbers or oracle answer. Source/task messages remain unchanged, with only the new first-system-message addition.

Distinct v2 prompt/profile and paragraph SHA bind the new semantic input and reservation/OWNER-consent identity; new tests exercise missing/wrong/cross/changed-contract refusal before credentials, old card/reader/audit/usage continuity, actual fake-output Backup/Restore, closed normal budget/eligibility and LOCAL/BILI denial. No new API/config/runtime selector or normal production authority is introduced. These positive engineering checks do not override the two compatibility counterexamples or demonstrate real semantic improvement. No new source/oracle was used in the offline outputs.

## Independent checks

Existing `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, explicit `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-grounded-prompt-v2-review/src`. Compile preceded tests. Synthetic long comparison additionally imports this WT tests/unit. No key/wire/network/actualcase.

| Check | Independent actual result |
|---|---|
| In-memory compile122 source+new test |123PASS |
| `python -m pytest -p no:cacheprovider tests/unit/test_grounded_cloud_prompt_v2.py tests/unit/test_local_grounding_harness.py tests/unit/test_long_grounding_projection.py -q --tb=short` |130PASS/1FAIL,10.91s; unchanged historical export failure above |
| Independent original-dataclass long snapshot comparison |Confirmed same messages/model but changed old semantic hash, sole extra None key |
| `python -m mypy --strict src` |122files PASS |
| `ruff check --no-cache src/youtube_intel/distillation.py tests/unit/test_grounded_cloud_prompt_v2.py` |PASS |
| `git diff --check 6a55e1c7 86ea0d06` |PASS |
| Old v1 symbols |13 source segments exact, including shared prompt/Ollama/OpenAI/NVIDIA/Moonshot transports/protocols |
| Fixed src/tests equality |442files exact86; combined path+bytes SHA256 `17eb1341f622ccc82b1356f9219d544fe5bdd1d9b44baa5e9cced201b9431328` |

An initial auxiliary read guessed the test filename incorrectly; actual changed filenames were then read from git diff before running the correct complete group. No tests ran or passed from that mistaken file read. No test/assertion was modified, deleted/skipped/weakened. Author518PASS13files is retained separately: it omitted the failing historical-harness file and does not prove every direct serialization consumer unchanged. Once these concrete old-contract regressions were confirmed, blindly repeating the author's larger overlapping group or full6000 tests was unnecessary. Root owns fixed repair/re-review.

**REJECT86 pending preservation of old direct input serialization and golden long-side identities.** No model eligibility/quality/free billing/whole-Goal/main approval is issued; zero real generation and no spent-case replay. Report commit then clean STOP.

## R2 — cumulative fixed repair review

**Latest verdict: APPROVE cumulative86 + repair `f878fcd9e6616a962e6fea7ca43fe312f21b803e`, bounded version/authority engineering only.** Original P2-01 and both its independently observed manifestations are closed. No remaining confirmed P0/P1/P2 in this slice. Original86/15f72 rejection stays historical; this approval is not retrospective acceptance of standalone86 or evidence that an unqualified model now has better semantics.

Root authorized only the repair cherry-pick into the clean existing review tree, yielding b34b92d1c03839ce4782a66051a158288617462c before this report. Only this R2 report addition is authored by reviewer. No real key/native/environment/provider/network/model, old actual package/D/liveQA, oracle, product/test implementation or main action.

### Compatibility and finite v2 type

Original19-field VerifiedDistillationInput class and canonical projection helper are now source-byte-identical to6a55, rather than filtering a new field at selected old consumers. Only explicit v2 uses a private frozen/slots/keyword-only subtype with the marker. Its builder copies typed fields/references through dataclasses.fields/getattr, preserving actual VerifiedEvidenceInput objects instead of asdict dictionaries. Arbitrary subclasses, wrong tuple/marker, base input at v2 and v2 input at v1 are refused by the finite exact-type/source/profile checks before credential/wire. Constructor existence alone grants no authority, and normal-production predicate/budget remain closed.

Independently enumerated **26 asdict calls** across committed src/scripts. Only three consume this verified-input contract: the canonical projection helper, historical timed export and local long value snapshot. Historical strict type/field checks and the long projection's exact-base input check remain untouched and now get their original base shape; neither is broadened to unknown extra fields or a cloud subtype. The other23 calls concern profile/command/usage/execution-result/local-proof/verified transcript-or-Evidence/catalog/provider-status/Delta dataclasses, not this input; their classes and consumers remain unchanged. No known-consumer patch or blanket unknown-field allowance was added.

Independent raw base export SHA is again `525f0ea4c1bc7cc923d17b81c9975ff2feff36ce7c491e548f0d39c7a7c02a72`; old long snapshot is again `4f6bdfc09fd434eac242f9daef4bfe9c568d6d7fe793d1f5bac8e0d159b25027`. The complete original historical-harness and long projection/profile suites pass without edits to their old assertions. All15 protected v1 symbols, including original base/projection/shared builder and old transport/protocol symbols, match6a55 source bytes; all41 packaged SQL files remain exact. Default v1 request/profile/golden execution identity remains unchanged.

### v2 identity, authority and actual storage controls

Loaded the actual frozen86 distillation module separately, built both old86 and repaired v2 on the **same trusted synthetic repository**, and compared semantic hash, full verified projection, outgoing request and complete command/execution ID. All are byte-identical; full SQL and physical DATA remain unchanged, credential/budget/wire callbacks all prohibited. Actual output:

```text
86->fixed v2 same DB: semantic/projection/request/command+executionID byte-identical;
SQL/DATA unchanged; key/budget/wire0
v2 semantic be64e9fd9db9535acd3dcc0c77990c25479ea849207396b9f7b71f2f822dcaa5
Base19-field class byte-exact; raw asdict525f and old long4f6b hashes restored
```

The added regressions pin base fields/raw export/long hash, frozen subtype, typed reference preservation and foreign-subtype/wrong-pair/unknown-marker refusal. Existing full v2 file retains generic contract/source separation, both languages, changed contract/profile input/execution/OWNER-consent binding, no credential on missing/stale consent, old card/audit/read/history survival, actual fake-output Backup/Restore and closed normal/LOCAL/BILI paths. No case-specific answer or independent oracle content was added to the generic paragraph; neither the spent real case nor a new source/model was executed.

### Independent final checks

Root's existing Python, explicit review src PYTHONPATH/PYTHONDONTWRITEBYTECODE=1; compile precedes tests. No dependency installs or source repairs.

| Check | Independent actual result |
|---|---|
| In-memory compile122src+new test |123PASS |
| Complete12-file group below |**483PASS**,104.37s; one expected duplicate-ZIP refusal warning |
| Strict mypy all source |122files PASS |
| Ruff no-cache changed source/test; diff check86→f878 |PASS |
| Frozen86 versus fixed v2 pure same-DB identity comparison |All compared bytes equal; SQL/DATA unchanged; no key/budget/wire |
| Base19-field/raw-asdict/old-long compatibility probes |Original bytes/hashes restored |
| Fixedsrc/tests equality after checks |442files exactf878; path+bytes SHA256 `e55a7ee352ffc589be6c1f98b4d4f9d8f408a04f82e2bf81edac808371bc6410` |

Actual complete pytest argument list after explicit review Python/environment prefix:

```text
-m pytest -p no:cacheprovider
tests/unit/test_grounded_cloud_prompt_v2.py
tests/unit/test_local_grounding_harness.py
tests/unit/test_long_grounding_projection.py
tests/unit/test_long_distillation_profile.py
tests/unit/test_bigmodel_distillation_adapter.py
tests/integration/test_bigmodel_distillation_transport.py
tests/unit/test_openai_distillation_adapter.py
tests/unit/test_moonshot_distillation_adapter.py
tests/unit/test_distillation_dispatch.py
tests/integration/test_task023b_distillation_reservation.py
tests/integration/test_task019_trusted_intelligence_read.py
tests/unit/test_backup_restore.py -q --tb=short
```

The initial attempted group used a nonexistent guessed reader-test filename and ran0 tests; it was corrected from the actual repository inventory before the complete group above. An auxiliary pure-comparison process initially omitted tests from PYTHONPATH and failed to import conftest before any fixture work; corrected explicit path then produced the identity proof above. Neither setup error is treated as a product failure or passing check. Original R1 130PASS1FAIL and author134focused/704expanded passes remain separately preserved, not erased or added to the independent totals. No existing test/assertion was removed, skipped or weakened. Larger overlapping/full6000 runs are not claimed or needed after the targeted complete group and causal compatibility probes passed.

**APPROVE repaired generic v2 engineering only.** Root alone accepts/integrates and independently reviews a new concrete unseen input/profile/outgoing package before any separately bounded real diagnostic. Existing model qualification/budget stay closed; original spent-case semantic REJECT/output/oracle/attempt remain immutable. No generation, actual free-billing guarantee, normal eligibility, whole-Goal or safe-main adoption is authorized by this review. Report commit then clean STOP.
