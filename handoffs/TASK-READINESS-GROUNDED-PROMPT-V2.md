# TASK-READINESS-GROUNDED-PROMPT-V2

## Metadata and scope

Implementer `/root/cloud_preview_writer`, sole writer/no subagents. Base
`6a55e1c7f711d7aa97db98c85f73a4df65f098a7`; branch
`codex/task-readiness-grounded-prompt-v2`; worktree
`/Users/developer/Documents/yia-worktrees/readiness-grounded-prompt-v2`.
Head reported in final chat. Suggested status IN_REVIEW; Root alone accepts and integrates.

Only product file `src/youtube_intel/distillation.py`, one new offline test file and
this handoff. No Schema/migration, dependency, config, credential, normal budget,
production qualification, API/UI, runtime selection or first-case script changes.
No read/write of native keys, live QA, owner data, old actual diagnostic package or
parallel unseen-oracle work. No network/provider/model call, replay or spent-case
experiment. No claim of actual semantic improvement or qualification from fakes.

DIRECT existing frozen v1 prompt builder, BigModel adapter's TLS/wire/decode bounds,
sealed input projection, SourcePolicy, immutable OWNER consent, dispatch claim,
admission, authoritative reader/audit and BackupRestore. Standard library only.
Tests reuse existing adapter input and task022/BigModel trusted repository builders;
physical synthetic DATA is registered before immutable timed Evidence so actual
backup validation remains intact. No new runner/framework or oracle.

## Contracts

- `_distillation_prompt_messages` source is byte-for-byte unchanged. The new wrapper
  appends a generic paragraph only to the first system message; task/personalization
  and UNTRUSTED_SOURCE_EVIDENCE bytes/order remain unchanged. It distinguishes
  product user/source speaker/publisher, attribution, modality/uncertainty/conditions,
  approximate quantities/units/comparisons, measurement versus unsupported magnitude,
  duration/causality, classified revisable own inference, and legal NO_NEW.
  It contains no case name, supplier name, mathematical example, answer or case numbers.
- Explicit `BigModelGlm47FlashGroundingV2DistillationTransport` inherits the accepted
  v1 transport lifecycle, exact provider/model/endpoint, thinking/JSON, 16384 output,
  temperature1, 300s/zero retry and all wire/decoder bounds. It changes only prompt
  and request-profile identities and adds a SHA of the generic paragraph to its
  profile. Default runtime still selects the original v1 adapter.
- Prompt `intelligence-grounding-v2`; profile
  `bigmodel-glm-4.7-flash-thinking-json-grounding-qualification-v2`.
  After the compatibility repair below, base `VerifiedDistillationInput` and its
  projection remain source-byte-identical to the original base. Only v2 uses private
  frozen/slots/keyword-only `_GroundingV2VerifiedDistillationInput.cloud_profile_id`.
  Trusted service builders derive that finite profile and copy original field values
  with fields/getattr, preserving nested typed Evidence references. The source gate
  accepts exact base type or the exact v2 subtype with matching tuple/marker; arbitrary
  subclasses and unknown markers reject. No external profile selector was added.
- The complete v2 profile/contract SHA and profile ID bind the semantic hash. Actual
  prompt/profile versions bind reservation ID. Existing immutable OWNER consent binds
  that exact new input hash/execution; old input hashes/consent/eligibility grant no v2
  authority. Cross/unknown profile checks precede credentials/wire. Cross-profile
  authorization itself refuses without modifying rows. A misrouted/stale reserved
  continuation retains the existing terminal REJECTED_EVIDENCE/count0 behavior,
  preserves its original consent, and never redispatches or leaves PENDING.
- Normal production remains explicitly false even with an owner qualification permit
  and an injected permissive fake budget; real ProductionDistillationBudget denies.
  LOCAL/BILIBILI cloud denial remains. No audit table, consent, claim, unknown-outcome,
  historical reader, old profile or restore rule was weakened or replaced.

## Evidence

Initial base compile and strict mypy122 passed before RED. New file initially
1PASS/6RED: cloud_profile_id and new adapter absent. After the first implementation,
3PASS/4FAIL exposed missing early profile authorization checks and an incorrect new
test expectation that a mismatched continuation raises (the existing lifecycle
instead returns terminal rejection). Added the early check; tested pure authorization
refusal without writes and separately asserted the unchanged terminal continuation
semantics. Next10PASS/1FAIL exposed the reused test factory's intentionally missing
physical DATA artifact. Fixed only the new fixture by registering real synthetic bytes
and hash before calling existing trusted Evidence builders; no production validation
or existing assertion changed. The focused11-case group then passed5.76s; an additional
normal-route refusal case is included in the final group. Ruff import order was fixed
only in the new file.

V1 golden tests independently pin input projection, shared prompt, profile, exact wire
body and reservation ID hashes captured on the untouched base. A separate read-only
proof executed frozen base-module source and current-module source on the *same*
trusted synthetic repository: real composed semantic hash, full input projection,
request and execution command/ID are identical; SQL/DATA unchanged; key/budget/wire
access0. Recorded in `.var/grounding-v2-checks/v1-identity.json`.

New offline behavior covers both languages, unchanged source/task messages, generic
rules with no case-specific literals, unknown/cross profile rejection before key/wire,
new identity and OWNER consent binding, missing consent with no writes, old consent
not reused, old card/read/audit/usage/history preservation, actual Backup→download→
stage→confirm→recover SQL/DATA equality, changed contract and cross-profile terminal
refusal/restart no replay, LOCAL/BILI denial and normal-route refusal. Fake final text
is explicitly synthetic and is no model-quality evidence.

Final complete affected-file run and static results are reported below/in chat.
`.var/grounding-v2-checks/final.{json,log}` records command, elapsed time, fixed source
hashes, source_unchanged and source equality for the frozen v1 builder and every
preexisting transport class apart from the deliberately narrowed BigModel profile
validation additions. All preexisting test files/assertions remain untouched.

Final fixed group: **518PASS195.68s**, exit0, 13 complete files: new grounding-v2,
BigModel adapter/service, OpenAI, Moonshot, Ollama, dispatch, task022, source context,
task019 trusted reader, BackupRestore, local wire branches and fixed local profile.
The only warning is the existing deliberate duplicate ZIP member in the invalid-backup
test; no warning/assertion was suppressed. source_unchanged=true over165 fixed source,
SQL, new-test and protected first-case-script hashes;13 protected v1 builder/transport
symbols are source-byte-equal to base. No old test file changed. Strict mypy122PASS,
RuffPASS, in-memory compile122 source+new test=123PASS, git diff --check PASS.

All checks use `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`
with explicit `PYTHONDONTWRITEBYTECODE=1` and
`PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-grounded-prompt-v2/src`;
the exact full pytest argv and hash manifest are in the final JSON above. The shared
editable-install default path is never trusted. No real HTTP/model/key operation was
used as evidence. Final scoped commit is reported in chat; clean STOP pending review.

## Independent-review compatibility repair

Fixed86ea was independently **REJECTED**, report
`15f72e662fa7054959550b3205131ad7ff8cf076` (Root preserved asad514).
Its518PASS did not cover two direct raw-asdict consumers: the added null base field
broke the historical YT export's strict key set and changed the long snapshot hash
despite identical model context/messages. That original failure/history is retained.

The repair removes the added field from the base class and restores the original
projection function verbatim; no historical consumer or unknown-field rejection was
changed. Only v2 constructs a dedicated frozen subclass. Conversion uses original
field references, not recursive asdict. Transport marker checks use getattr(None)
plus the finite exact-type/tuple/marker source gate. Existing v2 profile/contract,
identity/consent, normal denial and cross-profile behavior remain covered.

Current AST traversal of all src/scripts Python files found26 asdict calls, including
import aliases/dataclasses.asdict. The three direct VerifiedDistillationInput consumers
are distillation.verified_distillation_input_projection, long_grounding_projection.
_value_snapshot and qualify_readiness_qwen35_intelligence.historical_timed_input_projection.
The other23 serialize typed profile/proof/command/Evidence/source/summary/ledger/outcome/
catalog/delta/API objects, not this input. Full call/function/expression inventory:
`.var/grounding-v2-repair/asdict-inventory.json`. No consumer file was edited.

Three concrete RED checks preserved in `.var/grounding-v2-repair/red.log`: base field
list had the extra field; long old4f6bdfc09fd434eac242f9daef4bfe9c568d6d7fe793d1f5bac8e0d159b25027
becamebe4b25fbd854955184be326b52058419c219918ed23f5aa740512cebd2a07965; original
historical export raised its strict-contract ValueError. Repair focused group
**134PASS11.27s** across the complete new/local-harness/long-projection files. New
regressions pin all19 original base fields, raw-asdict SHA
525f0ea4c1bc7cc923d17b81c9975ff2feff36ce7c491e548f0d39c7a7c02a72,
the exact original long hash, frozen subtype/typed reference preservation and arbitrary
subtype/wrong tuple/unknown marker refusal. Original legacy tests remain unchanged.
Base class/projection/v1 builder source equal6a55e1c7 exactly; strict mypy122PASS and
RuffPASS. Final expanded complete group/results are recorded in
`.var/grounding-v2-repair/final.{json,log}` and reported in final chat. Earlier86ea
evidence is retained separately in `.var/grounding-v2-checks`; it is not relabeled as
compatibility acceptance. No source/prompt/oracle/model experiment was added by repair.

Final repaired group: **704PASS221.15s**, 16 complete files, exit0 and
source_unchanged=true over165 source/SQL/test/protected-script hashes. This is the
original13-file/518-test group expanded with the original local harness, long projection and
long profile files, plus the three new regression cases. The existing duplicate-ZIP
refusal fixture produces the sole expected warning; none is suppressed. All15 frozen
v1 symbols, including original base/projection, are byte-equal to6a55. Compile123,
strict mypy122, Ruff and diff checks pass. A separate frozen86ea-module versus repaired
module proof on one trusted synthetic repository confirms v2 semantic hash, full
projection/request and command/ID byte equality, unchanged SQL/DATA, and zero
key/budget/wire access (`.var/grounding-v2-repair/v2-identity.json`).
Only distillation.py, this task's test and handoff differ from86ea. No legacy consumer,
test, schema, first-case script, actual package or oracle was modified. Repair commit
reported in final chat; clean STOP for cumulative independent review.

## Limits and next gate

This is generic contract/version engineering only. Prompt rules cannot ensure that
an unqualified model preserves source meaning. Original real-case REJECT/output,
oracle and consumed attempt remain unchanged; do not rerun that source in any language
to prove this feature. No new public input was read or oracle chosen here. Root must
independently accept code, freeze separate unseen public input/oracle and review the
specific profile/outgoing package before any separately authorized actual diagnostic.
No production grant, new spending authority, automatic retry or fallback is provided.
