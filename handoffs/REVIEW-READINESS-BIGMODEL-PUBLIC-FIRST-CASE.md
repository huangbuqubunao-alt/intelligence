# REVIEW-READINESS-BIGMODEL-PUBLIC-FIRST-CASE

- Reviewer `/root/bigmodel_audit_review`, independent/no subagents;2026-10-28.
- Base `eaff966251231c08c39f9b44cfccf66d9b0252fd`; fixed author `14565034a3c3e20714bc7448c514f43132be86ff`.
- WT `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-public-first-review`, branch `codex/task-readiness-bigmodel-public-first-review`.
- Concrete package `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-public-first-case/.var/bigmodel-public-first-case`.
- Prepared SHA256 **`d31ae035ab3f8f7b012e48eb35e8d780a63a7d4455a994f9d64a04960e4dcd14`**.
- **Verdict: REJECT fixed145 preexecution package pending one P2 test-reproducibility correction. No APPROVE_ONE_PUBLIC_DIAGNOSTIC grant is issued.** No additional confirmed P0/P1/P2 in the bounded script/package safety inspection. Original writer and Root received the finding; Root assigned the smallest offline-test repair. Later repair is not reviewed here.

Only this report is written. Actual package and Root public source/DATA are not mutated; no approval or attempt marker is added, no real execute/preparation CLI action, native store/key/environment/live6178/6179/owner access, provider/network/model or production/main action. Python fake-injected execution occurs only in new temporary test packages. The invalid-CLI unit passes extra forbidden arguments and exits2 before calling execute; it does not run the real action.

## P2-01 — ordinary unit tests require untracked machine-local source

`tests/unit/test_bigmodel_public_first_case.py:25` opens `module.SOURCE/state.sqlite3?mode=ro`, then copies its DATA/metadata. That is the hardcoded Root `.var/.../bigmodel-public-diagnostic-20261028`, not a committed fixture. A normal clean checkout/CI cannot supply that exact private machine path. The new common-unit fixture therefore fails before testing the harness and prevents ordinary offline test reproducibility. This does not mean the real public source or oracle is invalid.

Independently ran the actual first unit through pytest, with only its imported module's original SOURCE pointed to a nonexistent temporary location. No Root file was renamed, hidden or modified. The import-spec wrapper changes the loaded constant after module import; the test otherwise runs unchanged. Actual result:

```text
ERROR at setup of test_prepare_is_readonly_and_matches_frozen_public_corpus
tests/unit/test_bigmodel_public_first_case.py:25
with sqlite3.connect((original / 'state.sqlite3').as_uri() + '?mode=ro', uri=True)
sqlite3.OperationalError: unable to open database file
1 error in0.48s; pytest exit1 (expected by the negative probe)
```

The regular group below passes only because this machine happens to have Root's stock; that pass cannot establish clean-checkout behavior. Minimum repair: make ordinary fake tests construct or reuse a tracked, provenance-preserving offline public fixture/helper without reading original SOURCE. Keep the real harness fixed public path and actual reviewed package unchanged; do not skip tests, lower source/Evidence/oracle requirements or present fixture output as real quality. Independently rerun ordinary tests with the original absolute SOURCE unavailable before re-review approval.

## Concrete public-package verification

Imported the fixed review script without invoking main, verified its bytes equal the stopped author's script, then pointed only its read-only validation globals to the exact author tree/package. Called pure validate, not prepare or execute. Prepared SHA is exact, all165 code/source/corpus/SQL hashes match, all public artifact hashes and DB/schema/DATA bindings validate. Actual81-table SQL snapshot and19DATA manifest remain identical before/after. `review.json` and external attempt marker remain absent.

Rebuilt actual production prospective command/input/request with its immutable source binding:

| Boundary | Independent result |
|---|---|
| Public case/source |real-deepthink-en/QoXRfTb7ves, source3cede107-8ff8-4c29-b40b-1ddab71727ea, manualfree-public-diagnostic-case-1, outputen |
| Verified input SHA |`4d4b30739519803c87fecd23b991b3f221a508512ecf2f63520f45c617c0150e` |
| Request projection |4224B; SHA`2ded85cc303228625d9026513453f2fa42bd84fd28cd567e4aeb8efa060e7448` |
| Actual JSON body |4132B; SHA`4b87a2d28698122e607f51876e6ddb7c1d67e6ff76daf52452ec8bed1298f03a` |
| Source/coverage |Previously independently compared all18 cue times/text against the exact corpus; actual package revalidation retains that comparison and complete two-Evidence canonical set |
| Data disclosure |Only public title/source/Evidence and original synthetic focus, empty preferences/ignore, BALANCED; original oracle and published Summary are local review artifacts, not model context |
| Official price |SHA`8b8c1f41835842f9f8dd316486ec2a3f34353d5e9d42eeb08a7b42876e5f1886`; exact GLM-4.7-Flash input/output/cache listed free; account entitlement/quota/invoice unknown |

Original attribution/tentative mathematical claims/similar-not-identical/human verification/retention oracle and positive requirement are unchanged. NO_NEW remains legal service success but fails this positive diagnostic. No oracle answer, private preference, unrelated Content or summary is added to the outgoing request. Actual provider quality is still wholly untested by this review.

## Safety inspection

Read the full fixed script/test/handoff and task, using existing review/security guidance and current source for this newly added script. Reuses existing production source-policy/sealed input, OWNER consent/claim, exact BigModel adapter/decoder, audit and Backup contracts; no duplicate lifecycle or normal budget/qualification change. Standard library JSON/SQLite/O_EXCL/fsync is DIRECT reuse; no dependency/framework/license change.

Checked finite single English public case/tuple/endpoint/profile/date/anticipated-free restriction; full code/DB/schema/DATA/request/oracle/price/hash bindings and independent review SHA gate before key access; no CLI credential/provider/path parameter or env fallback; fixed QA namespace only; narrow budget; no implicit paid/model fallback or retry. Source prepare clones via read-only SQLite and checks original rows/DATA before/after. Path/symlink checks and fixed artifact names bound the intended local package.

External O_EXCL/O_NOFOLLOW attempt marker is file+parent fsynced before reservation/consent/claim. It is expressly not proof of POST, is outside DB/DATA restore, and has no delete/reset/retry path. Concurrent/restarted/interrupted attempts cannot obtain another slot. Unknown POST remains claimed/ambiguous; output failures stop rather than generate again. Existing account status, token metrics and cost remain unknown rather than fabricated zero. The current fake tests cover actual Backup/Restore with retained external marker.

Only the exact public assistant final and named accounting/status plus optional opaque response hash are retained. Private reasoning channel is not inspected/exported. Explicit thought markers or exact credential echoes in public final are rejected before admission/persistence. Exception strings are not logged or saved; invalid CLI does not echo argv. Existing rows and DATA must remain, with finite additions bound to the sole execution/revision; no ordinary user execution or model qualification follows even if the diagnostic produces a positive card. Interruption may leave honest PENDING/claimed uncertainty and the consumed external slot; this is not misreported as confirmed execution or silently replayed.

## Independent checks and limitations

Commands use existing `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1`, explicit review `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-public-first-review/src`. Compile preceded fake tests. Actual public dataset is only read; fake runs clone stock into independent temporary directories and prohibit native/real-wire access.

| Check | Independent actual result |
|---|---|
| In-memory compile122src+script+test |124PASS |
| `python -m pytest -p no:cacheprovider tests/unit/test_bigmodel_public_first_case.py tests/unit/test_bigmodel_distillation_adapter.py tests/integration/test_bigmodel_distillation_transport.py -q --tb=short` |107PASS58.47s, on this machine with Root stock present |
| Actual unit with original SOURCE unavailable |Setup ERROR/pytestexit1, confirmed P2-01 |
| `python -m mypy --strict src scripts/qualify_bigmodel_public_first_case.py` |123files PASS |
| `ruff check --no-cache scripts/qualify_bigmodel_public_first_case.py tests/unit/test_bigmodel_public_first_case.py` |PASS |
| `git diff --check eaff9662 14565034` |PASS |
| Actual concrete package pure validation |PASS, exact prepared/input/request/body/code hashes; no approval/attempt/key/wire |
| Existing src/tests/frontend preservation |558 existing tracked files exactbase; no existing assertion changed |
| Fixed new script SHA |`8e8dce691055bb6307c55e52b48b679b8b1587c9ec65278c4d37b4dc60f00ab4` |
| Fixed new test SHA |`6025b29ce12ba4f661cbb1fd712c475d4968e8215d3d5d6338c3a8a9f12158bc` |

Author's original RED/development interrupted fixture failure and final107PASS remain separate historical evidence. No test was removed/skipped/weakened. Fake positive/NO_NEW/HTTP/private-marker outputs and fake keys are explicit engineering fixtures; they prove neither actual free billing nor real semantic quality. No real provider or user key was used. Whole6000-test expansion is outside this bounded preexecution review.

**REJECT145 pending offline test self-sufficiency and cumulative fixed-source re-review.** The concrete public data/package appears internally consistent, but this report must not be used to create its approval or consume its actual attempt. Root alone owns subsequent acceptance and at-most-one real public diagnostic under original standards.

## R2 — cumulative fixed-source and exact-package preexecution approval

**Latest verdict: APPROVE_ONE_PUBLIC_DIAGNOSTIC**, limited to the exact prepared SHA **`d31ae035ab3f8f7b012e48eb35e8d780a63a7d4455a994f9d64a04960e4dcd14`**, source script145 plus test-only repair **`7e7d4d6d68e6a7ba37145fa25b4ce1e8ce257d02`**. Root authorized cherry-picking only that repair into this clean review branch; resulting review source commit449e4331564195120e660c96237ed4d7b42226f6 preserves original4ce8728 rejection. P2-01 is closed. No remaining confirmed P0/P1/P2 in this bounded script/package review.

This verdict authorizes consideration of **at most one** public `real-deepthink-en` diagnostic, exact `zhipu_bigmodel/glm-4.7-flash`, original fixed input/profile/300s/zero-retry/Oct28-price restriction and `ANTICIPATED_FREE_EXACT_MODEL_ONLY`. It is not qualification, semantic PASS, a verified account/free bill, permission for another case/retry/provider/private input or normal production adoption. Account entitlement/actual bill remain UNKNOWN; original oracle/positive/NO_NEW standards stay unchanged. Root alone decides acceptance and creates the actual approval using this final review report commit. Reviewer never writes the actual review.json/attempt or executes the real request.

### Offline fixture correction and privacy/bounds

Repair changes only the unit fixture, committed public stock/manifest/README and author handoff. Independently confirmed all9 original behavioral test functions/decorators/assertions AST-identical to145; the production script is byte-identical, SHA`8e8dce691055bb6307c55e52b48b679b8b1587c9ec65278c4d37b4dc60f00ab4`. No execution/oracle/profile or public package change is needed.

Archive SHA`f12f59025ef423fb0a3b6b0bd74e33b46846d481879bf8cc431d5c360209065f`,723183B, exactly23 unique regular members/5167184 expanded bytes, each manifest size/hash independently verified. Validated no absolute/traversal/backslash/symlink paths, bounded archive/member/aggregate sizes and no duplicate entries. Extraction checks inventory before creating files, verifies pinned archive and each member hash, then writes only a fresh pytest tmp stock. The trusted SQL contains no ATTACH/DETACH/load_extension/writable_schema operation. It reconstructs actual user_version42, integrityok/FKempty, with complete81-table rows/schema exactly equal to the authorized public D; all19 DATA are byte-identical to D. No substitute model response or altered oracle is introduced.

Only four authorized public YouTube videos exist in the reconstructed fixture; preferences and both cloud-consent tables are empty. Sanitized public provenance omits live QA machine paths. No configs, real key/native data, approval, consumed attempt, model result/private reasoning, WAL/free pages or logs are archived. A member-by-member credential/private-key/Authorization-pattern scan found no hits; this supplements the exact known public-source comparison, not a claim that regex can establish arbitrary data's privacy. README preserves source attribution and does not invent a license over captions.

### Independent clean-export verification

Exported this review HEAD via git archive to a fresh temporary tree: no .var exists there. Ran the same full107 group with PYTHONPATH pointing to that export's byte-identical src, existing Root interpreter and PYTHONDONTWRITEBYTECODE=1. Additionally, an import wrapper forces the harness's original module.SOURCE to a nonexistent path, and an independent Python audit hook refuses file/directory/SQLite reads of the real original Root SOURCE. The repaired normal fixture must and does reconstruct its own tracked stock; it does not rely on this machine's untracked D. Actual output:

```text
Independent clean git export: .var absent;
module original SOURCE nonexistent; Root stock reads audit-denied
107 passed in59.28s
Independent clean export group exit: 0
```

This is the same three complete files named in R1, including concurrent/interrupted/restarted at-most-once, private-marker/error redaction, tampering-before-key, honest NO_NEW/unknown and real fake-output Backup/Restore with retained external attempt. Compile124PASS, strict mypy src+script123PASS, changed script/test Ruff no-cache PASS and `git diff --check 14565034 7e7d4d6d` PASS. No assertion/test was skipped, deleted or weakened. Author's intermediate106PASS1FAIL due missing dump user_version and its corrected Backup run remain separate history; true42 is restored, not bypassed. Original R1 local107PASS and missing-source ERROR are retained above, not overwritten by this new clean result.

Revalidated actual prepared package read-only after repair: exact d31ae035 SHA,165 code hashes, input4d4b307…150e, projection4224B/2ded85…7448 and body4132B/4b87a2…03a remain unchanged;81SQL/19DATA before/after equality passes. All8 frozen artifacts rehash through the original validate. Actual review.json and external attempt are still absent. No key resolution, actual provider HTTP/model invocation, real CLI execution or live Root settings QA access occurred.

**APPROVE_ONE_PUBLIC_DIAGNOSTIC only for the exact package above; report commit then clean STOP.** Root must preserve the consumed external marker and original outcome on every result, never tune/repair/replay this case, and independently assess only public final/metadata against the original source, actual Summary and semantic oracle. Even a genuine positive diagnostic does not complete model qualification, ordinary-user/full-Goal acceptance or main-adoption gates.
