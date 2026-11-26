# TASK-READINESS-SUMMARY-BASELINE-CONTEXT

## 元数据与范围

- Role: Implementer `/root/bigmodel_audit_review`（此前语义审查任务已结束，不是自审该输出）。
- Base: `0067feddc67e7d004514c515f7d985f45a54111e`。
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-summary-baseline-context`。
- Branch: `codex/task-readiness-summary-baseline-context`。
- 仅新增 `src/youtube_intel/summary_baseline.py`、`tests/unit/test_summary_baseline.py` 和本交接；建议主控窄审后决定是否接受，不自行合并。
- 目标：给后续显式 opt-in 新输入提供完整、可还原、可绑定身份的真实 Summary 比较基线；本提交不接线现有执行路径、不生成任何结果、不授模型资格。

## 复用与规格澄清

- `DIRECT`：标准库 `json` / `hashlib` / `re` / frozen dataclass；现成 `domain.AnalysisResult` 严格 JSON 校验及 `bound_evidence_reference.PROTOCOL` 常量。沿用已有依赖，无安装、锁文件或工具链修改。
- Root 已明确修正任务卡：真实旧 raw schema 是 `analysis-result-v1`，不是先前误写的 `content-summary-v1`。新比较协议独立命名为 `content-summary-baseline-v1`，不给旧 raw 添加 wrapper。
- 不使用只接受 DeepAnalysis `result_identity` 的 reader。pure API 允许本例合法的 `result_identity=None`、有 `analysis_artifact_id` 的旧抽取 Summary；不新增任何 repository/文件读取方法。
- Root 的只读原型 metadata 表示可压缩至 1,155B、拟 wire 20,753B，未批准发送。本实现仅参考 lossless typed-text 结构；未读取其真实 Summary/源正文、oracle、包或调用。原型费用/长度不能直接当作此提交的实际 wire/费用验收。

## 实现与调用约定

### `build_summary_baseline(...) -> SummaryBaseline`

显式关键字参数：`expected_video_id`、`current_pointer`、`artifact`、`raw_summary`（bytes）、`source_refs`、`summary_evidence`。

1. 指针五字段为 `video_id / analysis_artifact_id / result_identity / output_language / updated_at`；校验目标 video、artifact ID/key、`analysis_structured`、`DATA`、未删除/无失效期、原始文件 SHA、raw/provider/model 对应。
2. 严格使用完整 `AnalysisResult`，要求现有全部已知字段显式出现，拒绝重复 JSON key、未知/缺失语义字段、非有限数字、错误 kinds/IDs/引用；不靠 Pydantic 默认值掩盖不完整基线。
3. 保留全部 **10 个** semantic 字段：`one_sentence_summary`、8 个完整 point lists 和 `keywords`。每个 point 的 `text / kind / evidence_ids` 均原样保留。原 raw 的 Evidence 元数据/重复 excerpt 可不进入比较 view，但 whole-artifact raw hash 完整绑定；没有删除或改写原 raw。
4. `source_refs` 每项只允许 `ref` 加以下8字段：`video_id / evidence_id / excerpt / excerpt_hash / start_ms / end_ms / timed_transcript_id / timed_transcript_hash`。1–20 项、唯一 ID、严格原 E01…顺序、按原 start/end/ID 排序、同 video/同 timed capture+hash、合法整数时间及 excerpt hash。传入的是同一可信快照的投影，不是模型声明。
5. `summary_evidence` 每项为相同8字段（不含 ref）。旧 Summary IDs **无需等于** outgoing IDs，但须完整对应 raw Summary 的原 Evidence IDs/excerpt，且拥有同 video/timed capture/hash 的合法 bindings；不得扩大模型可引用的 E refs。原 raw 的 seconds=None 原样保留，使用 binding ms 证明同源，不伪补 raw 时间。现成 `EvidenceExcerpt` 秒字段是 `Literal[None]`；已知 schema 下非 None raw 仍由原 schema 拒绝，未擅自放宽成另一个协议。
6. 仅在已知字符串位置，把长度至少64字符的**精确匹配或精确子串**替换成 `{"source_text":[ref,start,end]}`；零起始 Unicode 字符索引、end exclusive。未匹配的字面文本不改、不模糊匹配、不正规化、不截断。inline 结构没有可重复的替换路径；JSON duplicate key/path 在进入 decoder 前拒绝。
7. `SummaryBaseline` 是 frozen slots，只有不可变 `projection_json / context_sha256`。完整 proof projection 绑定协议、video、artifact ID/raw hash、完整 semantic hash、指针 hash、原 source catalog binding hash、旧 Summary bindings hash；**必须由后续新请求身份纳入该完整 projection**，不是仅对小模型 view 做 hash。
8. 构造结束独立解码并逐值比较完整原 semantic projection，失败不返回 context。

### `restore_summary_baseline(context, source_refs=...)`

检查 context digest、精确协议/字段集、原 catalog digest、ref/range/Unicode 类型及完整 semantic hash；拒绝跨源、未知 ref、重复路径、越界、bool 伪整数、部分基线和内容漂移。返回新对象；改动返回字典不能修改 frozen context。

### `summary_baseline_prompt_messages(messages, context, source_refs=...)`

- 原 messages 每项重新拷贝、已有 content 字节不改。核对唯一原 `UNTRUSTED_SOURCE_EVIDENCE` 的 video/protocol/全部 refs+excerpt 与 proof catalog 相等；拒绝 double application。
- 追加一条通用 system 说明和独立 user `UNTRUSTED_CURRENT_SUMMARY_BASELINE`，**模型 view 仅含协议与全部 semantic Summary 的 lossless 表达**，不重复 Evidence binding 全文/一串 provenance hash。
- 明确基线是非权威比较 DATA、不是指令或新增 Evidence；已覆盖内容应 NO_NEW，除非有值得保留的独立支持/可修订判断。不强迫正向。任何字段中实质性的自身建议/解释应 SYSTEM_INFERENCE，并写基础/待验边界；输出字段/ref/stance/NO_NEW 格式均不改。
- 保守使用已有 Moonshot 的128,000B ceiling 对 raw、catalog、proof 与新 messages 做拒绝检查，不提高任何 transport 上限、不删字段来压预算。helper 不知道最终 transport envelope/实际 token 或价格；后续仍必须做原精确请求、授权、预算及质量校验。

## 运行证据

在本 worktree，复用 Root 已有 `.venv`，未安装依赖。Python 命令显式 `PYTHONPATH=/Users/developer/Documents/yia-worktrees/readiness-summary-baseline-context/src`、`PYTHONDONTWRITEBYTECODE=1`。

| 命令/检查 | 真实结果 |
|---|---|
| 首次 `python -m pytest tests/unit/test_summary_baseline.py -q`（尚无模块） | RED，exit2：`ImportError: cannot import name 'summary_baseline'`；这是新功能不存在的真实证据，不计通过 |
| 初版完整新文件 | 46 PASS /0.26s |
| 增加20/21边界、完整 excerpt、matching-hash错误原excerpt、不可变返回值、消息超限等控制后完整文件 | 50 PASS /0.26s |
| 最终只调整新测试函数内分组、未改产品后完整新文件 | **50 PASS /0.28s** |
| `mypy --strict --follow-imports=silent src/youtube_intel/summary_baseline.py` | PASS，1 source file |
| 最终 `mypy --strict src/youtube_intel/summary_baseline.py`（不使用 follow-imports=silent） | PASS，1 source file，3.17s |
| `ruff check src/youtube_intel/summary_baseline.py tests/unit/test_summary_baseline.py` | PASS |
| 两新 Python 文件 `compile(..., 'exec')` | PASS，无需生成字节码文件 |
| 逐个 `git show base:path` SHA 与当前既有 tracked src/tests/scripts/frontend/deps 字节比较 | **610 文件全部相等**；包括旧 dataclass、v1/v2/v3 builder/codec、state、001–043 SQL、原 tests、脚本及 frontend |

主要反证覆盖：缺失 raw/pointer/artifact；完整字面/精确全 excerpt/Unicode子串；全部 lists/kinds/旧IDs/keywords；raw hash/指针/video/provider/model/kind/root/删除错配；未知 schema/字段/缺失字段；旧 ID/源 hash/时间/capture/绑定缺失或重复；1–20原引用与21拒绝；错误/外来 ref/边界/重复 key、重签外层但未改 semantic hash的漂移；原始不可信指令只留 DATA；原 source messages不变/新拷贝；源消息错配/double application；新raw字节/指针修订/语义变化改变身份；超限拒绝而非截断。

## 限制、Diff 与交接

- 这些是 self-contained synthetic 离线检查；**没有真实模型质量通过、GUI、实际 source snapshot 接线、Backup/Restore、真实 wire/额度/账单验收**。任务明确不要求重跑完整 backend/frontend；未伪称这些通过。
- 纯输入校验不能从调用方任意 dict 自行产生可信 SQLite/Artifact authority。后续调用方必须获取同一 authoritative read-only snapshot、重新验 raw hash 与 current pointer、保留原 proof projection 并加入新输入/配置身份，再经原 consent/budget/once/资格 gates。本对象不授这些权限。
- 仅当前已知 `analysis-result-v1` / TIMED_MEDIA 源绑定 / bound Evidence refs；不扩 LOCAL_TEXT 或未知 Summary schema。未知/超限均 fail closed。
- 不读取 oracle 正文，不重审/修改此前 Kimi/GLM 输出，不读取真实凭据/Native/.env，不访问网络/模型/实际包/正式数据；零新增费用。旧实际失败和资格关闭均保持。
- 仅上述三个新增文件；无依赖、Schema、旧代码、测试削弱、格式噪声或无关改动。提交前检查 staged diff 与 `git diff --cached --check`。
- 当前实现可提交主控一次窄审；实际采用/新 QA profile/新请求预算/真实接线由 Root 后续决定。此提交本身不授权任何付费续试或下一真实样例。实现者提交后 clean STOP。

## Root 窄审后的最小 expiry 修复

- 保留原实现提交 `636cd909` 与上述证据。Root 发现 `artifact.get("expires_at") is None` 把缺失字段误判为明确不过期；这是已确认的 fail-closed 缺口。
- 先只给合法 synthetic artifact 明确加 `expires_at=None`，并在原参数化反证组追加 `missing-expiry`（不移除任何原断言）。完整新文件真实 RED：**50 PASS /1 FAIL /0.32s**；关键错误 `Failed: DID NOT RAISE ValueError`，新 case 删除 expiry 字段仍被旧代码接受。
- 产品仅改一行：要求 `expires_at` 显式存在且值为 `None`，与已有 `deleted_at` 的未知拒绝规则一致。没有改其他校验、codec、源消息、实际包或历史。
- 同一完整文件修后 **51 PASS /0.28s**；`mypy --strict src/youtube_intel/summary_baseline.py`（1 file）、两个新文件的 Ruff 和 compile 均 PASS。只对这项差异作收尾，不重跑旧大组；staged diff check PASS。
- 仅原三个任务文件的小追加提交，零真实 reader/SQL/Native/key/模型/网络/费用；提交后 clean STOP，交 Root 复核该行和反证。
