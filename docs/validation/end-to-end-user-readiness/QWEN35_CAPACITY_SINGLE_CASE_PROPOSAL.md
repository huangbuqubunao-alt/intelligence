# 固定9b输出容量：单例隔离诊断提案

2026-10-14，待用户具体批准。尚未实施或执行；只申请一次研究诊断，不授权资格、正式配置、后续模型调用或发布。

## 实际依据与停止点

已批准 official-thinking-v2 原英文首例真实一次：912 input、4096 output、194.6019675秒，native done=true/done_reason=length，公开最终正文为空；正规 REJECTED_OUTPUT。详见 QWEN35_THINKING_V2_FAILURE.json（result SHA256 66f3c27489bbf44b246b64ad5193e816a201d954b92957eafdf03995a7b8034d）。其余三个原样例未准备/调用，LOCAL八例未执行。原 nonthinking 四项语义 P1 及全部失败仍保留。

该证据证明现有预算下没有可接纳输出，不能证明增加预算就会正确。唯一待检验假设：同一固定输入与模式获得更多输出容量后，能否产生完整且满足原语义门槛的公开结构化结果。

## 唯一允许的新增动作

新增独立 research-only profile，只将 num_predict 4096 改为6144。只运行原 real-deepthink-en 一例一次；其他三个原资格样例、LOCAL八例均不在本次调用批准内。

继续使用已安装 qwen3.5:9b-q4_K_M，官方 manifest SHA256 56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90、原七个blob及现有 Ollama0.40.1；不下载、升级或替换权重。原生 think=true；temperature1.0/top_p0.95/top_k20/min_p0/presence_penalty1.5/repeat_penalty1.0/seed20261013/num_ctx8192/300秒请求上限全部不变。

原v5角色消息、结构schema、严格parser、原source/Summary/Evidence/VerifiedInput和语义标准逐项hash固定。不得修改prompt、样例、Evidence、seed、context、超时或输出内容；不得截断输入/扩大窗口/修补输出/抽样择优。新 actual request 除 num_predict 外须与保留的原V2请求深度一致，包括角色消息与全部options；新输入在独立DB重新准备，只能prepare-only，禁止复用旧执行身份或许可。原912+6144=7056小于8192只是容量前提，不能代替模板及真实输入未被截断的校验。

允许文件仅 scripts/qualify_readiness_qwen35_intelligence.py 的研究profile/单例permit约束、新版freeze与对应研究合同tests、任务/交接/证据。不修改生产distillation/state/runtime/API/Schema/配置/资格reader/依赖或旧V1/V2冻文件；旧测试不弱化。先独立审查代码及sealed input，再由root核验固定安装/runtime、实际资源及无并行重量任务，签发外部一次精确许可。

真实响应仅公开最终content和完成metadata用于parser及独立原标准语义审查；私有thinking不读、不展示、不据其修改输出，原响应仅不透明保存hash。零付费云、零正式数据/凭据/Vault操作。

## 停止、风险与恢复

单例最多一次。不论成功或失败，本次授权到此停止。length/达到6144预算、超时300秒、未知执行、协议或任何原语义失败均保留并停止，不重试、更换profile或继续其他样例。原194.6秒按容量比例可能接近300秒，此推算不保证延迟；超时不延长或重跑。结果不能自动推进原四例、LOCAL验收或production_qualified；即使单例PASS也只证明此例，后续完整资格需新的具体决定。

全新隔离worktree/DB/DATA/permit/result路径，保留所有旧失败与checkpoint/ledger，恢复/重启仍不重放已调用任务。模型重量操作与声学验收串行，不停止用户其它进程。正式main及服务维持原版本。

## 为什么需要本次具体批准

此前 QWEN35_THINKING_FOLLOWUP_PROPOSAL.md 明确固定 predict4096且任何FAIL即停，本次已遵守。改为6144并开启新研究不能从“继续”推定。用户全局AGENTS要求安全敏感模型边界先获具体批准。本申请只覆盖上述固定容量、一次原英文样例的隔离诊断，其他已批准字幕与本地文本工程继续。

## 2026-10-14 用户具体批准记录

用户明确回复“批准该精确单例容量诊断范围”。本精确research-only6144/ctx8192/300s/原英文最多一次范围已批准；未执行，其余样例与正式资格未授权。
