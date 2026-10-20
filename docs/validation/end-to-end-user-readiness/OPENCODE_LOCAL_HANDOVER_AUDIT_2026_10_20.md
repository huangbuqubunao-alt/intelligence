# OpenCode LOCAL 验收接管核验

2026-10-20 19:30 CST，用户明确交回 Codex root。Goal 未完成，未发布。唯一主控改为本对话；旧 OpenCode 停在 decision-needed，不运行旧 permit、不覆盖其文件/数据库。继续适用用户持续默认授权，必要整改记录范围后实施，不再逐文件申请。

## 已核实事实与纠正

独立只读审查者 `local_budget_evidence_audit` 重新核验真实日志、源码、8份 prepared/DATA/来源关联、回执及当前资格。零写入、零真实模型调用、零正式数据访问。

1. r3/r4 两次真实 generation 各耗尽6144输出token；prompt1075、runner512/512，真实耗时约294/284秒。相同request/seed/execution身份的两次运行不能视为独立统计样本，更不能推导8192一定完成或成功概率。旧失败停止，禁止继续签permit重跑择优。
2. R13真实：`validate_local_grounding_response` 拒绝响应时不携带已观测的结果metadata；service以REJECTED_OUTPUT/invocation1/实际身份None收尾，state正确拒绝，事务回滚，留PENDING/DISPATCH_CLAIMED/invocation1、usage空。另有 `_request` 的无法识别响应走相同缺陷。不允许报告中建议的 synthetic identity；修复保留真实观察，缺身份走诚实未知状态，绝不解除invocation保护。
3. 升级JSON SHA256 `09547fb436080db3e7c6760ce66b678f1b108a9a5c8da939677c419b951d3ba9`、MD `d246472fd52fe70cef9940370e20eaa146f3e2b838b6bfc4bd546a0f95232235` 匹配。其15项源hash有14项匹配：term-sheet后续追加内容，声明7f96f425…而当前0dea4080…；不能称“17项全等”。保留原件并记录快照漂移，不回写旧hash。
4. 8份准备数据、请求、完整DATA及source manifest真实匹配。案例1有真实760/4355 token、final hash和NO_NEW结果。raw checkpoint PENDING/usage空由既有NO_NEW overlay完整表达，不是第二个R13；真实结论仅为NO_NEW分支可运行。
5. 规格要求timed/TXT/MD中英6个正向，再NO_NEW及注入负向。麦克风测试与仓库前5行标题/日期/Assignee不能代替实质正向；英文输出不等于英文源。案例1 NO_NEW不计正向覆盖。
6. 原四例与未见YT holdout共至多10例先通过，才能进行LOCAL8，见 `LOCAL_MODEL_GROUNDING_PORT_PLAN.md`、`LOCAL_INTELLIGENCE_CHAIN_PROPOSAL.md`。本交接链缺该前置通过证据；当前固定包records=[]、旧语义失败保留，未获普通factory资格。
7. 当前6144配置属于同一个profile，YT_TIMED/LOCAL_TIMED/LOCAL_TEXT共用。直接改常量会改变多个scope及旧历史投影。新预算必须独立不可变版本，旧profile/hash/历史读取不变，不将旧receipt重签成新版本。
8. 即使input bound≤8191，8192只说明上下文可能容纳；按已观察速度估算379–392秒，超过现300秒时限。估算不是完成证明。1MB公开响应上限不因失败自动放宽。
9. R14未解决：fresh-server首载合规只是操作观察；warm后1024仍被正确拒绝。普通用户不能被要求每次重启模型服务。需固定真实加载参数并验证冷/暖/卸载后再次加载，不扩大runner白名单或降低资源检查。

## 主控决定与顺序

- 不采用C-OPT3/4删中文或删除LOCAL范围；不采用每案预算覆写。
- 暂不执行C-OPT1的字面量替换或新真实调用：先R13修复、独立审查、整合，再修普通连续执行；新预算在完整版本/时限/内存/上下文/响应上限合同确定后冻结。
- 保留全部8案目标；重新冻结具有实质判断/条件的中英正向来源，原4+holdouts先决门禁必须证明。旧LOCAL运行作为真实诊断/负向证据，不授资格。
- 下一产品任务 `TASK-READINESS-LOCAL-REJECTION-ACCOUNTING`，独立WT `readiness-local-rejection-accounting`，base a989873；只修distillation/harness及测试，不改state/Schema/预算/资格。测试必须证明已知拒绝落账、未知仍failclosed、不重发、重启及恢复保真、Cloud/NO_NEW不回归。实现预检证明现有trigger仅允许有限AMBIGUOUS outcome；主控选择复用诚实 `TRANSPORT_OUTCOME_UNKNOWN`，精确LOCAL错误另存诊断，不扩大Schema。既有规则可能允许完整持久化的终态AMBIGUOUS归档备份；这不等于执行成功、允许取消或重新执行，恢复后仍须保持未知且不重发。不得为阻塞备份而人为新增规则，也不得绕过其他活跃任务的阻塞。
- 后续R14先只读核对固定官方Ollama0.40.1选项及加载行为，再给最小不可变profile实现任务。官方类型声明存在num_batch，runner使用该值生成-b/-ub；这只是实现依据，不代替真实运行验收：[API](https://raw.githubusercontent.com/ollama/ollama/v0.40.1/api/types.go)、[runner](https://raw.githubusercontent.com/ollama/ollama/v0.40.1/llm/llama_server.go)。

### R14源代码预检补充

固定版本官方 [routes.go](https://raw.githubusercontent.com/ollama/ollama/v0.40.1/server/routes.go) 与 [sched.go](https://raw.githubusercontent.com/ollama/ollama/v0.40.1/server/sched.go) 表明：请求明确提供num_batch时禁用自动batch选择；当前未提供该选项，自动调度可选择1024。显式512应使旧1024 runner重载，而不是必须重启整个服务。独立审查者已核对选择/合并/reload/runner参数路径；这是待真实冷暖/卸载重载验证的修复假设。“服务生命周期首载固定512”不是源码规则。新profile必须固定显式加载参数，旧不可变profile不改写。

## Git 与生产保护

接管root a989873773c0f4018cc696930789566925e88c7c，clean；任务文档4614a25。19:25只读核验正式main clean，main与实际远端origin/main均 `73ee7e747b4461b9de8a201d6b47669eb3913d1a`。未访问或重置正式用户DB/配置/凭据，无push/main合并。模型门禁仍关闭，Goal不得标complete。

旧ASR隔离回执存在PASSED/identity ab0c9eab…，尚需独立核对17项与当前tuple，不能仅凭status文件宣称已完成最终声学验收。最终长协议、真正正向GUI保存/主题/Evidence、全量回归、全表全DATA恢复及安全采用条件仍须逐项完成。
