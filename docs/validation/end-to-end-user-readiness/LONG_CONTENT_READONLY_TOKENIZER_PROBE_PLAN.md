# 长内容容量只读诊断（不改产品、不生成）
2026-10-16，当前任务持续授权范围。现49.6分钟公开Sasha快照89221字符/2406原cue/114完整coverage Evidence；单改支持文案不能关闭完整提炼OPEN。先核验单次完整处理是否可能，不能未经证明就新增多调用Schema，也不截20条或改历史。

DIRECT已安装Ollama0.40.1的libllama.0.5.0.dylib，SHA256 72d39b320e896b29a6937214d0e2b8361ea4f094f8c437fc39b9f72571fd7112；REFERENCE其固定llama.cpp b11351 commit631109b34da437a3c4a5ebd75091d677671392e3官方include/llama.h与ggml/include声明。header明定model_params.vocab_only为只载词表不读权重；只在/tmp构建独立QA helper，打开固定GGUF只读、vocab_only=true/n_gpu_layers=0，不创建model context、不调用decode/generate，不连接Ollama内部runner端口，不改正式或候选生产代码/配置/依赖。标准系统clang与现有官方dylib，不安装下载权重；header及许可证来源/哈希记录，不复制实现代码。

helper仅对完整公开源构造的原始输入与固定renderer计算token数，用原Ollama相同库/词表/parse_special/add_special语义。先做空/Unicode/角色token小样例，严格错误退出；资源超时30秒、内存预期<512MiB，单进程，无任何generation。输入文件与输出元数据留本任务私有目录，不读任何thinking/正式owner文件。若实际ABI/词表身份/资源不满足即停，不能用估计数当生产容量。

本诊断不是生产实现、不是模型资格或放行。若完整长内容单次预算可行，仍须独立版本化来源/人数上限与NO_NEW全覆盖合同、模型输出预算/真实语义/恢复审查；若不行才设计明确可恢复父子执行方案。现有容量工程按已审bytebound继续，保持0生成/空资格。
