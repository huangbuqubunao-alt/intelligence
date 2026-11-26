# REVIEW-READINESS-GROUNDING-V2-PUBLIC-CAPSULE

Reviewer: `/root/bigmodel_audit_review`, independent reviewer, no subagents.
Fixed author: `65bb6b34221373ceb158b3602f14cb889cee66f0`.
Review base: `ec17b319331e9de26404bc081921e6cd05297781`.
Review worktree: `/Users/developer/Documents/yia-worktrees/readiness-grounding-v2-public-capsule-review`.

## Verdict and mandatory external hold

**APPROVE_CODE_AND_EXACT_PACKAGE_CONDITIONAL**. No new P0/P1/P2 was found in this
bounded engineering/preexecution review. This approves the fixed code and the exact
prepared public capsule below; it is **not present permission to resolve a credential
or execute a model request**.

Root's newer credential-safety decision at `4cdfa5a`, read from its Git-tracked
PROJECT_STATUS, is `WAITING_USER_ROTATION`. Before Root creates actual `review.json`
or performs any Native credential/model operation, the user must explicitly confirm
revoking/regenerating the affected QA credential and updating the isolated settings
page. Configured metadata, this report, and the author's older handoff cannot replace
that confirmation. I did not read the safety-status file, a credential identifier or
value, native Keychain, browser/live QA, `.env`, or private/formal data.

Only after Root records that confirmation, accepts this report, and revalidates the
unchanged fixed code/package/date may Root authorize **at most one** exact public
diagnostic request. Stop on every result, including success, NO_NEW, rejection,
uncertainty or interruption. No retry, next case, paid fallback, production
qualification, normal-budget grant, or rerun of the spent QoXR case is approved.
The Oct28 China-date guard still applies; this report cannot extend or refresh it.

## Exact reviewed capsule

Author package:
`/Users/developer/Documents/yia-worktrees/readiness-grounding-v2-public-capsule/.var/bigmodel-grounding-v2-public-case`.

| Binding | Independently verified value |
|---|---|
| prepared.json SHA256 | `35ba7475c9f734aa9760c7173c6c982a3ccfe2a5bd2332b8d4e861632015344b` |
| Case / public video | `unseen-deepmind-interactive-coding-en` / `IwglW_hIL_g` |
| Manual command | `free-public-grounding-v2-case-1` |
| Input semantic hash | `d97a7c74a56e4d69d5babb657ca3399e5a27576cda0773f8f3ce391150cbfbcd` |
| Request projection | 8928 bytes; `20f8a74c72e390dbf4e5aea74d87fb1426891c415b28be25a9a541942fdb656d` |
| Actual HTTP body | 8836 bytes; `8486c4e4738e84b35ce4c33f0e65101ad67b41aa46382dd9ada21245af763665` |
| Frozen oracle | `6760fd0da95e220e8599c585a11afee9ca7c0c71cd7737291ad03ce3b1ff9cc2` |
| Frozen official-price artifact | `8b8c1f41835842f9f8dd316486ec2a3f34353d5e9d42eeb08a7b42876e5f1886` |
| Complete manifests | 9 artifacts, 168 code/dependency hashes, 81 SQL tables, 19 DATA files |

I independently called only the pure validator against the actual package, with
socket connections denied, using the byte-identical reviewed source. Package DB
bytes, all SQL schema/rows and all DATA matched before/after. The approved first-case
helper's globals remained unchanged. `review.json`, external attempt and `result.json`
were absent. No preparation/reservation/consent/claim/key resolution/wire occurred in
that check. Earlier read-only full-source checking and this repeated validation agree
on all104 real cue fields, 5 canonical Evidence/binding ranges, original source policy,
metadata, published Summary and original focus. No deduplication, name correction,
truncation, source-interest change or synthetic source substitution occurred.

## Actual outgoing information and fair semantic review

The actual model source JSON has exactly `video_id`, `video_title`,
`source_display_name`, `evidence`. Each Evidence contains `evidence_id`, `start_ms`,
`end_ms`, `excerpt`, `excerpt_hash`, `timed_transcript_id`, `timed_transcript_hash`.
All five complete canonical excerpts are present, covering the full104-cue source;
the individual cue-index/time records are review artifacts, not separately sent.
The existing task includes English, BALANCED, the original synthetic focus
`AI reasoning and mathematical research: reliability, human verification, and test-time exploration`,
empty ignore rules and empty personalization. Fixed v2 instructions are the accepted
generic instructions, not a case-specific answer.

Neither oracle, minimum substantive judgment, original Summary, provenance, source
description, publication date nor metadata duration is added to model context.
This matters before generation: the oracle's description names Tong He, but that
description is not outgoing; the raw caption's Tom must not be judged against hidden
name information. A conservative presenter/source attribution, or attribution to the
source's own name wording, is permitted. The model cannot be required to reproduce
the hidden publication date. Conversely, title DeepThink versus caption DeepSeek is
a visible naming conflict: conservative generic descriptions are permitted, while
invented company/product facts are not supported. Historical access claims must stay
attributed to what the source says/plans, without requiring an unseen date. Publisher,
presenter and product user remain distinct. The 160 figure remains a query cap, not
measured usage; reported strategy is not independent verification.

These are preexecution visibility boundaries, not post-output relaxation. The frozen
original oracle/Summary and conditional beyond-Summary judgment/NO_NEW boundary remain
unchanged. No quality result exists for this new capsule, and a structured/admitted
response will still require independent actual semantic review.

## Code, lifecycle, privacy and compatibility

The full base-to-author diff adds only the new294-line script, new293-line offline
test file and author handoff. Product `src`, all41 SQL, accepted f878 implementation,
old scripts/tests/frontend, oracle and dependency/toolchain files are unchanged.
Reuse is DIRECT: approved stateless JSON/hash/path/SQL/DATA/durable-write helpers,
ReadOnlyRepository and Capture from the first capsule; existing prospective builder,
verified input, SourcePolicy, consent, claim, adapter/decoder/admission/audit and
BackupRestore own the application lifecycle. There is no generic runner/framework,
new provider or duplicated persistence protocol. The new module never mutates old
helper globals or calls old hardcoded context/prepare/validate/execute.

Actual MRO is CaptureV2 → Capture → BigModelGlm47FlashGroundingV2DistillationTransport
→ BigModelGlm47FlashDistillationTransport. The accepted v2 request builder/profile
really executes under the inherited pre-admission public-final privacy check. Secret
echo and explicit thought markers in final reject before parser/admission/persistence;
private reasoning is not inspected/exported. Exception/provider text is not logged,
only public final/named accounting/opaque outer-body hash. This finite guard is not a
claim to detect every possible private-thought paraphrase. Temporary secret cache is
cleared. Root's eventual resolver is only the provider-specific QA store, with no
CLI/env/file credential fallback.

Preparation is read-only source SQL/DATA and creates no application execution state.
Validation binds the full source, oracle, price, input, command, task/producer/manual
identity, destination, profile/contract, exact wire, runtime and code hashes. The
manifest includes the imported helper itself. Revalidation occurs before budget/key
and immediately before wire. Only the exact zhipu_bigmodel/glm-4.7-flash v2 pair,
fixed HTTPS destination, thinking JSON,16384 output cap/temp1/300s/zero retries and
existing size bounds are possible. Normal budget/qualification remain closed.

The independent review record binds the prepared hash and real review commit. The
external attempt uses O_EXCL/O_NOFOLLOW and file+parent fsync before any reservation,
consent, claim or key. It means ARMED_NOT_PROOF_OF_POST, not confirmed HTTP. It is
outside restored DB/DATA. Concurrent execution, hard interruption, fresh-module restart,
and restoring even a genuinely pre-execution database do not enable replay. Known
errors and unknown execution retain the authoritative domain outcome; no success is
fabricated. Original rows are preserved, additions are restricted to the exact
execution/revision, DATA remains exact. NO_NEW is legal but FAIL_STOP for this
conditional-positive diagnostic. Even SUCCEEDED means only awaiting semantic review.

The frozen exact-model public price artifact says anticipated free input/output/cache;
it does not prove account entitlement, quota, invoice or actual cost. Those remain
UNKNOWN and cost remains None. No actual endpoint/account/billing check was performed
in this review and no fee authorization is inferred.

## Independent checks and retained verification failures

Existing interpreter:
`/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`.
All source checks used explicit own src PYTHONPATH and PYTHONDONTWRITEBYTECODE=1;
no installation or lock/dependency change.

- Strict mypy `--strict src scripts/qualify_bigmodel_grounding_v2_public_case.py`:
  **123 source files PASS**.
- Ruff `check --no-cache` new script/new test: **PASS**.
- In-memory compile all122 src files plus new script/test: **124 PASS**.
- `git diff --check ec17b319331e9de26404bc081921e6cd05297781 65bb6b34221373ceb158b3602f14cb889cee66f0`:
  **PASS**; name/status exactly the three allowed added files.
- Final byte comparison of all600 tracked src/scripts/tests/frontend files against
  fixed65bb6b: **PASS**. New script SHA is
  `d66ce90b24cbc8adcff4ca5bd7e97dd2922ca741dc315fdc01f81ecc82c077e4`;
  new test SHA is `65be093d5206f7e8daf6b24bdd2035b176600bff301fbee82e17dce0f6072517`;
  oracle remains the fixed6760 SHA. No source changed between checks.
- Actual prepared package pure validation and immutability/MRO/outgoing checks above:
  **PASS**; no actual approval/attempt/result or network/key side effect.

Offline checks ran from a fresh `git archive 65bb6b...` export with no `.var`, its own
src, committed stock fixture, and an additional audit hook refusing the original Root
D path and all `socket.connect`. New fixtures also refuse native credentials and real
wire. The seven complete files exercised were:

```text
tests/unit/test_grounding_v2_public_capsule.py
tests/unit/test_bigmodel_public_first_case.py
tests/unit/test_grounded_cloud_prompt_v2.py
tests/unit/test_bigmodel_distillation_adapter.py
tests/integration/test_bigmodel_distillation_transport.py
tests/unit/test_local_grounding_harness.py
tests/unit/test_backup_restore.py
```

My first streamed run's completion could not be recovered after context interruption;
it is not counted as a pass. The retained-log rerun launcher initially lacked its own
`sys` import and stopped before pytest. Fixing that temporary launcher exposed its
second invocation issue: executing `/tmp/run.py` replaced the project-root module
search path. That attempt completed **270PASS/15FAIL/32ERROR in123.10s**, with all
failures/errors being unavailable `scripts.*` imports, not failed domain assertions.
The unchanged CLI negative test passed because `python -m` uses project-root context.
Full log is retained at:
`/var/folders/yk/wdmys1pn75lcr5pnnkyjv8km0000gn/T/capsule-independent-r2-a3c2n4tt/checks.log`.

I diagnosed the import path and reran only affected complete files with the same
export/audit hook using project-root `python -c 'import runpy; runpy.run_path(...,
run_name="__main__")'`, explicit export/src PYTHONPATH and the same pytest flags
`-q --tb=short -p no:cacheprovider`. New capsule **33PASS83.22s**; old local harness
**51PASS5.51s**. These close every import failure in the earlier attempted group;
the unaffected checks passed there. No product/test/assertion was changed. This is
split independent evidence, **not a claim that one seven-file run was fully green**.
The sole group warning was the existing deliberate duplicate-ZIP-member refusal test.
Author's separate263PASS169.08s is author evidence, not relabeled as my result.

The new complete fake tests specifically verify full-source pure preparation, real
v2 MRO/body without oracle leakage, fifteen tamper boundaries before key0/wire0/once0,
positive/NO_NEW/known HTTP errors/202/timeout/wrong model/schema, pre-admission thought
and key-echo refusal, post-key tamper before wire, normal gates/date expiry, concurrency,
interruption/restart and actual fake-output Backup→download→stage→confirm→recover.
The latter verifies all81 table rows plus19 DATA and the external once marker,
including recovery of a pre-execution DB without reopening dispatch.

## Limits and handoff

Only this review report is added by me. No business/test changes, model/HTTP calls,
keys/native/browser/live QA, actual review/attempt/result, source/package writes,
production data, formal main or deployment were touched. No actual GUI, account,
semantic quality, full qualification matrix, fee/quota or end-to-end product-readiness
pass is claimed. Previous failed model outputs, rejections and spent markers remain
untouched. Root must keep WAITING_USER_ROTATION until the user's explicit completion,
then independently decide whether the exact one-request diagnostic may proceed.

Scoped review report commit; clean STOP after reporting to Root.
