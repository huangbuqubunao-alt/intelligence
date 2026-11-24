# TASK-016B 交接报告

## 元数据

- Task: `TASK-016B`
- Role: `Implementer`
- Agent/session: `Codex primary`
- Base branch/commit: `main@60551f2b8606e50ed8e4bd8d161ac5636a8a9266`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-016b-scoring-output-language`
- Branch: `codex/task-016b-scoring-output-language`
- Head commit: `本实现提交（SHA 见最终 Implementation Report）`
- Started: `2026-08-13`
- Reported: `2026-08-13`

## 目标与范围

- 任务目标：让 Local Scoring 的用户可见 `ScoreResult.reason` 遵守
  `general.output_language`，并将语言纳入输入、Prompt、缓存身份、结构化结果与
  持久恢复 provenance。
- 允许修改：评分领域契约、评分服务、Ollama Adapter、Runtime provenance、固定
  Prompt、相关文档、任务卡、handoff 与测试。
- 实际修改：新增 `zh-CN | en` 可信语言字段；Prompt/Schema/Artifact producer 升为
  v2；加入保守错语种校验和既有一次 repair；跨语言缓存、旧 Artifact 与当前配置
  不匹配时 fail-closed。
- 明确未做：未实现或启动 TASK-016C；未实现 Deep Analysis、Knowledge Provider、
  Hybrid/Cloud Router、Note/Weekly V2、UI、migration 或 TASK-015 Remaining P2。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| AC-1：中文/英文理由遵守配置 | PASS | Prompt 指令、`ScoreResult.output_language`、保守语言校验及双向 repair 测试 |
| AC-2：语言进入缓存与持久身份 | PASS | `ScoringInput`、normalized input hash、结构化 Artifact、Runtime/current-config provenance 与跨语言缓存测试 |
| AC-3：旧缓存和错语言 fail-closed | PASS | v2 版本隔离、缺少/篡改语言的 provenance 回归、错误语言不写缓存 |
| AC-4：真实 Local-only smoke | PASS | 固定视频 `5ljV0Vxu00M`、`qwen3:8b`、`zh-CN` 返回中文 reason；无 Deep Analysis、Cloud、DB 或 Vault |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| TDD RED | PASS | 新语言契约初始 `5 failed, 2 passed`，证明字段、参数与验证缺失 |
| Focused pytest | PASS | `185 passed` |
| `uv lock --check`（sync 前后） | PASS | `84 packages`，锁文件未变 |
| `uv sync --locked --offline` | PASS | `61 packages` checked，无下载 |
| `uv run pytest -x -q` | PASS | `704 passed in 35.15s` |
| `uv run mypy src` | PASS | `27 source files` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run youtube-intel --help` | PASS | CLI help 正常，仅帮助命令 |
| `uv build --offline` | PASS | sdist/wheel 成功，wheel 内含 `scoring-prompt-v2` |
| `bash scripts/security_scan.sh` | PASS | `status=clean`；既有 WARN 不阻断 |
| `git diff --check` | PASS | 无 whitespace error |

## Real Local Scoring Smoke

- 视频：`5ljV0Vxu00M`
- 输出语言：`zh-CN`
- Provider / model：`ollama / qwen3:8b`
- Contract：`scoring-prompt-v2 / score-result-v2`
- 真实 scoring reason：`该视频详细解释了国际空间站如何维持氧气供应，涉及电解水制氧、气体分离技术以及未来可能的磁流体制氧方法（MOGA），内容科学严谨，具有较高的学习价值和产品应用价值。视频通过实际案例和未来技术展望，激发了观众对航天工程的兴趣，同时提供了实用知识。`
- 隔离边界：使用公开 metadata/一条公开字幕与 loopback Ollama；未读取项目配置或
  Key，未写数据库、Vault，未调用 Cloud，未继续 Deep Analysis。

## Diff 复核

- 修改文件：评分契约/服务/Adapter/Runtime、双份固定 Prompt、System Design、任务
  卡/索引/handoff，以及直接受字段升级影响的 scoring/runtime/note/weekly/E2E 测试。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：否；`dist/` 与 `.venv/` 为 ignored 本地门禁产物，
  未纳入提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：新增契约的预期 RED；字段升级后旧测试夹具缺少语言的 7 个回归；4 个
  Ruff import-order 问题。均经对应测试和全量门禁复核。
- 辅助检查：首次 wheel Prompt 核验误用不可用的系统 `python`，随后仅以锁定环境的
  `uv run python` 重跑并通过；正式安全扫描在此前已经独立返回 `status=clean`。
- 跳过检查及原因：未运行真实 Cloud/Deep Analysis/真实 Vault，均不在 TASK-016B
  范围且未获授权。
- 剩余风险：语言校验是刻意保守的明显错语种拦截，不是通用自然语言识别器；真实 smoke
  仅证明固定视频与本机 `qwen3:8b` 的 Local Scoring，不代表 TASK-016C 或生产发布。
- `DECISION NEEDED`：`None`

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`见最终 Implementation Report`
- 复现/验证说明：使用上述 Full Gates；真实 smoke 只允许固定视频、本地模型和评分
  reason，不得扩展到 Deep Analysis。

## Final Correction Round 2（2026-08-13）

### Root cause 与修复

- P1-1：旧启发式只检查目标字符是否出现，单个汉字可掩盖英文主体，且小写技术词会
  被误当英文自然语言。现先剥离固定技术词，再分别要求最小汉字主体或英文自然语言
  主体；不使用字符比例，单字符和纯技术词均不能通过，中文技术混排与英文中的短中文
  专名仍保留。
- P1-2：Pydantic 的 deprecated `copy(update=...)` 和 `model_construct()` 可生成
  未重验实例。新增单一 `validate_score_result()` / JSON 入口，把模型实例重新转为
  data 后执行完整 schema + language validators；内存 Cache、Provider/repair、
  Artifact 写入、stage completion 与 Runtime persisted load 均接入可信入口。
- P1-3：Repository cache 只校验 request/provider/model/language，未同时绑定
  `prompt_version` 与 `schema_version`。现 Result 与 ProviderCall 都必须匹配当前
  request 的 request hash、provider、model、output language、prompt 与 schema；
  任一错配均不得返回 `PERSISTED_CACHE_HIT`。

### 对抗与 provenance 证据

- 真实 Ollama Fake-transport 路径覆盖 `zh-CN` 英文主体加单字绕过，以及 `en` 中文
  主体加小写 `api/sdk/llm` 绕过；均进入一次 repair，修复后仍错误则 fail-closed。
- Domain 覆盖短单字、纯技术词、中文+英文技术词、英文主体和英文+中文专名。
- `copy(update=...)`、`model_construct()`、Provider 返回与内存 Cache 注入均在
  trusted boundary 重新验证，不会持久化或返回为有效结果。
- SQLite repository-backed 恢复矩阵分别篡改 Result 的六项 provenance，以及
  ProviderCall 的 prompt/schema version；Provider 调用计数保持 1，证明没有把错版
  Artifact 当作 persisted cache hit。

### Final gates

- Focused contracts/runtime/provider/provenance/weekly：`248 passed`；周报安全与
  Unicode 回归单独为 `41 passed`。
- Full pytest：`729 passed`。
- `uv lock --check`、`uv sync --locked --offline`：PASS，锁文件未变且无下载。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS，sdist/wheel 成功。
- `git diff --check`：PASS。
- 本轮未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge 或 push。

## Reviewer 结论

- Reviewer agent/session：
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1：

## Round 11：本地英文依存分析实现（2026-08-13）

### Root cause 与算法变更

- Round 10 的启发式会把相邻 token、大小写、后缀或有限技术词表误当成英文自然语言
  证据，因此无法可靠区分纯产品/技术实体列表与完整英文句法。
- Round 11 删除这些证明规则，改为固定本地 `en_core_web_sm` 依存分析：只有解析器成功
  加载，且至少两种大小写表示对完整 predicate + subject + argument/complement 结构
  达成共识，英文才为 `VALID`。大小写只用于抵抗模型对实体的偶发误标，不单独增加
  语言可信度。
- `Docker helps`、`Redis stores`、`OpenAI develops` 等缺少完整论元的短语保持
  `UNCERTAIN`。模型包缺失、加载失败或解析异常也统一返回 `UNCERTAIN`。
- 中文继续要求 Han 自然语言证据；Latin 混排只在本地 parser 判断为名词/专名材料时
  兼容。日文、韩文、阿拉伯文等非目标 script 继续 fail-closed。

### Dependency Change Review

- 用户批准并固定两个直接依赖：`spacy==3.8.15` 与 Explosion 官方
  `en_core_web_sm==3.8.0` wheel。模型 wheel 为 12,806,118 bytes，SHA-256 为
  `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`。
- `uv.lock` 从 84 增至 107 packages；新增 23 个包（2 direct + 21 transitive）：
  `annotated-doc`、`blis`、`catalogue`、`cloudpathlib`、`confection`、`cymem`、
  `en-core-web-sm`、`markdown-it-py`、`mdurl`、`murmurhash`、`preshed`、`rich`、
  `shellingham`、`smart-open`、`spacy`、`spacy-legacy`、`spacy-loggers`、`srsly`、
  `thinc`、`typer`、`wasabi`、`weasel`、`wrapt`。
- 新增包在本机安装后的合计文件体积约 48,807,374 bytes；其中 spaCy 约
  19,347,396 bytes，模型约 15,252,156 bytes。新 `uv.lock` SHA-256 为
  `782947100813f925f08e238e45ace62a9247a8a89b60cc706d8419969709d82f`。
- 已更新 `docs/SBOM.md`、`docs/THIRD_PARTY_NOTICES.md` 与
  `docs/REUSE_REGISTER.md`。spaCy/模型主体为 MIT；新增传递项的已安装 metadata
  显示 MIT/BSD/ISC 族许可证。模型来源包含 OntoNotes 5 与 WordNet 3.0，公开分发前
  仍须完成模型级 NOTICE/来源归属复核；此实现不解除 TASK-014 No-Go。
- 运行时只 `import_module("en_core_web_sm")` 并调用包内 `load`；不存在
  `spacy.load`、`spacy.cli.download`、网络 fallback 或用户远程模型地址。

### Adversarial、repair 与 Artifact 证据

- `Docker Kubernetes Terraform Ansible`、其 lowercase/排列变体、`Redis Kafka
  PostgreSQL MongoDB`（含 lowercase）、`OpenAI PyTorch TensorFlow Kubernetes`、
  `REST CUDA NLP CNN` 与复数缩写列表均为 `UNCERTAIN`。
- `Docker containers help developers deploy applications`、`Redis stores data
  and improves application performance`、`OpenAI develops useful AI models` 与
  `This Video Explains Machine Learning Workflows Clearly` 均为 `VALID(en)`。
- 中文 `该视频介绍 GPT API 调用流程` 为 `VALID(zh-CN)`；纯单字加技术标识、日文及
  其他非目标 script 不能形成成功结果。
- Fake Ollama 覆盖 primary validation → 一次 repair → repair validation；失败时
  返回 `INVALID_RESPONSE`，且无 `ScoreResult`、`SCORING_RAW`、
  `SCORING_STRUCTURED` 或成功 `response_artifact_id`；repair 成功仅持久化修复后
  response。既有 ScoreResult 可信入口与六项 cache provenance 校验未改。

### TDD 与门禁

- TDD RED：新增对抗用例初始为 `8 failed, 34 passed, 87 deselected`，直接复现
  lowercase 纯实体列表被误判为英文。
- Focused Domain/Ollama：`130 passed`；E2E recovery：`9 passed`；Note/Weekly 与
  scoring fixture 回归分别为 `49 passed`、`39 passed`。
- `uv lock --check` → `uv sync --locked --offline` → `uv lock --check`：PASS，
  107 resolved / 84 checked，无下载或锁漂移。
- Full pytest：`814 passed`；`uv run mypy src`：PASS（27 source files）；
  `uv run ruff check .`：PASS；`uv build --offline`：sdist/wheel PASS；
  wheel metadata 精确包含两个固定 direct requirements；`git diff --check`：PASS。
- `bash scripts/security_scan.sh`：`status=clean`；仅保留既有非阻断 WARN，项目自身
  LICENSE 仍为 UNRESOLVED。
- 未运行网络、真实 Ollama、Cloud、Vault、TASK-016C、merge、push、tag 或 release。

### Round 11 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 11 Implementation Report。

## Round 12 Correction（2026-08-13）

### Root cause 与 algorithm correction

- Round 11 将 spaCy 给出的 dependency relation 本身当作语言证明，并通过原文、
  `lower()`、`title()` 多版本共识抵抗误标。`Amazon Connect Salesforce` 会被 parser
  误标成 `nsubj + VERB ROOT + dobj`，从而穿透；同一句话的大小写也会改变共识结果。
- Round 12 完全删除大小写变体和 consensus，只解析用户收到的原始 reason 一次。
  大小写不再作为正面或负面语言证据。
- 英文 `VALID` 现在要求：真实 `VERB`；仅允许 `ROOT` 或有明确 coordinated subject
  context 的 `conj` predicate；同时具备 subject 与 object/attribute/complement
  （含介词的 `pobj`/`pcomp`）；并存在 determiner/modifier/coordination/complement
  等自然依存结构。
- subject 与主要 argument 若全部只是无内部自然结构的 `NOUN`/`PROPN` entity-like
  span，则保持 `UNCERTAIN`。该规则只读取 parser 的 POS/dependency tree，不包含品牌
  词表、白名单、黑名单、token 数量/位置或后缀启发式。

### Adversarial matrix

- `Amazon Connect Salesforce`、`Docker Kubernetes Terraform Ansible`、`Redis
  Kafka PostgreSQL MongoDB`、`OpenAI PyTorch TensorFlow Kubernetes`：全部
  `UNCERTAIN`。
- `Kubernetes orchestrates Docker`、lowercase 与全大写变体：结果一致，全部
  `UNCERTAIN`；证明大小写不会改变 bare entity-argument 判定。
- `Docker containers help developers deploy applications` 的原始、lowercase 与
  全大写变体全部 `VALID`；`Redis stores data and improves application performance`、
  `OpenAI develops useful AI models`、`This Video Explains Machine Learning
  Workflows Clearly` 继续 `VALID`。
- 中文技术混排、日文/韩文/阿拉伯文及模型缺失 fail-closed 矩阵保持通过。

### Artifact boundary evidence

- 新增真实 Fake Ollama `Amazon Connect Salesforce` primary → language validation →
  唯一一次 repair → validation 回归；repair 仍失败返回 `INVALID_RESPONSE`。
- Repository-backed 回归确认该 identifier-only response 不会得到
  `ProviderCall SUCCEEDED` 或 cache hit；无 `SCORING_RAW`、
  `SCORING_STRUCTURED`、成功 `response_artifact_id` 或 Artifact 文件。
- repair 成功只保存修复后的可信 response；P1-2 ScoreResult trusted validation 与
  P1-3 六项 cache provenance 逻辑未修改。

### Dependency compliance

- `docs/THIRD_PARTY_NOTICES.md` 已逐项列出 TASK-016B 新增 23 个包的固定版本、许可证、
  版权归属、上游来源和分发状态；覆盖 spaCy 本体及 21 个 transitive dependencies。
- 明确记录 `en_core_web_sm` MIT/Explosion 版权、OntoNotes 5 commercial source
  licensed by Explosion、ClearNLP citation-only 来源，以及 WordNet Release 3.0 的
  Princeton copyright、notice/disclaimer 保留和禁止宣传使用名称义务；WordNet
  要求随副本保留的完整 notice 已逐字收入 NOTICE 文档。
- 合规结论：固定 Local-only 安装/运行/离线构建证据闭合；公开 bundle 仍为 NO-GO，
  直至模型来源再分发、许可证文本装载及 release-owner sign-off 完成。SBOM 已同步，
  不把本轮合规补证误写成公开发行批准。

### TDD 与门禁

- 有效 RED：`4 failed, 134 passed`，分别证明 Amazon Domain 绕过、Kubernetes 大小写
  不一致、Ollama 未进入 repair，以及 Repository 错误持久化正式评分 Artifact。
- 聚焦 Domain/Ollama：`139 passed`；Weekly 安全/渲染回归单独 `41 passed`。
- 首次 full pytest 在 `792 passed` 后暴露一个旧测试夹具兼容问题：系词句
  `This video is directly useful.` 的核心被 parser 标为 `ADJ`，不再满足冻结的
  real-`VERB` 契约。仅将测试夹具改为等义的
  `This video provides directly useful guidance.`；Weekly production 未修改，
  对应 41 项回归随后通过。
- `uv lock --check` → `uv sync --locked --offline` → `uv lock --check`：PASS
  （107 resolved / 84 checked，无下载或锁漂移）。
- Full pytest：`823 passed`；`uv run mypy src`：PASS（27 source files）；
  `uv run ruff check .`：PASS；CLI help：PASS；`uv build --offline`：sdist/wheel
  PASS；wheel metadata 精确保留 `spacy==3.8.15` 与固定 3.8.0 模型 URL。
- 新增 23 包 NOTICE 清单与已安装版本逐项一致；WordNet 完整 notice 存在；
  `bash scripts/security_scan.sh`：`status=clean`（仅既有非阻断 WARN）；
  `git diff --check`：PASS。
- 未修改 TASK-016C、Cloud、Router、Weekly production、DB Schema/Migration；未运行
  网络、真实 Provider、merge、push、tag 或 release。

### Round 12 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 12 Correction Report。

## Round 13 Correction（2026-08-13）

### Root cause 与 parser/entity correction

- Round 12 把 `det`/`amod` 当作普通名词论元的自然结构证据，但品牌实体内部同样可包含
  `The`、`New`、`Home` 等依存修饰。固定 spaCy 模型因此把
  `Amazon Connect The Home Depot` 解析为 `nsubj + VERB ROOT + dobj`，并让整个品牌
  字符串穿透可信 `ScoreResult`。
- Round 13 继续使用已固定、离线的 `en_core_web_sm==3.8.0`，但不再排除其 NER pipeline。
  Predicate 本身处于命名实体 span 时立即 fail-closed；subject/object/complement 若
  全部属于命名实体内部，或只由 `det/amod/compound/flat` 组成，也不能建立 predicate
  independence。
- lowercase/all-caps 下 NER 可能不稳定，因此另以同一 dependency tree 的
  `det + compound/flat` 封闭名词结构兜底；判断不读取品牌名、公司名、token 大小写、
  token 位置、固定 token 数量或后缀。
- 正常句子只要至少一个核心论元包含独立自然语言结构即可通过。例如普通名词
  `containers/developers/data/models/system/deployment` 继续提供可信论元；实体
  `Docker/OpenAI/Redis` 本身不提供、也不阻止语言证据。

### Adversarial 与 spaCy validation evidence

- `Amazon Connect The Home Depot`、`The North Face` 等八个品牌/大小写变体全部
  `UNCERTAIN`；固定模型在 TitleCase 样例中返回单个或两个 `ORG` span，在 lowercase
  NER 为空、all-caps 仅部分命中时，dependency entity structure 仍保持相同结果。
- `Docker Kubernetes Terraform Ansible`、`Redis Kafka PostgreSQL MongoDB`、
  `OpenAI PyTorch TensorFlow Kubernetes` 继续 `UNCERTAIN`。
- `Docker containers help developers deploy applications`、`Redis stores data
  and improves application performance`、`OpenAI develops useful AI models`、
  `The system relies on Docker for deployment.` 继续 `VALID`。
- TDD RED：`9 failed, 140 passed`，分别证明六个 Domain/ScoreResult 绕过、Ollama 未
  repair、Repository 错误持久化 primary，以及成功 repair 仍保存品牌 primary。
- 首个 GREEN 收紧把所有 `det + compound` 一律视作 entity，导致 10 个合法自然语言/
  repair fixture 回归；随后把门禁限定为 NER entity-internal 或封闭
  `det + compound/flat` 结构，最终聚焦 Domain/Ollama `149 passed`。

### Artifact boundary evidence

- Fake Ollama 对 `Amazon Connect The Home Depot` 执行 primary validation → 唯一一次
  repair → repair validation；repair 仍失败时返回 `INVALID_RESPONSE`。
- Repository-backed 失败回归确认 ProviderCall 为 `FAILED_RETRYABLE` 且
  `response_artifact_id` 为空；不存在 `SCORING_RAW`、`SCORING_STRUCTURED`、Artifact
  文件、成功 ProviderCall 或 persisted cache hit。
- repair 成功回归把同一品牌攻击作为 primary，并从 SQLite Artifact 实际读取 raw
  response，确认只保存通过验证的 repair reason。P1-2 ScoreResult trusted validation
  与 P1-3 六项 cache provenance 均未修改。

### Dependency status 与 full gates

- 未新增或升级依赖；`pyproject.toml`、`uv.lock`、SBOM 和 NOTICE 均无 Round 13 Diff。
  既有 23 项 spaCy 新增包清单仍完整，锁文件 SHA-256 仍为
  `782947100813f925f08e238e45ace62a9247a8a89b60cc706d8419969709d82f`；公开分发仍
  `NO-GO`，Local-only 边界不变。
- `uv lock --check` → `uv sync --locked --offline` → `uv lock --check`：PASS
  （107 resolved / 84 checked，无下载或锁漂移）。
- Full pytest：`833 passed`；`uv run mypy src`：PASS（27 source files）；
  `uv run ruff check .`、CLI help、`uv build --offline` sdist/wheel、
  `git diff --check`：全部 PASS。
- `bash scripts/security_scan.sh`：`status=clean`；仅既有非阻断 WARN 与项目自身 LICENSE
  未决提示。
- 未修改 TASK-016C、Cloud、Router、Weekly production、DB Schema/Migration；未运行
  网络、真实 Provider、merge、push、tag 或 release。

### Round 13 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 13 Correction Report。

## Final Correction Round 3（2026-08-13）

### Root cause

- P1-1：Round 2 仍把整段文本压平成英文词计数；中文主体后追加若干英文词即可达到
  阈值，无法表达用户真正看到的首个自然语言主体。
- P1-3：SQLite 中成功的 `ProviderCall` 与 Artifact key 都是不可原位覆盖的审计
  记录。旧实现把 prompt/schema provenance mismatch 当作持久化错误，没有把它解释
  为可重算的 cache miss。

### Fixes 与对抗证据

- 语言校验先按换行及中英文句末符切分，再剥离固定技术词；逐段寻找首个可辨识自然
  语言主体。英文主体由谓词/关系结构识别，不再使用固定英文词数或字符比例；单汉字、
  技术缩写及无谓词英文尾巴都不能改变主体语言。
- Domain 与真实 Ollama Fake transport 的 primary/一次 repair/fail-closed 路径覆盖：
  `en` 中文主体加英文短尾、`zh-CN` 英文主体加中文短尾均拒绝；中文主体混排
  API/SDK/LLM/MLX 与英文主体混排 API/SDK/LLM 均通过。
- prompt/schema 版本失配现在建立确定性的 `scoring-cache-recompute-v1` 请求身份，
  调用 Provider 重新计算并写入新的 ProviderCall 与 raw/structured Artifact；旧
  ProviderCall、Artifact 记录和文件均保留。第三次相同恢复命中新可信缓存，不会反复
  调用 Provider。
- SQLite 对抗测试分别覆盖 Result Artifact 与 ProviderCall 的 wrong
  `prompt_version` / `schema_version`：Provider 调用由 1 增至 2、ProviderCall 表由
  1 增至 2、新 Artifact ID/路径生成，旧审计证据不变；request/provider/model/
  output_language 的非版本篡改仍保持 fail-closed，未削弱原有边界。

### Final gates

- TDD RED：`7 failed, 15 passed`，分别证明语言绕过仍被接受、版本失配仍直接失败。
- Focused scoring/domain/Ollama/repository：`71 passed`。
- `uv lock --check`、`uv sync --locked --offline`：PASS（84 resolved / 61 checked，
  无下载，锁文件未变）。
- Full pytest：`734 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge 或 push。

### Round 3 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 Final Correction Round 3 Report。

## Final Correction Round 4（2026-08-13）

### Root cause 与 algorithm change

- Round 3 仍以英文谓词词表及 `-ed/-ing/-s` 后缀识别英文主体，因此无谓词的英文
  自然语言段会被当作无证据，后接中文短段后可能被误判为中文。
- Round 4 删除谓词词表和后缀启发式。Reason 先按句末符/换行分段，每段剥离固定
  技术词，再输出 `zh_confidence`、`en_confidence` 或 `unknown_confidence`。
- 中文证据来自相邻汉字信息单元；英文证据来自相邻元音核信息单元。两者都是连续的
  自然语言信息量，不是固定词数、固定字符比例或“首个已识别语言”。技术词、单字符
  标记及零自然语言信息的 markup 段不形成主体证据。
- 所有段的有效信息量聚合后决定主体；混合脚本无法建立可靠 framing、unknown 非零、
  两种证据并列或无证据时均 fail-closed。

### Adversarial 与 Ollama repair evidence

- Domain 覆盖并通过：`en` 中文主体+英文短尾拒绝；`zh-CN` 英文主体+中文短尾拒绝；
  中文主体+API/SDK/LLM/MLX 通过；英文主体+API/SDK/LLM 通过；纯技术词不形成主体。
- 真实 Ollama Fake transport 覆盖 primary language validation → 唯一一次 repair →
  repair validation；Round 4 英文无谓词主体+中文短尾会进入 repair，repair 后仍错则
  `INVALID_RESPONSE` fail-closed。
- TDD RED：`3 failed, 17 passed`，分别证明 Domain、repair 路径和 repair 后
  fail-closed 的同一绕过。
- 额外安全渲染兼容回归：合法英文 reason 后的 HTML/Markdown payload 不会成为语言
  证据，Weekly 既有中和测试保持通过；未修改 Weekly 生产代码。

### Gates

- Focused Domain/Ollama/Weekly：`94 passed`。
- Full pytest、mypy、Ruff、offline build 与最终 Diff 结果见 Round 4 Final Report。
- 未运行网络、真实 Ollama、Cloud、Vault、TASK-016C、merge 或 push。

### Round 4 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 Final Correction Round 4 Report。

## Final Correction Round 5（2026-08-13）

### Root cause 与 algorithm change

- P1-1：Round 4 仍以字符数量、元音核与首尾脚本 framing 推断主体；两个同脚本标记
  可以把另一语种主体包在中间，且英文无谓词自然短语的判定依赖数量启发式。
- Round 5 删除字符数量比较、字符比例、元音核、减一阈值及对称首尾继承。Reason
  仍先按句末符/换行分段并剥离固定技术词，但主体证据改为结构性连续证据：中文需要
  连续且非单一重复标记的汉字段，英文需要相邻非技术词形成的连续短语。判断只回答
  “是否存在主体”，不比较哪一方字符或词更多。
- 双语主体默认 `unknown` 并 fail-closed。唯一保留的保守兼容是：完整英文语境两侧
  包围的中文专名不会取代已成立的英文主体；中文输出不会通过首尾汉字 framing 吸收
  英文主体。

### Adversarial 与 Ollama repair evidence

- Domain 覆盖首尾单汉字包裹、首尾多汉字包裹、单字符 `中`/`a`、中文主体加英文
  尾段、英文主体加中文尾段、纯技术词及英文无谓词自然短语；全部按冻结契约通过或
  拒绝。
- 合法样例覆盖 `该视频介绍 API、SDK、LLM、MLX 技术流程。`、`This video
  explains API, SDK and LLM workflow.`、中文技术词混排及英文中的中文专名。
- 真实 Fake Ollama transport 覆盖 primary language validation → 唯一一次 repair
  → repair validation → fail-closed；首尾单/多字符攻击均不会绕过 primary 或 repair。

### Artifact persistence

- Provider 以私有 `_InvalidLanguageResponse` 区分错语种与其他可恢复格式错误。错语种
  primary 在 repair 最终失败时不会通过 `consume_raw_response()` 暴露给 Repository，
  因而不会生成正式 `SCORING_RAW` / `SCORING_STRUCTURED` Artifact，也不会形成成功
  `response_artifact_id` provenance；ProviderCall 保持 `FAILED_RETRYABLE`。
- repair 成功时只持久化已经通过 schema 与语言 invariant 的 repair envelope；测试
  从 SQLite Artifact 读取并解析内容，确认正式 raw 中不存在错语种 primary reason。
- 非语言格式错误的既有 recovery-primary 行为保持不变，未扩大到 TASK-016C、Cloud、
  Router、Weekly production 或 DB Schema。

### TDD 与 final gates

- RED：语言对抗初始 `6 failed, 22 passed`；Repository-backed 双次错语种初始生成
  `scoring_raw`，直接复现两类 P1。
- Focused Domain/Ollama/scoring：`93 passed`。
- `uv lock --check`、`uv sync --locked --offline`：PASS（84 resolved / 61 checked，
  无下载，锁文件未变）。
- Full pytest：`752 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge 或 push。

### Round 5 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Final Correction Round 5 Report。

## Round 9 Correction（2026-08-13）

### 修复原因与设计边界

- Round 8 把单个 Han `中` 和单个 Latin `a` 当作足够语言证据，因此二者可与纯技术
  identifier 组合后错误生成 `VALID`。Round 8 同时把所有 TitleCase token 视为
  identifier，误杀正常英文标题。
- Round 9 保持三态 Violation Detector，不恢复字符比例、位置、首尾关系、谓词词表或
  固定 token 数量。单个 Han/Latin 字符现在提供零语言证据；全大写、CamelCase、
  已登记 identifier 及其复数仍提供零证据；普通 TitleCase token 不再被整体排除。
- `Kubernetes` 与普通 TitleCase token 在无词典/模型条件下不存在可泛化的结构差异，
  因此仅将任务明确冻结的该 identifier 加入既有技术集合；没有增加自然语言词表。

### 对抗、Repair 与 Artifact 证据

- `中 REST CUDA NLP CNN` 与 `a API SDK LLM GPT MLX` 均返回 `UNCERTAIN`，不能生成
  `ScoreResult`；纯技术 identifier 组同样保持 `UNCERTAIN`。
- `This Video Explains Machine Learning Workflows Clearly`、`OpenAI Develops
  Useful AI Models` 均为合法英文；`该视频介绍 GPT API 调用流程` 为合法中文。
- Fake Ollama 两条攻击均覆盖 primary validation → 一次 repair → 再验证；repair
  仍失败时返回 `INVALID_RESPONSE`。
- Repository-backed 双次失败回归确认：无正式 `SCORING_RAW` / `SCORING_STRUCTURED`
  Artifact、无成功 `response_artifact_id`，ProviderCall 为 `FAILED_RETRYABLE`。
- P1-2 ScoreResult contract、P1-3 cache provenance 与已有 Artifact fail-closed 生产
  流程均未修改。

### TDD 与 Full gates

- 有效 RED：`8 failed, 59 passed`，精确覆盖两个攻击的 Domain/Ollama 路径与两个
  TitleCase 合法英文误杀；最初一次测试补丁插入错误产生 SyntaxError，修正测试结构
  后未计入产品 RED。
- Focused Domain/Ollama/scoring：`130 passed`。
- `uv lock --check`、`uv sync --locked --offline`：PASS（84 resolved / 61 checked，
  无下载，锁文件未变）。
- Full pytest：`789 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未修改 TASK-016C、Cloud、Router、Weekly production 或 DB Schema；未运行网络、
  真实 Provider、merge 或 push。

### Round 9 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 9 Correction Report。

## Round 10 Correction（2026-08-13）

### Root cause 与 algorithm change

- Round 9 仍把任意未命中有限技术词集合的 Latin token 当作英文证据，因此此前未登记
  的产品/框架实体（例如 Docker、Redis、Terraform）可以跳过 repair 并进入可信
  `ScoreResult`、Artifact 与 Cache。
- Round 10 删除有限产品/技术词集作为语言证明来源。通用 identifier shape（单字符、
  全大写、CamelCase）只会降低证据，不会增加英文可信度；实现不包含 Docker、Redis、
  Kafka、Terraform、PostgreSQL 等产品白名单。
- 英文证据改为同一 Latin 片段内的自然语言连接，或标题式文本中的内部关系形态；
  单独的公司名、产品名、模型名、框架名序列只有弱证据，固定返回 `UNCERTAIN`。
  Unicode script、`zh-CN`/`en` 双语言门禁及三态 fail-closed 契约保持不变。

### Adversarial、Ollama repair 与 Artifact evidence

- Domain 对抗覆盖 `Docker Kubernetes Terraform Ansible`、`Redis Kafka PostgreSQL
  MongoDB`、`OpenAI PyTorch TensorFlow Kubernetes`、`REST CUDA NLP CNN` 与复数
  acronym 序列；均为 `UNCERTAIN`，不能构造可信 `ScoreResult`。
- 合法英文覆盖 TitleCase、实体加自然语言关系：`This Video Explains Machine
  Learning Workflows Clearly`、`Docker containers help developers deploy
  applications`、`Redis stores data and improves application performance`、
  `OpenAI develops useful AI models`；中文技术混排继续通过。
- Fake Ollama 证明纯实体 primary 必须进入唯一一次 language-bound repair；repair
  再失败返回 `INVALID_RESPONSE`。Repository-backed 回归确认失败路径无
  `SCORING_RAW`、无 `SCORING_STRUCTURED`、无成功 `response_artifact_id`；repair
  成功时正式 raw 只保存通过语言 invariant 的修复响应。
- P1-2 `ScoreResult` trusted validation、P1-3 cache provenance 与既有 cache
  recompute 行为未修改。

### TDD 与 Full gates

- 有效 RED：`8 failed, 37 passed`，同时复现 Domain 误判、Ollama 未 repair、失败
  response 生成正式 Artifact 以及成功路径错误保存 primary。
- Focused Domain/Ollama：`115 passed`。
- `uv lock --check` → `uv sync --locked --offline` → `uv lock --check`：PASS
  （84 resolved / 61 checked，无下载，锁文件未变）。
- Full pytest：`799 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未修改 TASK-016C、Cloud、Router、Weekly production 或 DB Schema；未运行真实
  Provider、网络、merge、push 或 tag。

### Round 10 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 10 Correction Report。

## Round 14 Correction（2026-08-13）

### Root cause 与 algorithm change

- Round 13 将介词宾语上的 `det` 误当作独立自然语言证据，因此 spaCy 对
  `Amazon Connect Jack in the Box` 生成的 subject / VERB / object / prep tree
  可以绕过 entity-only 边界。
- Round 14 将直接 predicate arguments 与 prepositional arguments 分开。只有直接
  核心论元中存在非 entity natural-language span，或介词补语提供非 entity-internal
  结构时，parse 才能成为可信英文证据；`det`、`compound`、`flat`、`amod`、`prep`、
  `pobj`、`appos` 组成的实体内部延伸不能单独证明语言。
- 英文解析改为对单一 `casefold()` 规范表示执行一次 parser。没有 lower/title/upper
  多版本投票、宽松结果选择、品牌/产品名单、token 数量/位置或词尾规则；同一自然
  英文的原始、lowercase、uppercase 形式因此进入相同的确定性 parse 边界。

### Adversarial、Repair 与 Artifact evidence

- `Amazon Connect Jack in the Box`、`Amazon Connect The Home Depot`、
  `Amazon Connect The North Face`、`The Home Depot`、`Amazon Connect Salesforce`
  及既有纯 identifier 矩阵全部为 `UNCERTAIN`。
- 四条合法自然英文（Docker containers、Redis stores、OpenAI develops、The system
  relies）各自的原始/lowercase/uppercase 形式均为 `VALID`。
- Fake Ollama 证明 Jack entity-only primary 必须进入唯一一次 repair；repair 再失败
  返回 `INVALID_RESPONSE`。Repository-backed 回归确认失败路径无 `ScoreResult`、
  `SCORING_RAW`、`SCORING_STRUCTURED`、成功 `response_artifact_id` 或可恢复 cache；
  repair 成功时 raw Artifact 只保存合法 repair response。
- P1-2 `ScoreResult` contract、P1-3 cache provenance、TASK-016C、Cloud、Router、
  Weekly production 与 DB Schema 均未修改。

### TDD 与 Full gates

- RED：`6 failed, 152 passed`，精确复现 Jack entity-only Domain/Ollama/Artifact 绕过、
  成功 repair 错存 primary，以及 uppercase Redis/OpenAI 回归。
- Focused Domain/Ollama：`158 passed`。
- `uv lock --check`：PASS（107 packages）。
- `uv sync --locked --offline`：PASS（107 resolved / 84 checked，无下载，锁文件未变）。
- Full pytest：`842 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge、push 或 tag。

### Round 14 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 14 Correction Report。

## Round 15 Correction（2026-08-13）

### Root cause 与 entity evidence boundary

- Round 14 仍把任意 `amod` 当作 nominal natural-language evidence；因此固定本地
  parser 将 `General Electric` 解析为 `general/ADJ/amod -> electric/NOUN/dobj`
  时，纯 entity-only phrase 可以进入 `VALID`。
- Round 15 不再让单独 `amod+noun` 或嵌套在 `compound` 下的 adjective 提供自然
  语言证明。只有同一直接论元同时包含 adjective 与 compound、且论元及其直接子节点
  均无 NER entity 标记时，该结构才能作为 nominal natural evidence；含 NER 的
  `amod/compound` 子树保持 entity-like。
- 并列实体列表作为 subject、后接完整 verbal predicate 的既有合法句，通过通用
  `cc + nominal conj + verbal conj` 依存结构识别；未加入品牌、公司、产品、技术
  白名单，也未增加大小写、token 数量/长度/位置或词尾规则。
- 保持单次 `casefold()` parser、三态保守验证与 parser 不确定即 `UNCERTAIN`。
  `Redis stores data` 在固定 parser 下没有 `VERB`，因此有明确回归固定为
  `UNCERTAIN`；完整的 `Redis stores data and improves application performance`
  及其原始/lowercase/uppercase 形式全部为 `VALID`。

### Adversarial、Repair、Artifact 与 Cache evidence

- 新增八个结构型 entity-only 攻击：General Electric、National Geographic、Meta
  Platforms、Advanced Micro Devices、Red Bull、Whole Foods Market、General
  Motors、Federal Express；连同 Jack in the Box、The Home Depot、Salesforce 与
  既有 identifier 矩阵，全部为 `UNCERTAIN`。
- Docker containers、Redis 完整句、OpenAI develops、The system relies 四类合法
  英文及规定大小写变体保持 `VALID`。
- Fake Ollama 证明 General Electric primary 必须进入唯一一次 repair；repair 再
  失败返回 `INVALID_RESPONSE`。Repository-backed 回归确认无 `ScoreResult`、
  `SCORING_RAW`、`SCORING_STRUCTURED`、成功 `response_artifact_id` 或可恢复成功
  cache；repair 成功时正式 raw Artifact 只包含合法 repair response。
- P1-2 `ScoreResult` contract、P1-3 cache provenance、TASK-016C、Cloud、Router、
  Weekly production、DB Schema 与 migration 均未修改。

### TDD 与 Full gates

- RED：`11 failed, 158 passed`，覆盖八个 Domain entity-only 绕过、Ollama 未 repair、
  失败响应正式持久化及成功 repair 错存 primary。
- Focused Domain/Ollama：`169 passed`。
- `uv lock --check`：PASS（107 packages）。
- `uv sync --locked --offline`：PASS（107 resolved / 84 checked，无下载，锁文件未变）。
- Full pytest：`853 passed`。
- `uv run mypy src`：PASS（27 source files）。
- `uv run ruff check .`：PASS。
- `uv build --offline`：PASS（sdist/wheel）。
- `git diff --check`：PASS。
- 未运行网络、真实 Provider、Cloud、Vault、TASK-016C、merge、push 或 tag。

### Round 15 结论

- 建议：重新进入 Independent Review。
- Commit SHA：见 TASK-016B Round 15 Correction Report。

## Round 16 Scope Decision（2026-08-13）

### 不可判定性证据

- 固定单次 `casefold()` spaCy parse 中，`General Dynamics Corporation` 与
  `useful AI models` 的 object 均为 `NOUN/dobj`，直接子节点均为
  `ADJ/amod + NOUN/compound`，且 NER 均无可用实体标记。
- 在禁止品牌/实体词典、外部知识、语义模型和 token/dependency 隐性启发式的约束下，
  无法可靠地把前者固定为 entity-only，同时把后者固定为自然语言。

### 决定与边界

- 已接受 [ADR-024](../docs/decisions/ADR-024-scoring-language-validator-scope.md)。
- Language Validator 只负责 script mismatch、自然语言结构验证与不确定时 fail-closed；
  不负责品牌/公司/产品识别、实体真实性或 entity stuffing 检测。
- 保持正常英文样例有效；entity-only 内容质量风险移交未来独立 Content Quality 任务，
  本轮不创建或启动该任务。
- 产品基线保持 `08fbae17086c74757b5cf98bf8ad76613872a32c`；未增加 entity/brand
  规则、dependency 例外、token 启发式或产品代码修改。

### 本轮验证

- 仅修改 ADR-024、ADR 索引与本 handoff。
- 未运行产品测试、类型检查、Lint 或 build：本轮没有代码、配置、依赖或测试变更。
- `git diff --check`：PASS。
- 未运行网络、模型、Cloud、Vault、TASK-016C、merge、push、tag 或 release。

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
