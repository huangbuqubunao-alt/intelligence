2026-10-16 09:32 本机无生成QA完成：完整公开字幕114 Evidence，108190 UTF-8 render bytes，实际固定runner /tokenize得到30238 input tokens；+6144输出+1余量=36383，16384/32768都不能完整容纳，65536仅token算术可行，资源/生产预检/语义尚未证明。一次空messages load-only、3次tokenize、0 generation、资格false；准确证据见 LONG_CONTENT_EXACT_TOKEN_QA_2026_10_16.json。起初task-owned ASR lock目录未初始化，在任何load前失败；原失败保留，随后仅创建私有排他锁并使用ps -ww完成身份检查。此计数不绕20限制、不授admission、不声称长内容已支持。下一步只读评估保留全部原cue映射的rolling projection与独立长内容协议，当前短输入容量工程不扩围。

2026-10-16 替代QA方案已获独立只读复核（local_text_review_resume，聊天STOP）：固定b11351 `/tokenize`仅调用词表tokenizer、不创建生成任务/不decode；显式content为完整rendered纯文本、add_special=true/parse_special=true/with_pieces=false。仅在本任务一次明确 `/api/chat messages:[]` load-only且ps原为空后，按服务父子关系取得唯一新runner，不扫描未知端口；校验UID/PID/starttime/父PID/已固定universal含ARM binary SHA/modelblob/loopback args/实际slot，并在调用前后复核。该load-only会创建context/装载权重，称无生成预检，不称整个流程vocab-only。当前Mac ps不支持arch字段，相关失败已保留；不得据uname推断进程实际slice，实际selected slice未单独证明，计数仅绑定当前真实runner而不是x86 dylib。若PID/端口/身份变化即关闭、不换端口重试；只允许该已验证loopback `/tokenize`，有界请求/响应/超时，不调用completion。确认无其它本应用重任务及资源足够，保留本机接收端证据。

本次输入由现有隔离公开字幕/全部114原coverage及其hash重建，手工QA请求不是合法生产admission，不赋Evidence/成功/资格或绕20上限。只输出计数与hash，所有模型generation仍0。它只用于判断是否值得单次完整协议；真正修复20及NO_NEW/text schema要另做独立版本化，不直接把token结果拿去放行。root原Chelper计划维持停止，下面旧段仅为历史。

2026-10-16 诊断分支结果：已安装libllama.0.5.0.dylib为x86_64，实际本机arm64且llama-server ARM slice静态链接；默认clang arm64链接失败，完整日志/tmp/readiness-vocab-native/compile.log（ld found architecture x86_64 required arm64）。未得到/执行helper，0 tokenizer/生成调用，不把最后cat命令exit0当编译成功。不改成Rosetta、不安装依赖、不碰生产代码。官方头7文件268735 bytes及来源SHA保存在/tmp/readiness-vocab-native/headers-sources.json；仅用于声明核验。后续只读评估任务固定runner公开/tokenize接口能否替代，尚未执行；不能扫描未知端口或把未验证接口当模型资格。下面是保留的原helper计划，当前已停。

# 长内容容量只读诊断（不改产品、不生成）
2026-10-16，当前任务持续授权范围。现49.6分钟公开Sasha快照89221字符/2406原cue/114完整coverage Evidence；单改支持文案不能关闭完整提炼OPEN。先核验单次完整处理是否可能，不能未经证明就新增多调用Schema，也不截20条或改历史。

DIRECT已安装Ollama0.40.1的libllama.0.5.0.dylib，SHA256 72d39b320e896b29a6937214d0e2b8361ea4f094f8c437fc39b9f72571fd7112；REFERENCE其固定llama.cpp b11351 commit631109b34da437a3c4a5ebd75091d677671392e3官方include/llama.h与ggml/include声明。header明定model_params.vocab_only为只载词表不读权重；只在/tmp构建独立QA helper，打开固定GGUF只读、vocab_only=true/n_gpu_layers=0，不创建model context、不调用decode/generate，不连接Ollama内部runner端口，不改正式或候选生产代码/配置/依赖。标准系统clang与现有官方dylib，不安装下载权重；header及许可证来源/哈希记录，不复制实现代码。

helper仅对完整公开源构造的原始输入与固定renderer计算token数，用原Ollama相同库/词表/parse_special/add_special语义。先做空/Unicode/角色token小样例，严格错误退出；资源超时30秒、内存预期<512MiB，单进程，无任何generation。输入文件与输出元数据留本任务私有目录，不读任何thinking/正式owner文件。若实际ABI/词表身份/资源不满足即停，不能用估计数当生产容量。

本诊断不是生产实现、不是模型资格或放行。若完整长内容单次预算可行，仍须独立版本化来源/人数上限与NO_NEW全覆盖合同、模型输出预算/真实语义/恢复审查；若不行才设计明确可恢复父子执行方案。现有容量工程按已审bytebound继续，保持0生成/空资格。
