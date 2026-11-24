# IQ2_M 唯一实际例独立语义审查

Reviewer `/root/long_completion_review_r1`，专用review WT `/Users/developer/Documents/yia-worktrees/readiness-model-diagnostic`，起点 `b6662931369852637a7800af75885af9c70309de`。只读原始实际输出、冻结source-case、原18cue/2Evidence请求/schema、once/capacity及安全结束证据；没有重新跑测试、HTTP、模型、信号或后续样例。

**结论：REJECT_STOP / FROZEN_SEMANTIC_GATE_FAILED。** 当前IQ2诊断已结束，模型资格继续closed，不授权修补/重试/后续case。正常JSON与INTELLIGENCE分支不足以通过原语义门。本结论只裁决这一次冻结候选，不推断所有模型或整个量化家族的能力。

## 已通过的实际执行与结构检查

原始 `generation-raw.json` SHA **`95feff12bd6f9250bbfb58c500234b46e4d5766fc2ea599b6d73301366b8d03c`**，位于作者WT `.var/model-diagnostic-iq2m/real-once-20261025/`。HTTP200，done=true/stop，generation **32.2719549579997s**，prompt722/cached0/eval506<8192，无thinking。parent总79.48389829100051s含文件/加载/metadata，与生成耗时分开。empty preload1.818157790999976s、空content/load；global/local once marker字节相同，SHA `4b2ce3e4f25df42191323649c3151670e54ae031eebfdadc60df0850267d0ce2`，共一次empty preload+一次真实generation，非输出截断或预算耗尽。

逐项检查原positive schema必需/允许字段、字符串/列表/引用整数类型、enum和额外字段：**PASS**，采用显式完整positive branch验证，未安装依赖。解析后的diagnostic-result与raw正文完全相等，raw_hash匹配。两Evidence正确且无遗漏重复：`4750f3da...`0–46320ms、`c0eb7495...`46320–62600ms，stance均supporting。引用定位结构PASS不代表被定位内容的解释正确。

实际freshRAM6211551232B>=5796860396B；完整nativeN722/P8192/C16384/required8916、tokens列表长度和预先idle单slot一致；capacity SHA `efab6fe36a02f2e7931cc13105e30d8feda0018eab74292366a9b32801afbdff` 与once绑定一致。request/schema hash复算一致，原输入与门槛没有被事后替换。

## 语义缺陷及原文对照

**P1 — `meaningful_details[1]` 丢失公共版/竞赛版比较关系，并增加已证明的能力提升说法。** 输出为：`The source indicates a qualitative shift in reasoning capacity ('very similar' to the previous Deep Think mode) demonstrated by solving problems at an 'IMO gold-medal standard' level.` 原38960–50440ms描述的是面向用户模式与用于IMO金牌标准模式之间的相似关系；没有“previous mode”提升比较或对当前公共版已证明IMO能力的结论。输出将比较对象改成泛指previous mode，再把IMO结果接到qualitative shift，未保留冻结retain[2]要求的公共版与竞赛版区别。输出包含very similar，但对象/能力归属仍发生偏移；本审查没有指称它逐字写了equal。

**P2 — `important_new_information[1]` 将猜测转为实际数量范围。** 原31760–35440ms含`it seems`及`20 or100`，是发言者对内部探索的估计。输出却说`notes it involved exploring significantly more possibilities (20-100 ideas)`。来源归因存在，但明确猜测限定消失，两个模糊替代数变成实际区间，违反原system保留猜测与measurement limits的要求。首条“anecdotal”说明不充分保留这个具体数量的不确定性。

**P2 — 缺失冻结retain[3]要求的必要验证。** 输出有“非独立验证的轶事”和“不可泛化”的局限，未保留仍需人工数学正确性核验这一必要条件。数学证明有效性是本case实质边界；只区分来源与独立验证，尚未表达需核验的正确性和验证责任。不得在审查时给模型补写此项以通过。

输出确实保留Google DeepMind来源归因、曾未解决猜想与不同方法，并给出实质内容；拒绝理由不是无正向JSON，而是上述语义偏移和必需边界丢失。原固定expectation/source-case SHA `c751f9a5c04f90ccd486c552a8f332ed386ced341f524115ce8627985dc798a3`，仍按该标准审查，没有临时加严或降低标准。

## 结束安全与证据

actual `after-result-native-slots.json` SHA **`5588c3b71415f28880126bf1477030cf542001d8f2aaaa7df6b5162b8771cbe5`** 单slot is_processing=false；completed log SHA **`b37fe30f73a4b8fb8f14220815284555183bc9440f3885daf587edf4afdb689f`** 有正常完成、release、all slots idle。root `result-stop-cleanup-proof.json` SHA **`10de7370992a877dd21893b96f3559d8c28b182e6ee55d0cbbf38de5a38e639a`** 绑定slot/log并记录随后对自有25107正常SIGTERM、daemon/runner退出与端口关闭、无其他进程被杀。Reviewer核验这些捕获证据，未亲自发送信号。

新证据 `/Users/developer/Documents/yia-worktrees/readiness-model-diagnostic/.var/iq2m-semantic-review/review-evidence.json` SHA **`178d47f370411af68b6dc9365b1d84aef746a51b1e38301683c680646057a978`** 保存逐项比较和所有原始文件hash。只有本新handoff受Git跟踪；未改任何旧package绑定文件、raw、model output或资格。本候选FAIL后STOP；普通用户正向完整链路仍未证明，不能从本次结构成功授资格或采用main。**提交后clean STOP。**
