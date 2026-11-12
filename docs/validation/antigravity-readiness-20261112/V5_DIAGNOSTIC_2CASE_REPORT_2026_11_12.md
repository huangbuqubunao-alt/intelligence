# v5 首轮 2 例真实诊断结果与 SSE 流式传输修复报告（2026-11-12）

## 1. 授权范围与执行摘要

按用户于 2026-11-12 明确批准的最小诊断范围（仅前 2 例公开案例：`public-IwglW_hIL_g-en`、`public-IwglW_hIL_g-zh-CN`，保守预留上限 `2,512,632` microCNY ≈ 2.512632 元），控制器 `scripts/validation/judgment_v5_trial.py` 在绑定提交 `b754620e45a2eceef09930e133617109b0870dfe`（`binding_sha256 = d6ff443e80ab2e5a16868cb3574031e6bf25e2ba05def1d4fc97ee30598f30aa`）上严格执行了 2 次单发真实调用，随后按停止门禁停机，未触发第 3 例调用。

| 案例 | HTTP / 终态 | 调用次数 | Token 用量（in / out） | 耗时 | 保守预留（microCNY） | 独立评审 / Root 语义结论 |
|---|---|---:|---|---:|---:|---|
| `public-IwglW_hIL_g-en` | `200` / `SUCCEEDED` | `1` | `3,305 / 1,341` | `51,311 ms` | `1,256,238` | 独立评审 `PASS`（0 P0/P1/P2，4 条 P3）；Root `PASS` |
| `public-IwglW_hIL_g-zh-CN` | `null` / `AMBIGUOUS` (`TRANSPORT_OUTCOME_UNKNOWN`) | `1` | `null / null` | `60,577 ms`（网关断连） | `1,256,394` | 未进入语义评审（传输结果未知，保守预留永久保留） |

## 2. 两项核心实证结论

### 2.1 模型语义假设得到正例证实（`public-IwglW_hIL_g-en` PASS）

1. **消除了前序轮次的摘要复述与噪声填充**：`important_new_information: []`、`filtered_noise: []` 均保持合法空数组，不再为凑满字段去翻译新增片段或编造背景噪声。
2. **产出了有证据支撑且超越完整抽取式 Summary 的收敛判断**：
   - `user_relevant_information[1]` 明确从来源宽泛的编程性能宣传收敛出具体可检验假说：显式维护候选状态（uncertainty representation）配合最坏情况查询选择（minimax）可能有助于交互式、查询受限（160 次查询上限）问题，但该价值在更广范围尚未经独立验证。
   - `meaningful_details` 准确保留了 160 次查询上限、猜错向根节点移动的设定边界，明确区分了来源宣传措辞（“extremely difficult / amazing”）与独立验证，未混入 DeepSeek 公司或外部基准。
   - `evidence` 引用 `E01–E03`（`supporting`）与 `E04`（`conditional`），全部合法绑定。
3. **独立评审观察（P3，不阻塞 PASS）**：最具实质新增价值的收敛假说落在 `user_relevant_information[1]`，而 `core_conclusion` 仍偏保守概括。按调用前冻结的 `V5_ORACLE_ADDENDUM_2026_11_12.md` 第 2 节判为 `PASS`。为避免机械堆叠提示词版本，**本轮保持 `system-synthesis-v5-judgment` 契约一字不改**。

### 2.2 暴露并定位非流式（`stream: false`）60 秒空闲连接断连缺陷

1. **精确时间证据**：
   - 本地 `HTTPSConnection("api.moonshot.cn", timeout=300.0)` 配置为 `300` 秒超时，并非本地超时。
   - 第 1 例（英文）耗时 `51.31s`（低于 60 秒阈值 8.7 秒），成功收到 HTTP 200。
   - 第 2 例（中文）在 `2026-11-11T23:46:03.132515Z` 写入分发检查点，于 `2026-11-11T23:47:03.731098Z`（**`60.58s`**）在 `connection.getresponse()` 收到响应头之前被上游网关/CDN 空闲读超时断开连接，落账为 `AMBIGUOUS / TRANSPORT_OUTCOME_UNKNOWN`（`http_status_code = null`，`invocation_count = 1`）。
2. **根因**：v1–v4 使用 `reasoning_effort="low"`（约 5–15 秒返回），`stream: false` 不会触碰 60 秒网关空闲上限；v5 启用 `reasoning_effort="high"` 后，模型内部推理阶段在 `stream: false` 下不向客户端发送任何字节，一旦思考超过 60 秒即被上游网关切断。若不修复，普通用户在真实界面对较长视频点击“提炼 Intelligence”时也会高频遭遇 `AMBIGUOUS` 与预算冻结。
3. **最小修复（复用仓库既有 SSE 解析器，零新提示词版本、零 Schema 改动）**：
   - 保持 `src/youtube_intel/system_synthesis.py` 的 `system-synthesis-v5-judgment` 策略完全不变；
   - 在 `src/youtube_intel/system_synthesis_profile.py` 将活动传输配置更新为 `moonshot-k31-system-synthesis-v5-judgment-stream-20261112`：仅开启官方 Chat Completions 文档支持的 `"stream": true` 与 `"stream_options": {"include_usage": true}`，直接复用 `src/youtube_intel/distillation.py` 已验证的 `_parse_moonshot_sse_stream`（流式消费 `delta.reasoning_content` 保活连接但不落盘推理文本，从末尾 `choices: []` 统计块读取精确 `usage`）；
   - 将原非流式 `moonshot-k31-system-synthesis-v5-judgment-20261112` 保留在 `KNOWN_PROFILE_IDS`，确保 `.var/judgment-v5-runs-20261112/` 中已产生的两份真实诊断库永久可通过 `verify_database()` 与 `Backup/Restore`。

## 3. 持久证据与恢复核验

- 原控制目录：`.var/judgment-v5-control-20261112/`（11 个文件全部 `0o600` 原样保留并已写入 `V5_R1_PINS` SHA256 锁定）。
- 独立评审落盘：`.var/judgment-v5-reviews-20261112/public-IwglW_hIL_g-en.independent.json`（SHA256 `962c96b0df9dbe76d2ed4cc649c7bc5f0bf05085d2ff0fa2565ae14812ea679a`）。
- 离线恢复实测：对 `public-IwglW_hIL_g-en`（`SUCCEEDED`）和 `public-IwglW_hIL_g-zh-CN`（`AMBIGUOUS`）两个真实持久库的离线克隆分别执行 `create_backup -> stage_restore -> confirm_restore`，恢复前后 `87/87` 张 SQLite 表与 `19/19` 个 DATA 文件逐项相等，恢复期间新增模型调用 `0` 次。
- 累计费用台账（只增不减，不释放未知账单）：
  - 接手前历史：7 次真实调用 + 1 个未发送持有槽 = `8,608,798` microCNY；
  - 本轮 v5-r1 诊断：2 次真实调用 = `2,512,632` microCNY；
  - 当前累计：9 次真实调用 + 1 个未发送持有槽 = **`11,121,430` microCNY（约 11.121430 元）**，实际账单 `UNKNOWN`。

## 4. 下一步最小付费验证方案（待用户决策）

工程修复已在离线单测、SSE 流式干跑、历史库回放、严格 `mypy`、Ruff 与前端 Vitest 中全部免费验证通过。为验证流式修复并推进资格闭环，提供两档明确方案供选择：

1. **方案 A（推荐，最省费用的两步走：先只跑前 2 例 `IwglW` 英/中流式验证）**：
   - 调用上限：最多 **2 次**（`public-IwglW_hIL_g-en`、`public-IwglW_hIL_g-zh-CN`）；
   - 保守预留上限：**`2,512,632` microCNY（约 2.52 元）**（按单次实际约 1,300–1,600 输出 token 计，真实花费预计约 **0.35–0.45 元**）；
   - 停止条件：任一例技术失败、`AMBIGUOUS`、语义不通过或返回 `NO_NEW` 立即停止；2 例均正向 `PASS` 后再决定是否继续剩余 6 例资格矩阵 + 普通界面真实闭环。
2. **方案 B（一步跑完完整 8 例流式资格矩阵 + 最多 2 次普通界面真实正向/NO_NEW 验收）**：
   - 调用上限：控制器 8 例 + 普通界面最多 2 例 = 最多 **10 次**；
   - 保守预留上限：控制器 8 例 `10,522,766` microCNY + 界面最多 2 例 `3,698,492` microCNY ≤ **`14,221,258` microCNY（约 14.23 元）**（真实 token 花费预计约 **1.5–2.5 元**）；
   - 停止条件：严格逐例执行独立评审与 Root 门禁，任一例技术/语义失败或 `IwglW` 返回 `NO_NEW` 立即停止，绝不消耗后续额度。
