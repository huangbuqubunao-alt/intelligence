# ADR-021：安全字幕目录契约状态诊断

## 状态

Accepted

## 日期

2026-07-29

## 背景

B10-classified directory-only 真实 evidence
`51d9749943270cb75c2b166e77bce0a5f663d92c` 是
`f00aa9cffa25dcb9b7165edf21a4d476263c1dc5` 的唯一子提交，且只修改获准的三份
evidence 文档。它保持未合并、只读且不得改写为成功。该次固定目标调用在
metadata=`1` / enumerate=`1` / read=`0` 后以 `INVALID_RESPONSE` 停止；安全摘要只产生
`directory_shape_unknown`、`directory_origin_mapping` 和
`directory_fingerprint_unknown`，未产生 B8 键名或 B10 availability 分类。

ADR-017 至 ADR-019 已冻结结构诊断、来源/指纹和一次受限键名例外，但该只读 evidence
仍不能在不暴露真实响应内容的前提下说明失败位于顶层视频标识、人工/自动字幕目录、
字幕桶、轨道条目还是必需成员。下一步需要一个有限、无值、可离线验证的项目内契约
状态矩阵；它只为独立兼容任务提供依据，不放宽当前解析契约。

## 决策

### D-01：固定六字段、固定顺序与封闭值域

B11 的项目内安全摘要对象严格且仅包含以下六个字段，并始终按此顺序表示。字段名是
本项目的契约概念，不是外部响应键名；实现不得枚举、复制或推导任意外部 key。

| 顺序 | 字段 | 固定允许值 |
|---:|---|---|
| 1 | `video_identity_shape` | `missing` / `string` / `other` / `unknown` |
| 2 | `manual_directory_shape` | `missing` / `mapping` / `other` / `unknown` |
| 3 | `automatic_directory_shape` | `missing` / `mapping` / `other` / `unknown` |
| 4 | `caption_bucket_shape` | `not_evaluated` / `absent` / `sequence` / `other` / `unknown` |
| 5 | `track_entry_shape` | `not_evaluated` / `absent` / `mapping` / `other` / `unknown` |
| 6 | `required_members_shape` | `not_evaluated` / `complete` / `missing` / `wrong_type` / `unknown` |

`not_evaluated` 只表示前置契约层未安全到达，不能解释为缺失或错误；`unknown` 只表示该层
已经进入评估，但无法从可信的无值内部状态安全分类。不得把两者互换、把推断写成事实，
或增加自由文本、数字、类型名、数量、顺序、成员名或其他值。矩阵出现时六字段必须完整，
不得按运行时材料增删字段。

### D-02：逐层语义只覆盖项目已知契约

- `video_identity_shape` 只表示项目既有顶层视频身份成员的值形状，不输出成员名或身份值。
- `manual_directory_shape` 与 `automatic_directory_shape` 只分别表示项目既有两类字幕目录
  概念的形状；不得列出目录 key、值、数量或顺序。
- `caption_bucket_shape` 只表示在前置目录为可靠 mapping 后，项目既有字幕桶概念是否未出现、
  为 sequence、为其他形状或无法安全判断；不得输出语言或桶标识。
- `track_entry_shape` 只表示已安全到达的项目既有轨道条目概念是否未出现、为 mapping、为
  其他形状或无法安全判断；不得输出索引、数量、轨道名或字段材料。
- `required_members_shape` 只表示项目既有必需成员集合整体为 complete、missing、wrong_type
  或无法安全判断；不得说明哪个成员缺失或类型错误。

实现只可由 Adapter 内已有校验分支产生无值、封闭的内部状态。不得通过异常字符串、URL、
响应文本、动态类型名、外部字段名/值或任意内容猜测状态。

### D-03：严格输出门禁与既有安全出口

只有下列条件全部同时成立时，既有 B5 每目标安全 stdout 摘要和既有 JSONL
`safe_message` 才可附加完整 B11 状态矩阵：

1. `smoke-public-subtitles --directory-only`；
2. 最终安全错误码为 `INVALID_RESPONSE`；
3. metadata=`1`、enumerate=`1`、read=`0`；
4. B7 `directory_origin=directory_origin_mapping`；
5. 没有读取字幕正文。

任一条件缺失时必须省略整个矩阵。矩阵只能作为既有安全消息中的固定顺序片段出现；
不得新增 JSONL schema 字段、`logging.py` 字段、Provider metadata、CLI 参数、配置、证据模型
或持久化状态。

### D-04：隐私、解析和运行边界保持不变

B11 新增矩阵不得输出或持久化视频 ID 值、任意外部响应键名、URL、标题、语言代码、轨道名、
字段值、数量、顺序、异常原文、原始响应、路径、Cookie、token、payload、用户数据或凭据；
既有 B5 安全目标标识与其他既有安全摘要语义保持不变，不属于 B11 矩阵。B11 不得改变
ADR-017 至 ADR-020 的词表、触发条件或含义，不得替换 B6/B7/B8/B10 诊断。

不得接受此前拒绝的目录形状，不得扩大字幕解析接受面或增加兼容规则。默认 smoke、退出码、
metadata/enumerate/read 计数、默认一次正文读取、directory-only 零正文、无重试、临时根、ID
上限、零业务记录、认证和所有 fail-closed 边界保持不变。

### D-05：离线实现与真实 evidence 分离

TASK-014B11 只能使用无值内部状态，或只含上述项目既有契约概念的合成替身。不得新增、恢复、
读取或复制真实响应 fixture，也不得把 `51d974…` 合并到 source/main。实现、审查和整合均为
独立离线阶段；任何真实 YouTube、网络、真实 smoke、认证、媒体、Vault、模型或云端操作都
需要新的明确授权。

B11 只提供兼容修复依据，不证明真实 smoke 成功、正文可读、yt-dlp 普遍兼容、根因已确认、
发行批准或最终 Go。TASK-014 始终保持 `IN_PROGRESS / No-Go`。

## 考虑过的方案

### 输出原始 key、值、类型名、计数或响应片段

拒绝。这些材料会扩大敏感数据面，并可能泄露身份、URL、语言、轨道、凭据或用户数据。

### 复用 B7 指纹继续细分

拒绝。B7 指纹是既有固定审计契约；改写会破坏历史可比性。B11 应是独立、严格门禁的
项目内状态矩阵。

### 直接修复或放宽真实目录解析

拒绝。当前 evidence 只支持定位诊断，不足以授权新的接受规则。兼容修复必须依据经独立
审查的 B11 证据另建最小任务。

## 后果

- TASK-014B11 最大产品范围仅为 subtitle Adapter、`public_subtitle_smoke.py`、两份离线
  integration test 与 `handoffs/TASK-014.md`；最终 Diff 必须是该允许范围的最小子集。
- 不新增 fixture、依赖、锁文件、Schema/migration、配置、认证、默认 CLI、`logging.py` 或
  日志 schema。
- `51d974…` 保持未合并只读失败 evidence；B11 离线完成不改变 TASK-014 的
  `IN_PROGRESS / No-Go`。
