# TASK-016C 交接报告

## Phase F accepted-equivalent integration 与 Phase G discovery

- Current Phase G baseline：`2f6e30bd4720e76a72783974704e8e975b6f60c0`，tracked worktree clean。
- 用户已授权把 conflict-free cherry-pick 的线性 integration equivalents 视为 Phase F 的 accepted
  implementation history：`c0268a… -> 61bb0bb…`、`df920cc… -> d059bea…`、
  `931674e… -> 2f6e30b…`。三组 tree/content diff 均为空；不要求 original source SHA 成为
  current HEAD ancestor，严禁 rewrite/rebase/squash/amend 以恢复原 SHA。
- Phase D `2c11faf…` 与 Phase E `9b92946…` 均已核验为当前 HEAD ancestor；Phase F 状态更新为
  `APPROVED`。Phase G design/control-plane 已完成，状态为 `READY / AUTHORIZED / IMPLEMENTATION NOT STARTED`。
- Discovery 事实：legacy `RepositoryBackedScoringService` 在 provider call 前持久化 reserve，随后直接
  写 raw/structured files，最后由 `complete_stage()` 的一笔 SQLite transaction 登记 Artifact、完成 call、
  更新 score/stage/job；它没有 tmp/fsync/promote protocol，filesystem 与 SQLite 不跨资源原子。
- 设计发现并关闭：当前 Phase F success 未保存完整 ScoringInput/quality PASS/attestation evidence，无法在
  “G only accepts success”条件下重验 trusted provenance。G 将最小 enrich 同一 sealed aggregate，以
  canonical bytes/hashes 封存该 evidence；不得以 caller DTO 补信任。
- G future normal path：`primary_attempt -> run_primary_trusted_scoring -> enriched success -> PREWRITE_VALIDATE
  -> ValidatedScoringWritePlan -> verified tmp/promote -> one atomic SQLite registration`。G 不得在 prewrite
  前 reserve/write/cache/stage，不得 provider/Judge recall；repair/recovery/cache verification 仍分别属于 H/I。
- Design authority：[Phase G Amendment](../docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md)。
- 本条仅为 control-plane discovery；未实施 Phase G、未运行真实 provider/network、未写 DB/filesystem。

## Phase F Implementation Authorization（历史控制面；当前状态由上方 integration 条目 supersede）

- Historical status at `acdaac1…`: `READY / AUTHORIZED / IMPLEMENTATION NOT STARTED`。该授权随后已经
  accepted-equivalent linear integration 实施并 APPROVED；本段仅保留历史上下文。
- Authority: `agent-prompts/TASK-016C-PHASE-F-IMPLEMENTATION-AUTHORIZATION.md`、
  `agent-prompts/TASK-016C-PHASE-F-IMPLEMENTER-WORKBUDDY.md` 与
  `docs/TASK-016C-PHASE-F-HANDOFF-CHECKLIST.md`。实现必须是本控制面提交和 Round 4 accepted design
  `e00f957…` 的 descendant，禁止 squash/rebase/history rewrite。
- 唯一阶段顺序已冻结：F=PRIMARY-only、candidate-only 的 non-production in-memory seam；
  G=pre-write validation + persistence registration + production cutover；H=repair/retry/recovery/
  budget；I=derived cache verification/recovery + production hardening/release acceptance。旧 J/K
  验收标签并入 I，不存在 capability 双重归属。
- 兼容生产链 `RuntimeOperations → RepositoryBackedScoringService → bare ScoreResult → persistence`
  仍是 `PRE-TASK-016C COMPATIBILITY PATH`，不能被称为 trusted path；Phase F 不改 default
  dispatch。F future seam 必须 exact-type 拒绝 bare ScoreResult、Mapping、JSON 和 legacy output，
  但不实例化/调用 RepositoryBackedScoringService。G 才可在 persistence boundary 后授权 cutover。
- Finalizer 输出合同已统一为 `TrustedScoringFinalizer -> TrustedScoreResult`。wrapper 内部保留
  已验证的 ScoreResult 业务字段；bare ScoreResult 只可位于 `LEGACY / EXTERNAL COMPATIBILITY
  BOUNDARY`。Phase F-G-H 不授权 internal unwrap。
- F 不拥有 repair/retry/budget/recovery：PRIMARY 任一步失败即 fail-closed，不能自动 repair；
  repair 的 operation identity 与未知 reservation recovery 都留给 H。
- F→G continuation 已冻结为内存 `PrimaryScoringAttempt`：它绑定既有 canonical scoring request
  identity、canonical candidate identity、`raw_response_hash = SHA-256(exact raw UTF-8 bytes)`、provider/model/
  digest、`PRIMARY` role 和唯一权威的 bounded UTF-8 decoded 完整 Provider HTTP JSON raw string。F/G 必须复用
  同一 pure canonical candidate parser，形成 `raw -> parser-derived candidate -> candidate hash -> Finalizer`
  的不可拆分语义链，故 raw A 与 candidate B 不能拼接通过。F 成功只输出
  `PhaseFTrustedScoringSuccess(TrustedScoreResult, PrimaryScoringAttempt)`；attempt 不可信、不可持久化、
  不可恢复且不授权任何写入。G 只能消费该 aggregate 的 raw source，必须按 request/raw hash/same-parser
  reparse/candidate hash/result/attestation 重新交叉验证；不得 provider recall、caller/cache/legacy raw substitution 或用 result
  反向重建 raw。
- 未执行：Phase F–I 代码、Provider/网络、持久化、cache、DB、Artifact、merge 或 history rewrite。

### Round 4 design provenance

- Phase F Runtime Integration Amendment Round 4 已以 `e00f957…` 获独立设计批准：它冻结 exact raw-body hash、
  shared canonical parser 与 F/G raw→candidate revalidation；本授权不改变该设计或扩大 Phase G–I。

## Phase E 实现交接

- Status: `IN_REVIEW`；仅实现纯内存 Trusted Finalizer，尚未进入 Phase F 或持久化。
- Base: `2c11faf41e17c3b823a39bfd1018c5c876b236c5`（Phase D 已批准）；Phase E control-plane
  authorization: `8aa9f0bb99d6c83250407d53bbb63eb909da0212`。
- 目标：建立 runtime-only `TrustedScoringContext`、唯一 canonical scoring request identity、
  `TrustedScoreResult` opaque wrapper 与无副作用 `TrustedScoringFinalizer`。
- 实际修改：
  - `src/youtube_intel/scoring.py`：抽取 `build_scoring_request_identity()`；
    `build_scoring_input()` 与 Repository-backed `_provider_request()` 均复用该纯函数，
    保持既有 request hash 行为。
  - `src/youtube_intel/runtime.py`：仅从已验证的 `AppConfig` 通过 `RuntimeOperations`
    铸造 `TrustedScoringContext`；LocalScoringSettings、Mapping、JSON、Provider、cache 和
    Artifact 均不能单独铸造 capability。
  - `src/youtube_intel/quality.py`：增加 exact-type、private-sentinel、不可复制/序列化/
    子类化的 Context 和 Result wrapper；Finalizer 先检查 capabilities，再重建所有
    不可信 DTO，重算 scoring identity，交叉验证 candidate/quality/attestation provenance，
    最后才创建 `TrustedScoreResult`。
  - `tests/unit/test_task016c_finalizer.py`：覆盖 hash compatibility、真实 Runtime
    authority chain、PASS 最终化、candidate hash 篡改、Mapping capability spoof 与 capability
    直接构造/复制/pickle/subclass 拒绝。
- 明确未做：Provider/Ollama 调用、repair orchestration、ProviderCall、Artifact、cache、
  filesystem、SQLite、migration、依赖或网络调用；Phase F–I 未启动。

### TDD 与验证证据

- RED：新增 Finalizer 端到端测试先因 `TrustedScoringFinalizer` 尚不存在而 collection
  ImportError；canonical identity 测试也先因 builder 不存在而 ImportError。
- GREEN：焦点 finalizer 测试 `3 passed`；与已有 scoring/attestation 回归组合 `159 passed`。
- 全量：`uv lock --check` → PASS；`uv sync --locked --offline` → PASS（84 packages checked）；
  `uv run pytest -x -q` → `1174 passed, 1 warning`；`uv run mypy src` → 28 source files PASS；
  `uv run ruff check .` → PASS；`uv build --offline` → sdist/wheel PASS；
  `bash scripts/security_scan.sh` → `status=clean`（已有非阻断 WARN 与项目 LICENSE unresolved
  warning）；`git diff --check` → PASS。
- 剩余风险：Phase E 只证明内存内 trust/provenance binding。尚未授权/实现 artifact file
  commit、atomic persistence、cache recovery、retry/recovery 或真实模型验证。

### Phase E Correction 1（主控独立式审查发现）

- P1：`TrustedScoringContext` 与 `TrustedScoreResult` 初版可通过普通 attribute assignment
  改写 private slot，破坏 opaque capability 的运行时不可变性。
- RED：`test_finalizer_accepts_only_runtime_bound_pass_material` 在尝试写入 Context language
  时复现 `Failed: DID NOT RAISE TypeError`。
- 修复：两个 wrapper 增加 sealed slot 与 fail-closed `__setattr__`；私有构造仍先使用
  sentinel，实例完成初始化后拒绝任何普通属性赋值。
- GREEN：Phase E focused `3 passed`；修正后重新执行 `uv lock --check`、
  `uv sync --locked --offline`、全量 pytest（`1174 passed, 1 warning`）、`mypy src`
  （28 files）、Ruff、offline build、security scan 与 diff check，均通过。

### Phase E 主控独立式最终复核

- Verdict: `APPROVE`；P0=0、P1=0、P2=0、P3=0。
- Git/范围：`2c11faf` 为 HEAD ancestor；implementation+correction 相对
  `8aa9f0b` 精确为 5 条授权路径（quality/runtime/scoring、Phase E test、handoff）；
  `git diff --check` 通过，worktree clean。
- 信任边界：RuntimeOperations 是唯一 production Context minting path；Finalizer 在读取
  capability 字段前执行 exact-type 验证，重建每个外来 DTO、重算 canonical request
  identity、验证 candidate/quality/attestation 交叉绑定，并只返回 opaque wrapper。
- 对抗覆盖：直接构造、subclass、copy/deepcopy、pickle、普通 slot mutation、Mapping
  capability spoof 和 candidate hash 篡改均 fail-closed；没有 ProviderCall、cache、Artifact
  或 filesystem 副作用。
- 检查复核：lock/offline sync、focused 3、scoring+attestation 159、full pytest 1174、
  mypy 28、Ruff、offline build、security scan clean 与 diff check 均通过；未运行网络、
  实际模型、云、数据库 migration 或 Phase F–I。

## Phase E control-plane authorization

- Status: `READY / AUTHORIZED`；implementation 尚未开始。
- Phase D baseline: `2c11faf41e17c3b823a39bfd1018c5c876b236c5`。
- Authority: `docs/TASK-016C-PHASE-E-AUTHORITY-AMENDMENT-ROUND-3.md`、
  `tasks/TASK-016C-PHASE-E-trusted-scoring-finalizer.md` 与
  `agent-prompts/TASK-016C-PHASE-E-IMPLEMENTER-CODEX.md`。
- 本控制面不含 production/test/dependency 变更；Phase E only，Phase F–K 保持未授权。

## 元数据

- Task: `TASK-016C Phase A`
- Role: `Implementer (Correction Round 1)`
- Agent/session: `WorkBuddy`
- Accepted design baseline: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- Original Phase A implementation commit: `cd9d8b2c41a130aadfc828559d537611f341850a`
- Correction Round 1 commit: `e9ffe699c52d1c2f4a20f9322df3c5eb445b1cf5`
- Correction Round 1.1 commit: `e8ccc2d9e3b348d23942450b3f99861cdbc25aa3`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

### Git 事实澄清

- `5ddc5f66c42433097e04f3d7adbb86fec61126dd` 是旧 handoff 元数据中的错误 base，不是 Phase A implementation base。
- `0b78787d9cbc7bd253e150c6ba6a13100ea9a955` 是 accepted-design baseline `c547b7c...` 的 sibling control-plane 子节点，用于冻结设计状态与任务卡；它不是 implementation branch 的 ancestor，本次 correction 未 cherry-pick/merge 该 commit。
- Control-plane history integration 由 Codex / Orchestrator 在 Phase A accepted 后另行处理。

### 设计状态

- Round 4.6 Independent Design Review verdict: `APPROVE FOR IMPLEMENTATION`
- Accepted design SHA: `c547b7c46afbf254979331c2c56cddb93a8503f2`
- 工作树里的 design headers 仍可能显示旧 `PROPOSED / INDEPENDENT DESIGN REVIEW REQUIRED` 文本，这是 control-plane ancestry 问题，不代表设计未批准。

## 目标与范围

- 任务目标：在 `src/youtube_intel/domain.py` 中建立 Content Quality Layer 的领域契约（Phase A），为后续 Deterministic Gate、Local Quality Judge、Finalizer、Attestation 与持久化提供可信输入边界。
- 本次 correction 范围：仅关闭 Codex Independent Review 在 Phase A 中明确列出的 P1/P2 findings。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `tests/unit/test_task016c_domain_contracts.py`
  - `handoffs/TASK-016C.md`
- 实际修改：
  - `src/youtube_intel/domain.py`：修正 `ContentQualityResult` REJECT 矩阵分派；补全 Evidence Registry canonical ordering、uniqueness、count/total-size bound；统一 `ScoringEvidence.evidence_id` 与 `ContentQualityResult.evidence_ids` 的 lexical/length contract。
  - `tests/unit/test_task016c_domain_contracts.py`：新增 26 项 RED-before-GREEN 测试（P1-1 矩阵 11 项、P1-2 registry 8 项、revalidation 2 项，以及 annotation 修复触发的覆盖），总计 59 项；Correction Round 1.1 再补充 1 项独立 total-character 测试与 1 项旧测试缺陷证明，总计 60 项。
  - `handoffs/TASK-016C.md`：修正 base/original/correction SHA、design status、test coverage 与验证结果。
- 明确未做：Deterministic Gate 实现、Local Quality Judge 调用、H1/H2 persistence、Quality PASS Attestation、`TrustedScoringFinalizer`、pre-write validation、`ValidatedScoringWritePlan`、Artifact 文件提交协议、原子 DB 登记、cache recovery、CLI 改动、数据库 migration、新依赖。

## P1-1 矩阵修正

### Gate REJECT

- 实现按 `decision_source` 明确分派：Gate 路径完成 source-specific validation 后不再落入 Local_Judge REJECT matrix。
- 三个 deterministic reason 全部合法：`EMPTY_CONTENT`、`CONTROL_CHARACTER_INVALID`、`EXACT_REPETITION`。
- Gate REJECT 强制：signals 为空、evidence_ids 为空、Judge identity 为空、confidence = HIGH/LOW/LOW。

### Grounding REJECT

- `LOCAL_JUDGE + REJECT + GROUNDING_INSUFFICIENT` 现在合法。
- grounding REJECT 的 usefulness confidence 边界为 `{LOW, MEDIUM, HIGH}`（ frozen matrix ）。
- grounding REJECT 要求 `grounding_confidence == LOW`、包含 `GROUNDING_INSUFFICIENT` signal、不得包含 `GROUNDING_PRESENT`。

### 负向矩阵

- Gate REJECT 使用 Judge-only reason → 拒绝。
- Local Judge REJECT 使用 Gate-only reason → 拒绝。
- UNCERTAIN 使用 deterministic rejection reason → 拒绝。
- PASS 携带 rejection reason → 拒绝。
- source/reason/status 不匹配仍 fail-closed。

## P1-2 Evidence Registry 修正

### Evidence ID 单一 Contract

- `_validate_evidence_identity` 是 `ScoringEvidence.evidence_id` 与 `ContentQualityResult.evidence_ids` 共享的唯一入口。
- 约束：non-empty、无空白-only、最大长度 100。

### Registry Uniqueness

- `ContentQualityInput.evidence_registry` 拒绝重复的 `evidence_id`（fail-closed，不采用 last-write/first-write/silent dedupe）。

### Canonical Ordering

- `ContentQualityInput.evidence_registry` 按 `evidence_id` 字典序稳定排序。
- 语义相同、输入排列不同的 registry 得到相同的 validated representation。

### Registry Bounds

- 条目数上限：100（复用项目既有 registry 模式）。
- 总字符上限：200,000（= 100 × 单条 excerpt 上限 2000，从 frozen per-item limit 推导）。
- 单条上限：`evidence_id` ≤ 100、`excerpt` ≤ 2000（已冻结）。
- Correction Round 1.1 已补充独立 total-character 回归测试，确保 count bound 不掩盖 total bound。

### Registry / Result 分离

- `ContentQualityResult.evidence_ids` 仅复用与 registry 相同的 identity lexical/length contract。
- 未实现 cross-object registry-membership validation（留给后续 Finalizer/Wrapper phase）。

## TDD RED Evidence

Correction 开始时新增测试全部 RED：

- 失败数：17
- 失败类别：
  - Gate REJECT 合法路径被错误拒绝（4 例）
  - grounding REJECT 合法 usefulness 边界被错误拒绝（4 例）
  - Evidence Registry canonical ordering / duplicate / count / total-size 未生效（4 例）
  - `ContentQualityResult.evidence_ids` 长度约束未与 `ScoringEvidence.evidence_id` 对齐（2 例）
  - Gate / grounding REJECT 的 trusted JSON revalidation 失败（2 例）
  - 另有 1 例测试期望去重但实际应拒绝重复，已按 fail-closed 修正测试本身

## Correction Round 1.1：独立 total-character 测试

### 旧测试缺陷

`test_evidence_registry_rejects_total_chars_above_max` 原实现使用 101 条 excerpt 最大长度（2000）的 evidence。该输入已经违反条目数上限（100），因此即使删除总字符上限校验，旧测试仍然会因 count bound 失败，无法独立证明总字符上限存在。

### RED Evidence

新增 `test_evidence_registry_old_total_chars_test_depended_on_count_bound`：

- 构造与原测试相同的 101 条 max-length registry；
- 通过 monkeypatch 将 `_MAX_EVIDENCE_REGISTRY_TOTAL_CHARS` 放大 100 倍，模拟移除总字符上限；
- 验证该输入仍因 "at most 100 items" 被拒绝。

这证明旧测试无法区分 count validation 与 total-character validation。

### GREEN Evidence

新增/替换 `test_evidence_registry_rejects_total_chars_above_max`：

- 使用恰好 100 条 evidence（count 合法，不触发 count bound）；
- 每条 excerpt 取 frozen 单条上限 2000，evidence_id 取最短合法长度；
- 总字符 = 100 × (2000 + 1..3) = 200100+，超过 frozen 总上限 200,000；
- 验证仅因 "total characters" 被拒绝。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| Phase A focused tests (`tests/unit/test_task016c_domain_contracts.py`) | 60 passed |
| TASK-016B language regression (`tests/unit/test_scoring_language.py`) | 101 passed |
| 全量 unit tests (`tests/unit`) | 456 passed |
| 全量 pytest | 912 passed, 2 warnings |
| `uv lock --check` | PASS |
| `uv run ruff check .` | PASS |
| `uv run mypy src` | PASS |
| `uv run youtube-intel --help` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` |
| `git diff --check cd9d8b2..HEAD` | PASS |

## 失败、跳过与风险

- 已解决失败：P1-1 Gate/grounding REJECT 矩阵、P1-2 Evidence Registry contract（含 Correction Round 1.1 独立 total-character 测试）、P2-1 handoff 元数据。
- 剩余风险：
  - Phase A 仍为纯内存 schema/matrix 验证契约，未涉及真实 Ollama、SQLite 持久化、文件提交协议或 cache recovery。
  - Registry 总字符上限 200,000 是从 frozen per-item excerpt limit（2000）与既有项目 registry count pattern（100）推导得出；frozen design 文本中未显式给出总上限数字。
- `DECISION NEEDED`：无（Phase A correction 范围内）。

## 实现者结论

- 建议状态：`IN_REVIEW / CORRECTION ROUND 1 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv run ruff check .
  uv run mypy src
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_scoring_language.py
  uv run pytest -x -q
  uv run youtube-intel --help
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check cd9d8b2..HEAD
  ```

## Reviewer 结论

- Reviewer agent/session：
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1：

## 主控验收

- Orchestrator：
- Verdict：`ACCEPT | REJECT`
- 依据：
- 批准整合的 commit：

## 整合结果

- Integrator：
- 主线 commit：
- 整合后检查：
- 最终状态：`DONE | BLOCKED`

---

# TASK-016C Phase B 交接报告

## 元数据

- Task: `TASK-016C Phase B`
- Role: `Implementer`
- Agent/session: `WorkBuddy`
- Phase B authorization commit: `0f558f36376f3f113e68d1ab7a2e5969aabd0073`
- Phase B implementation commit: `7e5e71d02e9d270a69da9f140d2ff7e7c9a92061`
- Phase B correction round commit: see 实现者结论 below
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`

## 目标与范围

- 任务目标：实现纯本地的 `DeterministicContentQualityGate`，仅覆盖 `EMPTY_CONTENT`、`CONTROL_CHARACTER_INVALID`、`EXACT_REPETITION` 三类 REJECT；所有结构合法但未命中门控的内容返回 `None`，交给后续阶段。
- 允许修改：
  - `src/youtube_intel/quality.py`
  - `tests/unit/test_task016c_quality_gate.py`
  - `handoffs/TASK-016C.md`
- 实际修改（原始 Phase B commit）：
  - `src/youtube_intel/quality.py`：新建 `DeterministicContentQualityGate`，按 raw empty → raw control scan → ASCII-whitespace empty → exact-repetition 顺序分类；结果通过 `ContentQualityResult.model_validate` 构造 DETERMINISTIC_GATE REJECT。
  - `tests/unit/test_task016c_quality_gate.py`：新建 35 项 RED-before-GREEN 测试，覆盖三类 REJECT、边界、结果契约与 mutation killers。
- 明确未做：Local Quality Judge、H1/H2 persistence、Quality PASS Attestation、`TrustedScoringFinalizer`、pre-write validation、`ValidatedScoringWritePlan`、Artifact 文件提交协议、原子 DB 登记、cache recovery、CLI 改动、数据库 migration、新依赖。

## Phase B 原始 RED/GREEN Evidence

- 原始 Phase B commit `7e5e71d` 实施前，`src/youtube_intel/quality.py` 不存在，35 项新增测试全部 RED（ImportError / 未实现失败）。
- 实现后：
  - `tests/unit/test_task016c_quality_gate.py`：35 passed
  - 全量 pytest：948 passed, 2 warnings（来自 Phase A 既有 bypass-revalidation 测试）
  - `uv run mypy src`：PASS
  - `uv run ruff check .`：PASS
  - `git diff --check`：PASS
- Mutation 验证（均已还原）：临时移除 control validation、使用 `lower()`/`casefold()` 比较、移除 exact-empty filter 均导致对应测试失败。

## Phase B Correction Round 1

### 范围声明

- 本 correction round 仅修正 Review 发现的 P1-1 顺序回归、增加 P1-2 frozen CONTINUE adversarial vectors，并补充 P2-1 handoff 说明。
- 本 correction commit **不**重新证明原始 Phase B RED chronology；原始 RED/GREEN evidence 已由 `7e5e71d` 记录。

### P1-1 CONTROL_CHARACTER 检测顺序

- 问题：原始实现先执行 `_is_empty()`（含 ASCII trim），导致 `\r`、`\v`、`\f` 等 raw control characters 被错误归类为 `EMPTY_CONTENT`。
- 修正：`_classify()` 现在严格按 `raw empty → raw control-character scan → ASCII-whitespace empty → EXACT_REPETITION` 顺序执行。
- 结果：
  - `\r`、`\v`、`\f`、`\x00`、`\u200b`、`\ufeff` 单独出现均返回 `CONTROL_CHARACTER_INVALID`。
  - `""`、`" "`、`"   "`、`"\t"`、`"\n"` 等仅含合法 ASCII whitespace 的内容返回 `EMPTY_CONTENT`。
- 测试：新增 `test_cr_only_rejects_control`、`test_vt_only_rejects_control`、`test_ff_only_rejects_control`；修正 `test_ascii_whitespace_only_rejects` 仅使用 space/TAB/LF。

### P1-2 冻结 CONTINUE adversarial vectors

- 仅增加测试，未增加任何实现逻辑：
  - `"API SDK GPT LLM"`
  - `"Docker Kubernetes Terraform"`
  - `"General Dynamics Corporation"`
  - `"Amazon Connect Salesforce"`
- 目的：证明 Gate 不包含 token、acronym、entity 或 uppercase heuristic。

### 修改文件

- `src/youtube_intel/quality.py`
- `tests/unit/test_task016c_quality_gate.py`
- `handoffs/TASK-016C.md`

## Correction Round 1 验证结果

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_gate.py` | 44 passed |
| `uv run pytest -x -q` | 957 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE B CORRECTION ROUND 1 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv run pytest -x -q tests/unit/test_task016c_quality_gate.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase C Correction Round 2 交接报告

## 元数据

- Task: `TASK-016C Phase C`
- Role: `Implementer (Correction Round 2)`
- Agent/session: `WorkBuddy`
- Previous correction commit: `69b508b`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 仅关闭独立审查在 Phase C 中剩余的 P1 findings，不扩展 Phase C 范围，不进入 Phase D+。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `src/youtube_intel/providers/ollama.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`
  - `tests/integration/test_ollama_provider.py`
  - `handoffs/TASK-016C.md`
- 明确未做：ProviderCall persistence、Quality PASS Attestation、`TrustedScoringFinalizer`、pre-write validation、`ValidatedScoringWritePlan`、Artifact 文件提交协议、原子 DB 登记、cache recovery、Primary/Repair 编排、CLI 改动、数据库 migration、新依赖、Phase D+。

## P1-1 H1/H2 可信身份边界

### 问题

`_validated=True` 可通过 `model_construct()`、private attribute 赋值、subclass override、model_dump override 绕过。

### 修正

- 移除 `QualityJudgeOperationInput._validated` 可变标记与 after-validator。
- 禁用 `QualityJudgeOperationInput.model_construct()`，任何构造绕过直接失败。
- `build_judge_h1_h2` 仅接受精确类型 `QualityJudgeOperationInput`，拒绝 subclass。
- 身份计算前必须从原始 `__dict__` 重新执行一次 `model_validate`，使 overridden `model_dump`/property 无法影响 H1/H2。
- 修改文件：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`

### 新增回归测试

- `test_model_construct_and_private_marker_injection_fails`
- `test_subclass_property_override_rejected_for_h1_h2`
- `test_model_dump_override_rejected_for_h1_h2`
- 保留 `test_unchecked_model_copy_update_cannot_produce_trusted_h1`

## P1-2 Trusted policy binding

### 问题

`policy_version` 未与固定 Judge 配置绑定；仅校验了 provider/model/digest/prompt/schema。

### 修正

- `OllamaQualityJudgeProvider._validate_trusted_binding` 增加 `policy_version == _QUALITY_POLICY_VERSION` 检查。
- 任何 mismatch 在发起 transport 前返回 `UNCERTAIN`/`JUDGE_UNAVAILABLE`，零 fake/真实请求。

### 新增回归测试

- `test_config_mismatch_fails_closed_without_transport` 参数化增加 `policy_version`。

## P1-3 Canonical Judge Payload Boundary

### 问题

Judge 请求参数 `reason=None`、`topics=()`  defaults 允许空评估材料；payload 不是 canonical、bounded、identity-bound。

### 修正

- `OllamaQualityJudgeProvider.judge` 改为要求 `content_input: ContentQualityInput`。
- 新增 `build_content_quality_input_hash`（`src/youtube_intel/quality.py`），对 `ContentQualityInput` 做精确类型检查 + raw `__dict__` 重验证 + canonical SHA-256。
- Provider 在校验 trusted binding 与 loopback 之后、transport 之前验证：
  - `content_input` 精确类型为 `ContentQualityInput`；
  - `content_input.candidate_hash == operation_input.candidate_hash`；
  - `content_input.scoring_request_hash == operation_input.scoring_request_hash`；
  - `build_content_quality_input_hash(content_input) == operation_input.quality_input_hash`。
- 任何失败 fail closed 为 `UNCERTAIN`/`JUDGE_UNAVAILABLE`，不发出请求。
- Prompt 仅由固定前缀 + 一个 canonical JSON payload 组成，payload 包含：
  - `judge_identity`（H1）
  - `quality_input_hash`
  - `language`
  - `candidate_reason`
  - `candidate_topics`
  - `evidence_registry`（id + excerpt）
- 无 raw 字符串插值，无空默认评估材料。
- `ContentQualityInput.evidence_registry` 增加非空校验，确保 payload Nonempty。

### 新增回归测试

- `test_missing_payload_is_rejected`
- `test_noncanonical_payload_type_is_rejected`
- `test_quality_input_hash_mismatch_is_rejected`
- `test_payload_requires_nonempty_reason_topics_and_evidence`
- `test_judge_request_payload_contains_bounded_evaluation_content` 改为解析 prompt 中单一 canonical JSON 并校验字段。

## P2 Loopback URL 变体

### 新增测试

`test_non_loopback_base_url_fails_closed_before_transport` 覆盖：

- `https://example.com`
- `http://example.com:11434`
- `http://user@127.0.0.1:11434`
- `http://127.0.0.1:11434?query=1`
- `http://127.0.0.1:11434#fragment`

复用现有 `_validate_loopback_http_base_url`，所有变体在 transport 收到请求前返回 `UNCERTAIN`。

## TDD RED Evidence

本次 correction 先写测试再实现。由于接口签名变化，原有部分调用在修正前直接触发 `TypeError`/`ImportError`；针对新增回归用例的 RED 表现：

- `test_model_construct_and_private_marker_injection_fails`：修正前 `model_construct` 成功 + private marker 注入后 `build_judge_h1_h2` 返回可信身份。
- `test_subclass_property_override_rejected_for_h1_h2`：修正前 subclass 被接受，H2 使用被覆盖 property。
- `test_model_dump_override_rejected_for_h1_h2`：修正前 subclass 被接受，H2 使用被篡改 `model_dump`。
- `test_config_mismatch_fails_closed_without_transport[policy_version]`：修正前 policy mismatch 仍发起 transport 并返回 `PASS`。
- `test_missing_payload_is_rejected`、`test_noncanonical_payload_type_is_rejected`、`test_quality_input_hash_mismatch_is_rejected`：修正前新 signature 不存在，调用异常或绕过 payload 校验。
- `test_judge_request_payload_contains_bounded_evaluation_content`：修正前 prompt 使用多字段 `.format` 插值，非 canonical JSON。

**RED chronology 说明**：Phase C 原始实现 commit `da1154d` 的 RED evidence 已由该 commit 记录；Correction Round 1 commit `69b508b` 的 RED evidence 已由该 commit 记录。本 Round 2 仅针对新增/调整用例记录 RED，不重新证明前序 RED chronology。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --offline` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py` | 57 passed |
| `uv run pytest -x -q tests/integration/test_ollama_provider.py` | 71 passed |
| `uv run pytest -x -q` | 1017 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 修改文件

- `src/youtube_intel/domain.py`
  - `QualityJudgeOperationInput`：移除 `_validated`，禁用 `model_construct`。
  - `ContentQualityInput.evidence_registry`：增加非空校验。
- `src/youtube_intel/quality.py`
  - `build_judge_h1_h2`：精确类型检查 + raw `__dict__` 重验证。
  - 新增 `build_content_quality_input_hash` 与内部 `_revalidated_fields`/`_canonical_json` helper。
- `src/youtube_intel/providers/ollama.py`
  - `OllamaQualityJudgeProvider.judge`：改为要求 `content_input`。
  - `_validate_trusted_binding`：增加 `policy_version` 校验。
  - 新增 `_validate_content_input_identity`。
  - `_generate`：prompt 改为固定前缀 + canonical JSON payload。
- `tests/unit/test_task016c_quality_judge_contract.py`：新增/调整 57 项测试。
- `tests/integration/test_ollama_provider.py`：调整 Judge 调用为新的 payload API，新增 `_judge_content_input` helper。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：P1-1 H1/H2 信任边界、P1-2 policy_version 绑定、P1-3 canonical payload boundary、P2 loopback URL 变体。
- 剩余风险：
  - 同进程内存模型下 `object.__setattr__` 仍可修改 `__dict__`；本修正通过“每次都从 raw `__dict__` 重验证”将风险转化为“只能传入有效数据”，但不具备密码学防篡改能力。
  - `ContentQualityInput` 非空 evidence 约束是新增强制规则；后续调用方需保证至少一条 evidence。
- `DECISION NEEDED`：无（Phase C correction 范围内）。

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE C CORRECTION ROUND 2 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_ollama_provider.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase C Correction Round 3

## 元数据

- Role: `Implementer (Correction Round 3)`
- Agent/session: `WorkBuddy`
- Parent commit: `eba5420f3ab89076f99c527743a55a11c99fa3fd`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 仅关闭 Phase C Correction Round 2 Independent Review 剩余的 3 个 P1 与相关 P2 gaps。
- 禁止进入 Phase D；禁止扩大 Phase C 范围。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `src/youtube_intel/providers/ollama.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`
  - `tests/integration/test_ollama_provider.py`
  - `handoffs/TASK-016C.md`
- 明确未做：scoring.py、state.py、runtime composition、Artifact、cache、DB、migration、ProviderCall persistence、Attestation、Finalizer、filesystem protocol、Phase D+。

## P1-1 — H1/H2 可信身份边界

- 问题：`QualityJudgeOperationInput` 的 deprecated `copy(update=...)` 仍可产生被修改的实例并进入 `build_judge_h1_h2`。
- 修复：在 `QualityJudgeOperationInput` 上覆盖 `copy()`，当 `update is not None` 时直接抛 `ValueError`；`model_copy(update=...)` 已由 `_UpdateProtectedQualityContract` 拒绝。
- 回归测试：
  - `test_deprecated_copy_update_cannot_produce_trusted_h1`
  - `test_unchecked_model_copy_update_cannot_produce_trusted_h1`
  - `test_unchecked_model_construct_cannot_produce_trusted_h1`
  - `test_subclass_property_override_rejected_for_h1_h2`
  - `test_model_dump_override_rejected_for_h1_h2`

## P1-2 — Judge 入口处立即重建

- 问题：`OllamaQualityJudgeProvider.judge()` 在信任重建前读取原始 operation input 的属性，subclass spoof 可到达 `GET /api/tags`。
- 修复：`judge()` 入口立即通过 `_revalidated_fields` 重建 `QualityJudgeOperationInput` 与 `ContentQualityInput`；所有后续 binding/loopback/identity/transport 逻辑只使用重建后的精确基类对象。
- 回归测试：
  - `test_subclass_getattribute_spoof_emits_zero_transport`
  - `test_subclass_model_dump_spoof_emits_zero_transport`
  - `test_model_construct_operation_input_emits_zero_transport`
  - `test_malformed_content_input_fails_closed_without_validation_error`
  - `test_zero_transport_on_content_input_hash_mismatch`

## P1-3 — 恢复空 Evidence Registry

- 问题：Correction Round 2 未经授权地给 `ContentQualityInput.evidence_registry` 增加了非空约束，导致 `ContentQualityResult` PASS 矩阵也要求至少一个 evidence ID。
- 修复：
  - 移除 `ContentQualityInput._canonical_registry` 中的非空检查。
  - 移除 `ContentQualityResult._validate_pass_matrix` 中 "PASS requires at least one evidence ID" 的检查。
  - 保留 canonical ordering、duplicate ID rejection、registry bounds、evidence ID lexical constraints。
- 回归测试：
  - `test_empty_evidence_registry_is_valid`
  - `test_empty_evidence_registry_hash_is_deterministic`
  - `test_judge_with_empty_evidence_registry_succeeds`

## 相关 P2 — Malformed Content Input Fail-Closed

- 问题：`ContentQualityInput.model_construct(...)` 绕过验证后，judge 内部重建时可能抛出 `ValidationError` 给调用方。
- 修复：`judge()` 入口的重建/身份验证全部包裹在 `try/except` 中，任何失败返回 `UNCERTAIN` 且零 transport。
- 回归测试：`test_malformed_content_input_fails_closed_without_validation_error`。

## TDD RED Evidence

Round 3 先写测试再实现。RED 阶段失败类别：

- `test_deprecated_copy_update_cannot_produce_trusted_h1`：修正前 `copy(update={"judge_model": ...})` 成功返回被修改实例。
- `test_subclass_getattribute_spoof_emits_zero_transport`：修正前 subclass 通过信任绑定，发出 `GET /api/tags`。
- `test_malformed_content_input_fails_closed_without_validation_error`：修正前 `ContentQualityInput.model_construct(...)` 进入 judge 后抛出 `ValidationError`。
- `test_empty_evidence_registry_is_valid` / `test_empty_evidence_registry_hash_is_deterministic` / `test_judge_with_empty_evidence_registry_succeeds`：修正前空 registry 直接触发 `ValidationError`。

**RED chronology 说明**：本 Round 3 仅针对新增/调整用例记录 RED；前序 Round 的 RED evidence 已分别由 `da1154d`、`69b508b`、`eba5420` 记录，Git 历史未重写。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py` | 67 passed |
| `uv run pytest -x -q tests/integration/test_ollama_provider.py` | 71 passed |
| `uv run pytest -x -q` | 1027 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 修改文件

- `src/youtube_intel/domain.py`
  - `QualityJudgeOperationInput.copy()`：拒绝 `copy(update=...)`。
  - `ContentQualityInput._canonical_registry`：移除非空约束。
  - `ContentQualityResult._validate_pass_matrix`：移除对空 evidence_ids 的拒绝。
- `src/youtube_intel/providers/ollama.py`
  - `OllamaQualityJudgeProvider.judge()`：入口立即重建 operation/content input；重建失败 fail-closed；所有后续逻辑只使用重建对象。
- `tests/unit/test_task016c_quality_judge_contract.py`：新增/调整 10 项 Round 3 回归测试，总计 67 项。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：P1-1 copy/update identity bypass、P1-2 reconstruction-at-entry、P1-3 empty evidence registry、P2 malformed content fail-closed。
- 剩余风险：同进程内存模型下物理内存篡改不在本合约防御范围内；每次重建仍依赖 Python 运行时提供的 `__dict__` 隔离。
- `DECISION NEEDED`：无（Phase C correction 范围内）。

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE C CORRECTION ROUND 3 COMPLETE`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_ollama_provider.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase C Correction Round 4

## 元数据

- Role: `Implementer (Correction Round 4)`
- Agent/session: `WorkBuddy`
- Parent commit: `f2827e2dc8a2a3f58f9e4cfe6c21ced310e86bdb`
- Correction commit: `913618c2e4cc834fb4152daec2b884c5a4b88b0f`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 仅关闭 Phase C Correction Round 3 Independent Review 剩余的 2 个 P1 与 2 个 P2 test gaps。
- 禁止进入 Phase D；禁止扩大 Phase C 范围；不重新设计 Phase C。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/providers/ollama.py`
  - `tests/unit/test_task016c_quality_judge_contract.py`
  - `handoffs/TASK-016C.md`
- 明确未做：`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、runtime composition、Artifact、cache、DB、migration、ProviderCall persistence、QualityPassAttestation、TrustedScoringFinalizer、PREWRITE_VALIDATE、filesystem protocol、repair orchestration、TASK-016B production logic、Phase D+。

## P1-1 — 恢复 PASS Evidence Invariant

- 问题：`ContentQualityResult` 的 PASS 矩阵未要求 `evidence_ids` 非空；空 evidence registry 的输入仍可能产生 `PASS` 结果。
- 修复：在 `ContentQualityResult._validate_pass_matrix` 中增加 `evidence_ids` 非空检查。
- 边界：
  - `ContentQualityInput.evidence_registry` 仍可为空。
  - Local Judge 对空 registry 仍可执行并发出请求。
  - Judge 返回 `PASS` 但 `evidence_ids=[]` 时，按 Phase C 既有的 invalid-response 语义 fail-closed 为 `UNCERTAIN`/`JUDGE_INVALID_RESPONSE`。
- 回归测试：
  - `test_pass_with_empty_evidence_ids_rejected`
  - `test_pass_with_one_valid_evidence_id_accepted`
  - `test_judge_empty_registry_pass_with_empty_evidence_fails_closed`
  - 保留 `test_empty_evidence_registry_is_valid`、`test_empty_evidence_registry_hash_is_deterministic`

## P1-2 — Malformed Operation Input Fail-Closed

- 问题：`OllamaQualityJudgeProvider.judge()` 在 operation input 重建失败时，使用原始（可能已损坏）的 operation input 构造 UNCERTAIN 结果；若该对象的 hash/provider/model/digest 字段不合法，`ContentQualityResult.model_validate` 会抛出 `ValidationError`。
- 修复：
  - 将 operation input 重建与 content input 重建分离。
  - operation input 重建失败时，直接返回不依赖任何输入字段的安全 UNCERTAIN 结果：hash 字段使用固定占位符 `"0" * 64`，Judge identity 使用 settings 中的可信 model/digest 与固定 provider。
  - 该路径零 transport、不构造 PASS/REJECT、不持久化、不暴露未验证字段。
- 回归测试：
  - `test_malformed_exact_base_operation_input_fails_closed`：参数化覆盖 provider、model、digest、scoring_request_hash、candidate_hash、quality_input_hash 的非法值。
  - `test_malformed_exact_base_operation_input_returns_no_validation_error`：显式断言无 `ValidationError` 泄露。

## P2 — 独立 Hash Mismatch 测试

- 新增 `test_content_input_hash_mismatch_fails_closed_before_transport`：
  - `candidate_hash` 不匹配：其余 hash 与 quality_input_hash 重新计算保持一致；预期 `UNCERTAIN`/`JUDGE_UNAVAILABLE` 且零 transport。
  - `scoring_request_hash` 不匹配：同上。
  - transport 配置为可成功响应；若移除对应显式比较，测试将因返回 `PASS` 而失败。

## P2 — 真正 Malformed Content Input 测试

- 替换原 `test_malformed_content_input_fails_closed_without_validation_error`（其使用空 registry，在 Round 3 后已是合法输入）。
- 新增 `test_truly_malformed_content_input_fails_closed_without_validation_error`：使用 `ContentQualityInput.model_construct(..., scoring_request_hash="not-a-valid-hash")` 等非法字段；预期 `UNCERTAIN`/`JUDGE_UNAVAILABLE`、零 transport、无 `ValidationError` 泄露。
- 保留独立测试证明空 registry 本身合法。

## TDD RED Evidence

Round 4 先写测试再实现。RED 阶段失败数与类别：

- 失败数：6
- 失败类别：
  - `test_pass_with_empty_evidence_ids_rejected`：PASS 空 `evidence_ids` 未拒绝。
  - `test_judge_empty_registry_pass_with_empty_evidence_fails_closed`：Judge 返回 PASS + 空 `evidence_ids` 被接受。
  - `test_malformed_exact_base_operation_input_fails_closed[scoring_request_hash-not-a-hash]` / `[candidate_hash-not-a-hash]` / `[quality_input_hash-not-a-hash]`：损坏 operation input 导致 `ValidationError` 泄露。
  - `test_malformed_exact_base_operation_input_returns_no_validation_error`：同上。

**RED chronology 说明**：本 Round 4 仅针对新增/调整用例记录 RED；前序 Round 的 RED evidence 已分别由 `da1154d`、`69b508b`、`eba5420`、`f2827e2` 记录，Git 历史未重写。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --offline` | PASS |
| `uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py` | 78 passed |
| `uv run pytest -x -q tests/integration/test_ollama_provider.py` | 71 passed |
| `uv run pytest -x -q` | 1038 passed, 2 warnings |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## 修改文件

- `src/youtube_intel/domain.py`
  - `ContentQualityResult._validate_pass_matrix`：新增 `evidence_ids` 非空检查。
- `src/youtube_intel/providers/ollama.py`
  - `OllamaQualityJudgeProvider.judge()`：分离 operation/content 重建异常处理；operation 重建失败使用 `_build_safe_uncertain_result`。
  - 新增 `_build_safe_uncertain_result()`：不依赖未验证输入字段的安全 fail-closed 结果构造。
- `tests/unit/test_task016c_quality_judge_contract.py`：新增/调整 Round 4 回归测试，总计 78 项。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：P1-1 PASS evidence invariant、P1-2 malformed operation fail-closed、P2 candidate/scoring hash mismatch 独立测试、P2 truly malformed content input 测试。
- 剩余风险：同进程内存模型下物理内存篡改不在本合约防御范围内；安全 fail-closed 路径依赖 `LocalScoringSettings` 在 provider 构造时已验证。
- `DECISION NEEDED`：无（Phase C correction 范围内）。

## 实现者结论

- 建议状态：`READY FOR PHASE C FOCUSED FINAL REVIEW`
- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_ollama_provider.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase D 交接报告

## 元数据

- Task: `TASK-016C Phase D`
- Role: `Implementer`
- Agent/session: `WorkBuddy`
- Parent commit: `dab0ba9d358c4624fb7619e95bfa034dd4dc70d7`
- Phase D authorization commit: `dab0ba9d358c4624fb7619e95bfa034dd4dc70d7`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-14`
- Reported: `2026-08-14`

## 目标与范围

- 任务目标：实现纯内存 quality `PASS` attestation 和 canonical `quality_result_hash`。重建并哈希完整 `ContentQualityResult(PASS)`；构造并验证 `quality-pass-attestation-v1`；绑定到 candidate / quality-input / request / version / judge / attempt 身份；任何畸形或不匹配值 fail closed。
- 允许修改：
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/quality.py`
  - `tests/unit/test_task016c_quality_attestation.py`（新建）
  - `tests/unit/test_task016c_domain_contracts.py`（最小改动）
  - `tests/unit/test_task016c_quality_judge_contract.py`（最小改动，实际未改）
  - `handoffs/TASK-016C.md`
- 实际修改：
  - `src/youtube_intel/domain.py`：新增 `QualityPassAttestation` frozen 模型（schema `quality-pass-attestation-v1`），含完整 frozen binding 字段、`evidence_ids` canonical 排序去重 validator、禁用 `model_construct` 与 `copy(update=...)`；在 `_UpdateProtectedQualityContract` 基类增加 `copy(update=...)` 禁用（统一所有 content-quality contract 的 bypass 防御）。
  - `src/youtube_intel/quality.py`：新增 `build_content_quality_result_hash`（untrusted reconstruction -> canonical SHA-256）、`build_quality_pass_attestation`（trusted application-side constructor）、`verify_quality_pass_attestation`（reconstruct + verify attestation_hash + cross-check）、`_reconstruct`（通用 untrusted->trusted 重建）、`_verify_pass_eligibility`（PASS + evidence registry 解析）、`_verify_cross_bindings`（跨 result/operation_input/quality_input 身份绑定）、`_compute_attestation_hash`。
  - `tests/unit/test_task016c_quality_attestation.py`：新建 91 项 RED-first 测试。
  - `tests/unit/test_task016c_domain_contracts.py`：更新 `test_deprecated_copy_update_bypass_is_revalidated` -> `test_deprecated_copy_update_bypass_is_blocked`（反映 `copy(update=...)` 现已被禁用）。
- 明确未做：`providers/ollama.py`、`scoring.py`、`state.py`、`TrustedScoringFinalizer`、trusted ScoreResult construction、Artifact、cache、DB、migration、ProviderCall persistence、PREWRITE_VALIDATE、filesystem protocol、repair orchestration、runtime composition、Phase E-K、dependencies、`pyproject.toml`、`uv.lock`。

## TDD RED Evidence

Phase D 先写测试再实现。RED 阶段所有 91 项测试因 `ImportError: cannot import name 'QualityPassAttestation'` 无法收集，全部 RED。

- RED 失败数：91（collection error）
- RED 失败类别：ImportError（`QualityPassAttestation` 及 `build_content_quality_result_hash` / `build_quality_pass_attestation` / `verify_quality_pass_attestation` 尚不存在）

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked --offline` | PASS |
| `tests/unit/test_task016c_quality_attestation.py` | 91 passed |
| `tests/unit/test_task016c_domain_contracts.py` | 60 passed, 1 warning |
| `tests/unit/test_task016c_quality_judge_contract.py` | 78 passed |
| 全量 `pytest -x -q` | 1129 passed, 1 warning |
| `uv run mypy src` | PASS (28 source files) |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

## quality_result_hash Contract Evidence

- `build_content_quality_result_hash` 对 untrusted `ContentQualityResult | Mapping | JSON` 执行 `_reconstruct`（instance -> `_revalidated_fields` 拒绝 subclass；Mapping/JSON -> `model_validate`/`model_validate_json`），然后对 `model_dump(mode="json")` 做 `_canonical_json`（UTF-8、`ensure_ascii=False`、sorted keys、separators `(",", ":")`）+ SHA-256。
- signals 由模型 `_canonical_signals` validator 按 enum value 排序去重；evidence_ids 由 `_canonical_evidence_ids` validator 按 stable ID 排序去重。
- 每个 frozen canonical 字段变化均改变 hash 或使 validation 失败（parametrized 测试覆盖 8 个 hash-changing 字段 + 14 个 validation-failing 字段）。
- Mapping / JSON 等价输入产生相同 hash（`test_mapping_and_json_equivalent_inputs_produce_same_hash`）。
- 手动 canonical JSON 独立验证 hash 值（`test_valid_pass_result_hash_matches_manual_canonical_json`）。

## Attestation Binding Evidence

- `build_quality_pass_attestation` 绑定全部 frozen 字段：candidate_hash、quality_input_hash、quality_result_hash、scoring_request_hash、policy_version、scoring_schema_version、scoring_prompt_version、quality_schema_version、quality_prompt_version、judge_provider、judge_model、judge_model_digest、judge_operation、judge_request_hash (H2)、attempt_role、decision_confidence、grounding_confidence、usefulness_confidence、evidence_ids、attestation_hash。
- `attestation_hash` 覆盖完整 canonical payload，仅排除自身（`test_attestation_hash_covers_full_payload_excluding_itself` 手动验证）。
- H1/H2 只复用 Phase C 已接受 `build_judge_h1_h2`，不重写（`test_attestation_binds_h2_as_judge_request_hash`、`test_h1_and_h2_remain_distinct`）。
- H2 = `build_provider_request_hash("local-content-quality-v1", H1, provider, model, prompt_version, schema_version)`，语义不变。
- confidence 与 evidence_ids 精确 mirror validated result。

## Adversarial / Mutation Evidence

### Bypass 防御

- `model_construct` on `QualityPassAttestation` -> 禁用，raises ValueError。
- `model_copy(update=...)` on `QualityPassAttestation` -> 禁用（继承 `_UpdateProtectedQualityContract`）。
- `copy(update=...)` on `QualityPassAttestation` -> 禁用（新增 override）。
- `copy(update=...)` on `ContentQualityResult` -> 禁用（`_UpdateProtectedQualityContract` 基类新增 override）。
- `model_construct` on `ContentQualityResult` -> 未禁用（Phase A 行为），但 `build_content_quality_result_hash` 通过 `_revalidated_fields` 从 `__dict__` 重建并 re-validate，无效值被拒绝。
- subclass property override -> `_revalidated_fields` 拒绝（`type(instance) is not model`）。
- subclass model_dump override -> `_revalidated_fields` 读 `__dict__` 不读 `model_dump()`，拒绝 subclass。
- fake trusted flag / unknown field -> `extra="forbid"` 拒绝。

### Binding mismatch fail-closed

- candidate_hash / quality_input_hash / scoring_request_hash mismatch -> build raises。
- judge_provider / judge_model / judge_model_digest / policy_version / prompt_version / schema_version mismatch -> build raises。
- non-PASS result -> build raises。
- external evidence ID -> build raises。
- empty registry -> build raises。
- forged attestation_hash -> verify raises。
- forged quality_result_hash -> verify raises。
- H2 mismatch -> verify raises。
- attempt_role mismatch -> verify raises。
- confidence mismatch -> verify raises。
- evidence mismatch -> verify raises。
- scoring_schema_version / scoring_prompt_version mismatch -> verify raises。
- unknown fields -> verify raises。
- forged complete attestation -> verify raises。

### Mutation proof

- 移除 `_verify_cross_bindings` 调用 -> `test_candidate_input_request_hash_mismatch_rejects[candidate_hash]` 失败（DID NOT RAISE）。已还原。

## No-Side-Effect Evidence

- `build_quality_pass_attestation` 和 `verify_quality_pass_attestation` 均为纯内存操作。
- `test_build_creates_no_filesystem_side_effects`：`tmp_path` 下无文件创建。
- `test_verify_creates_no_filesystem_side_effects`：同上。
- `test_attestation_has_no_persistence_identity_fields`：attestation 无 persistence 字段。
- 未导入或调用 `ScoreResult`、`Artifact`、`ProviderCall`、cache、DB、filesystem 模块。

## Reuse Decision

| 组件 | 决策 | 说明 |
|---|---|---|
| `_canonical_json` (quality.py) | DIRECT | 复用 Phase C 已接受 helper。 |
| `_revalidated_fields` (quality.py) | DIRECT | 复用 Phase C 已接受 helper。 |
| `build_judge_h1_h2` (quality.py) | DIRECT | 复用 Phase C 已接受 H1/H2 builder，不重写。 |
| `build_content_quality_input_hash` (quality.py) | DIRECT | 复用 Phase C 已接受 quality input hash。 |
| `build_provider_request_hash` (state.py) | DIRECT | 通过 `build_judge_h1_h2` 间接复用 ADR-003 builder。 |
| `_UpdateProtectedQualityContract` (domain.py) | ADAPT | 在基类增加 `copy(update=...)` 禁用。 |

## 修改文件

- `src/youtube_intel/domain.py`：新增 `QualityPassAttestation` 类；`_UpdateProtectedQualityContract` 新增 `copy(update=...)` 禁用；`__all__` 新增导出。
- `src/youtube_intel/quality.py`：新增 `build_content_quality_result_hash`、`build_quality_pass_attestation`、`verify_quality_pass_attestation` 及内部 helper。
- `tests/unit/test_task016c_quality_attestation.py`：新建 91 项 RED-first 测试。
- `tests/unit/test_task016c_domain_contracts.py`：更新 1 项测试。
- `handoffs/TASK-016C.md`：本报告。

## 失败、跳过与风险

- 已解决：全部 Phase D frozen contract 要求。
- 剩余风险：
  - 同进程内存模型下 `object.__setattr__` 仍可修改 `__dict__`；通过"每次都从 raw `__dict__` 重验证"防御。
  - `ContentQualityResult.model_construct` 未禁用（Phase A 行为）；依赖 `_revalidated_fields` 在入口处重建验证。
  - 1 个 Pydantic serialization warning 来自 Phase A 既有测试，非 Phase D 引入。
- `DECISION NEEDED`：无。

## 实现者结论

- 建议状态：`IN_REVIEW / PHASE D COMPLETE`

---

# Phase D Correction Round 1 — Bind attestation to trusted current provenance

## 目标

关闭 Independent Review 剩余 P1：``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 未绑定当前受信配置，导致自洽但未经授权的 provenance 可通过验证。

## 父提交

- ``b22a3ba0d64b8cfb79abb2a3acb261affdf92e92``

## 变更路径

- ``src/youtube_intel/domain.py``：新增 ``TrustedQualityProvenance`` 模型；``__all__`` 导出。
- ``src/youtube_intel/quality.py``：``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 改为接收 ``trusted_provenance``；新增 ``_verify_trusted_provenance`` 对 Judge 模型/digest 和 scoring schema/prompt 版本做当前受信上下文校验；``scoring_schema_version`` / ``scoring_prompt_version`` 改为从受信上下文写入，不再由调用方直接指定。
- ``tests/unit/test_task016c_quality_attestation.py``：新增 17 项 RED-first 回归测试，覆盖自洽非法 Judge 模型/digest 在 build 与 verify 阶段被拒绝、scoring 版本在 verify 阶段因受信上下文变化被拒绝、``TrustedQualityProvenance`` 自身 bypass 防御、合法配置仍可通过。

## 信任当前上下文绑定项

- ``judge_provider``
- ``judge_model``
- ``judge_model_digest``
- ``scoring_schema_version``
- ``scoring_prompt_version``

## RED Evidence

- 修正前：未授权模型 ``untrusted-local-model`` + 任意 digest + 任意 scoring 版本可在 build 与 verify 阶段生成/验证有效 attestation。
- 修正后测试写入时：108 项 attestation 测试全部 RED（依赖 ``TrustedQualityProvenance`` 未导入）；其中 17 项为新增 provenance 回归测试。

## GREEN Evidence

- ``tests/unit/test_task016c_quality_attestation.py``：108 passed
- ``tests/unit/test_task016c_domain_contracts.py``：60 passed, 1 warning
- ``tests/unit/test_task016c_quality_judge_contract.py``：78 passed
- ``uv run pytest -x -q``：1146 passed, 1 warning
- ``uv run mypy src``：Success (28 files)
- ``uv run ruff check .``：All checks passed
- ``git diff --check``：passed

## 伪造一致配置证据

- ``test_unauthorized_judge_model_build_rejects``：内部一致的未授权模型无法在授权受信上下文下 build。
- ``test_unauthorized_judge_model_verify_rejects``：使用未授权上下文构建的合法 hash attestation，在授权上下文 verify 时失败。
- ``test_unauthorized_judge_digest_build_rejects``：内部一致的未授权 digest 无法 build。
- ``test_individual_field_mismatch_verify_rejects``：scoring_schema_version / scoring_prompt_version 的受信上下文变化导致 verify 失败。

## 突变证据

- 临时注释 ``_verify_trusted_provenance`` 后，``test_unauthorized_judge_model_build_rejects`` 失败；已回退。

## 范围验证

- ``git diff --name-only`` 仅包含 ``src/youtube_intel/domain.py``、``src/youtube_intel/quality.py``、``tests/unit/test_task016c_quality_attestation.py``。
- 未修改 ``providers/ollama.py``、``scoring.py``、``state.py``、``pyproject.toml``、``uv.lock``、DB、Artifact、cache、Finalizer 等禁止路径。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D FOCUSED INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 2 — Close trusted provenance authority boundary

## 目标

关闭 Independent Review 剩余 P1：``TrustedQualityProvenance`` 仍是 caller-authoritative（调用者可自行创建并传入）。必须改为由应用当前配置（``LocalScoringSettings``）通过可信 provenance 工厂生成 ``TrustedQualityProvenance``，再用于 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation``，确保调用者无法成为信任来源。

## 父提交

- ``721b1c53233dfdea548e1d09e9fb6c0d4470f463``

## 变更路径

- ``src/youtube_intel/quality.py``：
  - 移除 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 的 ``trusted_provenance`` 参数。
  - 新增模块常量：``_JUDGE_PROVIDER = "ollama"``、``_QUALITY_JUDGE_OPERATION = "local-content-quality-v1"``、``_SCORING_SCHEMA_VERSION = "scoring-schema-v1"``、``_SCORING_PROMPT_VERSION = "scoring-prompt-v1"``。
  - 新增内部工厂 ``_build_trusted_quality_provenance(settings: LocalScoringSettings) -> TrustedQualityProvenance``：仅由应用当前配置生成受信 provenance，调用者无法传入。
  - ``_verify_trusted_provenance`` 增加 scoring_schema_version / scoring_prompt_version 一致性校验。
  - 签名统一改为 ``settings: LocalScoringSettings``。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 所有 ``trusted_provenance=_authorized_provenance()`` 调用点改为 ``settings=_authorized_settings()``。
  - 新增 ``LocalScoringSettings``/``_authorized_settings``/``_unauthorized_settings`` helper。
  - 保留 ``TrustedQualityProvenance`` 用于域模型级 bypass 测试。
  - 新增 ``test_self_consistent_attacker_provenance_rejected``：证明自洽的攻击者配置（模型/digest 互相对齐但非授权）在授权应用配置下 build 与 verify 均被拒绝。
  - 更新 ``test_scoring_version_mismatch_rejects`` 与 ``test_individual_field_mismatch_verify_rejects``：改为直接篡改 attestation JSON（重算 hash）后使用授权 settings verify，反映 scoring 版本现为应用固定常量。

## 受信边界

- 信任来源：``LocalScoringSettings.model`` + ``LocalScoringSettings.expected_model_digest``（应用当前配置）。
- 固定常量（模块所有）：``judge_provider``、``judge_operation``、``scoring_schema_version``、``scoring_prompt_version``。
- 工厂 ``_build_trusted_quality_provenance`` 是唯一从应用到 ``TrustedQualityProvenance`` 的支持路径。

## RED Evidence

- 修正前（由临时脚本 ``_vuln_demo.py`` 记录）：调用者构造的 ``TrustedQualityProvenance``（模型 ``untrusted-local-model``、digest ``sha256:dddd...``、scoring 版本任意）可成功 build 并 verify 自洽 attestation。
- 新测试 ``test_self_consistent_attacker_provenance_rejected`` 在修正前会失败：build 不会拒绝，verify 不会拒绝。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``tests/unit/test_task016c_quality_attestation.py`` | 107 passed |
| 全量 ``uv run --offline pytest`` | 1145 passed, 1 warning |
| ``uv run --offline mypy src`` | Success (28 source files) |
| ``uv run --offline ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_self_consistent_attacker_provenance_rejected``：
  - 使用攻击者 settings 可成功 build（证明输入本身不是非法的，只是非授权）。
  - 同一组输入在授权 settings 下 build 被拒绝。
  - 攻击者 settings 下生成的合法 hash attestation，在授权 settings 下 verify 被拒绝。

## 突变证据

- 临时注释 ``build_quality_pass_attestation`` 中 ``_verify_trusted_provenance`` 调用后，``test_self_consistent_attacker_provenance_rejected`` 失败（DID NOT RAISE）；已回退。

## 范围验证

- ``git diff --name-only`` 仅包含 ``src/youtube_intel/quality.py``、``tests/unit/test_task016c_quality_attestation.py``。
- 未修改 ``src/youtube_intel/domain.py``、``providers/ollama.py``、``scoring.py``、``state.py``、``pyproject.toml``、``uv.lock``、DB、Artifact、cache、Finalizer 等禁止路径。
- 未进入 Phase E。

## 已知基线

- ``tests/unit/test_task016c_quality_attestation.py`` 存在若干 pre-existing mypy 错误（如 ``**{field: value}`` 类型展开、subclass property override 等），本次变更未引入新的 mypy 错误；生产代码 ``src`` 保持 mypy clean。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D FOCUSED INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 3 — Close provenance authority boundary

## 目标

关闭 Independent Review 剩余 P1：``LocalScoringSettings`` 仍是 caller-controlled；攻击者可构造任意 model/digest 并通过自洽校验生成有效 attestation。必须完全删除调用者对 trusted provenance 的控制，改为由应用固定配置内部生成。

## 父提交

- ``fc363eba81eb4232d3ec41f66ff091fcfb1314db``

## 本次提交

- Message: ``TASK-016C Phase D correction round 3 close provenance authority boundary``
- SHA: 见 ``git log``（提交信息即上一条）。

## 变更路径

- ``src/youtube_intel/quality.py``：
  - 移除 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 的 ``settings`` 参数。
  - 移除 ``LocalScoringSettings`` 导入。
  - 新增固定应用常量：``_JUDGE_MODEL = "qwen3:8b"``、``_JUDGE_MODEL_DIGEST = "sha256:" + "b" * 64``。
  - 将内部工厂从 ``_build_trusted_quality_provenance(settings)`` 改为 ``_build_current_quality_provenance()``：无参数，仅从模块常量生成 ``TrustedQualityProvenance``。
  - 更新函数文档，明确调用者无法提供/覆盖任何 provenance 字段。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 删除 ``_authorized_settings()`` / ``_unauthorized_settings()`` helper。
  - 删除全部 ``settings=...`` 调用点。
  - 重写 ``TestTrustedProvenanceBinding``：
    - 新增 ``test_caller_local_scoring_settings_rejected_by_build``：调用者传入 ``LocalScoringSettings(model="untrusted-local-model", expected_model_digest=UNAUTHORIZED_DIGEST)`` 时 ``build_quality_pass_attestation`` 抛出 ``TypeError``。
    - 新增 ``test_caller_local_scoring_settings_rejected_by_verify``：同上，``verify_quality_pass_attestation`` 抛出 ``TypeError``。
    - 新增 ``test_self_consistent_attacker_inputs_build_rejects``：自洽的攻击者 model/digest 输入在固定配置下 build 被拒绝。
    - 新增 ``test_self_consistent_fake_provenance_verify_rejects``：攻击者手工构造完全自洽、hash 正确的 attestation（fake provenance/operation/result）在 verify 时被拒绝。
    - 移除已失效的 ``test_unauthorized_judge_model_verify_rejects``（无法再用调用者 settings 构建未授权 attestation）。
    - 更新类文档与注释，反映信任来源为应用固定常量。

## 受信边界

- 信任来源：模块级固定常量 ``_JUDGE_PROVIDER``、``_JUDGE_MODEL``、``_JUDGE_MODEL_DIGEST``、``_SCORING_SCHEMA_VERSION``、``_SCORING_PROMPT_VERSION``。
- 调用者无法通过参数提供：``TrustedQualityProvenance``、``LocalScoringSettings`` 或任何 caller-created provenance DTO。
- 唯一内部入口：``_build_current_quality_provenance()``。

## RED Evidence

- 修正前（Round 2 状态）：调用者传入 ``LocalScoringSettings(model="untrusted-local-model", expected_model_digest=UNAUTHORIZED_DIGEST)`` 与自洽输入可成功 ``build`` 并 ``verify`` attestation。
- 本 Round 新增测试在修正前失败：
  - ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``：API 仍接受 ``settings`` 参数，未抛出 ``TypeError``。
  - ``test_self_consistent_attacker_inputs_build_rejects``：未授权输入在 ``settings`` 可控时被接受，未抛出异常。
  - ``test_self_consistent_fake_provenance_verify_rejects``：自洽 fake attestation 在 ``settings`` 可控时可成功 verify。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 109 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q`` | 1147 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_caller_local_scoring_settings_rejected_by_build``：调用者尝试用 ``LocalScoringSettings`` 控制 build，API 直接拒绝（``TypeError``）。
- ``test_caller_local_scoring_settings_rejected_by_verify``：调用者尝试用 ``LocalScoringSettings`` 控制 verify，API 直接拒绝（``TypeError``）。
- ``test_self_consistent_attacker_inputs_build_rejects``：自洽攻击者输入因不符合固定受信配置而被 build 拒绝。
- ``test_self_consistent_fake_provenance_verify_rejects``：攻击者构造 fake provenance + fake operation + fake result 并保证 hash 完全正确，verify 仍因受信配置不匹配而拒绝。

## 突变证据

- 临时注释 ``build_quality_pass_attestation`` 中的 ``_verify_trusted_provenance`` 调用后：
  - ``test_self_consistent_attacker_inputs_build_rejects`` 失败（DID NOT RAISE）。
  - ``test_self_consistent_fake_provenance_verify_rejects`` 失败（DID NOT RAISE）。
  - ``test_unauthorized_judge_model_build_rejects`` / ``test_unauthorized_judge_digest_build_rejects`` / ``test_individual_judge_field_mismatch_build_rejects[...]`` 失败（DID NOT RAISE）。
- 已回退并重新通过全部测试。

## 范围验证

- ``git diff --name-only`` 仅包含 ``src/youtube_intel/quality.py``、``tests/unit/test_task016c_quality_attestation.py``、``handoffs/TASK-016C.md``。
- 未修改 ``src/youtube_intel/domain.py``、``providers/ollama.py``、``scoring.py``、``state.py``、``pyproject.toml``、``uv.lock``、DB、Artifact、cache、Finalizer 等禁止路径。
- 未进入 Phase E。

## 已知基线

- ``tests/unit/test_task016c_quality_attestation.py`` 仍存在若干 pre-existing mypy 错误（如 ``**{field: value}`` 类型展开、subclass property override 等），本次变更未引入新的 mypy 错误；生产代码 ``src`` 保持 mypy clean。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D FOCUSED INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Authority Boundary Amendment — Bind attestation to runtime provenance authority

## 目标

关闭 Phase D 剩余 P1：Round 3 使用硬编码测试身份（``_JUDGE_MODEL`` / ``_JUDGE_MODEL_DIGEST``）作为生产 authority，会同时拒绝真实应用配置。本轮通过 Option A 架构将信任边界迁移到 runtime composition：``already-loaded AppConfig → runtime.py → mint in-memory QualityProvenanceAuthority → quality.py``。

## 父提交

- ``39a1e864238388abe651c466c0a41a023934c872``

## Amendment cherry-pick

- SHA: ``17f0f23eec5263cf30d4b1bc2468480c81b16145``
- Source: ``31d35b82741e0069c4108ea7c4f2601cff54e7c7``
- 说明：仅 cherry-pick 新的 Authority Boundary Amendment；原 ``790644a2771315e5d3f96286ffd39cd4e863cd79`` 已通过 ``dab0ba9d358c4624fb7619e95bfa034dd4dc70d7`` 存在于祖先历史，未重复 cherry-pick。

## 变更路径

- ``src/youtube_intel/domain.py``：
  - 移除 ``TrustedQualityProvenance`` 及其 ``__all__`` 导出。
  - 质量 provenance 的权威表达不再通过可序列化/可构造的 Pydantic DTO。
- ``src/youtube_intel/quality.py``：
  - 新增 ``QualityProvenanceAuthority``：非 Pydantic、私有 sentinel 保护的 opaque runtime-minted 对象。
  - 新增 ``_QualityProvenanceAuthoritySentinel`` / ``_QUALITY_PROVENANCE_AUTHORITY_SENTINEL``：仅 ``runtime.py`` 可通过私有工厂持有 sentinel。
  - 新增 ``_mint_quality_provenance_authority``：私有工厂，接收 sentinel。
  - 删除 Round 3 的硬编码 ``_JUDGE_MODEL`` / ``_JUDGE_MODEL_DIGEST``。
  - ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 改为接收 ``authority: QualityProvenanceAuthority``，拒绝 ``LocalScoringSettings``、``TrustedQualityProvenance``、Mapping、JSON 等 caller-created DTO（``TypeError``）。
  - ``_verify_trusted_provenance`` 扩展为同时校验 quality policy/schema/prompt 版本与 Judge operation identity，全部来自 authority。
- ``src/youtube_intel/runtime.py``：
  - 新增 ``_build_quality_provenance_authority(local_scoring)``：唯一生产路径，从 ``AppConfig.settings.local_scoring`` 的 ``model`` / ``expected_model_digest`` 派生 authority。
  - 新增 ``_mint_quality_provenance_authority_for_test(local_scoring)``：受控测试 seam，仍走同一私有 minting 路径。
  - ``RuntimeOperations.__init__`` 在 composition 时调用上述函数，生成 ``self._quality_provenance_authority``。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 移除 ``TrustedQualityProvenance`` 导入。
  - 新增 ``REAL_CONFIG_DIGEST`` 常量，用于证明不再依赖 ``sha256:bbbb...``。
  - 新增 ``_current_authority()`` / ``_real_config_authority()`` helper，通过 ``_mint_quality_provenance_authority_for_test`` 从 ``LocalScoringSettings`` 获取 runtime-minted authority。
  - 所有 ``build`` / ``verify`` 调用增加 ``authority=...``。
  - 重写 ``TestTrustedProvenanceBinding``：
    - 新增 ``test_real_current_config_build_and_verify_succeeds``：真实当前 config digest（非 bbbb）可成功 build + verify。
    - 保留 ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``。
    - 新增 ``test_caller_mapping_rejected_as_authority``。
    - 新增 ``test_direct_authority_construction_rejected``：无 sentinel 直接构造 ``QualityProvenanceAuthority`` 失败。
    - 保留并更新 ``test_self_consistent_attacker_inputs_build_rejects`` / ``test_self_consistent_fake_provenance_verify_rejects`` / ``test_configuration_rotation_verify_rejects``。
  - 新增 ``TestQualityProvenanceAuthorityBypass``：证明 authority 无 ``model_copy`` / ``model_construct`` / ``model_validate`` 等 Pydantic bypass 路径。
- ``tests/integration/test_runtime_composition.py``：
  - 新增 ``test_runtime_operations_mints_quality_provenance_authority_from_config``：通过真实 ``load_app_config`` 加载 fixture 配置，验证 ``RuntimeOperations`` 生成的 authority 确实来自 ``AppConfig.settings.local_scoring``，digest 为 ``sha256:{'1' * 64}``（非 bbbb）。

## 受信边界

- 唯一 authority minting boundary：``src/youtube_intel/runtime.py`` 中的 ``_build_quality_provenance_authority``。
- Authority 来源：已经加载并验证的 ``AppConfig.settings.local_scoring.model`` 与 ``expected_model_digest``。
- 冻结常量仍保留在 ``quality.py``：``_JUDGE_PROVIDER``、``_QUALITY_JUDGE_OPERATION``、``_QUALITY_POLICY_VERSION``、``_QUALITY_SCHEMA_VERSION``、``_QUALITY_PROMPT_VERSION``、``_SCORING_SCHEMA_VERSION``、``_SCORING_PROMPT_VERSION``。
- ``quality.py`` 不读取配置文件；authority 由 runtime composition 注入。
- Caller 无法通过 ``LocalScoringSettings``、``TrustedQualityProvenance``、Mapping、JSON 或普通 ``QualityProvenanceAuthority(...)`` 构造绕过 sentinel 检查。

## AppConfig → Authority 路径

```
load_app_config(channels_path, settings_path)
  → AppConfig.settings.local_scoring
      → RuntimeOperations.__init__
          → _build_quality_provenance_authority(config.settings.local_scoring)
              → _mint_quality_provenance_authority(sentinel=private, model=..., digest=...)
                  → QualityProvenanceAuthority
```

## RED Evidence

- 修正前（Round 3 状态）：``quality.py`` 内部使用硬编码 ``_JUDGE_MODEL_DIGEST = "sha256:" + "b" * 64``，无法代表真实应用配置；真实 current config digest（如 ``sha256:{'1' * 64}``）会被拒绝。
- 本 Amendment 新增测试在修正前失败：
  - ``test_real_current_config_build_and_verify_succeeds``：真实 config digest 与硬编码 bbbb 不匹配，build/verify 拒绝。
  - ``test_runtime_operations_mints_quality_provenance_authority_from_config``：runtime 尚未 mint authority，断言失败。
  - ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``：API 仍接受 ``settings`` 参数，未抛出 ``TypeError``（Round 3 已部分覆盖，但 authority 类型检查强化后重新验证）。
  - ``test_direct_authority_construction_rejected``：无 sentinel 时 ``QualityProvenanceAuthority`` 可被直接构造。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 112 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q`` | 1151 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_real_current_config_build_and_verify_succeeds``：真实 current config digest（非 bbbb）可成功 build + verify。
- ``test_caller_local_scoring_settings_rejected_by_build`` / ``test_caller_local_scoring_settings_rejected_by_verify``：caller-created ``LocalScoringSettings`` 无法作为 authority。
- ``test_caller_mapping_rejected_as_authority``：caller-created Mapping 无法作为 authority。
- ``test_direct_authority_construction_rejected``：无 runtime sentinel 无法构造 ``QualityProvenanceAuthority``。
- ``test_self_consistent_attacker_inputs_build_rejects``：攻击者自洽 model/digest 输入 build 被拒绝。
- ``test_self_consistent_fake_provenance_verify_rejects``：攻击者构造完全自洽、hash 正确的 fake attestation，verify 被拒绝。
- ``test_configuration_rotation_verify_rejects``：authority A 创建的 attestation 在 authority B 下 verify 失败。
- ``test_runtime_operations_mints_quality_provenance_authority_from_config``：runtime composition 从 ``AppConfig.settings.local_scoring`` 派生 authority，digest 为真实 fixture 值。

## Mutation Evidence

- 临时破坏 ``src/youtube_intel/runtime.py`` 中 ``_build_quality_provenance_authority`` 的 config-to-digest 绑定，将 ``judge_model_digest=local_scoring.expected_model_digest`` 替换为固定 ``"sha256:" + "f" * 64`` 后：
  - ``tests/unit/test_task016c_quality_attestation.py::TestTrustedProvenanceBinding::test_real_current_config_build_and_verify_succeeds`` 失败（``ValueError: judge_model_digest does not match trusted current provenance``）。
  - ``tests/integration/test_runtime_composition.py::test_runtime_operations_mints_quality_provenance_authority_from_config`` 失败（digest 断言不匹配）。
  - ``test_configuration_rotation_verify_rejects`` 同样因 digest 绑定被破坏而失败。
- 回退 mutation 后，上述测试重新通过。

## 范围验证

- ``git diff --name-only HEAD`` 仅包含：
  - ``src/youtube_intel/domain.py``
  - ``src/youtube_intel/quality.py``
  - ``src/youtube_intel/runtime.py``
  - ``tests/unit/test_task016c_quality_attestation.py``
  - ``tests/integration/test_runtime_composition.py``
  - ``handoffs/TASK-016C.md``
- 未修改 ``providers/ollama.py``、``scoring.py``、``state.py``、DB、cache、Artifact、ProviderCall persistence、Finalizer、Phase E+、依赖、锁文件。
- ``runtime.py`` 变更范围严格限于 authority minting/injection bridge，未扩展 runtime 功能。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D AUTHORITY BOUNDARY INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 4 — Close authority minting boundary

## 目标

关闭 Independent Review 剩余两个 P1：

- P1-1：`QualityProvenanceAuthority` 接受 `isinstance(authority, QualityProvenanceAuthority)`，导致 subclass/property override/proxy/spoofed attribute 可通过信任边界。
- P1-2：`_mint_quality_provenance_authority_for_test(LocalScoringSettings)` 是 caller-controlled minting seam，违反 ADR-026 要求的 `AppConfig → Runtime composition → QualityProvenanceAuthority` 单一边界。

## 父提交

- ``23d3f1c727b948ace6bb0ac8eefa7858f17c07cf``

## 变更路径

- ``src/youtube_intel/quality.py``：
  - ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 的信任边界检查由 ``isinstance(authority, QualityProvenanceAuthority)`` 改为 ``type(authority) is QualityProvenanceAuthority``。
  - 拒绝 subclass、property override 对象、proxy 对象、spoofed attribute 对象。
- ``src/youtube_intel/runtime.py``：
  - 删除 ``_mint_quality_provenance_authority_for_test(local_scoring: LocalScoringSettings)`` 及全部相关导入/引用。
  - 唯一保留的 minting 路径是 ``_build_quality_provenance_authority``，由 ``RuntimeOperations.__init__`` 在 composition 时调用。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 移除 ``_mint_quality_provenance_authority_for_test`` 导入。
  - 新增 ``_write_minimal_project`` / ``_runtime_authority`` / ``_default_authority_project`` helper：所有 authority 必须通过 ``load_app_config`` → ``RuntimeOperations`` → ``QualityProvenanceAuthority`` 获得。
  - 新增 ``TestQualityProvenanceAuthoritySubclassRejection``：6 项回归测试覆盖 subclass 覆盖 ``judge_model``、``judge_model_digest``、``scoring_schema_version`` / ``scoring_prompt_version`` 在 build 与 verify 阶段均被拒绝。
  - 新增 ``TestQualityProvenanceAuthorityMintingBoundary``：
    - ``test_caller_local_scoring_settings_cannot_mint_authority``：断言测试 seam 已删除，且 ``LocalScoringSettings`` 作为 authority 被 ``TypeError`` 拒绝。
    - ``test_caller_fake_provenance_cannot_mint_authority``：caller-created fake provenance DTO 作为 authority 被 ``TypeError`` 拒绝。
  - 更新 ``test_real_current_config_build_and_verify_succeeds`` 与 ``test_configuration_rotation_verify_rejects`` 使用 ``tmp_path`` 通过真实 ``RuntimeOperations`` 获取 authority。
- ``tests/integration/test_runtime_composition.py``：
  - ``_project`` 增加 ``model`` / ``digest`` 参数。
  - 新增 ``test_runtime_operations_derives_authority_from_different_model_config``：证明 ``AppConfig`` 加载 ``model: different-model``、``expected_model_digest: sha256:{'1' * 64}`` 后，``RuntimeOperations`` 派生的 authority 包含完全相同的值。

## 受信边界

- 唯一 authority minting boundary：``src/youtube_intel/runtime.py`` 中的 ``_build_quality_provenance_authority``，由 ``RuntimeOperations`` composition 拥有。
- ``quality.py`` 仅接受精确类型 ``QualityProvenanceAuthority`` 的 opaque capability；subclass、property override、proxy、spoofed attribute 均在边界处被 ``TypeError`` 拒绝。
- Caller 无法通过 ``LocalScoringSettings``、fake provenance DTO、Mapping、JSON 或普通 ``QualityProvenanceAuthority(...)`` 构造绕过 sentinel 检查。

## RED Evidence

- 修正前（Round 3 Amendment 状态）：``isinstance`` 检查允许 subclass 覆盖 ``judge_model`` / ``judge_model_digest`` / ``scoring_schema_version`` / ``scoring_prompt_version`` 并通过 build/verify。
- ``_mint_quality_provenance_authority_for_test`` 在修正前存在，调用者可用任意 ``LocalScoringSettings`` mint authority。
- 本 Round 新增测试在修正前失败：
  - ``test_subclass_overriding_judge_model_rejected_by_build`` / ``..._verify``：subclass 被接受，build/verify 成功。
  - ``test_subclass_overriding_judge_model_digest_rejected_by_build`` / ``..._verify``：同上。
  - ``test_subclass_overriding_schema_prompt_rejected_by_build`` / ``..._verify``：同上。
  - ``test_caller_local_scoring_settings_cannot_mint_authority``：测试 seam 存在，``LocalScoringSettings`` 被接受。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 118 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q tests/integration/test_runtime_composition.py`` | 9 passed |
| 全量 ``uv run pytest -x -q`` | 1160 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_subclass_overriding_judge_model_rejected_by_build`` / ``..._verify``
- ``test_subclass_overriding_judge_model_digest_rejected_by_build`` / ``..._verify``
- ``test_subclass_overriding_schema_prompt_rejected_by_build`` / ``..._verify``
- ``test_caller_local_scoring_settings_cannot_mint_authority``
- ``test_caller_fake_provenance_cannot_mint_authority``
- ``test_runtime_operations_derives_authority_from_different_model_config``

## Mutation Evidence

- 临时破坏 ``src/youtube_intel/runtime.py`` 中 ``_build_quality_provenance_authority`` 的 config-to-digest 绑定，将 ``judge_model_digest=local_scoring.expected_model_digest`` 替换为固定 ``"sha256:" + "f" * 64`` 后：
  - ``tests/unit/test_task016c_quality_attestation.py`` 大量测试失败（首个失败为 ``TestQualityPassAttestationConstruction::test_valid_attestation_is_deterministic``，``ValueError: judge_model_digest does not match trusted current provenance``）。
  - ``tests/integration/test_runtime_composition.py::test_runtime_operations_mints_quality_provenance_authority_from_config`` 与 ``test_runtime_operations_derives_authority_from_different_model_config`` 的 digest 断言失败。
- 回退 mutation 后，上述测试重新通过。

## 范围验证

- ``git diff --name-only HEAD`` 仅包含：
  - ``src/youtube_intel/quality.py``
  - ``src/youtube_intel/runtime.py``
  - ``tests/unit/test_task016c_quality_attestation.py``
  - ``tests/integration/test_runtime_composition.py``
  - ``handoffs/TASK-016C.md``
- 未修改 ``providers/ollama.py``、``scoring.py``、``state.py``、DB、cache、Artifact、ProviderCall persistence、Finalizer、Phase E+、依赖、锁文件。
- ``runtime.py`` 变更范围严格限于删除测试 seam；未新增 composition 功能。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D AUTHORITY BOUNDARY INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_runtime_composition.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# Phase D Correction Round 5 — Close authority copy/serialization boundary

## 目标

关闭 Independent Review 剩余 P1： native copy/serialization 可制造出被 ``build_quality_pass_attestation`` / ``verify_quality_pass_attestation`` 接受的 ``QualityProvenanceAuthority`` 实例，绕过 runtime composition 单一边界。

## 父提交

- ``2993c688538d47dd1261e5860a2039355be6081d``

## 变更路径

- ``src/youtube_intel/quality.py``：
  - 为 ``QualityProvenanceAuthority`` 新增 ``__copy__`` / ``__deepcopy__``：抛出 ``TypeError("QualityProvenanceAuthority cannot be copied")``。
  - 新增 ``__reduce__`` / ``__reduce_ex__``：抛出 ``TypeError("QualityProvenanceAuthority cannot be serialized")``。
  - 阻止 ``copy.copy``、``copy.deepcopy``、``pickle.dumps``、``pickle.loads`` 制造 accepted authority 实例。
- ``tests/unit/test_task016c_quality_attestation.py``：
  - 新增 ``TestQualityProvenanceAuthorityCopySerialization``：
    - ``test_copy_rejected``
    - ``test_deepcopy_rejected``
    - ``test_pickle_dumps_rejected``
    - ``test_pickle_dumps_all_protocols_rejected``（参数化覆盖协议 0 至 ``pickle.HIGHEST_PROTOCOL``）
    - ``test_build_with_copy_attempt_rejected``
    - ``test_verify_with_copy_attempt_rejected``

## 受信边界

- ``QualityProvenanceAuthority`` 现在是 runtime-minted、non-copyable、non-serializable 的 opaque capability。
- 唯一来源仍为 ``RuntimeOperations`` composition 拥有的 ``_build_quality_provenance_authority``。
- 即使攻击者通过 native copy/serialization 获得一个 type 完全相同的实例，其创建操作本身会失败；无法传递到 build/verify 边界。

## RED Evidence

- 修正前（Round 4 状态）：``copy.copy(authority)`` 与 ``pickle.loads(pickle.dumps(authority))`` 可成功生成 ``QualityProvenanceAuthority`` 实例，并被 ``type(authority) is QualityProvenanceAuthority`` 接受。
- 本 Round 新增测试在修正前失败：
  - ``test_copy_rejected`` / ``test_deepcopy_rejected``：未抛出 ``TypeError``。
  - ``test_pickle_dumps_rejected`` / ``test_pickle_dumps_all_protocols_rejected``：未抛出 ``TypeError``。
  - ``test_build_with_copy_attempt_rejected`` / ``test_verify_with_copy_attempt_rejected``：copy 成功并传入 build/verify 边界。

## GREEN Evidence

| 检查 | 结果 |
|---|---|
| ``uv lock --check --offline`` | PASS |
| ``uv sync --locked --offline`` | PASS |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py`` | 124 passed |
| ``uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py`` | 60 passed, 1 warning |
| ``uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py`` | 78 passed |
| ``uv run pytest -x -q tests/integration/test_runtime_composition.py`` | 9 passed |
| 全量 ``uv run pytest -x -q`` | 1171 passed, 1 warning |
| ``uv run mypy src`` | Success (28 source files) |
| ``uv run ruff check .`` | All checks passed |
| ``git diff --check`` | PASS |

## 新增关键测试

- ``test_copy_rejected``：``copy.copy(authority)`` 抛出 ``TypeError``。
- ``test_deepcopy_rejected``：``copy.deepcopy(authority)`` 抛出 ``TypeError``。
- ``test_pickle_dumps_rejected``：``pickle.dumps(authority)`` 抛出 ``TypeError``。
- ``test_pickle_dumps_all_protocols_rejected``：所有 pickle 协议均抛出 ``TypeError``。
- ``test_build_with_copy_attempt_rejected``：无法将 copied authority 传入 ``build_quality_pass_attestation``。
- ``test_verify_with_copy_attempt_rejected``：无法将 copied authority 传入 ``verify_quality_pass_attestation``。

## Mutation Evidence

- 临时注释 ``src/youtube_intel/quality.py`` 中 ``QualityProvenanceAuthority`` 的 ``__copy__`` / ``__deepcopy__`` / ``__reduce__`` / ``__reduce_ex__`` 后：
  - ``TestQualityProvenanceAuthorityCopySerialization::test_copy_rejected`` 失败（DID NOT RAISE ``TypeError``）。
- 回退 mutation 后，上述测试重新通过。

## 范围验证

- ``git diff --name-only HEAD`` 仅包含：
  - ``src/youtube_intel/quality.py``
  - ``tests/unit/test_task016c_quality_attestation.py``
  - ``handoffs/TASK-016C.md``
- 未修改 ``src/youtube_intel/runtime.py``、``providers/ollama.py``、``scoring.py``、``state.py``、DB、cache、Artifact、ProviderCall persistence、Finalizer、Phase E+、依赖、锁文件。

## 设计偏差

- NONE

## 建议状态

`READY FOR PHASE D AUTHORITY BOUNDARY INDEPENDENT REVIEW`

- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
  uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
  uv run pytest -x -q tests/unit/test_task016c_quality_judge_contract.py
  uv run pytest -x -q tests/integration/test_runtime_composition.py
  uv run pytest -x -q
  uv run mypy src
  uv run ruff check .
  git diff --check
  ```
- 设计偏差：NONE

---

# TASK-016C Phase F 交接报告 — PRIMARY In-Memory Trusted Scoring Seam

## 元数据

- Task: `TASK-016C Phase F`
- Role: `Implementer`
- Agent/session: WorkBuddy
- Base/authorization commit: `acdaac1dbc0899e2b2b6e9871b1a734c7edb136e`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Head commit: `c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- Direct parent: `acdaac1dbc0899e2b2b6e9871b1a734c7edb136e`
- Commit message: `TASK-016C Phase F implement primary in-memory trusted scoring seam`
- 祖先核验（单父链，无 squash/rebase/rewrite，全部通过）：
  - Phase D 基线 `2c11faf41e17c3b823a39bfd1018c5c876b236c5` = ancestor ✓
  - Phase E 基线 `9b92946a3c156a7c365d808f92f7a1734dcca874` = ancestor ✓
  - Phase F Round 4 设计 `e00f9579bed3ad91a088c7f9a378cb0808308045` = ancestor ✓
  - Phase F authorization `acdaac1dbc0899e2b2b6e9871b1a734c7edb136e` = HEAD^ ✓
- 工作树：tracked 文件干净（仅 untracked `.workbuddy/`，按要求不读取/不提交）。

## 目标与范围

- 任务目标：实现 PRIMARY-only、candidate-only、memory-only 的 trusted scoring seam：
  ```text
  Provider raw response → 唯一 canonical parser → ScoringCandidate
  → candidate/request/raw binding → schema/language/quality → QualityPassAttestation
  → TrustedScoringFinalizer → TrustedScoreResult → PhaseFTrustedScoringSuccess
  ```
- 实际修改（4 文件，+1518/−2）：
  - `src/youtube_intel/providers/ollama.py`（+97）：抽取唯一 canonical parser `parse_scoring_candidate`（bounded raw → strict UTF-8 → JSON → subset-field → `ScoringCandidate.model_validate`）；`OllamaScoringProvider.primary_attempt()` 单次生成 attempt、无 repair path。
  - `src/youtube_intel/scoring.py`（+378）：`PrimaryScoringAttempt`（frozen，10 字段）、`build_primary_scoring_attempt`（exact-type → 重 parse → candidate 相等核对 → identity 重建 → 双 hash）、`mint_phase_f_trusted_scoring_success`（sealed 三 hash、private sentinel、防 copy/deepcopy/pickle/subclass）、`run_primary_trusted_scoring_seam`（全部 binding 再校验 + Finalizer + mint）。顶层不 import `quality`/`ollama`（函数内 lazy import，满足 import-graph 约束）。
  - `src/youtube_intel/runtime.py`（+38）：`RuntimeOperations.run_primary_trusted_scoring()` 薄包装；默认/legacy dispatch 不变。
  - `tests/unit/test_task016c_phase_f.py`（+1007）：28 个 focused 测试。
- 明确未做（授权禁止范围，均未触碰）：
  - 未修改 `state.py`、`quality.py`、`domain.py`、`pyproject.toml`、`uv.lock`。
  - 无 DB/migration、Artifact/cache persistence、ProviderCall completion、filesystem commit protocol、repair/retry/budget/recovery。
  - 无真实 Ollama/network/cloud/Vault/凭据调用；全程离线。
  - 未改变 transport、loopback、model/download/fallback/network semantics；未改 TASK-016B Language Validator；未改默认 persisted runtime dispatch。

## TDD RED Evidence

- 首次运行（RED，收集阶段即失败）：
  ```text
  ImportError: cannot import name 'parse_scoring_candidate' from 'youtube_intel.providers.ollama'
  ```
- 随后以最小 GREEN 逐项点亮 28 个 focused 测试；RED-first 成立（测试先于实现存在并失败）。

## GREEN Evidence

- `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` → `28 passed`
- 28 测试清单（覆盖 Authorization 8 项 TDD/对抗验收、5 项 mutation proof、checklist Implementer Completion 10 项与 Reviewer Matrix 8 项）：
  1. `test_provider_primary_attempt_returns_candidate_only_continuation` — Provider 只产生 Candidate/Attempt，非 `ScoreResult`；2 次 HTTP（GET+POST），无 repair
  2. `test_candidate_business_fields_match_score_result_contract` — candidate 业务字段兼容 `ScoreResult` 契约
  3. `test_attempt_factory_rejects_raw_a_candidate_b` — raw A + candidate B fail-closed
  4. `test_attempt_factory_rejects_post_parse_candidate_mutation` — post-parse candidate mutation 拒绝
  5. `test_attempt_factory_rejects_bare_score_result_candidate` — bare `ScoreResult` 不能充当 candidate
  6. `test_attempt_factory_rejects_mapping_candidate` — Mapping candidate 拒绝
  7. `test_attempt_factory_rejects_oversized_raw` — oversized raw（>1MB）fail-closed
  8. `test_attempt_factory_rejects_invalid_utf8_raw` — invalid UTF-8（`\ud800`）fail-closed
  9. `test_attempt_factory_rejects_oversized_inner_response` — inner response >20k chars 拒绝
  10. `test_one_byte_raw_mutation_changes_raw_hash` — 一 byte raw mutation 改变 raw hash（candidate hash 不变）
  11. `test_semantically_equal_different_bytes_raw_hash_differs` — 语义相同 bytes 不同 JSON → raw hash 不同
  12. `test_attempt_is_frozen_and_exact_type` — attempt frozen + exact-type
  13. `test_seam_rejects_attempt_raw_hash_mismatch` — seam raw hash 再校验拒绝
  14. `test_seam_rejects_attempt_candidate_hash_mismatch` — seam candidate hash 再校验拒绝
  15. `test_seam_rejects_attempt_candidate_not_from_raw` — candidate 非 canonical parse 产物拒绝
  16. `test_seam_rejects_request_identity_mismatch` — request identity mismatch 拒绝
  17. `test_seam_rejects_provider_model_digest_mismatch` — provider/model/digest mismatch 拒绝
  18. `test_seam_rejects_non_primary_attempt_role` — 非 PRIMARY role 拒绝
  19. `test_seam_rejects_bare_score_result` — legacy isolation：bare `ScoreResult` exact-type 拒绝
  20. `test_seam_rejects_mapping_and_json_in_attempt_slot` — legacy isolation：Mapping/JSON exact-type 拒绝
  21. `test_primary_flow_reaches_phase_f_trusted_scoring_success` — 合法 PRIMARY 流到达 aggregate
  22. `test_trusted_result_alone_is_not_a_phase_f_success` — TrustedResult 单独 ≠ envelope（mint 拒绝）
  23. `test_language_failure_blocks_success_aggregate` — language 失败（zh-CN reason + en output_language）阻止 aggregate
  24. `test_quality_reject_blocks_success_aggregate` — quality REJECT（DETERMINISTIC_GATE EMPTY_CONTENT）阻止 aggregate
  25. `test_attestation_mismatch_blocks_success_aggregate` — 异 candidate attestation 阻止 aggregate
  26. `test_success_mint_rejects_forged_trusted_result` — 伪造 TrustedResult exact-type 拒绝
  27. `test_success_aggregate_is_opaque_immutable_and_non_serializable` — 直接构造/copy/deepcopy/pickle/subclass/`_sealed` 变更全拒绝
  28. `test_primary_flow_has_zero_persistence_and_no_legacy_service` — 零持久化（快照相等）+ 无 legacy service

## Mutation Evidence（每项删除 → 对应测试失败 → 立即恢复）

1. **M1** 删除 raw reparse（canonical 重 parse 与 candidate 相等核对）→ `test_seam_rejects_attempt_candidate_not_from_raw` FAILED
2. **M2** 删除 raw-hash comparison（seam + mint 两层同时删除）→ `test_seam_rejects_attempt_raw_hash_mismatch` FAILED
3. **M3** 删除 candidate-hash comparison（seam + mint 两层同时删除）→ `test_seam_rejects_attempt_candidate_hash_mismatch` FAILED
4. **M4** 删除 exact-type trusted-result guard → `test_success_mint_rejects_forged_trusted_result` FAILED（AttributeError）
5. **M5** 删除 legacy isolation guard → `test_seam_rejects_bare_score_result` 与 `test_seam_rejects_mapping_and_json_in_attempt_slot` FAILED
- 全部恢复后：`28 passed` 复确认；无 mutation 残留标记。

## Raw→Candidate Binding Evidence

- 唯一 canonical parser：`parse_scoring_candidate`（`providers/ollama.py`），F 与未来 G 共用；无重复 parser 或 candidate-hash 算法。
- `raw_response_hash = SHA-256(final_raw_response.encode("utf-8"))` 对 exact response-body bytes；不使用 `payload["response"]`、截断值或 reserialized JSON。
- attempt factory 顺序：exact-type 检查 → 重 parse raw → candidate 相等核对 → identity 重建 → candidate/raw hash 计算。
- seam 与 mint 双重再校验：raw hash、candidate hash、canonical reparse、identity（request/normalized hash）、provider/model/digest。
- 测试证明：一 byte raw mutation 改变 raw hash 且不影响 candidate hash；语义相同而 bytes 不同的 JSON 具有不同 raw hash。

## 零副作用 / 零持久化 Evidence

- seam 全程不实例化、不调用 `RepositoryBackedScoringService`（该名称仅出现在 docstring 中）。
- seam 签名不含 provider handle。
- `test_primary_flow_has_zero_persistence_and_no_legacy_service`：项目根与 `data/` 目录 before/after 快照逐项相等（`bootstrap_runtime` 在组合期创建 `data/`，故以快照相等证明零写入）。
- grep 确认 seam 代码无 `state`/`Artifact`/`Cache`/`ProviderCall`/`data_dir`/`Path(` 写入引用；无 repair/retry/budget。

## Legacy Isolation Evidence

- seam 入口 exact-type guard：bare `ScoreResult`、legacy output/raw、Mapping、JSON 均以 `match="PrimaryScoringAttempt"` 拒绝。
- trusted path 永不触达 `ScoreResult`（Finalizer 内部短暂构造 `TrustedScoreResult`，与 legacy `ScoreResult` 类型隔离）。
- `RuntimeOperations → RepositoryBackedScoringService → ScoreResult → persistence` 保持 PRE-TASK-016C COMPATIBILITY PATH 未改动。

## 必须门禁（全部 PASS）

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | Resolved 107 packages, PASS |
| 2 | `uv sync --locked --offline` | Checked 84 packages, PASS |
| 3 | focused Phase F tests | `28 passed` |
| 4 | Phase A–E trust tests（5 个既有 task016c unit 文件 + `test_scoring_language.py`） | `417 passed, 1 warning` |
| 5 | `uv run --offline pytest -x -q`（全量） | `1202 passed, 1 warning`（46s） |
| 6 | `uv run --offline mypy src` | `Success: no issues found in 28 source files` |
| 7 | `uv run --offline ruff check . --output-format concise` | `All checks passed!` |
| 8 | `uv build --offline` | `dist/youtube_intel-0.1.0.tar.gz` + `py3-none-any.whl` 构建成功 |
| 9 | `bash scripts/security_scan.sh` | `status=clean`（仅既有 high-entropy-warn/test artifacts + license WARN） |
| 10 | `git diff --check` | `DIFF-CHECK-CLEAN` |

- 全部命令 `--offline`：uv 在线解析 `en-core-web-sm==3.8.0` 曾报网络/TLS 失败，统一离线后稳定；无下载、无联网、无真实模型调用。

## Reuse Decision

- `parse_scoring_candidate`：由 `ollama.py` 既有 parse 逻辑抽取为唯一 canonical parser（`ADAPT`，同文件内抽取，无新增依赖）。
- `build_scoring_candidate_hash` / `TrustedScoringFinalizer` / `ScoreResult.model_validate`（language fail-closed 强制点，domain.py:825-832）：复用 `quality.py` 既有实现（`DIRECT`，未复制算法）。
- `RepositoryBackedScoringService`：`REJECT/DEFER`——seam 不调用 legacy persistence path，属 Phase G 范围。
- 未新增依赖、未修改 lockfile。

## 设计偏差

1. provider/model mismatch 错误消息措辞加入 `"provider"` 子串（如 `"attempt provider model mismatches..."`、`"attempt provider model digest mismatches the trusted scoring context"`），以满足 `match="provider"` 断言。仅消息措辞，校验行为不变。
2. raw/candidate hash 校验同时存在于 seam 与 mint 两层（defense-in-depth）。单层删除不足以使测试失败，需两层同时删除才暴露——比授权最低要求更强；已作为 M2/M3 mutation 证据记录。

## 失败、跳过与风险

- 已解决失败：
  - uv 在线解析 `en-core-web-sm==3.8.0` 网络/TLS 失败 → 统一 `uv run --offline` / `uv sync --locked --offline`。
  - ruff F401（TYPE_CHECKING 未用导入）与 F841（未用局部变量）→ 清理后通过。
  - `data/` 存在性断言误报（`bootstrap_runtime` 组合期建目录）→ 改为 before/after 快照相等断言。
- 跳过检查及原因：真实 Ollama/network/cloud 执行——授权明确禁止，未执行。
- 剩余风险：
  - 本 seam 为非生产、PRIMARY-only、memory-only；未做默认 runtime cutover（属 Phase G）。
  - `PrimaryScoringAttempt` 是 untrusted continuation，生命周期仅限 aggregate handoff。
- `DECISION NEEDED`：`None`

## 实现者结论

- 建议状态：`READY FOR PHASE F INDEPENDENT REVIEW`
- Commit SHA：`c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- 直接父提交：`acdaac1dbc0899e2b2b6e9871b1a734c7edb136e`
- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
  uv run --offline pytest -x -q tests/unit/test_task016c_domain_contracts.py tests/unit/test_task016c_finalizer.py tests/unit/test_task016c_quality_attestation.py tests/unit/test_task016c_quality_gate.py tests/unit/test_task016c_quality_judge_contract.py tests/unit/test_scoring_language.py
  uv run --offline pytest -x -q
  uv run --offline mypy src
  uv run --offline ruff check .
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check
  ```

---

## Phase F Correction Round 1

### 审查状态

- 触发审查的 implementation commit：`c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- Review verdict：`REQUEST CHANGES`
- 本次 correction implementation commit：`df920cc268f732a5c809ba3d9e0c6b98ea1f44b0`
- 本次直接父提交：`c0268a2157d7b9bb99bdc888b2ee493655bbbaa2`
- 目标状态：`READY FOR PHASE F CORRECTION INDEPENDENT REVIEW`

### 关闭的 P1/P2 问题

- **P1-1** public aggregate mint bypass
  - `mint_phase_f_trusted_scoring_success` 从 `scoring.__all__` 移除并改名为 `_mint_phase_f_trusted_scoring_success`
  - mint 增加 raw reparse 检查：`parse_scoring_candidate(final_raw_response) == attempt.candidate`
  - mint 增加 business-field binding：trusted result 的 score/reason/topics/should_summarize/dimensions 必须与 attempt.candidate 一致
- **P1-2** deterministic gate + Local Judge ordering 缺失
  - `RuntimeOperations.run_primary_trusted_scoring` 现在只接受 `attempt` 和 `scoring_input`
  - 内部构造 `ContentQualityInput`
  - 执行 `DeterministicContentQualityGate.evaluate()`，reject 则 fail closed
  - 执行 `OllamaQualityJudgeProvider.judge()`，非 PASS 则 fail closed
  - 内部用 `self._quality_provenance_authority` 构建 `QualityPassAttestation`
  - 最后调用 private `_run_primary_trusted_scoring_seam`
- **P1-3** runtime caller-selected authority/context
  - `run_primary_trusted_scoring` 不再接受 `quality_authority` / `scoring_context` / 任何 quality material
  - 统一使用 `self._quality_provenance_authority` 和 `self._trusted_scoring_context`
- **P1-4** committed handoff evidence
  - 本 handoff 作为单独 commit 提交
- **P2** provider/model/digest 独立回归测试
  - 新增 `test_seam_rejects_provider_mismatch`
  - 新增 `test_seam_rejects_model_mismatch`
  - 新增 `test_seam_rejects_digest_mismatch_independent`

### RED Evidence

在修代码前加入 RED tests，记录失败证据：

- `test_mint_is_not_a_public_export` FAILED（mint 仍在 `__all__`）
- `test_seam_is_not_a_public_export` FAILED（seam 仍在 `__all__`）
- `test_mint_rejects_raw_a_candidate_b_bypass` FAILED（mint 接受 raw A + candidate B + legitimate TrustedScoreResult B）
- `test_mint_rejects_business_field_mismatch` FAILED（mint 接受 TrustedScoreResult B + attempt A）
- `test_deterministic_gate_blocks_exact_repetition` FAILED / TypeError（runtime 方法仍要求 8 个 kwargs）
- `test_deterministic_reject_prevents_judge_call` FAILED / TypeError
- `test_judge_non_pass_prevents_trusted_success` FAILED / TypeError
- `test_judge_failure_prevents_trusted_success` FAILED / TypeError
- `test_runtime_rejects_quality_authority_param` FAILED（runtime 接受 `quality_authority`）
- `test_runtime_rejects_scoring_context_param` FAILED（runtime 接受 `scoring_context`）
- 合计：10 failed, 31 passed

### GREEN Evidence

- `uv run pytest tests/unit/test_task016c_phase_f.py -q` → `41 passed`

### Mutation Proofs（M1–M6）

每次 mutation 后运行完整 Phase F 测试，记录失败测试，然后恢复并复现 `41 passed`：

- **M1** 删除 mint 所有校验 → `test_trusted_result_alone_is_not_a_phase_f_success`、`test_success_mint_rejects_forged_trusted_result`、`test_mint_rejects_raw_a_candidate_b_bypass`、`test_mint_rejects_business_field_mismatch` FAILED
- **M2** 删除 seam 与 mint 的 raw reparse → `test_seam_rejects_attempt_candidate_not_from_raw`、`test_mint_rejects_raw_a_candidate_b_bypass` FAILED
- **M3** 删除 deterministic gate → `test_quality_reject_blocks_success_aggregate`、`test_deterministic_gate_blocks_exact_repetition`、`test_deterministic_reject_prevents_judge_call` FAILED
- **M4** 将 Judge 调用替换为 synthetic PASS → `test_judge_non_pass_prevents_trusted_success`、`test_judge_failure_prevents_trusted_success` FAILED
- **M5** 允许 `quality_authority` 参数 → `test_runtime_rejects_quality_authority_param` FAILED
- **M6** 允许 `scoring_context` 参数 → `test_runtime_rejects_scoring_context_param` FAILED

### 10 Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | focused Phase F tests | `41 passed` |
| 4 | Phase A–E trust tests | `316 passed, 1 warning` |
| 5 | `uv run pytest -x -q` | `1215 passed, 1 warning` |
| 6 | `uv run mypy src` | PASS |
| 7 | `uv run ruff check .` | PASS |
| 8 | `uv build --offline` | PASS |
| 9 | `bash scripts/security_scan.sh` | `status=clean` |
| 10 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`tests/unit/test_task016c_phase_f.py`、`handoffs/TASK-016C.md`
- 未修改 `state.py`、DB、migration、Artifact/cache persistence、ProviderCall completion、filesystem protocol、repair/retry、依赖或 lockfile
- 未进入 Phase G
- 未 rebase / squash / amend / merge / push / tag

### Diff Review

- `scoring.py`：将 mint/seam 私有化；mint 增加 raw reparse + business-field binding
- `runtime.py`：`run_primary_trusted_scoring` 改为仅接受 `attempt`/`scoring_input`；内部执行 gate → Judge → attestation → private seam；新增 `quality_judge_provider_factory` 测试注入点
- `tests/unit/test_task016c_phase_f.py`：新增 13 个 RED/regression 测试，更新现有 runtime 测试至新 API

### Reuse Decision

- `DeterministicContentQualityGate`：`DIRECT`（`quality.py` 已有）
- `OllamaQualityJudgeProvider`：`DIRECT`（`providers/ollama.py` 已有）
- `build_quality_pass_attestation` / `TrustedScoringFinalizer`：`DIRECT`（`quality.py` 已有）
- 未新增依赖

### 失败、跳过与风险

- 已解决：
  - RED tests 中部分 `quality_authority`/`scoring_context` 拒绝测试因额外 kwargs 产生误报 → 改为仅传入目标 extra param，使用 `_judge_runtime` 提供 fake Judge
  - exact repetition 测试 reason 因语言检测失败提前退出 → 改用 "This video explains product strategy.\nThis video explains product strategy."
- 跳过：真实 Ollama/network/cloud 执行（授权禁止）
- 剩余风险：
  - 本 seam 仍为非生产、PRIMARY-only、memory-only
  - `RuntimeDependencies.quality_judge_provider_factory` 仅用于测试注入

### 实现者结论

- 建议状态：`READY FOR PHASE F CORRECTION INDEPENDENT REVIEW`
- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
  uv run --offline pytest tests/unit/test_task016c_quality_gate.py tests/unit/test_task016c_quality_judge_contract.py tests/unit/test_task016c_domain_contracts.py tests/unit/test_task016c_quality_attestation.py tests/unit/test_task016c_finalizer.py -q
  uv run --offline pytest -x -q
  uv run --offline mypy src
  uv run --offline ruff check .
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check
  ```

## Phase G Implementation

- Status: `READY FOR PHASE G INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Implementation baseline: `bff2b7d514ce4d65f5a2b68d976c5085539e728d`
- Role: Implementer (continuation/recovery)

### 目标与范围

- 任务目标：实现 TASK-016C Phase G trusted prewrite persistence cutover：
  `PREWRITE_VALIDATE -> ValidatedScoringWritePlan -> tmp/fsync/promote -> atomic SQLite registration -> normal scoring-stage cutover`。
- 允许修改：
  - `src/youtube_intel/scoring.py`
  - `src/youtube_intel/runtime.py`
  - `src/youtube_intel/state.py`
  - `tests/unit/test_task016c_phase_g.py`
  - 为 Phase G API 适配所必需的既有集成测试
  - `handoffs/TASK-016C.md`
- 实际修改：
  - `src/youtube_intel/scoring.py`：
    - 向后兼容地 enrich `PhaseFTrustedScoringSuccess`，封存 canonical ScoringInput/quality input/quality result/quality operation/attestation 与 sealed structured-result bytes/hashes；
    - 新增 `_EnrichedQualityEvidence`、`_sealed_trusted_score_result_serializer`；
    - 新增 `TrustedScoringPersistenceCommitter` 与 opaque `ValidatedScoringWritePlan`；
    - 实现 zero-write `prewrite_validate`（exact aggregate、bytes/hash 自洽、domain reconstruction、raw/candidate binding、business-field binding、request identity、runtime authority rotation、quality attestation、raw envelope/structured serialization）；
    - 实现 ordered filesystem writer（tmp exclusive create -> fsync -> hash/length verify -> no-clobber promote -> parent-directory fsync -> final reopen verify）；
    - 实现 `commit` 调用 `SQLiteStateRepository.atomic_register_scoring_success`。
  - `src/youtube_intel/runtime.py`：
    - 新增 `_trusted_scoring_committer` runtime-owned factory；
    - `scoring_stage` 唯一 cutover 到 `build_scoring_input -> primary_attempt -> run_primary_trusted_scoring -> prewrite_validate -> commit`；
    - `_validate_scoring_provenance` 接受 Phase G 新的 producer versions 与 schema/prompt 版本，保持 legacy 读取兼容。
  - `src/youtube_intel/state.py`：
    - 新增 `atomic_register_scoring_success`，在同一 SQLite IMMEDIATE transaction 内完成：验证 RUNNING SCORING job、upsert raw/structured Artifact rows、reserve+complete scoring 与 Judge ProviderCall、更新 video score/threshold/stage、完成 job。
  - `tests/unit/test_task016c_phase_g.py`：新增 21 项 Phase G 焦点测试，覆盖 enriched aggregate、PREWRITE_VALIDATE zero-write、filesystem ordering、atomic registration、idempotency、wrong owner/status、artifact hash binding、runtime cutover、legacy isolation、M1–M10 对抗矩阵。
  - `tests/integration/test_runtime_composition.py` 与 `tests/integration/test_task015_p1_fix.py`：适配 `primary_attempt` API 与 `_QualityJudgeProvider`。
- 明确未做：
  - repair/retry/budget、unknown/crash recovery engine、cache recovery/hardening；
  - 真实 Ollama/network/Cloud/Vault/credential 调用；
  - DB schema/migration、新依赖、`uv.lock`、pyproject.toml；
  - GUI、Web、多用户、V2 数据源；
  - Phase H/I 功能。

### 验收证据

| 验收项 | PASS/FAIL | 证据 |
|---|---|---|
| AC-1: PREWRITE_VALIDATE 零写入且只接受 exact `PhaseFTrustedScoringSuccess` | PASS | `test_prewrite_validate_creates_plan_without_side_effects`、`test_prewrite_validate_rejects_non_aggregate`、`test_prewrite_validate_rejects_unenriched_aggregate` |
| AC-2: filesystem 写入顺序与 no-clobber promote | PASS | `test_commit_writes_raw_and_structured_files`、`test_commit_raises_when_final_file_already_exists`、`test_commit_raises_when_temporary_file_already_exists` |
| AC-3: SQLite 原子登记两 Artifact + 两 ProviderCall + stage/job | PASS | `test_atomic_register_scoring_success_commits_all_rows`、`test_atomic_register_is_idempotent_for_filesystem_then_sqlite_retry` |
| AC-4: runtime scoring-stage 唯一走 trusted route | PASS | `test_scoring_stage_uses_trusted_route`、`test_repository_backed_scoring_service_remains_available_but_not_used` |
| AC-5: M1–M10 mutation matrix 先 RED 再 GREEN | PASS | 见下方 Mutation Proofs |
| AC-6: 全量 gates 通过 | PASS | 见下方 Gates |

### Mutation Proofs（M1–M10）

每次 mutation 临时删除/弱化一个 guard，确认至少一个对应测试失败，然后恢复并复现 `21 passed`：

- **M1** exact success guard：将 `if type(success) is not PhaseFTrustedScoringSuccess` 改为 `if False` → `test_prewrite_validate_rejects_non_aggregate` FAILED
- **M2** raw hash：将 `if raw_response_hash != primary_attempt.raw_response_hash` 改为 `if False` → `test_prewrite_validate_rejects_raw_response_hash_mutation` FAILED
- **M3** raw reparse：将 `if reparsed_candidate != candidate` 改为 `if False` → `test_prewrite_validate_rejects_raw_reparse_mutation` FAILED
- **M4** candidate/result binding：将 business-field binding check 改为 `if False` → `test_prewrite_validate_rejects_candidate_result_binding_mutation` FAILED
- **M5** runtime authority/context：将 `if primary_attempt.provider != context.scoring_provider` 改为 `if False` → `test_prewrite_validate_rejects_runtime_authority_rotation` FAILED
- **M6** ProviderCall request binding：将 `if scoring_call_request.request_hash != identity.request_hash` 改为 `if False` → `test_prewrite_validate_rejects_provider_call_request_binding_mutation` FAILED
- **M7** Artifact content/hash binding：将 runtime `_verified_artifact` 中 `hashlib.sha256(body).hexdigest() != record.content_hash` 改为 `if False` → `test_load_scoring_rejects_corrupted_structured_artifact` FAILED
- **M8** prewrite-before-write ordering：将 `if tmp_path.exists()` 改为 `if False` → `test_commit_raises_when_temporary_file_already_exists` FAILED
- **M9** bare-result compatibility re-entry：将 `run_primary_trusted_scoring` 中 `type(attempt) is not PrimaryScoringAttempt` 改为 `if False` → `test_scoring_stage_rejects_bare_score_result_reentry` FAILED
- **M10** stage-completion ordering：将 `atomic_register_scoring_success` 中 video `pipeline_status = :expected_status` 条件去掉 → `test_atomic_register_fails_on_wrong_pipeline_status` FAILED（commit 成功而非 fail-closed）

### 10 Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `21 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | `uv run --offline pytest -x -q` | `1236 passed, 1 warning` |
| 6 | `uv run --offline mypy src` | PASS |
| 7 | `uv run --offline ruff check .` | PASS |
| 8 | `uv build --offline` | PASS |
| 9 | `bash scripts/security_scan.sh` | `status=clean` |
| 10 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`tests/integration/test_runtime_composition.py`、`tests/integration/test_task015_p1_fix.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend / merge / push / tag
- 仅一笔 Phase G implementation commit

### Diff Review

- `scoring.py`：新增 Phase G committer/plan、enriched aggregate、sealed serializer、prewrite validator、ordered file writer
- `runtime.py`：trusted scoring-stage cutover、committer factory、provenance acceptance for Phase G artifacts
- `state.py`：原子 `atomic_register_scoring_success` transaction
- `tests/unit/test_task016c_phase_g.py`：21 项新测试覆盖 trust/persistence/cutover/mutation
- 集成测试适配：mock provider 使用 `primary_attempt` API 并提供 `_QualityJudgeProvider`

### Reuse Decision

- `SQLiteStateRepository` 与 `_immediate_transaction`：`DIRECT`（`state.py` 已有）
- `ProviderCallRequest` / `ArtifactWrite` / `StageCompletionResult`：`DIRECT`（`state.py` 已有）
- `TrustedScoringFinalizer` / `QualityProvenanceAuthority` / `TrustedScoringContext`：`DIRECT`（`quality.py` 已有）
- `parse_scoring_candidate` / `build_scoring_candidate_hash`：`DIRECT`（`providers/ollama.py` / `quality.py` 已有）
- 未新增依赖

### 失败、跳过与风险

- 已解决：
  - 继续前 Recovery Audit 确认工作区处于 Phase G 部分实现、集成测试 RED 状态
  - 修复 mock provider API 不兼容（`primary_attempt` + `_QualityJudgeProvider`）
  - 修复 runtime provenance 校验未适配 Phase G artifacts 的问题
  - 调整 M4/M6 测试以匹配实际 fail-closed guard 顺序（business binding 先于 structured bytes；ProviderCall request binding 通过替换 committer context 触发）
  - 新增 M7（artifact hash binding）、M9（bare-result re-entry）、M10（stage-completion ordering）显式 RED 测试与 mutation 证据
- 跳过：真实 Ollama/network/cloud 执行（授权禁止）
- 剩余风险：
  - 跨 filesystem/SQLite 崩溃恢复、cache verification/hardening、retry/repair 仍属于 Phase H/I
  - G 仅覆盖 normal-success path，PENDING/FAILED/partial/legacy conflict 均 fail-closed 并留给 H/I

### 实现者结论

- 建议状态：`READY FOR PHASE G INDEPENDENT REVIEW`
- 复现/验证说明：
  ```bash
  uv lock --check --offline
  uv sync --locked --offline
  uv run --offline pytest tests/unit/test_task016c_phase_g.py -q
  uv run --offline pytest tests/unit/test_task016c_phase_f.py -q
  uv run --offline pytest -x -q
  uv run --offline mypy src
  uv run --offline ruff check .
  uv build --offline
  bash scripts/security_scan.sh
  git diff --check
  ```

## Phase G Correction Round 1

- Status: `SUPERSEDED BY ROUND 2`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Correction commit: `b4497cf`
- Handoff commit: `6900b76`
- Role: Implementer (continuation/recovery)

### Correction Scope

本次 correction 仅关闭 Phase G 独立审查前发现的三个 P1 阻塞，不进入 Phase H/I，不重新设计/回滚/扩大范围：

| P1 | 位置 | 修复内容 |
|---|---|---|
| P1-1 Atomic No-Clobber Promote | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._write_atomic_file()` | 将 `exists()+os.rename()` 改为 `os.link(tmp, final)+os.unlink(tmp)` 原子 no-replace promote；保留 tmp write、fsync、hash/length verify、dir fsync、final reopen verify |
| P1-2 Strict Same-Plan Idempotency | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._check_committed_graph()` / `commit()` | 同一 plan 重复 commit 时，先验证完整 committed graph：raw/structured final 文件存在且 hash/length/path 匹配；Artifact rows、两个 SUCCEEDED ProviderCall、video SCORED、job SUCCEEDED 全部一致才返回已有结果；否则 fail-closed（不修复、不 recall provider） |
| P1-3 Close `atomic_register` Bypass | `src/youtube_intel/state.py` `_atomic_register_scoring_success()` / `ScoringRegistrationCapability` | 注册入口改为私有 `_atomic_register_scoring_success()`，仅接受内部 sentinel-mint 的 `ScoringRegistrationCapability`；普通 `ArtifactWrite`/`ProviderCall`/Mapping/JSON/object 全部拒绝；DB boundary 再防御性验证 final files 存在且 hash 匹配 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正以下 RED→GREEN 测试：

- **R1** no-clobber race：`test_r1_promote_does_not_overwrite_existing_final`、`test_r1_promote_uses_atomic_link_not_rename`
- **R2** strict same-plan idempotency：`test_r2_same_plan_after_commit_is_idempotent`、`test_r2_same_plan_with_raw_file_corrupt_rejects`、`test_r2_same_plan_with_partial_db_graph_rejects`、`test_r2_idempotent_retry_does_not_rewrite_files`
- **R3** direct registrar bypass：`test_r3_direct_repository_call_with_ordinary_dtos_rejects`、`test_r3_ordinary_capability_substitute_rejects`
- **R4** SQLite-after-promote failure semantics：`test_r4_sqlite_failure_leaves_promoted_finals`
- **R5** filesystem fault injection：`test_r5_temp_write_failure_no_sqlite_registration`、`test_r5_sqlite_transaction_rollback_no_partial_graph`
- **M14** final-file verification：`test_m14_registration_rejects_missing_final_files`

### Mutation Matrix（M1–M15）

使用 `run_mutation_matrix.py` 临时修改并恢复，每项至少导致一个测试失败：

| Mutation | 目标 | 结果 |
|---|---|---|
| M1 | `prewrite_validate` exact success guard → `if False` | KILLED |
| M2 | raw hash check → `if False` | KILLED |
| M3 | raw reparse check → `if False` | KILLED |
| M4 | candidate/result binding → `if False` | KILLED |
| M5 | runtime authority/context check → `if False` | KILLED |
| M6 | ProviderCall request binding → `if False` | KILLED |
| M7 | runtime artifact content/hash binding → `if False` | KILLED |
| M8 | stale-tmp O_EXCL guard 移除 | KILLED |
| M9 | `run_primary_trusted_scoring` PrimaryScoringAttempt exact-type guard → `if False` | KILLED |
| M10 | `_atomic_register_scoring_success` 跳过 job finish | KILLED |
| M11 | `_write_atomic_file` 将 `os.link` 改回 `os.rename` | KILLED |
| M12 | `commit()` 删除 complete-graph idempotency verification | KILLED |
| M13 | `_atomic_register_scoring_success` 删除 `ScoringRegistrationCapability` type guard | KILLED |
| M14 | `_atomic_register_scoring_success` 删除 final-file hash verification | KILLED |
| M15 | `commit()` 将 DB registration 提前到 promoted finals 之前 | KILLED |

Mutation 脚本本身未提交；生产代码在所有 mutation 恢复后 GREEN。

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline --dry-run` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `33 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E trust + TASK-016B regression | `417 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1248 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN/mutation 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 2

- Status: `SUPERSEDED BY ROUND 3`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1` (HEAD)
- Role: Implementer (continuation/recovery)

### Correction Scope

本次 correction 关闭 Round 1 Independent Review 的 REQUEST CHANGES，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1 | 位置 | 修复内容 |
|---|---|---|
| P1-1 Complete Graph Idempotency | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._check_committed_graph()` | 完整比较 committed graph：Filesystem（absolute controlled path、relative path、bytes、sha256、length）、Artifact rows（artifact_id/kind/path/relative_path/content_hash/size via length/provider/model/producer_version/retention_class/expires_at）、ProviderCall rows（provider/model/request_hash/operation/status/response_artifact_id/prompt_version/schema_version）、Video（score/should_summarize）、Job（job_id binding/stage/status/provenance）。任何 mismatch 均 fail-closed（不修复、不 recall provider） |
| Plan Expected Metadata | `ValidatedScoringWritePlan` | 新增 `raw_envelope_length` 与 `structured_length`，由 PREWRITE validated capability 携带，作为 single source of truth |
| P1-2 Registration Capability Authority | `src/youtube_intel/state.py` / `src/youtube_intel/scoring.py` | 关闭 `state.py` 的 `_mint_scoring_registration_capability()`；mint 能力完全内化为 `TrustedScoringPersistenceCommitter._mint_registration_capability()`；capability 新增 `_provenance_token`（SHA256 binding of job/owner/video/pipeline_version/artifact_ids/request_hashes/file_hashes）；registrar 重新计算并验证 token；普通 caller 无法 import mint、无法构造合法 capability、无法 copy/pickle/修改字段 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正以下 RED→GREEN 测试：

- **R2** complete graph idempotency：
  - `test_r2_artifact_artifact_id_change_rejects`
  - `test_r2_artifact_relative_path_change_rejects`
  - `test_r2_artifact_kind_change_rejects`
  - `test_r2_artifact_provider_metadata_change_rejects`
  - `test_r2_provider_call_request_metadata_change_rejects`
  - `test_r2_video_should_summarize_change_rejects`
  - `test_r2_job_binding_change_rejects`
- **R3** registration capability authority：
  - `test_r3_import_mint_function_fails`
  - `test_r3_direct_sentinel_construction_with_wrong_token_rejects`
  - `test_r3_copy_capability_rejects`
  - `test_r3_pickle_capability_rejects`
  - `test_r3_modify_capability_field_rejects`
  - `test_r3_legal_committer_path_succeeds`
- **M15** filesystem-before-SQLite ordering：`test_m15_registration_before_final_verify_rejected`
- **R5** filesystem fault injection（补充）：
  - `test_r5_fsync_failure_no_sqlite_registration`
  - `test_r5_promote_failure_no_sqlite_registration`
  - `test_r5_dir_fsync_failure_no_sqlite_registration`
  - `test_r5_final_reopen_verify_failure_no_sqlite_registration`

### Mutation Matrix（M1–M15）

使用 `run_mutation_matrix.py` 临时修改并恢复，每项至少导致一个测试失败：

| Mutation | 目标 | 结果 |
|---|---|---|
| M1 | `prewrite_validate` exact success guard → `if False` | KILLED |
| M2 | raw hash check → `if False` | KILLED |
| M3 | raw reparse check → `if False` | KILLED |
| M4 | candidate/result binding → `if False` | KILLED |
| M5 | runtime authority/context check → `if False` | KILLED |
| M6 | ProviderCall request binding → `if False` | KILLED |
| M7 | runtime artifact content/hash binding → `if False` | KILLED |
| M8 | stale-tmp O_EXCL guard 移除 | KILLED |
| M9 | `run_primary_trusted_scoring` PrimaryScoringAttempt exact-type guard → `if False` | KILLED |
| M10 | `_atomic_register_scoring_success` 跳过 job finish | KILLED |
| M11 | `_write_atomic_file` 将 `os.link` 改回 `os.rename` | KILLED |
| M12 | `commit()` 删除 complete-graph idempotency verification | KILLED |
| M13 | `_atomic_register_scoring_success` 删除 capability + provenance token guard | KILLED |
| M14 | `_atomic_register_scoring_success` 删除 final-file hash verification | KILLED |
| M15 | `commit()` 将 DB registration 提前到 promoted finals 之前 | KILLED |

Mutation 脚本本身未提交；生产代码在所有 mutation 恢复后 GREEN。

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline --dry-run` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `51 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E trust + TASK-016B regression | `417 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1266 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit `ef89b1e` 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud/credential 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 2 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN/mutation 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 3

- Status: `READY FOR PHASE G CORRECTION ROUND 3 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a` (HEAD)
- Role: Implementer (continuation/recovery)

### Correction Scope

本次 correction 关闭 Round 2 Independent Review 的 REQUEST CHANGES，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1-1 Registration Capability Authority | `src/youtube_intel/scoring.py` `_RegistrationAuthority` / `TrustedScoringPersistenceCommitter`；`src/youtube_intel/state.py` `ScoringRegistrationCapability` / `_atomic_register_scoring_success()`；`src/youtube_intel/runtime.py` `RuntimeOperations` | 引入 runtime-scoped 的 `_RegistrationAuthority` 对象作为不可推导的 authority proof；Runtime 创建唯一实例并同时注入 repository 与 committer；capability 必须携带该实例；registrar 通过对象 identity 验证来源。移除 deterministic SHA256 provenance token，避免被重新计算伪造。state.py 不再暴露任何 mint seam |
| P1-2 Exact relative_path Verification | `src/youtube_intel/scoring.py` `TrustedScoringPersistenceCommitter._verify_artifact_record()` | 先比较 `record.relative_path == expected.relative_path` 字符串，再比较 resolved absolute path；禁止仅依赖 `Path.resolve()`；路径归一化后相同但字符串不同会被拒绝 |
| P2 Failure Injection Completeness | `tests/unit/test_task016c_phase_g.py` `_assert_no_scoring_success()` | 每次 filesystem fault 后统一断言：raw/structured Artifact 不存在、scoring/judge ProviderCall 未 SUCCEEDED、video 未 SCORED、job 未 SUCCEEDED |
| P2 Mutation-as-Tests | `tests/unit/test_task016c_phase_g.py` | 关键 mutation 保护已转为 committed pytest tests：`test_r1_promote_does_not_overwrite_existing_final`（no-replace overwrite）、`test_r2_same_plan_after_commit_is_idempotent`（complete graph idempotency）、`test_direct_forged_capability_with_correct_fields_is_rejected` + `test_r3_ordinary_capability_substitute_rejects`（capability bypass）、`test_m14_registration_rejects_missing_final_files`（final file verification）、`test_m15_registration_before_final_verify_rejected`（DB registration ordering） |
| Worktree | `.gitignore` / `run_mutation_matrix.py` | 删除未跟踪的 `run_mutation_matrix.py`；将 `.workbuddy/` 加入 `.gitignore`（按策略不删除该目录） |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正以下 RED→GREEN 测试：

- **P1-1 authority forge：** `test_direct_forged_capability_with_correct_fields_is_rejected`
- **P1-2 exact relative_path：** `test_idempotency_rejects_relative_path_normalization_difference`
- **P2 failure injection：** 通过 `_assert_no_scoring_success()` 统一增强 `test_r5_temp_write_failure_no_sqlite_registration`、`test_r5_fsync_failure_no_sqlite_registration`、`test_r5_promote_failure_no_sqlite_registration`、`test_r5_dir_fsync_failure_no_sqlite_registration`、`test_r5_final_reopen_verify_failure_no_sqlite_registration`、`test_r5_sqlite_transaction_rollback_no_partial_graph`

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline --dry-run` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `52 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E trust + TASK-016B regression | `417 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1267 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`.gitignore`、`src/youtube_intel/scoring.py`、`src/youtube_intel/state.py`、`src/youtube_intel/runtime.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 3 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 4

- Status: `READY FOR PHASE G CORRECTION ROUND 4 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 3 Independent Review 的唯一 P1「Registration authority remains caller-configurable」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Authority Injection Trust Boundary | `src/youtube_intel/runtime.py` `bootstrap_runtime()` / `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `SQLiteStateRepository.__init__` / `ScoringRegistrationCapability` | 从 `bootstrap_runtime()` 与 `SQLiteStateRepository.__init__` 移除 `registration_authority` 参数；authority 改由 `SQLiteStateRepository` 在构造时内部创建。`RuntimeOperations` 只能从已组合的 repository 读取该实例并注入 committer。authority 不可外部传入、不可替换、不可复制、不可序列化。registrar 仍通过对象 identity 验证 capability 来源 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增 RED→GREEN 测试：

- **P1 external repository authority bypass：** `test_external_repository_authority_cannot_create_registration_success`
  - caller 直接创建 `SQLiteStateRepository`
  - caller 创建 forged `_RegistrationAuthority`
  - caller 构造 self-consistent `ScoringRegistrationCapability`（含正确 DTO、文件、hash）
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("registration authority proof mismatch")`，FAIL CLOSED

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `53 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1268 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `src/youtube_intel/scoring.py`（authority 验证逻辑不变，仅 authority 来源从 caller-configurable 改为 repository 内部创建）、`providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 4 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 5

- Status: `READY FOR PHASE G CORRECTION ROUND 5 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 4 Independent Review 的唯一 P1「SQLiteStateRepository remains authority-minting root」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Authority Minting Root | `src/youtube_intel/scoring.py` `_RegistrationAuthority`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `SQLiteStateRepository.__init__` / `_bind_registration_authority()` / `_atomic_register_scoring_success()` | 从 `SQLiteStateRepository.__init__` 移除 authority 创建逻辑；`_RegistrationAuthority` 增加 runtime-issued 标记；`RuntimeOperations` 是唯一创建并标记 authority 的主体，然后通过私有 `_bind_registration_authority()` 绑定到 repository，同时注入 committer。直接构造的 `SQLiteStateRepository` 没有 authority，无法产生 accepted registrar capability |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试：

- **P1 external repository has no authority：** `test_external_repository_authority_cannot_create_registration_success`（Round 4 测试断言更新）
  - caller 直接创建 `SQLiteStateRepository`
  - caller 创建 forged `_RegistrationAuthority`
  - caller 构造 self-consistent `ScoringRegistrationCapability`
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("repository has no runtime-bound registration authority")`，FAIL CLOSED
- **P1 external repository cannot authorize with its own authority：** `test_external_repository_cannot_authorize_with_own_authority`
  - caller 直接创建 `SQLiteStateRepository`
  - caller 创建自己的 `_RegistrationAuthority` 并尝试通过 `_bind_registration_authority()` 绑定 → 失败（非 runtime-issued）
  - caller 绕过 bind 检查直接将自己的 authority 附加到 repository，构造 self-consistent capability（正确 DTO、文件、hash）
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("registration authority was not issued by the runtime")`，FAIL CLOSED

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `54 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1269 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 5 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 6

- Status: `READY FOR PHASE G CORRECTION ROUND 6 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Round 5 correction commit: `0649447`
- Round 5 handoff commit: `b425dd4`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 5 Independent Review 的唯一 P1「Registration authority issuance boundary is still forgeable」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Authority Issuance Boundary | `src/youtube_intel/_phase_g_trust.py`（新建）；`src/youtube_intel/scoring.py` `_RegistrationAuthority`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `_bind_registration_authority()` / `_atomic_register_scoring_success()` | 移除 `_mark_runtime_issued()` 与 `_runtime_issued` boolean 等 mutable escalation API；引入 `_RuntimeIssuanceCapability` 作为只有 `RuntimeOperations` composition 能 mint 的 runtime-only capability；`_RegistrationAuthority` 构造函数必须接收该 capability，否则 raise TypeError；`RuntimeOperations` 在 `__init__` 内通过 `object.__new__` 创建 capability 与 authority 并绑定 repository；registrar 通过 capability 的 exact-type 与对象身份双重校验拒绝任何 caller-forged authority |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试：

- **P1 direct forged capability：** `test_direct_forged_capability_with_correct_fields_is_rejected`（Round 3 测试更新）
  - caller 使用任意 object 作为 `authority_proof`
  - 调用 `_atomic_register_scoring_success()`
  - 结果：`IntegrityConflict("registration authority proof is not a _RegistrationAuthority")`，FAIL CLOSED
- **P1 external repository has no authority：** `test_external_repository_authority_cannot_create_registration_success`（Round 4 测试更新）
  - caller 直接创建 `SQLiteStateRepository`
  - caller 使用任意 object 作为 `authority_proof`
  - 结果：`IntegrityConflict("repository has no runtime-bound registration authority")`，FAIL CLOSED
- **P1 external authority cannot be issued：** `test_external_authority_cannot_be_issued`
  - `_RegistrationAuthority()` → `TypeError`
  - `_RegistrationAuthority(object())` → `TypeError`
  - `object.__new__(_RegistrationAuthority)` 无 valid issuance capability
- **P1 external repository cannot become trusted root：** `test_external_repository_cannot_become_trusted_root`
  - 直接构造的 repository `_registration_authority is None`
  - caller 绕过 `__init__` 得到的 authority 无法通过 `_bind_registration_authority()`
- **P1 full attack chain：** `test_external_mark_bind_capability_register_attack_fails`
  - external repo = `SQLiteStateRepository(db)`
  - 无 `_mark_runtime_issued` API 可供调用
  - `_RegistrationAuthority()` 构造失败
  - `object.__new__(_RegistrationAuthority)` 得到的 authority 绑定失败
  - 构造 self-consistent capability（正确 DTO、文件、hash）调用 register → FAIL CLOSED
  - 即使强行把 forged authority 附加到 repository，register 仍因缺少 runtime issuance capability 而 FAIL CLOSED
- **P1 positive control：** `test_runtime_owned_registration_still_succeeds`
  - 正常 `RuntimeOperations` 路径完成 commit
  - 结果：`StageCompletionResult`，job `SUCCEEDED`，video `SCORED`

### Mutation Evidence

新增 regression tests 同时充当 mutation kill proof：

| 删除的保护 | 会失败的测试 |
|---|---|
| 删除 runtime issuance capability 类型校验（`_RegistrationAuthority.__init__` 或 registrar 中） | `test_external_authority_cannot_be_issued`、`test_external_mark_bind_capability_register_attack_fails` |
| 删除 repository binding authority 校验（`_bind_registration_authority` 中） | `test_external_repository_cannot_become_trusted_root`、`test_external_mark_bind_capability_register_attack_fails` |
| 恢复 caller-controlled authority injection | `test_external_repository_authority_cannot_create_registration_success`、`test_external_mark_bind_capability_register_attack_fails` |

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `58 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1273 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean` |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/_phase_g_trust.py`（新建）、`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 6 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、mutation evidence、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 7

- Status: `READY FOR PHASE G CORRECTION ROUND 7 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-PHASE-G-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Round 5 correction commit: `0649447`
- Round 5 handoff commit: `b425dd4`
- Round 6 correction commit: `dc3bad8`
- Round 6 handoff commit: `d2b82ec`
- Round 7 correction commit: `2f658b0`
- Round 7 handoff commit: `<TBD>`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 6 Independent Review 的唯一 P1「Runtime issuance capability is forgeable through object.__new__ attack」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Capability Provenance Boundary | `src/youtube_intel/_phase_g_trust.py`（删除，超出范围）；`src/youtube_intel/scoring.py` `_RuntimeIssuanceCapability` / `_RegistrationAuthority`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `_bind_registration_authority()` / `_atomic_register_scoring_success()` | 删除 Round 6 新增的 `_phase_g_trust.py`，将 capability 移回允许范围 `scoring.py`；`_RuntimeIssuanceCapability` 不再依赖 type-only validation，改为由 `RuntimeOperations` 在 composition 内维护唯一的 runtime-local `WeakSet` 实例注册表；repository binding 与 registrar 均通过 runtime 注入的 verifier closure 校验 authority 的 issuance capability 是否在该注册表中，从而拒绝 `object.__new__(_RuntimeIssuanceCapability)` 伪造的 capability 实例 |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试：

- **P1 object.__new__ capability forgery：** `test_object_new_runtime_capability_forgery_fails`
  - 使用 `object.__new__(_RuntimeIssuanceCapability)` 伪造 capability 实例
  - 用该实例构造类型正确的 `_RegistrationAuthority`
  - 尝试绑定 external `SQLiteStateRepository` → `IntegrityConflict("registration authority was not issued by the runtime")`，FAIL CLOSED
  - 构造 self-consistent capability（正确 Artifact DTO、ProviderCall DTO、文件、hash）调用 register → FAIL CLOSED
  - 即使强行把 forged authority 附加到 external repository，registrar 仍因不在 runtime issuance registry 而 FAIL CLOSED
  - 断言无 Artifact success / ProviderCall success / Video SCORED / Job SUCCEEDED
- **P1 external capability instance cannot authorize：** `test_external_capability_instance_cannot_become_runtime_authority`
  - `object.__new__(_RuntimeIssuanceCapability)` 得到的实例不是 runtime-issued
  - 构造的 authority 无法通过 external repository 的 `_bind_registration_authority()`
- **P1 positive control：** `test_runtime_owned_registration_still_succeeds`（Round 6 正控保留）
  - 正常 `RuntimeOperations` composition 路径完成 commit
  - 结果：`StageCompletionResult`，job `SUCCEEDED`，video `SCORED`

### Mutation Evidence

本次新增 regression tests 在以下临时 mutation 下失败，恢复后重新 GREEN：

| 删除/替换的保护 | Mutation 操作 | 观察结果 |
|---|---|---|
| 删除 runtime-owned capability provenance validation | 临时将 `state.py` 的 verifier 默认改为 `lambda _auth: True`，并把 registrar 的 provenance 校验改为恒真 | `test_object_new_runtime_capability_forgery_fails` 失败：攻击成功，未抛出 `IntegrityConflict` |
| 替换 instance provenance validation 为 `isinstance()` | 临时将 `state.py` `_bind_registration_authority()` 与 `_atomic_register_scoring_success()` 的 provenance 校验替换为 `isinstance(authority, _RegistrationAuthority)` | `test_object_new_runtime_capability_forgery_fails` 失败：`object.__new__(_RegistrationAuthority)` 通过 isinstance 检查， forged authority 被接受 |
| 恢复 external capability construction path | （隐含）若同时允许外部构造 capability 并移除 registry 校验，则 object.__new__ 攻击链可完整走通；已由前两项 mutation 覆盖 | — |

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `60 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1275 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean`（warnings only） |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 删除文件：`src/youtube_intel/_phase_g_trust.py`（超出允许范围）
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 7 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、object.__new__ attack regression evidence、mutation evidence、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 8

- Status: `READY FOR PHASE G CORRECTION ROUND 8 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`、
  `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`、
  `docs/TASK-016C-HANDOFF-CHECKLIST.md`
- Correction baseline: `ef89b1e` (Phase G implementation commit)
- Round 1 correction commit: `b4497cf`
- Round 1 handoff commit: `6900b76`
- Round 2 correction commit: `b8005d1`
- Round 2 handoff commit: `52c0bcf`
- Round 3 correction commit: `1780d9a`
- Round 3 handoff commit: `c1971da`
- Round 4 correction commit: `980497d`
- Round 4 handoff commit: `dda8040`
- Round 5 correction commit: `0649447`
- Round 5 handoff commit: `b425dd4`
- Round 6 correction commit: `dc3bad8`
- Round 6 handoff commit: `d2b82ec`
- Round 7 correction commit: `2f658b0`
- Round 7 handoff commit: `e5f20b6`
- Round 8 correction commit: `105457f`
- Round 8 handoff commit: `<TBD>`
- Role: Implementer

### Correction Scope

本次 correction 关闭 Round 7 Independent Review 的唯一 P1「Repository binding accepts caller-supplied provenance verifier」，不进入 Phase H/I，不重新设计/回滚/扩大范围，不修改 Phase F/D/E：

| P1/P2 | 位置 | 修复内容 |
|---|---|---|
| P1 Caller-Supplied Verifier Boundary | `src/youtube_intel/scoring.py` `_RegistrationBindingCapability` / `_mint_registration_binding`；`src/youtube_intel/runtime.py` `RuntimeOperations.__init__`；`src/youtube_intel/state.py` `_bind_registration_authority()` | 移除 `_bind_registration_authority(authority, verifier)` 的 verifier 参数；新增 `_RegistrationBindingCapability` 作为 runtime-only binding token，内部封装 runtime-created `_RegistrationAuthority` 与 runtime-owned verifier closure；repository 只接受该 binding capability，并校验其 verifier closure 必须捕获 runtime-local `WeakSet` 注册表，从而拒绝 `lambda _auth: True` 等 caller-supplied verifier |

### RED-first 补充测试

在 `tests/unit/test_task016c_phase_g.py` 新增/修正 RED→GREEN 测试，并同步修正 Round 5/6/7 中直接调用 `_bind_registration_authority(authority)` 的测试以适配新 API：

- **P1 external supplied verifier rejection：** `test_external_supplied_verifier_cannot_authorize_registration`
  - 旧 API `_bind_registration_authority(forged_authority, lambda _auth: True)` 直接因参数不匹配/类型错误被拒绝
  - 伪造 `_RegistrationBindingCapability` 并设置 `lambda _auth: True` verifier → `IntegrityConflict("registration verifier is not runtime-issued")`，FAIL CLOSED
  - 构造 self-consistent capability（正确 Artifact DTO、ProviderCall DTO、文件、hash）调用 register → FAIL CLOSED
  - 断言无 Artifact success / ProviderCall success / Video SCORED / Job SUCCEEDED
- **P1 runtime binding capability required：** `test_repository_requires_runtime_binding_capability`
  - external `SQLiteStateRepository` 直接传入 authority 被拒绝
  - 伪造 binding capability 因 verifier 无 runtime registry 被拒绝
  - 绑定后 repository 仍无 trusted authority
- **P1 positive control：** `test_runtime_owned_binding_still_succeeds`
  - 正常 `RuntimeOperations` composition 通过 `_RegistrationBindingCapability` 完成绑定与 commit
  - 结果：`StageCompletionResult`，job `SUCCEEDED`，video `SCORED`

### Mutation Evidence

本次 regression tests 在以下临时 mutation 下失败，恢复后重新 GREEN：

| 删除/替换的保护 | Mutation 操作 | 观察结果 |
|---|---|---|
| 删除 runtime-owned verifier registry 校验 | 临时移除 `state.py` `_bind_registration_authority()` 中的 `_verifier_carries_runtime_registry(binding)` 检查 | `test_external_supplied_verifier_cannot_authorize_registration` 与 `test_repository_requires_runtime_binding_capability` 失败：伪造 binding 的 `lambda _auth: True` verifier 被接受 |
| 恢复 caller-supplied verifier callback API | 临时让 `_bind_registration_authority()` 重新接受 `is_runtime_issued_authority` 参数并在提供时绕过 binding capability 校验 | `test_external_supplied_verifier_cannot_authorize_registration` 失败：旧 API 调用不再抛出 TypeError，攻击者可通过 `lambda _auth: True` 绑定 forged authority |
| 恢复 external capability construction path | 临时注释掉 `scoring.py` `_RegistrationAuthority.__init__()` 中对 `_RuntimeIssuanceCapability` 的类型检查 | `test_external_authority_cannot_be_issued` 失败：外部可通过 `_RegistrationAuthority()` 创建 authority |

### Mandatory Gates

| # | Gate | 结果 |
|---|---|---|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `63 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | Phase A–E regression | `316 passed, 1 warning` |
| 6 | `uv run --offline pytest -x -q` | `1278 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean`（warnings only） |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未新增/保留 `src/youtube_intel/_phase_g_trust.py` 等超出允许范围的文件
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend（基线 commit 之外的新 correction commit）/ merge / push / tag
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 8 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、caller-supplied verifier attack regression evidence、mutation evidence、gates 与 handoff 后决定是否验收；不进入 Phase H。

## Phase G Correction Round 9

- Status: `READY FOR PHASE G CORRECTION ROUND 9 INDEPENDENT REVIEW`
- Authority: `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`
- Baseline: Round 8 handoff commit（当前 HEAD ancestor）
- Round 9 correction commit: `8ffd78c`
- Round 9 handoff commit: `<TBD>`
- Role: Implementer

### Correction Scope

- 修复 Round 8 Independent Review 唯一阻塞 finding：`RegistrationBindingCapability provenance remains forgeable`。
- 彻底移除 closure/WeakSet/predicate 形式的 provenance；改为由 `RuntimeOperations` 独占创建并持有的 runtime-owned binding registry。
- 修改文件：
  - `src/youtube_intel/scoring.py`
  - `src/youtube_intel/runtime.py`
  - `src/youtube_intel/state.py`
  - `tests/unit/test_task016c_phase_g.py`
  - `handoffs/TASK-016C.md`
- 未进入 Phase H；未修改 provider、domain、DB migration、依赖、uv.lock。

### Finding

Round 8 通过 closure（`_verify`）把 runtime-owned WeakSet 隐藏进 `_RegistrationBindingCapability`，但 repository 仍把 closure 当作 caller-supplied verifier 来执行；攻击者可构造自己的 closure 或捕获/重放 verifier，导致 provenance 可伪造（forgeable）。

### Attack Reproduction（Round 8 shape）

1. 攻击者通过 `object.__new__(_RuntimeIssuanceCapability)` 伪造 issuance capability。
2. 构造 `_RegistrationAuthority(forged_issuance)`，得到类型正确的 authority。
3. 通过 `object.__new__(_RegistrationBindingCapability)` 伪造 binding，并附带上自己的 `_verify` closure。
4. 若 repository 接受 caller-supplied verifier，则该伪造 binding 可通过验证并授权后续 `_atomic_register_scoring_success`。

### Redesign

- 新增 `_RegistrationBindingRegistry`：仅由 `RuntimeOperations` 通过 `_create_binding_registry()` 创建，内部使用 `weakref.WeakSet` 按对象身份记录合法的 binding。
- 重定义 `_RegistrationBindingCapability`：只携带 `_authority` 与 `_binding_registry` 引用；`__new__`、copy、pickle 全部禁用。
- 新增 `_mint_registration_binding(authority, registry)`：在创建 binding 的同时将其身份注册到 runtime-owned registry。
- `RuntimeOperations.__init__` 调用 factory 创建 registry、mint binding、再调用 `repository._bind_registration_authority(binding)`；不暴露任何 verifier/closure/WeakSet/predicate。
- `SQLiteStateRepository._bind_registration_authority(binding)`：
  - 仅接受单一 `binding` 参数；拒绝 caller-supplied verifier、callback、closure、WeakSet 或 predicate。
  - 校验 binding 的 exact type、authority 的 exact type、registry 的 exact type。
  - 最终校验 `binding in registry`（对象身份是否在 runtime-owned registry 中）。
- `SQLiteStateRepository._atomic_register_scoring_success`：
  - 校验 `_registration_binding` 与 `_binding_registry` 已绑定。
  - 再次校验 `self._registration_binding in binding_registry`。
  - 再校验 `registration.authority_proof is self._registration_authority`。

### Implementation

- `src/youtube_intel/scoring.py`
  - 新增 `_RegistrationBindingRegistry` 与 `_create_binding_registry()`。
  - 重定义 `_RegistrationBindingCapability`（`__slots__` 含 `__weakref__`；property `authority` / `_registry`）。
  - 新增 `_mint_registration_binding()`。
  - 删除 closure verifier 相关逻辑与 `inspect`/`weakref` 在 provenance 中的使用。
- `src/youtube_intel/runtime.py`
  - 使用 `_create_binding_registry()` 与 `_mint_registration_binding()` 替代 closure verifier。
- `src/youtube_intel/state.py`
  - 删除 `_verifier_carries_runtime_registry()` 与 `inspect` import。
  - `__init__` 增加 `_registration_binding = None`、`_binding_registry = None`。
  - `_bind_registration_authority(binding)` 改为仅接受 binding，新增 registry membership 校验。
  - `_atomic_register_scoring_success` 新增 binding registry membership 校验。
- `tests/unit/test_task016c_phase_g.py`
  - 更新 Round 5–8 测试，移除对 `_verify` closure 的断言，改为断言伪造 binding 不在 runtime-owned registry 中。
  - 新增 4 个 Round 9 committed tests：
    - `test_external_fake_binding_object_new_fails`
    - `test_attacker_closure_registry_cannot_authorize_binding`
    - `test_external_repository_has_no_binding_registry`
    - `test_runtime_owned_binding_registry_succeeds`

### RED / GREEN Evidence

- RED：在实现 registry membership 检查前，上述 4 个新测试与 `test_repository_requires_runtime_binding_capability`、`test_external_repository_cannot_become_trusted_root` 因伪造 binding 被接受而失败（`DID NOT RAISE IntegrityConflict`）。
- GREEN：
  - `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` → `66 passed`
  - `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` → `41 passed`
  - `uv run --offline pytest -q` → `1281 passed, 1 warning`

### Mutation Evidence

- Mutation 1 — 移除 registry membership 检查：临时注释掉 `_bind_registration_authority` 与 `_atomic_register_scoring_success` 中的 `binding not in registry` 检查；5 个攻击测试全部失败（`DID NOT RAISE IntegrityConflict`）。恢复检查后通过。
- Mutation 2 — 恢复 closure verifier API：临时给 `_bind_registration_authority` 增加可选 `verifier` 参数，若 caller-supplied verifier 返回 `True` 则绕过 registry 检查；`test_attacker_closure_registry_cannot_authorize_binding` 在传入 `lambda _binding: True` 后失败（伪造 binding 被接受）。恢复后通过。
- Mutation 3 — 用 type-only 检查替换 registry membership 检查：临时把 `_bind_registration_authority` 中的 registry 成员校验改为仅检查 `type(binding) is _RegistrationBindingCapability`；`test_external_fake_binding_object_new_fails` 失败（`object.__new__` 伪造的 exact-type binding 被接受）。恢复 registry 检查后通过。

### Validation Gates

| # | Gate | Result |
|---|------|--------|
| 1 | `uv lock --check --offline` | PASS |
| 2 | `uv sync --locked --offline` | PASS |
| 3 | `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q` | `66 passed` |
| 4 | `uv run --offline pytest tests/unit/test_task016c_phase_f.py -q` | `41 passed` |
| 5 | TASK-016B regression | 未找到独立文件；由 full pytest 覆盖 |
| 6 | `uv run --offline pytest -q` | `1281 passed, 1 warning` |
| 7 | `uv run --offline mypy src` | PASS |
| 8 | `uv run --offline ruff check .` | PASS |
| 9 | `uv build --offline` | PASS |
| 10 | `bash scripts/security_scan.sh` | `status=clean`（warnings only） |
| 11 | `git diff --check` | PASS |

### Scope Verification

- 修改文件：`src/youtube_intel/scoring.py`、`src/youtube_intel/runtime.py`、`src/youtube_intel/state.py`、`tests/unit/test_task016c_phase_g.py`、`handoffs/TASK-016C.md`
- 未新增超出允许范围的文件
- 未修改 `providers/ollama.py`、`domain.py`、TASK-016B Language Validator、Cloud、Router、Weekly production、DB migration、依赖、`uv.lock`
- 未 rebase / squash / amend 基线 commit 之外的历史
- 无真实 Ollama/network/cloud 调用

### 实现者结论

- 建议状态：`READY FOR PHASE G CORRECTION ROUND 9 INDEPENDENT REVIEW`
- 下一步：由独立 reviewer 复核本 correction commit、RED/GREEN 证据、object.__new__ / closure-registry attack regression evidence、mutation evidence、gates 与 handoff 后决定是否验收；**不进入 Phase H**。

## Phase G Correction Round 10

- Status: `READY FOR PHASE G CORRECTION ROUND 10 INDEPENDENT REVIEW`
- Baseline: Round 9 implementation commit `8ffd78c`
- Role: Implementer

### Round 9 finding and architecture correction

Round 9 made `_RegistrationBindingRegistry`, `_create_binding_registry()` and
`_register()` the effective trust root.  That root was forgeable: a caller
could private-import the types, use `object.__new__`, create a fresh registry,
register a forged binding in that same registry, and then present the
self-consistent objects to the repository.

Round 10 removes the complete authority/binding/registry chain.  Runtime
composition now captures the trusted repository's bound low-level transaction
method in a local closure while creating a local committer subclass.  The
subclass is the only production caller of that captured method.  The entry is
not a `RuntimeOperations` field, is never stored in a repository, cannot be
passed by a caller, and has no module-level getter or factory.

`SQLiteStateRepository._persist_scoring_registration()` remains a mechanical
SQLite primitive only: it retains final-file verification, graph writes,
transaction ordering, idempotency and rollback semantics, but holds no
authority, binding, registry, token, verifier, entry or trusted registration
API.  The former `_atomic_register_scoring_success()` and
`_bind_registration_authority()` ingress points no longer exist.

### Scope

- Changed only:
  - `src/youtube_intel/scoring.py`
  - `src/youtube_intel/runtime.py`
  - `src/youtube_intel/state.py`
  - `tests/unit/test_task016c_phase_g.py`
  - `handoffs/TASK-016C.md`
- Did not modify providers, `domain.py`, `quality.py`, schema/migrations,
  TASK-016B implementation, dependencies or `uv.lock`.
- Did not enter Phase H/I.

### RED / GREEN evidence

Round 10 tests cover an externally constructed repository, fake subclass,
private-import plus `object.__new__`, repository attribute injection, and the
normal runtime success path.

- Initial RED (before migration): `4 failed` for the retained Round 9 trusted
  ingress, inherited API and registry exposure.
- GREEN: `uv run --offline pytest tests/unit/test_task016c_phase_g.py -q -k round10`
  → `5 passed, 65 deselected`.
- Full Phase G: `70 passed`.

### Mutation evidence

1. Replaced the closure-captured bound transaction call with a dynamic lookup
   through `self._repository`.  The fake-subclass/attribute-injection attack
   regression failed with `ScoringPersistenceError` caused by
   `runtime entry must retain its composed transaction`.  Restored the capture;
   the test returned GREEN.
2. Temporarily restored an external repository alias
   `_atomic_register_scoring_success = _persist_scoring_registration`.  Four
   Round 10 attacks failed because the old trusted ingress reappeared.  Removed
   the alias and restored GREEN.

### Validation gates

| Gate | Result |
|---|---|
| Round 10 focused | `5 passed, 65 deselected` |
| Phase G focused | `70 passed` |
| Phase F focused | `41 passed` |
| TASK-016B (`test_scoring_language.py`) | `101 passed` |
| Full `pytest -q` | completed successfully |
| `uv run --offline mypy src` | PASS |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (existing warnings only) |
| `git diff --check` | PASS |

### Implementer conclusion

`READY FOR PHASE G CORRECTION ROUND 10 INDEPENDENT REVIEW`

Stop here.  Do not begin Phase H before Independent Review.

## Phase G Correction Round 11

- Status: `READY FOR PHASE G CORRECTION ROUND 11 INDEPENDENT REVIEW`
- Implementation baseline: Round 10 implementation `1d52271`
- Implementation commit: `b4402ce`
- Role: Implementer

### Round 10 finding and correction

Round 10 left `SQLiteStateRepository._persist_scoring_registration()` as a
repository-owned capability admission point.  A caller that could construct a
valid-looking `ScoringRegistrationCapability` could invoke that method with
otherwise valid DTOs and final files, producing Artifact rows, successful
ProviderCalls, a `SCORED` video and a successful job without the Phase F
aggregate or `PREWRITE_VALIDATE`.

Round 11 removes both that method and `ScoringRegistrationCapability`.
`SQLiteStateRepository` no longer has a Phase-G scoring-registration entry or
stores any registration authority, binding, registry, verifier, token or
issued marker.  The base `TrustedScoringPersistenceCommitter` remains unable
to register; `RuntimeOperations._trusted_scoring_committer()` creates the
only execution entry.  Its local subclass captures the runtime-owned
repository and contains the SQLite transaction closure.  That closure accepts
only the already prevalidated `ValidatedScoringWritePlan` and promoted final
paths supplied by the committer's ordered commit flow.

The resulting success path is:

`PhaseFTrustedScoringSuccess -> PREWRITE_VALIDATE -> runtime-local persistence
entry -> SQLite transaction`.

No authority object or caller-provided registration graph is admitted by the
repository.  The runtime-local transaction closure preserves final-file
existence/hash checks, the immediate SQLite transaction, two Artifact rows,
two ProviderCall completions, stage/job completion, and rollback behavior.

### RED / GREEN evidence

- RED: before removal, the new external-repository regression failed at
  `assert not hasattr(state_module, "ScoringRegistrationCapability")`; the
  capability still existed and was accepted by the repository entry.
- GREEN: after removal and runtime-local entry composition:
  `uv run --offline pytest -x -q tests/unit/test_task016c_phase_g.py` ->
  `68 passed`.
- Cross-boundary regression:
  `uv run --offline pytest -x -q tests/unit/test_task016c_phase_f.py
  tests/unit/test_scoring_language.py` -> `142 passed`.
- Full suite: `uv run --offline pytest -x -q` ->
  `1283 passed, 1 existing Pydantic serializer warning`.

### Attack and mutation evidence

- External repository: a freshly constructed `SQLiteStateRepository` has no
  `ScoringRegistrationCapability`, `_persist_scoring_registration`,
  `_atomic_register_scoring_success`, `_bind_registration_authority` or
  `_write_scoring_transaction` trusted ingress.  The test also verifies no
  Artifact, successful ProviderCall, `SCORED` video or successful job exists.
- Fake subclass: an external `SQLiteStateRepository` subclass cannot provide
  a transaction hook to the already composed runtime path; normal runtime
  commit remains successful.
- Object construction and attribute injection: private-import/object-new
  attempts cannot recreate the removed authority classes, and injected
  repository attributes do not add a class-level trusted entry.
- Mutation: restoring either `ScoringRegistrationCapability` or a repository
  `_persist_scoring_registration` admission method makes the committed
  external-ingress tests fail because they assert both symbols are absent.
  All mutations were reverted before commit.

### Validation gates

| Gate | Result |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS |
| Phase G focused | `68 passed` |
| Phase F + TASK-016B focused | `142 passed` |
| Full pytest | `1283 passed, 1 existing warning` |
| `uv run --offline mypy src` | PASS |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (warnings only) |
| `git diff --check` | PASS |

### Scope

- Implementation changed only `src/youtube_intel/scoring.py`,
  `src/youtube_intel/runtime.py`, `src/youtube_intel/state.py`, and
  `tests/unit/test_task016c_phase_g.py`.
- This handoff is the separate evidence commit.
- No changes to providers, domain/quality contracts, TASK-016B, migrations,
  dependencies, `uv.lock`, Phase H/I, or external network behavior.

### Implementer conclusion

`READY FOR PHASE G CORRECTION ROUND 11 INDEPENDENT REVIEW`

Stop here. Do not begin Phase H before Independent Review.

---

## TASK-016C Phase G Correction Round 12

### Scope and implementation

- Base: `7f7eb15`; implementation parent: `b4402ce`.
- Changed only `src/youtube_intel/scoring.py`, `src/youtube_intel/runtime.py`,
  `src/youtube_intel/state.py`, and `tests/unit/test_task016c_phase_g.py`.
- `complete_stage()` rejects `TRANSCRIPT_READY -> SCORED` before opening a
  SQLite transaction.  Runtime's normal scoring route now creates a local
  `TrustedPersistenceEntry` and calls `persist_success(exact_success)`.
- Removed exported `ValidatedScoringWritePlan` and public `commit(plan)`.
  The write plan is private implementation state; no repository method is a
  plan consumer.
- Reuse decision: `DIRECT` — existing SQLite transaction primitives,
  filesystem protocol, Phase F success aggregate and standard library only;
  no dependency changes.

### RED / GREEN and attack evidence

- RED mutation A: removing the `complete_stage` scoring guard made
  `external_repository_complete_stage_scoring_fails_closed` fail (the call
  reached legacy provider-call completion instead of rejecting pre-transaction).
- RED mutation B: restoring `TrustedPersistenceEntry.commit(plan)` made
  `forged_plan_has_no_consumer` fail.
- Both mutations were restored; Phase G focused suite: `73 passed`.
- New regressions cover external DTO `complete_stage` ingress, forged and
  copied plans, malformed success before any write, and a successful entry
  path while `complete_stage` is poisoned to fail.

### Validation and known blocker

| Gate | Result |
|---|---|
| `uv lock --check --offline` | PASS |
| `uv sync --locked --offline` | PASS (84 packages) |
| Phase G focused | PASS (`73 passed`) |
| Phase F focused | PASS (`41 passed`) |
| TASK-016B regression | PASS (`101 passed`) |
| `uv run --offline mypy src` | PASS (28 files) |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS |
| `bash scripts/security_scan.sh` | `status=clean` (pre-existing warnings) |
| `git diff --check` | PASS |
| Full pytest | BLOCKED: `tests/e2e/test_failure_recovery.py::test_service_boundary_failures_recover_without_duplicate_outputs[subtitle]` expects the legacy repository-backed scoring service to complete `TRANSCRIPT_READY -> SCORED` via forbidden `complete_stage()`. |

The full-suite failure is a direct conflict between this Round 12 requirement
and an out-of-scope legacy E2E flow.  No Phase H work, migration, dependency,
provider, domain/quality, TASK-016B, or external/network behavior was changed.

### Implementer conclusion

`IN_REVIEW / DECISION NEEDED`: authorize an update to the out-of-scope legacy
E2E flow, or explicitly accept its expected failure while Phase G closes the
generic scoring ingress.  Do not begin Phase H.
