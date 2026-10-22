# 当前等待修复后的串行收尾

2026-10-21。状态：WAITING_DEPENDENCY；不是新阶段、不是已接受执行能力。依据只读 scout /root/local_fixed_runtime 对 root a571880 与当前未提交41草稿的检查。先完成当前 WAIT/CANCEL/Backup 任务的固定提交、独立审查、整合与真实 GUI；不得并行改共享核心。

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
