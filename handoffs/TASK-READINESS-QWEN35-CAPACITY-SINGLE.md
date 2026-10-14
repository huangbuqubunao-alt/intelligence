# READINESS-QWEN35-CAPACITY-SINGLE 实现交接

2026-10-14，Implementer `/root/intel_bounded_review`；独立 Reviewer待主控安排
`caption_resume` 在Schema作者STOP后执行。Base
`bc110441627c0afd87b364c723c77a392a1c2145`，独立tree
`/Users/hua/Documents/yia-worktrees/readiness-qwen35-capacity-single`，branch
`codex/task-readiness-qwen35-capacity-single`。用户具体批准在
QWEN35_CAPACITY_SINGLE_CASE_PROPOSAL.md末尾，未授权作者真实推理/资格/正式采用。

## 实际范围与复用

DIRECT既有installed fixed9b身份、Ollama0.40.1的已冻结static参数路径、标准库JSON/
SQLite/hash/exclusive fsync audit、已接受research transport与ordinary v5生成器/严格
parser；REFERENCE旧V2profile/freeze/公开输入/真实失败原请求。不新增任何依赖。
图谱查询研究脚本无节点，按指定文件fallback。repo协议/任务/PRD/system/reuse/具体
批准和旧freeze/FAIL已读；未重新读private thinking或调用服务查模型。

仅六个文件：研究脚本、新V3profile/freeze/input准备receipt、新focused合同tests、本
handoff。没有src/Schema/API/配置/qualification reader/模型安装/旧tests/旧V1V2冻文件
改动。第一次误找独立APPROVAL文件不存在，实际批准已追加到proposal；不重问授权。

- 新profile `readiness-qwen35-9b-thinking-capacity6144-single-v3`，仅num_predict6144；
  thinktrue/T1/topP.95/topK20/minP0/presence1.5/repeat1/seed20261013/ctx8192/300s不变。
- V3 load/prepare/execute先拒绝所有非原英文case，不读permit/freeze、不建目录/DB。
  CLI仅新V3/原EN；旧V1/V2 CLI及execute不重开，原模块合同测试仍可离线审计。
- 完整绑定旧V2 actual request/prepared/result/verified输入/harness与18DATA原SHA；
  新freeze覆盖全部旧core/corpus/政策/runtime/install与新harness/tests/profile/task/
  proposal。旧core与旧tests hash必须一致，ordinary v5generate hash仍92c003ee…。
- 离线Projection仅调用ordinary v5纯wire组装，覆盖本地_request保存body，零接口访问；
  `{}`只供生成器返回结构，**不写ledger/Artifact/语义结果，也不接纳为模型输出**。
  wire逐项比较原actual request，只允许options.num_predict改变。真实dispatch前再
  同样比较body，任何新消息/schema/options/model/input差异直接阻断。
- 新manual command包含新profile，通过既有deterministic算法自然产生新execution ID；
  没有改源码authority、硬改ID或替换消息。VerifiedInput完整hash与原V2逐字节一致。
- 外部root一次permit额外绑定单例ID集合/max1/projectionSHA/baseline requestSHA，保留
  exact安装/runtime/static意义/资源/重模型互斥与无未知执行校验；没有作者permit。
  execute重验DB/input/all DATA完整集合/projection，exclusive许可/生成marker不覆盖，
  结果成功失败都停止，不主动再次continue或推进case。原普通parser/markerdecode不改。
- thinking输出达到6144仍拒绝，原V1/V2恢复4096阈值。length/empty/timeout/unknown仍
  留opaque响应/marker并拒绝重启再调用。研究transport始终production_qualified false。

## 检查与保留失败

- 新合同TDD初 **23 ERROR**（未实现V3profile），
  `/tmp/qwen35-capacity-tdd-red.txt`，未执行任何模型。
- 首green **91 PASS/1FAIL**，`/tmp/qwen35-capacity-first-green.txt`：prepare合同因
  尚未落盘新版freeze而FileNotFoundError。补完整实际freeze后通过；没有弱化断言。
- 初mypy研究脚本PASS；Ruff仅新测试一行E702，拆新语句后PASS，不格式化旧文件。
- 最终 `PYTHONPATH=src:. .venv/bin/python -m pytest -q
  tests/unit/test_readiness_qwen35_capacity.py tests/unit/test_readiness_qwen35_research.py`
  → **101 PASS /13.68s**，`/tmp/qwen35-capacity-final-tests.txt`。32新增+旧完整原模块69。
  原模块bytes/hash781baf63…与旧V2freeze完全相同；没有删/skip任何所谓旧73合同，
  先前73统计若含另项须由主控按其原日志核对，不能自填73单文件通过。
- 新32覆盖exact旧wire/input/18DATA/fresh ID、后3case在load/prepare/execute前拒绝、
  无rootpermit零文件/请求、旧CLI不重开、篡改policy/model/seed/caseorder/timeout、
  单例permit类型/额外case/prior/runtime互斥/未知执行/baseline/projectionSHA、4096
  完整响应在新budget下可解析而6144/length/empty/timeout拒绝、durable marker重启
  不再调用/productionfalse。都是fake wire合同，不是实际模型兼容或语义验收。
- py_compile PASS；`MYPYPATH=src .venv/bin/mypy --strict src
  scripts/qualify_readiness_qwen35_intelligence.py` → **103 files PASS**，
  `/tmp/qwen35-capacity-final-mypy.txt`；Ruff全src/tests/scripts PASS，
  `/tmp/qwen35-capacity-all-ruff.txt`；git diffcheck PASS。
- 未跑完整backend/前端/build：只有研究脚本/newdocs/合同测试，没有产品代码改动。
  主控最终全量门禁仍需进行，本作者不能以合同替代实际生成/独立语义审查/GUI。

## 实际 prepare-only（零推理/零provider接口）

只在本新tree准备real-deepthink-en。实际准备时Ollama基类_request与urlopen装失败
sentinel，若被调用立即停止；两访问计数均0。普通wire Projection独立override，无
tags/chat/show/model加载/HTTP/下载。保留 `/tmp/qwen35-capacity-actual-prepare.txt`。

路径 `.var/readiness-qwen35/readiness-qwen35-9b-thinking-capacity6144-single-v3/real-deepthink-en`。
新的prepared/database/verified-input/request-projection都write-once，新DB与18DATA独立
copy，source DB只mode=ro读，不抓公网/不改源。source3cede107…/ContentQoXRfTb7ves/
Evidence2与原相同；预备checkpoint **PENDING/0**。新case没有execution-permit、
generation.started、actual request、response或result；其他3case目录均未准备。

| Seal | SHA256 |
|---|---|
| prepared.json | ef02514aa842c7b595f81f6501e1178816606653dac3103517f15d4dcc000844 |
| state.sqlite3 | b089a7943ed8e2ced7bb5550cc824d518fce3c0b47febdb094da311aa725d77a |
| verified-input.json（与旧相同） | 1cda0703943eec515f08c7e3520011c110e4069805173f5afc5971e9cc355136 |
| request-projection.json | 6bdc1eb3d1b0f136e47cdf58da490ff8bb8478a92233f5c7fefa175247f747d2 |
| newfreeze | a5525188016fad45c0b8b1427501ae41c0a532e25317dd15422ec9cf17a9bbd5 |
| newprofile | 1c1a2e6ee43927fb5491f1c556ec66f3dc657c5a0d23bb1513a2bc037f083472 |
| harness | b49c0ffcc362e21e005109a7e2360cbd074881060d744d3f59e221eded1474db |
| oldactualrequest（不变） | 8244ff88c8dd9cf37a5ee15f4446a6e641f97b8d6fa41639373949177e9c7a7c |

新execution `distillation:reservation:v3:909d1c2ab68f0acfe3328a6b840f9a37bc9f807da3d599ff822159047c5b709e`；
原V2为2b2b1f85…，不复用。newactualprojection深度与原actualJSON相同，唯
options.num_predict4096→6144；schema/两role/messages所有文本与其它nativeoptions
不变。全部18DATA路径/byteshash相同，旧opaque response只hash核对不变，private
thinking未解析/读取/展示。完整receipt见QWEN35_CAPACITY_V3_INPUT_PREPARATION.json。

## 剩余门禁与STOP

这是作者prepare，**不是独立pre-output APPROVE，也不是模型兼容/容量/语义或生产
资格通过**。Reviewer须独立复算全部seal/原actualwire/规范与code，不自审；root接受
后fresh核验固定安装/runtime/磁盘与重模型互斥，再外部签唯一EN一次许可。912+6144
小于8192只算容量前提，actual未截断/最终语义仍需真实响应证明。300秒未知/失败不
加预算/重试/seed reroll，成功也不能继续3case或授LOCAL/生产。

原V1/8b/V2失败、Schema38 REJECT、UI979caeREJECT与正式版本均保留。没有main合并/
push/正式构建，未读owner/凭据/Vault，无production reader/付款/Cloud变化。提交
后作者STOP/clean，建议IN_REVIEW，不自行APPROVE/ACCEPT/DONE或推理。


## 2026-10-14 Independent pre-output review — APPROVE

Reviewer caption_resume，非本研究作者。审查 base
`bc110441627c0afd87b364c723c77a392a1c2145` → author
`21657d13d8cefc40dfab8ece0ec3152b42eadce8`，作者已 STOP/clean。
按已批准精确单例提案、任务卡及 code-review-and-quality 复核完整六文件差异；
Reviewer 仅追加此 handoff，未改代码、测试、freeze、profile、准备库或失败证据。

**APPROVE 仅表示本研究单例预输出工程/输入门禁通过。** 不授予模型执行许可、
实际 runtime/容量/语义合格、LOCAL 完整链路或生产资格。Root 仍须接受候选、重新
核验固定资源与互斥、签精确外部一次许可；300s、length/6144/empty/unknown/任何
原语义失败停止，成功亦停止，后3案例和正式资格不在授权内。

独立结果：

- `PYTHONPATH=src:. .venv/bin/python -m pytest -q
  tests/unit/test_readiness_qwen35_capacity.py tests/unit/test_readiness_qwen35_research.py
  tests/unit/test_ollama_local_distillation.py` → **105 PASS /13.85s**，
  `/tmp/qwen35-capacity-independent-tests-corrected.log`。32 新合同 + 原研究69 +
  普通 transport4，原所谓73即后两模块合计；未删/skip/弱化任何测试。
- py_compile PASS；Ruff 全 src/tests/scripts PASS；strict mypy src + 本脚本
  **103 files PASS**；base diffcheck PASS。日志
  `/tmp/qwen35-capacity-independent-{ruff,mypy}.log`。
- 独立只读复算实际准备库及冻结32文件，阻断 provider `_request`/HTTP sentinel
  期间零访问；`/tmp/qwen35-capacity-independent-seal.log`。prepared
  `ef02514aa842c7b595f81f6501e1178816606653dac3103517f15d4dcc000844`、DB
  `b089a7943ed8e2ced7bb5550cc824d518fce3c0b47febdb094da311aa725d77a`、
  verified `1cda0703943eec515f08c7e3520011c110e4069805173f5afc5971e9cc355136`
  与作者 receipt 实际相同；VerifiedInput 与原V2逐字节相同，18 DATA 完整路径/
  bytes hash 集合相同。新 execution909d…不同于旧2b2b…；SQLite mode=ro 查
  checkpoint **PENDING/0**、该执行 resource_usage0。
- 新 profile `production_qualified=false`。只有唯一 EN 目录；没有 permit、
  generation.started、实际 request、response、result 或后3目录。
- 实际 request-projection 与旧真实 request 深度相同，唯一 options.num_predict
  4096→6144；messages、原v5 role/prompt、schema、全部其它参数不变。
  profile/freeze/harness SHA 与 receipt 相同。旧 V1/V2 corpus/policy、普通 parser/
  service/core、旧合同和 V2 length/empty-final FAIL hashes 未变；未知状态不得重放。
- 完整差异未触及生产 src/Schema/配置/deps/资格 reader/云或正式数据。只读复用
  installed9b 原身份/静态 provenance；未调用任何真实 API、模型、下载或网络，
  未读取/解析/展示任何私有 thinking，未重新抓取来源。
- 独立检查 dispatch 前深比较旧实际 wire，exclusive durable marker 后才请求，
  重启/超时/未知不能二次调用；新 case 在文件/DB/permit I/O 前限制唯一 EN，
  老 V1/V2 CLI/execute 已退休；外部 exact prepared/code/profile/freeze/projection/
  runtime/exclusive single-case receipt 必须一致。保留原 ledger/parser/budget seam。

Reviewer 最初测试命令遗漏 `PYTHONPATH=src:.`，共享环境误导入旧
`/Users/hua/youtube-intel/src/youtube_intel/distillation.py`，3 collection errors
（缺 KnownLocalDistillationResponseError/OllamaLocalDistillationTransport）；原日志
`/tmp/qwen35-capacity-independent-tests.log` 保留。仅按仓库命令加正确 PYTHONPATH，
不安装/改环境配置/改测试，即得到上述105 PASS。只读 seal 探针第一次使用不存在的
`distillation_executions` 表名，查询失败后用 sqlite_master 确认实际 checkpoint
表名再完整复核；未修改任何库或 product，不能把该探针错误当产品行为。

未执行完整后端/前端/build/GUI：本切片无产品代码变更，最终集成完整回归与真实
用户链路仍由 root 门禁约束。912+6144<8192 仅容量前提，未被本审查转换为实际
加载、不截断或语义通过。没有发现本精确差异内需退回的 P0/P1/P2。Reviewer
提交本 review-only handoff 后 STOP；Schema61b6作者树仍 STOP，不自审。


## 2026-10-14 Independent actual single-case semantic review — REJECT (P1)

Reviewer caption_resume，独立于作者与实际许可/执行者 root。唯一实际 EN 已结束，
本次成功失败均 STOP；未执行任何后续案例。只查看 `message.content` 公开最终正文、
完成 metadata、原 VerifiedInput/冻结 EN expectation 及 mode=ro ledger；私有 thinking
未查看/解析/展示。未改原正文、响应、结果、profile、freeze、门槛或代码，未调用
provider/API/网络/模型。对应执行909d…只生成1次、invocation1，productionfalse。

实际证据 hash：

| 文件 | SHA256 |
|---|---|
| result.json | b865c9115fba68cea608e8c13911d88929f21943193c160153bc7eb6b8db5c5f |
| opaque response.json | bb980c4fa03eca06351e603482bac9e983dcce7bccd019d585dbbe48d7ebc73f |
| verified-input.json（原V2不变） | 1cda0703943eec515f08c7e3520011c110e4069805173f5afc5971e9cc355136 |

协议/持久化 **PASS**：实际精确9b、done=true/done_reason=stop、912 input/
4638 eval、total_duration218.922517041s，低于唯一6144/300s门槛；公开非空 JSON
经既有 research-only marker 表示适配及普通 parser 得到 SUCCEEDED。公开两条
Evidence ID/范围与输入相同。独立将第一条15 cues/0–46320ms、第二条3 cues/
46320–62600ms文本逐项拼接并重算excerpt SHA，与冻结18 cues完全一致。mode=ro
checkpoint SUCCEEDED/invocation1；resource_usage SUCCEEDED/ADMITTED、实际ollama/
qwen3.5:9b-q4_K_M、912/4638/invocation1，结果 generations1/productionfalse。
这些是协议/绑定/记录成功，不能代替下述语义审查。

语义按未改变的 INTELLIGENCE_REAL_CORPUS_V2 `real-deepthink-en.expectation`：

1. **P1 来源忠实性失败。** core声称模型利用
   “significantly deeper test-time exploration than typical human reasoning”。
   源0–46320ms仅有一位讲者对本次问题的自述：自己想到可能三种思路，并猜测模型
   似乎想到20或100种；没有一般人类推理基线、比较实验或可推广的深度结论。该
   core把单个经历/估计扩大为一般人类比较，且 using/utilizing 把猜测的探索机制
   写作此成就的解释。开头 “According to Google DeepMind” 与证明的 appears
   保留部分归因/不确定性，但不能补足这个新增一般比较命题的来源支持。
   “humans had previously only checked but not solved” 同时把特定原提问者过去未
   证明扩为 humans，进一步显示归因范围扩大；主要拒绝点仍是明确典型人类基线。
2. **P1 实质判断/保留要求失败。** require_substantive_judgment=true 与 retain
   “Still needs human mathematical verification and broader evaluation” 未满足。
   user_relevant_information仅写对理解数学研究可靠性/潜力“Relevant”，没有
   区分演示与独立正确性、后续人类数学验证或更广泛评估的保留判断。
   meaningful_details复述不确定措辞与 verification status uncertainty，但
   不构成需要 human mathematical verification / broader evaluation 的同义判断；
   broader evaluation 全部公开字段中不存在。不能把提到 reliability 或一句
   不确定词当原要求的完整满足。
3. 报告此前未证明猜想/多种方法这一主干 **部分通过**：来源确有先前未证明与
   方法探索，模型保留 conjecture/appears 等；上述泛化阻止整体来源忠实 PASS。
4. Google DeepMind归因与不独立确证 **部分通过**：core有来源归因、appears，
   detail有不确定性；但未清楚区分讲者经历与经过独立人类验证的结果。
5. 公共 mode 与 IMO gold-medal-standard mode **部分通过**：输出分别保留
   “basically very similar” modes 和 IMO milestone；没有准确交代是用户将获得
   的 mode 与所用 IMO mode 的相似关系。不自行为缺失联系补写解释或判完整PASS。
6. 原禁项检查 **通过这些局部项**：没有把 human-level intelligence 已实现作
   无归因事实；没有保证正确证明/声称全claims独立验证；没有新增延迟、价格或
   20/100为精确测量值。claim_kind FACT 在归因的报告中本身不是本次拒绝原因。
   这些局部通过不能抵消新增典型人类比较及缺少必要实质判断。
7. confidence **仅部分支持**：proof appears/不确定词存在，没有百分比或保证；
   不意味着其它泛化结论获得独立证据。NO_NEW未使用，不强迫改结果或重新生成。

最终 verdict **REJECT / SEMANTIC_FAIL / P1**。新增容量使该单例产生可解析公开
结果，证明这个固定输入的一次请求能在6144/300s内完成；不证明原四例或 LOCAL
可用、一般容量充分、语义质量或生产资格。result的 SUCCEEDED 是服务协议结果，
原 semantic_acceptance仍 PENDING_INDEPENDENT_REVIEW；本 handoff记录独立语义
拒绝而不篡改原实际文件。旧 V1/V2 FAIL 与全部冻结政策保持原样。遵守具体批准：
**本次单例已到终点，不调用后3样例、不reroll/校准/改prompt/延长timeout/授资格。**

Reviewer 仅提交此 handoff后 STOP；原 Schema61b6仍作者 STOP待独立核心重审，
普通 UI979cae返修等主控下一任务。没有 main/正式配置/owner数据/云付费操作。
