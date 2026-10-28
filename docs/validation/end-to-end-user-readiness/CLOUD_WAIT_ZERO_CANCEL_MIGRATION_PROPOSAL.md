# Schema42→43：云端尚未执行等待的安全取消与有限429原因提示

当前Goal持续授权已包含必要、兼容且可恢复的隔离Schema修复；本方案先记录范围和风险，不再次按文件请求批准。实现、测试和恢复仅使用独立临时资料库，正式owner/配置/凭据不变，模型资格和预算不放行。

## 已复现的真实工程缺口

已审BigModel v1/v2在fake缺密钥或已知TLS建连失败且尚未POST时，均持久化WAITING_MODEL/invocation_count0；全部actual provider/model、tokens、cost、duration、HTTP及Intelligence/revision均NULL，合法OWNER consent保留。现37的Python和SQL只接受Ollama，因此can_cancel=false且Backup为DISTILLATION_ACTIVE。TLS分支历史outcome叫CLOUD_CREDENTIAL_REQUIRED_BEFORE_DISPATCH，不可据其字面断言发生过HTTP或一定是密钥错误。

两种明确零调用outcome仅为MODEL_UNAVAILABLE_BEFORE_TRANSPORT及CLOUD_CREDENTIAL_REQUIRED_BEFORE_DISPATCH。当前BudgetDecision只有allowed/state；真实capsule的checkpoint与usage budget_state均为PUBLIC_DIAGNOSTIC_ANTICIPATED_FREE_MAX_ONE，另有既有ADMITTED等明确允许标签。reason是命令原因，不是预算说明。**当前checkpoint不持久化request_identity_json；不得假造该列、payload或授权。**

## 精确迁移范围

只追加043 SQL，新建第一张不可变`distillation_cloud_waiting_model_cancellations`，12字段：execution_id/source_id/video_id/reason/use_case/selected_provider/selected_model/output_language/budget_state/checkpoint_updated_at/cancelled_at/outcome。execution/source/video外键RESTRICT，字段类型/时间/绑定明确校验；outcome固定CANCELLED_BEFORE_CLOUD_MODEL_INVOCATION。追加插入安全校验、禁止receipt更新删除、已取消checkpoint不可更新或再claim、禁止新child挂接及旧child恢复的保护triggers。不改037表/guards，不ALTER或重写现有数据，另追加下述六字段非权威429观察表，不新增其它表/列，不删除checkpoint/ledger/consent/Evidence，不写费用0。

receipt引用原checkpoint全部身份与时间，不重复存profile/request/consent。只覆盖已审zhipu_bigmodel/glm-4.7-flash v1/v2公开YT，可靠WAIT0及上述outcome，全部实际结果字段NULL，checkpoint/usage一致、预算为明确已准入标签，无HTTP/failure/NO_NEW/结果权威冲突、无关联活跃或不一致SourceRun。必须验证已存在的42 consent（USER_CONFIRMATION或OWNER_QUALIFICATION），不补授权。可用retained consent input hash、可信完整canonical Evidence身份、checkpoint字段和有限v1/v2 prompt/profile参数重算既有reservation ID；无法可靠匹配则拒绝，不凭ID前缀猜测，不要求已变化的当前兴趣冒充原兴趣。不要穷举子集或制造丢失payload。未知/无可靠consent legacy、PENDING/RUNNING/WAITING_BUDGET、已执行或部分执行仍failclosed。

## 最小代码与用户反馈

复用现有事务/幂等取消API、can_cancel DTO、CANCELLED读投影和UI按钮；新增窄cloud证明helper，state按provider路由证明。多SELECT读取同一snapshot；取消在BEGIN IMMEDIATE内重验/追加，claim与取消二选一，后续SQL guards不可绕过。保留原账本/同意/证据，复取消返回同一receipt，重启/恢复不复活，不清capsule外部once标记。旧Ollama行为不变。

Backup复用逻辑CANCELLED和已有SourceRun窄关闭路径，同时新增43反向证明/Schema验证；其它活跃任务仍阻止备份，不能因一项取消就ready。**旧manifest集合34…41+LATEST在LATEST=43时会遗漏42，必须显式保留34–42及43。** UI仅在已有提示确实误导云端时最小调整：尚未开始执行，检查密钥/网络或取消；不能把历史含糊outcome写成确定故障原因。取消反馈原内容/字幕/摘要/Evidence保留、未生成洞察；不新增重试框架或自动上云。

## 兼容与恢复策略

旧001–042全部SQL字节不变。正常42→43只有schema_migrations追加43登记、用户版本43、额外两空表与guards；原81表所有旧行和DATA不改。完整测试旧34–42备份恢复及新43带取消receipt恢复；42不可因版本集合疏漏被拒。恢复前先以标准备份保留隔离基线；有问题停止采用并保留候选，使用既有Restore恢复原隔离快照，不做down migration/删表/强制重置。正式采用仍等全部Goal门禁，不能从Schema获批推导生产放行。

风险是把未知执行误当0、取消/claim竞态、遗漏读入口、旧42恢复兼容和单项取消误放Backup。用四种已复现v1/v2×缺key/knownTLS0、真实invocation/unknown/budget/pending/running拒绝、前后并发/幂等、snapshot/SQL拒绝重启、receipt/schema/consent/字段篡改failclosed、所有SQL/DATA恢复一致以及其它未完成任务继续阻塞覆盖。全部fake key/wire，绝无Native/浏览器/实际provider调用；与Root已耗的一次真实诊断严格隔离。

## 2026-10-28补充：同一未发布43中的有限429观察

用户已确认轮换并更新隔离密钥，Root在固定65bb6b/867606f具体prepared35ba7475包上真实执行一次，HTTP429、REJECTED_OUTPUT/invocation1、无最终内容，立即停止。旧adapter没有保留业务码，因此不能判断是余额、限流、额度、忙碌还是密钥类型，也不能把它算作新版语义失败。原result/外部once/旧错误不改写；不得倒填猜测。该真实终态已经正常开放Backup，取消功能不能拿来消除它。

为让后续普通用户获得可操作原因，在同一尚未发布43追加第二张非权威不可变sidecar，严格6字段：execution_id、selected_provider、selected_model、http_status（仅429）、error_code（1113/1302/1305/1308/1315五值）、observed_at。execution外键RESTRICT；只绑定已终结CLOUD_HTTP_ERROR/429/invocation1的合法checkpoint、042 failure和原同意记录。042 failure与raw resource_usage互斥，公开usage是前者的派生读投影，不能要求或制造双账本；raw usage/NO_NEW不存在。字段、时间、绑定及不变性由SQL和读/恢复验证保护。它不改变原CHECK/outcome/reason/状态/调用计数/费用或Backup readiness，也不具有模型、证据、授权或取消权威。

只在BigModel非200分支按既有有界读取与300秒总期限解析严格JSON中有限`error.code`。未知/异常/过长/非429沿用generic错误；不保存message、原body、账号标识、凭据、响应hash或任意服务端字符串。旧42/历史generic429无观察表/无sidecar也仍兼容，不回填。有限getter/DTO将已知原因映射为核对账户状态、稍后手动重试、等待额度重置或检查标准API密钥的固定中文提示；不诱导充值，不自动重试，不自动转付费。现有base dataclass不加None字段，避免改变旧asdict/输入hash。

成功请求wire/body/prompt/profile/decoder、旧001–042、实际capsule和oracle全保留原字节。必要文件仅distillation非200观察分支、新helper/state/Backup、窄API/UI提示和相关tests；无依赖/模型/网络读取次数变化。结合原取消测试一次验证两张新表、旧34–42/新43恢复、有限码、私密message丢弃、未知码generic、单次invocation、事务失败与篡改拒绝；固定实现后做一次针对性独审，不反复审查已经通过且未改变的成果。

业务码依据官方文档 <https://docs.bigmodel.cn/cn/faq/api-code>，这是未来错误的有限诊断提示；真实已耗429的具体业务原因仍未知。新增风险仅为非权威元数据误绑定、私密错误文本残留和错误提示误导，以上有限字段/白名单/旧generic兼容与不改变执行许可用于限制风险。
