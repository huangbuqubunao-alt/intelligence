# TASK-008A 交接报告

## 元数据

- Task: `TASK-008A`
- Role: `Implementer`
- Agent/session: `Codex /root`
- Base branch/commit: `main@82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-008a`
- Branch: `codex/task-008a-cloud-analysis-shared-contracts`
- Head commit: 本报告与实现位于同一个新提交；精确 SHA 由提交后的完成报告记录。
- Started: `2026-07-20`
- Reported: `2026-07-20`

## 目标与范围

- 任务目标：在不实现 Provider、Prompt、采样、token 计数、凭据解析、预算或事务编排的
  前提下，冻结 TASK-008/TASK-009 共用的最小化云分析输入、结构化完成/跳过结果、
  配置、隐私/版本和依赖基线。
- 允许修改：`src/youtube_intel/domain.py`、`src/youtube_intel/config.py`、
  `config/settings.example.yaml`、`tests/unit/test_contracts.py`、`pyproject.toml`、
  `uv.lock` 和本报告。
- 实际修改：仅上述 7 个路径；新增或收紧共享 Pydantic 契约、云配置和正反契约测试，
  并锁定获批的 OpenAI SDK/tiktoken 直接依赖及必要传递依赖。
- 明确未做：未新增 Provider/业务模块、Prompt、Schema/migration、Repository/state、
  CredentialResolver、CloudCallBudget、采样/请求构造、缓存、事务或 CLI 行为；未读取
  环境变量值、实例化 OpenAI client、调用 API、写入 Vault 或访问用户内容。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 完成/跳过 union、最小 payload、证据约束和未验证 update | PASS | `AnalysisCompleted`/`AnalysisSkipped`/`AnalysisOutcome`、五个固定跳过原因、四个固定证据来源、V1 空时间字段、每点非空且有效 evidence 引用、字段种类规则和全套 `model_copy(update=...)` 拒绝探针；无 update 的 frozen copy 保持合法。 |
| 云配置默认关闭及所有固定边界 | PASS | `CloudSettings` 固定 openai、显式 model/tokenizer 映射、5 次、28k/30k、描述/输出边界、四个版本和既有 120 秒 timeout；未知 model/tokenizer/字段及跨预算错误均失败关闭。 |
| `AnalysisPayload` 精确出站白名单 | PASS | JSON 序列化键精确等于 10 个 A-04 字段；`extra="forbid"` 排除路径、内部 ID/哈希、评分、密钥名和自由 metadata；描述对象上限为 4,000 code points。 |
| 依赖、离线导入、许可证和既有依赖稳定 | PASS | 直接范围精确为 `openai>=2.46.0,<2.47` 与 `tiktoken>=0.13.0,<0.14`；锁定/离线导入为 2.46.0/0.13.0；Python 3.12.11、arm64；既有直接依赖未升级。 |
| 无 Provider/Schema/Repository/Prompt/编排行为 | PASS | 完整 Diff 仅 7 个获准路径；源码静态测试证明 `domain.py`/`config.py` 不导入 OpenAI 或 tiktoken，配置不导入 `os`；无禁止路径变化。 |

## ADR-008 A-01 至 A-15 追溯

| 决策 | 本切片证据或明确边界 |
|---|---|
| A-01 共享契约先行 | 本提交只冻结具名契约、配置和依赖，不实现云 Provider 或业务编排。 |
| A-02 完成/跳过显式 union | `AnalysisCompleted`、`AnalysisSkipped`、`AnalysisOutcome` 和五个固定跳过原因均有正反测试。 |
| A-03 资格与副作用顺序 | 本切片不实现副作用；有限 `AnalysisInput` 和结构化跳过面供 TASK-008/TASK-010 按固定顺序消费。 |
| A-04 专用最小出站对象 | `AnalysisPayload` 只有 video/title/channel/time/duration/language/description/sample 共 10 个具名字段；`AnalysisInput` 将 payload 与本地哈希/版本隔离。 |
| A-05 本地保守 token 预算 | 配置冻结 `o200k_base` 显式模型映射、28,000 本地上限、30,000 Provider 上限和 `cloud-token-sampling-v1`；采样/计数实现留给 TASK-008。 |
| A-06 完整请求身份 | `AnalysisInput` 冻结 transcript/request hash 与 Prompt/Schema/采样/隐私版本；实际哈希构造和缓存匹配留给 TASK-008。 |
| A-07 按真实出站请求计预算 | 配置上限固定为 5；未实现或伪造预算计数，`CloudCallBudget` 留给 TASK-010。 |
| A-08 注入且延迟读取密钥 | 配置只存经验证的 env 名；不读取进程环境，repr/异常脱敏测试覆盖 secret 哨兵。 |
| A-09 固定 OpenAI 传输边界 | 仅加入官方 SDK 依赖；未实例化 client、未实现 Responses API、重试、temperature 或网络行为。 |
| A-10 严格 Structured Outputs | provider-neutral `AnalysisContent` 不能生成 provider/model/prompt/request/call metadata；本地 `AnalysisResult` 才增加可信审计字段。Adapter 和 JSON Schema 留给 TASK-008。 |
| A-11 最小输入可验证证据 | 来源精确映射到 title/channel_name/description/transcript_sample，时间字段只能为 `None`，所有 point 必须引用存在的 evidence，种类规则固定；运行时精确子串核验留给 TASK-008 Adapter。 |
| A-12 复用现有事务 | 未改 Artifact、Provider call、`complete_stage`、Schema、migration 或 `state.py`；持久化编排留给 TASK-008/TASK-010。 |
| A-13 依赖与并行隔离 | 本任务独占修改清单/锁文件，锁定 OpenAI 2.46.0、tiktoken 0.13.0 和必要传递依赖；未触及 TASK-009A/Jinja2。 |
| A-14 离线隐私/预算验收 | 本切片覆盖白名单、secret 脱敏、支持/未知 tokenizer、28k/30k 及配置边界；Provider/Fake/SQLite 场景属于后续实现验收。 |
| A-15 真实云路径单独授权 | 未读取密钥、未发送字幕、未调用 OpenAI/YouTube/Vault/媒体/模型；仅使用已批准包索引下载，锁定后验证均无 API 行为。 |

## 版本、复用与许可证

- 固定版本：`analysis-prompt-v1`、`analysis-result-v1`、
  `cloud-token-sampling-v1`、`cloud-privacy-v1`。
- `DIRECT`：既有 Pydantic 2.13.4 不可变/严格模型和 Python 标准库
  `datetime`、`enum`、类型能力；官方 OpenAI SDK 2.46.0（Apache-2.0）与
  tiktoken 0.13.0（MIT）。
- 必要新增传递依赖：distro 1.9.0（Apache-2.0）、jiter 0.16.0（MIT）和
  sniffio 1.3.1（MIT OR Apache-2.0）；其余 OpenAI 依赖已在既有锁图中。
- 既有直接解析版本保持不变：mlx-whisper 0.4.3、Pydantic 2.13.4、
  PyYAML 6.0.3、yt-dlp 2026.7.4；tiktoken 0.13.0 从既有传递依赖提升为显式直接依赖。
- `REJECT/DEFER`：手写 OpenAI HTTP、Chat Completions、第二 Provider、云端 token
  计数、SDK 自动重试、真实 client/API/密钥、Prompt/Schema 运行实现。

## TDD 证据

- RED：新增契约测试依次证明缺少 `AnalysisPayload`/outcome、旧 `AnalysisInput` 形状、
  可写时间戳、未固定 enum、未知 tokenizer、跨预算、YAML 缺字段和缺少直接依赖时失败。
- GREEN：每个最小契约/配置/依赖变化后对应测试通过；最终专项 `66 passed`、全套
  `318 passed`。
- REFACTOR：仅修复 Ruff 导入顺序并复跑专项测试；未删除、跳过、弱化测试或修改门禁。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages`。 |
| `uv sync --locked` | PASS | `Resolved 84 packages`，`Checked 61 packages`。 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | Python 3.12.11；`66 passed`。 |
| `uv run python -m pytest` | PASS | `318 passed`。 |
| `uv run mypy src` | PASS | `Success: no issues found in 13 source files`。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | sdist 与 wheel 均构建成功。 |
| sdist/wheel 内容检查 | PASS | 两个产物均包含 `youtube_intel/migrations/001_initial.sql`；核验后仅清理本轮生成的忽略 `dist/`。 |
| Python/平台/许可证元数据 | PASS | Python 3.12.11、`arm64`；直接和新增必要传递依赖的许可证元数据均已核验。 |
| `git diff --check` | PASS | 提交前工作 Diff 无空白错误；提交后精确 base range 由完成报告记录。 |

## Diff 复核

- 修改文件：仅任务批准的 7 个路径。
- 是否存在任务范围外修改：否；禁止的 Provider、Prompt、Schema/migration、state、
  Repository、CLI、任务卡、ADR 和 TASK-009A 路径均未修改。
- 是否存在生成文件或格式化噪声：否；`dist/` 只为离线验包生成，已核验并清理。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：只按明确审批修改
  `pyproject.toml`/`uv.lock` 和下载包；未触及其他红线。敏感模式审查只命中既有测试
  脱敏哨兵，未发现凭据、token、私钥或真实绝对路径。

## 失败、跳过与风险

- 已解决失败：沙箱最初拒绝读取用户级 uv 缓存；按门禁授权原命令后锁定、同步、元数据
  和离线构建均成功。依赖许可证测试最初读取了并非两个包都提供的
  `License-Expression` 字段，随后按实际安装元数据改为验证 OpenAI `License` 和
  tiktoken MIT 文本；Ruff 仅报告测试 import 排序，自动排序后所有检查通过。
- 跳过检查及原因：未运行任何真实 OpenAI/API/token-count/网络推理、CredentialResolver、
  环境变量值读取、Provider、Prompt、SQLite/Vault/YouTube/字幕/媒体/模型路径；均为范围外
  或未授权。除已批准依赖下载外无外部网络行为。
- 剩余风险：模型到 tokenizer 的显式表当前只冻结 V1 支持的 GPT-4.1 系列；新增模型必须
  经配置契约变更。精确 evidence 子串验证、请求哈希覆盖、采样/token 计数、SDK 参数、
  错误映射、缓存及持久化原子性仍必须由 TASK-008/TASK-010 的 Fake/临时 SQLite 测试证明。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：见包含本报告的唯一实现提交；精确 SHA 由完成报告记录。
- 复现/验证说明：在本 worktree 从固定 base 执行上表命令；所有测试只验证纯配置、
  领域契约、离线 import 和现有本地代码，未创建 OpenAI client。

## Reviewer 结论

- Reviewer agent/session：`Independent Codex Reviewer /root`
- 审查 commit：`382251298af7fcbfadba66c1902af6de0a425179`
- 重新运行的检查：
  - `uv lock --check`：PASS，`Resolved 84 packages`。
  - `uv sync --locked --offline`：首次因沙箱无权读取
    `/Users/hua/.cache/uv` 失败；按既有任务级包缓存授权原样重跑后 PASS，
    `Resolved 84 packages`、`Checked 61 packages`，未访问 API。
  - `uv run python -m pytest tests/unit/test_contracts.py`：PASS，`66 passed`。
  - `uv run python -m pytest`：PASS，`318 passed`。
  - `uv run mypy src`：PASS，13 个 source files 无问题。
  - `uv run ruff check .`：PASS。
  - `uv run python -m youtube_intel --help`：PASS。
  - `uv build --offline`：首次同样仅因 uv 缓存沙箱权限失败；授权原样重跑
    PASS。sdist/wheel 均包含 `youtube_intel/migrations/001_initial.sql`；
    核验后只清理本轮忽略的 `dist/`。
  - `git diff --check <base>...<reviewed-head>`：PASS；实际固定 SHA 为
    `82d1fd7c7f2f82e77df0518e63755bad0bf240f2...382251298af7fcbfadba66c1902af6de0a425179`。
- 独立探针：
  - Probe A（最小出站/公共面）：10 个 payload 字段、4,000 code points 描述
    上限、extra forbid、provider-neutral `AnalysisContent`、公共 exports 和八个
    JSON Schema 的封闭性均 PASS；未发现自由 `dict`、`Any`、宽 `object` 或 SDK
    类型。
  - Probe B（Pydantic/hash）：八个新增分析对象对空/非法/未知/嵌套/类型混淆
    `model_copy(update=...)` 全部拒绝；无 update shallow/deep copy 合法。但三个
    审计哈希字段及多项空白语义值 FAIL，见 P1-1/P1-2。
  - Probe C（证据/grounding）：四个来源与 payload 一一映射、时间只能为
    `None`、字段 kind、引用存在性、去重和基数均 PASS。跨来源错误 excerpt 当前
    可构造是 TASK-008 精确子串运行时 validator 的明确后续职责，本身不形成
    finding；但空白 evidence 内容/身份 FAIL，见 P1-2。
  - Probe D（配置/隐私）：默认、支持表、未知/空白模型、encoding、5/28k/30k、
    description/output、120 秒、四版本、local<=provider 和未知 YAML 全 PASS。
    受控 import/load/schema 探针未读取真实环境值、未开 socket；直接
    `ValidationError` 脱敏 PASS，但 `ConfigError` traceback FAIL，见 P1-3。
  - Probe E（依赖/离线副作用）：Python `3.12.11`/`arm64`；既有锁图版本零变化；
    新增锁包仅 OpenAI 2.46.0、distro 1.9.0、jiter 0.16.0、sniffio 1.3.1，
    tiktoken 0.13.0 由既有传递依赖提升为直接依赖；安装元数据许可证与 handoff
    一致。包 import 不联网且未实例化 client，但 tokenizer 空缓存离线解析和 SDK
    凭据环境读取 FAIL，见 P1-4/P1-5。
  - Probe F（五轴/范围/性能）：固定父链、作者身份、7 路径范围、禁止路径、复用、
    红线均 PASS；最大 90 个嵌套 points、20 evidence/keywords、每 point 10 refs
    边界及所有 over-limit 反例 PASS。完成结果与调用审计关联 FAIL，见 P1-6。
- 验收矩阵：
  - AC-1：FAIL。union、kind/ref/cardinality/copy 大部通过，但空白 evidence/point/
    keyword 可进入，不能称为完整 fail-closed 证据契约。
  - AC-2：FAIL。配置数值/版本/未知字段通过；secret-shaped YAML 值仍可从
    `ConfigError.__traceback__` 的项目帧访问。
  - AC-3：PASS。`AnalysisPayload` 序列化集合精确为 A-04 的 10 个字段，禁止字段
    与 4,001 字符描述均被拒绝。
  - AC-4：FAIL。范围、锁定版本、许可证、arm64 package import 和既有依赖稳定
    通过；全新空缓存无法离线解析 `o200k_base`，且 OpenAI SDK import 读取凭据型
    环境变量。
  - AC-5：PASS。无 Schema/Repository/Provider/Prompt/编排或真实资源行为。
- ADR-008 追溯：
  - A-01：PASS，共享契约/依赖切片，无 Provider 或业务编排。
  - A-02：FAIL，union/固定 reason 已冻结，但 `AnalysisCompleted` 可持有互相矛盾
    的 result/call provider/model。
  - A-03：后续 TASK-008/TASK-010；本切片未实现副作用顺序。
  - A-04：PASS，出站字段白名单和封闭 Schema 正确。
  - A-05：FAIL，共享配置边界正确，但空 tokenizer 缓存会尝试网络下载 BPE；
    采样/计数/纯请求构造仍是 TASK-008。
  - A-06：FAIL，哈希构造算法是 TASK-008，但本切片冻结的三处哈希值表示并非
    64 位小写 SHA-256。
  - A-07：共享配置上限 PASS；真实请求计数/`CloudCallBudget` 是 TASK-010。
  - A-08：FAIL，resolver/延迟读取是后续任务，但当前 ConfigError traceback 与
    SDK import 已违反共享隐私前提。
  - A-09：后续 TASK-008；当前 OpenAI 2.46.0 import 全局读取
    `AZURE_OPENAI_AD_TOKEN` 的事实会阻断“只通过注入解析”的 Adapter 前提。
  - A-10：provider-neutral `AnalysisContent` PASS；Structured Outputs/Adapter
    语义验证是 TASK-008。
  - A-11：FAIL，来源/kind/ref/time 公共形状通过且足以实现后续精确 grounding，
    但空白 excerpt/evidence ID/point ref 可绕过有效证据语义；精确子串比较本身
    仍正确留给 TASK-008。
  - A-12：边界 PASS；Artifact/Provider-call/事务为 TASK-008/TASK-010，未改
    `state.py`、Schema 或 `complete_stage`。
  - A-13：PASS，直接范围/锁文件隔离/必要传递依赖正确。
  - A-14：FAIL，共享切片的 hash/privacy/offline tokenizer 反例未通过；完整 Fake/
    SQLite/SDK 参数矩阵仍是后续任务。
  - A-15：PASS，未读取真实密钥、未调用真实 API/token-count、未访问真实
    YouTube/Vault/媒体/模型/用户内容。
- Findings：
  - P1-1（correctness/architecture，`src/youtube_intel/domain.py:521,683-684`）：
    `AnalysisInput.transcript_content_hash`、`AnalysisInput.request_hash` 和
    `AnalysisResult.request_hash` 只有 `min_length=1`。独立矩阵实际接受纯空白、
    非十六进制、63 位和 64 位大写值，仅空字符串失败；这与本任务“审计哈希”、
    ADR-008 A-06 及既有 `TranscriptSample.source_content_hash` 的
    `^[0-9a-f]{64}$` 表示不一致，后续无法可信消费公共请求身份。
  - P1-2（correctness/security，`src/youtube_intel/domain.py:403-424`、
    `src/youtube_intel/domain.py:434-471`）：多个新增“非空”出站/模型字段仅以
    长度判断。独立反例实际
    接受纯空白 title、transcript sample、evidence ID、excerpt、point text、
    point evidence ID 和 keyword；空白 evidence ID 还能与空白引用自洽，令无有效
    内容的模型输出通过 grounding 公共门禁。
  - P1-3（security，`src/youtube_intel/config.py:636-645`）：secret-shaped
    `api_key_env` 的公开错误、repr、`errors()`、cause/context 和格式化 traceback
    均已脱敏，但遍历 `ConfigError.__traceback__` 可在 `load_settings` 的第
    643/645 行项目帧局部变量 `raw` 取回完整 sentinel。Reviewer 包明确要求
    traceback 也不得泄漏。
  - P1-4（correctness/privacy，`pyproject.toml` 的 tiktoken 直接基线）：
    在受控全新空 `TIKTOKEN_CACHE_DIR`、socket/API 均拦截的离线探针中，
    `tiktoken.get_encoding("o200k_base")` 尝试 GET
    `https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken`。
    wheel/lock 本身不能保证 A-05 的本地解析，既会令干净离线运行失败，也会产生
    未授权隐式网络路径。
  - P1-5（security/architecture，`openai==2.46.0` 依赖基线）：受控 env 哨兵
    证明单纯 `import openai` 即尝试读取 `AZURE_OPENAI_AD_TOKEN`；安装源码
    `openai/__init__.py:158-164` 在 import 时读取并保存 Azure/OpenAI 全局环境
    配置。这不实例化 client 或联网，但已破坏 A-08“最后才由注入 resolver 读取
    凭据”的共享前提，后续 Adapter 不能仅靠传入 `api_key` 消除 import 时读取。
  - P1-6（correctness/audit，`src/youtube_intel/domain.py:516-521,550-552`）：
    `AnalysisCompleted` 不校验 `result.provider/model` 与 `call.provider/model`。
    独立反例成功构造 result=`openai/gpt-4.1-mini`、
    call=`different-provider/different-model` 的不可变完成结果，公共契约允许
    互相矛盾的可信审计元数据。
  - P0：无。P2：无。P3：无。
- 五轴/范围/红线/复用结论：
  - Correctness：上述 P1-1/P1-2/P1-4/P1-6 阻断；其余结构、基数和固定 enum
    通过。
  - Architecture：provider-neutral 边界和专用 payload 正确；SDK 全局环境读取、
    tokenizer 隐式网络和完成审计不一致阻断安全后续消费。
  - Security：无真实密钥/API/Vault 行为；P1-2/P1-3/P1-5 阻断。
  - Performance：新增 point/evidence/keyword 序列均有有限上限，验证循环最坏
    规模受控；无新增热路径或 Provider 调用。
  - Readability：变更集中、命名清晰、职责基本单一；未见无关重构或死代码。
  - 范围/红线：implementation head 是 base 的唯一非 merge 子提交，精确 7 个批准
    路径；无禁止路径、真实数据、凭据、Provider、Prompt、Schema/state/cache 或构建
    产物提交。
  - 复用/许可证：`DIRECT` 官方 OpenAI/tiktoken 范围与锁定/许可证证据一致，
    无复制第三方实现或手写 OpenAI HTTP；但 P1-4/P1-5 证明当前复用基线尚不满足
    已冻结的离线/凭据副作用要求。
- 跳过检查：未运行真实 OpenAI/API/token-count、真实环境变量值、付费调用、真实
  YouTube/Vault/用户内容、媒体、模型或凭据路径；均未授权，且不作为拒绝理由。
- 剩余风险：精确 evidence 子串运行时验证、采样/token 计数、完整请求哈希算法、
  CredentialResolver、CloudCallBudget、SDK 参数、缓存与 SQLite 原子性仍属于
  TASK-008/TASK-010；其尚未实现本身未被列为 finding。
- `DECISION NEEDED`：`None`；由原 Implementer 在获批 correction 包内修复上述
  findings 后重新提交并接受全新独立审查。
- Verdict：`REJECT`
- 未解决 P0/P1：P0 无；P1-1 至 P1-6 全部未解决。

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

## Correction 1 实现者追加（2026-07-21）

### 元数据、目标与范围

- Role：`Codex Implementer (Correction 1)`。
- Starting review evidence：
  `0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`；其唯一父提交为 reviewed
  implementation `382251298af7fcbfadba66c1902af6de0a425179`。
- 目标：只关闭第一轮 Reviewer 的 P1-1 至 P1-6，并落实已批准的 ADR-008
  A-16/A-17；不重做已通过的共享契约/依赖工作。
- Correction 1 实际修改：`src/youtube_intel/domain.py`、
  `src/youtube_intel/config.py`、`tests/unit/test_contracts.py`、
  `src/youtube_intel/resources/o200k_base.tiktoken` 和本 handoff。
- 保持不变：`config/settings.example.yaml`、`pyproject.toml`、`uv.lock`；没有修改
  Provider、`analysis.py`、Prompt、Schema/migration、`state.py`、
  `complete_stage`、Repository、CLI、其他测试、任务、ADR 或 main。
- Correction commit：本追加与纠偏实现将位于同一个新的非 merge、非 amend
  commit；精确 SHA 由提交后的完成报告记录。

### A-16 固定 tokenizer 资源

- 唯一 GET：
  `https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken`；
  无认证、无 Cookie/header/token/query、禁用代理且不跟随重定向。没有重试或访问
  其他 URL。
- 提交路径：`src/youtube_intel/resources/o200k_base.tiktoken`。
- 本机下载后立即校验：`3,613,922` bytes；SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`。
- 包内读取：测试通过 `importlib.resources` 定位包资源，并向 tiktoken 0.13.0
  低层 `load_tiktoken_bpe` 显式传入 expected hash；未调用
  `tiktoken.get_encoding("o200k_base")`。
- 离线失败关闭：在空 `TIKTOKEN_CACHE_DIR`、`requests.get` 和
  `socket.create_connection` 均被拒绝的进程中，本地包资源解析成功；资源缺失、
  单字节篡改、错误 expected hash 和内容可哈希但解析失败均本地报错，未回退网络或
  既有 cache。
- 打包证据：`uv build --offline` 生成的 sdist/wheel 均同时包含
  `youtube_intel/migrations/001_initial.sql` 与
  `youtube_intel/resources/o200k_base.tiktoken`；从两份归档解包流重新计算，资源
  均为 `3,613,922` bytes 且 SHA-256 与上述固定值一致。`uv_build` 自动包含资源，
  因此未修改 `pyproject.toml`。
- 许可证：依赖 tiktoken 0.13.0 仍为 MIT；固定 OpenAI BPE Blob 的文件级分发许可、
  归属和 NOTICE 结论明确待 `TASK-014` 发布门禁复核，未在本任务推定。

### A-17 OpenAI SDK 隔离导入

- 产品源码 AST 与 pytest 主进程均未直接或间接导入 `openai`；依赖和版本验证只用
  `importlib.metadata`。
- SDK 导入只在全新独立子进程完成：绝对 `sys.executable`、`-I`、参数列表启动、
  `shell=False`，不构造 client、不读取密钥、不发请求。
- 子进程 `env` 精确由三个固定字面量构成：
  `PYTHONNOUSERSITE=1`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`；没有复制
  `os.environ`。
- 父进程只写入合成哨兵，覆盖 `OPENAI_*`、`AZURE_*`、`HTTP_PROXY`、
  `HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY`、`PYTHONPATH` 及
  `*_TOKEN`/`*_KEY`/`*_SECRET`/`*_PASSWORD`。子进程在导入 OpenAI 2.46.0 前后
  回传的禁用变量名列表均为空，stdout/stderr 不含哨兵，pytest 主进程
  `sys.modules` 前后均无 `openai`。
- A-17 的“导入完成后经专用匿名管道传临时密钥”只作为后续 TASK-008 契约冻结；
  本切片没有实现进程协议、Provider、密钥管道或真实凭据路径。

### P1-1 至 P1-6 RED/GREEN 与关闭证据

相同六个具名纠偏探针先在 review evidence 上运行得到 `6 failed`，再在最小修复后
运行得到 `6 passed`：

| Finding | RED 反例 | GREEN 关闭证据 |
|---|---|---|
| P1-1 审计哈希 | 三字段接受 63/65 位、大写、非 hex 和前后空白 | `AnalysisInput.transcript_content_hash`、`AnalysisInput.request_hash`、`AnalysisResult.request_hash` 均固定 `^[0-9a-f]{64}$`；合法 64 位边界通过 |
| P1-2 语义非空 | 出站、grounding、provider/model 多字段接受纯空白 | 任务新增契约边界拒绝全部列明空白字段，`description=""` 和 `default_language=None` 仍合法；带首尾空格的非空原值原样保留 |
| P1-3 异常图脱敏 | `load_settings.raw` 的 frame local 可观察完整哨兵 | 校验在返回安全文本的隔离 frame 内完成；raise 前清空并删除原 mapping，`ConfigError` 无 cause/context；文本、repr、Pydantic errors、递归异常图、traceback、所有 `src/youtube_intel` frame locals 与 pytest getrepr 均无哨兵 |
| P1-4 tokenizer 本地只读 | 固定资源缺失，无法在空 cache/断网条件下解析 | source/package/sdist/wheel 哈希一致；包内低层 loader + expected hash 离线解析；缺失/篡改/错误 hash/解析失败全部本地失败关闭 |
| P1-5 SDK 隔离 | 既有依赖测试在 pytest 主进程 `import openai` | 主进程只用 metadata；独立白名单环境子进程完成离线 import，合成敏感父环境未继承 |
| P1-6 完成元数据 | provider/model mismatch、`None`、纯空白均可构造 | `AnalysisCompleted` 在 call 字段边界强制 provider/model 非空且与 result 精确一致；浅/深 copy 保持一致，全部 `model_copy(update=...)` 继续拒绝；错误不回显结构化内容哨兵 |

额外回归：`AnalysisPayload.model_dump()` 仍精确为 A-04 的 10 字段白名单；全部新增
分析契约继续拒绝 `model_copy(update=...)`；Cloud 默认关闭、28k/30k、model/
encoding/version、配置脱敏和空描述行为均由最终 contracts/full suite 通过。

### 离线检查结果

| 命令/探针 | 结果 |
|---|---|
| P1-1 至 P1-6 相同六探针 RED | `6 failed`，逐项命中 Reviewer 六个 finding |
| P1-1 至 P1-6 相同六探针 GREEN | `6 passed in 0.79s` |
| `uv lock --check --offline` | PASS，`Resolved 84 packages` |
| `uv sync --locked --offline` | PASS，`Resolved 84 packages`、`Checked 61 packages` |
| `uv run --offline python -m pytest tests/unit/test_contracts.py` | PASS，`72 passed` |
| `uv run --offline python -m pytest` | PASS，`324 passed` |
| `uv run --offline mypy src` | PASS，13 个 source files 无问题 |
| `uv run --offline ruff check .` | PASS，`All checks passed!` |
| `uv run --offline python -m youtube_intel --help` | PASS |
| `uv build --offline` | PASS，sdist/wheel 成功且 migration/resource 内容与哈希均通过 |
| 下载后网络边界 | 除唯一固定 Blob GET 外，全部命令显式离线；无 API、token-count、Provider 或真实资源访问 |
| 提交前 `git diff --check` | PASS；提交后固定 base range 由完成报告记录 |

### 依赖、Diff、安全与复用复核

- 直接依赖仍精确为获批范围：
  `mlx-whisper>=0.4.3,<0.5`、`openai>=2.46.0,<2.47`、
  `pydantic>=2.13.4,<2.14`、`pyyaml>=6.0.3,<7`、
  `tiktoken>=0.13.0,<0.14`、`yt-dlp[default,deno]>=2026.7.4,<2026.8`。
- working `uv.lock` blob 与 reviewed implementation 完全相同，均为
  `db78e4503c2ac9d4b9bbe1ce7001c6a1217553c9`；没有新增、删除或升级依赖。
- `DIRECT`：既有 Pydantic/标准库验证能力、官方 OpenAI 2.46.0
  （Apache-2.0）、tiktoken 0.13.0（MIT）及 A-16 固定 Blob；未复制或改写第三方
  实现。固定 Blob 文件级许可证风险按 A-16 留给 TASK-014。
- `REJECT/DEFER` 保持：手写 OpenAI HTTP、第二 Provider、云端 token-count、SDK
  主进程导入/自动重试、正式 tokenizer runtime、采样/请求构造、真实 client/API/
  密钥、匿名管道 Provider、缓存和事务编排。
- 相对 review evidence 的 Correction Diff 只涉及 domain/config/contracts
  test/resource/handoff；相对 original base 的完整产品 Diff 仍严格属于获准的 8
  路径。`pyproject.toml`、settings example 与 lock 在 Correction 1 中字节不变。
- 敏感模式与范围搜索未发现真实 key、token、私钥、用户数据、API 响应、cache、
  模型、媒体或未批准文件；命中仅为隔离子进程源码字符串及显式合成测试哨兵/路径。
- 五轴自审：correctness、architecture、security、performance、readability 均无
  未解决 P0/P1/P2/P3；新增循环只遍历受限契约集合、有限异常图或 13 个产品源码
  文件，无无界生产热路径。

### 跳过项、风险与结论

- 跳过：未运行真实 OpenAI/API/token-count、真实环境变量值/密钥、付费调用、真实
  YouTube/Vault/用户内容、媒体、模型、Provider、Prompt、采样、缓存、事务或正式
  匿名管道协议；均为范围外或未授权。
- 剩余风险：固定 `o200k_base.tiktoken` 的文件级分发许可证/归属/NOTICE 必须由
  TASK-014 给出发布结论；正式 tokenizer runtime 的 `CONFIG_INVALID` 映射、匿名
  管道生命周期、Provider/凭据/timeout/错误映射仍须由 TASK-008 独立实现和审查。
- `DECISION NEEDED`：`None`。
- 建议状态：`IN_REVIEW`；不得由本会话启动 Reviewer、修改 main 状态、merge 或 push。

## Correction 1 第二轮独立 Codex Reviewer（2026-07-22）

### 审查对象与门禁

- Reviewer：`Codex /root`（第二轮全新独立审查）。
- Reviewed Correction 1 head：`d95745fd04b115369a9fd70362cd735d1eb70917`。
- 动态授权：main 位于 `aa134f43af57e6f6bdc7455b56c59ac97ee342e7`；该文件的授权提交为
  `4eec2e186fce6dedbb105234f624fcb93274c938`，其唯一父为所要求的
  `3eac5f9897bdfb59e764afde411e632822dcfb66`。main 干净且控制面
  `TASK-008A=IN_REVIEW`。
- source 分支、HEAD、父链、身份与洁净度均通过：分支为
  `codex/task-008a-cloud-analysis-shared-contracts`，HEAD 精确为 reviewed head，
  其唯一父为 `0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`；Git 身份为
  `Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`。
- Correction range 精确为 handoff、`domain.py`、`config.py`、contracts test 和固定
  tokenizer resource 五个路径；完整 base range 精确为获准的八个路径，
  `pyproject.toml` 与 `uv.lock` 相对 reviewed implementation 均未变化。无 Provider、
  `analysis.py`、Prompt、Schema/migration、`state.py`、`complete_stage`、CLI、任务/ADR、
  凭据、缓存或构建产物变更。

### 独立复跑检查

| 检查 | 结果 |
|---|---|
| `uv lock --check` | PASS，`Resolved 84 packages` |
| `uv sync --locked --offline` | PASS，`Resolved 84 packages`、`Checked 61 packages` |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS，`72 passed` |
| `uv run python -m pytest` | PASS，`324 passed` |
| `uv run mypy src` | PASS，13 个 source files 无问题 |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS |
| `uv build --offline` | PASS；sdist/wheel 成功生成 |
| `git diff --check 82d1fd7...d95745f` | PASS |
| package contents | PASS；sdist/wheel 都包含 `migrations/001_initial.sql` 与 BPE resource |
| BPE archive hash | PASS；source、sdist、wheel 均为 `3,613,922` bytes、SHA-256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d` |

### 六组独立探针与追溯

- A（hash/语义非空/完成审计/copy）：PASS。三处 hash 拒绝 63/65 位、uppercase、
  non-hex、空白；出站、grounding、provider/model 的纯空白被拒绝且原值不被 strip；
  空 description 仍合法。`AnalysisCompleted` 拒绝 provider/model mismatch、None/空白
  call model；浅/深 copy 合法，所有 analysis contract 的 `model_copy(update=...)` 被拒绝。
- B（完整 ConfigError 脱敏图）：PASS。使用新的 secret-shaped YAML 哨兵，递归检查异常、
  cause/context、Pydantic errors、普通 traceback 表示和全部项目 frame locals；哨兵未出现，
  安全字段路径与分类仍保留。
- C（A-16 本地资源/无网络）：PASS。socket 被拒绝时，包内 resource 经 expected hash 的
  低层 loader 离线解析；缺失、篡改、错误 hash 与可哈希但畸形内容均 fail-closed，未调用
  `get_encoding`、HTTP 或 cache fallback。source/sdist/wheel 哈希一致。
- D（A-17 SDK 隔离）：PASS。产品源码静态 AST 和 pytest/main probe 均无 OpenAI 导入；
  使用绝对 Python、`-I`、`shell=False` 与仅三项固定 env 的新子进程导入 OpenAI 2.46.0。
  合成 `OPENAI_*`、`AZURE_*`、代理及 `*_TOKEN/_KEY/_SECRET/_PASSWORD` 哨兵均未进入子进程，
  未构造 client 或请求 API。
- E（回归/范围）：PASS。A-04 十字段 payload 白名单、evidence kind/cardinality/空时间、
  Cloud 默认关闭、model/encoding、5/28k/30k/4k/120 秒/版本及未知字段 fail-closed 均由
  contracts/full suite 和独立范围审计覆盖；无 public free-form dict/Any/object、SDK 类型、
  Provider、Prompt、Schema/state 或配置兼容性回归。
- F（五轴/复用/ADR）：PASS。A-01 至 A-17 中属于共享契约/依赖基线的 A-02、A-04、A-05 前提、
  A-06 表示、A-08 前提、A-13、A-14 前提、A-16、A-17 全部满足；Provider、匿名管道、
  sampling/token 计数、CredentialResolver、CloudCallBudget、缓存和 SQLite 事务均明确留给
  TASK-008/TASK-010，未因其未实现而拒绝。

### Findings 与结论

- Findings：P0 无；P1 无；P2 无；P3 无。
- Correctness：六个第一轮 P1 均由独立反例关闭；契约、包资源和构建归档一致。
- Architecture：领域层无 SDK 导入；官方 SDK 仅以隔离子进程验证，后续 Adapter/匿名管道仍在
  既定任务边界内。
- Security：未触及真实密钥、API、内容、Vault 或网络；异常图、本地 BPE 和 SDK 环境隔离均
  fail-closed。固定 BPE Blob 的文件级许可/NOTICE 仍由 TASK-014 发布门禁复核。
- Performance：新增验证均有明确有限上限；无新增生产热路径、网络调用或无界循环。
- Readability/范围/红线/复用：变更集中、命名清晰；范围和禁止路径均通过。复用保持
  `DIRECT`（OpenAI 2.46.0 Apache-2.0、tiktoken 0.13.0 MIT、固定 BPE Blob）和既有
  `REJECT/DEFER` 边界，无未批准依赖或来源不明代码。
- Skipped checks：真实 OpenAI/API、密钥/真实环境值、付费调用、云端 token-count、真实
  YouTube/Vault/用户内容、媒体/模型及正式 Provider/匿名管道均未运行；它们未获授权且不构成
  本次拒绝理由。
- Remaining risks：BPE 文件级分发许可/NOTICE 待 TASK-014；正式 tokenizer runtime 错误映射、
  凭据生命周期、Provider/timeout/缓存/事务原子性待 TASK-008/TASK-010。
- `DECISION NEEDED`：`None`。
- Verdict：`APPROVE`。
- 未解决 P0/P1：无。
