# TASK-016A 交接报告

## 元数据

- Task: `TASK-016A`
- Role: `Implementer`
- Agent/session: `Codex primary`
- Base branch/commit: `codex/task-016a-intelligence-contract-foundation@36969c5c5f7af75a2cf2255b63f742c12cf4fb0c`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016a-intelligence-contract-foundation`
- Branch: `codex/task-016a-intelligence-contract-foundation`
- Head commit: recorded by the single implementation commit containing this report
- Started: `2026-08-12`
- Reported: `2026-08-12`

## 目标与范围

- 任务目标：建立 Local-only 第一里程碑所需的 Intelligence Mode、可独立配置的 Local
  Analysis，以及 Local/Cloud 共用的 Knowledge V2 和 Weekly Knowledge V2 契约。
- 允许修改：example settings、Config/Domain 契约、契约单测和本 handoff。
- 实际修改：严格限于上述五条路径。
- 明确未做：Provider、Router、Prompt、Artifact/SQLite、Renderer、Runtime wiring、
  TASK-016B–H、网络、模型、Key、真实 Vault。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 严格三模式与安全默认 | PASS | `local-only / hybrid / cloud`；新配置和旧 Cloud OFF 均解析为 Local-only，旧 Cloud ON 明确兼容映射为 Hybrid，冲突组合 fail-closed |
| Local Analysis 可信身份 | PASS | 独立 model/base URL/digest；未设置时从 Local Scoring 解析为具体值，可形成后续 cache identity |
| Provider-neutral Knowledge V2 | PASS | summary、why-it-matters、core points、可空机会字段、Evidence Registry、可信 timestamp basis、Knowledge Graph、完整 provenance |
| Weekly Knowledge V2 | PASS | 独立 Provider-neutral synthesis schema，所有结论携带 video/evidence source references |
| 校验边界 | PASS | Config 与 Knowledge V2 禁止 unchecked `model_copy(update=...)`；mode/provider/digest/fallback/evidence 交叉验证 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 84 packages resolved，锁文件未变 |
| `uv sync --locked --offline` | PASS | 61 packages checked，无网络 |
| `uv run pytest tests/unit/test_contracts.py -q` | PASS | 86 passed；TDD 初始 RED 为缺少 `IntelligenceMode` |
| `uv run mypy src/youtube_intel/config.py src/youtube_intel/domain.py` | PASS | 2 source files，无问题 |
| `uv run ruff check .` | PASS | 全仓 Python lint 通过 |
| `uv run pytest -x -q` | PASS | 686 passed |
| `uv build --offline` | PASS | sdist 与 wheel 构建成功 |
| `uv run ruff check config/settings.example.yaml ...` | FAIL（任务包命令缺陷） | Ruff 将 YAML 当 Python 解析并产生 syntax errors；已用 `yaml.safe_load`/契约测试覆盖 example 配置，并另跑 `ruff check .` 通过 |
| `git diff --check` | PASS | 实现范围无空白错误 |

## Diff 复核

- 修改文件：`config/settings.example.yaml`、`src/youtube_intel/config.py`、
  `src/youtube_intel/domain.py`、`tests/unit/test_contracts.py`、`handoffs/TASK-016A.md`。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：否；`dist/` 为既有 ignore 范围，不纳入提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：契约测试先 RED 后 GREEN；实现中补充了 timed-subtitle timestamp basis、
  Hybrid fallback reason、配置重验证和 Local/Cloud model digest 交叉约束。
- 跳过检查及原因：未运行真实 Provider/网络/模型/Key/Vault，均不在 TASK-016A 权限内。
- 剩余风险：本任务只冻结契约，不提供用户可见知识输出；Local Provider、持久化与
  Renderer 必须由后续独立任务实现。旧 `cloud.enabled=true` 映射到 Hybrid 仅是兼容
  配置语义，不会在本任务触发任何外发。
- `DECISION NEEDED`：None。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：the single implementation commit containing this report
- 复现/验证说明：在固定 worktree 离线执行上述命令；Reviewer 应独立复核安全迁移、
  provider-neutrality、Evidence 引用、timestamp basis、provenance 和 update-bypass。

## Reviewer 结论

- Reviewer agent/session：pending
- 审查 commit：pending
- 重新运行的检查：pending
- Findings：pending
- Verdict：pending
- 未解决 P0/P1：pending

## Independent Reviewer 1 evidence（2026-08-12）

### 固定对象与范围

- Reviewer：全新独立 Codex Reviewer。
- 固定实现提交：`210dd203e722eabf3453808f490f4afe52139183`。
- 唯一父提交：`36969c5c5f7af75a2cf2255b63f742c12cf4fb0c`。
- Source 分支/worktree 与固定授权一致，审查开始时工作树干净。
- 完整产品 Diff 精确为任务允许的五条路径；`pyproject.toml`、`uv.lock`、migration、
  State、Runtime、Provider 和模板均未变化。

### Findings

- `P0`：0。
- `P1`：1。
- `P2`：0（P1 后依任务包停止继续穷尽审查）。
- `P3`：0（P1 后依任务包停止继续穷尽审查）。

#### P1-1：可信 Evidence 时间戳接受非有限值，序列化后破坏契约

`src/youtube_intel/domain.py` 的 `KnowledgeEvidence.start_seconds` 与
`end_seconds` 仅使用 `ge=0`。独立 JSON 边界探针证明：

- 输入 `end_seconds: 1e999` 会被 Pydantic 解析并接受为正无穷 `inf`；
- 该对象同时被接受为 `source=transcript_sample`、
  `timestamp_basis=timed-subtitle` 的可信 Evidence；
- 随后 `model_dump_json()` 将 `inf` 序列化为 `null`，而 `start_seconds` 保持
  `0.0`，产生无法通过同一契约恢复的半时间戳 payload。

这违反 ADR-023 “只有可验证的字幕时间映射才展示 timestamp”以及 TASK-016A
Evidence Registry fail-closed 边界。它会让已经验证的对象在 Artifact/JSON
持久化边界变成自相矛盾的数据，因此定为 P1。修复需对两个时间字段明确要求有限值，
并新增 JSON 输入、对象构造、JSON round-trip 对 `NaN/+Inf/-Inf/overflow` 的回归。

### 独立检查证据

- `uv lock --check`：PASS。
- `uv sync --locked --offline`：PASS；无网络。
- `uv run pytest tests/unit/test_contracts.py -q`：PASS，`86 passed`。
- `uv run mypy src/youtube_intel/config.py src/youtube_intel/domain.py`：PASS。
- `uv run ruff check .`：PASS。
- example settings `yaml.safe_load` 与关键值断言：PASS。
- mode/execution/fallback/digest 对抗矩阵：仅接受预期四种组合。
- Local Analysis 继承值重新校验探针：PASS。
- `uv run pytest -x -q`：PASS，`686 passed`。
- `uv build --offline`：PASS，sdist/wheel 均成功。
- 固定实现范围 `git diff --check`：PASS。
- 非有限时间戳 JSON 对抗探针：FAIL，复现上述 P1。
- 发现 P1 后未继续运行额外产品命令或扩大探针。

### Reviewer verdict

- Verdict：`REJECT`。
- 未解决 P0/P1：`P1-1`。
- 未运行真实 Provider、Ollama、OpenAI、Key、网络、真实 Vault 或用户数据路径。
- 本次只追加本 handoff；未修改业务代码、任务状态或其他任务资料，未 merge/push。

## Correction 1 Implementer evidence（2026-08-12）

- 固定起点：Review 1 evidence `6a564b18a3c91e4366c1b744733910dc5584854b`。
- 修复范围：仅 `KnowledgeEvidence.start_seconds/end_seconds` 增加有限数值约束，
  并新增对象构造、JSON overflow 和合法 JSON round-trip 回归。
- TDD RED：非有限对象值未抛出 `ValidationError`，目标测试 `1 failed`。
- GREEN：契约测试 `87 passed`、全量 `687 passed`、mypy、Ruff、offline build、
  Correction/完整范围 diff check 均通过。
- 未改变 mode、fallback、Evidence ID、Weekly、Config 或其他产品语义；未触及依赖、
  Schema、Runtime、Provider、模板或真实资源。

## Independent Reviewer 2 evidence（2026-08-13）

### 固定对象与范围

- Reviewer：全新独立 Codex Reviewer 2。
- 固定 Correction 提交：`26a74cd508b28c9fd89e86af741414c8653f2721`；唯一父提交为
  Review 1 evidence `6a564b18a3c91e4366c1b744733910dc5584854b`。
- 原实现提交 `210dd203e722eabf3453808f490f4afe52139183` 的唯一父提交为固定
  base `36969c5c5f7af75a2cf2255b63f742c12cf4fb0c`。
- Review 1 evidence 仅追加本 handoff；Correction Diff 精确为 domain、契约测试与本
  handoff 三条路径；完整 TASK-016A Diff 精确为任务允许的五条路径。
- Source 分支、HEAD、授权链与 worktree 洁净度均符合 Reviewer 2 任务包。

### Findings

- `P0`：0。
- `P1`：1。
- `P2`：0（发现 P1 后停止继续穷尽审查）。
- `P3`：0（发现 P1 后停止继续穷尽审查）。

#### P1-1：模型侧 KnowledgeContent 可自建 Evidence Registry，违反可信 Evidence 边界

ADR-023 和 System Design 明确要求：Evidence Registry 由应用从 canonical Transcript
建立，模型只能返回其中的 ID；excerpt 与可信 timestamp 由应用补全。现有契约却将
`evidence_registry` 定义在 `KnowledgeContent`，并由同一个模型内容对象使用该 Registry
校验其 `summary_evidence_ids` 与各 `AnalysisPoint.evidence_ids`。因此一个模型 payload
可以同时提供任意 `excerpt`、`source_content_hash`、时间戳和匹配的自引用 ID，并通过
`KnowledgeContent` 校验。`KnowledgeResult` 只在其上增加 provenance，未建立应用拥有的
Registry 与模型只读引用之间的信任边界。

这不是未来 Provider 的可选实现细节：TASK-016A 的目标正是冻结 Provider-neutral V2
内容/结果契约；现有 V1 及 Weekly V2 也采用 `*Content` 作为模型内容、`*Result` 增加可信
应用字段的分层。按当前 V2 契约继续 TASK-016C/E，要么允许模型伪造 Evidence，要么再次
破坏并重做已经冻结的公共契约，故定为 P1。

最小修复方向：模型侧 `KnowledgeContent` 只承载 Evidence ID 引用；应用建立的
`EvidenceRegistry` 放在可信结果边界（例如 `KnowledgeResult`）并在应用封装结果时统一
执行引用交叉验证。回归必须证明模型内容不能提交 Registry/excerpt/hash/timestamp，且
应用注入 Registry 后未知 ID 仍 fail-closed。

### Correction 1 与独立门禁证据

- 原 P1 非有限时间戳修复：PASS。对象与 JSON 输入的 `NaN`、`+Inf`、`-Inf`、
  `1e999/-1e999` 以及字符串/Decimal 非有限变体均被拒绝；合法 timed-subtitle 时间戳
  JSON round-trip 保持一致。
- mode/execution/fallback/digest 对抗矩阵：PASS。
- Evidence ID 引用、update-bypass、example settings YAML 与 Local-only 默认/Cloud OFF：
  PASS。
- `uv lock --check`：PASS，84 packages。
- `uv sync --locked --offline`：PASS，84 resolved / 61 checked，无网络。
- `uv run pytest tests/unit/test_contracts.py -q`：PASS，`87 passed`。
- `uv run mypy src/youtube_intel/config.py src/youtube_intel/domain.py`：PASS。
- `uv run ruff check .`：PASS。
- `uv run pytest -x -q`：PASS，`687 passed`。
- `uv build --offline`：PASS，sdist/wheel 均成功。
- Correction/完整 TASK Diff 与 `git diff --check`：PASS。
- P1 在完成上述门禁后的最终五轴静态复核中确认；确认后未继续运行其他产品命令。

### Reviewer 2 verdict

- Verdict：`REJECT`。
- 未解决 P0/P1：`P1-1`。
- 未运行真实 Provider、Ollama、OpenAI、Key、网络、真实 Vault 或用户数据路径。
- 本次只追加本 handoff；未修改业务代码、任务状态或其他任务资料，未 merge/push。

## Correction 2 Implementer evidence（2026-08-13）

- 固定起点：Review 2 evidence `2ea00258ec2b1843e268d4ed1ffef03bd6b0347d`。
- TDD RED：`KnowledgeContent.model_fields` 仍含 `evidence_registry`，目标测试 `1 failed`。
- 最小修复：模型侧 `KnowledgeContent` 只保留 Evidence ID；可信应用侧
  `KnowledgeResult` 注入 `EvidenceRegistry` 并统一验证所有引用。
- 明确边界：Content 额外提交 Registry/excerpt/hash/timestamp 会因 `extra=forbid`
  拒绝；Result 缺 Registry 或引用未知 ID 均 fail-closed。
- 最终门禁：contracts `87 passed`、full `687 passed`、mypy、Ruff、locked offline
  sync、offline build、Correction/完整范围 diff check 均通过。

## Independent Reviewer 3 evidence（2026-08-13）

### 固定对象与范围

- Reviewer：全新独立 Codex Reviewer 3。
- 固定 Correction 2 提交：`dfe087924d1c99695b2608afbfea96e46e93175f`；唯一父提交为
  Review 2 evidence `2ea00258ec2b1843e268d4ed1ffef03bd6b0347d`。
- Review 2 evidence 仅追加本 handoff；Correction 2 Diff 精确为 domain、契约测试与
  本 handoff 三条路径；完整 TASK-016A Diff 精确为任务允许的五条路径。
- Source 分支、授权控制面、父链、固定范围、`git diff --check` 与 worktree 洁净度
  均通过前置核验。

### Findings

- `P0`：0。
- `P1`：1。
- `P2`：0（发现 P1 后按 Reviewer 包立即停止，未继续穷尽审查）。
- `P3`：0（发现 P1 后按 Reviewer 包立即停止，未继续穷尽审查）。

#### P1-1：KnowledgeResult 子类实例可穿透模型侧 KnowledgeContent 边界

Correction 2 已使 JSON/mapping 形式的模型 payload 不能向 `KnowledgeContent` 注入
`evidence_registry`。但 `KnowledgeResult` 仍继承 `KnowledgeContent`，而 Pydantic 默认
不会重新验证已是目标类型子类的实例。独立对象边界探针证明：

- `KnowledgeContent.model_validate(result)` 接受一个带可信 Registry 的
  `KnowledgeResult`；
- 返回值与传入 `result` 是同一实例，运行时类型仍是 `KnowledgeResult`；
- 返回对象仍可访问 `evidence_registry`，其 `model_dump()` 仍包含 Registry、excerpt、
  source hash、可选 timestamp、provenance 与结果 schema 字段；
- 相同内容转成 mapping 后会被 `extra=forbid` 正确拒绝，说明缺口专属于 Python 对象/
  子类边界，而不是映射校验。

这违反 Correction 2 Reviewer 包的绝对要求：模型侧 `KnowledgeContent` 不能接受 Registry、
excerpt、hash 或 timestamp。类型契约允许任何接受 `KnowledgeContent` 的 Provider/解析边界
直接接收 `KnowledgeResult`，使应用拥有的可信 Registry 再次进入模型侧对象；后续 Provider
只要传递领域对象而不是原始 mapping，就会绕过这次修复。因此该公共契约仍未真正分离信任
边界，定为 P1。

最小修复方向：不要让可信 `KnowledgeResult` 成为 `KnowledgeContent` 的子类；改用组合或
其他能在对象边界保持类型隔离的结构，并继续由应用侧 Result 对 Content 的全部 Evidence ID
引用与 Registry 做统一交叉验证。回归必须覆盖 mapping 注入和已构造 Result/子类实例注入。

### 独立检查证据

- Git 身份、固定 branch/HEAD/唯一父、动态 main 授权、Review 2 handoff-only、Correction
  三路径、完整五路径、禁止范围、两组 `git diff --check`：PASS。
- 模型侧 mapping Registry 注入：按现有测试与独立探针为拒绝。
- 模型侧 `KnowledgeResult` 实例注入：FAIL；`same_instance=True`、运行时类型保持
  `KnowledgeResult`、Registry 仍存在。
- 按“发现 P0/P1 立即停止”规则，未运行 lock、offline sync、contracts、mypy、Ruff、
  full pytest、offline build 或 YAML safe-load；Implementer 自报门禁不计为本轮独立证据。
- 未运行网络、Provider、Ollama、OpenAI、Key、真实 Vault、用户数据或 TASK-016B–H。

### Reviewer 3 verdict

- Verdict：`REJECT`。
- 未解决 P0/P1：`P1-1`。
- 本次只追加本 handoff；未修改业务代码、任务状态或其他文件，未 merge/push。
