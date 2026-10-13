# 隔离本地模型整改审批范围

这次批准只授权工程整改和资格验证，不授权生产采用或改写旧资格。

2026-10-12：用户对两次呈现的同一具体范围明确回复“批准该隔离整改与真实资格验收范围”“批准该精确隔离整改范围，继续实施和验收”。本方案工程与真实验收门禁已批准；正式采用仍待合格结果及单独批准。

1. 声学：只读使用此前已批准安装的 `mlx-community/whisper-large-v3-turbo`，revision `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`，weights SHA256 `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`。沿用既有 mlx-whisper 0.4.3 / MLX 0.32.0，不下载第二模型或升级运行时。
2. 为修复已证明的中长录音解码/尾部重复、停顿和控制样本幻觉，在独立工程 worker 中开发基于现有 PCM/ffmpeg 的确定性静音边界分段和时间映射。解码参数、边界参数、输入/期望文本和样本哈希必须在候选执行前冻结；不得根据候选结果修改样本、挑选子集、丢弃失败、修剪幻觉文字或降低现有准确率/覆盖/遗漏/非有限时间门槛。对任何变更生成新的 tuple/版本；旧证据和 FAILED receipt 保留。
3. Intelligence：只使用已安装的 qwen3:8b，digest `sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`，通过已有 loopback Ollama 与结构化契约，在独立 DB 上运行真实本地资格样例。允许修复本项目 prompt/解析/证据绑定的根因；样例与语义标准先冻结，prompt/实现变更使旧资格失效。不会依赖 Scoring/Summary 资格或手动 True 获得 Intelligence 资格。
4. 不访问付费云、真实凭据或正式 owner 配置；不写真实 Vault；不改 Schema、依赖、锁文件、SDK 安装或工具链；不在 main 实现。私有推理输入仅使用非个人的固定测试资料和此前隔离声学 corpus，不以正式用户资料做模型实验。
5. 合格能力进入普通用户配置与生产执行前，必须有完整真实正向产物、恢复/安全验证、独立审查及具体最终采用批准。模型未达到既有门槛时继续关闭，不能宣称所有链路完成。

批准依据：仓库 AGENTS.md §5 限制安全敏感/生产变更；既有 `docs/decisions/V1X-PHASE9-DR-001-acoustic-qualification.md` 明确要求 materially changed profile 的 explicit decision，Phase9R 报告 §47 要求 separately authorize silence-aware segmentation。原任务只批准旧 profile，故本次冻结 profile 的整改需要明确范围批准。用户已授权本轮全面修复；其他常规修复、只读诊断和用例建立继续执行。
