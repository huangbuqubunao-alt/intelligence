# Intelligence 正向门禁长期不收敛：根因判断（Antigravity，2026-11-12）

状态：根因判断已完成，**未进行任何新的模型调用**。旧的 REJECT 记录、原始输出、收据、费用历史均保持不变；本文只追加复核意见。

基线：`18f366b80e9f184795e44d7716f49d0ac418fb7f`（完整候选，接手时仍冻结且干净；交接后各分支没有新提交）。
本分支：`antigravity/task-user-readiness-20261112`，工作树 `/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`。

## 1. 直接阅读的材料（全部只读）

| 材料 | 路径 / SHA256 |
|---|---|
| 冻结 oracle | `readiness-bounded-synthesis-v4-r2-trial/.var/.../prepared-20261107-r1/input-only-oracle.md` = `0b6dbae6…e29d`（与记录一致） |
| r2 实际请求 | 同包 `cases/public-aircAruvnKk-en/artifacts/provider-body.json` |
| r2 原始正文 | `end-to-end-user-readiness/.var/bounded-synthesis-v4-r2-trial-20261107-r1/public-aircAruvnKk-en.final.json`，raw_text SHA `50c09a22…2414`（与记录一致） |
| r2 Root 语义 | 同目录 `.semantic.json` = `d7d0feee…2962` |
| r2 独立评审 | `readiness-v4-budget-final-validation/.var/independent-r2-semantic-20261107/public-aircAruvnKk-en.json` = `ab104958…b454` |
| v2 同案例原始正文与 PASS | `end-to-end-user-readiness/.var/bounded-synthesis-v2-trial-20261106-r2/public-aircAruvnKk-en.{final,semantic}.json`，**oracle 同为 `0b6dbae6…`** |
| 提示词源码 | `src/youtube_intel/system_synthesis.py`（v1–v4 契约），`distillation.py` L995–1020（TASK-022 原契约），L3318–3340（GLM grounding 契约） |
| Summary 生成 | `src/youtube_intel/extractive_summary.py`，`runtime_composition.py` L223–235 |

## 2. 五个问题的逐项结论

### 2.1 模型能力是否不足？——**没有证据证明不足**

- r2 的事实、限定、来源归属、引用全部通过独立核验（独立报告前 5 项 PASS）。
- **同一案例、同一 oracle（`0b6dbae6…`）下，v2 英文输出被独立评审和 Root 判 PASS**。v2 的核心判断是“教程用 Sigmoid 只是入门模型，访谈指出 ReLU 更易训练；这是训练实践区分，不是数学推理可靠性证据”，并给出面向用户的含义“不要从教程公式推断 Sigmoid 仍是首选”。也就是说，这个模型在同一材料上产出过评审认可的判断。
- r2 的 `usage`：输入 11565、输出 **955** tokens（含推理）。正文 3207 字符约 700–800 tokens，推理只剩约 150–250 tokens。官方文档写明 K3.1 Pro 默认 `max`，支持 `low/high/max`；历次配置都是 `low`。历次输出 token 为：v1 1655、v2-en 798（PASS）、v2-zh 738、v3 1183、r2 955。**v2 英文在同样很小的预算下通过**，所以 `low` 不是失败的必要条件，只是可能的贡献因素：在 r2 的输入几乎翻倍（完整 Summary 直读）之后，逐项比对需要更多推理。这一点尚未经过对照实验证明，v5 把它和契约修正一起调整，并如实注明两者无法单独归因。
- 能确认的模型弱点只有一项：在只有“翻译级新事实”的情况下，它选择输出正向结果，没有选择 NO_NEW，即判断校准不足。

### 2.2 提示词和输出字段是否诱导摘要？——**是，这是主要工程根因**

- TASK-022 原契约（`distillation.py` L995）明确定义了 Intelligence：“值得超越一次性 Summary 保留的、有证据、可修订的判断，例如实质结论、有意义的发展、有用的解读……”。
- v1–v4 system-synthesis 契约（`system_synthesis.py` `_CONTRACT`）用一条新的 system 消息**替换**了原契约，删掉了这段定义。剩下的契约约 3.8k 字符，主要都是禁止项；“什么样的正向是有价值的判断”只有一句阈值描述。
- 契约**完全没有定义五个输出字段**，只列出字段名。`important_new_information`、`meaningful_details`、`user_relevant_information` 这些字段名本身是摘要式的，模型会自然地把“Summary 缺少的原文片段”翻译后填进 `important_new_information`，再用复述把其余字段填满。仓库里另一套 GLM grounding 契约（L3329–3333）其实定义过字段用途，system-synthesis 没有沿用。
- 契约没有给出判断流程，例如“先列候选判断，逐项对照完整 Summary，翻译、改写或范围性提醒一律剔除，剩不下就返回 NO_NEW”。
- 结论：契约要求的是“新判断”，但输出结构和字段名都是“个性化摘要”。r2 输出正好落在这两者的缝隙里。

### 2.3 来源、已有摘要和兴趣是否留有合理新增空间？——**aircAruvnKk 几乎没有空间；IwglW 有空间**

- 普通导入路径（`DISCOVER_ONLY`）里的 Summary 是 `extractive-source / deterministic-excerpts-v2`：它把原文的前 N 段 Evidence **逐字**放进 `core_points`，`keywords=["source excerpts"]`，`one_sentence_summary` 是第一段原文截断。已验证：aircAruvnKk 的 6 个 core point 分别逐字等于 E01–E06；IwglW 的 5 个分别逐字等于 E01–E05（覆盖 100%）。
- 所以对这些材料来说，“超越完整 Summary”实际等于**“超越原文本身”**。对已覆盖内容做任何翻译、浓缩、重组，都只能算复述；能算新增的只有纯推断，以及没进入前 N 段的尾部片段（aircAruvnKk 的 E07）。
- aircAruvnKk 是 2017 年的神经网络入门教程，用户兴趣是“AI 推理/数学研究的可靠性、人工验证和 test-time exploration”，主题基本不相关。唯一未覆盖的 E07（Sigmoid→ReLU）与兴趣关系很弱。**这个案例的正确输出最可能是 NO_NEW**，至多有一个很窄的正向判断。
- IwglW（Gemini Deep Think 演示）与兴趣直接相关：演示只给出供应商单方面展示，没有展示判定结果，问题本身是可机械判定的交互题（目标随查询移动、160 次上限）。oracle 也明确允许具体的验证判断，所以这里存在真实的新增判断空间。

### 2.4 “摘要补充 / 新增判断 / 诚实 NO_NEW”定义是否一致？——**不一致**

| 概念 | 产品/oracle 实际含义 | v4 线上契约 | 后果 |
|---|---|---|---|
| 摘要补充（Summary 漏掉的原文事实，如 E07） | oracle：“翻譯原句…不足”，不算 Intelligence | 字段名 `important_new_information` 直接邀请填写；契约没说这类内容不足以单独构成正向 | 模型把补充当成正向理由 |
| 新增判断 | 有依据、有条件、可修订、超出 Summary 的判断 | 只有一句阈值描述，没有字段承载“判断 / 依据 / 条件 / 如何修订” | 判断被淹没在复述里 |
| 诚实 NO_NEW | 无新增判断时的合法结果（包括来源不涉及兴趣的情况） | 只有“如果没有……就返回”，没说明“来源不涉及兴趣”“只有翻译级新事实”都属于 NO_NEW | 校准偏向正向 |

### 2.5 评审是否有不合理要求或事实错误？——**未发现事实错误；但跨轮次判定不一致**

- 已逐项复核 r2 两份评审的引用：可靠性教训逐字位于 Summary `core_points[4]`（“網路能輸出正確的結果但是過程跟你想像中有差異…測試你的認知”）；层次结构保留在 `core_points[2]` 结尾（“不管這個是不是我們最終的網絡實際上的實施是另一個問題”）；布局限定在 `core_points[1]`（“這只是擺好看的設定”）。**全部属实。**
- 但 r2 `core_conclusion` 第一句已经提出“对其 Sigmoid 教程的历史限定：现代网络因 ReLU 更易训练而转向”。这正是 oracle 点名的“區分教學例子的 Sigmoid 與訪談談及的訓練選擇”，也是 v2 被判 PASS 的核心依据。两份 r2 评审只认定 `important_new_information[0]` 是翻译，**没有讨论这句 core_conclusion，也没有和 v2 PASS 对照**。
- 我的复核意见：**维持 REJECT**，理由更窄。r2 只是描述性地重述 E07，没有像 v2 那样给出面向用户的推论；同时大量填充已在 Summary 中的内容；而且该区分与用户兴趣基本无关。这个判定处在边界上，同一 oracle 下 v2 PASS、r2 REJECT 已经说明：**该案例的正向判定噪声很大，不适合作为第一道或唯一的正向资格门**。
- oracle 示例里的“提出有條件、可復驗的實現/實驗選擇”与用户本轮禁止的“固定实验建议式价值”存在张力。未来评审应把它理解为“若有则须扎实”，而不是“必须有”。

## 3. 为什么前几轮不收敛

1. 每轮都用 aircAruvnKk-en 当第一例，而它是正向空间最小、判定最边界的案例。只要失败就停止，后面真正能检验正向能力的 IwglW 从未执行。
2. 每个版本只修补上一轮评审指出的那一个点：v2→v3 统一来源级归属，v3→v4 直读 Summary。契约越来越长，禁止项越来越多，但“新增判断”的定义和字段语义始终没有补回。
3. 推理预算始终是 `low`。
4. 每次都先跑约 2 小时的全量工程测试，再花钱跑一例；工程绿灯和语义质量之间没有关系。

## 4. 最小方案（据此实施，不重建系统）

1. **一个新 profile `v5-judgment`**，不修改 v1–v4 的历史契约和 hash：
   - 在 v4 全部规则（事实、归属、Evidence、防注入、完整 Summary 直读）之上**追加**：恢复 TASK-022 对 Intelligence 的通用定义；定义每个字段承载判断的哪一部分；加入写作前判断流程，翻译、改写、“来源未涉及兴趣”、通用提醒一律不算，Summary 缺少的原文只算判断的输入。
   - `reasoning_effort` 改为 `high`，输出上限按推理需要上调，并相应调整费用预留公式。
   - 不硬编码任何视频内容、关键词或“实验建议”模板。
2. **免费先行**：离线渲染全部 8 个冻结输入（同一 Source、Summary、refs、兴趣），校验大小、预留和契约，并加入单元测试确认契约不包含案例特有内容。
3. **执行顺序最小化**：资格矩阵仍是同样 8 例、同一 oracle，但调用前把顺序固定为 IwglW-en → IwglW-zh → aircAruvnKk-en/zh → 4 个合成负控。最有信息量的正向案例先跑，失败即停。
4. 调用前用 addendum 澄清评审口径（见付费方案），不在看到结果后移动门槛。
