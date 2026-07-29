# ADR-020：安全内容可用性诊断

## 状态

Accepted

## 日期

2026-07-29

## 背景

此前三个不同公开视频的受限 directory-only 验证均完成一次 metadata 和一次字幕目录枚举、零正文读取，随后以固定安全码
`CONTENT_UNAVAILABLE` 停止。B9 未合并 evidence `bd770ef9d212ebe75689b8f33145bf2556fe93c2` 只记录该安全摘要；不得合并、
修改、清理或改写为成功。继续盲目更换样本不能说明失败来自视频不可用、访问环境受限、提取器兼容性不足，还是无法安全确定。

ADR-015 至 ADR-019 已冻结 `INVALID_RESPONSE` 的目录结构、来源、指纹及受限键名诊断。它们不适用于 `CONTENT_UNAVAILABLE`，且
不得用原始响应、异常文本、URL、标题、语言、轨道或字段材料补充判断。

## 决策

### D-01：固定、封闭、无值的可用性词表

仅在受限 `smoke-public-subtitles --directory-only` 路径的最终安全码为 `CONTENT_UNAVAILABLE` 且正文读取 `read=0` 时，既有安全
stdout 摘要和既有 JSONL `safe_message` 可以附加下列一个固定 `content_availability` code：

```text
content_availability_video_unavailable
content_availability_environment_restricted
content_availability_extractor_compatibility
content_availability_unknown
```

Adapter 只可从已有的本地、无值内部状态或固定错误映射分支选择前三者；无法完整且安全地判定时必须使用
`content_availability_unknown`。不得猜测、拼接动态文本、从异常原文/响应/字段/URL 推导，也不得省略 unknown 回退。

### D-02：只复用现有安全出口

code 只可附加到 B5 已有的每目标安全 stdout 摘要和 JSONL `safe_message`，例如现有安全消息中的固定
`content_availability=<code>` 片段。不新增 JSONL schema 字段、`logging.py`、Provider metadata、CLI 参数、配置、证据模型或
持久化状态。

目录 `INVALID_RESPONSE` 的 ADR-015 至 ADR-019 诊断保持原触发条件、词表和语义；不得被 availability code 替换、细分或反推。
默认 smoke、成功、其他错误码、任何正文读取、非受限路径或不可靠分类都不得输出 availability code。

### D-03：解析与运行边界保持不变

不得放宽字幕目录或正文解析接受面，不得改变退出码、重试、metadata/enumerate/read 计数、默认 smoke 的一次正文读取、临时根、ID
上限、零业务记录、默认 CLI、认证或所有 fail-closed 边界。不得输出或持久化 URL、标题、语言、轨道、字段名/字段值、原始响应、异常原文、
路径、Cookie、token、payload、用户数据或凭据。

### D-04：离线实现与真实证据分离

TASK-014B10 只允许无值内部状态/替身与离线 integration 测试；不得新增、恢复或读取含真实或结构化目录材料的 fixture。不得运行
YouTube、网络、真实 smoke、认证、媒体、Vault、模型或 OpenAI。B10 的离线实现只帮助决定下一步，不构成真实验证通过、发布批准或
TASK-014 Go。

## 考虑过的方案

### 继续更换公开视频

拒绝。重复样本不能安全地区分可用性来源，且会扩大真实资源访问而不增加受控的诊断证据。

### 记录原始错误、响应或目录字段

拒绝。该材料可能泄露 URL、标题、语言、轨道、Cookie、token、payload 或用户数据，并突破 B5 的安全摘要边界。

### 复用或改写 B6--B8 的目录 `INVALID_RESPONSE` 词表

拒绝。`CONTENT_UNAVAILABLE` 与目录结构校验失败是不同的安全码和边界；改变既有词表会破坏可比性并扩大其触发面。

## 后果

- TASK-014B10 最大范围仅为既有 subtitle Adapter、`public_subtitle_smoke.py`、两份离线 integration 测试和
  `handoffs/TASK-014.md`；最终 Diff 可以是该允许范围的最小子集，不得为凑范围修改文件。
- 不新增依赖、锁文件、Schema/migration、`logging.py`、默认 CLI、配置、认证边界或真实资源权限。
- B9 `bd770ef9…` 仍是未合并的失败 evidence；TASK-014 保持 `IN_PROGRESS / No-Go`。
