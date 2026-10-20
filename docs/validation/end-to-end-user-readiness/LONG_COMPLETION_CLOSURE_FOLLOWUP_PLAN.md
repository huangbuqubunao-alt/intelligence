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
