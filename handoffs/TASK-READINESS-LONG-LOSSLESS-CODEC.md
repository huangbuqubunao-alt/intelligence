# TASK-READINESS-LONG-LOSSLESS-CODEC 交接报告

## 元数据

- Role: Implementer；恢复中断 WIP 的独立 agent `long_lossless_codec_oct19`。
- Base：产品 `a073354` + root 任务元数据 `0ae374f`；本 worktree HEAD 起点 `0ae374f`。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-long-lossless-codec`。
- Branch：`codex/task-readiness-long-lossless-codec`。
- 实现 commit：`72dd0bd1b2d62a3a63aa5b99fbc9271969dac233`。
- 本报告与最小 synthetic hash 固定断言为后续交接 commit；最终 HEAD 见 root 回传及 `git log -1`。
- Reported：2026-10-19；状态建议 `IN_REVIEW`，作者 clean STOP，不合 main。

## 目标与范围

仅新增纯函数 codec、独立单元测试与本交接。延续原 WIP，未覆盖重建。提供完整有序 TIMED_MEDIA 的 RLE 编码、逐 cue / Evidence 精确展开和严格 alias 引用替换。不是 source-authority、模型执行、语义验收、模型资格或持久 proof。

实际新增：

- `src/youtube_intel/long_grounding_codec.py`
- `tests/unit/test_long_grounding_codec.py`
- 本报告

任何既有产品/测试文件、配置、依赖、Schema、执行准入、旧 profile/schema、资格和前端均零改。无正式用户数据或盲 holdout 读取，无模型 load/tokenize/generate、网络或 Provider 请求。真实 Sasha roundtrip 留待 root 按独立验证流程执行；本作者只做明确标注的合成数据测试。

## 复用与接口

DIRECT Python 标准库 `json/hashlib/dataclasses` 与现有 `state` 纯值类型及 `TimedTranscriptWrite.from_cues`。REFERENCE 当前 accepted `local_distillation_profile.py`、`distillation.py` timed schema / `_parse_candidate`，无第三方代码复制或新依赖。项目自有完整覆盖、alias、输出原 wire / 展开 wire 绑定；标准库和既有可信值足以实现，不需额外解析/压缩库。许可证沿仓库 NOTICE，无新外部许可证资产。

- `encode_grounding(source_id, content_provider, source_content_hash, canonical_text_hash, transcript: VerifiedTimedTranscript, evidence: tuple[EvidenceSpan, ...]) -> EncodedGrounding`，参数为 keyword-only。
- `EvidenceSpan(VerifiedEvidenceText, start_cue_index, end_cue_index)` 使用半开 cue 区间。第一段从 0 开始，相邻严格衔接，末段到全部 cue 数；拒绝空段、缺段、重叠、倒序、重复 Evidence ID。
- `EncodedGrounding.canonical_wire` 为冻结 bytes，`input_hash = SHA256(canonical_wire)`。
- `expand_grounding` 重建具名不可变值并重新 encode；只有唯一 canonical JSON/RLE 字节完全相等才返回。
- `decode_output(public_wire: bytes, encoded) -> DecodedOutput` 保留 `input_hash`、原始 `public_wire` 与其 SHA-256，以及独立 `decoded_wire` / SHA-256。`decoded_value` 每次解析为新对象，调用者后续修改不影响冻结值。

## 独立 codec 身份与原输入绑定

版本固定为 `long-grounding-lossless-timed-v1`。版本在 canonical root，参与完整 `input_hash`；不复用 `local-grounding-complete-evidence-v1`、现有 profile/schema 身份，不注册到运行时。后续任何行为/shape/限制变化需要新版本和独立验收，不能把本 packet 当旧短协议输入。

canonical 固定为严格 UTF-8、`ensure_ascii=False`、`sort_keys=True`、`separators=(",", ":")`、`allow_nan=False`。root 精确字段为 codec 版本、source/provider/source hash/canonical hash、video/canonical artifact/timed transcript ID 与 hash、完整有序 Evidence。每个 Evidence 绑定原 ID、TIMED_MEDIA、起止毫秒、起止 cue index、原 excerpt hash、可选 source hash 和 runs。每个 run 仅复用同一 Evidence 内相邻逐字符完全相同的文本，每个原 cue 仍单独保留 `[index,start_ms,end_ms,text_hash]`。不 trim、不 NFC、不跨 Evidence 合并、不截输入。

每个 cue hash、完整有序 timed hash/ID、原 Evidence excerpt/hash 和时间定位都重新核对；excerpt 必须等于该区间 cue 文本以 `\n` 精确连接。现既有可信 cue 质量边界仍拒绝纯空白 cue；含首尾空白、换行、tab、NUL、组合 Unicode 和 emoji 的非空白文本逐字保留。source/canonical hash 是调用者已验证的源身份，本纯 codec 不猜原文件序列化、不声称据此验证源权威。

确定性合成示例（不是实际 Sasha 文本或模型数据）：

| 示例 | canonical bytes | input SHA-256 |
|---|---:|---|
| 默认 4 cue / 2 Evidence | 1464 | `d304dd267e1916e1d76b02f1250b5a367ae6c7a8ae007684cd1b5133c84b417b` |
| 合成 2406 cue / 114 Evidence | 272268 | `9ee910aef1d757ad981622883db57a2a650e1efe6c0f690168b075dd921d4139` |

第二例由测试里的 `synthetic {i // 4} é e\u0301 😀\t\x00` 和 `(2406*i)//114` 分段生成。两个示例都全量逐 cue / 逐 Evidence roundtrip；后者 NO_NEW 全量 114 引用严格通过。该 bytes 数不是模型输入 token 数、压缩率、slot 或资源实证。

## public final 输出 shape 与主控决定

只接受以下两个精确 root shape，无额外字段，无 `wire_version`，不读取 thinking：

1. `INTELLIGENCE`：`result,core_conclusion,user_relevant_information,important_new_information,meaningful_details,filtered_noise,claim_kind,evidence`。结论为 1..4000 字符非空白且无首尾空白原字符串；四个文本列表各 0..20 个 1..2000 字符同等文本。claim kind 仅 FACT / EVIDENCE_BACKED_STATEMENT / OPINION / PREDICTION / RUMOR / SYSTEM_INFERENCE。Evidence 为 1..20 个精确 `{evidence_id,start_ms,end_ms,stance}`，唯一 alias，时间精确相等，stance 仅 supporting / contradicting / conditional，至少一个 supporting。保留原引用顺序，可选实际相关子集。
2. `NO_NEW_INTELLIGENCE`：仅 `{result,evidence}`，Evidence 每项恰为 `{evidence_id,start_ms,end_ms}`。先验完整长度、唯一性、全集、canonical 顺序 E1..En 与原时间，全通过后返回展开结果；不补缺失引用、不修输出。

2026-10-19 root 明确决定：普通 positive 保持 accepted schema maxItems20，不能把旧 parser 漏验最大数当作允许；新 codec NO_NEW 才使用完整输入 cardinality，包括 114。输入始终完整全量。未来长 schema/执行身份仍须单独定义，不扩大旧 short NO_NEW 合同。positive 21 引用已先实际复现失败再最小修复；20 成功、21 拒绝。

两 branch 只替换精确 `E1..En` 为冻结原 Evidence ID，其他解析字段/文字/语言/stance/uncertainty 逐字段原样。严格拒绝未知 alias、E01、重复、直接 runtime ID、时间改变、缺/多字段和类型混淆；不做事实、归因或输出语言判断，不声称通过既有语义准入。

## 有界资源与失败行为

| 范围 | 上限/规则 |
|---|---|
| provider | YOUTUBE / LOCAL timed；其他拒绝，不扩既有模型 scope |
| 总 cue / Evidence | 32768 / 4102（既有 local-media read 边界的保守限制） |
| 单 cue 文本、单 Evidence excerpt | 4000 Unicode code points |
| 单 Evidence cue / run / run markers | 最多 4000；仍受 excerpt 与总量限制 |
| 总 cue 文本保守累计 | `sum(len(text)+1)` ≤1000000 code points、`sum(len(utf8(text))+1)` ≤4000000 bytes |
| canonical packet | 5000000 bytes，超限明确拒绝 |
| 原 public wire / 展开 output wire | 分别最多 1000000 bytes；展开变大仍单独校验 |
| identity 字符串 | 非空、严格 UTF-8、最多512字符；SHA-256为64位小写十六进制 |
| cue index / millisecond / span index | exact int，0..2^63−1；拒绝 bool / float / 负数 / 溢出 |
| JSON nesting | 深度最多16；重复 key、NaN、±Infinity、指数溢出、错 UTF-8、lone surrogate、fence/尾随数据均拒绝 |

输入值构造及展开是有界内存工作，不包含 I/O、tokenizer、加载或推理；这些边界不是模型 context 预算。超限只抛 ValueError，不做截断或降质。构造完整且自洽的另一 packet 会得到不同 input hash，不能用 hash 一致性推导来源或调用权威；后续调用者必须验证并绑定预期 input hash。

## 验收与检查结果

使用现有 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/` 中 Python / pytest / Ruff / mypy，并设置 `PYTHONPATH=src`，没有安装或更改依赖。

| 命令/检查 | 结果 |
|---|---|
| `python -m compileall -q src/youtube_intel/long_grounding_codec.py` | PASS |
| `mypy --strict src` | PASS：106 source files |
| `python -m pytest -q tests/unit/test_long_grounding_codec.py` | PASS：110，最后补固定 hash 断言后0.32s |
| `python -m pytest -q tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_harness.py tests/unit/test_local_grounding_qualification.py tests/integration/test_local_grounding_proof.py` | PASS：113，56.63s |
| `ruff check src/youtube_intel/long_grounding_codec.py tests/unit/test_long_grounding_codec.py` | PASS |
| `git diff --cached --check` / 完整新增 diff 人工复核 | PASS；仅两新文件，之后本独立报告 |

新测试覆盖精确全量 roundtrip、分组/身份哈希差异、跨边界重复、Unicode/控制字符、非法顺序/index/time/hash/locators、冻结后原对象修改、原 wire/hash 独立保存、NO_NEW 全集完整顺序、positive 20/21、支持立场、字段/类型严格性、包篡改/非 canonical RLE、所有主要资源拒绝和展开 output 独立 byte bound。

## 失败、跳过与风险

- 已解决：恢复 WIP 新测试的 Ruff E701（一行多个语句，36处），只 format 本任务两新文件；原60测试 PASS。
- 已解决：`pytest ... -k positive_reference_boundary`：1 failed / 1 passed，`test_positive_reference_boundary_stays_at_accepted_twenty[21]` 报 `DID NOT RAISE ValueError`；按 root 决定增加 positive20限制后 PASS。未弱化任何测试或现有断言。
- Graph 工具未索引本新 worktree，既有 graph 对 local_grounding 无结果，后续用只读精确文本检索；未索引/改工具配置。
- Jev bounded routing HTTP451，不可用；按规则保持原默认模型和独立审查要求，不绕过为自动接受。
- 未跑全仓 suite/build：新模块没有产品接线，任务指定 focused/static 与相关113回归已通过；全仓/最终产品验收由后续串行集成完成。
- 实际 Sasha、完整 rendered tokenizer/slot/host resources、模型语义资格、长 input proof/receipt、反向 reader、Backup Restore 均未执行/未完成，继续 closed；tracked40+混合字幕共享核心接受后由 root 安排串行接线。
- 本切片不授任何模型资格，不能作为“长内容已可用”的证据。
- `DECISION NEEDED`: None；纯切片完成并等待独立 review。

## Diff 复核与实现者结论

已复核相对 `0ae374f` 的全部新增实现与测试，未改旧 golden、产品、依赖、Schema、配置、密钥、真实 Vault、云调用或调度。建议 `IN_REVIEW`。作者提交后 clean STOP；不继续产品开发，不合 main。

## Reviewer 结论

- Reviewer / 审查 HEAD / 复跑检查 / findings / verdict：待主控指定独立 Reviewer。
- 作者不得填写独立 APPROVE；本报告不代表主控 ACCEPT。

## 主控验收与整合

- Orchestrator verdict / 批准整合 commit / 主线 commit / 整合后检查：待 root。
- 未设任务 DONE，未整合 main，未发布。

## 独立 Reviewer 复核（2026-10-19）

- Reviewer：`subtitle_recovery_preflight_oct19`，非实现者；指定独立 WT `/Users/hua/Documents/yia-worktrees/readiness-long-codec-review`、branch `codex/review-readiness-long-lossless-codec`。
- 精确审查：`0ae374f..f0cf9537ea40e4e3139d0cda300ac7e6f9c17e3c`；起始工作区 clean、作者已 STOP。读 root 最新任务追加决定及 `REVIEW-READINESS-LONG-LOSSLESS-CODEC.md`，按 code-review-and-quality 五轴检查，先读测试再逐行核查539行产品实现。
- **Verdict: APPROVE（仅纯 codec 工程切片）。P0/P1/P2/P3 actionable findings：无。** 本结论不授 source authority、生产执行准入或任何模型资格，不宣称长内容功能可用。
- Scope：精确 diff 仅 codec、其新单测、本 handoff 三个新增文件。旧产品、short/Cloud/profile/schema、state/Backup、资格、前端、依赖/lock/config 均零修改；review 自己只追加本节。图检索未覆盖新模块，改读指定 fixed candidate 源码；未改索引。

### 独立运行的检查

所有 Python 命令使用 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` 与 root 既有 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`；工具目录相同。实际打印确认 codec 模块路径是本 review WT 的 `src/youtube_intel/long_grounding_codec.py`，未借其他 editable 项目。未安装依赖。

| 独立命令（在 review WT） | 结果 |
|---|---|
| `python -m compileall -q src/youtube_intel/long_grounding_codec.py` | PASS |
| `python -m pytest -q tests/unit/test_long_grounding_codec.py` | **110 passed**, 0.40s |
| `python -m pytest -q tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_harness.py tests/unit/test_local_grounding_qualification.py tests/integration/test_local_grounding_proof.py` | **113 passed**, 54.38s |
| `mypy --strict src` | PASS，106 source files |
| `ruff check src/youtube_intel/long_grounding_codec.py tests/unit/test_long_grounding_codec.py` | PASS |
| `git diff --check 0ae374f..f0cf953`；精确文件范围及旧核心 zero-diff 检查 | PASS |
| `python .var/codec-independent-review-20261019/adversarial.py` | PASS，全部独立合成边界及对抗检查 |

独立 private QA 脚本与输出绝对路径分别为 `/Users/hua/Documents/yia-worktrees/readiness-long-codec-review/.var/codec-independent-review-20261019/adversarial.py`、同目录 `adversarial.log`。明确只用合成源，无真实 Sasha、blind holdout、thinking 或模型输出；没有 QA 断言失败，也没有修改产品或既有测试以获通过。

### 独立证据与安全边界

1. 实际边界值而非只缩小常量：32768 cue 成功 / 32769 拒绝；4102 Evidence 成功 / 4103 拒绝；累计1000000字符成功 / 1000001拒绝；单 cue 与单 Evidence excerpt 各4000成功 / 4001拒绝；canonical packet 恰5000000 bytes 编码及展开成功 / 5000001拒绝；原 public wire 恰1000000 bytes成功 / 1000001拒绝；独立展开后的 output 恰1000000 bytes成功 / 1000001拒绝；毫秒2^63−1成功 / 2^63拒绝；source ID 512成功 / 513拒绝；严格 JSON helper 深度16成功 / 17拒绝。4MB原文本byte限制另经逐行检查，且实际1M累计字符限制本身使其保守冗余（每字符UTF-8最多4 bytes、每cue separator仅1 byte），未把这当作可提升模型预算的依据。
2. 120个固定种子 Unicode、组合字符、NUL、首尾空白/换行、RLE重复与随机 Evidence 分组全量精确往返；原 cue index/time/text/hash 与完整 Evidence excerpt/identity 均相等。只在同 Evidence 内相邻相同文本合并；canonical 重编码对非规范 RLE、错顺序/缺cue/错hash/多字段严格拒绝。
3. 114条完整输入的 NO_NEW 全序展开成功；遗漏、逆序或重复引用拒绝。相同114输入的 positive20成功 / positive21拒绝，至少 supporting 约束继续保留。严格拒绝 E0/E01/E+1/大小写/全角数字/尾空白/NUL/直接runtime ID，以及 bool/float/NaN/±Inf/指数溢出、错UTF8/BOM/尾随JSON。缺任一positive字段均拒绝。
4. public bytes及其hash独立保留，decoded bytes/hash独立绑定输入；只替换引用ID，claims、stance、顺序、组合Unicode与不确定性原文逐字段相等，未补齐或修复输出。冻结后原对象或返回JSON的修改不影响已存 bytes/hash。hash和canonical编码绑定身份，不能证明来源；完整自洽更换source metadata会产生不同hash，未来调用者必须验证预期输入hash与既有authority，不能仅凭 codec 值授信。
5. Root另报真实 Sasha 2406cue/114Evidence roundtrip，是 root 的独立实证，未冒称为本 reviewer 自己读取或执行。本次无 network、tokenize、模型 load/generate、正式数据、SQLite维护或新持久化。Jev因本任务明确0网络/模型约束未调用，未据此降级审查。

### 未执行项与结论限度

全仓 suite/frontend build、真实 rendered tokenizer/slot/host资源、模型语义/资格、长 schema/profile/inputproof/receipt、反向 reader 和 Backup Restore 仍需后续串行任务验收。本模块未接入旧产品，现有短/Cloud合同零diff；本轮已运行规定 affected 回归及静态检查，不用本切片替代最终验收。无当前阻塞或需退回作者的缺陷。Reviewer 仅提交本 handoff 后 clean STOP，不合 main，不更新任务状态。
