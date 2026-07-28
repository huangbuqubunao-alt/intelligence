# ADR-019：受限键名级字幕目录诊断

## 状态

Accepted

## 日期

2026-07-29

## 背景

未合并的 B-1 B7 evidence `8f5dfce33ac77a45800f4ff53ff6e7054d8f68b0` 只能作为只读失败 evidence 引用；不得合并、重写、重跑或表述为通过。它不授权解析兼容性修复、真实验证或记录响应内容。

ADR-017 与 ADR-018 已提供固定、无值的目录诊断、来源和结构指纹。在目录映射边界仍为 `unknown` 时，产品负责人明确批准一次受限例外：仅输出经过严格筛选的映射键名，以支持后续离线兼容性决策。

## 决策

### D-01：极窄的触发条件

只有同时满足下列条件，既有安全 stdout 摘要和 JSONL `safe_message` 才可增加可选 `directory_key_names`：directory-only 模式、目录阶段最终安全码为 `INVALID_RESPONSE`、`directory_origin=directory_origin_mapping`、`directory_fingerprint=directory_fingerprint_unknown`，且正文 `read=0`。其他阶段、默认 smoke、成功、正文失败或任一条件缺失时必须省略该字段。

### D-02：全有或全无的有限键名词表

`directory_key_names` 只能是稳定 ASCII 字典序、去重后的键名数组，最多 16 项。每项必须完整匹配 `[A-Za-z][A-Za-z0-9_]{0,63}`；这排除了空白、控制字符、路径分隔符、URL 形态、凭据形态及任意非规范 ASCII。只在 Adapter 的目录映射边界检查直接键名，绝不递归、绝不读取或输出值。

任一候选不合格、去重后超过 16 项，或无法可靠取得完整候选集时，必须 fail-closed：整个 `directory_key_names` 省略；不得截断、部分输出、替换、哈希或记录拒绝项。

### D-03：隐私与行为边界不变

这是“禁止字段名”规则的单次、受限例外，不允许字段值、URL、字幕正文、标题、语言值、轨道值、路径、原始异常、Cookie、token、payload、用户数据或凭据。ADR-017/ADR-018 原有诊断与词表、默认/directory-only 读取计数、退出码、CLI、临时根、ID 上限、无重试、零业务记录和 fail-closed 边界保持不变。

不得因此放宽目录解析接受面、增加兼容规则、变更 Schema、`logging.py`、CLI 结构、默认配置、依赖、锁文件或真实资源权限。兼容性修复必须另行设计、审查和授权。

### D-04：离线实现与真实验证分离

TASK-014B8 只允许使用有限的合成安全键名进行离线 Fake/integration 测试，证明允许、拒绝与上限行为。不得保存或引入真实目录 fixture、URL、身份、语言、轨道或字段值。B8 的离线实现不构成真实 B-1 成功、真实服务验证、发行批准或 TASK-014 Go。

## 考虑过的方案

### 输出原始目录或字段值

拒绝。它会直接暴露响应内容，并可能携带 URL、身份、Cookie、token 或用户数据。

### 在所有 `INVALID_RESPONSE` 输出键名

拒绝。该做法会扩大异常出口，并将非 mapping/unknown 边界的材料写入安全摘要。

### 静默截断超过上限的键名

拒绝。截断会产生不完整的诊断，并可能规避对异常目录的 fail-closed 处理。

## 后果

- TASK-014B8 只可修改字幕 Adapter、`public_subtitle_smoke.py`、两份离线 integration 测试和 TASK-014 handoff。
- 不新增依赖、锁文件、Schema、`logging.py`、CLI 结构、发布状态或真实资源动作。
- `8f5dfce…` 保持未合并的只读失败 evidence；不得把 B8 或任何后续真实验证写成发行批准。
