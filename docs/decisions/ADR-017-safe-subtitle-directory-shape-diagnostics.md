# ADR-017：安全字幕目录结构诊断

## 状态

Accepted

## 日期

2026-07-28

## 背景

未合并的 B-1 auditable directory-only evidence `c7a3f403c910ab8e50e74f08b1c5ead057a5e4fa` 是基于
`58f0215aa329b99d74429e8616bb5f8f673ef102` 的失败 evidence。它只能作为只读失败输入引用；不得合并、重写、重跑或表述为通过。
该 evidence 的安全摘要可确认目录阶段的固定错误码和 1/1/0 调用计数，但不能安全说明目录响应在何种结构分支失败。

ADR-015 已规定有限、无值的 `directory_diagnostic`，B4 固定 directory-only 零正文边界，B5 固定安全 stdout 摘要。
仍需更细的结构分类来支持离线 fixture、现有安全摘要和既有 JSONL `safe_message`，同时绝不能保存或扩大对目录响应的接受面。

## 决策

### D-01：固定、无值的 B6 目录形状 code

仅当字幕目录阶段最终错误码为 `INVALID_RESPONSE` 时，Adapter 可生成下列一个固定 code：

```text
directory_shape_missing
directory_shape_not_object
directory_shape_not_list
directory_shape_empty_list
directory_shape_unsupported_entry
directory_extractor_directory_error
directory_shape_unknown
```

code 只表示已命中的校验分支；不得拼接字段名、字段值、类型名、索引、长度、URL、异常文本或任何动态内容。若无法以确定的安全分支分类，必须使用
`directory_shape_unknown`。

### D-02：只复用既有安全审计出口

新 code 只可作为既有 `directory_diagnostic` 的固定值进入已存在的安全 stdout 摘要和 JSONL `safe_message`。不新增 JSONL schema、
`logging.py`、CLI 参数、配置、Provider 元数据字段或证据数据模型。成功目录、非目录阶段、非 `INVALID_RESPONSE`、正文读取及无可靠分类时
不得输出 B6 code。

### D-03：解析和运行边界不变

不得因分类而接受先前拒绝的目录形状，也不得放宽身份、URL、格式、长度、数量、语言或条目校验。默认和 directory-only 的读取次数、退出码、
临时根、1--3 唯一 ID、无重试、零业务记录和所有 fail-closed 行为保持不变。兼容修复必须等待独立审查和新的真实授权。

### D-04：离线实现与真实失败 evidence 分离

TASK-014B6 只允许脱敏 fixture、离线 Fake/integration 测试和静态检查。不得运行 YouTube、网络、真实 smoke、认证、媒体、Vault、模型或
OpenAI。`c7a3f403…` 不进入 main，也不被改写为通过；B6 离线完成不改变 TASK-014 的 `IN_PROGRESS / No-Go`。

## 考虑过的方案

### 保存字段名、字段值或异常文本

拒绝。即使看似只保存“结构信息”，也可能暴露响应形状、URL、标题、语言、Cookie、token、payload 或其他用户数据。

### 放宽解析以让真实目录继续执行

拒绝。该做法把诊断任务变成兼容性修复，削弱 fail-closed 边界，并绕过独立审查和新的真实授权。

### 继续只使用 ADR-015 的粗粒度 code

拒绝。它无法区分有限的、可离线断言的目录结构失败分支；B6 的新增 code 保持固定且无值，因此不扩大审计数据面。

## 后果

- TASK-014B6 完整产品范围只可包含字幕 Adapter、`public_subtitle_smoke.py`（将有限无值 Adapter 分类传递至既有安全摘要）、
  一个脱敏结构 fixture、两份离线 integration 测试和 TASK-014 handoff；该传递不新增输出面或放宽解析。
- 不新增依赖、锁文件、Schema、`logging.py`、CLI 结构、发布状态或真实资源动作。
- 任何真实验证、兼容修复、重试、合并 `c7a3f403…` 或发布决定都需要单独授权。
