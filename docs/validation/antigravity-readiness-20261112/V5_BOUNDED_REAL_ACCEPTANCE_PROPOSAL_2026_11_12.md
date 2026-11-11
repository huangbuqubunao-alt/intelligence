# v5 有界真实验收方案（待用户批准；当前未授权）

状态：**NOT_AUTHORIZED**。本方案没有执行任何调用。现有 v4-r2 批次已经停止，它剩余的次数和 16 元上限**不作为**本方案的授权。

## 1. 要验证什么

只验证一个假设：恢复 Intelligence 定义和字段语义（v5 契约），并把推理强度从 `low` 调到 `high` 之后，Kimi K3.1 Pro 能否在合适材料上产出真正有价值的正向判断，并在没有新增时诚实返回 NO_NEW。两者都必须通过原冻结标准。

根因与证据见 `ROOT_CAUSE_2026_11_12.md`，评审口径见调用前已冻结的 `V5_ORACLE_ADDENDUM_2026_11_12.md`。

## 2. 固定配置

| 项 | 值 |
|---|---|
| 模型 | `moonshot / kimi-k3.1-pro`，官方端点 `https://api.moonshot.cn/v1/chat/completions` |
| profile | `moonshot-k31-system-synthesis-v5-judgment-20261112`（policy `system-synthesis-v5-judgment`） |
| 变化 | 相比 v4：契约追加通用的“判断定义 / 字段语义 / NO_NEW 判断流程”；`reasoning_effort=high`；`max_completion_tokens=12288`。端点、JSON 模式、5 分钟缓存、300 秒超时、零重试均不变 |
| 输入 | 原 v4-r2 冻结包（manifest `4f399f0d…dcc2`）的同 8 例：2 个公开 YouTube 视频 × en/zh-CN，加 4 个自有合成负控。Source、完整 Summary、refs、兴趣都不变，v5 只替换 system 契约 |
| 私人数据 | 无。只发送公开字幕片段和合成文本 |
| 凭据 | 用户在隔离设置页保存的 QA Keychain 项（`…qa.kimi-public-20261029`），由程序内部读取；不导出、不打印，不进命令行 |
| 控制器 | `scripts/validation/judgment_v5_trial.py`（复用原受控执行核心；旧费用历史按 SHA 只读固定，不修改、不释放） |

## 3. 次数、预算与费用历史

| 阶段 | 次数上限 | 保守预留上限 |
|---|---|---|
| 资格矩阵（8 例，顺序见 §4） | 8 | 10,522,766 µCNY（逐例 1.07–1.85 元，按最大输出 token 计） |
| 合格后的普通界面正向 + NO_NEW 演示 | 2 | 3,698,492 µCNY |
| **本方案合计** | **10** | **14,221,258 µCNY（硬上限 15.0 元保守预留）** |

- 预留按“输入字节数 + 2048”×26 µCNY（含缓存写入的最坏单价）加满额输出 token×68 µCNY 计算。这只是上限，不是实际费用。按 r2 实际用量估算，实际费用大约是预留的 1/3–1/2，具体以账单为准，目前未知。
- 原历史不变：已有 7 次真实调用和 1 个未发送持有槽，保守预留 8.608798 元，实际账单 UNKNOWN。本方案只追加，不清空、不释放旧记录。
- 执行当天调用前重新核对官方价格页。价格上调导致预留超限时，不执行，并重新报告。

## 4. 执行顺序与停止条件

顺序：IwglW-en → IwglW-zh-CN → aircAruvnKk-en → aircAruvnKk-zh-CN → no-new-en → no-new-zh-CN → injection-en → injection-zh-CN。

- 每次只调用一例。拿到结果后先由独立评审（另一个会话，不看本方的预期结论）按原 oracle 和 addendum 给出评审意见，再由 Root 写入决定，下一例才能调用。
- 立即停止的情况：任何技术失败、截断、未知状态；任何事实、归属、Evidence、注入或隐私问题；价值判定 FAIL；**IwglW 任一语言返回 NO_NEW**（正向能力假设在最有空间的材料上被否定）。
- 停止后已发生的费用如实记录；剩余次数**不能**被理解为继续花钱的许可。

## 5. 通过后的动作（同一授权内）

1. 用 8 份真实收据和独立评审生成资格记录，并在冻结代码 hash 下注册（不能手填 `qualified=true`）。
2. 通过隔离候选的普通界面（`--allow-qualified-cloud-execution`，仍需逐次审阅和确认）完成：设置/授权 → 提炼 → 保存 → Topic → Evidence 回跳 → 重启 → Backup/Restore。最多调用 2 次：1 次正向（IwglW），1 次预期 NO_NEW（aircAruvnKk）。
3. 比对全部数据库、DATA 和费用记录，确认没有重复调用或数据丢失。

## 6. 如果不通过

保留全部原始输出和评审记录，不改写输出，也不在事后移动门槛，然后带着新的证据重新诊断。下一步候选方向包括换模型、换服务商，或请用户就产品标准做决定。需要时另行申请授权。
