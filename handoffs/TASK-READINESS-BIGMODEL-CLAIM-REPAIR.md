# TASK-READINESS-BIGMODEL-CLAIM-REPAIR

Status IN_REVIEW; not accepted or merged. Sole implementer `/root/bigmodel_audit_writer`, new WT `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-claim-repair`, branch `codex/task-readiness-bigmodel-claim-repair`, base `b64cf87d5fce7789a7275fd1eb570b4a3f6f728f` (fixed2bf source plus only Root task/prompt). Original audit WT/896/2bf and all failure evidence remain unchanged.

## Complete pre-edit invocation-write inventory

Graph discovered direct/reserved claim and caller `PersonalizedDistillationService._distill_impl`; graph root predates some new methods, so current AST and SQL-string discovery covered every `.py` in `src/youtube_intel`. Thirteen checkpoint-write functions were found before implementation, preserved in `.var/bigmodel-claim-repair/pre-edit-invocation-writes.json`. Classification below distinguishes permission-to-dispatch from completion/count retention; no route grants quality/fee permission.

| Existing boundary | New-provider classification before repair | Required closure/control |
|---|---|---|
| `state.begin_distillation_execution`, `reserve_distillation_execution` | Accepted initialization; INSERT count0 only | No claim; existing042 INSERT guard refuses count1 |
| `claim_distillation_execution` | Accepted direct PENDING/NOT_CHECKED/count0; **missing raw audit validation**, confirmed malformed BLOB hash crosses claim | Same existing validator inside transaction before UPDATE; exact RED and all-row/DATA refusal proof |
| `claim_reserved_distillation_execution` | Accepted RESERVED_NOT_DISPATCHED/count0; already invokes new-provider raw validator | Retain and test matching corrupt/valid cases |
| `confirm_and_claim_cloud_execution` | Accepted fresh-only repository seam: existing execution refused, typed ID/hash arguments plus strict042 SQL create new consent in same immediate transaction | Malformed args produce zero writes; cannot adopt a damaged historical row; valid fresh/repeat/concurrent controls. Runtime new-provider transport/qualification remains unavailable |
| `long_distillation_execution.claim_long` | Dedicated fixed Ollama proof/profile/readiness path; generic long IDs are rejected by all state claim APIs | New cloud route does not acquire its long/local authority; preserve existing tests |
| `local_model_capacity` / transport arm helpers | Readiness/arming, not checkpoint claim writes | Generic local execution ultimately uses state reserved/direct claim; dedicated long uses `claim_long` |
| `finish_distillation_without_admission`, `admit_distillation` | Completion APIs can retain/set count1, including a count0→1 write; not permission to call transport, but malformed new consent must not become durable authority | Reuse new-provider validator before their existing writes, without redesigning admission or restricting old providers |
| `record_distillation_no_new_intelligence` | Requires already-claimed count1/DISPATCH_CLAIMED before its count1 retention write | Preserve claimed-only precondition and validate new audit before persistence |
| `finish_distillation_cloud_response_failure` | Requires already-claimed count1, updates terminal state only | Not a new claim; existing strict read/reverse validation remains; no count promotion |
| `finish_distillation_unidentified_http_response` | Explicitly refuses new pair because it has no legacy unidentified table | No write for new provider |
| `long_distillation_execution.complete_long` | Requires sealed thread-owned dedicated claim and persisted count1 before completion, plus fixed Ollama proof | Count is retained, not acquired; new cloud does not gain this lifecycle |
| `long_distillation_persistence._reserve` | Initialization only, inserts count0 and exact proof | No invocation claim; fixed local profile/source validation retained |

Raw SQL can always be corrupted on an explicit adversarial copy by disabling CHECK/immutability; application claim boundaries must still refuse bad persisted scalar authority. BLOB/time test corruption restores identical schema/trigger SQL and CHECK state. The NULL fixture necessarily weakens NOT NULL on its isolated table; raw validation still refuses it. SQL042 and every historical migration are read-only in this task.

## Initial RED

The exact reviewer case was recreated using genuine `begin_distillation_execution` (NOT_CHECKED/count0), a valid consent API insert, and only BLOB input-hash corruption. `claim_distillation_execution` did not raise StateStoreError, crossing the durable boundary: **1RED /1.05s**. No provider/model was called.

The first completion fixture wrongly supplied a source_excerpt through the untrusted `create_evidence` path; the existing API correctly rejected it before any claim test. It was corrected to the existing TimedTranscript and EvidenceTextBinding capture methods, without any implementation bypass. The completed tests then read only the preserved original2bf source through explicit PYTHONPATH: rejected/admitted/NO_NEW completion cases all **DID NOT RAISE StateStoreError (3RED /1.54s)**. The corrected source passed all four initial cases. That original worktree stayed clean at2bf; no cache/bytecode/model/owner write was made there. The setup failure is not counted as behavioral RED.

## Final minimal implementation / preserved controls

Only seven production lines were added in `state.py`: four mirror the reserved sibling's existing new-provider validator under the direct claim's immediate transaction, before UPDATE; one reuses that same validator before each existing without-admission/admitted/NO_NEW completion write. No new validator/framework/lifecycle or SQL change. Its old-provider branch immediately returns, preserving old-provider behavior.

The validator intentionally does not require consent for a real uninvoked PENDING/count0 execution. The tests prove no-consent zero-call WAITING_MODEL and WAITING_BUDGET still record their original terminal wait/usage instead of becoming orphan PENDING, and neither can be claimed later. Invoked/unknown/completed histories are not reset or re-adopted. Normal direct/reserved consent with time progression claims once across two concurrent connections and restart; known completions and NO_NEW remain supported. All positive admitted/NO_NEW rows are explicitly offline repository fixtures, not model output or qualification.

The fresh atomic path needed no implementation change: malformed raw arguments refuse before writes, strict SQL creates the typed new consent under the single writer lock, and any existing execution is refused before its callback. Tests prove a valid fresh claim, concurrent one-winner behavior and refusal to adopt the same corrupted claimed history. These repository controls do not grant new-provider runtime/qualification/budget eligibility; no transport is invoked. Generic long identities remain refused at all three state claim APIs; a new cloud tuple cannot bind the fixed local-long profile. Complete LOCAL timed and long-storage suites run below.

## Fixed-source verification

All tests use explicit `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-claim-repair/src`, `PYTHONDONTWRITEBYTECODE=1`, existing `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, and independent SQLite/DATA fixtures. No provider HTTP/model, credentials, owner/Root GUI clone/service, dependency or production action occurred. Jev was not exposed in available tools; the existing strong/default workflow and independent review remain required. TDD/incremental implementation skills were followed.

| Check | Actual result |
|---|---|
| New full claim/control matrix |35PASS,10.69s; included again in complete group below, not disjoint |
| Six complete files: new matrix; Backup; State; task022; LOCAL timed; long completion storage |**430PASS**,236.45s; one expected duplicate-ZIP fixture warning |
| All source/test `.py`/`.sql` before/after run |**398 identical hashes**, source_unchanged=true |
| Strict mypy all source |**122 files PASS** |
| In-memory compile changed two Python files |2PASS |
| Ruff no-cache / git diff check |PASS |
| Every packaged001–042 migration, including unreleased042 |**41 files byte-identical to b64 baseline**; no029 exists |
| Original `/readiness-bigmodel-audit` status/HEAD |Clean at `2bf9cf21725494309d7d9222759dc835a4dc2996` |

Evidence: `.var/bigmodel-claim-repair/pre-edit-invocation-writes.json`, `red-observations.json`, `final-command.json`, `final.log`, `final-source-before/after.json`, `final-result.json`. Final log SHA256: `2416eea8dd8a056c922447c3484f558ab9b1612f7b91972ab84d95866eb8258c`, process exit0,237.209s wall. No test was removed/skipped, assertion loosened or result relabelled. Prior8961458PASS5FAIL→109 repair, and2bf378PASS1FAIL→111 repair plus independent379PASS/remaining P2, remain their original separate evidence.

Scope is one existing production file, one new related test file and this own handoff. No schema/042 checksum, frontend, transport, fees/qualification, credentials/configuration, owner data, main or Root GUI service change. Existing reuse/source/license contracts are unchanged; standard-library SQLite, concurrency/time and existing fixtures are DIRECT reuse, no copied third-party code or dependencies.

Recommendation IN_REVIEW. Root alone accepts/integrates. Commit SHA is reported after clean STOP; no whole-Goal, cloud usability or main-adoption claim is made.

Reuse DIRECT existing immediate transactions, `_validate_zhipu_execution`, original claim/consent/ledger/receipt and fixture builders. No new framework, provider, transport, model/fee authority, dependency, configuration, owner data, frontend or main change. Root owns independent review/integration and the ordinary-user Goal.
