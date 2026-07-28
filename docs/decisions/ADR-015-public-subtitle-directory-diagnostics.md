# ADR-015：公开字幕目录兼容性诊断

## 状态

Accepted

## 日期

2026-07-28

## 背景

TASK-014 Phase B-1 的唯一真实 evidence
`9acab5d876b38d64a9aeab7aca3474be2676ce38` 证明两个固定公开视频均完成一次元数据读取并启动一次字幕目录调用，
但均在目录响应映射完成前、正文选择/读取前以 `INVALID_RESPONSE` 失败。该 evidence 不保存 URL、正文、标题、字段值、Cookie、token、
完整 payload 或用户数据，因此不能说明是哪一种目录结构假设不兼容。

当前 `YtDlpSubtitleAdapter` 对目录响应执行严格的身份、语言桶、轨道条目、格式、URL 和名称校验；其失败统一映射为
`INVALID_RESPONSE`。`smoke-public-subtitles` 只审计通用错误码和调用计数，不能安全地区分有限的目录结构类别。直接保留
原始响应、异常文本或 URL 会违反 ADR-013 的审计和隐私边界；放宽校验会削弱 fail-closed 保障，均不可接受。

## 决策

### D-01：有限、固定的目录诊断分类

B3 只在字幕目录枚举失败且最终错误码为 `INVALID_RESPONSE` 时，产生一个固定、枚举化的诊断分类。分类只描述校验
分支，不包含字段值、URL、标题、正文、异常文本、请求/响应片段、凭据或用户数据。最低分类集合为：

```text
directory_extractor_parse
directory_identity
directory_bucket_shape
directory_track_shape
directory_track_format
directory_track_url
directory_track_name
directory_no_supported_format
directory_unknown_invalid_response
```

若无法可靠归类，必须记录 `directory_unknown_invalid_response`；不得猜测、拼接动态内容或回退记录原始信息。

### D-02：最小安全审计出口

Adapter 必须把该有限分类作为现有 `ProviderCallMetadata.diagnostics` 的固定 `code` 保存；不得把原始异常或 payload
放入 diagnostic message。`PublicSubtitleSmoke` 仅在目录枚举的 `INVALID_RESPONSE` 失败时，把该枚举 code 附加到
既有 JSONL `safe_message` 的固定键（例如 `directory_diagnostic=<code>`）。这要求对 smoke 审计出口做最小修改，
因为现有账本只写通用 `error_code` 和调用计数。

除上述固定键外，不修改 JSONL 公共字段、默认 CLI、参数、退出码、临时根、调用顺序或正文内存边界。目录成功、其他错误码、
正文读取和无分类情形不得输出目录诊断。

### D-03：校验保持 fail-closed

不放宽 URL allowlist、HTTPS/端口/凭据/fragment 拒绝、身份匹配、语言/条目类型、字段长度、512 条上限或受支持格式要求。
如果 B3 的离线 fixture 表明良性 Provider 变体需要兼容，只允许对该明确形状进行最小规范化；所有未知、危险、缺字段、
超限或不支持格式仍必须失败关闭并产生有限分类。

### D-04：离线实现与真实资源分离

B3 只允许离线 Fake/fixture 和静态审计验证；不运行 YouTube、网络、真实 smoke、媒体下载、认证、真实 Vault、模型或云服务。
未来真实诊断或验证必须另有单次授权、全新临时根、固定目标、脱敏 evidence 和独立审查，不能由 B3 隐含启动。

## 考虑过的方案

### 在 evidence 中保留原始响应或异常

拒绝。可能泄露签名 URL、token、标题或未知响应字段，且与 ADR-013 的脱敏审计契约冲突。

### 只扩大 `INVALID_RESPONSE` 的文本消息

拒绝。动态文本难以审计、容易泄露输入，且不能形成稳定的离线断言。

### 放宽目录校验或记录所有未知字段

拒绝。会降低 URL/结构安全边界，或无必要地扩大数据收集。

## 后果

- TASK-014B3 只实现有限诊断、最小 smoke 审计出口和离线 fixture/test；不改依赖、锁文件、Schema、默认 CLI 或业务流程。
- B-1 的 `9acab5d…` 保持真实 smoke `FAIL` evidence，不合并、不重写为成功，也不触发重试。
- TASK-014 继续 `IN_PROGRESS / No-Go`；B3 离线通过不等于真实兼容性已验证、发布批准或最终 Go。
