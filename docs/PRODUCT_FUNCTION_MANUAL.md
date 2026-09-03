# YouTube Intelligence 功能手册

## 阅读前：产品当前能做什么

本手册描述当前正式本地 workspace 的实际 UI/API 投影，不把旧 PRD、Demo 样例或已实现但受 gate 限制的代码写成已开放能力。

产品定位：**面向单个操作者的本地优先 YouTube Intelligence 工作台，用于配置 Source/计划并复核当前 authority 已记录的内容与运行状态。**

当前可直接操作的是 Source、policy、schedule、source enable/disable 与 desired provider preference；当前可阅读的是 Dashboard、Sources、Videos、Weekly、Automation、Activity、Settings，以及 Source detail 和 Video Detail。真正的外部检查、处理、周报生成和 Deep Analysis 不是此 UI 的直接操作能力。

## 5–10 分钟 Quick Start

1. 打开 **Dashboard**，阅读 *Needs Attention* 与 **Deep Analysis** 卡片；它们是状态信息，不是执行按钮。
2. 打开 **Sources**。
3. 点击 **Add source**。
4. 在 **YouTube Channel or Video URL** 粘贴一个显式 HTTPS YouTube Channel 或 Video URL。
5. 在 **Processing policy** 选择 **Discover only** 或 **Standard intelligence**；不要期待选择 Full intelligence，它当前禁用。
6. 在 **Schedule** 选择 **MANUAL**、**DAILY** 或 **WEEKLY**；Daily 填本地时间，Weekly 再选择 weekday。
7. 点击 **Save source**。此刻只保存配置，不检查 YouTube、不处理视频、也不调用模型。
8. 在 Sources 表点击该 Source 的 **Open**，确认 **Overview** 和 **Schedule / Processing**；需要暂停时点击 **Disable source**。
9. 当已有受控运行写入的视频后，到 **Videos** 点击视频行，阅读 **Transcript** 和 **Scoring**。只有 `AVAILABLE` transcript 与 **VERIFIED SCORING** 可作为可读结果。
10. 在 **History** 或 **Activity** 查看运行状态；若有 Weekly 记录，再到 **Weekly** 阅读其报告和 authority 标签。

## 页面导航地图

| 页面/表面 | 主要用途 | 常见下一步 |
| --- | --- | --- |
| Dashboard | 五秒了解来源、视频、计划、运行和 gate | Sources、Videos、Automation、Weekly、Activity |
| Sources | 新增、筛选与打开 Source | Source detail drawer |
| Source detail | 修改 policy/计划/启停；看该来源的视频/活动 | Video Detail、Automation |
| Videos | 所有已发现或已处理视频的统一工作区 | Video Detail |
| Video Detail | 单视频的 transcript、可信评分、Note/Deep Analysis 状态、历史 | Activity / 返回 Videos |
| Weekly | 已有周报投影与边界 | Videos（当前 linkage 不可用时不可由周报跳转） |
| Automation | 所有保存的计划与 next run | Source detail |
| Activity | 跨 Source/Video/Automation 的运行观察 | Video Detail / Source detail（按上下文） |
| Settings | 本地 posture、policy 默认值与 provider qualification | 返回日常工作页 |

## Dashboard

**目的：** 首次进入时建立操作上下文，不是“开始处理”页。

**何时来：** 打开产品、发现异常、想快速确认是否已有计划或结果时。

**关键区域与可做动作：**

- **Needs Attention**：显示后端投影出的有 `last_error` Source 数；点击 **Review activity** 前往 Activity。它不是错误的自动修复按钮。
- **Sources / Discovery**：显示订阅 Source 数；**Open sources** 前往 Sources。
- **Videos / Processing**：显示当前记录的视频数；**Open videos** 前往 Videos。数字是已记录数据，不承诺已经/即将执行处理。
- **Automation / Next Activity**：显示一个启用、非 MANUAL 计划的 cadence、时区和启停；**Open automation** 前往 Automation。它是时间计算信息，不是 scheduler 已获授权的证明。
- **Weekly**：说明它是 read-only report projection；**Open weekly** 前往 Weekly。
- **Recent processing**：列出最近 automation runs；在此看成功、失败、blocked 或 ambiguous 的记录。
- **Deep Analysis**：当前始终是 `BLOCKED`，原因是没有 qualified live provider；没有 fallback/retry/action。

**正常与限制：** 0 sources/0 videos/无计划是正常空状态。Dashboard 的卡片除了导航按钮外都是展示；不能在这里检查、处理、生成周报或启用 provider。

## Sources

**产品概念：** Source 是“我希望关注什么”的配置记录，不是已经被验证的 YouTube 内容，也不是执行结果。

**两类 Source：**

- `CHANNEL`：持续关注频道 URL；将来受控检查可能发现该频道的视频。
- `VIDEO_URL`：只跟踪一条规范化视频 URL；它不是频道订阅。

**关键区域：**

- 搜索框 **Search sources** 按 canonical URL 查找。
- 筛选：**All**、**Active**、**Disabled**、**Needs Attention**。Needs Attention 指 Source 有被后端记录的最后错误。
- 表格显示 Source、policy、Schedule（提示在 drawer 看）、Last checked、Status。
- **Add source** 打开添加窗口；每行 **Open** 打开 Source detail。

### Add source

填写 **YouTube Channel or Video URL** 后点击 **Save source**。保存会：

- 接受受支持的显式 HTTPS YouTube URL，并在本地规范化；不跟随网络重定向。
- 创建或复用对应 Source，默认启用。
- 保存同一表单所选的 SOURCE_CHECK schedule。

保存不会：检查 YouTube、读取凭据、调用 provider、处理视频、创建评分或生成周报。URL 不合法时显示本地 service 返回的 validation error。

### Source 状态怎么读

| 显示 | 含义与建议 |
| --- | --- |
| `ACTIVE` | Source 启用，可被将来的受控 check 考虑。无需动作。 |
| `DISABLED` | 未来 intake 暂停，历史仍保留；如要恢复未来检查，在 drawer 点击 **Enable source**。 |
| `SOURCE_CHECK_FAILED` 或其它 error code | 上次记录的检查失败；用 Needs Attention、drawer Recent Activity 或 Activity 查看，不要靠反复保存 Source 重试。 |
| `Not checked` | 尚无已记录的检查时间；保存配置后常见。它不是失败，也不是已检查。 |

**何时修改计划：** 希望改变未来期望的到期时间时，在 drawer 修改；此操作不能补跑历史或立即执行。**何时查看 Recent Videos：** 需要从某个来源进入已经记录的视频时。**何时 disable：** 不再希望该来源成为未来工作的候选，但不希望删除历史时。

当前 Sources 表与 Source detail 不单独显示每个 Source 的 “next check” 时间；它们显示保存的 cadence 和 Last check。要看后端计算的 **Next run**，请到 Automation。该时间仍是计划计算，不是已授权执行的收据。

## Source detail drawer

点击 Sources 表的 **Open** 后出现 **Source detail**。它有四段：

1. **Overview**：canonical Source URL、`ACTIVE`/`DISABLED`、Last check。这里是只读。
2. **Schedule / Processing**：可在 `Discover only` 与 `Standard intelligence` 间选择并点 **Save policy**；可点 **Disable source**/ **Enable source**；可选 MANUAL/DAILY/WEEKLY 后点 **Save schedule**。`Full intelligence unavailable` 禁用。变更只作用于未来 due work，绝不在保存时启动 check/run。
3. **Recent Videos**：仅列出已持久化关联到该 Source 的最近十条视频。点击一行打开 Video Detail；无关联时显示空状态。
4. **Recent Activity**：该 Source 的 automation run 投影。当前可读；它只显示 source-scoped runs，不能在这里手动执行、重试或编辑历史。

## Videos

**目的：** 所有已发现/已处理视频的统一工作区。它不是 YouTube 的实时搜索页；没有视频时表示没有本地已记录的 video，而不是 YouTube 没有内容。

**何时来：** 想找一条已经出现的内容、比较当前处理状态、或进入视频详情时。

**表格信息：**

- **Video**：标题、来源频道、发布时间；缺失时显示 video ID 或 Date unavailable。
- **Processing**：持久化 pipeline status，如 `DISCOVERED`、`METADATA_READY`、`TRANSCRIPT_READY`、`SCORED`、`COMPLETE`、`DEFERRED`。它反映记录阶段，不能由浏览器推导出“已经全部完成”。
- **Scoring**：`VERIFIED` 只代表有可信验证的评分读取；其它不可用/失败状态不显示为可信分数。
- **Note**：当前通常为 `UNAVAILABLE`，原因见 Note tab。
- **Deep Analysis**：当前 `BLOCKED`，不会因高分改变。

点击整行打开 Video Detail。Videos 页面没有 Process、Retry 或 Analyze 按钮。

## Video Detail

这是单条视频的主要复核表面。标题下显示 video ID 与 pipeline status，随后可切换 **Overview**、**Transcript**、**Scoring**、**Note**、**Deep Analysis**、**History**。tabs 都是读取/切换，不会改变视频。

### Overview

显示该视频的 **Pipeline status** 与 “Controlled local projection” 信任说明。它用于确认正在看的记录，而不是提供完整 YouTube 元数据或执行控制。

### Transcript

**目的：** 阅读当前 authority 已记录的 canonical transcript。

- `AVAILABLE`：系统存在该视频的 canonical transcript artifact，且路径、大小、UTF-8 内容与内容哈希都可安全核验。正文可读，旁边有 Recorded 时间。
- `UNAVAILABLE`：存在的 transcript artifact 当前无法安全读取/完整性核验；不能以文件残留或推测内容替代。
- `FAILED`：Transcript processing 已终态失败，显示安全 failure code；它不是“稍后会自动补齐”。
- `NOT_PROCESSED`（UI 作为不可用状态解释）：还没有 canonical transcript 被记录。不是所有视频都有 transcript。

Transcript 是既有 authoritative/processed data 的受控读取，不承诺当前 UI 可为任意 URL 生成字幕。

### Scoring

**目的：** 只展示可被系统验证的评分，以辅助判断是否推荐 intelligence delivery。

- 页面出现 **VERIFIED SCORING**、数值、Reasoning/evidence、topics 与 `VERIFIED` 时，才有可信评分。它来自当前 product authority 对完整谱系的验证读取，而不是任意 JSON 文件。
- `AVAILABLE` 是 API 数据可读状态；UI 以 `VERIFIED` 明确其评分信任状态。
- `UNAVAILABLE` / `NOT_AVAILABLE`：没有可验证的评分读取，包括“有一份 raw scoring-like artifact”但没有受信任结果的情况。不要把原始 JSON、草稿或数据库分数当成评分。
- `FAILED`：评分没有以 trusted result 完成；显示 failure code，且不显示分数。

技术附注：只有系统通过权威评分读取链路验证的结果才显示为 VERIFIED；仅仅存在评分 JSON 不足以显示分数。

### Note

**目的：** 如有可验证 Note authority 时展示其状态；当前不承诺可读笔记内容。

- **Note V1**：若没有 persisted authoritative `NoteRef` association，状态为 `UNAVAILABLE`，代码为 `NOTE_REF_NOT_PERSISTED`。这是当前可验证读取链路尚未建立的能力边界，不是 UI bug。
- **Note V2**：状态为 `UNAVAILABLE`，代码为 `NOTE_V2_UNAVAILABLE`。没有可由当前 authority 呈现的 Note V2。

用户不能从此页浏览 Vault、补造关联或要求 UI 显示未验证笔记。

### Deep Analysis

**目的：** 清楚呈现高级分析的资格门禁，而不是提供绕过入口。

当前为 `BLOCKED`：没有完成 live qualification 的 production-eligible provider。即使用户在 Settings 选择了 desired provider，或某 provider adapter 存在、显示 `AVAILABLE`，也不等于 `QUALIFIED` 或 `PRODUCTION_ELIGIBLE`。系统不会尝试另一个 provider，也不会使用 unqualified model；用户不能 override trust gate。

### History

**目的：** 理解这一条视频发生过什么，包括排队、阶段状态与 attempts。它与全局 Activity 不同：History 仅是单视频生命周期。

| 状态 | 怎么理解 | 建议 |
| --- | --- | --- |
| `SUCCEEDED` / `COMPLETE` | 该记录的工作完成。 | 继续查看相关 tab。 |
| `PENDING` / `PROCESSING` / `RUNNING` | 已排队或正在处理的历史状态。 | 到 Activity 查看跨计划上下文；不要用 UI 反复创建请求。 |
| `FAILED` / `FAILED_FINAL` / `FAILED_KNOWN` | 有明确失败结论或错误代码。 | 查看 code 与阶段；是否可重试取决于受控运行路径，当前 UI 没有 Retry。 |
| `AMBIGUOUS` | 系统知道请求进入了无法确定结果的状态；provider 可能已收到并执行请求。 | **不要自动或反复重试。** 系统不自动重试，以避免重复请求或重复收费；请保留记录并按受控运营流程处置。 |

`AMBIGUOUS` 绝不是普通 `FAILED` 的同义词。

## Weekly

**目的：** 阅读当前已持久化的周报投影。它不是“立即生成周报”页面。

每条报告显示 ISO 年/周（如 `2026 W36`）、report status、version 和可安全读取的内容。内容不存在或不能安全读取时为 `UNAVAILABLE`，不从 raw Vault 文件回退读取。

必须保留三个边界：

- **Weekly version = `UNKNOWN`**：当前 authority 不能证明 version；不能因内容可读、报告是 Demo，或旧 V1 renderer 存在而标为 V1/V2。
- **Weekly V2 = `UNAVAILABLE`**：当前没有可展示的 Weekly V2 authority。
- **Video linkage = `UNAVAILABLE_IN_CURRENT_AUTHORITY`**：当前不能由报告安全推导/展示视频关联；不要假设每条周报都可跳到视频。

无报告是正常的空状态。Weekly generation 是独立受控写入操作，当前 UI 没有生成按钮。

## Automation

**目的：** 查看已保存的 Source check 或 Weekly Intelligence schedule，不是配置真实后台服务。

表格显示 Type、Target、Cadence、Timezone、State、Last result、Next run：

- `MANUAL`：无定时 next run；也不代表有 Run now 按钮。
- `DAILY`：每天的 Local time。
- `WEEKLY`：weekday + Local time。
- `ENABLED`：计划可成为未来到期候选；`DISABLED`：计划保留但不会被领取。
- **Last result**：该计划最近完成 run 的时间；**Next run**：按设置计算的下一个未来时刻。它们都不是执行授权证明。

当前实现的 scheduler tick 最多领取一次错过的到期项，不对未知历史补跑；但 actual check/weekly generation 仍需要 runtime side-effect authorization。当前 UI 不安装 launchd、不执行 tick、不显示 Run now，也不保证“配置完就会在后台永久自动跑”。

## Activity

**目的：** 全局运行/事件观察面板。它汇总跨 Source、Video 与 Automation 的 run，而不是单条视频的细节日志。

看 **What**（target type）、**When**、**Status** 与 **Result**/error code。`AMBIGUOUS` 会额外提示 provider 可能已收到请求、系统不做自动重试。Activity 不展示凭据、原始 provider 响应或原始日志；也不提供执行/重试按钮。

**与 Video Detail → History 的区别：** Activity 看“系统范围的计划运行”；History 看“一条视频的 pipeline/job/attempt 生命周期”。需要解释某条视频时优先 History；需要发现哪个来源或 weekly schedule 出问题时优先 Activity。

## Settings

**目的：** 查看本地 workspace posture、默认 policy、provider qualification、storage/system 的安全投影；它不是凭据或模型控制台。

**实际可做的操作：** 在 **Models & Providers** 的 **Desired preference** 选择 No preference、OpenAI、Kimi 或 Local。这只保存期望；页面同时明确 **Active production model: None**。它不会启动模型、读取/写入 key、改变模型资格或强制使用该模型。

**不要混淆以下状态：**

| 状态 | 普通语言解释 |
| --- | --- |
| `CONFIGURED` | 用户选择/指定了偏好，或系统已有配置记录。它不是可调用证明。 |
| `AVAILABLE` | 当前环境可发现 adapter/满足基础调用条件的安全投影。它不是质量或正式资格证明。 |
| `QUALIFIED` | 该 provider/model 已通过本产品规定的 qualification。 |
| `PRODUCTION_ELIGIBLE` | 当前允许进入正式产品处理路径。必须同时满足资格和产品门禁。 |

目前 provider 卡显示 adapter availability、credential status、qualification 与 Production eligible。当前没有 production-eligible provider；OpenAI 是 credential-blocked 的 `0/2` live qualification，Kimi 是 `1/2; SCHEMA_INVALID`，Local unqualified/search closed。**Credential configuration: DEFERRED**：UI 没有 API key 输入框，也不应在这里输入 key。

General、Processing Defaults、Storage、Advanced / System、About 是安全/只读 posture。Release posture `NO-GO`、Doctor `NOT_RUN`、Backup / recovery `NOT_RUN` 不等于用户应从本页执行这些操作。

## 统一状态词典

| 状态 | 一句话定义 | 用户要行动吗 | 建议 |
| --- | --- | --- | --- |
| `AVAILABLE` | 当前 authority 可安全读取该项内容/投影。 | 通常不必。 | 阅读并结合来源与时间复核。 |
| `UNAVAILABLE` | 当前没有安全、可验证的读取能力。 | 不要强行绕过。 | 阅读 code/reason；到相关 History/Activity 查看上下文。 |
| `BLOCKED` | 明确 gate 阻止该动作/结果。 | 不能由普通用户解除。 | 接受当前终态或走 PO/运营授权流程。 |
| `VERIFIED` | 结果已通过系统规定的可信验证。 | 可使用结果。 | 仍结合视频语境判断。 |
| `UNVERIFIED` | 有候选/原始资料但未通过可信验证。 | 不作为正式结果使用。 | 等待受控链路产生 verified read；不要把 JSON 当评分。 |
| `UNKNOWN` | 当前 authority 不能证明该属性。 | 不需立即修复。 | 保留未知，不自行标为 V1/V2 或成功。 |
| `ENABLED` | Source 或 schedule 可参加未来已授权工作。 | 视需要。 | 确认时间/目标；不等于已经运行。 |
| `DISABLED` | Source 或 schedule 暂停未来候选工作。 | 按意图决定。 | 要恢复时在 Source drawer 启用。 |
| `PROCESSING` / `RUNNING` / `PENDING` | 记录已排队或处于处理中。 | 不要在 UI 重复提交。 | 看 History/Activity；当前没有手动 retry 控件。 |
| `FAILED` / `FAILED_KNOWN` / `FAILED_FINAL` | 已记录的明确失败。 | 需要理解原因。 | 查看安全 code/阶段；由受控运行流程决定后续。 |
| `AMBIGUOUS` | provider 可能已执行，但结果无法确定。 | 不要自动/反复重试。 | 保留记录并按运营流程处理，避免重复收费/请求。 |
| `COMPLETE` / `SUCCEEDED` | 对应记录的工作成功结束。 | 通常不必。 | 转到结果 tab 或下一工作项。 |
| `DISCOVER_ONLY` | 只发现/记录的 Source 意图。 | 可配置。 | 用于轻量关注；不承诺处理结果。 |
| `STANDARD_INTELLIGENCE` | 标准智能处理意图/默认 policy。 | 可配置。 | 用于未来受控标准路径；保存本身不执行。 |
| `FULL_INTELLIGENCE` | 请求 Deep Analysis 的 policy。 | 当前不可用。 | 不能选择或绕过，等待 provider gate/PO acceptance。 |

## 能力矩阵

| Capability | Current Status | User Can Configure? | User Can Execute? | Result Available? | Key Limitation |
| --- | --- | ---: | ---: | ---: | --- |
| Source subscription | IMPLEMENTED / AVAILABLE | 是 | 保存 Source | 是，配置投影 | 保存不检查 YouTube。 |
| Single video Source | IMPLEMENTED / AVAILABLE | 是 | 保存 Video URL Source | 是，配置投影 | 不等于立即拉取/分析。 |
| Discovery | IMPLEMENTED but runtime-gated | 通过 Source/policy/计划 | 当前 UI 否 | 仅已记录视频可读 | 外部检查需 side-effect authorization；默认 guard block。 |
| Transcript | Read projection AVAILABLE when verified artifact exists | 否 | 当前 UI 否 | 条件式 | 不是每条视频都有；无 canonical/安全读取即 unavailable。 |
| Scoring | Read projection AVAILABLE when verified | policy 可选 | 当前 UI 否 | 条件式 | 只有 verified scoring 可显示；raw JSON 不算。 |
| Note V1 | UNAVAILABLE in current authority | 否 | 否 | 否 | 无 persisted authoritative NoteRef association。 |
| Note V2 | UNAVAILABLE | 否 | 否 | 否 | 当前无可验证读取链路/合格 live 输出。 |
| Deep Analysis | BLOCKED | desired provider 可选，Full policy 不可选 | 否 | 否 | 无 production-eligible qualified live provider，且不可 override。 |
| Weekly | Read-only projection available when report exists | weekly schedule 可保存 | 当前 UI 否 | 条件式 | generation 是独立受控写入；version 可为 UNKNOWN。 |
| Weekly V2 | UNAVAILABLE | 否 | 否 | 否 | 不得由现有 report 推断。 |
| Automation schedule | IMPLEMENTED / AVAILABLE | 是 | 保存计划 | 是，计划投影 | 配置不等于真实常驻执行。 |
| Real scheduler execution | runtime/operational gated | 间接（计划） | 当前 UI 否 | 可能记录 BLOCKED run | 需明确 side-effect/运营授权；不管理 launchd。 |
| Provider/model preference | IMPLEMENTED, read/write preference only | 是 | 保存 desired preference | 是，状态投影 | CONFIGURED 不等于 qualified/eligible。 |
| Credential setup | DEFERRED | 否 | 否 | 否 | 没有 credential UI 或 key 输入。 |

## 看到这些状态怎么办

| 情况 | 代表什么 | 要不要重试 | 去哪里看 | 用户动作 |
| --- | --- | --- | --- | --- |
| Source failed | 上次 Source check 记录了失败。 | 不要通过反复 Save source 重试。 | Sources → Needs Attention；Source detail → Recent Activity；Activity。 | 核对 source 是否应启用、等待受控运行流程。 |
| Video failed | 某视频阶段有明确失败。 | 当前 UI 无 Retry；是否重试取决于受控运行策略。 | Video Detail → History。 | 记录 error code/阶段，按运营流程处置。 |
| Transcript unavailable | 没有 canonical transcript，或它不能安全读取。 | 不要假定可从网页补出。 | Video Detail → Transcript / History。 | 接受不可用或等受控处理路径。 |
| Scoring unverified/missing | 没有可信评分读取；原始 artifact/草稿不算。 | 不要把它当正式分数重试/使用。 | Video Detail → Scoring / History。 | 等待 verified result；无 UI 强制评分。 |
| `AMBIGUOUS` | provider 可能已收到并执行请求，结果却无法确定。 | **绝不建议自动或反复重试。** | Video Detail → History；Activity。 | 保留记录并走受控运营处置，防止重复请求/收费。 |
| Deep Analysis blocked | 没有 production-eligible qualified live provider。 | 否。 | Video Detail → Deep Analysis；Settings。 | 无用户侧绕过；等待资格与 PO acceptance。 |
| Weekly `UNKNOWN` | authority 不能证明报告 version。 | 不适用。 | Weekly。 | 按 UNKNOWN 阅读，不标为 V1/V2。 |
| Note unavailable | Note V1 缺 NoteRef；Note V2 当前无 authority。 | 不适用。 | Video Detail → Note。 | 不是 UI bug；当前不能查看内容。 |
| Provider not production eligible | adapter/偏好/环境状态不足以进入产品路径。 | 不可由用户重试资格。 | Settings。 | 不要输入 key 或 force-use；等待合格 provider/授权。 |

## 当前不支持/尚未开放

- credential setup 或 API key 输入；
- 强制使用 unqualified provider/model；
- 静默 provider fallback、自动模型切换、自动 Deep Analysis retry；
- 从 `AMBIGUOUS` 自动或反复重试；
- UI 中的 Check now、Run now、Process、Retry、Weekly generate；
- Note V2、Weekly V2、可正式执行的 Deep Analysis；
- public SaaS、multi-user account、remote cloud dashboard；
- UI 管理 launchd、部署、发布或远程 scheduler。

## PO Demo 的正确使用方式

PO Review Demo 是只绑定 loopback 的 synthetic fixture 环境：5 个 Source、12 个视频、2 个 generic weekly report、4 个 automation record，以及成功、失败、blocked、AMBIGUOUS 样例。它不会加载真实 settings/credentials/Vault/provider/YouTube/scheduler execution。

推荐演示样例：

- Source drawer：**Practical AI Engineering**；
- Verified scoring/Transcript：**How teams turn AI roadmaps into decision systems**；
- 未验证评分样例：**A rough scoring draft without a trusted result**；
- AMBIGUOUS：**Provider result uncertain after an interrupted request**；
- Weekly：`2026 W36`，保留 UNKNOWN/V2/linkage 的真实边界。

Demo 中出现的报告、分数或历史只能证明该 UI 正确呈现 synthetic authoritative projection；不能证明真实外部执行已获授权或 Deep Analysis 已可用。

## 常见问答

**保存 Source 后为什么没有马上出现视频？** 保存只做本地 URL 校验、Source 与 schedule 配置。发现/处理必须经单独获授权的 runtime path。

**为什么 Full intelligence 灰掉？** 它请求 Deep Analysis，而当前没有 qualified、production-eligible 的 live provider；这是产品 gate。

**为什么有评分草稿却没有分数？** 只有已验证的评分结果可展示为 VERIFIED；原始 JSON 或类似 artifact 不具备可信读取资格。

**为什么 Weekly 有内容但 version 是 UNKNOWN？** 报告内容可安全读取并不证明其 version。当前 authority 不足以标为 V1 或 V2。

**我能否在 Settings 填 API key 后开始分析？** 不能。没有 credential UI，且 key/desired preference 不能绕过 qualification 与 production-eligibility gate。
