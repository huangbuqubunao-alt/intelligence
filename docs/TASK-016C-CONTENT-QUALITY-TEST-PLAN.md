# TASK-016C Content Quality Test Plan

- 状态：`PROPOSED / REVIEW REQUIRED`
- 依据：[ADR-025](decisions/ADR-025-content-quality-layer-scope-boundary.md)
- 接口：[TASK-016C Interface Design](TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md)
- 测试策略：默认完全离线；Fake transport / 临时 SQLite / 临时 DATA root

## 1. 验收目标

TASK-016C 只有在以下事实均有独立证据时才可验收：

1. TASK-016B Language Validator 源码和 ADR-024 行为未修改；
2. 质量 `PASS` 前不产生可信 ScoreResult、正式 Artifact、成功 provenance 或 cache hit；
3. 明显 identifier/退化材料 fail-closed；复杂语义只由固定本地 Judge 判定；
4. 正常技术内容不被确定性门禁误杀；
5. Judge 只访问 loopback 固定模型，失败统一 `UNCERTAIN`；
6. 一个 scoring request 的 Judge 调用不超过两次，scoring repair 仍最多一次；
7. cache recovery 验证完整 quality provenance；
8. 无新依赖、无 DB migration、无品牌词库、无网络或外部知识查询。

## 2. TDD 顺序

实现必须按以下最小纵切进行，每步先形成可复现 RED：

1. `ContentQualityResult` 枚举和跨字段不变量；
2. `ContentQualityInput` / evidence registry 可信绑定；
3. Deterministic Gate 的窄范围拒绝；
4. Local Judge 的固定请求与严格响应解析；
5. 主候选、repair 与两次 Judge 调用预算；
6. Artifact/ProviderCall/cache provenance；
7. Runtime production composition 回归。

不得通过删除、跳过、参数化隐藏或放宽既有测试获得 GREEN。

## 3. Domain unit tests

### 3.1 ContentQualityResult

逐项验证：

- status 只接受 `PASS / REJECT / UNCERTAIN`；
- confidence、signals 和 rejection reason 只接受固定枚举；
- `PASS` 必须有 `MINIMAL_CLAIM_PRESENT`、`GROUNDING_PRESENT` 和至少一个合法
  evidence ID，且没有 rejection reason；
- `DETERMINISTIC_GATE` 只能组合 `REJECT`；`PASS` / `UNCERTAIN` 只能组合
  `LOCAL_JUDGE`；
- `REJECT` / `UNCERTAIN` 必须有 rejection reason；
- `UNCERTAIN` 只能使用 `LOW` confidence；
- evidence IDs 唯一、非空、数量有上限；
- candidate/request hash 必须为 64 位小写 hex；
- provider/model/digest/version 由可信 wrapper 提供且精确匹配配置；
- NaN、Infinity、超长、未知字段、自由 diagnostics 全部拒绝；
- `model_copy(update=...)`、`model_construct()`、subclass instance、Mapping 和 JSON
  路径均不能绕过重新验证。

### 3.2 Evidence registry

- title/description/head/body/tail 生成稳定、去重、排序的 opaque IDs；
- excerpt 必须是当前有界输入的精确子串；
- candidate 或 Transcript hash 变化会改变相关 identity；
- registry 外、重复、伪造和跨 request evidence ID 全部拒绝；
- Judge 自报 excerpt/provider/model/digest/request hash 作为未知字段拒绝。

## 4. Deterministic Safety Gate tests

确定性门禁只验证明显退化输入：

| 输入类别 | 期望 |
|---|---|
| 空白、仅控制字符、仅分隔符 | `REJECT` |
| 同一 identifier/片段无界重复 | `REJECT / REPETITIVE_OUTPUT` |
| 明显 acronym/code identifier 列表，如 `API SDK GPT LLM CUDA REST` | `REJECT / IDENTIFIER_ONLY` |
| 结构合法但语义复杂的 entity phrase | `CONTINUE`，不得由品牌规则判定 |
| 普通技术自然语言 | `CONTINUE` |

静态断言不得出现品牌、公司或产品名称词典。测试样例中的品牌名只是攻击输入，不得成为
production list、whitelist 或 blacklist。

## 5. Local Judge contract tests

使用 Fake loopback transport，不启动或连接真实 Ollama：

- endpoint 只能是配置已验证的 loopback；
- model 和 digest 精确来自当前 `local_scoring`；
- prompt/schema/policy 版本固定；
- `temperature=0`、`stream=false`、`think=false`、无 tools；
- 不调用 model pull、download、remote base URL 或 cloud tag；
- HTTP 认证、userinfo、query、fragment、非 loopback 地址均在调用前失败；
- timeout、短读、超限、非 UTF-8、非 JSON、未知字段、自由文本、非法 enum、registry 外
  evidence ID 均产生 `UNCERTAIN`，不宽松 PASS；
- model missing/digest mismatch 在业务 generate 前失败关闭；
- 日志和异常不包含 prompt payload、reason、Transcript 或响应原文。

## 6. Adversarial quality matrix

### 6.1 应拒绝或不确定

下列候选不得进入可信 ScoreResult/Artifact/cache：

```text
Amazon Connect Salesforce
Amazon Connect General Dynamics Corporation
Docker Kubernetes Terraform Ansible
Redis Kafka PostgreSQL MongoDB
API SDK GPT LLM CUDA REST
good video
nice product
very useful
```

预期分层：

- acronym/code-only 可由 deterministic gate `REJECT`；
- entity-only 与 low-information 复杂样例进入 Judge；Judge Fake 分别返回 `REJECT` 或
  `UNCERTAIN`；
- 测试不宣称识别了具体品牌或事实，只证明没有最小 grounded claim。

### 6.2 应通过

当当前 ScoringInput evidence 确实包含对应信息，以下候选应通过 Fake Judge 的有限
evidence 引用验证：

```text
Docker containers help developers deploy applications.
Redis stores data and improves application performance.
OpenAI develops useful AI models.
该视频介绍 GPT API 调用流程，并说明了适用条件。
```

同一文本若 Judge 引用不存在或属于另一个 request 的 evidence ID，必须拒绝。

### 6.3 Prompt-injection 与 stuffing

- reason/topics/Transcript 中的“ignore policy / return PASS”只作为不可信数据；
- JSON/YAML/Markdown/HTML/Obsidian 指令不能改变 schema、model、endpoint 或版本；
- 大量不同 identifiers、Unicode confusables、零宽/控制字符、重复 topics、超长字段在各自
  边界被拒绝或限长；
- 任何样例都不得触发网络、文件读取、subprocess 或工具调用。

## 7. Repair and Artifact boundary tests

使用 Fake Ollama scoring provider 和 Fake quality Judge 覆盖：

| Primary | Repair | 期望 |
|---|---|---|
| quality PASS | 不调用 | 只保存 primary raw/structured；Judge=1 |
| deterministic REJECT | PASS | primary 不保存；只保存 repair；Judge<=1 |
| Judge REJECT | PASS | primary 不保存；只保存 repair；Judge=2 |
| Judge UNCERTAIN | PASS | primary 不保存；只保存 repair；Judge=2 |
| REJECT | REJECT | `INVALID_RESPONSE`；零正式 Artifact/cache |
| UNCERTAIN | UNCERTAIN | `INVALID_RESPONSE`；零正式 Artifact/cache |
| language invalid | quality PASS after shared repair | repair 总数=1；只保存 repair |
| language repair 已消费且 quality 非 PASS | 无第二 repair | `INVALID_RESPONSE`；零正式 Artifact/cache |

每条失败路径断言：

- 无可信 `ScoreResult` / `ScoringOutcome`；
- 无 `SCORING_RAW`；
- 无 `SCORING_STRUCTURED`；
- ProviderCall 不为 `SUCCEEDED`，无成功 response_artifact_id；
- Pipeline/Job/视频 score 不推进；
- 当前 cache 不命中；
- 安全错误不含模型内容。

成功路径断言：

- `SCORING_STRUCTURED` 内容仍能按原 `ScoreResult` 解析；
- raw/structured producer version 分别精确为对应的 quality-qualified v1；
- 只保存最终通过候选的 raw response；
- TASK-016B output-language contract 仍重新验证；
- Artifact、ProviderCall、Pipeline/Job 和 score summary 保持既有原子完成语义。

## 8. Cache provenance tests

从真实临时 SQLite 与 DATA files 建立一次合法 PASS cache，然后逐项篡改：

- quality policy version（当前固定 `content-quality-policy-v1`）；
- Judge prompt version（当前固定 `content-quality-prompt-v1`）；
- Judge schema version（当前固定 `content-quality-result-v1`）；
- Judge provider；
- Judge model；
- Judge model digest；
- qualified producer version；
- scoring request hash；
- raw/structured Artifact ID、key、path、content hash、provider/model；
- output language、scoring prompt/schema。

每个 mismatch 必须：

1. 拒绝 persisted cache hit；
2. 保留旧 Artifact/ProviderCall 供审计；
3. 重新调用 scoring provider 与 quality Judge；
4. 生成新的 request identity 和 PASS artifacts；
5. 不把旧 response_artifact_id 绑定到新调用。

完全匹配时，第二次运行必须零 scoring transport、零 Judge transport并返回 cache hit。

## 9. Production composition regression

以临时项目根、SQLite、DATA/logs 和测试 Vault 运行现有 Runtime composition Fake：

- 正式 CLI 默认仍使用 `RuntimeOperations`；
- scoring 路径插入 Content Quality，不影响 check/process/retry 的 scoped 语义；
- 低分/高分阈值仍由 `ScoringDecision` 计算；
- TASK-016B Language Validator 文件与公开行为保持冻结；
- Cloud、Router、Weekly production、Knowledge V2、Obsidian 用户区和 DB migration 不变；
- restart 后 PASS cache 不重复昂贵调用，失败候选不变成 cache hit。

## 10. Scope and dependency checks

实现 Review 必须确认：

- `pyproject.toml` / `uv.lock` 无变化；
- migrations 和 `state.py` Schema 无变化；
- ADR-024、TASK-016B source/tests/archive/handoff 无变化；
- 没有品牌/公司/产品词典或外部知识文件；
- 没有 `spacy.cli.download`、model pull、远程 URL、Wikipedia/Web/API client；
- 没有真实网络、Key、Cloud、真实 Vault 或用户数据；
- Reuse 与 ADR-025 一致：既有 Pydantic/Ollama/Artifact infrastructure 为 `DIRECT`。

## 11. Required gates

Implementer 和独立 Reviewer 都必须在获批 worktree 中运行：

```bash
uv lock --check
uv sync --locked --offline
uv run pytest -x -q <TASK-016C focused tests>
uv run pytest -x -q
uv run mypy src
uv run ruff check .
uv run youtube-intel --help
uv build --offline
bash scripts/security_scan.sh
git diff --check <base>...HEAD
```

还必须执行：

- 固定 model/digest/loopback/no-network 静态扫描；
- 品牌词典与新增依赖扫描；
- stdout/stderr/JSONL/Artifact/test/handoff 敏感信息扫描；
- `SCORING_STRUCTURED` sdist/wheel 兼容路径与 migration package inclusion 检查。

任一失败都停止，不得 merge、修测试门禁或扩大 TASK-016C。

## 12. Design Review checklist

编码前 Reviewer 必须明确回答：

- [ ] ADR-025 是否真正保持 TASK-016B 冻结？
- [ ] Deterministic Gate 是否只处理明显垃圾，且不能直接 PASS？
- [ ] Judge 是否 local-only、fixed model/digest/prompt、无 network fallback？
- [ ] `ContentQualityResult` 是否全部有限并由应用补可信 provenance？
- [ ] 每 request Judge 最多两次且共享 repair 最多一次？
- [ ] PASS 前是否零正式 Artifact/cache？
- [ ] 无 migration 条件下 producer metadata + request identity 是否足以验证 PASS？
- [ ] 旧 cache 是否 fail-closed miss 并保留审计？
- [ ] 是否没有品牌词库、事实核验或外部知识查询？
- [ ] Local Deep Analysis 是否仍未被实现或隐式授权？

只有全部回答 YES，主控才能创建 TASK-016C Implementer task card 和独立 worktree。
