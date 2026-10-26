# BigModel 最小持久化适配计划（未实施）

只读检查基线 bcb2df474a687395b3aa26732241502bc6c094af。目标只新增 `zhipu_bigmodel` / `glm-4.7-flash` 的有限资格验收支持，复用现有 Evidence、授权、一次派发、入卡/NO_NEW 和恢复，不新建业务生命周期。用户持续默认授权覆盖必要兼容迁移的隔离实施；先记录精确范围，独立验收后才考虑正式采用。此计划尚未修改 Schema、生产绑定、凭据或资格，真实调用为零。

## Schema 41→42 范围

一份新042 migration，原025–041字节不改，旧表/领域行不重建、不回填、不删除。新增两张不可变表：

1. `distillation_zhipu_cloud_authorizations`：复用既有九字段 consent 结构：authorization_id PK、execution_id UNIQUE/FK RESTRICT、provider/model 精确 CHECK、verified_input_hash、consent_kind（USER_CONFIRMATION/OWNER_QUALIFICATION）、disclosure_version、cost_status（UNKNOWN）、authorized_at。INSERT 需同源精确模型的 PENDING/count0/未派发 checkpoint；UPDATE/DELETE 禁止。新 provider 全部 count0→1 claim 必须先有匹配不可变同意；未知型号不得绕过。
2. `distillation_zhipu_cloud_response_failures`：复用028有限失败回执字段/状态语义：execution_id PK/FK、actual_provider 精确值、actual_model NULL、status REJECTED_OUTPUT、有限 outcome、http_status_code、input_tokens/output_tokens/cost_microunits NULL、duration_ms、received_at。允许现有 HTTP错误/身份缺失或错误/格式损坏/202未完成类别；必须绑定该新 consent 和已claim checkpoint，不能与成功/NO_NEW/usage/旧失败回执竞争；UPDATE/DELETE 禁止。不要另加重复的 legacy unidentified 表，解析器应能明确表达该表不适用于此新 provider。

仅替换028三个 provider-union trigger，完整保留旧分支并追加唯一新 tuple：`distillation_no_new_http_status_bound`、`distillation_resource_usage_http_status_bound`、`distillation_cloud_failure_outcome_finite`。旧028 failure 表的 CHECK 和历史不改，新失败由新表承担。若实施发现还需其他触发器/字段，先补精确技术记录并继续必要隔离工作，不逐文件请求已覆盖的批准。

对 LOCAL text proof 增加只拒新云 provider 的补充 INSERT 保护；不修改039旧 SQL。注意 `_verify_local_text_proof_schema` 对该表全部 sqlite_master 对象作精确比较，必须按版本识别新保护并拒缺失/篡改，不能简单关闭严格校验。037模型等待取消仍只接受 Ollama + 匹配零调用本地usage，不给新云 provider 新取消权；冲突回执读取清单需识别新表。

## 读取、备份与兼容

有限 descriptor 集中 tuple、固定端点/profile、凭据命名空间及 audit 路由；保留旧 identity，不向每层复制业务判断。state 注册042和必要 audit/HTTP 路由；可信读、取消、长文本持久化的云拒绝与竞争回执清单按存在的版本处理。新 provider 未获真实资格前，不能继承 Moonshot“云完成解除本地等待”的生产例外。

Backup 两处 allowlist 目前是34–40加LATEST，LATEST升42时必须显式保留41。34–41包按原版本严格验包、原 stage/activation/startup 连续迁移，不在归档中补造新回执；42才要求新表/精确触发器及双向回执校验。旧 schema 的源行与全部 DATA 路径/字节/hash不变；registry/userversion和新增空表等预期变化分别列明。42 包必须验证新授权/成功/NO_NEW/失败/未知的行及文件，损坏或缺失保护拒绝，不能因 free 标签绕过 Backup。

迁移在隔离候选单一事务中执行，失败回滚并保留原库与验收失败；不提供删新表的反向迁移，不把42库交给旧程序。正式采用前已有完整 owner 备份保护；回退需原程序配其兼容的原备份，通过正常恢复流程，不直接覆盖正式数据。本轮不执行正式升级。

## 适配边界与完成标准

后续在 preview UI 已审基线上串行实现：集中有限云 descriptor + 新 transport + audit/read/backup；再单独配置路由和界面。新 Keychain service 使用独立 `com.huangbuqubunao.intelligence.zhipu_bigmodel`，独立环境变量，隔离验收先专用命名空间；既有 Moonshot service/account/环境与旧接口原样保留，不能 fallback/覆盖旧凭据。不要把新模型塞到 legacy Deep Analysis/local_analysis/tokenizer 配置。

模型固定HTTPS endpoint、原Evidence sealed input、有限非流式 JSON profile、明确 thinking/输出/等待/零重试；profile 在首次真实生成前冻结。资格只面向公开 YOUTUBE 样例，每条原标准不变，生产资格初始false。官方当前价格0不等于免费 entitlement 或预算权威；生产预算继续拒绝未配置政策，资格专用有限授权/计数也须可审计，不能直接 allowedTrue。

至少证明旧34–41正常升级及备份恢复、42全部表全行与物理DATA一致；新consent无效/缺失/篡改/并发/claim/rollback/重启，HTTP429/202/身份错缺/畸形/截断/未知，NO_NEW/成功真实Evidence绑定，LOCAL/BILIBILI/文字输入拒绝，旧三provider和本地等待取消不回归。之后独立review、真实公开样例语义验收、普通GUI全链和最终完整回归，才可谈 main。账号未完成不阻止离线工程；不付费、不发私人数据、不授假资格。
