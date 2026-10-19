# Tracked Content retry：040 执行与恢复补充合同

2026-10-19。配合原迁移提案及 root 2026-10-18/19 的取消、真实 preparation attempt 和事件预算决定。040 尚未正式采用；没有正式040历史需要兼容。保留原三表、128条事件上限、旧34–39全部领域行及DATA；不新增依赖、不签发模型资格。

## 执行和读取

- worker持稳定store SH + request EX直到同步字幕adapter返回、文件结清及终态持久化。暂停在preHTTP事务先赢时不调用该网络方法；已开始的同步方法不假称能撤回。每次取得writer增加epoch；过期lease本身不证明旧writer已退出。
- 首次真正网络方法前，在同一事务追加`DISPATCH_INTENT`（ACQUIRING→ACQUIRING、相同epoch、action=null），再把dispatch改为`DISPATCH_INTENT_DURABLE`。后续候选body方法复验authority，不再重复marker。无marker的NOT_DISPATCHED可恢复；已有intent且无法证明结果时AMBIGUOUS，不重发。
- job成功只表示字幕持久化。timed、Evidence、extractive Summary及完整completion另行验证；失败只进入本地ATTENTION，最多3次local attempt。原文、文件意图与buffer均保留，不创建SourceRun成功、不执行评分/洞察/ASR/Cloud。
- reader重放固定typed事件/action/hash/epoch，复验旧job全行、真实attempt、source/video/channel/ENROLLED和全部冻结参数；验证每个provider、target attempt、文件producer/实际bytes与完成证据。Backup再做正反向所有权、精确040 Schema和全DATA闭包。
- 明确收到的typed adapter失败，在抛出前同事务持久化provider FAILED_FINAL及FAILED_KNOWN；不确定异常/超时走BaseException，不写known。若在执行终态前中断，恢复只结清既有known receipt，保留原错误code/message。若在known receipt前中断，仍是未知并关闭重发。
- API的action按不可变request验证Content归属，不依赖“当前最新request”。新child产生后，同command重放旧取消仍返回旧receipt；错Content在任何写入前拒绝。action历史重放也完整验证provider/files/completion。

## 本地次数的事件证明（最终窄返修）

- `tracked_retry_store._verify_events()`始终从0顺序重放次数，所有阶段的execution投影次数及`CLOSE_HISTORY_LIMIT`输入次数必须等于重放值。纯heartbeat允许revision增加但不得消耗次数；不能据当前投影反推历史容量分支是否合法。
- 新普通开始事件为`LOCAL_ATTEMPT_STARTED`（FINALIZING→FINALIZING），实际本地工作前同事务提交。新单槽容量结果为`LOCAL_INLINE_ATTENTION`或`LOCAL_INLINE_COMPLETED`（FINALIZING→ATTENTION/SUCCEEDED），实际本地工作后与结果和次数同事务提交。三个事件均必需唯一`local_attempt`对象，精确字段为`phase,before,after`；phase严格字符串`START`或`INLINE_RESULT`，before/after严格整数（拒bool/浮点），分别等于重放前次数和该次数+1。缺失、额外字段、错phase/epoch/状态/action、超过3次均拒绝。
- INLINE_RESULT仅允许已有历史的事件数`i`满足`i + 4*(3-before) + 2 > 128`；`i`是结果前事件数，before仅来自已验证历史。未开始的普通COMPLETED或无见证旧容量结果不构成本地次数证明。普通失败结果须对应同owner已开始的attempt；不消耗次数的合同不可用ATTENTION仍保留原行为。
- 兼容边界：34–39不变；候选040旧普通开始事件（同epoch、FINALIZING→FINALIZING的RECOVERED）可确定重放，正常历史保留。旧040容量inline没有充分开始/次数证明，拒绝读取但原记录/文件保留，不回填或伪造见证。040尚未正式采用，无正式数据迁移需求；新事件名使删除新START/INLINE_RESULT见证不能伪装成旧事件。
- 固定反控包括：各阶段count±1、合法无事件heartbeat、所有新见证缺失/坏类型/多字段/错phase/epoch、重放count=1时容量阈值前后117/118/119条、旧普通开始正控/旧无证明inline拒绝、100+真实中断及全部3次真实本地失败。严格保持128/3，原错误/文件、Budget/Cloud和资格不变。


## 三种独立旧失败证明

1. 初始generic：固定五项错误白名单、同码真实最后FAILED_FINAL attempt、终态job/lease及原有全部准入条件。不扩名单。
2. 本协议attempt0：不可变父request+精确CANCELLED/FAILED事件。取消必须有CANCEL_BEFORE_DISPATCH receipt；只允许原本本地前置条件错误。父target、epoch、时间、lease及message匹配；无任何provider、dispatch、attempt、artifact或file intent。新command持父request EX；旧终态不改、最初oldjob不重复消费。
3. 本协议真实preparation attempt1：仅下述HISTORY_LIMIT_CLOSED receipt证明NOT_DISPATCHED、无DISPATCH_INTENT marker、无artifact/files，target及唯一真实attempt以CAPABILITY_UNAVAILABLE同码结清；provider唯一attempt1为匹配冻结request的FAILED_FINAL/FAILED_KNOWN，owner/lease空。保留真实attempt1，不当作attempt0；未知、已dispatch、错receipt/epoch/attempt/provider、缺marker/父记录、活跃writer均关闭。

父链由`verify_old_failure()`迭代遍历，不递归、不截断。每个祖先都检查完整请求、历史source与其前任证明；重复祖先拒绝。1051条合法取消历史可读取和新建command，中间祖先receipt被删仍拒绝。所有分支同command幂等。

## 容量终态receipt

新事件`HISTORY_LIMIT_CLOSED`只在FAILED/AMBIGUOUS终态使用，action operation=`CLOSE_HISTORY_LIMIT`。action保持原六字段；input严格包含：

`request_id, operation, command_id, expected_revision, prior_state, prior_epoch, dispatch_status, target_status, attempt_count, provider_attempt_count, local_attempt_count, had_dispatch_intent`。

command_id为`history-limit:`加不含command_id的上述输入canonical hash。输入hash、revision、epoch、state、真实attempt计数、前序marker与最终provider/job状态全部复验。关闭前必须已取得实际request锁并结清文件，不能凭lease猜执行结果。NOT_DISPATCHED结清可走独立第三分支；已有intent只结清AMBIGUOUS，不赋新HTTP权限。SUCCEEDED substrate优先真实纯本地完成，绝不退回字幕请求。

## 128事件的源头预算

- acquisition的claim/recovery及每次preHTTP前预留16个事件槽；不足时不新claim/不调用网络，锁内追加诚实终态receipt。
- 剩余local attempt数为`r=3-local_attempt_count`。每次local claim/finalize前预留`4*r+2`：每次用户resume、recovery claim、attempt开始、结果各一个，另留entry/Close。RESUME action须预留`4*r+1`。
- 若重复重启已经逼近该预算，直接用当前request锁做真实本地完成，不先消费新的claim/attempt事件；结果事件与local_attempt_count同事务提交。失败进入ATTENTION，仍保留后续所有合法local attempts及Close。
- 正常路径的最大临界值：首次网络前至多112条，intent后113；首个本地结果至多116条，local attempt1；下一次本地结果至多120条，attempt2；第三次结果至多124条，attempt3；Close至多125条。重复纯heartbeat可增加revision但不消费事件，也不改变此界限。
- 因此本版普通执行不能制造“126条+字幕已成功+仍有合法local attempt但只能Close”的状态。测试用真实worker反复中断于preflight前和local claim后；保留全部既有事件、真实attempt、3次本地配额及128硬界限，不扩常量、不裁历史。

独立review仍须重跑基础REJECT三项、完整父链/容量负控与恢复矩阵。本文不是主控验收；root真实旧tracked全DATA副本GUI、重启及恢复仍为最终采用门禁。

备份语义负控先用原ZipInfo原样重包做可stage/cancel正控；新增DATA项明确S_IFREG。两组独立恶意库提交后关闭，使用immutable=1新只读连接验证实际入ZIP主库的完整iterdump等于预期损坏快照，排除WAL遗漏；12项所有权/文件与4项prepared父链损坏须在语义校验层拒绝，不能靠ZIP特殊文件错误判绿。

## 真实推进时钟与已知 capture 失败后继（2026-10-19）

- 一次原子 claim/reserve/takeover 只取一次真实 `claimed_at`，所有该事务的 started/updated/available 及五分钟 lease 由此派生。后续 IO/heartbeat 使用真实时刻；已有 `started_at > updated_at`、未来 updated/available 或倒退时钟继续拒绝，不夹值、不重写坏历史。取得 claim 后若时钟倒退到 execution.updated_at 之前，在调用 adapter 方法前 fence。原 `register_subtitle_source_capture` 严格时序校验保持原样。
- 第四种旧失败证明仅适用于本 tracked 协议：execution 为 `FAILED/LOCAL_FINALIZATION_FAILED`、local count=0，真实 job/provider attempt 各=1；job 为 `FAILED_FINAL/INVALID_RESPONSE`，provider 为 `FAILED_FINAL/LOCAL_RESOURCE`，双方 message 精确为 `LOCAL_FINALIZATION_FAILED`，dispatch 为 `FAILED_KNOWN`。execution/job/provider/dispatch/终事件终结时间完全相等，无 live owner/lease/response/cost 或完成 authority。唯一真实 attempt 与首 CLAIMED 时刻、worker owner 格式、错误、终结时刻及 lease 一致；末两事件严格为同 epoch 的 DISPATCH_INTENT、FAILED。全历史仍先经过现有 typed/action/hash/source/request 证明。
- 文件闭包仅允许既有协议的 1 或 2 个 VERIFIED CAPTURE，各有精确 ABSENT WRITE_BUFFER，数量及路径无额外项。逐项重建 producer/proof/hash，读取实际受限 DATA bytes；buffer 必须在磁盘上确实不存在，ABSENT 不是 partial。两 capture 必须是同源、同规范语言/请求语言、按时间先 plain 后 native VTT/SRT 的原生计时替代；不增加原 cap2。capture artifact 可以不存在或为完全匹配的非权威 source-capture 记录；任何 canonical/timed/Summary/Evidence 或其他 job artifact/文件均拒绝。
- `verify_old_failure(..., data_root=...)` 在既有迭代父链的每层复验上述完整闭包。`read(..., data_root=...)` 向下传递显式 DATA root；遇这种祖先而缺 root 时关闭。服务/current/status、历史/action、worker、reader 及 Backup 路径均使用绑定 root。真实旧 attempt owner 没有独立事件 owner 字段，故仅验证已有真实 attempt 的 worker owner 格式与当前 owner 全空；新 command 还必须取得父 request EX 锁，不能仅据 lease 判定 writer 退出。
- 此分支由 execution 的专属错误类别选择，provider 变成 generic 可重试错误也不能降级走普通名单。原 generic `KNOWN_RETRYABLE`、128/3、typed counter witness、1051 祖先及 34–39/LOCAL39/Cloud 行为不变。只允许用户显式新 command、新 target/provider identity；同 command 幂等、父记录只消费一次。原 FAILED、capture bytes、原错误及次数均不改；未知 dispatch/partial/额外文件/未结清 writer 继续关闭。
- 该 narrow predicate 已只读核对原真实 3975B capture 失败，允许其作为新 command 的严格父证明；这不是执行或真实 GUI 正控。离线推进时钟/1–2 capture/重启/完整 Backup restore 为实现证据，真实 GUI 与全仓后端/独立 review 仍由 root 在固定候选上验收。旧 2 个 unindexed DATA 属独立 MIXED 缺口，不在此修复或绕过。
