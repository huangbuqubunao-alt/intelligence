# ADR-006：字幕获取、规范化与缓存契约

## 状态

Accepted

## 日期

2026-07-15

## 批准记录

产品负责人于 2026-07-15 在主控对话中明确批准：

```text
批准 ADR-006 T-01 至 T-15 推荐方案；TASK-005 不新增 Schema/migration，不修改 state.py 或 complete_stage。真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍不授权。
```

批准范围为本 ADR T-01 至 T-15 的完整契约，包括“不新增 manifest Schema”和“不修改 Repository 完成语义”。该批准冻结设计，不构成 TASK-005 worktree、Implementer、依赖安装、网络下载、真实内容或文件写入授权；TASK-005 在 TASK-004 `DONE` 和正式分配包完成前保持 `BLOCKED`。

## 背景

PRD 已批准“人工字幕 > 自动字幕 > 本地 Whisper”，但尚未冻结语言匹配、格式选择、规范化、质量阈值、返回对象、缓存失效和文件恢复细节。若这些细节留给 Implementer 临时决定，会导致公共领域对象漂移、重复下载、失败与“需要转写”混淆，或为缓存复用过早修改 SQLite Schema。

TASK-005 应直接复用 TASK-004 已锁定的 `yt-dlp[default,deno]==2026.7.4` 和 Python 标准库，不另写 YouTube 字幕协议，也不让第三方工具拥有本项目的领域、状态或文件边界。

## 已批准决策

### T-01：候选全局顺序

候选稳定排序为：来源类型、配置语言顺序、语言匹配等级、规范化实际语言、格式、规范化轨道名称、Provider 原始位置。所有人工字幕候选先于所有自动字幕候选；人工的较低语言偏好仍先于自动的较高语言偏好。首个候选无效时继续下一个，直至成功或候选耗尽。

### T-02：语言匹配

语言标签比较时大小写不敏感、`_` 等同 `-`，不新增 BCP-47 依赖。对每个配置语言依次匹配：规范化精确标签、基础语言轨道、同基础语言的地区/脚本变体；变体按规范化实际语言字典序稳定排序。产物保留 Provider 返回的实际语言值，不以 TASK-004 的 `available_languages` 代替轨道重查。

### T-03：允许格式与稳定优先级

字幕格式只允许具名 `SubtitleFormat.JSON3`、`VTT`、`SRT`，同一语言按 JSON3、VTT、SRT 选择。临时 URL 不参与排序，不进入 SQLite、日志或异常。不得调用 ffmpeg、subprocess、Cookie、登录态、`.netrc` 或 remote components；只读取被选中的字幕正文，不下载音频、视频、缩略图或其他媒体。

### T-04：具名结果联合

`TranscriptProvider.fetch` 返回 `TranscriptFetchResult = TranscriptReady | TranscriptionRequired`：

- `TranscriptReady(outcome="ready", artifact, call)` 表示已有可供下游使用的规范文本。
- `TranscriptionRequired(outcome="transcription_required", reason, call, attempted_track_count)` 只表示无轨道、无匹配语言或全部候选无效。
- `TranscriptionReason` 固定为 `NO_TRACKS`、`NO_MATCHING_LANGUAGE`、`ALL_CANDIDATES_INVALID`。

网络、权限、配置、本地资源、内容不可用和 Provider 非法响应继续使用既有 `AppError`，不得伪装成普通转写需求，也不得新增 `ErrorCode`。

### T-05：最小公共对象扩展

公共契约新增 `SubtitleFormat`、`TranscriptQualityFlag`、`TranscriptionReason`、`TranscriptReady`、`TranscriptionRequired` 和 `TranscriptFetchResult`，不得使用自由 `dict`、`Any` 或宽 `object`。`TranscriptArtifact` 在保留现有字段的基础上新增：

- `requested_language: str | None`：字幕来源时为触发匹配的配置语言；Whisper 或无单一匹配语言时允许 `None`。
- `source_format: SubtitleFormat | None`：人工/自动字幕必须存在；Whisper 允许 `None`。
- `source_content_hash: str`、`source_byte_count: int`：原始来源产物的 SHA-256 与字节数。
- `normalization_version: str`：规范化与质量规则版本。
- `quality_flags: tuple[TranscriptQualityFlag, ...]`：替代自由字符串。

`TranscriptQualityFlag` 固定为 `ROLLING_CUES_DEDUPED`、`SPEAKER_LABELS_PRESENT`、`NON_SPEECH_MARKERS_PRESENT`。它们只记录通过质量门禁后的非失败诊断；空文本、非法 UTF-8、过短、乱码比例、重复率、压缩比或资源上限失败必须切换候选，不能作为 `TranscriptReady` 的 flag 继续下游。

Provider 调用元数据放在 `TranscriptReady.call` / `TranscriptionRequired.call`，不把 SQLite artifact key、临时 URL 或绝对路径塞入领域对象。现有 `text_path`/`timed_text_path` 分别指向安全 DATA-relative 的规范文本/原始字幕。

### T-06：确定性规范化

只接受严格 UTF-8，允许 UTF-8 BOM；非法字节不得静默 replacement decode。行尾统一 LF，HTML entity 解码一次，Unicode 使用 NFC 而非 NFKC。VTT/SRT 删除 header、时间行、cue ID、STYLE、REGION、NOTE 和受支持样式标签；JSON3 只读取已验证的 event/segment 字段。cue 内换行折叠为空格，cue 间保留一个 LF，非空文件以一个 LF 结尾。

### T-07：语义保留与滚动字幕

显式 speaker label 保留为 `Speaker: text`；音乐/音效标记保留，但 marker-only 内容不计入最低有效长度。连续完全重复 segment 删除；当前文本以前一文本加词边界为前缀时只保留新增后缀。不使用模糊编辑距离或会改变语义的重写。

### T-08：质量与资源阈值

冻结以下 V1 数值：原始正文最大 `5_000_000` bytes；规范文本最大 `1_000_000` Unicode code points、`100_000` segments；最少 `20` 个非空白且非纯音乐/音效标记字符；U+FFFD 占非空白字符比例大于 `1%` 判无效；去重/滚动删除比例达到 `80%` 判异常；原始正文至少 `10_000` bytes 且规范 UTF-8 bytes / raw bytes 小于 `1%` 判异常。超过硬阈值的候选无效并尝试下一候选；全部无效才返回 `ALL_CANDIDATES_INVALID`。

### T-09：分层幂等键

原始请求键包含 `video_id`、有序语言偏好、selection policy version、format policy version、Provider/版本和显式 refresh generation。规范文本键包含 raw content hash、source format、normalization version 和 quality policy version。规范化规则变化只使 canonical 缓存失效，不强制重新下载原始字幕；与字幕无关的 Pipeline 版本变化也不强制重新下载。

### T-10：文件写入与恢复

原始字幕使用 `ArtifactKind.SUBTITLE_SOURCE`，规范文本使用 `ArtifactKind.TRANSCRIPT_CANONICAL`；两者均为 `StorageRoot.DATA`、`LONG_LIVED`、`expires_at=None`。路径位于 `transcripts/<video_id>/<request_hash>/`，只保存安全相对路径。文件在同目录临时写入，边写边限流并计算 SHA-256，随后 flush、fsync、原子替换并 fsync 父目录；SQLite 不保存字幕正文。

文件成功而 DB 失败时保留确定性文件，下一 attempt 验证哈希后补索引；DB 记录存在但文件缺失/哈希不符时返回 `LOCAL_RESOURCE` 并停止推进；不得相信未验证的缓存。

### T-11：错误与重试

- 无轨道、无匹配语言、全部候选无效：分别返回具名 `TranscriptionRequired`，不作网络重试。
- 刚成功枚举的临时字幕 URL 返回 403/404：`TRANSIENT_NETWORK`、retryable；下一 Job attempt 必须重新枚举 URL。
- 轨道目录 401/403：`PERMISSION_DENIED`、nonretryable。
- 429：`RATE_LIMITED`，尊重有效 `Retry-After`。
- timeout/连接中断/短读：`TRANSIENT_NETWORK`；5xx/临时 Provider 不可用：`PROVIDER_UNAVAILABLE`。
- 非法轨道 payload、危险 URL 或不支持格式：`INVALID_RESPONSE`、nonretryable。
- 已删除/私有/地区不可用：`CONTENT_UNAVAILABLE`、nonretryable。
- 磁盘不足、缓存哈希不符：`LOCAL_RESOURCE`；DATA 边界或写权限失败：`PERMISSION_DENIED`；非法配置：`CONFIG_INVALID`。

Provider 不实现全局退避；应用层沿用最多 3 attempts、base 2 秒、max 60 秒、jitter 0.2 和 HTTP timeout 30 秒。

### T-12：复用与依赖边界

直接复用已锁定的 `yt-dlp[default,deno]==2026.7.4` Python API 枚举轨道和读取选中字幕正文，解析、规范化、哈希和原子文件操作使用 Python 标准库；TASK-005 不新增或升级生产依赖，不修改 `pyproject.toml`/`uv.lock`。附件 skill 与 `yt2md` 只按 ADR-005 `ADAPT/REFERENCE` 使用测试思想，不复制其 subprocess、ffmpeg、代理、远程 API、密钥或 Vault 写入架构。

### T-13：V1 不新增 manifest Schema

拒绝只读 Scout 提出的 `transcript_manifest` ArtifactKind/migration。V1 使用现有两个 Artifact kind、稳定 artifact key/relative path、Provider-call 记录和经验证文件重建所需元数据；语言、来源、格式和版本以可逆、安全且有版本的编码进入 key/path 约定，字符/segment 计数由 canonical 文件确定性重算。若实现证据证明这些信息仍无法无歧义恢复，停止 TASK-005 并另开 Schema ADR，不得在本任务内临时加 migration。

### T-14：V1 不修改 Repository 完成语义

拒绝为 TASK-005 新增 job-neutral Artifact 或“把旧 Artifact 重新绑定新 Job”的 Repository 语义。首次成功仍以当前 Job 写入两个 Artifact 并完成 Provider call；缓存命中时先通过 `get_artifact_by_key` 和文件 SHA-256 验证既有产物，再以 `complete_stage(artifacts=(), provider_call=None)` 原子推进当前 Job/Pipeline。不得修改 `state.py` 或 migration。若集成测试证明该路径不成立，停止并升级新 ADR。

### T-15：远端变化只由显式 refresh 触发

普通缓存命中不联网探测远端字幕变化。显式 refresh generation 生成新的 request hash/path，并重新枚举轨道；旧 Artifact 保留审计记录，不原地覆盖。V1 不做后台 TTL 探测。

## 不采用的方案

- 新增 `youtube-transcript-api`：与现有 yt-dlp 能力重复，只有正式证据证明 yt-dlp 路径不足时才重新申请依赖审批。
- 新增 `transcript_manifest` migration：当前可由稳定 key/path、Provider call 和文件重算满足 V1，Schema 成本与并行冲突不成比例。
- 修改 `complete_stage` 绑定旧 Artifact：会改变已验收的 TASK-003 Repository 语义；缓存命中可使用空 Artifact 完成路径。
- 整套复用外部字幕/Obsidian 应用：会绕过本项目的领域、恢复、隐私、路径和审计边界。

## 后果

- TASK-005 预计只修改领域契约、字幕 Service/Adapter、固定夹具、测试和 handoff，不修改 Schema、state、依赖或锁文件。
- 离线测试必须覆盖完整选择矩阵、边界阈值、原子文件恢复、Provider-call/Artifact 缓存、空 Artifact stage completion 和敏感信息脱敏。
- 真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥继续未授权。
- 本 ADR 已接受，但 TASK-005 仍须等待 TASK-004 `DONE`、最新 main worktree/分支分配和任务级命令/网络授权。
