# YouTube Intelligence 产品操作链路

## 这是什么

YouTube Intelligence 是一个本地优先的 YouTube 内容工作台：它让单个操作者保存要关注的频道或单条视频、设定处理意图和检查计划，并在同一处查看已被当前本地 authority 记录的来源、视频、字幕、可信评分、周报和运行历史。

它不是一个已经获准持续联网、自动处理和自动调用模型的云服务。当前工作台的配置与阅读能力可用；真实的来源检查、处理、周报生成及任何外部副作用仍须经过运行时/运营授权。Deep Analysis 目前全局 `BLOCKED`。

## 当前闭环：配置、记录、复核

当前可见的完整链路应这样理解：

```text
Dashboard
  → Sources：保存 Channel 或 Video URL、策略和计划
  → （经单独运行时授权的检查/处理；当前 UI 不触发）
  → Videos：查看已被记录的视频
  → Video Detail：字幕、Verified Scoring、Note/Deep Analysis 状态、History
  → Weekly：查看已有周报投影
  → Activity：跨来源/计划的运行记录
```

其中“保存 Source”是当前可执行操作；“检查/处理”不是保存后的隐式动作。计划是未来到期工作的配置，不能被理解为永久后台服务承诺。

## 先区分五种产品状态

| 词语 | 产品含义 |
| --- | --- |
| 已设计（DESIGNED） | 有产品或架构设计，不代表可由当前 UI 执行。 |
| 已实现（IMPLEMENTED） | 代码或受控投影存在；仍可能被运行时、资格或运营门禁阻止。 |
| 可用（AVAILABLE） | 当前 authority 能安全读取或当前 UI 能执行该项动作。 |
| 已阻止（BLOCKED） | 系统有明确门禁，不能通过普通用户操作绕过。 |
| 不可用/延期（UNAVAILABLE/DEFERRED） | 当前没有可验证读取链路或刻意未开放；不是把空白当成成功。 |

## 第一次使用的主链路

下面的流程可完成目前真正可做的“建立订阅与理解产品状态”；涉及外部执行的地方会明确停在门禁处。

1. 打开 **Dashboard**。先查看 *Needs Attention*、来源数、已记录视频数、下一项计划、最近运行和 Deep Analysis 卡片。
2. 打开 **Sources**，点击真实按钮 **Add source**。
3. 在 **YouTube Channel or Video URL** 输入显式 HTTPS YouTube URL。支持频道 URL/handle/custom channel，以及 watch、短链、Shorts、live 等可规范化的视频 URL；保存时只在本地校验和规范化 URL。
4. 选择 **Processing policy**：`Discover only` 或 `Standard intelligence`。`Full intelligence — unavailable: no qualified live provider` 处于禁用状态，不能选择。
5. 选择 **Schedule**：`MANUAL`、`DAILY` 或 `WEEKLY`；每日填写本地时间，每周再选择 weekday。界面使用后端定义的时区。
6. 点击 **Save source**。这会创建/复用 Source 并保存一个计划；不会检查 YouTube、处理视频、调用模型或创建运行记录。
7. 回到 Sources，点击该行 **Open**，在 Source detail 中确认状态、策略和计划；必要时用 **Save policy**、**Save schedule**、**Disable source**/ **Enable source** 调整未来配置。
8. 当有经过获准运行路径写入的视频记录时，进入 **Videos**；这不是保存 Source 后必然立即出现的结果。
9. 点击视频行（或在 Source drawer 的 **Recent Videos** 点击一条）打开 **Video Detail**。先看 Overview，再查看 Transcript、Scoring 和 History。
10. 若 Transcript 为 `AVAILABLE`，可读到已记录且通过完整性核验的 canonical transcript；若 Scoring 显示 **VERIFIED SCORING**，才把分数作为可信评分使用。
11. 到 **Activity** 核对跨来源的计划运行；到 **Weekly** 阅读已有周报及其 authority 边界。不要把现有周报视为 Weekly V2。
12. 在 **Settings** 只查看或设置 desired provider preference；这不会配置凭据、使模型合格、启用模型或解除 Deep Analysis 门禁。

## 三个最重要的使用流程

### A. 订阅一个 YouTube Channel

**目的：** 持续关注频道，并为将来的检查配置意图与时间。

1. 在 Sources 点击 **Add source**。
2. 输入频道的 HTTPS URL，例如 `https://www.youtube.com/@...` 或 `https://www.youtube.com/channel/...`。
3. 选择 `Discover only` 或 `Standard intelligence`，再选择 `MANUAL`、`DAILY` 或 `WEEKLY`。
4. 点击 **Save source**。系统只校验/规范化 URL，保存 Source 和计划；相同规范化 URL 会复用现有 Source，而不是产生重复订阅。
5. Source 出现在 Sources 表中。表中显示 Source 类型、策略、最后检查时间和状态；计划详情在 **Open** 后的 drawer 中查看。
6. 若外部检查在获准运行环境执行，新的、已被记录的视频会在该 Source 的 **Recent Videos** 和全局 **Videos** 中出现。当前 UI 没有 **Check now** 按钮；即使调用受控检查路径，默认运行时 guard 也会返回 `BLOCKED`，直到具备明确副作用授权。
7. 失败先看 Sources 的 **Needs Attention** 筛选或 Dashboard 的 attention，再到 Activity 查看该 Source 的相关运行记录。Source drawer 的 Recent Activity 是该 Source 的 scoped run 记录，不是原始日志。

**何时使用 Disable source：** 暂停未来 intake、但保留既有 Source/视频/历史时。禁用不会删除既有资料，也不是“重试失败”的替代。

### B. 添加单个 YouTube Video

**目的：** 只跟踪一条视频，不建立频道持续订阅。

1. 同样从 **Sources → Add source** 进入。
2. 输入单条视频 URL（watch、短链、Shorts 或 live 的受支持形式）。保存后 Source type 为 `VIDEO_URL`，而非 Channel。
3. 选择 `Discover only` 或 `Standard intelligence`，再保存计划。对单视频而言，计划仍是 Source-check 计划的配置；不是“立即分析此视频”。
4. 在 Source drawer 查看该 Source 的 **Recent Videos**。只有当该视频已由受控执行路径记录后，才可点入 Video Detail。
5. 在 Video Detail 按 **Transcript → Scoring → History** 的顺序复核。Note 与 Deep Analysis 目前不提供可读成品，具体原因会明确显示。

### C. 每周自动更新

**目的：** 例如把某个频道检查设为每周日 20:00，并查看已有 Weekly 结果。

1. 在 Add source 或 Source detail 的 **Schedule / Processing** 选 `WEEKLY`。
2. 选择 **Weekday = Sunday**、**Local time = 20:00**，点击 **Save schedule**。当前 week-day 编号以界面显示的 Monday 到 Sunday 为准。
3. 在 **Automation** 查看 cadence、timezone、`ENABLED`/`DISABLED`、Last result 和 Next run。`next run` 是后端按该计划和当前时间计算的下一个未来时点；不等于一项已获授权、必将完成的执行承诺。
4. Automation 中还可能出现目标为 **Weekly Intelligence** 的 weekly-generation 计划。它和 Source check 都是计划记录；Weekly 页面只展示已经存在的 report projection。
5. 真正 scheduler tick 在当前实现中最多领取一次错过的到期项，且不补跑未知历史；若没有显式运行时副作用授权，source check 与 weekly generation 都记录为/返回 `BLOCKED`。UI 也不提供 Run now、launchd 安装或 scheduler 开关。
6. 到 **Weekly** 阅读已有报告。报告的 `UNKNOWN` version、`UNAVAILABLE` Weekly V2 和 `UNAVAILABLE_IN_CURRENT_AUTHORITY` video linkage 必须按原样理解，不应把 Demo report 当成 Weekly V2 交付。

## Processing Policy 手册

Policy 是 Source 的持久化处理意图，不是一次保存时立即执行的命令。当前 workspace 没有把 Source 保存直接接到 YouTube、转写、评分或 provider 调用。

| Policy | 适合谁 | 当前可配置性 | 它表达什么 | 它不保证什么 |
| --- | --- | --- | --- | --- |
| `DISCOVER_ONLY` / Discover only | 只想先收集/观察新内容的人 | 可选、可保存 | 希望先发现和记录内容，不选择智能处理意图 | 不会因保存而检查 YouTube，也不承诺字幕、评分、笔记或周报。 |
| `STANDARD_INTELLIGENCE` / Standard intelligence | 希望在受控处理路径可用时采用标准智能处理意图的人 | 可选、可保存；也是 Settings 显示的默认 policy | 表示标准处理偏好；现有历史视频可显示 transcript 与 verified scoring 等已记录结果 | 当前配置本身不启动任何处理；不包含/不解除 Deep Analysis gate。 |
| `FULL_INTELLIGENCE` | 未来在有 production-eligible provider 且运营批准后需要深度分析的人 | 当前不可选，后端也会拒绝 | 唯一会请求 Deep Analysis 的 policy 语义 | 当前没有 qualified live provider，因此不能保存/执行；绝不等于“选择后必定得到 Deep Analysis”。 |

## Source → Video → Intelligence → Weekly 的真实信息流

1. **Source** 是用户意图：频道或单视频的规范化 URL、启停、policy 和计划。
2. **检查/发现** 只有在受控、获授权的 runtime path 中才可能把视频写为记录；当前 UI 不能自行触发。
3. **Video** 是已记录视频的统一工作区。其 processing status 表示记录中的 pipeline 状态，不是浏览器推断。
4. **Transcript/Scoring** 只在存在可安全读取的 canonical transcript 或可信 `VerifiedScoringRead` 时展示内容/分数。
5. **Deep Analysis** 目前 `BLOCKED`，不能从高分、desired model 或已配置状态推导为可执行。
6. **Weekly** 是已有 Report 的只读投影；当前 authority 不证明 Weekly V2 或视频关联。

## Automation 的角色

Automation 是“把时间和目标保存为计划”的控制面，而不是常驻云调度器：

- `MANUAL`：没有自动计算的 next run；它是一个手动 cadence 记录，并非 UI 提供的立即执行按钮。
- `DAILY`：按本地时区的时间计算未来到期点。
- `WEEKLY`：按 weekday + 本地时间计算未来到期点。
- `DISABLED`：计划保留但不会成为可领取的未来工作。

计划变更只影响未来 due work；不会立即检查、处理、创建 run 或重试。真实 execution 还取决于系统外的运行/运营授权，且本项目不会由 UI 安装、加载或管理 launchd。

## 推荐使用策略

### 轻量：先发现，不处理

为频道选择 `DISCOVER_ONLY` 与 `MANUAL` 或低频计划；用 Sources、Videos 和 Activity 管理已记录内容。适合先建立关注清单。不要期待保存后自动入库。

### 标准：频道追踪 + 已有 transcript/scoring 的复核 + Weekly 阅读

选择 `STANDARD_INTELLIGENCE`，设置 DAILY/WEEKLY 计划，并在获准运行环境产生记录后，从 Videos 打开详情，阅读 `AVAILABLE` Transcript 和 **VERIFIED SCORING**；在 Weekly 只阅读当前 report projection。适合当前最接近“持续工作台”的方式，但 execution 与 Weekly generation 仍独立受 gate 控制。

### 高级：未来 Full Intelligence

只有未来出现 qualified、production-eligible 的 live Deep Analysis provider，且取得 Product Owner acceptance/运行授权后，才应考虑 `FULL_INTELLIGENCE`。现在不要把 desired provider、凭据存在或高分当成绕过门禁的方法。

## 当前能力边界

- 没有 credential setup UI；凭据配置为 `DEFERRED`，Settings 不输入或展示 API key。
- 没有 force-use unqualified model、静默 provider fallback、自动 Deep Analysis retry，或 AMBIGUOUS 自动重试。
- 没有 UI 中的 Check now、Run now、处理/重试、launchd 管理、scheduler execution 开关。
- Note V1 没有已持久化的 authoritative NoteRef 关联时为 `UNAVAILABLE`；Note V2 为 `UNAVAILABLE`。
- Weekly version 在当前 authority 无法证明时是 `UNKNOWN`；Weekly V2 为 `UNAVAILABLE`；Weekly video linkage 是 `UNAVAILABLE_IN_CURRENT_AUTHORITY`。
- 产品是本地、单操作者工作台；不是 public SaaS、multi-user account、remote cloud dashboard 或已发布服务。
- Release posture 是 `NO-GO`；PO Review Demo 是隔离 synthetic data，不是生产环境证明。

## 高级能力状态（管理员/PO）

当前所有 Deep Analysis provider 均不具备 production eligibility：OpenAI adapter/offline path 已合格但 live qualification `0/2` 且 credential-blocked；Kimi production adapter `1/2`、`SCHEMA_INVALID`，因此 unqualified；Local 当前 critical-path candidate unqualified，search closed。`CONFIGURED`、`AVAILABLE`、`QUALIFIED` 和 `PRODUCTION_ELIGIBLE` 是不同状态，用户不能 override trust gate。
