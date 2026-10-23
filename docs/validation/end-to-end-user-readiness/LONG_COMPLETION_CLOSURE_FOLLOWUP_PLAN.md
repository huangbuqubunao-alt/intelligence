# 当前等待修复后的串行收尾

2026-10-23。状态：DEPENDENCY_DONE，待当前root记录提交后生成串行任务；不是新阶段、不是已接受执行能力。依据只读 scout /root/local_fixed_runtime 对 root a571880 与当前未提交41草稿的检查。先完成当前 WAIT/CANCEL/Backup 任务的固定提交、独立审查、整合与真实 GUI；不得并行改共享核心。

## 下一工程切片

保持已冻结的 long profile（32768 context / 6144 output / 300秒、原模型/采样/语义）及已审 codec、projection、request、canonical。R14 LOCAL 8192 profile不授予长内容能力，records=[]不授资格。复用既有适配器、资格和容量边界进行明确版本化扩展，不复制另一整套框架。

最小专用接口为 claim_long、complete_long、verify_completion/revision：只消费持久化 proof 重建的 PreparedLongRequest；不将调用者传入的 VerifiedInput 或 options 当作权限。generic 所有写入口继续拒 long。

旧 WAITING_MODEL/WAITING_BUDGET 和取消均保持终态。资格后由用户新 command 建新 execution，不能复活旧等待。新 reserve/claim 同事务复验完整来源、预算、精确资格和已封存 readiness，CAS 一次 inv0→1，transport 消费能力一次。

完成先保存真实 public/decoded 各自原字节和 hash，positive 再经既有 canonical 投影绑定 revision content hash，不改措辞/stance。依41最终接受合同，receipt 与 intelligence/revision/Evidence/history/current/card/checkpoint/真实 usage 一次事务提交。不得调用会另开事务且拒 long 的旧 admit 接口后补证明。NO_NEW 按 receipt→checkpoint 时间/预算→035 sidecar顺序，随后不再更新 checkpoint；不重复落物理 zero usage。所有延迟 FK/三 branch先用隔离正负控证明写序。

提交异常后新连接只认完整一致 receipt 和闭包；缺失、部分或冲突保持未知且不重发。length/donefalse/错模型保留拒绝实况；未知实际身份或超时不造 completion receipt。所有历史读、Save/Topic、quiescence、Backup 在 checkpoint/proof/receipt/revision/035/usage 双向验证，不能因组合删除并重签 ZIP 降级为 generic。合法 Summary/policy 刷新不改旧快照读取。

工程期仍不启用真实 transport/资格。必需检查：三分支、完整114/2406假 transport正向/NO_NEW→保存/主题/历史/重启/全SQL及全部DATA恢复；逐写点及commit故障、并发claim/完成/取消、重复消费、未知结果、输出cap/超时、错证据/stance/父链、历史刷新和组合删除反控；旧短输入/Cloud/R13/R14回归。假输出测试只证明工程，不计真实语义资格。

## 后续真实门

核心稳定后沿同一生产 builder 接入固定模型 native renderer/slot/完整容量和专用资格路径，CODE_FILES覆盖实际执行与41及纯模块。按原标准固定原资格例及未见样例，首次真实失败停止，不改预算/时间/语义标准凑过。LOCAL 六实质正向及两反例不能拿 mic-test/仓库头几行充数。

真实合格后还须普通 GUI 正向提炼→保存→主题→Evidence 回跳/刷新/重启/全量恢复，最终 ASR tuple seal复查、完整前后端/静态/build与图文手册。全部原采用条件满足才可安全 ff-only/push/launcher；当前候选未发布。

## 旧 long v1 运行参数的版本边界

只读核验确认旧longv1仅继承短v1的options并覆盖32768context，没有显式batch512。旧profile/request字节及本次等待/取消proof必须永久保留。未来真正执行如须固定512，应新建明确long运行profile版本，保持32768/6144/300和语义标准，单独验证原生容量/槽/资源及资格；不改旧_OPTIONS_WIRE或覆盖旧PROFILE_ID的历史含义。历史重建必须按proof冻结的profile_id选择保留resolver/builder，而非后来全局新默认。当前只WAIT且生成关闭，此处不是已获模型能力。

## 固定 b3546ff 后续只读核验

2026-10-21 scout /root/local_fixed_runtime 零写入/网络/模型核验：041最终字段、branch CHECK和延迟FK已能表达positive/NO_NEW/REJECTED，不需仅为三分支再迁移；SQL可表达不等于完成authority。新运行profile可保留long执行协议v1 namespace，由profile/request/freeze hash区分，勿把profile升级误作namespace升级。

DIRECT复用ApplicationHeavyLease/共享重负载锁、安装字节验证、ready→arm→consume单次/线程/请求绑定及claim后不探测、300秒/1MB有界loopbackHTTP。LocalCapacitySession仍绑定短builder/resolver/16384槽，资格reader/permit也固定短版本，须明确long版本适配；不能通用重签permit授执行。新增执行文件补CODE_FILES，records仍空。verify_receipt_payload本身不能代替严格计数/cap/语义/revision完整双向闭包。先完成当前Settings/真实WAIT0取消恢复，再共享核心串行此工程，不同时写入。

## 当前0.40.6官方实现只读前检

2026-10-21 当前已安装程序为0.40.6，旧0.40.1 runtimeproof及binary哈希已不匹配；机器安装catalog新增不授执行能力。scout使用agent-reach GitHub路由/官方GitHub插件读取固定官方代码，零写入/模型动作。官方[v0.40.6 commit2476d5ead197abe04629651028f83d48dc75d2b2](https://github.com/ollama/ollama/commit/2476d5ead197abe04629651028f83d48dc75d2b2)，对照[v0.40.1 cf2a313a298066d572c36812e5ad30a21c0db13b](https://github.com/ollama/ollama/commit/cf2a313a298066d572c36812e5ad30a21c0db13b)。以下是源码推论，不是容量、质量或资格验收。

- 显式num_batch仍关闭自动batch，显式num_ctx关闭自动context；已载1024与新显式512 options不等时需reload。[routes.go](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/routes.go#L202-L223)、[sched.go](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/sched.go#L1428-L1477)
- 普通completion正batch映射成对-b/-ub，context为NumCtx×parallel，qwen35调度parallel1；16384/8192、32768/6144不被10×context兜底改小，但不保证实际输入+输出容纳。新增decision-head整prompt分支可把batch改为context，目标模型必须实测属于普通completion，不能以显式512推导所有模型都512。[runner参数](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llm/llama_server.go#L92-L135)
- 指定文件中think布尔/native enable_thinking、空messages正keepalive加载契约未变；keepalive0是卸载，不能用于装载证明。[API](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/api/types.go#L135-L172)、[load分支](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/routes.go#L3189-L3208)

0.40.6官方文件SHA256（scout内存计算/Git blob交叉核验）：api/types.go e19aafa5065afa3ed058df9135d200527391e012349ed5955dd0cc09c0b33f7a；server/routes.go 47c0bce03da44ba50c65e436f61538c67457282b9504a1ecc11d090461120855；server/sched.go 3383fad80c474ae352da2289ed6ecc5a22763be722433eda4ac9816775ff382d；llm/llama_server.go 4d9477c32d90ed8c3436aa67480a2ac55234dd401038d097bb33ab8101c4461c。

后续真实执行必须新版本冻结当前runtime/binary，不改旧profile/proof：cold/warm512、已知1024→512严格空加载、两context真实slot/argv、native renderer全token、thinking/public final、自然keepalive过期、ready→arm前host变化。应用lease不锁外部Ollama客户端；claim后仍一次consume、不隐藏重试，未知保持未知。先完成当前Settings等待/取消/恢复工程与GUI，才可串行实现。

## 2026-10-23根调用点只读补核（非开工）

固定292/b187的 `long_distillation_persistence.verify_proof` 当前调用无profile参数的 `prepare_long_request`，`_verify_prepared` 又直接 `resolve_long_profile(PROFILE_ID)`；将来不能仅换这个全局常量。必须由严格解码、有限已知ID的历史 `proof.profile_wire` 选择保留builder/resolver，并逐项重建request/profile/schema/freeze hash；新reserve只由后端可信运行选择确定新版本，调用者不能上传任意profile获得权限。旧v1 proof和已取消任务永久可读，不按当前binary或新增manifest键集重解释。

当前 `reserve_wait` 已把真实手动command身份绑定为 `MANUAL_CONTENT:<manual_command_id>`，经policy/semantic/freeze及最终execution_id持久化；保留此机制。新手动命令可以形成新identity，旧取消仍不可复活，不应为支持重试重写旧取消行或削弱037。

041的profile_wire/hash与request_wire/hash字段没有硬编码执行profile ID，三branch和usage延迟FK已经存在。后续先复用最终41而非仅为新增profile再迁移；SQL可表达仍不授claim/complete、语义质量或模型资格。当前 `verify_execution` 明确只接受inv0 WAITING_MODEL/WAITING_BUDGET，拒claimed/result，后续专用原子claim/complete与双向reader必须一起闭包后才改变此拒绝。来源/摘要/政策完整性guard及generic long-family拒绝保留。


## 2026-10-23 官方 no-truncation 合约补核

只读scout `/root/native_capacity_contract_scout` 使用agent-reach/gh官方源；未写产品、未请求本地模型、未加载/生成。固定Ollama0.40.6 commit2476d5ead197abe04629651028f83d48dc75d2b2及upstream620d2225cc436ab0b001e3200e590e3b286ef9ab。以下源码结论不能代替机器实测容量或语义资格；仅新有限profile可采用，旧冻结字节永久保留。

- 高层Chat/Generate正式支持**顶层**`truncate:false`和`shift:false`，不属于options；默认true。false经routes及CompletionRequest传播，关闭历史/Go runner提示裁剪。[ChatRequest](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/api/types.go#L166)、[GenerateRequest](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/api/types.go#L114)、[routes](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/routes.go#L3244)、[Go runner裁剪](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llm/llama_server.go#L299)。
- shift还参与runner加载/重载；预加载、readiness、arm及最终请求须同值，claim后不能变更触发重载。[sched解析](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/sched.go#L178)、[启动](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/sched.go#L624)、[重载](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/sched.go#L1460)。
- 低层/completion请求不解析这两个字段；任意追加不能授保障。shiftfalse令Ollama不加--context-shift，upstream默认false，但LLAMA_ARG_CONTEXT_SHIFT环境配置仍可能覆盖，因此“argv没有该参数”不等于实际关闭。[低层请求](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llm/llama_server.go#L1435)、[启动argv](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llm/llama_server.go#L815)、[upstream默认](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/common/common.h#L578)、[环境选项](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/common/arg.cpp#L1743)。不得为验证该单一属性输出进程全部环境或无关凭据。
- 高层响应没有truncated字段，prompt_eval_count=cached+evaluated；200/done/stop/单个count都不能单独证明输入完整。upstream最终JSON虽有truncated，也不能证明此前高层没删历史。[高级响应](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/api/types.go#L525)、[低层响应映射](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llm/llama_server.go#L1590)、[upstream字段](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-task.cpp#L330)。
- 关闭shift后超长输入报错，生成触slot边界产生limit/truncated；不能当完整成功。[输入边界](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L3675)、[生成边界](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L2026)。

有限当前profile须将false pair绑定真实最终request/freeze，完整Qwen35渲染/tokenize、实际slot/runner配置和N+输出+安全边界一并验证；不能仅靠字节长度、旧版本proof或成功HTTP授容量。此补核只澄清既有不截断要求，不扩大输出预算/context/300秒、依赖、模型或资格范围。


## 2026-10-23 root 裁决：完整容量性质与不可观察开关分离

官方补核明确native `/props`、Ollama load/ps均不暴露实际context_shift；顶层shiftfalse不能排除继承环境。不能伪造false证明，也不读取用户daemon全部环境/凭据、不为此直接引入第二套daemon管理框架。前节“实际runner配置”要求按下述可验证的安全性质实现；不是降低全量输入或无截断标准。

/root/native_capacity_contract_scout 对同一固定upstream作有边界源码核验：只在纯文本普通单次completion、完整实际最终token序列N、实际单slot容量C、每请求真实硬上限P全部成立，并严格 **N+P+2<=C** 时，即使内部ctx_shift=true，容量触发分支仍不可达。该证明表达“本请求无容量shift/截断”，不表达“runner开关为false”。

依据：[请求n_predict优先](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L1960)、[采样递增](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L4478)、[达到P停止](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L2036)、[容量shift入口](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L3374)。入口要求prompt.n_tokens()+1>=C，而约束使全过程<=N+P+1<=C-1。输入超限本身拒绝：[输入检查](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L3675)。历史cache按commonprefix并删除尾部，不把旧cache全长与N相加：[匹配](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L3700)、[满命中退一/keep_first](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L3907)、[删cache尾](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L3944)、[纯文本position](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-common.cpp#L435)。

裁决：授权仅在新增有限当前runtime/profile的adapter工程中采用此充分条件，复用原有单daemon/lease/ready-arm-consume框架。仍冻结顶层truncatefalse/shiftfalse并在warm/load与最终请求一致；完整实际Qwen35渲染、true/true tokenize及BOS边界、请求/模板/schema/model/runtime/runner身份、真实C与P一一绑定。不得把请求num_ctx当实际C、字节估算当N、HTTP200或单个prompt_eval_count当完整性证明。排除媒体、续context、共享子请求和工具自动后续生成；任一前提不能实证就拒绝，不增加预算/时间、修补输出或启用registry。

必须有synthetic ENGINEERING_ONLY正负控覆盖边界等号/越界、错slot/模板/token/host、cache冷热、未知上限，以及独立审查后真实机器容量/语义验收。此裁决只允许最小工程路径，不等于机器容量、模型质量或生产资格通过；不能据此写入registry。若实现发现源码前提不成立则记录具体反例并failclosed，再讨论最小受控启动边界。


## 2026-10-23 root 裁决：有限资格记录与长输入真实质量门

当前资格模块仅旧PROFILE_ID/按scope唯一/最多3记录，不能直接支持current short与long同YT_TIMED；更不能据short资格开放long。任务内允许有限适配：生产记录按严格(profile_id,scope)唯一、完整binding逐项复验，当前最多4组合=short YT_TIMED/LOCAL_TIMED/LOCAL_TEXT与long YT_TIMED；保留既有262144字节等有界读取、package-only seal、过期/代码/模型/runtime/manifest/case顺序校验、重复/未知全部failclosed。不按恰好匹配hash挑优，不改全局旧PROFILE_ID/历史冻结或给旧R14版本授生成权。旧格式/原case矩阵保持，原始历史记录不改写；工程期resource records=[]。

Long资格显式绑定base_schema+codec+profile，其每次动态alias schema仍由完整request/proof重建。原YT资格10例/原LOCAL8例的输入、语言、语义、独立review顺序和首次失败即停规则均保留，不能复用short receipt跨profile。长profile另在原YT矩阵末尾追加2个有界强制案例：`long-full-en`输出en、`long-full-zh`输出zh-CN；二者使用同一真实完整0eMzc-WnBfQ来源（114 ORIGINAL Evidence/2406 timed cues，不截20、不删cue、不调整历史），按该long profile各一次，前例获真实review通过才允许后例。它们是新增长profile的额外门，不替换/减少原10例或distinct unseen holdouts；不开放给short/LOCAL profile借用。

补充案例的真实原文/摘要/政策/完整来源与请求hash、capacity/runtimeproof、冻结harness/manifest、permit前序链在最终工程固定后、任何实际调用前由root一次性封存；此处仅定义不可省略的质量覆盖。当前不授真实调用、签permit或写registry；资源不足/任何真实FAIL仍停并保留。若新增long案例需要最小有限case_scope/selector映射，属于当前qualification适配，不另建通用任意case机制。最终独审须核查profile隔离、篡改/重复/错case/profile/schema/code/model/容量/封印拒绝，以及长输入两例确为完整真实来源。普通GUI长内容正向/保存/主题/重启/恢复仍须通过，不能以工程合成结果或短样例替代。


## 2026-10-23 think=true 精确 renderer 前检

scout对同一0.40.6官方Go qwen3.5源码只读补核：仅system/user、无tools/媒体/历史且thinktrue时，精确文本为`<|im_start|>system\n{GoTrimSpace(S)}<|im_end|>\n<|im_start|>user\n{GoTrimSpace(U)}<|im_end|>\n<|im_start|>assistant\n<think>\n`，最后一个LF保留；无手写文本BOS、无false模式的空闭合thinking块。[固定实现](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/model/renderers/qwen35.go#L252)、[assistant后缀](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/model/renderers/qwen35.go#L349)、[LeadingBOS](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/model/renderers/qwen35.go#L72)。自动special/BOS由实际true/true native tokenization计算，不能另用假设减去。

必须证明实际Config.Renderer=qwen3.5及模型内置Messages为空；请求两条消息并不保证最终只有两条。[内置历史前插](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/server/routes.go#L3598)。Go路径schema作grammar，不加入文本prompt；native另一template分支包含messages/response_format，不能套此公式。[grammar](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llm/llama_server.go#L1707)。

官方测试仅有true后缀断言及另一assistant prefill场景，没有该精确S/U两条true全串golden；新测试必须注明固定官方源码推导，不冒称官方完整golden。[官方后缀测试](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/model/renderers/qwen35_test.go#L173)。这仍仅为工程实现输入，不是实际机器token容量或质量通过。


## 2026-10-23 当前资格的真实结果约束

`LIVE_MODEL` 表示实际调用方式，不表示产生了有效洞察。当前有限版本资格必须将封存的真实结果分支与逐例独立语义评审绑定：LOCAL前六个timed/TXT/MD中英文案例均需实质正向Intelligence，末两例按原NO_NEW/注入反例标准；long-full-en/zh均需完整来源下的实质正向。NO_NEW、拒绝或空正文不得凭PASS字符串、hash全等或一次调用记作正向通过。原输入、语义、case顺序和首次FAILSTOP不改，不修补模型输出；历史旧格式保持可读，不据旧receipt授当前生成资格。这属于已定原质量标准的显式工程校验，不新增模型调用或变相放宽。


## 2026-10-23 实际 native slot 字段核验

只读scout /root/native_slot_schema_scout 按固定官方源码确认：Ollama2476d5e构建LLAMA_CPP_VERSION=b11669精确指向已固定upstream620d2225；兼容补丁不改server routes。[构建](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/llama/server/CMakeLists.txt#L118)。

该已验证runner端口的GET /props无需--props（该开关控制POST），default_generation_settings.n_ctx为实际每slot容量，total_slots为实际parallel数量，is_sleeping为实际状态；不是请求num_ctx回显。[props构造](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L5226)、[实际slot计算](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L4652)。GET /slots默认开启，数组项有id/n_ctx/speculative/is_processing。[默认](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/common/common.h#L681)、[字段](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/server-context.cpp#L733)。

当前有限adapter要求total_slots严格int1、is_sleeping严格false、slots恰好一项id严格int0、两处实际C一致且slot空闲；保留runner/host前后身份绑定。503/超时/缺字段/类型错误或矛盾都failclosed，不采用request容量兜底。这些是固定源码合同，零本地HTTP/加载/生成的scout结论不代替真实机器容量验收。


## 2026-10-23 current-long reserve→claim 中断恢复

普通POST同步reserve→continue；若进程在新current-long PENDING/inv0持久化后、claim前退出，合法零调用任务不能再次永久阻塞Backup。本任务内补最小启动恢复，不新增DDL/调度器/自动模型调用：持同一ApplicationHeavyLease，仅完整历史proof与真实MANUAL_CONTENT、PENDING0/RESERVED、无ledger/usage/035/receipt的明确未执行记录，在IMMEDIATE事务内重验CAS后走现有defer_long。当前预算仍允许时WAITING_MODEL0可沿原路径取消；预算已否决时真实WAITING_BUDGET，保持原规则，不伪造ADMITTED。

当前来源/Summary/policy指针合法刷新不等于冻结历史损坏；安全deferral验证完整保留历史，执行准入仍另需当前校验。inv1/未知/损坏/冲突/legacy/旧WAIT或WAIT_BUDGET、其他活跃lease均不降级或重发，不绕过Backup。若启动时别的真实任务持lease，保持真实阻塞并复用既有恢复机会或正常重启，不新建后台框架。恢复与claim竞争只能一个赢家，两次启动幂等；中断→恢复→取消→全SQL/全部DATA备份恢复不复活须有外部测试证据。

保留真实中断reason，不能在实际已合格时虚称没有合格模型；优先沿既有DTO/提示展示“上次提炼在模型执行前中断，可安全取消后重新提炼”。若缺失，仅必要文案/翻译/测试纳同task，前端有改即重跑完整前端/TS/build。此为用户持续默认授权下的必要恢复边界，不需要逐方法审批；最终源码冻结、独审、真实门及采用条件均保持。
