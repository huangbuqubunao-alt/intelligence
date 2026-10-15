# 本地容量只读证明及无生成预检
2026-10-15；当前任务持续授权覆盖必要隔离模型调整。不是旧失败方案重试；新grounding profile尚未冻结、0次真实生成、0新proof、资格全关闭。原8192方案不足；本方案必须先独立审查才进入生产实现，所有旧语义失败保留。

复用 DIRECT Python标准库读取固定GGUF metadata，REFERENCE Ollama官方v0.40.1与其固定llama.cpp b11351（631109b34da437a3c4a5ebd75091d677671392e3），不复制执行外部源码，不装依赖/下载模型。

实际固定模型GGUF含248320词，247587条merge；完整256 GPT2 byte→Unicode符号及每条merge拼接都在词表，形状有效、0缺失。Qwen35 byte encoding/regex分段不增加原始byte符号数，合法merge仅减少数量；已证明不走缺词encoded-byte fallback，特殊token分段也不增加byte上界，保守另留BOS/EOS两位。单user/thinktrue/无system、messages、history、tools、images、suffix、context、请求template/rawfalse的官方renderer封装58UTF8bytes。原完整request上限7680也限制prompt≤7680，故input≤7680+58+2=7740。6144最大输出再留1位，最低13885；选择16384，不提高输入上限、不截来源/Evidence、不改输出预算/语义标准。训练context262144足够；但这不是实际slot证明。

本次root允许一次无生成预检：先校验原manifest/all blobs与Ollama/llama-server binary hashes，API ps无其它模型、余盘≥10GiB、16GiB物理内存与当前压力有可用空间，再POST /api/generate 设置 _debug_render_only=true、thinktrue、num_ctx16384、num_predict6144、truncatefalse、shiftfalse，单个无敏感诊断prompt。官方routes.go在Completion前直接返回渲染文本；不得删此字段/错误重试成生成。严格对比完整58byte公式、image_count0及实际ps context_length≥16384、runner参数每slot能力。不匹配/资源不足即STOP，不授资格。该操作会装载已安装权重，预计约6–10GiB内存；无下载/上云/费用/正式数据修改。只记元数据及非敏感诊断文本，不读thinking。

若证明成立，另记录最小工程任务：仅新profile固定16384和truncatefalse/shiftfalse，新增固定renderer/tokenizer/运行器前提与fail-closed容量检查；旧None/Cloud/旧TextProfile全字节行为不动。容量算法进执行身份/hash并在新profile第一次真实proof前冻结；生产请求与once harness同构造器。每次实际执行仍需当前有效模型/运行时/渲染配置及容量前提；单次诊断不能长期授执行authority。0生成与空资格继续保持，只有统一代码冻结及独立真实语义验收通过才登记资格。若profile已产生真实proof，后续投影改变须新id，不能破坏历史读取。

证据 LOCAL_CAPACITY_VOCABULARY_READONLY.json。官方来源：
- https://github.com/ollama/ollama/blob/v0.40.1/model/renderers/qwen35.go
- https://github.com/ollama/ollama/blob/v0.40.1/server/routes.go
- https://github.com/ollama/ollama/blob/v0.40.1/llm/llama_server.go
- https://github.com/ggml-org/llama.cpp/blob/631109b34da437a3c4a5ebd75091d677671392e3/src/llama-vocab.cpp
- https://github.com/ggml-org/llama.cpp/blob/631109b34da437a3c4a5ebd75091d677671392e3/src/unicode.cpp
