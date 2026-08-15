# ADR-026：TASK-016C Phase D 当前配置溯源授权边界

## 状态

Accepted；2026-08-15。此 ADR 是对 ADR-025 已冻结 Phase D 证明来源的狭义修订，不开放
Phase E、Finalizer、持久化、缓存恢复或运行时评分编排。

## 背景

Phase D Correction Round 3 移除了调用方可传入的 `TrustedQualityProvenance` 和
`LocalScoringSettings`，但以硬编码模型与 digest 替代它们。独立审查正确指出：硬编码值不等于
运行中应用已经解析的当前配置，不能证明 attestation 的 provider/model/digest 是当前有效配置。

当前实际配置所有权链为：`config.load_app_config/load_settings` 解析配置，`cli._load_config`
将已解析的 `AppConfig` 交给 `runtime.create_runtime_operations`。`quality.py` 刻意无运行时状态，
因此它不能自行取得当前配置。原 Phase D 禁止访问组合层，和“attestation 必须绑定当前配置”
同时存在，构成授权冲突而非实现错误。

## 决定：采用 Option A，新增狭义 Authority Boundary Amendment

Phase D 仅扩展到已加载配置后的运行时组合边界。`runtime.py` 在创建运行时组合时，从该运行实例
持有的已解析 `AppConfig` 铸造一个内存、不可序列化、非 Pydantic DTO 的
`QualityProvenanceAuthority`。该能力对象仅作为 `quality.py` build/verify 的输入；它不是配置、
不是 Artifact、不是 cache、不是 ProviderCall，也不会产生 I/O。

`QualityProvenanceAuthority` 至少封装并绑定：

- 当前 Judge provider（本版本为受限本地 `ollama`）；
- `AppConfig.settings.local_scoring.model`；
- `AppConfig.settings.local_scoring.expected_model_digest`；
- 当前 scoring schema version 与 scoring prompt version；
- ADR-025 已冻结的 quality policy/schema/prompt version；
- 既有 H1/H2 所需 operation/request identity 约束。

模型和 digest 必须来自已解析的当前 `AppConfig`，不得使用硬编码生产常量、`settings.example.yaml`、
未跟踪的本地 `settings.yaml`、测试 fixture 或调用方 DTO 作为信任来源。固定协议版本可以来自
应用内已冻结常量，但不得由调用方覆盖。

## 精确职责划分

### runtime/composition 拥有

- 在 `create_runtime_operations` 的现有组合边界、已有 `AppConfig` 已被加载后铸造 capability；
- 仅保存 capability 供未来受控运行时路径内部使用；
- 不提供公开的“传入任意 settings/AppConfig 即返回 authority”工厂；
- 不发起 Judge、Ollama、网络、持久化、ProviderCall 或缓存操作。

### quality 层继续拥有

- 完整 `ContentQualityResult` 的不可信重建、矩阵校验、排序去重与 canonical hash；
- `QualityPassAttestation` 构造、`attestation_hash`、Evidence/confidence binding；
- H1/H2 identity 的重算与验证；
- 接收 opaque authority 后的当前配置一致性校验与所有不一致 fail-closed。

`quality.py` 不读取 `AppConfig`、`LocalScoringSettings`、Mapping/JSON 配置或环境变量；它只接受
opaque authority。build/verify 不得接受 `settings=`、`config=`、`trusted_provenance=` 或等价
调用方可构造的参数。

## 信任假设

这是应用架构中的 authority boundary，不是针对同一 Python 进程内任意恶意代码的密码学隔离。
项目威胁模型要求拒绝模型、provider、cache、Artifact、Mapping/JSON、测试 fixture 和普通调用方
对象伪造的 provenance；它不声称阻止能够导入私有模块、反射或篡改进程内存的任意 Python 代码。

因此 capability 必须没有公开 Pydantic/JSON/Mapping 构造路径，构造受 runtime 私有工厂和私有
sentinel 约束；测试可通过受控 composition seam 验证，但该 seam 不得成为产品公开 API。

## 允许的下一轮生产文件

- `src/youtube_intel/runtime.py`：仅在已解析配置后的组合点铸造并私有保存 authority；
- `src/youtube_intel/quality.py`：opaque authority 类型、构造/验证入口以及 fail-closed binding；
- `src/youtube_intel/domain.py`：仅为移除或封闭旧 caller-constructible provenance DTO 所必需的
  最小契约改动。

允许的测试文件：

- `tests/unit/test_task016c_quality_attestation.py`；
- `tests/unit/test_task016c_domain_contracts.py`（仅最小契约回归）；
- `tests/integration/test_runtime_composition.py`（证明已加载配置经真实组合路径铸造 authority）。

任何其他生产或测试路径先停下并请求新授权。

## 明确禁止

禁止修改 `config.py`、`cli.py`、`scoring.py`、`providers/ollama.py`、`state.py`、Artifact、cache、
数据库、migration、ProviderCall、文件提交协议、`TrustedScoringFinalizer`、ScoreResult 构造、
primary/repair 编排、Judge budget、H1/H2 算法、TASK-016B Language Validator、依赖或锁文件。

禁止真实 Ollama、网络、云端、模型下载、配置写入、数据库写入、文件写入、cache hit 或任何
Phase E–K 行为。

## 验收场景

1. 由测试配置加载并经 runtime composition 铸造的 authority，能以其真实 model/digest 构造并验证
   合法 PASS attestation；
2. 调用方新建的 `LocalScoringSettings`、`AppConfig`、旧 provenance DTO、Mapping/JSON、provider
   response 或 cache/artifact 对象都不能作为 build/verify authority；
3. 即使 attestation 所有内部 hash 自洽，只要其 provider/model/digest/version 与当前 authority
   不同，验证必须失败；
4. 配置 A 创建的 attestation 在配置 B（任一受绑定 identity 改变）下必须失败；
5. H1/H2 算法及既有 request-hash builder 不变，且 H1/H2 不可互换；
6. 该 correction 全程无 ScoreResult、Artifact、cache、ProviderCall、response ID、文件或数据库
   副作用。

## 后果

Phase D 继续只交付纯内存 attestation primitive，但它现在可以表达真实的当前应用 provenance。
最终 Runtime scoring、Finalizer、持久化和恢复仍分别属于后续已冻结 Phase E–K，不能由本修订
提前实现或声明完成。

## 与 Phase E 的冻结衔接

Phase D 已通过独立审查；其 `QualityProvenanceAuthority` 和
`QualityPassAttestation` 的字段、铸造者与验证语义保持不变。Phase E 不能把 scoring context
塞入本 authority，也不能以 attestation 替代 scoring request identity。后续仅在获得明确授权后，
才可按 `TASK-016C-PHASE-E-AUTHORITY-AMENDMENT-ROUND-3.md` 新增独立、runtime-owned 的
`TrustedScoringContext`，并由 Finalizer 同时消费两个不同职责的 opaque capability。
