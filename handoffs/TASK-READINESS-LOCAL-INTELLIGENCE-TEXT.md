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
