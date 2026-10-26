# 三路径模型实施顺序与首个安全修复（2026-10-26）

用户目前没有API账号。当前进程仅对MOONSHOT/NVIDIA/NVIDIA_NIM/GROQ/GEMINI已知变量做presence-only检查，均无；未读.env/Keychain/正式配置，不推定机器其它上下文无凭据。现有真实M12云端K2.6验收保留，但官方现行定价页提示10月31日起K2不向新用户开放、12月底计划退役，故不作为新用户长期默认。免费NVIDIA仅prototyping范围、旧K3两次终止历史不能重开；Groq提供freeplan但账户/配额/地区/隐私尚未实际核实。优先继续核实国内可注册的BigModel GLM-4.7-Flash：官方当前页面标输入/输出/缓存免费，尚未验证实名、余额门槛、账户额度、API可达和模型真实质量，不承诺永久免费或已通过。

本地Whisper/字幕/摘要已验收成果保留；本地Intelligence当前候选均保持未合格，Gemma实际首例455a06独审拒绝。Granite权重不下载，避免再把local-only当门槛。

## 源码核实的先修缺口

1. runtime_composition.ProductionDistillationBudget.check直接返回allowedTrue；其它授权与at-most-once仍在，但这个接口没有实现费用/账户额度上限，不能据此宣称收费预算已强制执行。
2. local_api POST cloud-intelligence/review在凭据缺失时拒绝预览；有资格/凭据时调用reserve_distillation_execution建立PENDING，随后review_reserved_cloud_execution才返回告知内容。用户只是预览/返回也会留下阻塞Backup的准备任务；前端没有放弃入口。
3. App.tsx硬编码K2.6费用段和WAIT_MODEL条件；当前provider/价格/新账户可用性、各能力配置与首次引导需要区分。LOCAL/BILIBILI云端明确不支持，不能借新目标静默扩权限/上传私人内容。

只读预检代理因selectedmodel capacity两次停止，无代码改动；主控已通过graph+当前AST/路由/前端源码独立核对以上事实，不把未完成代理当已审报告。

## 最小顺序

A. 后端无副作用云预览：不要求密钥、不调用网络、不消耗预算、不创建reservation/checkpoint/授权/任务；复用当前可信输入投影和有限provider authority。确认才重校验输入/模型/同意/预算并建立执行，拒绝/过期/来源变化不能留下新孤儿PENDING。费用未配置时默认拒绝收费调用，保留本地路径。无需新Schema优先，必要原子方法明确记录。旧PENDING不删除、不假装quiescent，作为后续零调用安全终止slice处理。
B. 独立审查A，补前端可退回的模型/数据/费用预览、设置深链接及转写/摘要/洞察各自状态。跳过首次引导后相关操作仍可配置；不因选择cloud就发请求。
C. 并行核实一个免费provider的条款/网络/账号/额度/隐私/确切modelAPI；正式决定最小fixedendpoint适配、provider-specific安全凭据及需要的兼容迁移。仅用户自己注册/在设置录Key，不在聊天收key，不自动接受外部条款。仅公开/合成数据真实资格，不私有上传。
D. 费用策略/预算与旧未派发reservation安全取消：原子claim+永久cancel记录，invocation/未知状态failclosed、旧错误/ledger/provenance保留，重启/BackupRestore不复活。精确迁移范围/兼容/恢复/风险先记录，按持续授权隔离实施，不逐文件再询问。
E. 一条真实合格模型的普通用户路径先完成（不要求所有本地模型合格）；其它路径标真实/模拟/未验证。再完整回归/真实GUI/79表全部行与物理DATA/恢复/证据回跳，通过后按原Git安全采用条件推进。没有可用账号/授权则实报，不模拟称为真实通过。

A-D不包含任何新付费、私有上传、正式数据或配置变更、依赖升级、模型重试、main采用。付费路径具体预算/数据scope与准备完成后再请求一次明确授权；未授权继续零费用工程。每个slice独立WT、writer、review，现有框架和成果不重做。
