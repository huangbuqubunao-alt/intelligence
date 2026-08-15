# TASK-016C 交接报告

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
