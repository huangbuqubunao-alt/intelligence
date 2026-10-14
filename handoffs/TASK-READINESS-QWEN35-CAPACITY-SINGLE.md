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
