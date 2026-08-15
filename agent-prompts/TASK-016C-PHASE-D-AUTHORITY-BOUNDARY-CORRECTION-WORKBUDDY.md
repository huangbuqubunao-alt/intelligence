# TASK-016C Phase D：当前配置 Provenance Authority Boundary 修正实施包

## 角色与停止条件

你是 WorkBuddy Implementer。只实施 ADR-026 所定义的狭义 Phase D authority bridge。
完成一个 correction commit 后立即停止，等待独立审查。

禁止 merge、push、tag、rebase、squash、reset、改写历史、启动 Phase E 或执行真实模型/网络调用。

## 固定前置

实现必须以审查中的 Phase D HEAD `39a1e864238388abe651c466c0a41a023934c872` 为祖先，并先
同步本控制面提交。开始前完整阅读 ADR-025、ADR-026、TASK-016C Interface、Test Plan、Master
Plan、TASK-016C handoff 及本提示词。如发现这些权威文件冲突，停止并报告。

## 唯一目标

消除 hard-coded model/digest，不允许调用方以 `LocalScoringSettings`、`AppConfig`、
`TrustedQualityProvenance`、Mapping、JSON、provider response、cache/artifact 或 fixture 常量充当
attestation authority。

在 `runtime.py` 的已有已加载配置组合点，从当前 runtime 自己持有的 `AppConfig` 铸造私有、
不可序列化的 `QualityProvenanceAuthority`；`quality.py` 的 build/verify 只接收该 opaque capability。
此能力必须携带当前 Judge provider、`local_scoring.model`、`expected_model_digest`、scoring
schema/prompt 与 quality policy/schema/prompt 的冻结身份。

## 允许修改的文件

- `src/youtube_intel/runtime.py`
- `src/youtube_intel/quality.py`
- `src/youtube_intel/domain.py`（仅移除或封闭旧 caller-constructible provenance DTO 的最小变更）
- `tests/unit/test_task016c_quality_attestation.py`
- `tests/unit/test_task016c_domain_contracts.py`（仅必要的最小回归）
- `tests/integration/test_runtime_composition.py`
- `handoffs/TASK-016C.md`

任何其他文件都不在授权范围内。

## 冻结实现规则

1. runtime composition 是唯一 capability 铸造点；不得公开 `settings/config -> authority` 工厂；
2. capability 不得是 Pydantic DTO，不能由 Mapping/JSON 反序列化，不能用 public constructor 创建；
3. `quality.py` 不得读取配置、环境变量或文件，也不得接收 raw settings/config/provenance 参数；
4. capability 仅用于 attestation build/verify 的当前配置 binding；保留完整 quality-result canonical
   hashing、Evidence/confidence binding、H1/H2 验证和 fail-closed 行为；
5. H1/H2 与 `build_provider_request_hash` 不得修改；
6. 该实施仍须纯内存：不得构造 ScoreResult、Artifact、cache、ProviderCall、response artifact ID，
   不得写文件/数据库。

不要声称该 Python 私有 capability 能抵抗拥有同一进程任意执行权的攻击者；它只实现 ADR-026 的
应用边界，拒绝普通调用方和所有不可信数据对象。

## 必须 TDD 的对抗场景

先写 RED，再最小 GREEN。至少证明：

- 经真实测试配置加载和 runtime composition 得到的当前 model/digest 能 build + verify PASS；
- caller-created `LocalScoringSettings`、`AppConfig`、旧 provenance DTO、Mapping/JSON 均不能授权；
- 完全自洽但 provider/model/digest/版本不同的伪造 attestation 仍被当前 authority 拒绝；
- 配置 A 的 attestation 在配置 B（任一受绑定 identity 改变）下失败；
- H1/H2 完全不变且不可互换；
- Pydantic `model_copy`、`model_construct`、subclass/property/model_dump spoof 与 fake trusted flag
  不能越过 authority；
- 无 ScoreResult、Artifact、cache、ProviderCall、response ID、文件或数据库副作用。

## 禁止范围

不得修改 `config.py`、`cli.py`、`scoring.py`、`providers/ollama.py`、`state.py`、数据库、migration、
Artifact、cache、ProviderCall、filesystem protocol、TrustedScoringFinalizer、primary/repair、Judge budget、
TASK-016B Language Validator、依赖或 `uv.lock`。

不得使用真实 Ollama、网络、云端、模型下载或任何 Phase E–K 行为。

## 必须门禁

```text
uv lock --check
uv sync --locked --offline
uv run pytest -x -q tests/unit/test_task016c_quality_attestation.py
uv run pytest -x -q tests/unit/test_task016c_domain_contracts.py
uv run pytest -x -q tests/integration/test_runtime_composition.py
uv run pytest -x -q
uv run mypy src
uv run ruff check .
git diff --check
```

## 提交与交接

仅创建一个 correction commit，建议信息：

```text
TASK-016C Phase D bind attestation provenance to runtime authority
```

在 `handoffs/TASK-016C.md` 记录 RED/GREEN、所有门禁、完整对抗矩阵、无副作用证据、commit 与唯一
父提交、精确路径、复用决定和剩余风险。随后停止；不得自行启动审查或合并。
