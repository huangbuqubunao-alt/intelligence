# 长字幕无损输入与引用编码：纯函数切片

Status: IN_PROGRESS（/root/long_lossless_codec_oct18，独立WT，0ae374f任务元数据基线）。Role Implementer，root指定独立worktree/agent；Base a073354（当前已接受工程+真实失败证据）。持续默认授权涵盖必要任务内整改；不申请逐文件批准。此切片不授任何模型资格/执行准入。

## 目标、边界与并行决定

现真实49.6min/2406cue/114完整Evidence原输入实际30238 tokens，旧20条上限不能满足普通用户完整提炼。只读已审无损方案见 LONG_CONTENT_READONLY_TOKENIZER_PROBE_PLAN.md。将其中**纯编码/反解码**单独做成可独立测试的最小模块；不接产品路由、schema、执行、持久化或模型。

原决定长协议共享核心等tracked40接受后串行，仍有效。root现明确允许此纯函数例外与tracked40并行：只新增 src/youtube_intel/long_grounding_codec.py + 对应 tests/unit/test_long_grounding_codec.py + 本任务独立handoff/证据，不修改任何既有产品或测试文件。共享state/Backup/distillation/domain/profiles/reader/SQL/前端接线继续等待；不抢迁移编号。作者如必要变更接口/文件先向root报告，非向用户重复审批。两writer无共享写入。完成切片不等于长内容可用了。

Reuse DIRECT标准库json/hashlib/dataclasses与已批准纯值/可信cue合同，REFERENCE现local_grounding原协议；不新增依赖、codegen、配置或网络。无真实模型/load/tokenize/正式数据访问。不得看私有blind holdout预期。

## 固定语义

1. 完整顺序原Evidence及cue。校验唯一身份、原hash/locator/index/time/text、连贯全覆盖，无多份权威歧义；不从字符串猜时间，不补cue或篡改来源。
2. 仅在**同一Evidence内部相邻且逐字符完全相同文本**使用RLE。每个原cue index/time/hash均保留；expand结果与原每条cue/原Evidence摘录逐字一致。不得trim/NFC/模糊去重、跨Evidence合并、静默截断。空白、Unicode/换行/重复跨界必须精确保留；沿用现有来源/质量边界，对超限显式拒绝。
3. 固定本次canonical顺序E1…En双射，绑定全部原Evidence ID/hash/locator/source identity。QA与runtime IDs不可混用。hash由canonical严格编码确定，不接受可变dict别名后悔改写。
4. 模型输出引用解码仅允许严格、冻结双射展开；拒绝未知/E01/重复/缺失/多余字段/类型混淆。NO_NEW先验证完整长度、唯一性、全集和顺序，随后纯展开；不补齐引用、不换立场、不修JSON、不改任何claim/text/uncertainty。普通claims的引用按既有合法shape检验，不得因alias允许无证据输出。严格输出shape须从现accepted local_grounding合同读取，在handoff列清；如纯切片无法保持其语义即先报告，不自创新的产品结果shape。
5. 原始public final wire bytes/hash和解码值/hash为独立值，提供后续持久proof所需确定性绑定；不读/记录thinking。此模块不声称输入权威/执行成功，未来必须由调用者在既有验证后使用，并经独立inputproof/receipt事务和反向reader闭包才能接生产。
6. 真实Sasha只做root指定已有隔离文件的只读编码roundtrip验证，不能调用provider；合成对抗样例明确标记。没有新完整render token/slot/资源/语义实证，不调大ctx或原20，资格保持关闭。

## 验收与交接

先类型/语法，最小函数+meaningful tests逐步验证。测试包含逐cue/逐Evidence精确roundtrip、不同分组同内容hash边界、跨Evidence重复不合并、空白/Unicode/控制字符、顺序/缺cue/重复identity/时间或hash错、E01/unknown/重复/缺失NO_NEW、额外字段/类型混淆、输入对象后续修改、claims/stance逐字段不改、output原wire保留，以及所有有界拒绝。测试不得修改现有断言或门槛。

focused pytest、Ruff、strict mypy src、diff check；旧short/cloud golden应保持零diff。独立handoff按模板，记录明确shape/限制与0模型IO，创建清洁提交并STOP。独立Reviewer对准确base…SHA审查/重跑，root接受整合前不可接入产品。完整长协议/迁移/保存主题/Backup Restore/实际模型验收是后续同一Goal必需，不能以本切片替代。
