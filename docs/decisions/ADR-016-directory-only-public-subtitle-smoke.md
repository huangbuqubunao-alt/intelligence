# ADR-016：受限 directory-only 公开字幕目录 smoke

## 状态

Accepted

## 日期

2026-07-28

## 背景

TASK-014 Phase B-1 的最终真实 evidence 在两个固定公开视频的字幕目录映射前以
`INVALID_RESPONSE` 停止，正文读取均为零。ADR-015 已将目录 `INVALID_RESPONSE`
安全地归为有限的 `directory_diagnostic` code，但既有 `smoke-public-subtitles`
在目录成功后会按原有发布 smoke 契约读取一份字幕正文。因此它不能用于只验证元数据和
字幕目录的受限诊断。

保留原始响应、URL、标题、字段值、正文、Cookie、token 或异常文本不是可接受的替代方案；
放宽目录校验同样会破坏既有 fail-closed 边界。

## 决策

### D-01：仅限受限 smoke 的显式模式

在既有 `smoke-public-subtitles` 子命令增加布尔 `--directory-only`。该参数不是默认配置、
不是新的顶层命令，也不能被 `check`、`process`、`retry`、`weekly` 或 `doctor` 接受。

默认调用不带该参数时，既有行为不变：元数据一次、字幕目录一次、排序后至多读取一份
正文。带该参数时，每个目标只执行元数据一次和字幕目录映射一次；无论目录成功或失败，
`read_track` 调用数均为零，且不选择、下载、持久化或记录字幕正文。

### D-02：目录失败的固定脱敏分类

仅当目录枚举以 `INVALID_RESPONSE` 失败时，B4 沿用 ADR-015 已批准的固定
`directory_diagnostic=<code>` 输出。不得新增 JSONL 字段、动态文本、原始异常、响应片段或
任何 URL、标题、字段值、正文、Cookie、token 或用户数据。目录成功或非目录失败不输出
该分类。

### D-03：受限解析与原有安全边界不变

`--directory-only` 只能与 `smoke-public-subtitles`、既有不存在的绝对 `--temporary-root`
以及 1--3 个不同的 `--video-id` 组合使用。全局 `--project-root`、`--settings`、`--channels`
在 smoke 路径仍须在 runner/Adapter/临时根初始化前拒绝；超限、重复或不合法 ID 保持既有
使用错误。不得改变 URL allowlist、HTTPS/端口/凭据/fragment 拒绝、身份、语言、结构、长度、
数量或格式的 fail-closed 校验。

### D-04：实现与真实诊断分离

TASK-014B4 只实现并离线验证模式；不运行 YouTube、网络、真实 smoke、认证、Cookie、API key、
媒体、ffmpeg、模型、Ollama、OpenAI、真实 Vault 或用户数据。未来真实 directory-only
执行仍须单次、独立授权，且不因 B4 实现或离线测试通过而获批。

## 后果

- 只允许修改 CLI 解析、`PublicSubtitleSmoke` 的受限组合分支、必要离线 Fake/integration
  测试及 TASK-014B4 handoff；不新增依赖、Schema、默认配置或通用下载能力。
- B3 的固定目录诊断集合和既有安全审计出口直接复用；不修改 Provider Adapter。
- 旧 B-1 evidence 继续是 `FAIL`，且 TASK-014 保持 `IN_PROGRESS / No-Go`。B4 不是发布批准、
  真实兼容性证明或最终 Go。
