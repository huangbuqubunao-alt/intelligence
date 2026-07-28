# ADR-018：安全字幕目录来源与结构指纹

## 状态

Accepted

## 日期

2026-07-28

## 背景

未合并的 B-1 B6 evidence `17bfe9062677f3b3117df4dd192848d27690541c` 只能作为只读失败 evidence 引用；不得合并、重写、重跑或表述为通过。
它不授权扩展兼容性、真实验证或响应内容记录。

ADR-017 已冻结 `directory_diagnostic` 的七个固定、无值形状 code，并由 B5 安全 stdout 摘要和既有 JSONL `safe_message`
审计。B6 code 说明已命中的安全诊断，但无法在不记录响应内容的前提下区分失败是在提取器调用、目录解码或目录映射边界发生，也无法
表达有限的结构类别。

## 决策

### D-01：保留 B6 `directory_diagnostic` 原语义与固定值

ADR-017 的 `directory_diagnostic` 保持原有的语义、触发条件和七个固定值，不得重命名、替换、合并或从新标签反推/改写。B7
不新增兼容规则，不改变任何目录响应的接受面。

### D-02：仅为目录 `INVALID_RESPONSE` 提供两个可选、有限、无值标签

只有目录阶段最终安全错误码为 `INVALID_RESPONSE` 时，既有安全 stdout 摘要和 JSONL `safe_message` 可以附加下列可选标签。
它们只表示已命中的本地安全边界；不能携带、拼接或推导响应字段、动态类型、索引、长度或异常文本。

`directory_origin` 词表严格且仅为：

```text
directory_origin_extractor
directory_origin_decode
directory_origin_mapping
directory_origin_unknown
```

`directory_fingerprint` 词表严格且仅为：

```text
directory_fingerprint_top_level_not_mapping
directory_fingerprint_subtitle_bucket_missing_or_not_mapping
directory_fingerprint_language_bucket_missing_or_not_sequence
directory_fingerprint_track_entry_not_mapping
directory_fingerprint_required_field_missing
directory_fingerprint_unknown
```

无法确定安全类别时分别使用相应的 `*_unknown`；没有可靠安全分类时标签可省略。非目录阶段、非 `INVALID_RESPONSE`、成功目录或正文读取
不得输出这两个标签。

### D-03：安全出口与运行边界不变

标签只能附加到既有 B5 安全 stdout 摘要和 JSONL `safe_message`，不新增 JSONL schema、`logging.py`、CLI 参数、配置、Provider
元数据字段或证据模型。不得输出字段名、字段值、URL、字幕正文、标题、语言、轨道名、路径、原始异常、Cookie、token、payload、用户数据
或凭据。

默认与 directory-only 的读取计数、退出码、CLI 边界、临时根、1--3 唯一 ID、无重试、零业务记录和 fail-closed 行为保持不变；不得
因来源/指纹分类放宽身份、URL、格式、长度、数量、语言、条目或目录校验。

### D-04：离线实现与真实验证分离

TASK-014B7 仅允许脱敏 fixture、离线 Fake/integration 测试和静态检查。不得运行 YouTube、网络、真实 smoke、认证、媒体、Vault、模型
或 OpenAI。任何真实验证必须在 B7 实现经独立审查后另行授权；B7 的离线完成不改变 TASK-014 的 `IN_PROGRESS / No-Go`。

## 考虑过的方案

### 记录字段名、字段值、异常或原始目录形状

拒绝。即使看似只描述结构，也可能泄露 URL、标题、语言、Cookie、token、payload 或其他响应/用户数据。

### 用 B7 标签替换或细分 B6 code

拒绝。B6 已是既有安全审计契约；替换会破坏固定诊断的可比性，并把来源信息误写为错误语义。

### 为通过真实目录而放宽解析

拒绝。该做法是兼容性修复而非安全诊断，会削弱 fail-closed 边界，必须独立设计、审查与授权。

## 后果

- TASK-014B7 只可修改字幕 Adapter、`public_subtitle_smoke.py`、一个脱敏指纹 fixture、两份离线 integration 测试和
  TASK-014 handoff。
- 不新增依赖、锁文件、Schema、`logging.py`、CLI 结构、发布状态或真实资源动作。
- `17bfe906…` 保持未合并的只读失败 evidence；不得把 B7 离线实现或其后续真实验证写成发布批准。
