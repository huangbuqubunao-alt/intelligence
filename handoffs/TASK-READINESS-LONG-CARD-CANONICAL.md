# TASK-READINESS-LONG-CARD-CANONICAL 交接报告

## 元数据

- Task: `TASK-READINESS-LONG-CARD-CANONICAL`；Role: Implementer。
- Agent/session: `long_card_canonical_oct19`。
- Base: `8f8c3d51fc89c06e322ec32c32d2ef5aa2da490e`。
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-long-card-canonical`。
- Branch: `codex/task-readiness-long-card-canonical`。
- Reported: 2026-10-19；实现和报告同一提交，准确 SHA 见最终回传及 `git log -1`。
- 建议 `IN_REVIEW`；提交后 clean STOP。Reviewer 及 root 最终验收待完成。

## 目标与范围

只新增纯模块 `src/youtube_intel/long_card_canonical.py`、对应新测试 `tests/unit/test_long_card_canonical.py` 和本报告。固定未来长 timed card 的历史 revision 表示，解决 codec 的 decoded hash 与现有 `content_hash` 不同的问题。未改任何已有产品、测试、任务状态、依赖、配置、Schema、注册表、资格、执行、reader 或持久化路径。

模块只有标准库 `hashlib/json/dataclasses/typing`，零文件、DB、网络、tokenizer、模型 IO。测试全部合成；旧 parser oracle 使用内存 stub，既有 reader 回归使用测试临时数据库，不访问真实数据、源快照、holdout、thinking、owner、凭据、Vault 或 Provider。无 main、push、部署或生产接线。

## 复用、精确 oracle 与接口

`DIRECT` Python 3.12 标准库 JSON/SHA-256/冻结 dataclass；`REFERENCE` 本仓库既有 trusted timed-card canonical 语义。没有新增依赖或第三方实现复制；标准库依原有 Python/PSF，项目代码依仓库 `NOTICE`。不从包含 IO 的产品模块导入 helper；生产去重和接线留后续共享任务。

精确基线 oracle：

- `distillation.PersonalizedDistillationService._parse_candidate`：4201–4368；局部合法 `INTELLIGENCE` marker 去除；4349–4359 使用全部七个 card 字段、按 **原始 Evidence ID 的 Python 字符串顺序** 重建 evidence，`json.dumps(sort_keys=True, separators=(",", ":"))`，默认 `ensure_ascii=True`，随后 `.encode("utf-8")`。
- `distillation.py:3890`：revision `content_hash = sha256(candidate.canonical_content).hexdigest()`。
- `intelligence_read.AuthoritativeIntelligenceReader._read_card`：276–290 对 trusted card 重新投影相同七字段、compact ASCII JSON 并核验 revision hash。
- 与 codec 的 `ensure_ascii=False`、保留 result、保留输出引用顺序的 decoded wire **不同**。测试实际调用旧 `_parse_candidate`，并非只复制其 JSON 表达式自证。

```python
canonicalize_long_card(decoded_wire: bytes) -> CanonicalLongCard
# frozen/slots: canonical_content: bytes
# deterministic read-only property: content_hash: str
```

输入只接受精确不可变 `bytes`，内容是 codec 解码后的 positive `INTELLIGENCE` timed-card JSON；不接受 Python mapping、list、自定义对象、bytes 子类或可变容器，因而 cycles/non-JSON 对象在 wire 边界直接拒绝。只接受 result/core_conclusion/claim_kind/evidence/四信息列表这八个精确字段；去掉 result 后得到历史七字段。`NO_NEW_INTELLIGENCE` 无 card revision，明确拒绝；LOCAL_TEXT 或任何新 provenance/version 字段拒绝。

不解析、重命名或猜测 Evidence ID。合法原 ID 的空白、标点、引号、反斜杠、控制字符、中文和 astral 字符逐字符保留。没有 trim/NFC、截断、采样、修复、stance 改写或 claims 文本替换；只按旧语义排序 evidence。信息列表顺序及重复项保留。

**完整性限度**：这个历史 hash 绑定七字段的所有内容；历史 oracle 本就不含 source/video/Summary/policy/执行 provenance。不得把这些字段擅自加入导致历史 hash 改变。调用者必须另行保留原 public/decoded wire 及其 hash、冻结的来源身份和完整 input proof/receipt，且在 hash 前完成真实 Evidence 归属/时间绑定、语义、语言、qualification 与执行校验。本 helper 不授 admission 或 authority，也不把哈希自洽称作来源可信。

## 精确边界与实达值

| 维度 | 接受域及证据 |
|---|---|
| decoded 输入 | 精确 bytes，1..1,000,000B；真实 1,000,000B（合法 JSON 加空白）通过，1,000,001B 拒绝，无 monkeypatch |
| core | 1..4,000 Unicode code points；非空、首尾空白保持既有严格形状；真实 astral max/max+1 测试 |
| 四信息列表 | 各 0..20 项；各项 1..2,000 code points；逐列表真实 count20/21 与文本2000/2001 测试，重复不去除 |
| positive evidence | 1..20；20通过/21拒绝；原 ID 唯一且 1..512 code points，512/513测试 |
| 时间 | 精确 int，拒绝 bool/float/string/null；0..2**63-1 且 end>start；0、19位最大合法正区间、2**63 反例 |
| 分类 | FACT/EVIDENCE_BACKED_STATEMENT/OPINION/PREDICTION/RUMOR/SYSTEM_INFERENCE；UNCLASSIFIED/未知拒绝 |
| stance | supporting/contradicting/conditional，至少一个 supporting；不改变每条原 stance |
| JSON | duplicate keys（root/引用）、未知/缺字段、无效 UTF-8、lone surrogate、非 JSON、NaN/Inf/overflow float、unsupported scalar/type confusion 全拒；接受形状最大 depth3，深恶意嵌套拒绝并转换 RecursionError |
| canonical bytes | 3,000,000B **冗余结构上界 guard**；固定 shape 的实达严格最大值2,093,375B，故不排除任何 shape 合法输入；不使用错误的逐wire3倍论证（DEL可由1B变6B） |

canonical 3MB guard 不可在固定 shape 下达到，未伪造 3MB 成功样例或缩小测试常量。测试填满 **core4000 + 4×20×2000 文本 + 20×512 原ID**，全部 astral（每字符12 ASCII bytes）；采用最长 claim、最大19位时间戳、19个最长 stance 与一个必需 supporting。实际最大 canonical **2,093,375B**（文本2,090,880B + 固定结构2,495B），decoded **699,729B**；实际旧 parser 全 bytes 相等。此样例已超过被否决的2MB guard；每个可变维度的 max+1 均有拒绝测试。输入 bytes cap1MB则单独真实验证 max/max+1。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 历史表示/hash | PASS | 实际旧 parser 输出逐 byte/SHA相等；ASCII astral escape、原ID排序及全部字段绑定 |
| 冻结与 wire 分离 | PASS | frozen dataclass/不可变 bytes；decoded hash 明确不同，原 bytes 原样保留 |
| 确定性 | PASS | mapping key 与 positive 引用重排不改 canonical；信息项重排、NFC不同文本及任一字段改变均改变 hash |
| 严格形状/资源 | PASS | 上述真实 max/max+1、重复/额外/缺失/类型/Unicode/非有限/循环等88新测试 |
| 旧 codec/projection/reader | PASS（所列专项） | 最终282项联合检查通过 |
| 更广 Topic/Save/wire 回归 | **FAIL，继承基线限制** | root已保留327PASS/32FAIL；不能称全回归绿，见下文 |
| 生产支持/资格 | 未授予 | 始终未注册、未接线；完整长协议/模型能力仍OPEN |

## 检查结果

公共前缀 `PYTHONPATH=src`，复用 Python：`/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`；无安装或依赖变化。

| 实际命令（Python 后缀） | 结果 |
|---|---|
| `-m mypy --strict src` | PASS，114 source files；最终 doc更正后重跑通过 |
| `-m ruff check src/youtube_intel/long_card_canonical.py tests/unit/test_long_card_canonical.py` | PASS |
| `-m pytest tests/unit/test_long_card_canonical.py -q` | 最初新87 PASS/0.34s；root中断QA87 PASS/0.24s |
| `-m pytest tests/unit/test_long_card_canonical.py tests/unit/test_long_grounding_codec.py tests/unit/test_long_grounding_projection.py tests/integration/test_task019_trusted_intelligence_read.py -q` | **最终282 PASS/5.69s**；此前281 PASS/6.97s；含最终精确2,093,375B断言、raw DEL旧parser反证与修正后的oracle文档 |
| `git diff --cached --check` / staged scope review | 提交前执行；只三新增允许文件；最终回传准确状态 |

root 已执行的完整失败命令（保留而不重复碰原断言）：

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python -m pytest -q tests/unit/test_long_card_canonical.py tests/unit/test_long_grounding_codec.py tests/unit/test_long_grounding_projection.py tests/integration/test_task019_trusted_intelligence_read.py tests/integration/test_task023_topic_timeline.py tests/integration/test_task025a_saved_intelligence.py tests/integration/test_local_distillation_wire_branches.py > .var/interrupted-canonical-qa-20261019/regression.log 2>&1
```

终态 **327 PASS/32 FAIL，30.48s，exit1**。日志原样保留于本WT忽略目录，不混入提交；root持有完整证据。32项均在旧fixture初始化或升级断言中期待Schema39，而实际Schema40，尚未进入相关 card 行为；涉及Topic22、Save3、local wire7。关键行：`AssertionError: assert 40 == 39`，受影响 `test_task023_topic_timeline.py:45/254`、`test_task025a_saved_intelligence.py`、wire共用 `test_task022_personalized_distillation.py:671`。root另在不含新helper的当前候选复现三代表同类FAIL；此模块未被旧产品import，不将此继承失败归因于新helper，也不冒称已有32项行为获得验收。旧测试维护已由root指定原共享core writer修复；本作者不越过三文件范围。最新core整合后的相同专项复验仍待root/独立Reviewer。

## 失败、跳过与风险

- TDD最初 `pytest tests/unit/test_long_card_canonical.py -q` 收集期 `ImportError: cannot import name 'long_card_canonical'`，因为尚未创建模块，exit2/0.09s；随后最小实现及严格mypy通过，新87项全绿，没有弱化断言。
- staged自审纠正了最初错误的“ASCII编码最多逐wire增长3倍”说明：真实原始DEL由1B变6B，新增旧parser逐byte反证测试。guard3MB未变化，其正确依据是完整shape最大2,093,375B；原实现行为未受此说明错误影响。
- Jev advisory两次schema校验错误（先缺 decision/evidence/priorities/candidates，随后 candidates需object而非string），路由不可用；停止该尝试并保留默认强推理执行，没有自动降级，也未使路由成为阻塞。
- root私有QA最初mkdir缺 `.var`父目录，修harness为parents=True后才运行检查，无产品变更；原证据在 `.var/interrupted-canonical-qa-20261019/wip.json`。
- 上述32继承FAIL未修改、跳过或隐藏；没有声称全量测试通过。独立review/最新base复验未由实现者替代。
- 不运行模型、tokenizer、网络、真实用户路径或备份接线测试：本任务只有纯函数、不授这些接口或资格；不是以此关闭完整长协议验收。
- canonical helper 故意局部复现历史表达式/有限字段常量，以免import IO模块；未来生产接线时须进行单一共享契约去重，且保持本oracle回归，不能让新路径绕开旧准入。
- `DECISION NEEDED`: None。功能限定、3MB结构上界guard与原oracle已向root回报并获确认。

## Diff 复核

仅三新增允许文件。无已有产品/测试字节改动，无生成资产、宽泛格式化、依赖/锁文件、Schema/配置/凭据、真实数据或生产行为变更。无 main/push/task-state 修改。提交前审完整 staged diff；最终 Git clean 状态及SHA由回传提供。

## 实现者结论

建议 `IN_REVIEW`，保持本helper **unwired**。实现、静态检查及最终282专项有外部运行证据；32项继承失败仍显式保留，需在root最新接受测试维护基线上复验。提交后clean STOP，等待独立Reviewer，未自行宣布任务DONE或长内容可用。

## Reviewer 结论

待独立Reviewer：准确base…HEAD、关键复跑、findings、APPROVE/REJECT及未解决P0/P1。

## 主控验收与整合

待root；实现者未合并、未改变任务状态，未发布或取得模型资格。
