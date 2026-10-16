# Tracked Content retry：Schema39→40 精确迁移提案

2026-10-16，**PROPOSED，供 root 决定，尚未实施**。提案工作树基线 `d775b0c91f02bccaa3ba1790fdb315206785e6bf`；依据 root `3ecbce8` 的方案B及后续只读指令。工作树内旧任务卡的“noSchema优先/复用SourceRun”描述由该决定收窄、替代：独立请求及执行投影，不创建虚假的八阶段SourceRun成功。用户持续默认授权覆盖必要迁移、安全保护及验收；本文件不申请逐文件人工审批，也不构成产品开工/正式采用。

本次只写本文，不修改产品、测试、迁移SQL、任务状态或运行数据；真实网络/模型IO为0。实现须等待HOST及capability接受后由root固定最新基线。既有VIDEO_URL流程不改。第一slice仅YOUTUBE、tracked CHANNEL、ENROLLED、METADATA_READY、明确允许重试的TRANSCRIPT FAILED_FINAL。METADATA retry、scoring、distillation、ASR、Cloud、全pipeline drain均不在范围。

## 1. 已有代码事实与复用选择

- `012_add_source_run_orchestration.sql`：SourceRun FINALIZATION绑定八阶段；COMPLETED child需distillation execution。不能把Content-only完成写成这些步骤成功。
- `state.py:claim_next_job/reclaim_expired_jobs/activate_retry_jobs`：generic路径会claim TRANSCRIPT或恢复过期lease。新增target必须同时从claim、reclaim、activate、rerun及generic drain隔离；传入明确job_id也不能绕过。
- `state.py:transcript_refresh_generation`取当前FAILED_FINAL数量；不能在恢复时再取它构造新provider request。
- `transcripts.py:fetch`先保留文件，再complete_stage，随后补timed；`load_verified_transcript`用`complete_stage=False`读取同一已验证缓存并能恢复timed。job SUCCEEDED仍可能没有timed或Summary。
- 当前subtitle acquisition没有自己的完整durable dispatch intent包围adapter调用；不能用provider lease过期推导“没有调用”。
- `extractive_summary.py:create/read`为无网络的deterministic source excerpts，写文件、artifact、Summary指针分步完成，可在严格同输入下恢复；不得改成模型摘要。
- `backup_restore.py:_artifact_records/_verify_complete_data_set`要求实际DATA与普通artifact/既有neutral retention集合精确一致。m038 neutral proof强制SourceRun与verified successor，不能伪造这些关联复用。
- 当前`providers/subtitles.py:YtDlpSubtitleAdapter`通过同步`extract_info(download=False)`及同步body reader取回数据。此观察不是全部child/callback已被证明安全；未来实现仍需锁生命周期及真实进程反证。

DIRECT：SQLite事务/外键、现有provider request hash builder/dispatch状态、managed path/hash、native subtitle验证、timed/Evidence authority、extractive Summary、现有Backup后台门禁。ADAPT仅限新协议的dispatch、文件写入及恢复hook；旧调用默认行为保持。REJECT：SourceRun伪成功、复活旧job/ledger、全pipeline retry、m038伪successor、hash枚举或客户端自报权限。无新依赖；标准库`fcntl`仅限已支持本地POSIX运行环境。

## 2. 基础类型与规范化

下文`ID`为`TEXT NOT NULL`、trim后非空、≤512码点；YT video ID另按当前合法ID验证。`HASH`为64位小写hex的`TEXT NOT NULL`，SQL检查必须排除任意非hex字符。`UTC`为当前统一27字符微秒UTC格式。所有FK均`ON DELETE RESTRICT`。INTEGER用`typeof(x)='integer'`，不能由字符串/布尔JSON冒充。

canonical JSON使用UTF-8、固定键、稳定排序、无多余空白，不去掉合法列表元素、不截断、不猜默认值；以UTF-8 byte数限界。SHA用于完整性，幂等仍比较完整typed canonical输入。未知键/版本/enum拒绝。超限在admission之前失败。

第一slice固定：`contract='tracked-content-retry-v1'`、`operation='RETRY_NATIVE_TRANSCRIPT'`、`provider='YOUTUBE'`、`target_stage='TRANSCRIPT'`。一个请求仅一个logical acquisition；目录和候选body可有多个受现有native policy限制的HTTP，不能声称整个字幕流程只有一条HTTP。

## 3. 精确三表

040只追加以下三表、索引和必要保护trigger，不重建既有表、不补造旧请求。无额外SourceRun或SourceRun child/event/checkpoint。

### 3.1 `tracked_content_retry_requests`：不可变请求与冻结输入

除明确nullable外均NOT NULL。

| 字段 | SQLite类型及约束 |
|---|---|
| `request_id` | ID，PK；`tracked-content-retry:v1:`协议前缀+完整SHA256 |
| `contract` | TEXT，固定上述contract |
| `operation` | TEXT，固定上述operation |
| `command_id` | ID |
| `client_input_json` | TEXT，canonical object，UTF-8≤8192 bytes |
| `client_input_sha256` | HASH |
| `source_id` | ID，FK→source_subscriptions.source_id |
| `video_id` | ID，FK→videos.video_id |
| `observation_identity` | TEXT非空≤100；复合FK `(source_id,observation_identity)`→source_observations的复合PK |
| `provider` | TEXT，固定YOUTUBE |
| `channel_id` | ID；insert/verifier核对source/video/channel identity，不能凭客户端给值 |
| `expected_old_job_id` | ID，FK→jobs.job_id，UNIQUE |
| `old_job_snapshot_json` | TEXT，canonical object，UTF-8≤16384 bytes |
| `old_job_snapshot_sha256` | HASH |
| `target_job_id` | ID，FK→jobs.job_id，UNIQUE |
| `pipeline_version` | ID；绑定旧job与admission时video pipeline |
| `target_stage` | TEXT，固定TRANSCRIPT |
| `parameters_json` | TEXT，canonical object，UTF-8≤65536 bytes |
| `parameters_sha256` | HASH |
| `refresh_generation` | INTEGER，0..2^60-1；与冻结输入一起验证 |
| `raw_request_hash` | HASH，UNIQUE |
| `provider_request_hash` | HASH，UNIQUE；这是未来provider row的身份承诺，不在此列设提前存在的FK |
| `created_at` | UTC |

索引：`UNIQUE(source_id,operation,command_id)`、`UNIQUE(video_id,refresh_generation)`，以及video/source历史读取索引。`expected_old_job_id`唯一意味着旧失败只能被一个请求消费；后续新的已知失败target可作为另一个新请求的old job，不能再次消费最初old job。

固定JSON合同：

- `client_input_json`恰有`contract,operation,video_id,command_id,expected_job_id`。前三项由路由/版本规范化，不接受客户端source/channel/provider/stage/model参数。路由同video才可重放；同source+operation+command改任意typed输入为409。server无法唯一绑定一个合法source时409，不任选source。
- `old_job_snapshot_json`恰为admission读到的完整JobRecord持久列投影，包括job/scope/video/type/stage/pipeline/lineage、终态、attempt/max、available_at、空lease、error code/message、created/updated/finished_at。验证FAILED_FINAL、TRANSCRIPT、VIDEO_STAGE、完成时间与无活动attempt；不能只比job ID或错误文案。
- `parameters_json`恰有`language_preferences,adapter_name,adapter_version,selection_policy_version,format_policy_version,native_timing_policy_version,normalization_version,quality_policy_version,metadata_snapshot,local_finalize_max_attempts`。语言保留实际规范化后顺序，不删重复、不采用恢复时新配置；`metadata_snapshot`保存完整已验证VideoMetadata供同请求重构；`native_timing_policy_version='tracked-native-timed-v1'`、`local_finalize_max_attempts=3`。其余版本取admission实际已安装常量/adapter。任何不支持/不匹配版本关闭执行，不能以当前默认值替换。
- request ID来自canonical `{contract,source_id,operation,command_id}`；target ID固定`tracked-content-retry-job:v1:`+hash(request ID、oldjob、stage、pipeline)。generation固定取request完整digest首15hex的整数；原provider/raw request若已存在且不能证明属于同一原请求即拒绝，不碰撞重试或采用动态失败计数。哈希派生只是稳定身份，不是权限证明。
- raw/provider request用现有builder、冻结参数复算；provider operation为现有`subtitle.fetch`、model为null、prompt/schema版本及deterministic raw artifact key完整匹配。

禁止UPDATE/DELETE request；关联old job一旦被消费，禁止修改/删除其历史持久列。target job身份/参数不可修改，状态只能由新协议受保护方法推进。不能保护旧行的同时禁止合法source enabled/policy后续变更；历史reader不要求source当前仍enabled。

### 3.2 `tracked_content_retry_executions`：CAS执行投影

| 字段 | SQLite类型及约束 |
|---|---|
| `request_id` | ID，PK/FK→requests.request_id |
| `source_id` | ID，FK→source_subscriptions；trigger保证等于request.source_id |
| `revision` | INTEGER≥0，初始0；每次改变行恰好+1 |
| `state` | TEXT，枚举见转换矩阵 |
| `fencing_epoch` | INTEGER≥0，初始0；每次取得新的执行所有权恰好+1 |
| `lease_owner` | TEXT nullable；非空≤512 |
| `lease_until` | UTC nullable |
| `provider_call_hash` | TEXT nullable，FK→provider_calls.request_hash，UNIQUE；只准NULL→request.provider_request_hash一次 |
| `local_attempt_count` | INTEGER，0..3；本地finalize尝试只增不减 |
| `error_code` | TEXT nullable；固定公开机器码集合，不保存任意异常作为公开状态 |
| `canonical_artifact_id` | TEXT nullable，FK→artifacts.artifact_id |
| `timed_transcript_id` | TEXT nullable，FK→timed_transcripts.timed_transcript_id |
| `summary_artifact_id` | TEXT nullable，FK→artifacts.artifact_id |
| `completion_json` | TEXT nullable，canonical object，UTF-8≤1MiB |
| `completion_sha256` | TEXT nullable，严格HASH |
| `events_json` | TEXT，canonical array，UTF-8≤1MiB；初始只有admission事件，append-only |
| `updated_at` | UTC |
| `finished_at` | UTC nullable |

partial UNIQUE(source_id)只覆盖`QUEUED,ACQUIRING,FINALIZING,ATTENTION`。同源SourceRun/source_check互斥仍需跨表trigger及同事务guard，不能由这个index单独保证。

`events_json`避免第四张命令表，同时保存可重放的状态证据和本地动作receipt。每个元素恰有`event,prior_state,state,revision,fencing_epoch,at,action`；event为`ADMITTED/CLAIMED/RECOVERED/LOCAL_ATTENTION/LOCAL_RESUMED/COMPLETED/FAILED/CANCELLED/AMBIGUOUS`。`action`为null或恰有`operation,command_id,expected_revision,input_json,input_sha256,applied_revision`。初始ADMITTED绑定原command；用户本地动作操作仅`RESUME_LOCAL/CLOSE_LOCAL/CANCEL_BEFORE_DISPATCH`，input固定request_id/operation/command_id/expected_revision。

同一request+action operation+command历史完整输入相同返回原receipt+当前投影，不重新排队；不同输入409；不存在历史receipt才按expected_revision CAS并追加。SQL trigger用json_each验证旧数组完整前缀不可变：有状态/动作/epoch变化时恰追加一条；纯heartbeat保持数组原样，只更新lease/revision，不追加假状态事件。typed verifier验证canonical/hash、唯一动作key与转换重放一致。最多允许3次local finalize；用户动作receipt与状态事件可由同一元素表示。完整事件数组最多128项，126项后禁止新claim/resume、为诚实结束保留终态空间；若不能证明安全终止仍closed，不因容量强制放弃。任何未知/伪造/丢失事件使reader/Backup拒绝。

列组合：只有ACQUIRING/FINALIZING持lease；非持lease状态owner/until均NULL。只有SUCCEEDED/FAILED/CANCELLED/AMBIGUOUS有finished_at。只有SUCCEEDED可有非空完整completion及三个完成FK，且全部同时存在；其它状态均NULL。中间已产生的artifact仍通过provider/files普通权威读取，不在这些列伪称完成。ATTENTION/FAILED/AMBIGUOUS必须有匹配error；QUEUED/ACQUIRING/FINALIZING/SUCCEEDED的error为NULL。终态整行不可UPDATE/DELETE；身份不可变；其余更新须CAS并校验epoch/owner。

`completion_json`恰有`contract,request_id,target_job_id,provider_request_hash,parameters_sha256,raw_artifact_id,raw_sha256,canonical_artifact_id,canonical_sha256,timed_transcript_id,timed_transcript_hash,summary_artifact_id,summary_sha256,summary_producer_version,evidence`；evidence是完整canonical覆盖顺序的`{evidence_id,excerpt_hash,locator_type,timed_transcript_id,start_cue_index,end_cue_index}`数组。它绑定完整源覆盖集合；extractive Summary仍按现有规则选摘录，不截源字幕、不把Summary的前6条当全部覆盖。完成证明不授Intelligence/NO_NEW或模型资格。

### 3.3 `tracked_content_retry_files`：写入意图与中性文件闭包

| 字段 | SQLite类型及约束 |
|---|---|
| `request_id` | ID，FK→requests.request_id |
| `relative_path` | TEXT非空≤4096；managed DATA相对路径；全局UNIQUE；与request_id为PK |
| `role` | TEXT，`CAPTURE/RAW_SOURCE/CANONICAL_DERIVATION/SUMMARY_DERIVATION/WRITE_BUFFER` |
| `expected_sha256` | HASH；网络返回并验证后、文件打开写入前冻结完整预期bytes的hash |
| `expected_size_bytes` | INTEGER≥0，按role现有写入上限校验，不提高字幕/文件资源上限 |
| `state` | TEXT，`PLANNED/VERIFIED/RETAINED_PARTIAL/ABSENT` |
| `observed_sha256` | TEXT nullable，非NULL严格HASH |
| `observed_size_bytes` | INTEGER nullable，非NULL≥0 |
| `proof_json` | TEXT，canonical object，UTF-8≤65536 bytes |
| `proof_sha256` | HASH |
| `created_at` | UTC |
| `settled_at` | UTC nullable |

除三个nullable列外NOT NULL。identity/role/expected/proof/created不可变；禁止DELETE。仅`PLANNED→VERIFIED/RETAINED_PARTIAL/ABSENT`，settled后全行不可变。PLANNED的observed/settled均NULL；VERIFIED的observed精确等于expected；RETAINED_PARTIAL仅允许WRITE_BUFFER，持真实observed hash/size且仅作中性字节保留；ABSENT的observed均NULL、必须持有隔离旧writer的证明且该路径不存在。

proof固定键为`contract,request_id,provider_request_hash,parameters_sha256,fencing_epoch,logical_target_path,expected_artifact_id,capture_artifact_id,source_format,source_language,requested_language,source_type,normalization_version,quality_policy_version`；非适用值显式null，不能省略猜测。对canonical/Summary还须通过协议role对应的完整可重构producer规则校验，不以单一hash当来源证明。buffer绑定预先批准的逻辑target，不能用事后扫目录给任意文件补证明。

每个实际写路径（包括atomic write buffer）必须先有PLANNED，再打开/写/fsync/rename；buffer与final各有intent。正常rename后buffer可验证为ABSENT且target VERIFIED；崩溃遗留partial buffer以真实bytes保留，不能删除或改称canonical。非buffer实际bytes与expected不符属于损坏，不能中性降级掩盖。普通artifact与中性表引用同物理path时hash/size必须一致，physical集合只计一次。

在HTTP返回但尚未来得及把bytes持久接受的崩溃中，不可能证明内存body已保留；此时只能报告未知，不能宣称未调用或完整capture存在。这里保证全部**已持久接受或落盘的文件**闭包，不虚构丢失的内存响应；未知请求不重发。未来实现必须把完整accepted capture持久化放在后续解析/选alternate/完成stage之前。

## 4. Admission、互斥与preHTTP intent

`POST /api/v1/content/{id}/retry`只接受`command_id,expected_job_id`。读取/错误响应采用现项目机器码合同。已有VIDEO_URL入口保持；tracked入口独立返回request/execution及明确能力。

锁顺序固定：现有`background_work`许可→稳定store共享锁→per-request排他锁→SQLite BEGIN IMMEDIATE。禁止持SQLite等待flock。admission同事务完成：

1. 优先查该来源/operation/command完整历史；同请求返回历史，不因source现在paused而伪造新执行；仍验证原历史完整性。
2. 新请求证明source enabled、YOUTUBE CHANNEL、真实tracking/membership、observation非baseline且ENROLLED/content_id一致、source/video/channel一致、公开metadata及METADATA_READY、指定oldjob是当前可重试TRANSCRIPT FAILED_FINAL，无活动job/attempt/provider未知状态。
3. 同源所有live SourceRun/source_check/retry互斥；标准health/trust guard不能跳过。没有网络来补admission缺失metadata。
4. 冻结参数并检查raw/provider hash无不相关历史，创建max_attempts=1的稳定PENDING target、immutable request和QUEUED execution；一项失败全部rollback。

首slice legacy失败白名单固定为`TRANSIENT_NETWORK/RATE_LIMITED/PROVIDER_UNAVAILABLE/INVALID_RESPONSE/CONTENT_UNAVAILABLE`，且最后job attempt须以同码明确FAILED_FINAL结束、没有活动lease/未知dispatch。未知码、空码、LEASE_EXPIRED、UNKNOWN_PROVIDER_STATE、CONFIG_INVALID、PERMISSION_DENIED、LOCAL_RESOURCE、CAPABILITY_UNAVAILABLE、TRUST_INTEGRITY_INVALID不凭文案猜成可重试。新协议自己的pre-dispatch取消/前置条件失败target，只有strict prior request证明零dispatch且当前全部资格已恢复，才可作为下一人工command的old job；这不是legacy通用白名单扩张。root开工包须把实际旧tracked失败原证据与此集合核对；若实际错误不匹配，本文不能声称已覆盖该P1，须先精确修订规则，不能放宽未知/信任标准。

QUEUED零调用结束采用**仅本协议target**的行政终态：PENDING→FAILED_FINAL、attempt_count=0、没有伪造job_attempt，finished_at明确；由匹配request/execution终态trigger核验，不扩大generic JobStatus迁移集合。job/provider保留现有Domain ErrorCode或既有系统错误合同；本文execution/API的公开机器码是独立协议枚举，不向冻结的Domain ErrorCode添加值。零调用行政结清由专属方法及receipt表示，不假称发生过provider失败。

给source_run/source_check新增insert/active-transition guard，反向拒绝同源live retry；新retry也拒绝这些行，覆盖手工/自动Check Now两序竞争。未来动作不写source policy、observations、frontier、health、last_checked_at、last_success_at。

专用claim在同事务复查request完整性、target身份、current authority/paused、CAS revision+epoch，创建job attempt/provider reservation和provider_call_hash绑定。job/provider的lease_owner采用该request稳定的logical owner，不把进程nonce当权限；跨进程所有权以同一flock和execution epoch证明。max_attempts=1指一个logical acquisition attempt；pre-dispatch恢复只在NOT_DISPATCHED下延长同一attempt的lease，保留原attempt number/started_at/owner，追加RECOVERED事件及新epoch，不finish旧attempt后再创建第二个attempt。专用恢复方法原子更新execution/job/job_attempt/provider lease；普通renew不能授权过期恢复。

generic所有路径排除request-owned及明确协议prefix的target；generic provider reserve/recovery也不得接管本协议provider hash。prefix存在但关联缺失/未来未知版本只能报损坏，不能当generic工作执行。只有专用上下文、锁、epoch与完整request验证同时通过才能接续该logical attempt。

在首次adapter网络方法之前，持锁事务复查enabled/authority/lease/epoch，持久`DISPATCH_INTENT_DURABLE`后才允许enumerate/read。此事务是“暂停先赢则0网络”的线性化点；不能承诺撤回已开始HTTP。后续adapter网络方法仍复查pause，不因已有intent绕过暂停。一次logical acquisition内的目录/候选读取按冻结native policy执行，不增新provider identity。

当前`fetch`的通用exception/fail_provider_call不能把intent之后的不确定返回改写成FAILED_KNOWN。新协议需精确hook：已收到明确失败才能记录known failure；无法证明结果则保留未知，停止自动HTTP。所有新provider完成/失败须绑定request、owned target及epoch，不修改初始旧失败ledger。

## 5. 稳定flock、writer fencing与child/callback证明

`lease_until<=now`、PID不存在、换process nonce都**不是**安全放弃证明。新协议要求：

- 稳定锁目录位于应用managed runtime控制目录，不能放在会被restore交换的DATA/DB候选内。目录/文件禁止symlink，检查owner/type；lock file不删除、不重命名、不按重启换inode。
- 每个request有确定文件名的`fcntl.flock(LOCK_EX|LOCK_NB)`；writer从claim前持到全部HTTP、response/capture、文件/DB/finalize和回调彻底结束。所有恢复、local action、结束和terminal receipt同样取得该锁。
- 同一store另有稳定共享/排他锁：新retry writer持SH；Backup创建/恢复activation持EX并保留现有`background_work/_protect_background`。锁顺序store→request→SQLite；不无限等待，忙时明确BUSY。此新增证明只覆盖新协议，不能声称解决所有既有跨进程工作。
- 取得旧request排他锁后才可事务CAS增加fencing_epoch；所有file intent、stage/provider完成与finalize同时核验epoch和当前lease。新worker不能通过“lease已过期”抢锁。旧worker不得释放锁后继续使用已取出的callback或异步写操作。
- production adapter必须证明没有逃逸的managed写入者：同步方法返回且response已关闭、相关future/callback已join；若存在child，必须退出/reap后才释放锁，或证明child根本没有managed DATA/DB写能力且只向受控pipe/隔离temp输出。不能仅kill parent、detach thread、启动新nonce后宣称完成。
- 父进程被真正终止时OS释放flock；恢复仍需证明残留child不能写managed存储，并在持锁状态核对全部intent/actual文件。任何一项未知继续closed，不发新HTTP、不生成terminal/Backup许可。

验收必须使用两个实际进程/受控迟到writer：A卡在HTTP后、lease过期，B不能取锁/结束/备份；A释放后B才能推进；A旧epoch的DB/文件写被拒；进程退出/残留child/迟到callback各有独立证明。普通Python线程mock或单测nonce不足。

## 6. 状态转换与诚实用户出口

所有迁移需持同一request锁、合法CAS及文件条件。未列迁移禁止；终态无回退。

| 原状态 | 允许目标 | 前置条件/动作 |
|---|---|---|
| QUEUED | ACQUIRING | 专用claim；enabled/资格/冻结版本再验证；新epoch/lease |
| QUEUED | CANCELLED、FAILED | 可证明尚无dispatch；取消或确定前置条件失败，target诚实FAILED_FINAL |
| ACQUIRING | ACQUIRING | 独占锁确认旧writer已退出，provider仍NOT_DISPATCHED，绝无network intent；新epoch续同一logical attempt，不增attempt count、不生成新generation |
| ACQUIRING | FINALIZING | provider+target成功及已持久原始响应，转纯本地；job成功本身不代表Content完成 |
| ACQUIRING | FAILED | 明确已知字幕/原生timing失败或可证明pre-dispatch失败；owned新provider/job结清；文件闭包 |
| ACQUIRING | AMBIGUOUS | intent后结果未知；旧writer已隔离；provider dispatch保留AMBIGUOUS、call/target终态诚实；文件闭包 |
| FINALIZING | FINALIZING | 取得同一锁、隔离旧writer后新epoch恢复本地工作，attempt<3；只读既有成功provider/源字节，禁止HTTP |
| FINALIZING | SUCCEEDED | 完整canonical/timed/Evidence/extractive Summary proof通过；原子写completion+终态 |
| FINALIZING | ATTENTION | 已完成网络，timed/本地Summary未完成或版本暂不可用；释放lease，仍阻塞Backup |
| FINALIZING | FAILED | 确定不可恢复或三次本地上限；无writer、所有文件闭包，绝不伪成功 |
| ATTENTION | FINALIZING | 重启恢复或显式RESUME_LOCAL；仅本地、冻结参数、attempt<3；原command不重放 |
| ATTENTION | FAILED | 显式CLOSE_LOCAL或确定无法恢复；同锁隔离+文件闭包后结束，不要求Summary成功 |

公开机器码第一slice限定：`SOURCE_PAUSED/SOURCE_CONTEXT_CHANGED/RETRY_CONTRACT_UNAVAILABLE/NATIVE_TIMING_UNAVAILABLE/CAPTIONS_UNAVAILABLE/KNOWN_PROVIDER_FAILURE/LOCAL_FINALIZATION_FAILED/LOCAL_FINALIZATION_LIMIT/LOCAL_FINALIZATION_CLOSED/CANCELLED_BEFORE_DISPATCH/DISPATCH_OUTCOME_UNKNOWN`；损坏统一`RETRY_INTEGRITY_INVALID`，保持closed，不能转换为“允许忽略”。实际adapter错误映射必须按现类型判断known/unknown，不能用任意exception文案分类。

- 原生timed不可得：在new target stage完成前FAILED_FINAL，保存已收到的plain/候选capture；不授timed/Evidence，不启动ASR，不先把plain成功当完整完成。
- target SUCCEEDED后：只能用冻结参数调用`load_verified_transcript(complete_stage=False)`恢复timed/Evidence，再create/read extractive Summary。若服务当前版本不匹配，ATTENTION或诚实FAILED，不请求字幕补救。
- stage尚未成功时的已知完整响应/本地持久化失败，若有严格durable response/capture证明，可作为明确本地失败结清owned target/provider并保留文件；不把未完成stage自动升级成功。没有该证明的intent后崩溃仍AMBIGUOUS。此slice不从不明裸文件修补一次成功，也不通过再次HTTP完成它。
- 同一provider已知失败后不自动重发；新人工command只有在新的FAILED_FINAL target也满足首slice全部资格时才产生新generation。已消费的最初oldjob不能重用。UNKNOWN target不允许成为可重试旧job。
- ATTENTION提供“只重试本地整理”“结束本次整理并保留已读内容”；后一动作不删除字节、不把job SUCCEEDED改失败，也不假称Summary可用。用户可以查看失败原因、已验证原文和做静止Backup。达到本地上限仍可安全结束。
- 结束动作只有取得锁/无迟到writer且文件闭包才能执行；做不到时返回BUSY/UNKNOWN及“等待正在运行的读取结束后再操作”。不能用按钮解除安全门禁。公共GET只读，保持unknown，不触发恢复/HTTP；显式动作才wakeup。
- AMBIGUOUS终态保持“不知道原调用结果”，不自动/隐式重发。只有能证明无writer且文件闭包时才可能允许保留未知历史的Backup；否则仍blocked。新协议不许普遍把AMBIGUOUS当known failure。

## 7. 完成、正反向读与Backup证明

统一strict reader供API/worker/recovery/Backup复用：request/hash/canonical JSON、原oldjob快照、稳定target、provider身份/dispatch/lease、file intents、原始字节及canonical/timed/Evidence/Summary全部重构；任何关联缺失不补默认、不枚举hash、不过滤坏行。

成功proof必须引用该请求原canonical/timed/完整Evidence覆盖和Summary artifact。完成时验证当时当前Summary指针；之后合法新Summary刷新不损坏历史proof，历史读取验证原artifact/原引用，不强迫当前pointer永远等于旧值。原artifact或proof坏了必须closed；保留完整原字幕，不截20项、不降低NO_NEW等其它协议标准。

反向验证至少覆盖：

1. 每个显式`tracked-content-retry-job:v1:`或未来未知版本target必须有且仅有合法request/execution；只删三表关联但留下job不能降generic。
2. 每个request的old/target/provider/source/video/observation关系双向一致；同一个target/provider不能被另一请求接管。带显式本协议artifact/file proof身份的记录即使失去execution也拒绝。
3. 每个已调用execution必须有该provider row/dispatch证据；成功provider+target却没有finalize投影不能视为静止或Content-ready。
4. 每个本协议file path必须有合法intent及普通artifact或中性保留证明；每个VERIFIED/RETAINED_PARTIAL必须存在同hash/size字节。PLANNED未闭包、额外文件、缺文件、symlink/path escape全拒，不能用重新hash的ZIP掩盖缺关联。
5. malformed/unknown contract或future marker仅要求严格验证/关闭，绝不授执行/恢复authority。

Backup新增live gate：QUEUED/ACQUIRING/FINALIZING/ATTENTION全部阻塞，即便target job已SUCCEEDED；持现有background_work和上述store锁。SUCCEEDED/FAILED/CANCELLED在全部终态/文件证明通过后静止。

AMBIGUOUS需**专属逐request**settled verifier：严格请求/dispatch未知receipt、call/target终态无lease/active attempt、同锁证明无writer、全部file intents settled、无completion假结果；才可接受该请求的未知历史。不能把全局`_TERMINAL_DISPATCH`添加AMBIGUOUS，不能放宽无关provider/SourceRun的Backup。

Schema40 manifest仍format1，在每个data_files项条件追加`tracked_content_retry_files`引用数组（所有40项都含，普通项为[]），counts条件追加`tracked_retry_retained_files`；只计没有普通artifact引用、由本协议中性证明纳入的物理path数量。普通artifact计数语义不变；data_bytes及新physical preview字段仍来自完整unique物理集合。引用对象固定`request_id,role,state,proof_sha256`，不得装入正文/私密数据。RETAINED_PARTIAL仅为字节保留，不能成为Transcript/Evidence。

_artifact_records须先验证三表与原始/完成proof，再把合法中性路径合并到物理集合；stage时按candidate DB重算manifest/counters/全部hash、验证反向关联与完整实际文件集合。不能接纳一个带claimed checksum、却没有生成来源/意图证明的任意新文件。备份创建/恢复激活期间持store EX锁，restore后旧线程不得在新DATA继续写。

## 8. 34–40兼容、失败恢复与风险

- 两处schema允许集合显式为`{34,35,36,37,38,39,40}`；不能只把LATEST从39改40而漏39。required tables/manifest字段按包的真实schema条件验证，旧包不强制新表/字段，40缺任一表或新proof拒绝。
- 034–039 SQL、registry历史和旧数据不改。旧34–39包先按原schema完整验包/stage/activation，再按既有正常startup连续迁移到40；040只增加空表/trigger/index，无backfill，无稀疏registry。旧039 proof/取消/NO_NEW/retention语义照旧。
- 040失败事务全rollback，旧39 registry/userversion/全部领域行/DATA原样；不删除新表来假装回退。旧二进制不支持40，不能就地反向迁移；回退只能用迁移前完整受验证备份，在受保护恢复窗口换回匹配旧程序。
- 新40包恢复后重启：terminal不重执行；QUEUED仅在NOT_DISPATCHED且锁/权威通过时续同请求；SUCCEEDED target的FINALIZING只本地恢复；unknown绝不重新HTTP。恢复不访问字幕网络来“补验证”。
- 已知本地失败要能安全FAILED并解除本协议live gate；文件损坏、仍有writer或未知child无法证明时继续closed。这是数据安全限制，不能在文案中假称已恢复/已终止/可备份。

必要验证矩阵（仅验收定义，本文未编写/运行这些测试）：同command完整输入/历史replay/CAS冲突、oldjob双消费、同源Check Now两序并发/paused-before-intent零网络、generic所有入口隔离、冻结参数/重启/adapter版本变更、实际两个进程flock与过期lease/迟到child、HTTP各窗口kill、文件写/rename/DB commit故障、job成功timed/Summary各缺口、三次本地上限与显式结束、known failure/unknown分离、正向/反向删关联与完整rehashed ZIP负控、34/35/36/37/38/39真实恢复正常启动40与40全表/全部DATA恢复。每类失败保留证据；不重演盲测holdout、不调用真实模型。

## 9. 后续必要范围与root决定

建议批准的实现边界：`040`新增迁移、state迁移登记/独立request方法/target guard；新专属retry service/reader/worker；runtime_composition仅显式dispatch/wakeup接线；transcripts/source_authority/extractive_summary仅新协议的dispatch/文件intent/本地finalize hook；source run与following check admission的双向互斥；backup_restore的40条件验证/文件集合/静止证明；runtime doctor最新版本；local_api/App/uiLanguage专用tracked资格、状态和动作；对应测试/handoff/docs。不改旧SourceRun成功合同、旧VIDEO_URL产品流程、模型profile/资格/容量、依赖/配置/credentials/正式owner数据。

主要风险是跨进程锁覆盖不全、接收文件存在无证明窗口、unknown被错误当known、target成功掩盖Summary失败、合法Summary刷新被历史reader误拒，以及40错误拒绝39包。若只能证明单进程内锁、不能证明adapter逃逸writer/file闭包，则此方案尚不满足实现验收，不允许靠过期lease/新nonce放弃来出“可用版”。root据此固定开工包；本提案不提前创建WT或实现。
