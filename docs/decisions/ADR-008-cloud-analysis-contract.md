# ADR-008：云端深度分析契约

## 状态

Accepted

## 日期

2026-07-20

## 批准记录

- 批准日期：2026-07-20
- 补充批准日期：2026-07-21
- 决策人：用户（产品负责人）
- 批准范围：ADR-008 A-01 至 A-17，以及 TASK-008A 使用
  `openai>=2.46.0,<2.47`、`tiktoken>=0.13.0,<0.14`、必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改和任务卡离线 uv 验证/构建命令。
- A-16 资源授权：TASK-008A Correction 1 可从 OpenAI 官方 Blob 单次下载
  `o200k_base.tiktoken`，只在 SHA-256 精确为
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d` 时提交到
  `src/youtube_intel/resources/o200k_base.tiktoken`。该授权不扩展为一般网络权限。
- A-17 隔离授权：TASK-008A 只冻结并离线验证 SDK 子进程导入/匿名管道密钥策略；
  不实现 Provider，不读取任何真实环境变量值或密钥。
- 执行边界：依赖动作只能在后续固定 base/worktree/角色/文件范围的 TASK-008A
  正式分配包内执行；本次接受不创建 worktree、不安装依赖。
- 继续未授权：真实 OpenAI API、密钥读取、付费调用、云端 token-count 请求、真实
  YouTube/Vault/用户数据、媒体、模型或凭据操作。

## 背景

TASK-008 只读预检确认，现有 `AnalysisInput`、`AnalysisResult`、
`SummaryProvider`、Artifact、Provider call 和 `complete_stage` 已提供基础，但还
不能直接实现安全、可审计的云端分析：

- 没有结构化的“已完成/按策略跳过”结果，TASK-009 只能把所有未分析情况压成
  `analysis=None`。
- 现有输入包含过宽的领域对象，不能证明实际发往云端的数据严格符合最小化清单。
- token 采样、证据引用、请求哈希、缓存、调用预算和密钥读取顺序尚未冻结。
- OpenAI SDK、`tiktoken` 仍未成为显式直接依赖；TASK-008 与 TASK-009 若各自修改
  公共契约和锁文件，不能安全并行。

产品负责人已接受本文契约与拆分方案。接受只冻结设计和 TASK-008A 依赖范围；固定
worktree/角色/文件范围仍须另行分配，真实密钥和云调用继续禁止。

## 推荐决策

### A-01：先完成共享契约与依赖基线

新增 `TASK-008A：云分析共享契约与依赖基线`。它先冻结具名输入/输出、配置、预算和
依赖，不实现 Provider、不读取密钥、不联网调用 OpenAI。TASK-008A 完成后再完成
TASK-009A；两项均为 `DONE` 后，TASK-008 与 TASK-009 才可从同一最新 main 并行。

### A-02：分析结果必须显式区分完成和跳过

新增不可变、禁止未验证 `model_copy(update=...)` 的具名对象：

- `AnalysisCompleted(result, call: ProviderCallMetadata)`；
- `AnalysisSkipped(reason, call: ProviderCallMetadata | None, safe_message)`；
- `AnalysisOutcome = AnalysisCompleted | AnalysisSkipped`。

跳过原因冻结为 `CLOUD_DISABLED`、`CREDENTIAL_UNAVAILABLE`、
`BUDGET_EXHAUSTED`、`INPUT_TOO_LARGE`、`PROVIDER_REFUSAL`。这些是业务结果，不扩展
ADR-002 的八个 `ErrorCode`。低价值视频不创建 Analysis Job，也不产生
`AnalysisOutcome`。

### A-03：资格与副作用顺序固定

执行顺序必须为：

1. 验证上游最终评分为高价值、Pipeline/Job/规范字幕均有效；
2. 处理云端关闭；
3. 构造最小化输入并完成本地采样、token 计算和缓存命中检查；
4. 检查 run 调用预算；
5. 最后才通过注入的 `CredentialResolver` 读取环境变量；
6. 预留 Provider call，执行一次云端推理。

关闭、缓存命中、低价值、超限、预算耗尽和缺少凭据均不得调用 OpenAI。无效字幕、
provenance、Pipeline 或 Job 是硬错误，不得伪装成跳过。

### A-04：实际出站数据使用专用最小化对象

新增 `AnalysisPayload`，只允许下列字段进入 OpenAI 请求：

- `video_id`、标题、频道名、发布时间、时长、默认语言；
- 最多 4,000 Unicode code points 的公开 YouTube 描述；
- 最终字幕语言、输出语言；
- 按 A-05 得到的规范字幕样本。

不得发送本地路径、Vault/用户内容、Artifact/Job/Provider-call ID、内部哈希、
诊断、评分子维度、密钥名称或任何自由 metadata。`AnalysisInput` 只可把
`AnalysisPayload` 作为出站对象，另带本地审计哈希/版本；Adapter 只能序列化
`payload`。

### A-05：token 预算采用本地保守计数

`tiktoken` 只在本地完成采样和计数。模型必须命中项目维护的显式
model-to-encoding 映射；未知模型/encoding 为 `CONFIG_INVALID`，不得猜测或调用
Provider 探测。

- Provider 硬上限保持每视频 30,000 input tokens。
- 本地发送上限固定为 28,000 tokens，为 Responses framing 保留 2,000 tokens
  安全余量。
- 采样版本为 `cloud-token-sampling-v1`，保留 head/body/tail，顺序稳定且不重复。
- 固定 system/developer instructions、JSON Schema 和 payload 必须一起计入本地
  预算；本地仍超限时返回 `INPUT_TOO_LARGE`，零云调用。
- 计数和出站必须消费同一个纯请求构造函数的规范字段，禁止先计算一种 Prompt 再
  发送另一种请求。

V1 不调用 `/v1/responses/input_tokens`，因为该计数请求本身会把 payload 发往云端并
消耗调用/隐私预算。推理返回的实际 `usage.input_tokens` 必须记录并复核不超过
30,000。

### A-06：请求身份与缓存覆盖完整生成条件

请求哈希必须覆盖规范化 payload、完整 transcript content hash、采样文本及版本、
Prompt/Schema 版本、Provider、模型、输出语言、最大输出 tokens 和
隐私策略版本。固定版本：

- `analysis-prompt-v1`
- `analysis-result-v1`
- `cloud-token-sampling-v1`
- `cloud-privacy-v1`

只有哈希、Provider、模型、版本、Artifact 内容哈希和成功 Provider call 全部匹配
时才可命中缓存。

### A-07：run 预算按真实出站请求计数

单次 run 最多 5 次云端请求。每次开始网络传输即消耗一次预算，包括 timeout、
限流、5xx 和其他失败请求；缓存、关闭、缺凭据和本地校验不消耗。SDK 内置重试必须
关闭，Provider 内不做格式修复调用，因此每个视频最多一次推理请求。

V1 保持单 worker 并发，预算由 TASK-010 注入的单进程 `CloudCallBudget` 管理；不
新增 Schema/migration。进程崩溃后依靠已持久化 Provider call 和 Artifact 恢复，
不声称跨进程严格 exactly-once。

### A-08：密钥只通过注入解析且延迟读取

`CredentialResolver` 公共接口只接收已验证的环境变量名称并返回临时 secret 值；
值不得进入 Pydantic 对象、YAML、`repr`、异常、日志、诊断、测试快照或 Artifact。
只有 A-03 的所有前置门禁通过后才读取。环境变量缺失返回结构化
`CREDENTIAL_UNAVAILABLE`，不把变量名或值发送给 Provider。

### A-09：OpenAI Adapter 的传输边界固定

首个且唯一 V1 云 Adapter 使用官方 OpenAI Python SDK 的 Responses API：

- 官方固定 endpoint，不允许自定义 `base_url`；
- `store=False`、无 tools、无 streaming、`truncation="disabled"`；
- timeout 使用已冻结的 120 秒；
- `max_retries=0`；
- V1 不发送 temperature；`max_output_tokens` 默认 4,000，范围 `256..8,000`；
- 模型可配置但必须通过 A-05 的显式 tokenizer 支持表。

Adapter 不读取全局环境变量、不自行重试、不回退到 Chat Completions，也不添加第二个
Provider。

### A-10：只接受严格 Structured Outputs

请求使用 OpenAI Structured Outputs 和 provider-neutral `AnalysisContent` 的严格
JSON Schema；Schema 不允许模型生成 provider、model、prompt/request hash 或调用
元数据。Adapter 校验内容和证据后，以本地可信请求上下文封装最终
`AnalysisResult`。V1 不执行第二次“格式修复”调用：

- 合法结构继续执行语义/证据校验；
- Provider refusal 返回 `PROVIDER_REFUSAL`；
- Schema/语义/短读/超限响应为 `INVALID_RESPONSE`；
- timeout/连接为 `TRANSIENT_NETWORK`；
- 429 为 `RATE_LIMITED`；
- 5xx 为 `PROVIDER_UNAVAILABLE`；
- 401/403 为 `PERMISSION_DENIED`。

异常图必须脱敏，不得保留 payload、字幕、响应正文、密钥或绝对路径。

### A-11：证据必须可在最小化输入中验证

所有 `AnalysisPoint` 至少引用一个 evidence ID。`EvidenceExcerpt` 增加精确来源字段，
只允许标题、频道、描述或 transcript sample；excerpt 必须是对应最小化字段的精确
子串。V1 没有规范文本到时间戳的稳定映射，因此 `start_seconds`/`end_seconds` 必须
为空。

字段种类固定：

- `key_facts` 仅 `fact`；
- 产品/商业机会、待验证假设、风险仅 `inference`；
- 可落地方向和行动建议仅 `recommendation`；
- 核心观点只允许 `fact` 或 `inference`。

### A-12：沿用现有 Artifact/Provider-call/完成事务

原始响应写 `ANALYSIS_RAW` / `RAW_RESPONSE_30D`，结构化结果写
`ANALYSIS_STRUCTURED` / `LONG_LIVED`。成功时使用现有 `complete_stage` 在同一
SQLite 事务中完成 Artifact、Provider call、`SCORED -> ANALYSIS_READY` 和 Job。

结构化跳过不伪造 Provider call；由 TASK-010 持久化安全的跳过结果/诊断并推进同一
状态。共享切片若发现现有 Repository 无法原子表达，必须报告 `DECISION NEEDED`；
本 ADR 不授权 Schema、migration 或 `state.py` 变更。

### A-13：依赖版本与并行隔离

推荐显式直接依赖：

- `openai>=2.46.0,<2.47`，Apache-2.0；
- `tiktoken>=0.13.0,<0.14`，MIT。

由 TASK-008A 独占修改 `pyproject.toml`/`uv.lock`，执行包下载、锁定、导入和许可证
验证；不得调用 API。正式 TASK-008 不再修改依赖/锁文件。TASK-009A 后续独占
Jinja2 的依赖基线，从而使 TASK-008/TASK-009 正式实现写入范围完全隔离。

### A-14：离线验收必须覆盖隐私和预算

至少覆盖：

- 关闭、低价值、缓存、超限、预算耗尽、缺凭据均零调用/延迟读取；
- 支持/未知 tokenizer、采样确定性、28k/30k 边界；
- 请求序列化白名单与敏感哨兵；
- Structured Outputs 成功、refusal、缺字段、语义错误、限流、5xx、timeout；
- 证据精确 grounding、Artifact/Provider-call/SQLite 回滚与重排恢复；
- SDK 配置 `store=False`、`max_retries=0`、无 tools/stream/custom base URL。

测试只使用 Fake transport 和临时 SQLite，不读取真实环境变量值。

### A-15：真实云端路径单独授权

接受本 ADR 仍不授权：

- 读取真实密钥；
- 真实 OpenAI 请求、付费调用或字幕发送；
- 真实 YouTube、Vault、媒体、模型或凭据操作。

TASK-008A 已获本文批准的依赖/锁文件/包下载和离线命令范围，并已获得固定
base/worktree/角色/文件范围。第一轮 Reviewer 的 6 个 P1 由 Correction 1 在原 7 路径
加 A-16 固定资源文件范围内修复。TASK-008 仍须单独实施授权；真实云端冒烟留给
TASK-013 的单独审批。

### A-16：`o200k_base` 必须是固定包内资源

项目把 OpenAI 官方 Blob 的 `o200k_base.tiktoken` 作为固定本地资源，提交路径为
`src/youtube_intel/resources/o200k_base.tiktoken`，SHA-256 固定为
`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`。

- TASK-008A Correction 1 只允许对
  `https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken`
  执行一次无认证 GET；下载后必须先核对哈希，再纳入 source、sdist 和 wheel。
- 运行时必须通过包资源定位该文件并向 tiktoken loader 显式提供 expected hash。
  资源缺失、哈希不符、无法解析或打包遗漏都返回本地 `CONFIG_INVALID`，且在任何
  Provider、凭据或网络副作用前失败。
- 禁止调用 `tiktoken.get_encoding("o200k_base")` 所隐含的 HTTP/cache fallback；
  空 cache、无网络和 socket 拒绝条件下必须仍可读取已验证的包内资源。
- 本决定不授权其他资源下载、API、模型、密钥或云端操作。该 BPE 资源的文件级分发
  许可证、归属和 NOTICE 边界由 TASK-014 最终复核；未通过不得发布捆绑产物。

### A-17：OpenAI SDK 必须隔离导入，密钥只走导入后的匿名管道

OpenAI SDK 不得在主进程直接或间接导入。TASK-008 的正式 Adapter 必须：

1. 使用绝对 Python executable 启动独立子进程，不通过 shell；
2. 不复制父进程环境，子进程环境只能由固定字面量
   `PYTHONNOUSERSITE=1`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1` 构造；
3. 明确禁止 `OPENAI_*`、`AZURE_*`、`HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、
   `NO_PROXY`、`PYTHONPATH` 以及任何 `*_TOKEN`、`*_KEY`、`*_SECRET`、
   `*_PASSWORD` 进入子进程环境；
4. 先在无密钥状态导入 SDK 并通过非敏感握手确认导入完成，再由父进程通过专用匿名
   管道传入临时密钥；
5. 密钥不得进入环境变量、argv、文件、Pydantic 对象、异常、traceback、诊断、
   Artifact 或日志；进程结束、失败或 timeout 均须关闭管道并丢弃临时值。

TASK-008A 只冻结以上边界，并使用合成哨兵证明离线导入不读取父进程 OpenAI/Azure
变量；它不得实现子进程 Provider、发送请求或读取真实凭据。正式的进程协议、timeout、
子进程退出和错误映射由 TASK-008 在独立实施/审查包中完成。

## 官方证据

- OpenAI Responses API：<https://platform.openai.com/docs/api-reference/responses>
- OpenAI Structured Outputs：
  <https://platform.openai.com/docs/guides/structured-outputs>
- OpenAI Python SDK：<https://pypi.org/project/openai/>
- tiktoken：<https://pypi.org/project/tiktoken/>
- OpenAI 官方 `o200k_base` Blob：
  <https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken>
- tiktoken 0.13.0 `o200k_base` 映射与 expected hash：
  <https://github.com/openai/tiktoken/blob/0.13.0/tiktoken_ext/openai_public.py>
- tiktoken 0.13.0 HTTP/cache loader：
  <https://github.com/openai/tiktoken/blob/0.13.0/tiktoken/load.py>
- OpenAI Python 2.46.0 顶层环境读取：
  <https://github.com/openai/openai-python/blob/v2.46.0/src/openai/__init__.py>

## 不采用的方案

- 直接把整个领域对象/评分对象序列化到云端：无法证明最小化发送范围。
- 使用 OpenAI token-count endpoint 作为默认预检：计数本身会发送字幕内容。
- 开启 SDK 自动重试或格式修复调用：破坏 5 次 run 预算和恢复审计。
- 在主进程导入 OpenAI SDK：2.46.0 顶层导入会读取 OpenAI/Azure 环境变量，破坏
  “最后才读取密钥”的可证明边界。
- 依赖 tiktoken 空 cache 时自动下载 encoding：离线行为和供应链身份不可控。
- 把跳过原因映射为新 `ErrorCode`：违反 ADR-002 冻结枚举。
- 让 TASK-008 与 TASK-009 各自修改公共契约和锁文件：并行会产生冲突。

## 后果

- 产品负责人已批准 A-01 至 A-17；TASK-008A 第一轮审查拒绝后的 Correction 1
  必须先关闭 6 个 P1，再进入新一轮独立审查。
- 两个共享任务均 `DONE` 后，TASK-008/TASK-009 才能从同一 main 并行实施。
- 默认路径继续完全本地；真实云调用、付费、密钥和内容发送保持独立门禁。
- 发布物新增固定 tokenizer 资源，TASK-014 必须给出其文件级许可证与分发结论。
