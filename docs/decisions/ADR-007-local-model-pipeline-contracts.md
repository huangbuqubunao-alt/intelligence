# ADR-007：本地转写与评分共享契约

## 状态

Proposed

## 日期

2026-07-16

## 背景

TASK-006/TASK-007 只读预检确认，两项任务虽可在 TASK-005 完成后并行，但当前
`config.py`、`domain.py` 和 `state.py` 仍存在共享契约空白：

- Whisper 的精确包版本、模型 revision、解码参数、系统解码器、资源门禁和音频清理接口未冻结。
- Ollama 的本地地址、服务/模型版本、结构化调用、确定性采样和模型建议/应用最终决定未分离。
- `videos.score` / `videos.should_summarize` 已存在，但 `complete_stage` 不能在评分阶段原子写入这两个摘要字段。
- TASK-006/TASK-007 若分别修改共享文件，会破坏同基线并行与锁文件隔离。

因此推荐在 TASK-005 `DONE` 后先完成一个共享契约切片，再从同一已验收 main
分别创建 TASK-006 与 TASK-007 worktree。本文仅是提案；产品负责人批准前不得
创建该共享任务、修改代码、安装依赖、下载模型或启动服务。

## 推荐决策

### L-01：TASK-005 最终契约是前置门禁

TASK-005 整合并关闭为 `DONE` 后，必须先复核最终
`TranscriptFetchResult`、`TranscriptArtifact`、`TranscriptProvider` 和质量枚举。
TASK-006/TASK-007 在此之前保持 `BLOCKED/UNASSIGNED`，不得创建写入 worktree。

### L-02：新增共享契约切片

批准后新增 `TASK-005A：本地模型共享契约`，由一个 Codex Implementer 和一个全新
独立 Codex Reviewer 完成。该切片只负责：

- 扩展具名配置与公共领域对象；
- 为评分阶段增加具名、原子的评分摘要写入；
- 为音频 Artifact 增加安全删除确认与过期枚举 Repository 接口；
- 更新示例配置和契约/状态测试。

共享切片不得实现 Whisper/Ollama Provider，不新增 Schema/migration，不安装模型
或系统工具。TASK-006/TASK-007 必须以其 `DONE` commit 为共同 base。

### L-03：模型建议与应用最终决定分离

保留 `ScoreResult.should_summarize` 作为模型原始建议。新增不可变具名对象：

- `ScoringDecision(threshold, final_should_summarize, model_disagrees)`；
- `ScoringOutcome(result, decision, call)`。

`final_should_summarize` 必须严格等于 `ScoreResult.score >= threshold`；
`model_disagrees` 必须严格等于模型建议与最终值不一致。不得覆盖模型原值，不得使用
自由 `dict`、`Any` 或宽 `object` 表达应用决定。

### L-04：评分摘要在阶段完成时原子持久化

新增具名 `ScoringSummaryWrite(score, should_summarize)`，并把它作为
`complete_stage` 的可选参数；只有 `TRANSCRIPT_READY -> SCORED` 转换允许非空。
同一事务必须完成：

1. `SCORING_RAW` / `SCORING_STRUCTURED` Artifact；
2. Provider call；
3. `videos.score` 与最终 `videos.should_summarize`；
4. Pipeline CAS 与 Job 成功。

其他阶段传入评分摘要必须失败且全部回滚。现有列足够，V1 不新增 migration。

### L-05：评分输入采用具名三段采样

新增不可变 `TranscriptSample`，字段固定为 `head`、`body`、`tail`、
`selected_char_count`、`source_content_hash` 和 `sampling_version`。

- `max_transcript_chars` 最小值由 `1` 提升为 `3`。
- `n <= M` 时 `head` 为全文，`body`/`tail` 为空。
- `n > M` 时：
  - `head_len = (M + 2) // 3`
  - `body_len = (M + 1) // 3`
  - `tail_len = M // 3`
  - 正文取剩余可用区间中心的连续片段，并保证三段不重叠。
- `selected_char_count` 只统计原文字符且不得超过 `M`；Prompt 使用固定字段标签，
  标签不计入该内容预算。

采样版本固定为 `sampling-v1`。Prompt、Schema 分别固定为
`scoring-prompt-v1`、`score-result-v1`。

### L-06：评分元数据与哈希边界

评分元数据稳定顺序为：`video_id`、标题、频道名、发布时间、时长、默认语言、最终
字幕语言、描述。新增 `local_scoring.max_description_chars=4000`，范围
`0..20000`；描述按 Unicode code point 截断。

规范输入哈希必须覆盖全部入选元数据、完整 transcript content hash、
`TranscriptSample` 的实际三段与版本、语言、模型、temperature 和输出上限。
主评分与格式修复使用不同 operation/request hash。

### L-07：Ollama 仅使用标准库本地 HTTP

TASK-007 使用 Python 3.12 `urllib.request` / `json`，不新增 `httpx` 或 Ollama
Python SDK。新增配置：

- `local_scoring.base_url` 默认 `http://127.0.0.1:11434`；
- 只允许 `http` 与 loopback 主机 `127.0.0.1`、`localhost`、`::1`；
- 禁止 userinfo、query、fragment 和非空路径；
- 健康/模型预检使用 `GET /api/tags`；
- 评分/修复使用 `POST /api/generate`，`stream=false`，`format` 为
  `ScoreResult` JSON Schema，`think=false`。

Provider 内不做全局网络重试，不自动启动 Ollama、不自动拉取模型、不访问 cloud
tag 或远程地址。

### L-08：Ollama 与评分模型固定版本

首个本机验证版本推荐为 Ollama `0.32.1`，允许范围 `>=0.32.1,<0.33`，MIT。
首个评分模型推荐：

- tag：`qwen3:8b`
- Ollama content digest：
  `sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`
- model layer：`5,225,374,496` bytes
- quantization：`Q4_K_M`
- 上游模型：`Qwen/Qwen3-8B`，Apache-2.0

新增 `local_scoring.expected_model_digest`，启动预检必须精确匹配本地
`/api/tags` 结果。模型缺失或 digest 不匹配为 nonretryable `CONFIG_INVALID`。
Ollama 安装、服务启动、模型拉取和真实本机调用是独立授权，不由本 ADR 自动授权。

### L-09：评分调用、缓存与错误

合法 JSON 直接严格验证；非法 JSON或 Schema 失败最多执行一次格式修复。主调用失败
或修复失败不在 Provider 内循环重试；下一 Job attempt 优先复用已保存的主响应。

- 原始响应：`SCORING_RAW` / `RAW_RESPONSE_30D`
- 结构化结果：`SCORING_STRUCTURED` / `LONG_LIVED`
- 未启动/拒绝连接：`PROVIDER_UNAVAILABLE`
- timeout/短读：`TRANSIENT_NETWORK`
- 429：`RATE_LIMITED`
- 5xx：`PROVIDER_UNAVAILABLE`
- 401/403：`PERMISSION_DENIED`
- 非法/超限响应：`INVALID_RESPONSE`

日志不得记录 Prompt 全文、字幕正文、原始响应或本机绝对路径。

### L-10：mlx-whisper 包与解码参数

TASK-006 推荐 `mlx-whisper>=0.4.3,<0.5`，MIT、Python `>=3.8`；实际锁定前必须
在本机 Python 3.12/arm64 解析并复核 `mlx`、`numba`、`numpy`、`torch`、
`tqdm`、`more-itertools`、`tiktoken`、`huggingface_hub`、`scipy` 等必要传递
依赖。允许修改 `pyproject.toml`/`uv.lock`、安装和下载包必须由产品负责人另行批准。

首版参数固定并进入参数哈希：

- `task="transcribe"`
- `language_hint: str | None = None`
- `temperature=0.0`
- `compression_ratio_threshold=2.4`
- `logprob_threshold=-1.0`
- `no_speech_threshold=0.6`
- `condition_on_previous_text=true`
- `word_timestamps=false`
- `initial_prompt=None`
- `fp16=true`
- `parameter_policy_version="mlx-whisper-v1"`

不得把全部底层 kwargs 暴露为自由映射。

### L-11：Whisper 模型固定 revision 与项目缓存

默认模型保持 `mlx-community/whisper-large-v3-turbo`，固定 revision
`a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`。`weights.safetensors` 固定为
`1,613,977,612` bytes，LFS SHA-256
`951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`。

模型只能由显式安装/doctor 动作下载到项目受控
`data/models/mlx-whisper/<revision>/`，运行时禁止隐式联网；启动时验证 revision
清单、大小和哈希。上游 OpenAI Whisper 模型为 MIT，但该 MLX Community 转换仓库
当前 model card 未声明 license；在模型下载批准与 TASK-014 许可证清单中必须保留
此差异，不能自动推断转换产物许可。

### L-12：音频获取与 ffmpeg 分门禁

音频获取复用锁定的 `yt-dlp==2026.7.4`，只选择一个 audio-only stream，
`download=True` 仅在 TASK-006 的受控媒体授权后允许；禁止 Cookie、登录、`.netrc`、
remote components、播放列表、postprocessor、媒体合并和隐式 ffmpeg。

官方 mlx-whisper 文件解码路径调用 ffmpeg。推荐本机验证版本为 Homebrew
`ffmpeg 8.1.2`；Homebrew 当前构建标记 GPL-3.0-or-later，项目不得捆绑或重新分发，
许可证继续进入 TASK-014。ffmpeg 安装/调用、固定压缩音频冒烟与真实 YouTube 媒体
下载必须分别审批。

### L-13：时长与 `--force` 归属 TASK-010

TASK-006 只提供纯策略函数与防御性校验，不自行把 TRANSCRIPT Job 完成为
`SKIPPED_DURATION_LIMIT`。TASK-010 在创建 Job 前执行 180 分钟门禁：

- 未 force：从 `METADATA_READY` 进入 `SKIPPED_DURATION_LIMIT`，不下载音频；
- force：允许创建 TRANSCRIPT Job。

为满足“日志和状态中记录”，TASK-010 分配前必须另行批准专用 migration，为 Job
增加具名 `duration_limit_overridden` 与 `override_reason` 审计字段；不得把 force
编码进 `scope_key`、`pipeline_version` 或错误文本。本 ADR 不授权该 migration。

### L-14：音频 Artifact 与清理

下载完成即登记 `ArtifactKind.AUDIO`、`EPHEMERAL_AUDIO`、
`expires_at=created_at+7d`。成功转写并安全落盘后立即删除音频；删除失败只记录安全
诊断，不回滚转写。

共享契约切片新增：

- `mark_artifact_deleted(artifact_id, expected_content_hash, now) -> bool`
- `list_expired_artifacts(retention_class, now, limit) -> tuple[ArtifactRecord, ...]`

TASK-006 负责成功路径删除确认；TASK-012 负责周期性过期文件删除与 `deleted_at`
更新。两者只能处理 DATA 根下已登记且哈希匹配的文件。

### L-15：超时、资源与分阶段审批

本地模型调用在独立 `multiprocessing` spawn 子进程执行，超过
`timeouts.local_model_seconds` 时终止并返回 `LOCAL_RESOURCE`；不得只等待不可取消
线程。首次资源门禁采用可配置初始值：

- `transcription.min_free_disk_gib=8`
- `transcription.min_available_memory_gib=6`
- `transcription.max_audio_bytes=2_000_000_000`

真实 180 分钟生产门禁必须根据短音频和中等音频实测再校准。授权拆分为：

1. Python 包解析/锁定/安装；
2. Whisper 模型下载；
3. 固定可再分发 WAV 由标准库解码为 waveform 后执行本地 MLX 冒烟，不调用
   ffmpeg；
4. ffmpeg 安装与固定压缩音频冒烟；
5. Ollama 安装/启动；
6. qwen3:8b 模型拉取与固定文本冒烟；
7. 真实 YouTube/字幕/媒体冒烟。

任一授权不得隐含后续门禁。TASK-006 独占 `pyproject.toml`/`uv.lock`；
TASK-007 使用标准库且不得修改锁文件，因此在共享契约切片完成后可安全并行。

## 官方证据

- mlx-whisper PyPI：<https://pypi.org/project/mlx-whisper/>
- MLX Whisper 官方说明：<https://github.com/ml-explore/mlx-examples/tree/main/whisper>
- MLX Whisper 官方音频加载实现：
  <https://github.com/ml-explore/mlx-examples/blob/main/whisper/mlx_whisper/audio.py>
- MLX Community 模型：
  <https://huggingface.co/mlx-community/whisper-large-v3-turbo>
- OpenAI 原始模型：<https://huggingface.co/openai/whisper-large-v3-turbo>
- Ollama API：<https://docs.ollama.com/api/introduction>
- Ollama generate：<https://docs.ollama.com/api/generate>
- Ollama 模型列表：<https://docs.ollama.com/api/tags>
- Ollama qwen3:8b：<https://ollama.com/library/qwen3:8b>
- Qwen3-8B：<https://huggingface.co/Qwen/Qwen3-8B>
- FFmpeg 许可证：<https://ffmpeg.org/legal.html>
- Homebrew ffmpeg：<https://formulae.brew.sh/formula/ffmpeg>

## 不采用的方案

- TASK-006/TASK-007 直接从 TASK-005 base 并行：共享 config/domain/state 会冲突。
- TASK-007 新增 httpx 或 Ollama SDK：标准库足够，额外依赖会制造锁文件冲突。
- 使用 `latest` 模型 tag 或运行时自动拉取：不可复现且会隐式联网。
- 把模型建议覆盖为最终策略：丢失审计证据并违反 DEC-09。
- 把评分摘要推迟到 TASK-010：会让 `SCORED` 状态与 `videos` 摘要不一致。
- 在 TASK-006 内把超长 TRANSCRIPT Job 标为跳过：违反既有阶段转换归属。
- 只在线程中等待本地模型超时：无法可靠中断卡死推理。

## 后果

- 产品负责人批准后，先创建并完成 `TASK-005A`，再分配 TASK-006/TASK-007。
- 真实模型、服务、ffmpeg 和媒体路径继续使用独立审批，默认离线门禁不得隐式触发。
- 本 ADR 若获批准，需要同步 System Design、Product Decisions、配置示例、任务卡和
  TASK-014 许可证/资源风险；批准本 ADR 本身仍不构成实现或下载授权。
