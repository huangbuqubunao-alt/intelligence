# TASK-016C Content Quality Test Plan — Round 3.5

- 状态：`PROPOSED / INDEPENDENT DESIGN REVIEW REQUIRED`
- 依据：[ADR-025](decisions/ADR-025-content-quality-layer-scope-boundary.md)
- 接口：[TASK-016C Interface Design](TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md)
- 测试环境：完全离线；Fake scoring/Judge transport、临时 SQLite、临时 DATA root

## 1. 验收目标

TASK-016C 只有在以下事实都有独立证据时才可验收：

1. TASK-016B source、ADR-024 与 Language Validator 行为未修改；
2. Deterministic Gate 只有三个机械 reason，所有 identifier/entity 样例进入 Local Judge；
3. Provider Adapter 只能返回 `ScoringCandidate`；
4. primary、repair、cache recovery 都只能经 `TrustedScoringFinalizer` 创建
   `ScoreResult`；
5. 每个成功结果有完整、可重算的 Quality PASS attestation；
6. cache hit 不调用 Judge，缺失/版本不匹配与 integrity failure 使用不同恢复语义；
7. PRIMARY 与 REPAIR Judge 各最多一次，崩溃未知状态不重复调用；
8. 三项 confidence 和 status/reason/signal 组合全部 fail-closed；
9. Finalizer 成功之前零 scoring Artifact、response_artifact_id、ProviderCall SUCCESS 或
   cache identity；成功后只允许单事务 atomic persistence；
10. 无新依赖、无 migration、无品牌词库、无网络或外部知识查询。

## 2. TDD 纵切顺序

实现须逐步形成可复现 RED，再实现 GREEN：

1. 三个 deterministic reason 与 Gate 组合；
2. `ContentQualityResult` 三 confidence 和合法矩阵；
3. `ScoringCandidate` Provider contract 与唯一 Finalizer；
4. `ContentQualityInput`、Evidence Registry、candidate/input hash；
5. Local Judge 固定请求与严格响应 wrapper；
6. Quality PASS attestation 创建与验证；
7. PRIMARY/REPAIR operation identity、一次性预算与崩溃恢复；
8. raw envelope、structured Artifact 与 cache recovery；
9. production composition 和 TASK-016B 回归。

不得删除、跳过、弱化断言、修改既有测试门禁或把失败样例移入生产词表。

## 3. Deterministic Gate tests

### 3.1 唯一允许拒绝

| 输入 | 预期 |
|---|---|
| 空/规范化后空的内容 | `REJECT / EMPTY_CONTENT` |
| 含禁止控制字符 | `REJECT / CONTROL_CHARACTER_INVALID` |
| 两个规范化后完全相同的相邻非空 segment | `REJECT / EXACT_REPETITION` |
| 大小写不同或近似重复 | `CONTINUE`，不得模糊判断 |

固定顺序和字符矩阵必须逐项覆盖：

- 严格 decode 失败在 Gate 前拒绝；
- NULL `U+0000` -> `CONTROL_CHARACTER_INVALID`；
- TAB `U+0009` 与 LF `U+000A` -> control scan 允许；
- CR `U+000D` -> 拒绝；
- ZERO WIDTH SPACE `U+200B` -> 拒绝；
- BOM `U+FEFF` -> 拒绝；
- 其他 Unicode `Cc` -> 拒绝。

EXACT_REPETITION 表格：

| reason | 预期 |
|---|---|
| `same\nsame` | `REJECT / EXACT_REPETITION` |
| ` same\nsame ` | 首尾 ASCII trim 后 `REJECT` |
| `same\n\nsame` | 删除空 segment 后 `REJECT` |
| `same\n same` | `CONTINUE`；segment 不二次 trim |
| `Same\nsame` | `CONTINUE`；禁止 lowercase/casefold |
| `same!\nsame` | `CONTINUE`；禁止标点 normalization |
| `same\nother\nsame` | `CONTINUE`；只比较相邻 segment |

静态扫描不得出现 casefold/lower、tokenization、NLP、Unicode/标点 normalization 或
非相邻 repetition 逻辑。

### 3.2 必须进入 Local Judge

以下逐项断言 Gate 为 `CONTINUE` 且 Judge Fake 被调用一次：

```text
API SDK GPT LLM
Docker Kubernetes Terraform
General Dynamics Corporation
Amazon Connect Salesforce
```

静态扫描 Gate production Diff 不得出现：

- identifier/acronym/technical/brand/product 词表；
- token 数量、大小写、首尾、位置、词尾规则；
- POS/dependency/NER/spaCy 调用；
- `PASS` 返回值。

## 4. ContentQualityResult contract matrix

### 4.1 合法矩阵

分别构造并 round-trip：

- Gate `REJECT`：三个 reason 各一例；Judge identity 全空；
- Judge `PASS`：decision=`HIGH`，grounding/usefulness=`MEDIUM` 与 `HIGH` 的边界组合；
- Judge `REJECT`：每个内容 reason 与同名负向 signal；
- Judge `UNCERTAIN`：`GROUNDING_INSUFFICIENT`、`JUDGE_UNAVAILABLE`、
  `JUDGE_INVALID_RESPONSE`。

### 4.2 非法组合

参数化拒绝：

- Gate + `PASS` / `UNCERTAIN`；
- Gate reason 与 Judge source，或 Judge reason 与 Gate source；
- Gate result 带 Judge identity/evidence；
- `PASS` decision 不是 `HIGH`；
- `PASS` grounding/usefulness 为 `LOW`；
- `PASS` 缺正向 signal、缺 evidence、带 rejection reason 或负向 signal；
- `REJECT` 缺 reason/同名 signal，或同时声称完整 PASS signals；
- identifier/entity/low-information/minimal-claim `REJECT` 的 usefulness 不是 `LOW`；
- grounding `REJECT` 的 grounding 不是 `LOW`，或带 `GROUNDING_PRESENT`；
- `UNCERTAIN` 任一 confidence 不是 `LOW`，或带完整 PASS signals；
- 重复/空白/registry 外 evidence ID；
- unknown enum/field、自由 diagnostics、错误 hash、超限集合。

每个非法组合必须覆盖五条入口：

1. 普通 constructor；
2. `model_copy(update=...)` 后进入 trusted wrapper；
3. `model_construct()` 后进入 trusted wrapper；
4. `model_validate_json()` restore；
5. subclass/Mapping instance 进入 wrapper。

断言 wrapper 总是从 canonical mapping/JSON 重建；对象已是目标类型也不能跳过验证。

## 5. ScoringCandidate 与唯一 Finalizer tests

### 5.1 Provider boundary

- Fake primary/repair Adapter 只返回 `ScoringCandidate`；
- `score` 接受并 round-trip 非整数 `7.25`，不得丢失精度；
- `dimensions=None` 与完整 `ScoreDimensions` 都合法；
- Candidate 与 Finalizer 输出的 reason/topics/should_summarize/dimensions 业务字段保持等值；
- 静态契约确认 ADR-025 supersede SYSTEM_DESIGN 的 Provider->ScoreResult 旧语义，生产
  composition 只有 Provider->Candidate->Finalizer 一条可信路径；
- 返回 `ScoreResult`、带 provenance 的 candidate、未知 quality 字段全部拒绝；
- Provider response 在 quality `PASS` 前不能被 Runtime/Artifact/cache 当成结果。

### 5.2 Finalizer positive path

用合法 candidate/context/input/attestation 调用 Finalizer，断言：

- 返回现有公共 shape 的 `ScoreResult`；
- provider/model/output language/prompt/schema 来自 trusted context；
- candidate、input、attestation hash 全部重算；
- TASK-016B language invariant 仍执行；
- primary、repair 和 cache recovery 三个入口都调用同一 Finalizer。

### 5.3 Finalizer bypass matrix

逐字段篡改 candidate、context、attestation：

- `model_copy(update=...)`；
- `model_construct()`；
- Mapping / JSON；
- cache 中伪造的 ScoreResult instance；
- candidate/output language 不一致；
- candidate/input/attestation hash 任一不一致；
- policy/prompt/schema/provider/model/digest 任一不匹配；
- evidence registry 外引用。

全部必须拒绝且无 ScoreResult/Artifact/cache。静态扫描生产代码确认除
`TrustedScoringFinalizer` 外，没有 TASK-016C 路径直接构造、copy、construct 或 restore
可信 `ScoreResult`。

## 6. Local Judge contract tests

使用 Fake loopback transport，不启动真实 Ollama：

- endpoint 只能是已验证 loopback；
- provider/model/digest 精确来自当前 trusted local config；
- policy/prompt/schema 固定；
- `temperature=0`、`stream=false`、`think=false`、无 tools；
- 禁止 pull/download、remote base URL、cloud tag、dynamic prompt、network fallback；
- authentication、userinfo、query、fragment、非 loopback 在调用前失败；
- timeout、短读、超限、非 UTF-8、非 JSON、unknown field、invalid enum、registry 外 ID
  产生 `UNCERTAIN`；
- model missing/digest mismatch 在业务 generate 前 fail-closed；
- stdout/stderr/JSONL 不含 prompt、candidate、evidence excerpt、Transcript 或响应原文。

## 7. 精确内容质量案例

### 7.1 Attack / low-quality

以下四例必须由 Gate `CONTINUE`，再由 Judge Fake `REJECT` 或 `UNCERTAIN`；不得进入
Finalizer/Artifact/cache：

```text
Amazon Connect Salesforce
Docker Kubernetes Terraform
API SDK GPT LLM
General Dynamics Corporation
```

测试只证明 Judge 判定“不足以成为有 grounding 的评分理由”，不宣称识别了品牌、公司、
产品或实体事实。

### 7.2 Normal

当前 Evidence Registry 包含相应输入时，Judge Fake 可对以下候选返回合法 PASS：

```text
Docker containers help developers deploy applications
Redis stores data and improves application performance
OpenAI develops useful AI models
```

每例必须满足三项 confidence 门槛、两个正向 signal 和合法 evidence IDs。相同 Judge
response 若换成另一 request 的 evidence ID，必须拒绝。

### 7.3 Low information 与 injection

`good video`、`nice product`、`very useful` 必须进入 Judge 并非 PASS。Prompt injection、
Markdown/HTML/Obsidian 指令、Unicode confusables 和 stuffing 都不能改变 model、endpoint、
版本、schema 或 evidence registry，也不能触发文件、工具、subprocess 或网络访问。

## 8. Fake flow 与事件顺序

### 8.1 Primary PASS

```text
CANDIDATE_PRIMARY
LANGUAGE_PRIMARY
QUALITY_PRIMARY
ATTESTATION_PRIMARY
FINALIZE
ATOMIC_PERSISTENCE
```

断言 Judge=1、repair=0。ATTESTATION_PRIMARY 结束时仍无 Artifact、response_artifact_id、
ProviderCall SUCCESS 或 cache；Finalizer 成功后一次事务才保存 attested raw envelope、
structured result、两份 completion 与 cache identity。

`CANDIDATE_*` 必须包含严格 schema parsing；非法 DTO 在 language/quality 前停止并消费共享
repair。不得另插一个可以绕过 Candidate 的 schema 事件。

### 8.2 Primary quality failure, repair PASS

必须严格产生：

```text
CANDIDATE_PRIMARY
LANGUAGE_PRIMARY
QUALITY_PRIMARY
REPAIR
CANDIDATE_REPAIR
LANGUAGE_REPAIR
QUALITY_REPAIR
ATTESTATION_REPAIR
FINALIZE
ATOMIC_PERSISTENCE
```

不得遗漏 repair candidate/language，不得提前 Finalize，不得保存 primary raw。

### 8.3 失败矩阵

| Primary | Repair | 期望 |
|---|---|---|
| Gate REJECT | Judge PASS | primary 不调 Judge；repair Judge=1；只保存 repair |
| Judge REJECT | Judge PASS | Judge=2；只保存 repair |
| Judge UNCERTAIN | Judge PASS | Judge=2；只保存 repair |
| REJECT | REJECT | `INVALID_RESPONSE`；零正式 Artifact/cache |
| UNCERTAIN | UNCERTAIN | `INVALID_RESPONSE`；零正式 Artifact/cache |
| language invalid | quality PASS after repair | shared repair=1；只保存 repair |
| repair language invalid | 不执行 quality repair | `INVALID_RESPONSE`；零正式 Artifact/cache |

每条失败路径断言：无可信 ScoreResult/ScoringOutcome、无 `SCORING_RAW`、无
`SCORING_STRUCTURED`、无成功 scoring response_artifact_id、Pipeline/Job/score 不推进，
当前 cache 不命中，安全错误不含模型内容。

## 9. Judge budget、crash 与 recovery tests

为 PRIMARY / REPAIR operation 分别验证 canonical identity 包含全部冻结字段且 role 不同。
另以 Fake Repository 证明 one-shot wrapper 先查询：record 不存在时可 reserve/call；
live PENDING 只能等待或停止；expired PENDING 只有在 deterministic PASS Artifact 完整
验证后才可进入 artifact recovery；任何既有 record 都不得进入通用 expired/failed
takeover 后再外部调用。

| 预置状态 | 运行行为 | 调用计数 |
|---|---|---:|
| missing PRIMARY | reserve -> call -> complete | 1 |
| missing REPAIR after explicit primary non-PASS | reserve -> call -> complete | 1 |
| live PENDING | fail-closed / in progress | 0 |
| expired PENDING + verified PASS artifact | artifact recovery | 0 |
| expired PENDING without verified PASS artifact | `ATTEMPT_UNKNOWN`，不 reclaim | 0 |
| FAILED_RETRYABLE | role 已消费，不自动 retry | 0 |
| FAILED_FINAL | role 已消费 | 0 |
| SUCCEEDED + valid PASS attestation | recover | 0 |
| SUCCEEDED + missing/mismatched artifact | integrity failure | 0 |

故障注入点：reserve 后、transport 前；transport 后、response parse 前；PASS wrapper 后、
attestation 构造前；attestation 后、Finalizer 前；Finalizer 后、临时文件前；临时文件后、
atomic transaction 前；transaction 内每个 Artifact/completion/cache/stage 步骤。任何“可能
已调用”的状态都不能重调同一 identity；transaction 内失败不得留下部分 DB 成功状态。

统计断言：PRIMARY<=1、REPAIR<=1、总 Judge<=2、scoring repair<=1；进程重启不能清零。

## 10. Quality PASS attestation tests

### 10.1 生成与 round-trip

- candidate/input/Judge operation 生成稳定 canonical hash；
- attestation hash 排除自身字段并稳定；
- attestation 首先只存在内存；Finalizer 前 Repository 中不存在其 Artifact/cache/成功调用；
- raw envelope round-trip 保留最终 provider raw 与完整 attestation；
- Judge ProviderCall `SUCCEEDED.response_artifact_id` 指向同一 raw envelope；
- structured payload 仍能由 Finalizer 的 persisted candidate 路径恢复，且外部 ScoreResult
  JSON shape 不变。

### 10.2 单字段篡改

逐项篡改并拒绝：

- candidate hash；
- quality input hash；
- scoring request hash；
- policy/schema/prompt version；
- scoring schema/prompt version；
- Judge provider/model/digest；
- operation/request hash/attempt role；
- 三项 confidence；
- evidence IDs；
- attestation hash；
- raw Artifact key/path/content hash/producer version；
- Judge ProviderCall status 或 response artifact ID。

任何篡改不得因重新计算单个外层 hash 而变成可信；Recovery 必须从当前 input/config 和两份
Artifact 重建全链交叉关系。

### 10.3 Atomic persistence tests

Finalizer 成功前逐项查询并断言不存在：

- `SCORING_RAW` / `SCORING_STRUCTURED` Artifact record；
- scoring/quality `response_artifact_id`；
- scoring/quality ProviderCall `SUCCEEDED`；
- 可命中的 cache identity；
- pipeline `SCORED` 状态。

Finalizer 成功后调用一次 atomic Repository API。对 raw insert、structured insert、quality
attestation binding、scoring completion、quality completion、cache identity 和 stage update
逐点注入异常，断言整个 SQLite transaction 回滚且零部分状态。全成功时单事务提交全部对象，
两个 ProviderCall 与 attested raw Artifact/structured Artifact 关系完整。事务前临时文件不在
Artifact 索引中，不能 cache hit；失败后仅可作为不可见临时文件清理，不能恢复成成功记录。

## 11. Cache recovery tests

在临时 SQLite/DATA 建立合法 PASS cache：

### 11.1 完整 hit

第二次运行必须：

- scoring transport=0；
- Judge transport=0；
- 重算 candidate/input/attestation hash；
- 验证 Judge call 与 raw envelope；
- 经 Finalizer 重建 ScoreResult；
- 返回 persisted cache hit。

允许只读观察历史 atomic commit 中已有的 `SUCCEEDED` 和 Artifact；断言当前执行在
Finalizer 成功前没有新 ProviderCall/Artifact/cache/stage 写入，也没有向调用方返回 hit。

### 11.2 普通 miss

以下视为 miss，保留旧审计并以新 identity 计算：

- legacy cache 无 quality attestation；
- quality/scoring policy、prompt、schema 版本变化；
- trusted Judge model/digest 变化；
- output language 或 scoring request 变化。

断言新 identity 的 scoring provider/Judge 各按预算调用，旧 Artifact 不删除、不覆盖。

### 11.3 Integrity failure / unknown attempt

以下不是普通 miss，不得重新调用同一 Judge identity：

- 当前版本 attestation 或 Artifact hash 矛盾；
- Judge call `SUCCEEDED` 但 response artifact 不一致；
- 当前 identity 为 live/expired PENDING；
- 当前 identity 已 FAILED。

断言 fail-closed、Judge=0、无新成功 Artifact/cache。

## 12. Production composition regression

以临时项目根、SQLite、DATA/logs 和测试 Vault 运行 Fake production composition：

- CLI 默认仍使用 `RuntimeOperations`；
- check/process/retry scoped 语义不变；
- ScoreResult 只由 Finalizer 返回；
- TASK-016B source、ADR-024、language tests 与 spaCy pipeline hash 均不变；
- scoring thresholds 与 `ScoringDecision` 不变；
- Cloud、Router、Weekly production、Knowledge V2、Obsidian 用户区、DB Schema/migration
  不变；
- restart 后合法 cache 不重复调用；失败或 unknown attempt 不变成 cache hit。

## 13. Scope、dependency 与 leakage checks

实现 Review 必须确认：

- `pyproject.toml` / `uv.lock` 无变化；
- migrations 与 state Schema 无变化；
- 允许为原子多 completion 增加 Repository 方法，但不得改变表、CHECK 或 migration；
- ADR-024、TASK-016B source/tests/archive/handoff 无变化；
- 没有品牌/公司/产品/技术词典；
- Gate 没有 token/case/POS/dependency/spaCy 逻辑；
- 没有 download/model pull/remote URL/Wikipedia/Web/API client；
- 没有真实网络、Key、Cloud、真实 Vault 或用户数据；
- stdout/stderr/JSONL/Artifact/test/handoff 不泄漏 candidate、evidence 或原始响应；
- Reuse 与 ADR-025 一致，且没有新增依赖。

## 14. Required gates

Implementer 与独立 Reviewer 均须在获批 worktree 运行：

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

另须执行：Finalizer 唯一构造点静态扫描、Judge one-shot operation 扫描、Gate 禁止规则
扫描、attestation/cache adversarial matrix、固定 loopback/model/digest/no-network 扫描和
全输出面泄漏扫描。

## 15. Independent Design Review checklist

- [ ] Deterministic Gate 是否精确只有三个 reason？
- [ ] 四个攻击样例是否全部进入 Judge？
- [ ] Provider 是否只能返回 ScoringCandidate？
- [ ] Finalizer 是否为 primary/repair/cache 唯一 ScoreResult 入口？
- [ ] Candidate 是否保持 score=float、dimensions 可选和全部现有业务字段？
- [ ] ADR-025 是否明确 supersede SYSTEM_DESIGN 的 Provider->ScoreResult 旧契约？
- [ ] PASS attestation 是否绑定用户要求的全部字段并可重算？
- [ ] Finalizer 前是否零 Artifact/call success/cache，之后是否单事务原子提交？
- [ ] EXACT_REPETITION 和 CONTROL_CHARACTER 是否严格采用冻结算法与顺序？
- [ ] Cache hit 是否零 Judge 调用？
- [ ] PRIMARY/REPAIR 是否各最多一次，PENDING unknown 不重调？
- [ ] 三项 confidence 与 status/reason/signal 矩阵是否封闭？
- [ ] model_copy/model_construct/JSON restore 是否均不能绕过？
- [ ] Fake event 顺序是否精确且 PASS 前零正式 Artifact？
- [ ] 无 migration 条件下 raw envelope 是否不破坏 structured consumer？
- [ ] ADR-023 是否明确 TASK-016C 被 ADR-025 supersede，Local Deep Analysis 为 TBD？
- [ ] TASK-016B、依赖、DB、Cloud、Router、Weekly 是否完全未改？

只有全部回答 YES，才可授权编码。
