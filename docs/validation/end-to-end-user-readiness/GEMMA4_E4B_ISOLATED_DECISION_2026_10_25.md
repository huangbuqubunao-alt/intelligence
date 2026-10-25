# Gemma4 E4B 精确隔离候选决定

2026-10-25，继续用户已明确要求的正向链路Goal。用户持续默认授权覆盖完成任务所需的隔离模型调整；本文件记录具体范围和风险，不再次逐文件申请。此前Qwen9B alias+thinking真实结果完整合法NO_NEW，独立f914a156确认正向门未满足；该配置已停止，once不可重用。此次不是追加旧case或更改其结果。

## 唯一新候选及依据

采用不同模型家族的官方Gemma4 E4B作为一项私有可行性候选；不再调整旧Qwen的prompt/预算寻找通过。固定Ollama官方e4b manifest SHA dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c（1552B）；主GGUF SHA370c2879f17648d337b0ab4e208fdce348e24d1060064e93d7645daafd56d39c（5493439296B），config7ca1ae564b24fefd47da34cc579b906b75024860ed4e5bfbfa6d6cbd9777cee5（241B）。只下载这一主模型及原config/template/license/params，不下载projector/draft，不调用付费云或升级运行时/依赖，不改正式配置或数据。

固定已安装Ollama0.40.9/源码5e31438d5d2223d8338595b366b7434ef3539708已注册gemma4-small renderer/parser，支持布尔thinking和JSONschema。官方模型卡同系列E4B在GPQA/AIME/Tau2/MRCR指标高于E2B，故不只为保留前台应用而降低候选选择；这些指标不证明本任务的归因/正向洞察门能通过。E2B本轮仅保留只读比较，不下载或测试。

来源：[官方模型卡](https://ai.google.dev/gemma/docs/core/model_card_4#benchmark-results)、[官方registry](https://ollama.com/library/gemma4:e4b)、[固定renderer](https://github.com/ollama/ollama/blob/5e31438d5d2223d8338595b366b7434ef3539708/model/renderers/gemma4.go)、[固定schema/BOS实现](https://github.com/ollama/ollama/blob/5e31438d5d2223d8338595b366b7434ef3539708/llm/llama_server.go)。公开metadata与源码原始字节另固定在本次ignored artifacts，不依赖浮动tag执行。

## 范围和保护

1. 在root独立 `.var/end-to-end-user-readiness/gemma4-e4b-20261025/` 下载固定blob，逐字SHA/长度核验；公开证据和原license（Apache2.0）保留。下载可安全续传，失败保留partial，不修改旧模型。
2. 检查GGUF metadata/张量名称，必须证明无inline `v.*` vision tensors；固定0409在该标记存在时会自动附加投影器。只有证明后，才允许组装保留主文件原始字节的新私有纯文本manifest，身份必须不同于官方full manifest。projector/draft可选由固定source证明，不冒称自动兼容。
3. 私有范围最多约四个适配/执行模块及针对性测试，DIRECT复用现有E1/E2 codec、原source/语义门、资源/身份/lease/once/HTTPdeadline/原始结果/精确退出保护。没有产品业务代码/Schema或新框架。Gemma专属renderer和容量证明单独固定，不复用Qwen renderer/N；effective prompt必须按固定Go逻辑处理leading BOS，native tokenizer自动补BOS，准确校验实际prompt_eval_count。
4. 固定原real-deepthink-en完整18cue/2Evidence、原系统prompt/通用schema/用户focus/语言/正文；仅模型family/native renderer/官方采样适配不同。原E1/E2映射及严格完整NO_NEW保持，不能强迫正向或补写输出。think=true，temperature1/top_p.95/top_k64/repeat_penalty1按官方params；min_p0/presence_penalty0作为显式中性选择，seed20261013/num_predict8192/num_ctx16384/num_batch512/300秒保持。所有选项需新freeze记录，不能声称与旧请求单变量等价。
5. 全部静态/离线guard和新的BOS/tokenizer/无draft/projector反控通过、独立源审查及具体owner/package绑定通过后，才可最多一次原英文实际生成；结果后停止、独立公开内容与原标准审查。此次不授权任何后续样例、生产资格或main采用，正向信号通过后才冻结后续最小任务和原完整资格/真实用户链。

## 资源、风险、恢复

原主要文件5493439296B，config/template/license/params合计11673B，essential总5493450969B，加原2GiB为7640934617B，磁盘仍至少10GiB。这是启动下界，不是峰值证明；官方加载估算不含context/支持软件。E4B原生KV/allocator必须现场观察，unknown/资源不足保持failclosed；不为通过而调低余量。若需要用户手动退出Codex，必须先完成独立终端再请求实际操作，不自动关闭受保护的Codex/Jimmm。

新权重可能仍无法满足语义门、超时或仅NO_NEW；完整保留失败并停止，不继续同配置调整seed/预算/重复调用。源文件和原始输入不可事后修补。原模型、全部once、历史结果、585产品文件及正式owner均受保护。原6003/1026完整回归不因此私人下载而重跑或伪称新跑，业务后续改动再按影响和最终门禁验收。
