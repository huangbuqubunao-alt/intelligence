# TASK-READINESS-LONG-CARD-CANONICAL 独立审阅

- 结论：**APPROVE，仅限未接线的纯 canonical 切片**。无新增 P0/P1/P2/P3 finding。
- Reviewer：`long_card_canonical_review_oct19`，独立于作者；2026-10-19。
- 精确 base：`8f8c3d51fc89c06e322ec32c32d2ef5aa2da490e`。
- 精确候选：`11ffb558c7103ee934c33ef9c51452e841ad378d`。
- 审阅 WT：`/Users/developer/Documents/yia-worktrees/readiness-long-card-canonical-review`；branch `codex/review-readiness-long-card-canonical`。
- 唯一新增跟踪文件为本报告；未修改实现、测试、状态、配置、依赖、Schema、资格、注册表、owner/source、模型、tokenizer 或凭据。无网络、main、push 或发布操作。

## 范围、标准与证据来源

核对 root 精确 reviewer package、候选 task/package、AGENTS、COLLABORATION、PRD、SYSTEM_DESIGN、REUSE、long plan 和作者 handoff；当前状态采用 root 紧凑 `docs/PROJECT_STATUS.md`，不用本 WT 143KB 历史状态判断当前任务。采用 `code-review-and-quality` 的正确性、清晰度、架构、安全、性能五轴审查。Jev 在当前 root 状态中已确证 HTTP451 不可用，不重复调用，不降级或以其阻塞审查。

自己的 MCP graph 使用本 WT `fast`、`persistence=false`，先定位再读取实际函数；未写图文件或共享资产。检查 `base...candidate` 的全部三新增文件；没有已有产品或测试变动。纯模块仅导入标准库 `hashlib/json/dataclasses/typing`，无文件、DB、网络或模型调用、产品 import/cycle、隐藏修复或资格路径。graph `canonicalize_long_card` inbound（排除 tests）返回 `callers: []`，与 diff 的 unregistered/unwired 边界一致。

复用为 DIRECT 标准库 JSON/SHA/frozen dataclass，REFERENCE 原产品 oracle；无外部新实现或生产依赖。局部有限常量和投影复制是任务明确允许的隔离选择，后续正式接线须共享去重并维持 oracle 检查，本次不扩展范围。

## 历史语义与准入边界

独立读取真实源：

- `distillation.py:4188` `_text` / `:4196` `_texts`：非空且无首尾空白，4000/2000 字符与各列表20项；拒绝而不 trim。
- `distillation.py:4201–4368` `_parse_candidate`：positive 本地 marker 仅解包，七字段原文不变；真实 Evidence ID 按 Python 字符串排序，stance 原值，默认 `ensure_ascii=True`、`sort_keys=True`、compact separators 后 UTF-8。
- `intelligence_read.py:228–309` `_read_card`：trusted timed card 七字段按同一表示重建并核验 revision SHA-256。

私有探针没有复用新测试的 payload/oracle：240 个 seeded Unicode/ID/分类/stance/card 变体实际调用旧 `_parse_candidate`，逐 byte/SHA 相同；另调用实际 trusted `_read_card` 241 次（含完整最大形状），全部接受对应 canonical hash。全部只用内存合成 repository stub，未访问真实 source/owner 或授予 authority。

原始 IDs 中 NUL/DEL、引号、反斜杠、首尾空格、组合/预组合字符、BMP/astral 均按原字符保留；Python codepoint 排序而非转义文本或 UTF-16 排序。240 变体各验证 mapping/reference 重排与 ASCII/raw Unicode wire 编码两项不变性，以及文本改变必改变 hash。列表顺序、重复项和不同 Unicode 文本没有被归一或去重。

输入为精确不可变 bytes、1..1,000,000B、positive INTELLIGENCE 严格八字段；只接受固定 JSON 类型、有限 claim/stance、唯一原 ID、至少1 supporting 与合法整数区间。不支持 NO_NEW/LOCAL_TEXT，不替代 Evidence 归属、原 wire/decoded hash、source/policy/provenance、语言、模型资格或执行校验。结果冻结且内容为 bytes；content hash 与 decoded-wire hash 分别验证，不能互换，也不能把一致性称为来源可信。

## 固定形状上界与独立负控

每个合法 Unicode codepoint 最多12 ASCII bytes。容量为 `4000 + 4×20×2000 + 20×512 = 174240` codepoints；最大 syntax/enum/timestamp 开销2495B。因此精确结构上界为 `174240×12 + 2495 = 2,093,375B`。astral 填满全部字段、20个互异最大 ID、最长 claim、19个 contradicting +1个必需 supporting、两端19位最大合法整数时可达，并且与旧 parser 的完整 bytes 相等。私有 compact decoded wire 为 **699,479B**；作者 default-space fixture 的699,729B是不同合法 JSON 空白表示，canonical 一致。3,000,000B guard 是冗余安全上界，既不可达，也不排除任何合法形状；没有 monkeypatch 常量或伪造3MB成功样本。

原始 DEL 一字节可转义为六字节；私有 DEL 满文本样本和作者新增回归都证明 canonical 可超过输入三倍，**通用3x倍率论证不成立**。候选已移除该错误依据，保留的是上述结构证明。另实际对 NUL 和 astral 满文本样本与旧 oracle 比较。

私有独立探针共 **1,324 项检查 PASS**：

| 类别 | 实测 |
|---|---:|
| seeded 实际旧 parser parity | 240 |
| 实际 trusted reader parity | 241 |
| 字段/引用重排、编码不变性 | 480 |
| 身份内容改变 | 240 |
| 合法边界 / 非法形状与 max+1 | 13 / 70 |
| 真实全形状最大 / 1MB输入最大及+1 | 1 / 1及1 |
| malformed Unicode/JSON / 非bytes | 25 / 8 |
| DEL/NUL/astral oracle / 冻结 | 3 / 1 |

70项负控包含每个 prose 长度和列表计数的真实 max+1、20/21 refs、512/513 ID、时间负数/2**63/bool/float/string/null、缺字段、重复 ID、无 supporting、额外 provenance 和错误分支；接受端独立重放完整 max。25项 malformed 包含 escaped 等价 root/nested duplicate key、lone surrogate、raw control、非法/overlong/surrogate/out-of-range UTF-8、非有限/overflow 数值、垃圾/拼接JSON和5000层嵌套。可变/自定义 bytes、mapping/cycle/object 在入口拒绝。1,000,000B合法 JSON 加空白接受，1,000,001B拒绝。作者88新测试补充并覆盖其余有限分类、引用和文本边界。

## 实际复跑命令与结果

公共环境：review WT，`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1`，Python `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`；复用已有 venv，无安装。

| 命令（Python 后缀） | 结果 |
|---|---|
| `-m mypy --strict --cache-dir=/tmp/long-card-review-mypy src` | PASS：114 source files |
| `-m ruff check --no-cache src/youtube_intel/long_card_canonical.py tests/unit/test_long_card_canonical.py` | PASS |
| `-m pytest -p no:cacheprovider tests/unit/test_long_card_canonical.py tests/unit/test_long_grounding_codec.py tests/unit/test_long_grounding_projection.py tests/integration/test_task019_trusted_intelligence_read.py -q` | **282 PASS，6.11s**（88新 +110codec +68projection +16reader） |
| `.var/long-card-canonical-independent-review-20261019/probe.py` | **1,324 independent checks PASS**，seed20261019 |
| `git diff --check 8f8c3d51fc89c06e322ec32c32d2ef5aa2da490e...11ffb558c7103ee934c33ef9c51452e841ad378d` | PASS |

私有证据保留于本 WT 忽略目录 `.var/long-card-canonical-independent-review-20261019/`：`probe.py` SHA256 `c9e77b87d3251eceb9b679560baffb9bcb11ac87dc0b60abd5baf3a3de87a870`；`probe.json` SHA256 `22e48dc0bb29027029a607886085ec0099e03fbd7aaeffe3af641aa851b7d423`。

## 失败证据、跳过与剩余门禁

私有 harness 首跑 exit1：`probe.py:91 assert len(wire(v))==699729`。原因是 reviewer 自己使用 compact separators，却拿作者带空格 fixture 的输入长度断言；此前240 parser/reader以及精确 canonical 最大断言均通过。只修私有期望为699479，原失败保存在 `harness-failure.txt`，随后1,324检查全部通过；这是 harness 错误，不是产品失败，也未改作者测试。初次寻找旧回归日志时误用 root WT 路径，报 No such file；之后在作者 WT 找到原日志，只读，没有重跑失败命令。

更广旧失败保持为失败：作者 WT `.var/interrupted-canonical-qa-20261019/regression.log` 实际 **327 PASS/32 FAIL/30.48s**。完整命令为上述四组加 `tests/integration/test_task023_topic_timeline.py tests/integration/test_task025a_saved_intelligence.py tests/integration/test_local_distillation_wire_branches.py -q`（未用 `-p no:cacheprovider`）。22 Topic、3 Save、7 local-wire 在旧latest39初始化/升级断言失败，关键 `AssertionError: assert 40 == 39`，文件 `test_task023_topic_timeline.py:45/254`、`test_task025a_saved_intelligence.py:39`、共享 `test_task022_personalized_distillation.py:671`，尚未检验相关 card 行为。

独立读取 root 非helper基线代表证据 `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/tracked-root-integration-20261019/current-schema-three-red.log`，**3 FAIL/1.17s/exit1**，同样断言：

```text
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
 tests/integration/test_task023_topic_timeline.py::test_topic_contract_remains_available_with_m013_weekly_foundation
 tests/integration/test_task025a_saved_intelligence.py::test_fresh_m014_creates_empty_saved_state
 tests/integration/test_local_distillation_wire_branches.py::test_verified_local_positive_branch_decodes_without_changing_content
```

这是读取已留存实跑证据，不冒称 reviewer 在本轮复跑。root 产品基线89cca38不含新 helper。未重复相同已知失败命令，未编辑、跳过、弱化原断言，未宣称完整回归绿。原Schema40作者维护完成后，root仍须在最新接受核心上重跑这些相关组及最终完整回归。

本次不运行无关 frontend 全量、真实 GUI、网络、模型/tokenizer、长生产协议或真实备份验收；纯模块不拥有这些入口。长协议 proof/receipt、tracked clock/capture recovery、mixed subtitle、模型资源与语义资格、GUI用户全链路和最终全仓验收仍 OPEN。APPROVE 不代表已接线、可发布、任务DONE或普通用户长内容已可用。

## 最终交付

仅提交本新增审阅报告；提交前 scope/diff-check，无其他跟踪变动；提交后 clean STOP。报告提交 SHA 由最终回传提供。后续整合和当前任务状态属于 root，本 Reviewer 未操作 main/push/发布。
