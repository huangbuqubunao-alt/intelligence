# 固定9b失败后的单次官方模式隔离验收提案

2026-10-13，待具体批准，未实现/未执行。仅研究验收，不授权正式采用或资格reader激活。

## 已完成及停止

固定 qwen3.5:9b-q4_K_M nonthinking-v1 原首例真实一次协议SUCCEEDED，但独立语义FAIL四项：将讲者暂定成果变成事实、探索数量泛化、人类水平/IMO归属错置、缺人类核验及广泛评估判断。原finalcontent/opaque response/hash/输入/失败保留。后3例没有准备或调用；未重复同一模式抽样择优，正式资格false。

## 提议的唯一新增实验

复用同一已批准安装digest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90、现有Ollama0.40.1及原v5角色隔离prompt、原结构/严格Evidenceparser、原真实中英与NO_NEW15/注入四例/原语义阈值。**只改原生think=true及官方general-thinking固定采样temperature1.0/top_p0.95**；top_k20/min_p0/presence_penalty1.5/repeat_penalty1.0/seed20261013/ctx8192/predict4096/既有300秒请求上限保持。不是8b曾失败的配置换名：确切权重/digest/version独立绑定；不保证成功。

官方Qwen3.5-9B模型卡2026-10-13复核：Quickstart说明默认thinking，Best Practices及Quickstart采样段均一致给出上述general-thinking参数。来源 https://huggingface.co/Qwen/Qwen3.5-9B 。这是可用模式与官方设置依据；不能据此证明本项目语义可靠，也不代表每一参数效果已做实证消融。Ollama原生think与参数仍须固定installed源码/support检查及独立预输出审查；不使用不支持的/think文本开关，不升级运行时。

实验是“原生推理模式可能改善来源边界判别”的明确假设，不能预先称修复。只有最终公开结构化content进入现有parser/独立语义审查；思考字段不读、不展示、不依据它改输出，完整原响应仅不透明保存hash。保留此前精确INTELLIGENCE marker表达适配，仅去既有marker，不修prose/claim_kind/引用/分类。

只新增版本化研究profile/freeze、受支持模式分支及合同tests；scope scripts/qualify_readiness_qwen35_intelligence.py、tests/unit/test_readiness_qwen35_research.py、独立docs/task/handoff。生产distillation/state/runtime/config/schema/deps/正式数据不改。用新独立worktree/全新每例DB路径，不复用旧prepared/results/permit，不覆盖原失败。原冻结corpus/semantic政策hash必须完全相同；代码/profile/input/model/runtime全部freeze，prepare-only无推理，独立审查sealed inputs后root才给一次外部绑定许可。

固定顺序：real-deepthink-en→real-deepthink-zh-cn→no-new-fifteen→source-injection。每例最多一次真实本地调用，总最多4次，前例独立原标准PASS才可后例；任何超时/预算/未知执行/协议或语义决定性FAIL即停，不reroll、不切seed/profile、不补提示/修结果、不扩大context/output或删Evidence。旧4P1标准保留，不将NO_NEW误作正向代替，调用账本及费用0Cloud真实保留。声学与洞察重量任务串行，只有该重量模型，free space>10GiB，不停止用户其他任务。

全部通过也仅是research资格证据；现有旧YT receipt不授LOCAL权力，普通production reader仍关闭。要正式版本化生产准入须另行精确检查/独立审查，不复制boolean。已批准LOCAL最多8例仍依赖此原四例全PASS及新LOCALcode/corpus/profile冻结；任何一项FAIL都不执行该8例。保存/主题/来源/Backup恢复及最终完整回归没有因研究成功而免除。

## 风险与批准依据

官方thinking可能更慢或耗尽原输出预算，也可能继续失真；失败即保存并停止，不能承诺其必然使链路可用。此前固定9b批准明确要求首个决定性失败即停，本轮已遵守；重新开启一种冻结模式不能从“继续”推定。用户全局AGENTS敏感模型边界、既有冻结研究政策都要求具体决定，因此申请仅上述有界隔离新模式，不请求新下载/付费云/正式配置或自动采用。其他已批准字幕/界面整改继续。
