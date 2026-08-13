# ADR-024：评分语言校验器的可判定职责边界

## Status

Accepted

## Date

2026-08-13

## Context

TASK-016B 使用固定本地 `spacy==3.8.15` 与 `en_core_web_sm==3.8.0`，对单一
`casefold()` 文本执行离线英文依存分析。该校验器只能使用 Unicode script、POS、
dependency 与模型给出的 NER；不得调用网络、外部知识或语义模型，也不得维护品牌、
公司、产品或实体词典。

Round 15 后的对抗审查证明，以下两个 object span 在上述允许信息内同构：

```text
General Dynamics Corporation
corporation NOUN/dobj
├─ general ADJ/amod
└─ dynamics NOUN/compound

useful AI models
models NOUN/dobj
├─ useful ADJ/amod
└─ ai NOUN/compound
```

两者在单次 `casefold()` parse 中也都没有可依赖的 NER 标记。只使用现有结构信息时，
无法可靠地同时保证前者为 entity-only、后者为自然语言；继续增加 dependency 例外、
token 启发式或隐藏词表只会把不可判定问题伪装成确定判断，并不断产生新绕过或正常文本
回归。

## Decision

1. TASK-016B Language Validator 的职责冻结为：
   - 检测明显的 Unicode script mismatch；
   - 验证保守的自然语言结构证据；
   - parser 缺失、失败或证据不足时 fail-closed 为 `UNCERTAIN`；
   - `INVALID` 与 `UNCERTAIN` 均不得进入可信 `ScoreResult`、正式 scoring Artifact
     或当前 cache。
2. Language Validator 不负责：
   - 品牌或 entity-only phrase 检测；
   - 公司、产品或技术实体识别；
   - 实体真实性判断；
   - entity stuffing 或内容质量判断。
3. 保持 `OpenAI develops useful AI models`、`Docker containers help developers
   deploy applications` 与 `Redis stores data and improves application
   performance` 为合法自然语言结构。
4. 不再为 entity-only 对抗样例增加品牌词典、实体规则、dependency 例外、token
   数量/长度/位置/词尾启发式、大小写投票、外部知识或语义模型。
5. `Amazon Connect General Dynamics Corporation` 暴露的 entity-only 风险移交给
   后续独立 Content Quality 边界；该后续任务必须另行设计、授权和验收，不得从本 ADR
   推断已获实施许可。
6. 当前实现基线保持
   `08fbae17086c74757b5cf98bf8ad76613872a32c`；本决定不修改产品代码、测试、依赖或
   lockfile。

## Alternatives Considered

- 增加品牌、公司、产品或实体词典：拒绝。集合不可穷举，会形成维护和绕过风险。
- 继续增加 dependency 或 token 启发式：拒绝。同构 parse 无法提供所需区分，规则只会
  转移误报与漏报。
- 在 TASK-016B 引入外部知识或语义模型：拒绝。超出当前 Local-only 语言契约、依赖与
  许可证边界。
- 将同构结构全部判为 `UNCERTAIN`：拒绝作为当前 TASK-016B 行为，因为会误拒已明确
  要求保持的正常自然语言；内容质量风险应在独立边界处理。

## Consequences

- TASK-016B 继续提供语言/script 与自然语言结构的保守 fail-closed 门禁，但不宣称能
  识别所有品牌短语或 entity stuffing。
- 通过 Language Validator 不等于内容质量、事实性或实体真实性已验证。
- 后续 Content Quality 设计必须明确自己的证据来源、误报/漏报策略、Artifact/cache
  边界与独立审查门禁。
- P1-2 `ScoreResult` contract、P1-3 cache provenance、TASK-016C、Cloud、Router、
  Weekly production、DB Schema 与 migration 均不受本决定影响。
