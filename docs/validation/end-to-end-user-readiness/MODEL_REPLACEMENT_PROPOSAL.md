# 洞察模型阻塞后的精确隔离替换验收提案

日期：2026-10-13。状态：待具体批准，未下载、未执行、未启用。

## 实际阻塞

已安装固定 qwen3:8b 经 v3–v11 不同冻结实验均未通过原语义门槛。最新 v11 实际一调用、完整响应、正确来源名且未超输出预算，但仍虚构20–100+同时探索、将讲者自己的三种想法扩成一般人类能力比较、混合猜想与IMO并遗漏核验限制；独立审查 REJECT。无新洞察与协议成功不替代正向资格。原失败/输入/阈值不改写，停止该方法的重复调参。

## 申请范围

仅新增一份本地权重候选 `qwen3.5:9b-q4_K_M`，复用已经安装的 Ollama 0.40.1，不升级应用、依赖、运行时或系统工具。不调用任何付费云/外部推理，不改变正式数据、凭据、配置、model default 或资格门禁。

来源为官方 Ollama registry，固定 tag对应的已读取 manifestSHA与每一blobdigest见 MODEL_REPLACEMENT_PINNED_MANIFEST.json。下载前核对同一manifest，下载后核对安装digest及blobsha，任何改变则停止，不改为latest。仅使用现有Ollama管理的本地model cache；保留所有旧权重、失败记录与receipt。总层字节数6,550,825,373（约6.55GB，含必要projector与元数据），不删除其他文件。现查可用磁盘22GiB，执行前再次确认下载后至少10GiB余量，不足则停止。

只有本地文本洞察资格使用该候选；不启用视觉、工具调用、网络搜索或新产品能力，不发送图片/正式owner文本。若当前运行时不支持，则停止，不暗中升级。16GiB本机一次只加载一份重量模型；先释放本任务已加载的8b，再串行验收。

冻结旧真实输入与原语义政策（英文、中文、无新洞察、注入、15项覆盖；真实正向来源）以及新模型/运行时/digest、官方采样、Schema与代码后才执行；每案例最多一调用、原始响应保留，不改写claim_kind或prose，不seed reroll，不以更大模型或厂商benchmark声称合格。超过窗口/Evidence上限的内容另做安全链路设计，不静默裁剪。若失败，保留失败并报告，不循环换模型。

成功也仅说明隔离资格达到标准；需独立审查、真正普通factory资格绑定、保存/主题/来源/重启/备份恢复、完整回归后，再请求具体正式采用，不复制production_qualified布尔值。

## 复用及风险

DIRECT：现有Ollama loopback HTTP、固定模型digest验证、严格解析器、EvidenceResolver、ledger/checkpoint、资格验收边界。官方模型许可证Apache2.0。新模型不会自动更可靠，较新架构兼容性、延迟和内存均需实际验证；这是一次有边界的替换实验，不保证通过。相比此前已只读核验的 `qwen3:14b-q4_K_M` 约9.28GB层下载及较高内存需求，9b候选降低本机资源压力，能力以本项目原资格实测为准。

官方来源（只读检索，不复制安装命令到生产）：
- https://ollama.com/library/qwen3.5:9b
- https://huggingface.co/Qwen/Qwen3.5-9B
- https://registry.ollama.ai/v2/library/qwen3.5/manifests/9b-q4_K_M

## 必须先获具体批准的原因

此前模型整改批准明确限定“只复用已安装固定Whisper与qwen3:8b，不下载”；用户全局AGENTS红线也要求新增权重/依赖相关动作先具体批准。本提案只申请上述一份固定权重的隔离下载和验收，不申请运行时升级、Cloud或正式采用。其他已获批准的字幕/备份/UI修复与回归继续。

独立 bounded advisory（intel_bounded_review）：APPROVE 提交本提案供用户具体批准，官方manifest字节核对一致；不是下载授权或资格批准。总层字节6,550,825,373，config177字节，总6,550,825,550字节。
