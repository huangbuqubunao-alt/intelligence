# ADR-025：Content Quality Layer 职责与信任边界

## Status

Accepted

## Date

2026-08-13

## Context

TASK-016B 已按 ADR-024 验收并冻结。Language Validator 只判断 Unicode script 是否
明显不匹配、是否存在保守的自然语言结构证据，以及无法证明时是否应 fail-closed。它
不能在无品牌词库、实体数据库、外部知识或语义模型的条件下可靠区分：

- 有价值的自然语言评分理由；
- 品牌、产品、框架或 identifier 的堆叠；
- 语法成立但没有评分价值的低信息文本；
- 看似有主谓宾但无法由当前评分输入支持的陈述。

继续把这些问题塞入 Language Validator 会违反 ADR-024，并重新引入品牌词表、token
位置、大小写、词尾或 dependency 例外等不可穷举的启发式。TASK-016C 因此建立独立
Content Quality Layer，使“语言形式合规”与“内容具有可信评分价值”成为两个串行门禁。

ADR-023 原先把 `TASK-016C` 分配给 Local Deep Analysis Provider。本 ADR 仅替代
ADR-023“Local-only 第一里程碑”清单中的该任务编号分配：`TASK-016C` 现用于 Content
Quality Layer。Local Deep Analysis 的产品目标和其他 ADR-023 决策保持有效，但必须由
主控在未来重新编号并重新分配，不能从本 ADR 推断其已获实现授权。

## Decision

### 1. 职责边界

TASK-016C v1 负责：

- identifier-only response detection；
- entity-only / entity-stuffing 的内容质量识别，但不判断实体真实身份；
- low-information scoring reason detection；
- minimal claim validation；
- 相对于当前 `ScoringInput` 的 grounding confidence；
- 在无法可靠确认时返回 `UNCERTAIN` 并 fail-closed。

TASK-016C 不负责：

- language、script 或 grammar validation；
- 品牌、公司、产品或技术实体的事实识别；
- 事实真伪核验；
- Web、Wikipedia、外部 API、远程知识库或用户知识库查询；
- TASK-016B Language Validator 的修改、替换或重新解释。

### 2. 双层判定

Content Quality Validator 固定为两层：

```text
schema-valid scoring candidate
        |
        v
Deterministic Safety Gate
        |
        v
Fixed Local Content Quality Judge
        |
        v
ContentQualityResult: PASS | REJECT | UNCERTAIN
```

Deterministic Safety Gate 只拒绝无需语义判断即可证明的垃圾，例如空白/控制字符材料、
越界结构、重复退化输出和明显的 acronym/code identifier 列表。它不能以品牌词表、公司
名单或开放式技术词表判断复杂样例，也不能单独产生 `PASS`。

所有未被确定性门禁拒绝的候选都必须进入固定本地 Judge。复杂的 entity-only、低信息、
最小 claim 和 grounding 判断由 Judge 完成；Judge 缺失、加载失败、超时、输出无效或
证据不足统一产生 `UNCERTAIN`，不得宽松放行。

### 3. Judge 运行边界

v1 Judge：

- 复用当前 `local_scoring` 的固定 Ollama model 与 expected model digest；
- 只允许现有受限 loopback HTTP Adapter，不允许远程 base URL；
- 固定 `content-quality-prompt-v1`、`content-quality-result-v1` 与
  `content-quality-policy-v1`；
- 使用结构化输出、`temperature=0`、`stream=false`、`think=false`，不使用 tools；
- 不启动 Ollama、不拉取模型、不下载资源、不执行网络 fallback；
- 不接受用户提供的远程模型地址、动态 prompt 或外部知识源；
- 每个 scoring request 最多调用两次：主评分候选一次、唯一 repair 候选一次；
- 只返回有限枚举、布尔判定和由应用预先建立的 evidence ID，不能自报 provider、model、
  digest、版本、request hash 或 excerpt。

Judge 的 `PASS` 不是事实真实性证明，只表示候选包含最小可用 claim，且该 claim 在当前
评分输入的有限 evidence 中有足够支持。

### 4. Fail-closed 与 repair

处理顺序冻结为：

```text
untrusted Ollama response
  -> structural candidate validation
  -> frozen TASK-016B Language Validator
  -> TASK-016C Content Quality Validator
  -> trusted ScoreResult
  -> Artifact / cache
```

schema、language 或 content-quality 任一门禁返回失败时，共享同一个“最多一次 repair”
预算。repair 后重新执行全部门禁。第二次仍为 `REJECT` / `UNCERTAIN`，或 Judge 自身不可用，
必须返回 `INVALID_RESPONSE`。

未获 `PASS` 的候选不得生成可信 `ScoreResult`，不得写正式 `SCORING_RAW`、
`SCORING_STRUCTURED`、成功 Provider-call provenance 或当前 cache。安全日志只记录有限
错误码和版本，不记录模型原文、Transcript、路径或用户数据。

### 5. ContentQualityResult

`ContentQualityResult.status` 只允许 `PASS | REJECT | UNCERTAIN`。其他字段也使用有限
枚举或受限 ID：confidence、signals、rejection reason、grounding evidence IDs、candidate
hash，以及由应用补充的 policy/prompt/schema/provider/model/digest provenance。

模型输出只是未可信 Judge response；只有应用验证 evidence 引用、组合规则和可信
provenance 后，才能构造 `ContentQualityResult`。`ScoreResult` 的现有字段、语言契约与
Pydantic 不变量保持不变。

### 6. Artifact 与 cache

TASK-016C 不新增 SQLite migration。现有 `artifacts.kind` 有固定 CHECK，v1 不新增
Artifact kind 或数据库字段。

只有 quality `PASS` 的结果才能写现有 `SCORING_STRUCTURED`。v1 用以下已有能力表达
质量决策：

- `SCORING_RAW` 与 `SCORING_STRUCTURED` 分别使用新的、固定的 quality-qualified
  producer version，表示它们只可能来自已通过 `content-quality-policy-v1` 的同一
  最终候选；
- normalized scoring identity 纳入 quality policy version、Judge prompt/schema
  version、provider、model 与 expected model digest；
- Artifact key/content hash 与 Provider-call request hash 继续绑定该 identity；
- `SCORING_STRUCTURED` 的 JSON 内容继续保持现有 `ScoreResult` 形状，避免破坏当前
  Runtime、Report 与 Weekly consumer。

因此，成功 Artifact 的存在与固定 producer metadata 表示 `PASS`；v1 不把 REJECT /
UNCERTAIN 结果持久化为正式 scoring Artifact。若以后必须长期保存完整 quality signals，
必须另开 ADR 评估新的 Artifact kind 或 Schema，而不能复用错误 kind。

cache recovery 必须同时验证：既有评分 provenance，以及 quality policy version、Judge
prompt version、Judge schema version、Judge provider/model/digest 和 qualified producer
version。任一缺失或不匹配都视为 cache miss，保留旧 Artifact 供审计并重新计算，不得
返回 persisted cache hit。

### 7. Reuse decision

- `DIRECT`：现有 Pydantic 领域校验、标准库 hashing/JSON、受限 Ollama loopback Adapter、
  `local_scoring` 固定 model/digest、ProviderCall、Artifact 和 cache identity。
- `DIRECT`：已锁定 spaCy 只继续服务 TASK-016B；TASK-016C 不扩展或修改其语言职责。
- `REJECT`：品牌/公司/产品词典、网络查询、Wikipedia、外部 API、远程知识库、动态模型
  下载和新增 NLP 依赖。

## Alternatives Considered

### 把 entity-only 规则继续加入 Language Validator

拒绝。ADR-024 已证明语法同构结构不可可靠区分，继续添加规则会重新打开 TASK-016B。

### 只使用确定性规则

拒绝。复杂 entity-only、低信息和 grounding 需要有限语义判断；纯规则要么漏检，要么
误杀正常技术内容。

### 只使用 Local Judge

拒绝。明显垃圾无需消耗模型调用；输入边界、资源上限和退化模式应由确定性门禁先处理。

### 引入品牌/实体知识库或网络检索

拒绝。超出 Local-only、隐私和离线边界，也不能穷举实体。

### 新增数据库字段或 Artifact kind

拒绝 v1。现有 Schema 对 kind 有 CHECK，新 kind 必须 migration；成功结果的 PASS 标记与
完整 provenance 可由既有 producer metadata 和 request identity 承载。

## Consequences

- 评分路径增加最多两次固定本地 Judge 调用，延迟与本机资源占用上升。
- 保守策略允许部分正常候选进入 `UNCERTAIN` 并触发一次 repair；安全性优先于召回率。
- 通过 quality gate 不等于外部事实核验，只证明当前评分理由具有最小内容价值和输入内
  grounding。
- 旧 scoring Artifact 因缺少 quality provenance 不再是当前 cache hit，但继续保留审计。
- TASK-016C 实现必须先通过独立 Review；本 ADR 不授权 TASK-016C 之外的 Local Deep
  Analysis、Cloud、Router、Weekly V2、数据库 migration、真实模型或网络操作。
