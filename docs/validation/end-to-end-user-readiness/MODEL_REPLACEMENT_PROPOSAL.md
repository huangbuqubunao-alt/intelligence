# 洞察模型阻塞后的精确隔离替换验收提案

日期：2026-10-13。状态：待具体批准，未下载、未执行、未启用。

续作授权记录（2026-10-13）：用户明确回复“批准固定权重隔离下载与验收”。执行前重新获取官方 manifest，SHA256 与固定 56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90 完全相同；现有运行时 Ollama 0.40.1，模型运行列表为空，缓存卷可用 22,175,809,536 字节，下载总计 6,550,825,550 字节后仍超过10GiB余量。已开始仅此固定 tag 的下载；尚未验收、未推理、未给予生产资格。最终安装 digest/blob/hash 仍须再次校验。原提案正文与失败记录保留。

安装核验续记（2026-10-13T05:17:30Z）：下载完成，官方原 manifest blob 与固定文件逐字节相等，config 与每一原 layer 大小/SHA 全部一致。Ollama 本地 wrapper 的 raw SHA 为7dd7bb…，其唯一额外层引用 byte-identical 的56671c2…原 manifest，原字段和层未改；API 精确 tag digest仍56671c2…。完整证据 MODEL_REPLACEMENT_INSTALL_RECEIPT.json；余盘15,469,645,824字节。状态仅 DOWNLOAD_INTEGRITY_PASS_QUALIFICATION_PENDING，实际推理0，生产资格false，正式配置未动；独立安装复核及预输出 harness 审查仍待完成。

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
