# TASK-016C 交接报告

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
