# Tracked Content retry：040 执行与恢复补充合同

2026-10-19。配合原迁移提案及 root 2026-10-18/19 的取消、真实 preparation attempt 和事件预算决定。040 尚未正式采用；没有正式040历史需要兼容。保留原三表、128条事件上限、旧34–39全部领域行及DATA；不新增依赖、不签发模型资格。

## 执行和读取

- worker持稳定store SH + request EX直到同步字幕adapter返回、文件结清及终态持久化。暂停在preHTTP事务先赢时不调用该网络方法；已开始的同步方法不假称能撤回。每次取得writer增加epoch；过期lease本身不证明旧writer已退出。
- 首次真正网络方法前，在同一事务追加`DISPATCH_INTENT`（ACQUIRING→ACQUIRING、相同epoch、action=null），再把dispatch改为`DISPATCH_INTENT_DURABLE`。后续候选body方法复验authority，不再重复marker。无marker的NOT_DISPATCHED可恢复；已有intent且无法证明结果时AMBIGUOUS，不重发。
- job成功只表示字幕持久化。timed、Evidence、extractive Summary及完整completion另行验证；失败只进入本地ATTENTION，最多3次local attempt。原文、文件意图与buffer均保留，不创建SourceRun成功、不执行评分/洞察/ASR/Cloud。
- reader重放固定typed事件/action/hash/epoch，复验旧job全行、真实attempt、source/video/channel/ENROLLED和全部冻结参数；验证每个provider、target attempt、文件producer/实际bytes与完成证据。Backup再做正反向所有权、精确040 Schema和全DATA闭包。
- 明确收到的typed adapter失败，在抛出前同事务持久化provider FAILED_FINAL及FAILED_KNOWN；不确定异常/超时走BaseException，不写known。若在执行终态前中断，恢复只结清既有known receipt，保留原错误code/message。若在known receipt前中断，仍是未知并关闭重发。
- API的action按不可变request验证Content归属，不依赖“当前最新request”。新child产生后，同command重放旧取消仍返回旧receipt；错Content在任何写入前拒绝。action历史重放也完整验证provider/files/completion。

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
