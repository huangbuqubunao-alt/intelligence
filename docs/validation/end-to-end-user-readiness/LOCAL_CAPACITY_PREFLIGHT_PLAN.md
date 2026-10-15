2026-10-15 完整请求资源界补充：普通builder无IO测量原四输入，十五Evidence NO_NEW请求在新ctx/安全字段下7869 bytes，原7680 body cap错误拒绝；源与Evidence全部保留，测量见LOCAL_CAPACITY_FOUR_INPUT_MEASUREMENTS.json。新未冻结profile提议将body资源cap改12288，单独限制system+user content合计8192；actual完整输入token上界=实际content UTF8 bytes+88+2，最大8282，6144输出+1余位合计14427≤16384（余1957）。schema/JSON封装只影响body资源界，不渲染成prompt，二者不能混用。原四case最大content5971，均能原样接受。此项尚未实现、未冻结、未生成、未授资格，不改任何旧失败或已冻结profile。

冷模型可在严格当前合法命令/once permit及应用重量工作锁下，一次显式empty-prompt load-only（官方done_reason=load在Completion前返回），核验实际ps digest/llamacpp/slot≥16384后才允许claim与唯一生成POST。UI/read-only availability不得装载；失败或取消/丢lease时invocation0，model仅留缓存无假结果。metadata检查只在claim前，generate消费绑定execution+requesthash的readiness；claim后不再次GET，不把已知预检失败记unknown。真正POST后超时/unknown保持fail-closed及持久历史。必须有冷模型可操作入口，不能仅因未loaded让用户永久等待。

2026-10-15 精确入口更正（优先于保留的初版假设）：独立port审查发现真实新builder为 `/api/chat`，system+user两条message，不是`/api/generate`单user。初版58byte只证明该单user特例，不能授生产容量。真实两条消息的官方qwen3.5封装88bytes；完整request≤7680已包含两content UTF8及JSON封装，因此render≤7768，input保守≤7770，最大6144输出与1余位要求13915；16384仍足。必须按真实system+user合同固定request所有字段，无history/tools/images/context/suffix/附加roles，本地模型本身SYSTEM/MESSAGE仍空。无生成诊断改用`/api/chat`、相同两角色及`_debug_render_only=true`；两种chat(native/legacy)官方分支均在实际模型Completion前返回。此前generate诊断尚未执行，实际生成仍0。当前profile仍原8192/BLOCKED，新的16384代码须后续独立任务和审查，不原地当已通过。

完整manifest/config/5原层实核全部PASS，Ollama0.40.1与llama-server二进制SHA已记录`.var/end-to-end-user-readiness/capacity-runtime-preflight.json`。ps为空；16GiB物理RAM、44%系统free、余盘15.195GB。装载前必须再核压力，不能拿旧压力当当前资源承诺。新profile无实际proof/生成；旧profile不改。初版保留如下，明确不执行其中错误单user预检：

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
