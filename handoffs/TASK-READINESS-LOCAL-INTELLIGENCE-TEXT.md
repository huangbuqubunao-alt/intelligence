# TASK-READINESS-LOCAL-INTELLIGENCE-TEXT implementation handoff

## Metadata

- Role: Implementer `local_text`; independent Reviewer `intel_bounded_review` pending.
- Base: `2978550aee692c7b24d5707d2eb4ebdfcc1d0e2f`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-local-intelligence-text`.
- Branch: `codex/task-readiness-local-intelligence-text`.
- Final full commit SHA is supplied in the delivery message; implementation and
  this report are in that same atomic commit.
- Approvals: task card, LOCAL_INTELLIGENCE_CHAIN_PROPOSAL,
  LOCAL_TEXT_TRUSTED_READER_ADDENDUM and the subsequently specifically approved
  LOCAL_TEXT_READ_CURRENT_ADDENDUM at root `54a8c20`. The latter was read from
  `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/docs/validation/end-to-end-user-readiness/LOCAL_TEXT_READ_CURRENT_ADDENDUM.md`;
  root owns that governance document and task-card amendment.

## Goal and delivered scope

Real LOCAL TXT/MD source authority supplies exact TEXT_RANGE references, Unicode
code-point offsets, derived lines, source/canonical/excerpt hashes and NULL
timestamps. Manual source/Summary admission is source-bound and remains manual
only. The new independent wire is `local-text-distillation-v1`; provider output
cannot invent or expand a range. Strict parsing rejects unknown/missing/extra
fields, booleans as positions, duplicate JSON keys, fabricated hashes/times,
mixed locators, cross-Content references and incomplete NO_NEW coverage.

Schema 38 remains unchanged. The immutable versioned execution ID holds sealed
input/context hashes and an identity hash that binds exact command fields and
the independent profile hash. The card hash binds those commitments and every
cited range. The reader requires exactly one matching checkpoint and ledger for
the revision, validates status/invocation/source/Content/model identity and
profile, resolves the current source ranges, then verifies the exact card hash.
It never tries alternate hashes or infers a new version from NULL timestamps.
The approved public `read_current` hook applies the same `_read_card` validation
to actual LOCAL text cards before direct Save, list_saved or Topic can consume
the trusted revision. Save/Topic write transactions and CAS are unchanged.

Admission rechecks the exact current source, Summary and coverage context in the
transaction. Historical reading preserves the original context commitment while
revalidating current source authority and lawful revision state; a genuinely new
verified deterministic Summary does not rewrite old cards or make them unreadable.

The existing Evidence UI shows real text lines or bilingual unavailable copy.
Internal Content/Evidence IDs are serialized in the hash; on refresh or history
navigation the current Content DTO must contain that same Evidence before focus
is restored. URL offsets and timestamps never grant authority. The layout reuses
the existing workspace DESIGN.md; no new screen, nav or stylesheet is introduced.

Independent `LocalTextDistillationProfile` and preparation-only harness freeze
exact model/digest, prompt/schema/parameter hashes and code hashes. There is no
generate function, factory installation or production receipt. Content inputs
are not yet frozen. All model qualification remains false; real LOCAL8 is still
BLOCKED by the failed original four-case/semantic qualification.

## Reuse and scope hygiene

- DIRECT: standard-library JSON/hashlib/SQLite, existing source_authority and
  Evidence resolver, Summary/current pointer, sealed command/input, reservation,
  budget/ledger/cancellation, NO_NEW transaction, authoritative reader, Save,
  Topic and Backup/Restore. Existing approved dependencies are reused as installed.
- ADAPT: only the first-party exact text wire/profile/hash and reader binding.
- REJECT: pseudo 0ms evidence, mixed timed/text authority, external URL authority,
  missing hash/range validation, output repair, inherited old receipt/qualification.
- No third-party code was copied; source/license inventory remains
  docs/REUSE_REGISTER.md and the existing project NOTICE. No dependency, lockfile,
  toolchain, schema or provider code was changed.
- Actual files: distillation.py, state.py, intelligence_read.py, local_api.py;
  App.tsx/uiLanguage.tsx/App.test.tsx; corresponding two local integration test
  files; preparation script/profile JSON; this handoff and LOCAL_TEXT_CONTRACT.md.
- runtime_composition.py, Save/Topic writers, subtitle providers, raw/archive
  contracts, production configuration and formal owner data are unchanged.

## Verification

All positive outputs are explicitly offline fixture transport outputs. They are
not real-model qualification or owner acceptance evidence.

| Check | Evidence/result |
|---|---|
| TDD baseline | Two TXT/MD tests initially failed at manual-ready rejection; real text ranges/NULL times now pass. |
| Final affected backend suite | 333 PASS in 230.78s, `.var/local-text/verified-final-checks.log`; nine execution-binding/profile checks PASS in 18.83s after the final fixture strengthening below. |
| New negative current/save/list/topic paths | Eight execution/ledger corruption types closed; targeted 13 checks PASS. |
| True Summary refresh/history | New source-bound EXTRACTION produces a different verified Summary artifact; unchanged historical/card revision remains readable, PASS. |
| Save/Topic/Backup/Restore | Positive/NO_NEW fixtures preserve every table and DATA hash; durable reload, exact revision/evidence binding PASS. |
| Full frontend | 446 tests PASS, 27 files; latest log `.var/local-text/frontend-tests.log`. |
| TypeScript/build | npm run typecheck and npm run build PASS. |
| Strict typing | PYTHONPATH=src:. .venv/bin/python -m mypy --strict src scripts/prepare_readiness_local_text.py: 103 source files PASS. |
| Runtime/tests/scripts lint | PYTHONPATH=src:. .venv/bin/python -m ruff check src tests scripts PASS. |
| Diff hygiene | git diff --check PASS; changes confined to approved scope. |

Focused backend batch command (no hidden network/model qualification):

```sh
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/integration/test_local_intelligence_text.py \
  tests/integration/test_local_intelligence_timed.py \
  tests/integration/test_local_distillation_wire_branches.py \
  tests/integration/test_task022_personalized_distillation.py \
  tests/integration/test_task023b_distillation_reservation.py \
  tests/integration/test_task019_trusted_intelligence_read.py \
  tests/integration/test_task025a_saved_intelligence.py \
  tests/unit/test_ollama_local_distillation.py \
  tests/unit/test_distillation_dispatch.py -q
```

Coverage includes bilingual output, Unicode emoji/combining marks/multiline
positions, exact source/hash/range/version checks, before/final context damage,
complete NO_NEW, Cloud API/service zero payload/dispatch, old transport zero
credential/request receipt rejection, double click, WAITING_MODEL cancellation,
WAITING_BUDGET, unknown result/restart, saved/topic trust, historical Summary
refresh and exact Backup/Restore tables/files. Old YouTube wire/card hash and
DTO exact-shape regression checks remain intact. The previous timed test's
obsolete text-not-supported assertion was replaced with an explicit new-version
zero-invocation assertion; its foreign-source and unbound-storage rejection
checks remain.

## Failures corrected and remaining gates

- Old DTO exact-shape regression failed after adding locator fields to all
  references; narrowed the fields to TEXT_RANGE only, preserving old YouTube and
  timed DTOs. The original assertion is unchanged and passes.
- Fixture-only defects corrected: misplaced test assertions, duplicate-checkpoint
  SQL column count, keyword-only SaveIntelligence construction, and an invalid
  attempted same-artifact language relabel. The latter was replaced with a
  genuine source-bound extraction and newly verified Summary, not a weakened
  history assertion. No assertions/tests/CI gates were removed or skipped.
- Final preparation fixture now obtains the pinned model input directly from the
  application reservation rather than substituting caller fields. The input hash
  assertion and input/context corruption cases use the corrected execution-ID
  component indexes; all nine binding/preparation cases were rerun and passed.
- The broad `ruff check .` also scans historical docs Python examples and reports
  40 pre-existing out-of-scope errors, e.g. unused sys in
  docs/dogfood/opencode-user-pilot/build_manual_html.py:5 and semicolon examples
  in docs/validation/phase13. Those files are unchanged; required src/tests/scripts
  lint passes. No broad formatting cleanup was made.
- One preparation invocation accidentally used system python3 and failed on the
  existing tiktoken dependency. It was rerun successfully with the approved
  shared `.venv` and PYTHONPATH=src:.; no installation/dependency change occurred.
- Existing frontend act warnings remain in the old tests. New tests' warning was
  resolved by awaiting the UI action; assertions remain unchanged.
- Entire backend final-readiness regression, independent review, root's real
  TXT/MD and Research refresh GUI proof, and actual qualified Intelligence →
  Save → Topic ordinary-user positive acceptance remain overall gates. This task
  makes no claim that fixture output passed any real model gate.
- Model, public network, Cloud, credential reads, downloads, owner/formal data,
  launchd, merge/release/deployment: zero authorized real actions taken. Jev was
  not invoked under this task's explicit zero-model-call restriction.

## Delivery

Suggested status: IN_REVIEW; final affected checks passed. Implementer
stops all writing after the exact committed SHA is reported. No self-approval,
main merge, task-board DONE update or production activation is performed.
Independent Reviewer and root acceptance are pending.


## 2026-10-14 独立 Reviewer / intel_bounded_review

**REJECT** 固定候选 `b79b509d3f039b2376e8122f8d8ed70e8bfb5302`，base
`2978550aee692c7b24d5707d2eb4ebdfcc1d0e2f`。实现者已停止且树干净；本 Reviewer
仅追加交接，不修改业务/测试/Schema/旧冻结文件，不调用模型、网络、凭据、正式
API 或 owner 数据。全独立回归通过不覆盖以下可信边界缺口，不能整合此候选。

### Spec / P1-1：原封存输入与上下文只剩 opaque hash，历史证明未重新验证

`intelligence_read.py:_text_card_projection` 约 337–341 行从 execution_id 取
`input_hash/context_hash`，传回 `_text_execution_id` 重算第三段，只检查当前
`manual_local_text_context_hash(...) is not None`。checkpoint/ledger 验证来源和
执行状态，但没有持久原 sealed input/context 投影供 reader 重构原哈希；原
Summary identity/hash/language/coverage 等事实不能从两段哈希恢复。card hash
包含同样两段字符串，只证明内部字符串一致，未验证这些字符串所承诺的历史。
违反任务/可信 reader 补充的“不能仅 opaque hash 自证”与 sealed context 要求。

独立正常私有 SQLite/fixture 复现（只一次离线 fake transport，无真实模型）：
1. 原 source-bound TXT → 正常 reservation/调用/入卡；
2. 复用原作者历史正控建立真实 source-bound EXTRACTION，正常创建新 Summary；
   新旧 Summary artifact 不同，新 Summary 读取有效，历史卡仍可读，正控 PASS；
3. 仅在私有 DATA 损坏原 sealed Summary 文件，未改 DB、trigger、checkpoint、
   card/hash、当前新 Summary 或 canonical/Evidence；原 ExtractiveSummaryService
   reader 明确拒绝该损坏文件；
4. `read_current_card`、`read_recorded_card`、`read_current`、直接 Save、Topic
   全部仍 ACCEPTED。同一原 admitted context 已无法验证却进入 trusted 消费入口。

命令：`PYTHONPATH=src:.:tests .venv/bin/python /tmp/local-text-review-history-probe.py`。
日志 `/tmp/local-text-review-history-probe-resolved.log`；证据库
`/private/var/folders/yk/wdmys1pn75lcr5pnnkyjv8km0000gn/T/local-text-review-history-jbajzc4r`。
关键输出 `Original historical Summary actual reader CLOSED: ValidationError`，
随后五项 `DAMAGED original context still ACCEPTED`。
进一步正常 Backup readiness 对真实 DATA 损坏仍 ready=false、message referenced
artifact changed/missing（`/tmp/local-text-review-history-backup.log`）；因此本 finding
是可信读取/原 context 证明缺失，**不是 Backup 绕过、费用或生产资格绕过**。

返修需保存并重新验证明确原输入/上下文的完整事实与原 Summary/source/coverage
关联，匹配原哈希和唯一执行，而不是把 opaque hash 纳入另一个 hash 即自证。
合法 Summary refresh 必须保留正控，不能用“当前 context 等于旧 hash”粗暴拒绝
所有历史。若既有 Schema/批准文件范围不能承载可验证持久证明，按原任务 STOP
并报告精确增补，不擅迁移/倒填历史/授新模型资格。

### Spec / P1-2：卡片缺失时 read_current 跳过新增可信校验

`intelligence_read.py:read_current` 约 154 行将 `get_distillation_card(...) is
not None` 作为进入 TEXT_RANGE 严格验证的前提。对于实际已持久化本地文本提炼
revision，卡片缺失时 `_read_card` 必须拒绝，但公共 read_current 直接返回原
verified，Save/list_saved/Topic 正好使用这个入口，故新缺版本/执行关联校验可漏。

独立负控沿用作者 tests 中的损坏 repository getter seam：真实私有正常入卡后，
仅令该 getter 返回 None；未删除 SQLite 行、修改/停用 immutable trigger，未
声称正常 SQL 可以删卡或已在正式产品造成此损坏。直接卡片入口 CLOSED
`IntelligenceReadRejected: distillation card is unavailable`，而 read_current、
Save、list_saved.verified=True、Topic 仍 ACCEPTED。
脚本 `/tmp/local-text-review-missing-card-probe.py`，同名 `.log`；证据库
`/private/var/folders/yk/wdmys1pn75lcr5pnnkyjv8km0000gn/T/local-text-missing-card-review-qba3oszd`。
命令同上述 Python/PYTHONPATH，fake transport 1，真实调用 0。

返修须以实际 revision/LOCAL text Evidence/持久执行关联判断是否必须验证，而不
以待验证卡片存在作为前提；新类型的缺失 card/proof/关联应 failclosed，原普通
非-card revision 及旧 YT/timed 合同保持。此项独立于 P1-1，两者均需关闭。

### Standards 与其他范围复核

重读 task、AGENTS/协作/规范，以及原 LOCAL_INTELLIGENCE_CHAIN_PROPOSAL、
LOCAL_TEXT_TRUSTED_READER_ADDENDUM 和 root 的已批准 READ_CURRENT_ADDENDUM。
graph-first 尝试既有 symbols，新增函数不在旧索引，按固定候选实际完整 13 文件
差异读源码；没有建立/重建索引。仓库一个 Reviewer 优先于 review skill 并行建议。
范围、DIRECT 复用、strict JSON/精确 reference typed equality、duplicate keys、
TIMED/TEXT 混用拒绝、real codepoint/line/NULL 时间、manual-only 与当前 Summary
admission/NO_NEW final CAS、完整 coverage、Cloud 三层拒绝、等待/取消/未知恢复
未发现另外独立 P0/P1/P2。两 P1 是 Spec 和可信边界问题，未用 passing tests 降级。

原 Ollama generation/messages/schema 及 cloud helper 没有改动；新增旧 authorization
拒绝新 wire，未注册真实 transport 或发资格。Schema/runtime composition/Save/
Topic writers/source_authority 字节不变；新 preparation JSON 与实际脚本/code hashes
精确相同、inputs_frozen=false、execution_authority=NONE、production_qualified=false。
前端只接受内部 Content/Evidence identity 再由现 DTO 恢复位置；旧 Detail keyed ID、
useRemote late-result guard 保留，URL 不供应 offsets/timestamps。根与候选共同祖先
是 fixed base；root 当前已接受的 native/provider 修改与本差异无产品文件重叠。

### 独立实际检查

- 原 handoff 的九文件受影响后端命令原样独立执行：**333 PASS /223.89s**，
  `/tmp/local-text-review-tests.log`；含本地 text/timed、旧 wire/reservation/read/save、
  ordinary Ollama/dispatch。完整全后端仍属于 root 最终验收，不冒充已跑。
- `npm test -- --run`：**446 PASS /27 files /11.90s**，
  `/tmp/local-text-review-frontend.log`；旧 act warnings 保留，没有删 skip/assertions。
- `npm run typecheck`、`npm run build`：PASS，build 508ms，
  `/tmp/local-text-review-typescript.log` 与 `/tmp/local-text-review-build.log`。
- 四 source 与准备脚本 py_compile、`ruff check src tests scripts`、
  `PYTHONPATH=src:. python -m mypy --strict src scripts/prepare_readiness_local_text.py`
  **103 source files PASS**；`/tmp/local-text-review-mypy.log`。
- AST/旧 wire/cloud 函数/Schema/runtime/save/topic/source authority 与 preparation freeze
  exact hashes 比较 PASS，`/tmp/local-text-review-invariance.log`；diff check PASS。
- 首历史反证尝试直接使用未 resolve 的 macOS tempfile，正常 DATA NOFOLLOW 边界
  拒绝 `/var` symlink，`NotADirectoryError: 'var'`，日志
  `/tmp/local-text-review-history-probe.log`。仅修正临时脚本根 `.resolve()` 后才得到
  有效反证，不修改业务或弱化边界；保留原失败输出，不作为产品缺陷。

两 P1 负控为隔离人工损坏/fixture，未读取 private thinking/真实模型结果，没有
真实 GUI 或资格宣称。原四例/6144真实语义 FAIL 和 LOCAL8 BLOCKED 保持。Reviewer
结论 **REJECT / P0=0 / P1=2 / P2=0**；退回原实现者，交接提交后 STOP。


## 2026-10-15 Implementer repair handoff — Schema 39

This section supersedes the original implementation's v1/no-migration claims.
The original independent REJECT and its evidence above remain unchanged.

- Repair base: `3b562c64ebca70bb49bdc67b1f20ee96b766ed99`.
- Specific approval: root `74a5795`,
  `LOCAL_TEXT_INPUT_PROOF_MIGRATION_PROPOSAL.md`, human answer
  “批准该精确隔离迁移与验收范围” (`call_37d985304ad94a94b581ed1e53765c44`).
  Governance files were read from root; none were cherry-picked or edited here.
- Parent clarified legacy restore: existing 34–37 package validation/staging/
  activation stays original; normal startup executes existing continuous
  035–038 SQL then additive 039. A 38 image needs only 039. No sparse lineage,
  stage upgrade, activation modification or old migration rewrite was added.
- Author remains Implementer, independent review/acceptance pending. Exact repair
  commit SHA is delivered in chat. No self-approval or main integration.

### Delivered repair

Additive `039_add_local_text_input_proofs.sql` has exactly the approved 15 fields,
real FKs, version constants, lowercase SHA256/UTC/combined 512 KiB UTF-8 checks,
source/video indexes, immutable UPDATE/DELETE triggers and source-bound reserved
INSERT checks including real Evidence/preference IDs. Existing tables/rows and
DATA are not rewritten by 039. Runtime doctor expects 39; backup still accepts
original 34–38 packages using their own original manifest/data contracts.

Checkpoint + typed proof are inserted in one BEGIN IMMEDIATE before dispatch,
with current source/Summary/Evidence/policy/preferences/display metadata rechecked.
Any failed proof validation rolls both back, including after existing successful
work; no truncation or invented history is used. Explicit v2 seals complete input
and context: full excerpts/ranges/hashes, original display metadata/language,
original preference rows and both immutable policy revisions/effective settings,
precise profile/model/digest/prompt/schema/think/options, original Summary identity/
hash/language/producer, original Summary Evidence and deterministic reconstruction.
Proof hash binds all projections and row identity. No new DATA file is introduced.

Historical verification reads specified original Summary bytes, checks artifact
identity/hash, resolves its original references, rebuilds the original deterministic
AnalysisResult/request hash and rehashes complete input/context against immutable
original policy/preference records. It never trusts opaque ID hashes alone or
compares the admitted old context to the latest presentation. Legal later Summary,
policy and preference changes preserve history; original byte/reference damage
closes current/current-card/recorded-card/Save/saved-list/Topic trusted reads.

Public read_current classifies LOCAL TEXT using exact durable revision/execution
or persisted card membership rather than a nullable card projection getter. It
then calls the same card/proof/execution/ledger/hash validator. Missing proof,
card or ledger cannot downgrade to a generic read. Generic non-card revisions
without a distillation association remain readable; old YouTube v5/timed identity,
hash, receipt/eligibility and reader behavior retain their existing algorithms.
Unpublished local text v1 is not backfilled or silently authorized.

Admission/NO_NEW preserve existing current CAS, budget, source guards and unknown
rules, additionally revalidating the full proof. Schema 39 backup verifies every
proof and exact execution/ledger/result binding, including canceled/UNKNOWN/NO_NEW
and successful cards. Cancellation reuses its immutable zero-call receipt while
preserving the original WAITING_MODEL ledger. New text readers explicitly close
SQLite read connections so staged validation cannot leave unmanifested WAL/SHM.
Restore allowlists/integrity/file/hash gates are unchanged.

Prepare-only harness now records independent v2; original V1 preparation evidence
is preserved and a new `LOCAL_TEXT_PREPARATION_PROFILE_V2.json` records exact
current code hashes. Verification confirmed real_model_calls=0,
production_qualified=false, execution_authority=NONE, inputs_frozen=false. Original
four-case model qualification remains FAIL; real LOCAL8 remains BLOCKED. Positive
outputs throughout these checks are explicitly offline fixture transports.

### Checks and retained failure evidence

All commands used this worktree's `PYTHONPATH=src:.` and existing shared .venv;
no installation or toolchain/configuration change occurred.

| Check | Actual result / evidence |
|---|---|
| Two P1 TDD, before repair | `pytest -q tests/integration/test_local_intelligence_text.py -k 'missing_card_projection or history_keeps'`: 2 failed, 1 passed; both `Failed: DID NOT RAISE IntelligenceReadRejected` at original Summary damage and nullable card getter. |
| Original LOCAL slice | 64 passed; expanded missing proof/card/ledger adds recorded/current/direct Save/list/Topic negatives. |
| LOCAL/timed/Backup/retained-schema/state-store cohort | 292 passed, 1 intentional duplicate-zip fixture warning, 320.34s. |
| Related reader/distillation/reservation/saved/topic/old transport cohort | 364 passed, 3 failed initially, 294.19s. Two failures were exact migration-tail expectations after adding 039; one genuine positive restore failed `Restore staging contains unmanifested files` due SQLite context not closing. All three fixed and rechecked below. `.var/local-text-repair/affected-checks.log`. |
| Other 22 latest-schema affected test files | 430 passed, 3 failed initially, 189.42s. Only stale latest-name/tail-size expectations; update preserves exact full migration tail plus 039. Focused all three rechecks: 3 passed, 1.66s. `.var/local-text-repair/additional-checks.log` and `schema-expectation-rechecks.log`. |
| Proof/doctor cohort | 31 passed, 21.16s; exact 15 fields/FKs, immutable triggers, atomic mixed rollback, migration-39 rollback preserving all 38 domain rows/DATA, old 34–38 full-table/DATA restore then ordinary 39 startup, cancellation/UNKNOWN restore/restart, original preference/policy history, generic LOCAL non-card and future-version rejection. |
| Forged backup negatives | 4 passed, 12 deselected, 9.16s. Rehashed DB + original valid ZIP metadata cannot hide missing proof/card/ledger or damaged projection; rejection before any live replacement. First fixture attempt had ZIP special-file attributes; next retained uncheckpointed test WAL. Mechanism corrected with original ZipInfo and explicit checkpoint/DELETE-mode/close on isolated forged DB, preserving the strict expected proof error. Failed evidence: `forged-checks.log`; passing: `forged-checks-after-checkpoint.log`. |
| Final LOCAL + proof + both exact migration-tail rechecks | **85 passed**, 144.05s, including real positive Save/Topic/BackupRestore all tables/DATA equality, two original P1 negatives/all trusted entries, missing-proof/card/ledger and legal Summary refresh. `.var/local-text-repair/final-local-checks.log`. |
| Real UTF-8 overflow negative | **1 passed**, 16 deselected, 1.29s; 40 real persisted preferences each within existing 2048-character bound cause full UTF-8 projection >512 KiB; fails before checkpoint/dispatch with all tables/DATA unchanged. `bounded-checks.log`. |
| Syntax | `python -m compileall -q src/youtube_intel scripts/prepare_readiness_local_text.py` PASS, plus changed new test syntax checked before running. |
| Ruff | `ruff check src/youtube_intel tests scripts/prepare_readiness_local_text.py` PASS. |
| Strict types | `mypy --strict src/youtube_intel scripts/prepare_readiness_local_text.py`: **103 source files PASS**. |
| Prepare freeze | Every recorded source hash independently recomputed; exact v2 + zero calls/qualified false/authority NONE PASS. |
| Diff hygiene | `git diff --check` PASS; production changes only approved state/distillation/reader/backup_restore/runtime/039, preparation harness/freeze/contract/handoff; other test edits only latest schema expectations/exact migration-list append and preserved m038 fault targeting. |

Additional setup mistakes were resolved before substantive checks: initial 039
registration omission (`no such table: local_text_input_proofs`) was corrected in
explicit migration names; wrong imagined unit test filenames gave no-tests exit4
and were replaced with actual existing filenames; one additional-test subprocess
omitted PYTHONPATH and had collection errors, rerun with correct worktree import
path. Cancellation fixture initially selected test-transport, correctly rejected
by existing Ollama-only cancellation authority; fixture now uses unavailable
Ollama with zero calls. These did not weaken production or test constraints.

### Scope, reuse and STOP

DIRECT standard-library JSON/hashlib/SQLite/contextlib, existing Evidence/source
resolver, deterministic Summary/domain models/digest, immutable policy/preferences,
checkpoint/ledger/CAS/cancellation/NO_NEW, ordinary restore/startup migration,
Save/Topic readers. No third-party code or dependency added.

Repair changed no App/frontend/local_api/provider/runtime_composition/analysis,
Save/Topic writers, formal owner data, credentials, production configuration,
qualification receipt or existing migration SQL. No real model, Cloud or external
provider invocation, weights download, deployment or main merge was performed.
Frontend was already STOP and is not rerun by this backend-only repair; root owns
final frontend/GUI/full acceptance. Root's separately reported seven analysis
LeaseConflict failures are outside this repair and were not modified or claimed
fixed. Existing pass counts are cohorts with overlap, not a unique total.

Author delivers limited commit and **STOP**. Independent intel_bounded_review must
reverify exact commit and original P1 probes before acceptance. Final qualification,
ordinary real-model positive Save/Topic and formal adoption remain pending their
existing gates; no production eligibility is granted by this handoff.

## Independent Schema39 re-review — 2026-10-15 — REJECT

Reviewer: independent `local_text_review_resume`, continuing the interrupted
`intel_bounded_review` audit. Reviewed candidate
`2068ee1312c6981f6bd8984554b689a0b38215f7`, cumulative base
`2978550aee692c7b24d5707d2eb4ebdfcc1d0e2f`; original rejection
`3b562c64ebca70bb49bdc67b1f20ee96b766ed99` remains preserved. Read root AGENTS,
COLLABORATION, task/agent package, approved exact Schema39 proposal and continuing
authorization. Graph lookup found no new proof implementation; actual fixed-SHA
source/diff was authoritative. Jev advisory returned HTTP451; review was not
downgraded. No business code, tests, dependencies, configuration, original SQL,
formal data or model eligibility was changed by this review.

### P1 — Losing every association downgrades an explicit text distillation to a generic trusted read

Locations: `src/youtube_intel/intelligence_read.py:158-169` and
`src/youtube_intel/backup_restore.py:1237-1242`.

`read_current` only requires the text-card verifier when a checkpoint or card
still survives. The backup reverse check likewise only enumerates surviving
checkpoints without proofs. If all four associated rows are absent together,
the immutable `intelligence_revisions` row still has interpretation
`DISTILLATION` and the explicit
`revision:distillation:distillation:local-text-v2:<input>:<context>:<identity>`
identity, with its Evidence/dependency graph intact, but neither gate discovers
it. Its admitted text card no longer exists and its historical input cannot be
verified, yet direct current/Save/Topic issue or consume a trusted read. A forged
Schema39 package containing that orphan revision also passes stage validation.
This violates the approved missing-proof/card/ledger fail-closed requirement;
passing one-row deletion controls is insufficient.

Fresh independent reproduction (exit0):

```text
PYTHONPATH=src:.:tests .venv/bin/python /tmp/local-text39-review-missing-associations.py
All4 associations removed only in forged copy; original immutable schema triggers restored; FK/integrity [('ok',)]
Remaining revision [... 'DISTILLATION', 'EVIDENCE_BACKED_STATEMENT']
FORGED all-association-loss archive ACCEPTED: dc4a3ca82872412d8c65ac5dc341be4c
CLOSED: current-card IntelligenceReadRejected distillation card is unavailable
FORGED association-loss ACCEPTED: current
FORGED association-loss ACCEPTED: save
FORGED association-loss ACCEPTED: topic
```

Probe starts with a real offline-fixture admitted text result and its normal
backup. Only in a private copied backup database, it removes rows from
`local_text_input_proofs`, `distillation_cards`, `distillation_resource_usage`,
and `distillation_execution_checkpoints`, temporarily dropping and then restoring
each table's exact original triggers. It checks foreign keys/integrity, commits,
checkpoints WAL, switches DELETE journal mode and closes before reading bytes.
It updates the manifest's DB SHA256/size and retains every original ZipInfo;
therefore the rejection is not masked by ZIP metadata, dirty WAL or manifest
corruption. It stages but never activates the forged archive. Direct readers
use that isolated forged DB with the original private fixture DATA. Real model,
Cloud and network calls: zero; fixture generation: one. Script and outputs are
preserved in `/tmp/local-text39-review-missing-associations.py`,
`/tmp/local-text39-review-missing-associations.log` (pre-interruption) and
`/tmp/local-text39-review-resume-associations.log` (fresh confirmation).

Required repair: discover explicit LOCAL_TEXT distillation revisions independently
of optional surviving sidecar rows, and reject missing exact associations at both
trusted-read and backup validation boundaries. Preserve legal generic non-card
revisions and old YouTube/timed behavior. Add the combined-loss negative alongside
the individual-loss controls; retain exact immutable schema and full restore
guards. No schema expansion is requested by this finding.

### Verified controls and evidence

- Fresh `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_local_text_input_proof.py`:
  **17 passed in 27.02s**, exit0, `/tmp/local-text39-review-resume-proof.log`.
  Includes exact15-field/FK/immutable schema, atomic mixed rollback, failed039
  rollback, old34–38 original restore then normal startup39/all-domain-row/DATA
  equality, cancel/UNKNOWN restart, immutable policy/preferences history, generic
  revision positive, individual proof/card/ledger/projection forged archives,
  and real UTF-8 overflow rejection. These passing tests do not close the P1 above.
- Fresh original historical-summary probe, explicitly calling the evolved
  fixture with `damage_original=False`: legal later Summary refresh PASS; after
  only original Summary bytes are corrupted, current-card, recorded-card,
  current, Save and Topic all CLOSED. Exit0,
  `/tmp/local-text39-review-resume-history.log`; script
  `/tmp/local-text39-independent-history-probe.py`. Original signature TypeError
  is retained in `/tmp/local-text39-review-original-history.log`, not relabelled PASS.
- Fresh nullable-card getter projection probe: current-card/current/Save/Topic
  CLOSED; no saved relation minted. Exit0,
  `/tmp/local-text39-review-resume-card.log`; original script
  `/tmp/local-text-review-missing-card-probe.py`. Original two P1 are repaired.
- Recovered completed independent cohorts: `/tmp/local-text39-review-core.log`
  **309 passed, one intentional duplicate-ZIP warning, 356.06s**;
  `/tmp/local-text39-review-related.log` **254 passed, 131.31s**. No related pytest
  process remained when resuming. Preserve actual 254, not an estimated ~286;
  overlapping cohorts are not a unique total.
- Preserved independent strict type output
  `/tmp/local-text39-review-mypy.log`: **103 source files PASS**. Prior syntax/Ruff
  evidence from the interrupted audit remains unchanged; fresh `git diff --check`
  PASS. No repeated hours-long cohort was necessary after the confirmed blocker.
- Reviewed latest-schema assertions append exact039 and extend full migration
  tails rather than relaxing them; old explicit migration fixtures remain.
  Preparation V2 records zero real calls, qualification false and authority NONE;
  Schema39 does not grant model eligibility. Final full backend/frontend, actual
  GUI, model semantic qualification and root integration remain root gates.

Verdict: **REJECT**, one open P1, no additional P0/P2 finding asserted. Return to
the original implementer for the bounded repair and independent re-review. This
commit changes only this handoff. Reviewer **STOP**; no acceptance or integration.

## Implementer association-loss repair — 2026-10-15

Repair starts at independent REJECT `b2aebad7ba54cf0a6acc29db2fe9637609c8042b`
on the original task branch/worktree. All prior implementation/rejection commits
remain in history. Scope is reader/Backup validation, the matching proof tests,
contract and this handoff plus a new preparation snapshot. No Schema/SQL, state,
App/UI, runtime/provider, config, dependency, owner, qualification or network
change. Continuing authorization and the exact 15-field proposal/startup
clarification were read from the orchestrator worktree. Graph lookup was stale
for this implementation; exact fixed-SHA source/diff was used. Jev routing was
unavailable (HTTP451); strong/default reasoning and independent review retained.

Reuse DIRECT existing authoritative current/recorded card readers, exact v2
execution/proof/ledger verifier, SQLite and ZIP/hash restore guards. The reserved
`revision:distillation:distillation:local-text-v<decimal version>:` identity now
independently requires strict card validation. It grants no authority and does
not try alternative hashes. Unknown future versions cannot become generic.
The text verifier also requires the exact generated revision/execution identity.
Backup traverses all produced revisions through the shared classifier and
recorded-card reader, including results whose four associations disappeared.
Ordinary generic identities (including incidental/non-version lookalikes) retain
their original behavior. No new dependency or third-party source was needed.

Regression fixtures retain every original ZIP entry's ZipInfo, rehash DB/manifest,
checkpoint and close SQLite, restore exact immutable triggers and assert FK plus
integrity before actual stage validation. Eleven association-loss combinations
plus the original projection damage cover stage and reopened current/current-card/
recorded-card/Save/saved-list/Topic. When a ledger survives, its FK requires its
checkpoint row: those two cases remove only the checkpoint's result association,
using a terminal non-ambiguous status with NULL result IDs; the original all-four
probe still deletes all four rows. Future v2/v3/v999 identities with no sidecars
also exercise actual rehashed stage. Strict expected proof-error assertions and
live all-table/DATA equality remain, with no unknown-file guard weakened.

Evidence preserved, including failed attempts:

- TDD RED: `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_local_text_input_proof.py -k 'proof+card+ledger+checkpoint'`:
  **1 failed**, `Failed: DID NOT RAISE BackupRestoreError` at actual stage,
  `/tmp/local-text39-association-red.log`.
- Direct/future RED: same module `-k explicit_text_revision`: **3 failed**,
  `Failed: DID NOT RAISE IntelligenceReadRejected`, v2/v3/v999 current reads,
  `/tmp/local-text39-future-red.log`.
- Initial expanded proof run: **26 passed, 2 failed**, both newly added fixture
  combinations attempted to delete a checkpoint still referenced by its retained
  ledger; `sqlite3.IntegrityError: FOREIGN KEY constraint failed`,
  `/tmp/local-text39-association-proof.log`. The already-started overlapping run
  was deliberately interrupted before repeating this failure: **18 passed,
  KeyboardInterrupt**, `/tmp/local-text39-association-local.log` (not PASS).
- The first association-only fixture used AMBIGUOUS and correctly hit the earlier
  ledger consistency guard: **3 passed, 2 failed**, expected proof error versus
  `An ambiguous distillation resource record failed validation.`,
  `/tmp/local-text39-association-fixture-fix.log`. The fixture was corrected to the
  non-ambiguous terminal association-loss case above, rather than weakening the
  expected error. Focused rerun: **2 passed**, 7.40s,
  `/tmp/local-text39-association-fixture-closed.log`.
- Original independent external probe rerun:
  `PYTHONPATH=src:.:tests .venv/bin/python /tmp/local-text39-review-missing-associations.py`:
  exit0, FK/integrity `ok`; archive CLOSED with
  `Local text input proof failed validation.`, current-card/current/Save CLOSED
  with `distillation card is unavailable`, Topic CLOSED; one offline fixture
  generation, zero real model/network calls. Preserved output:
  `/tmp/local-text39-association-original-probe.log`.
- Related `pytest -q` cohort: `tests/unit/test_backup_restore.py`,
  `tests/integration/test_task019_trusted_intelligence_read.py`,
  `tests/integration/test_local_intelligence_timed.py`,
  `tests/integration/test_task025a_saved_intelligence.py`,
  `tests/integration/test_task023_topic_timeline.py`: **180 passed**, one intentional
  duplicate-ZIP fixture warning, 91.27s,
  `/tmp/local-text39-association-related.log`.
- `ruff check src/youtube_intel tests scripts/prepare_readiness_local_text.py`:
  PASS, `/tmp/local-text39-association-ruff.log`.
- `mypy --strict src scripts/prepare_readiness_local_text.py`: **103 source files
  PASS**, `/tmp/local-text39-association-mypy103.log`. Initial src-only run was
  102 files; it is not misreported as the complete harness check.
- `compileall -q src/youtube_intel scripts/prepare_readiness_local_text.py tests/integration/test_local_text_input_proof.py`:
  PASS. Syntax/type errors were checked before test debugging. `git diff --check`
  PASS; diff inspection confirms no migration/state/frontend/dependency edits.
- Exclusive preparation output `LOCAL_TEXT_PREPARATION_PROFILE_V3.json` has all
  recorded source hashes recomputed successfully; unchanged v2 wire/profile,
  inputs not frozen, qualification false, real calls0, authority NONE. Historical
  V1/V2 files preserved.

Final `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_local_text_input_proof.py tests/integration/test_local_intelligence_text.py`:
**97 passed in 183.69s**, `/tmp/local-text39-association-final-local.log`.
Includes all expanded actual-stage/direct negatives, the two original P1s,
legal Summary refresh and policy/preferences history, ordinary generic controls,
Schema39 Save/Topic/new-backup activation/restart with all-domain-table/DATA
equality, original34–38 restore/activation then continuous normal startup39,
exact fifteen-field/immutable schema, atomic rollback, cancellation/raw WAITING
ledger receipt, UNKNOWN restart/no redispatch, NO_NEW, Cloud zero-dispatch and
Unicode bounds. No tests skipped, removed or weakened.

Prior independent
309/254 cohorts remain evidence for the previous candidate; they were not rerun
or relabelled for this repair. Root final full backend/frontend, actual GUI,
semantic model qualification and formal adoption remain separate gates. Author
delivers a bounded commit and **STOP** for independent re-review; no acceptance,
integration, public task-status update or qualification grant is claimed.

## Independent final association re-review — 2026-10-15 — APPROVE

Reviewer `local_text_review_resume`; exact candidate
`5909ef7427491a09493efbdf8966a6264407de73`, repair diff against previous independent
REJECT `b2aebad7ba54cf0a6acc29db2fe9637609c8042b`; cumulative original base remains
`2978550aee692c7b24d5707d2eb4ebdfcc1d0e2f`. Original failures and rejections above
remain history. Six-path repair has no state, migration/Schema, frontend,
dependency, configuration, eligibility or owner-data change. Reviewer modified
only this handoff after author clean STOP.

The remaining P1 is closed. `intelligence_read.py:41-44,159-186` independently
recognizes the reserved decimal-version text revision family, even without
sidecars; this is a requirement to validate, never an authority grant.
`335-343` requires the supported exact v2 execution and its exact generated
revision identity. Unknown versions fail closed. `backup_restore.py:1243-1250`
reverse-checks produced revisions with the same classifier and recorded-card
verifier, while preserving the existing forward proof/result checks. Ordinary
generic and near-marker identities retain their legal behavior. No alternate
hash guessing, new storage field or weakened restore guard was introduced.

Independent verification on this exact candidate:

- Original external all-four-loss replay:
  `PYTHONPATH=src:.:tests .venv/bin/python /tmp/local-text39-review-missing-associations.py`,
  exit0, `/tmp/local-text39-final-review-original-associations.log`. Original
  schema/triggers restored, FK/integrity `ok`, checkpointed/rehashed DB and
  original valid ZipInfo. Actual stage now CLOSED with
  `BackupRestoreError Local text input proof failed validation.`;
  current-card/current/Save CLOSED with `distillation card is unavailable`;
  Topic CLOSED. Private fixture only, no activation, real model/network0.
- `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_local_text_input_proof.py tests/integration/test_local_intelligence_text.py`:
  **97 passed in 173.19s**, exit0,
  `/tmp/local-text39-final-review-local97.log`. Independently covers all expanded
  association combinations in actual rehashed archives and reopened direct
  current/current-card/recorded-card/Save/saved-list/Topic; v2/v3/v999 no-sidecar
  markers; ordinary and incidental/non-version generic positives; the original
  missing-card projection and historical Summary damage negatives; legal later
  Summary refresh; cancellation preserving raw WAITING ledger receipt; UNKNOWN
  and NO_NEW; exact fifteen-field/immutable schema, atomic mixed rollback,
  old34–38 restore/activation followed by ordinary continuous startup39, and
  Schema39 positive full-domain-table/DATA restore/restart equality.
- `PYTHONPATH=src:. .venv/bin/python -m compileall -q src/youtube_intel scripts/prepare_readiness_local_text.py tests/integration/test_local_text_input_proof.py`:
  PASS, exit0.
- `.venv/bin/ruff check src/youtube_intel tests scripts/prepare_readiness_local_text.py`:
  PASS, `/tmp/local-text39-final-review-ruff.log`, exit0.
- `PYTHONPATH=src:. .venv/bin/mypy --strict src scripts/prepare_readiness_local_text.py`:
  **103 source files PASS**, `/tmp/local-text39-final-review-mypy.log`, exit0.
- Independently invoked prepare-only `prepare_profile()` and compared its whole
  output with committed V3, recomputed every recorded source SHA256 and checked
  V1/V2 byte equality against previous review commit: PASS. Unchanged v2 profile,
  real calls0, production qualification false, authority NONE, inputs not frozen.
- `git diff --check` PASS. Reviewed changed tests: added exact stage-error and
  trust-rejection assertions; the FK-preserving partial-checkpoint fixture is
  explicitly distinguished from the original all-four deletion. No removed/
  skipped/weakened security assertion or unrelated source edit.

Prior independent 309/254 cohorts and original 17-proof results belong to their
recorded candidates and are not relabelled or aggregated as unique tests for
this repair. The fresh97 cohort is the bounded high-risk rerun; author180-related
is preserved as author evidence. Full root backend/frontend and real GUI are
still root acceptance gates, not asserted here. Real-model semantic qualification
and formal eligibility remain closed under their existing requirements.

Verdict **APPROVE**: no open P0/P1/P2 found in this review; original two P1 plus
the all-association-loss P1 now have passing independent negative/positive
controls. Handoff-only review commit, clean **STOP**. Root owns acceptance,
integration and final product validation; this review grants no model execution.
