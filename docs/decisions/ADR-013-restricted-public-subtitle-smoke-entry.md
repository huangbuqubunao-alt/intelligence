# ADR-013：受限公开字幕 smoke 组合入口

## 状态

Accepted

## 日期

2026-07-26

## 背景

TASK-014 Phase B-1 的 blocker evidence `be230490a5b5779c7f1eb1e46c0fd717055fc28c` 证明：现有
`check/process/retry/weekly` 只通过外部注入的 `Operations` 组合服务运行，默认实现刻意 fail-closed；它们也不能
将一次真实调用限定为单个公开视频的元数据读取、字幕目录读取和一条选中字幕正文读取，或保证使用新的临时
SQLite/DATA/测试 Vault 根。直接调用 yt-dlp Adapter 或临时脚本会绕开项目入口、审计和根目录边界，不可接受。

产品负责人已经授权受限的公开发布 QA，但不授权通用下载、媒体、认证、模型、云调用或真实 Vault。该场景形成新的、
可观察的 CLI 行为，必须先冻结契约，不能通过放宽默认 `process` 或 ad-hoc 脚本实现。

## 决策

新增一个独立的 CLI 子命令：

```text
youtube-intel smoke-public-subtitles \
  --temporary-root ABSOLUTE_NEW_EMPTY_DIR \
  --video-id ID [--video-id ID] [--video-id ID]
```

### S-01：显式、有限的输入

- 只接受 1–3 个相互不同、通过既有 YouTube ID 规则校验的 `--video-id`；不接受 channel、URL、playlist、
  glob、stdin 或自动发现输入。
- `--temporary-root` 必须是调用前不存在的绝对路径。命令只可创建该根与其中固定的 `state.sqlite`、`data/`、
  `test-vault/`、`logs/`；不得接受或复用既有项目 `data/`、`logs/`、Vault 或用户路径。
- 命令不读取 YAML、`.env`、环境变量值、Keychain、Cookie、浏览器 profile、API key 或登录态。

### S-02：唯一允许的执行图

对每个 ID，顺序只允许：`YtDlpMetadataProvider.fetch` → `YtDlpSubtitleAdapter.enumerate_tracks` → 按既有
`rank_subtitle_candidates` 选择第一条候选 → `read_track` 一次。Adapter 已有的 `skip_download`、无 Cookie、
无 remote components、无媒体/字幕文件写入防护必须保持。

- 固定 HTTP timeout 为 30 秒；每个目标的每一步最多一次，不调用 `retry`，不执行并发或替换目标。
- 任何失败只生成安全错误类别和审计结果；不得自动重试、转入完整 Pipeline、下载音频/视频/缩略图，或调用
  ffmpeg、Whisper、Ollama、OpenAI、付费服务、launchd、Knowledge Sink 或 Weekly Reporter。
- 选中字幕正文只在内存中读取后立即丢弃：不能写入 SQLite、DATA、JSONL、Vault、异常或提交证据。临时 SQLite
  只初始化既有 migration 以验证隔离根，且不创建 Pipeline/Job/ProviderCall/Artifact 业务记录；测试 Vault 只作
  空根边界验证，不写入笔记。

### S-03：审计、退出与默认安全性

- 每次命令必须使用 UUID4 `run_id` 写入临时根内的 JSONL；只允许记录 run ID、视频 ID、阶段、结果、错误码、
  调用计数和耗时，不得记录字幕正文、临时 URL、绝对路径、密钥或用户数据。
- 复用 ADR-011 的 exit code：`0` 全部目标完成，`1` 有已执行目标失败，`2` 参数/前置条件失败，`3` 临时根或
  SQLite 本地资源失败；部分失败不得伪装成功。
- `check/process/retry/weekly/doctor` 的解析、注入式 `Operations` 边界和默认 fail-closed 行为不得修改。

### S-04：范围与发布门禁

不新增依赖、不修改 `pyproject.toml`/`uv.lock`、Schema/migration、领域公开契约、Repository/Pipeline/Job
语义或项目自身 LICENSE。该入口仅供发布 QA；运行成功不是发行批准、法律结论、严格 exactly-once 证明或风险接受。
`mutagen` GPL 分发、BPE 文件级归属/NOTICE、真实 Vault、at-most-once 风险签署和 PO/TL/QA 最终 Go-No-Go
继续为 TASK-014 的 No-Go 门禁。

## 考虑过的方案

### 复用 `check` 或 `process`

拒绝。两者是通用编排表面，默认无组合根时 fail-closed，且不能承诺不进入后续 Pipeline、写既有根或扩大到多个
目标/重试。

### 临时脚本或直接调用 Adapter

拒绝。会绕过生产入口、临时根初始化、脱敏审计与可审查的 CLI 契约。

### 修改 Schema 保存 smoke 历史

拒绝。发布 QA 证据不需要持久业务状态；临时 JSONL 与提交后的脱敏文档足够，避免改变已接受的 Schema。

## 后果

- B-0 以窄 CLI + 专用组合模块 + 离线 Fake 测试实现；真实网络不属于 B-0。
- B-1 的未合并 blocker evidence 保持为审计输入；不被 cherry-pick、merge 或改写。
- 未来真实 B-1 运行必须在 B-0 审查、整合及独立运行授权后进行，仍受单次、最多三目标和所有资源红线限制。
