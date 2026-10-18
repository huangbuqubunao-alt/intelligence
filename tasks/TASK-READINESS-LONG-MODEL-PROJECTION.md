# 完整长字幕模型可见投影：纯函数切片

Status IN_PROGRESS（long_lossless_codec_oct19；fe4cfba独立WT；仅纯新文件）。Base root@15ccb3f（已接受codec、root真实源/词表对照证据）。独立Implementer/WT后独立Review；root不写产品。

## 必要目标与严格边界

已接受codec证明2406cue114Evidence精确无损，但323768B packet是完整侧证明，不应全部作为LLM输入。仅新增 `src/youtube_intel/long_grounding_projection.py`、`tests/unit/test_long_grounding_projection.py`、对应handoff/证据。不得改任何已有产品/测试/Schema/registry/执行/transport/profile/资格/依赖/前端。此纯新模块与tracked40共享核心作者无写入交叉，root明确允许并行；全部生产持久化/准入/reader/Backup仍等tracked40和混合字幕补修接受后串行。用户持续默认授权覆盖必要整改，无逐文件审批。

Reuse DIRECT已接受long_grounding_codec、现VerifiedDistillationInput纯值及local_distillation_profile受信固定prompt、标准库；不新依赖/Provider/网络。代码必须未注册、无执行方法、无tokenizer或模型IO。

## 最小接口与语义决定

建议 `prepare_long_projection(packet: EncodedGrounding, value: VerifiedDistillationInput, *, source_snapshot: bytes, summary_snapshot: bytes, policy_snapshot: bytes) -> PreparedLongProjection`，可在不增文件范围内选择更简洁等价接口，先向root回报。

- 先expand/验证packet，与value全部当前完整timed Evidence（ID/time/excerpt/hash/timed identity/locator）逐项严格相等、同video/provider；不能按20截输入，不能混用其他数据库alias，不能仅检查数量。YT_TIMED首切片；LOCAL_TEXT拒绝，不授LOCAL资格。
- **模型可见context保留旧accepted builder的全部原语义字段**：video_id/video_title/source_display_name、全部personalization/focus/ignore/style/output_language。原Evidence仅改为冻结E1..En及原start_ms/end_ms、有序runs[{text,repeat}]。repeat exact正整数，展开逐cue文本以原换行连接必须等原excerpt；不trim/NFC/总结/跨Evidence合并或删遗漏。原模型本来仅看到Evidence范围，原逐cue index/time/hash仍完整保存在packet侧证明，不减少旧模型可见的时间粒度。
- 原builder**没有独立Summary字段**。本切片不擅自新增Summary给模型；完整Summary权威快照与身份只原样保存在独立side snapshot，全部source/policy快照同理。opaque snapshot只严格JSON/UTF8/资源校验和无损冻结，不自授完整性或来源权威，后续factory/proof必须验证完整真实记录，不得用空/伪快照获准入。
- 模型system只复用原受信YT_TIMED prompt，并追加精确定义lossless RLE/text重复次数及alias引用的固定说明。源title/Evidence/policy等仅JSON数据，不拼系统指令；保留归因、个人经历不推广、reported不是独立验证、必要限定、不确定性/立场/语言/注入隔离全部既有规则。不内置已知样例答案，不修模型输出。
- 返回冻结独立 model_context_wire、messages_wire、semantic_snapshot_wire 及各自hash/codec_input_hash（命名可等价）；原全部value/opaque快照保留在side，不把侧证明大包直接送模型。bytes不可被后续可变对象影响；来源值变化严格反映hash。原public/decoded输出仍由既有codec分开处理。
- 新独立projection/prompt版本常量进入side及消息身份。不注册profile、不构造可调用transport、不沿用旧short schema/profile身份或预算绕20。positive仍≤20、NO_NEW新长schema需全N唯一原序；本切片不新增schema/ctx/options，待完整messages离线测量后冻结，旧short/Cloud完全零diff。
- 所有JSON有界、duplicate-key/NaN/Inf/bool冒int/错UTF8/未知字段等严拒。资源边界精确记录，不能借扩大安全上限掩盖模型预算；没有token/slot证明就不声称可执行。pure验证不能代替authority或输入证明。

## 验收

先最小类型/语法，meaningful测试：完整114合成投影及逐原excerpt严格展开；同Evidence重复与跨界重复；原metadata/personalization/policy/语言不漏；Summary只在side完整保留不进model、不可变和hash绑定；任一Evidence/locator/hash/video/provider/顺序/数量不匹配拒；错包/缺失或非JSON snapshot拒、Unicode/控制字符/注入字符串始终数据；bytes/depth等真实资源边界；旧short/Cloud输出golden不变。Ruff/strict mypy src/focused tests及既有grounding相关回归/diff。

真实源/完整renderer/tokenizer由root随后独立QA，作者不读盲holdout或thinking；0模型/网络/Tokenizer IO。只创建范围明确commit+handoff并clean STOP，不main。APPROVE后root整合复验。此切片不是完整长协议或Goal完成，后续不可变inputproof/receipt/反向closure/兼容备份/实际语义仍是必需。
