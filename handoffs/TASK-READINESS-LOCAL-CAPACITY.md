# TASK-READINESS-LOCAL-CAPACITY 交接报告

## 元数据

- Task: `TASK-READINESS-LOCAL-CAPACITY`
- Role: Implementer
- Agent: `native_scan_resume`
- Base: `e4c693f80ffff388bc494e1c27c6b9269255742e`
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-local-capacity`
- Branch: `codex/task-readiness-local-capacity`
- Reported: 2026-10-16
- Head: 本报告随实现 commit；提交后以 Git HEAD 和实现者最终消息的完整 SHA 为准。

## 目标与范围

为未冻结、未取得资格的 9b native-thinking profile 接入完整输入容量界和当前机器预检；生产和 once harness 使用同一 builder、prepare/arm/claim/dispatch。作者仅离线与受控 fake HTTP，真实 metadata/load/debug/generation 均为 0；没有签发真实 permit、写入 qualification 或读取 thinking。

实际修改：profile、distillation、qualification CODE_FILES、新 local_model_capacity、runtime_composition、once harness、两个可选 guard provider、ASR `_slot`、相关测试和本交接。额外 scope 依据 root task 的 `b2257e9`（完整 provider I/O guard）、`7fadbd5`（ASR unknown 判定）、`32eb456`（不可抹 claim 与 preclaim arm/intent）。这些 root task 仅只读，不 cherry-pick。

未修改 App/local_api/state/source_policy/Schema/依赖/配置/credentials/正式数据/旧 freeze 或失败 receipt。普通 8b factory/provider 类型、请求与费用合同保留；旧 Cloud classes、TextProfile 和 providers/ollama.py AST 保留。UI capability 接线不属本任务，仍待 root 串行任务与统一 freeze。

## 实现及验收合同

- 新 profile 的 complete body 上限 12,288 UTF-8 bytes，system+user content 上限 8,192；两消息/固定角色、prompt、schema、model/options、顶层 `truncate=false/shift=false` 严格白名单。固定 ctx16,384/output6,144，实际输入界为 content bytes+88+2；最坏 8,282+6,144+1=14,427≤16,384。容量算法、两上限与固定词表 hash 纳入 projection/identity。没有切片 Evidence/来源，也没有增加 tokenizer 依赖。
- 原四份完整输入 body 为 4,822 / 4,825 / 7,869 / 4,149 bytes；Evidence 数为 2/2/15/2。新 bound 的安全前提为 root 已复核的官方固定 renderer、完整 byte vocabulary 和 merge 结果；不能推广为任意模型/tokenizer 的一般假设。
- 当前主机检查固定 manifest/all six blobs/三个 runtime binaries 的真实 hash；show 无 SYSTEM/MESSAGE override、固定 qwen35/gpt2/preqwen35；固定唯一 server、实际 runner 参数、单 parallel slot/ctx16,384、内存/磁盘。未知、缺失或变化均关闭。冷准备仅 `/api/chat` messages:[] load-only，严格 done/load、空正文、无 eval；之后检查真实 ps/runner。轮询 available 不加载。
- 同一应用 ASR worker.lock + Backup background gate 持至完整 I/O read/close/exception。评分/判官实际 factory 保留 exact type，通过既有 transport 包装；Summary/translation 新 optional guard 默认 None 保留旧行为。没有取得普通非重入 worker._execution；同线程嵌套和跨线程/进程反证覆盖。该锁仅约束参与本应用的入口，不锁住外部 Ollama 客户端。
- readiness 绑定 execution、canonical request hash、实际保序 wire hash、主机身份、owner thread 和 preclaim 30 秒期限。durable once intent 用 O_EXCL+fsync 在 claim 前写入，明确 `ARMED`/`generation_post_proven=false`。意图 I/O 后最后检查并 arm，随即进入既有 SQLite claim；claim 失败 discard/release 0 POST。已成功 claim 的 token 不再墙钟过期；generate 仅纯 hash/一次消费和唯一 POST，之后没有 metadata/fingerprint/TTL I/O。
- intent 写入失败 0 invocation；写入后 claim 失败或崩溃保留 spent intent，不能自动重试/授资格。claim 后本地令牌丢失或崩溃保留 invocation1 的保守 unknown，独立记录本机 `generation_post_attempted_locally`，不伪称已生成；timeout 不重发。取消赢 claim 竞态为 CANCELLED/0 POST。
- shared unknown predicate：active PENDING+inv1 立即关闭且 0 metadata；历史 terminal AMBIGUOUS 必须 checkpoint/resource truth 完整一致，且当前固定 server 唯一、启动严格晚于全部相关 unknown.updated_at、ps[]、无 fixed runner，才允许独立新任务。恢复/跨机器无本机证据时关闭；所有观察均在应用锁内，没有 persistent bypass bool。原 execution 永不重发/改历史。ASR `_slot` 使用同一只读判定，异常总释放 fd。Backup 本身的既有 quiescence 规则未改。
- qualification CODE_FILES 纳入实际新模块、两 provider、ASR 和 Backup，空 records 保持关闭；fixture PASS 不产生资格。39 历史 proof wire/hash、旧 None/Cloud 请求与失败资料保留。

- 独立 harness 必须用 `<audit_name>.workspace/state.sqlite3` 和同根 `data`，private 当前 UID owner、非 symlink/非 hardlinked DB；prepare 在 reservation 前拒绝外部 DB。描述、prepare/execute/最终意图 arm 都绑定并复验同 workspace dev/inode，bounded lsof 缺失/异常/他进程 holder 或 restore marker 都关闭。root 冻结前还须核验该专用 root 无 GUI/API/其它 Backup 服务；这不是跨进程 Backup 全局锁。隔离数据由普通 import/proof producers 构造，原 input/semantic/request hashes 和 Summary/Evidence 证明不改，也不复制正式 owner 数据。

## 检查结果

| 检查 | 结果 | 证据 |
|---|---|---|
| compileall src/scripts/新增测试 | PASS | 语法先行，无依赖安装 |
| `PYTHONPATH=src:. .venv/bin/mypy src scripts/qualify_local_grounding_v1.py` | PASS | 106 source files，`.var/capacity/final-complete-mypy.log` |
| `.venv/bin/ruff check src tests scripts` | PASS | `.var/capacity/final-complete-ruff.log` |
| 完整受影响后端 33 files（distillation/旧 Cloud 费用与授权、8b adapters、39、runtime、ASR、Backup、harness） | PASS | 1,015 passed / 473.44s；`.var/capacity/affected-tests.log`。原 zip duplicate-path 恶意归档负控发 1 warning，非跳过/失败 |
| 最终容量/profile/reader/harness/实际 composition/历史 proof | PASS | 178 passed / 83.37s，`.var/capacity/final-capacity-tests.log`；涵盖最终 ownership/cold-runner/arm 顺序变更 |
| preclaim arm 顺序单独复验 | PASS | 11 passed / 18 deselected（仅 `-k ordinary_reserved` 选择当前相关 case，不是删除/skip）；`.var/capacity/final-arm-order-tests.log` |
| Diff/AST/范围 | PASS | `git diff --check`；`.var/capacity/ast-compatibility.json`；资格 records[] 原字节无改 |

最终实际 ASR 跨进程复验：75 PASS / 28.78s，`.var/capacity/asr-final-tests.log`；实际生产 factory 的 score/judge/summary/translation 完整 read/close/exception 持锁期间，子进程构造真正 LocalTranscriptionJobs 并调用 `_slot()` 全部拒绝；9b readiness 持锁也拒绝真正 `_slot()`。最后 Ruff PASS（`.var/capacity/asr-final-ruff.log`），`git diff --check` PASS。旧 None-profile generate 在新 profile 分支后的完整 AST suffix 与 exact base 相同。

可复验：先设置 `PYTHONPATH=src:.`，使用共享现有 `.venv`（不安装）。完整 affected 文件为 unit 的 local_model_capacity/local_grounding_profile/local_grounding_qualification/local_grounding_harness/distillation_dispatch/ollama_local_distillation/ollama_analysis_adapter/evidence_translation/ollama_deep_analysis_adapter/scoring/scoring_language/openai_distillation_adapter/moonshot_distillation_adapter/readiness_qwen35_research/readiness_qwen35_capacity/backup_restore/offline_transcription/transcription_policy；integration 的 local_capacity_composition/local_grounding_proof/local_intelligence_timed/local_intelligence_text/local_distillation_wire_branches/runtime_composition/distillation_source_context/task022_personalized_distillation/task023b_distillation_reservation/task019_trusted_intelligence_read/ollama_provider/offline_transcription_jobs/local_transcription_service/v1x_phase1b_backup_restore/research_backup_restore（均 `test_*.py`）。最终178项复验是 unit local_model_capacity/local_grounding_harness/local_grounding_qualification/local_grounding_profile 与 integration local_capacity_composition/local_grounding_proof；最后75项仅 local_model_capacity+local_capacity_composition。

## 失败证据与处理

- 原旧合同测试 `.var/capacity/service-tests.log`：`...ordinary_reserved... [expire-after-claim]` FAIL，关键原断言为 claim 后 TTL 过期试图 WAITING_MODEL/invocation0，触发 `sqlite3.IntegrityError: local invocation claim cannot be erased`，随后 `IntegrityConflict: distillation terminal state violates the ledger contract`。原 37 trigger/Schema/状态断言保留；root `32eb456` 正式修正不可能的合同为 preclaim arm deadline，测试补 preclaim expiry0、claim 后一次、intent I/O0、取消 race0、postclaim lost/timeout 不重发。失败日志保留，不将历史失败改为 PASS。
- ownership 新正向 fixture 首次使用自动 reservation reason 而 LOCAL 仅允许手动 Content，`.var/capacity/ownership-tests.log` 为 101 PASS/1 FAIL `local Intelligence requires an explicit manual Content command`。改正 fixture 为与 prepare 完全相同的 `MANUAL_CONTENT:grounding-local-timed-en`，不改产品拒绝合同；最终 178 PASS。
- 一次测试启动未设置本 WT `PYTHONPATH`，共享 venv editable 导向主 checkout，收集 ImportError；日志 `.var/capacity/arm-tests.log`。修正为 `PYTHONPATH=src:.`，未安装/修改依赖。
- `PYTHONPATH=src` 的测量测试缺仓库根 scripts import：101 PASS/1 ImportError，`.var/capacity/arm-tests-local-src.log`。`src:.` 复验含新增 host 负控 120 PASS，`.var/capacity/arm-host-tests.log`。
- 初始 TDD/静态/旧参数预期失败保留 `.var/capacity/`：pure-red/readiness-red/transport-tests。原 ctx8,192 与 blocked capacity 仅按本未冻结新 profile 合同更新，prompt_count 原拒绝转精确 actual bound/+1 负控；没有删测试、skip、弱化旧黄金或门禁。

## 复用与来源

DIRECT：已批准标准库 hashlib/json/fcntl/contextlib/subprocess/urllib 和系统只读 lsof（有界；作者仅 fake）；既有 SQLite claim/ledger、SourcePolicy 验证、ASR worker slot、Backup background gate、production builder/qualification reader/harness。ADAPT：仅现有 factory transport 的完整生命周期 lease。REFERENCE：仓库 LOCAL_CAPACITY_PREFLIGHT_PLAN、LOCAL_CAPACITY_RENDER_SLOT_DIAGNOSTIC / VOCABULARY_READONLY / FOUR_INPUT_MEASUREMENTS receipts 中固定官方 Ollama v0.40.1 与 llama.cpp b11351 来源/许可证；没有执行/嵌入外部源码。REJECT/DEFER：新 tokenizer/模型/依赖、自动卸载/重启、把旧收据 bool 当主机 authority、provider result 或 fixture PASS 直接授资格。

## Diff 复核与风险

- 仅授权 scope；新文件执行代码纳 CODE_FILES，无生成/配置/依赖/Schema/正式数据差异。
- 既有旧 Cloud/TextProfile/providers/ollama.py AST 对照证据 `.var/capacity/ast-compatibility.json`。两个 provider 的 optional guard AST 变更如实包含，不宣称零差异。
- 固定版本/path/manifest 单 slot 方案有意 fail closed；安装升级或 runner 参数变化需要重新审查。完整 hash 读取会产生本地准备耗时；不把这些工程 fixture 视为真实 load/语义验收。
- 外部 Ollama 客户端不参与锁，不能宣称物理 exactly-once 或全局独占。API metadata 与进程的检查不是对恶意同机进程的密码学绑定；遵循固定受信本地服务前提。
- frontend 无 diff，未运行 frontend/TS/build；可参考 root 已接受的 496 项 frontend/TS/build，作者不将其计作本 WT 新运行结果。
- 真实工程 host/load-only、统一 codefreeze、逐案 once permit、语义与 UI capability 接线均由 root 在独立 review 接受后决定；当前资格 false。

## 实现者结论

- 建议状态：IN_REVIEW，提交后 clean STOP，等待独立 Reviewer；不自行 merge/main/push 或标 DONE。
- Reviewer/主控验收：待独立执行，本报告不自签接受。

## 独立 Reviewer — APPROVE（2026-10-16）

- Reviewer：`local_text_review_resume`；累计审查 exact base `e4c693f80ffff388bc494e1c27c6b9269255742e` → author `e0b123aaf241e39a8e4867c90ef48a53c9944763`。开始/结束产品审查时该 author SHA 均 clean STOP；本次仅追加本交接报告，不修改产品、测试、任务状态或 root。
- 结论：**APPROVE，P0=0 / P1=0 / P2=0**。仅接受本任务工程合同；没有实际 metadata/load/debug/generation、permit 签发、模型语义验收或资格开放。生产资格仍 false。root 的真实 host/load-only、统一 freeze/once 和最终 UI/core 验收不算本次 PASS。
- 独立读取 actual cumulative diff、task/agent-prompt、容量 proof plan/已有来源证据及 root 最新 `32eb456` / `b2257e9` / `7fadbd5` 决定，未将 root docs cherry-pick 入 author。graph 对新容量符号无可用当前内容，按固定 SHA 的实际文件与调用链复核。五轴结论如下。

### 正确性与安全边界

- 完整请求严格限定 system+user 两角色、固定 prompt/schema/model/options 和八个顶层字段；body 12,288、content 8,192 分别计算。UTF-8 原文、JSON 转义资源界和 canonical identity / 保序 wire hash 分开；bound=actual content bytes+88+2，最坏 8,282+6,144+1=14,427≤16,384。原四输入 4,822/4,825/7,869/4,149 bytes 与 2/2/15/2 Evidence 全部保留。补独立 BOM、汉字、emoji、组合字符、NUL、CRLF/tab/U+2028/U+2029 及非法 surrogate 反证，未用近似 tokenizer 或外部 proof bool 替代编译合同。
- prepare 在受控 lease 内验证固定 manifest、全部 blobs/三 binaries、renderer/tokenizer、唯一当前 server/runner、单 slot ctx、资源；cold 仅合法 messages:[] load-only，随后复验 ps/host。独立六轮 Settings available 仅 version/tags GET，0 chat/load。已有官方来源与字节词表证明是固定模型前提，不能泛化到任意模型。
- 同应用 ASR 文件锁和 Backup background gate 覆盖 score/judge/summary/translation factory 的实际 transport/read/close/异常完整周期。实际 provider exact type、同线程嵌套、另线程和真正子进程 LocalTranscriptionJobs `_slot()` 竞争已独立执行。lease 拒绝/丢失不会进入底层 transport；不取得 worker 非重入 mutex。
- PENDING/inv1 立即关闭且不做 metadata。terminal AMBIGUOUS 的 checkpoint/resource、未知成本/身份字段及允许 outcome 一致后，仍须固定新 server 启动严格晚于历史 unknown、ps[]、无 runner 且前后 process 身份一致，才能独立新工作。独立新增 12 类 resource mismatch（含 provider/model/source/video/reason/use_case/invocation/budget/outcome/actual fields）全部在机器证据前关闭；另 9 类 restart witness 负控覆盖同时间/更早/runner/multiple server/wrong binary/ps busy/version/重复 JSON/观察中 server 改变。不抹历史、不中止或重发旧 unknown，无持久 bypass bool。
- readiness 绑定 execution、两个 request hash、owner thread、host 和 preclaim TTL；最终 intent I/O 后 arm，再执行既有 claim。成功 claim 后不再 TTL/metadata/fingerprint I/O，仅消费一次 token、重建纯 hash 后唯一 POST；preclaim 失败/取消为 0 invocation/POST，claim 后失 token 为 inv1 AMBIGUOUS 并如实记本机 POST 未发生。原 claim 不可抹 trigger 与原 RED 日志保留。超时/replay 不发第二次。独立反证 consumed token 不可重 arm、另一线程不能消费或释放原 owner lease。
- harness 限 dedicated private sibling workspace，prepare 在 reservation 前验证路径/UID/非 symlink/hardlink、dev/inode、restore marker 和 lsof；execution/arm 复验。新增真正 `/usr/sbin/lsof` + 隔离 Python holder 的正/负/释放后正向检查，外进程持 DB 时拒绝。O_EXCL/fsync 的 ARMED 只代表 spent intent，不代表 generation；没有将独立 harness 描述为跨进程 Backup 全局锁。root 冻结仍须明确排除该专用库上的 GUI/API/其它 Backup 服务。

### 回归、测试质量、范围与可维护性

- 独立 AST/逐字节核验四个 Cloud transport、LocalTextDistillationProfile、旧 None-profile generate 完整 suffix 保持原样；providers/ollama.py、state、backup_restore、intelligence_read、source_policy、039 SQL、空资格 resource 全字节相同。两个 optional guard provider 是明确授权变更，没有将其虚称零 diff。新容量模块、两 provider、ASR、Backup 和 composition 均纳 CODE_FILES；实际执行代码/算法上限改变会使旧资格 binding 失效。
- 旧断言调整仅对应尚未冻结新 profile 的 ctx/options 与精确 prompt bound；原 overload 拒绝改为 actual bound/+1 控制，没有删除、skip 或降低旧 Cloud/8b/39 黄金、费用、安全与恢复断言。原 expire-after-claim → invocation0 不可能合同及其失败证据保留，按 root 精确决定改为 preclaim arm，不修改 schema/trigger 来绕过。
- 累计 15 paths 均在任务及上述 root 相关 scope 内，无 frontend/Schema/state/source_policy/dependency/config/owner DATA 改动。DIRECT 标准库、现 ASR/Backup/claim/builder，REFERENCE 固定官方来源，无第三方生产依赖或下载执行。接口与 helper 分离明确，没有新增外部调度器或任何 fixture qualification authority。

### 本 Reviewer 实际执行证据

| 独立检查 | 结果与本机日志 |
|---|---|
| unit local_model_capacity/local_grounding_harness/local_grounding_qualification/local_grounding_profile；integration local_capacity_composition/local_grounding_proof | **178 PASS / 80.71s**；`/tmp/capacity-review-focused.log` |
| unit distillation_dispatch/ollama_local_distillation/openai_distillation_adapter/moonshot_distillation_adapter；integration local_intelligence_timed/local_intelligence_text/local_distillation_wire_branches/task023b_distillation_reservation/task019_trusted_intelligence_read/offline_transcription_jobs/local_transcription_service | **248 PASS / 190.79s**；`/tmp/capacity-review-regression.log` |
| unit backup_restore；integration v1x_phase1b_backup_restore/research_backup_restore/runtime_composition | **109 PASS / 78.42s**；`/tmp/capacity-review-backup-runtime.log`；仅既有 malicious duplicate ZIP-path 负控 warning |
| 新增临时独立 Unicode/unknown/restart/Settings/consumed-token/thread/真实 lsof 反证 | **28 PASS / 4.93s**；脚本 `/tmp/test_capacity_independent_review.py`，日志 `/tmp/capacity-review-independent.log`；不写仓库测试 |
| `PYTHONPATH=src:. .venv/bin/mypy src scripts/qualify_local_grounding_v1.py` | **PASS，106 source files**；`/tmp/capacity-review-mypy.log` |
| `.venv/bin/ruff check src tests scripts`；compileall src/harness；`git diff --check e4c693f..e0b123a` | **PASS**；Ruff `/tmp/capacity-review-ruff.log`，compile/diff exit0 |
| 独立 AST、旧 suffix/安全基础文件 bytes、CODE_FILES 和空资格 | **PASS**；`/tmp/capacity_review_ast.py`、`/tmp/capacity-review-ast-corrected.log` |

总计本次独立 **563 PASS**，无跳过项；未冒充作者 1,015 全套是本 Reviewer 重跑。上述 pytest 统一使用 `PYTHONPATH=src:. .venv/bin/python -m pytest -q`，将表内模块名还原为各 unit/integration 下 `test_*.py` 即可复验。前端零 diff，本次不重复 frontend/Chrome，不触 root 正在运行的服务。

QA 脚本自身的初错原样保留：`/tmp/capacity-review-ast.log` 首次 AssertionError 是探针错误使用不存在的 `OpenAIDistillationTransport` / `MoonshotDistillationTransport` 名称，核对实际 AST 后改为四个确切 Cloud class names，同一对照算法 PASS；未改产品或弱化比较。一次只读查找猜测了不存在的 qualifications 文档路径，随后确认实际固定 resource 为 `src/youtube_intel/resources/local_distillation_qualification_v1.json` 并逐字节/reader 验证 records[]。

### 接受的明确限制与 STOP

- 固定本地受信 runtime 前提仍成立才可执行；文件/进程 metadata 与 HTTP 观察不是对恶意同机服务的密码学绑定，应用锁不约束外部 Ollama client，不宣称物理 exactly-once、跨机器锁或跨进程 Backup 全局锁。
- 工程 fixture 不证明实际资源充足、真实 load 成功或语义质量；任何安装/renderer/runner/slot/profile 改变继续关闭，未来需新的当前证据/审查。所有模型资格仍 false；最终 root 验收与工程整合独立进行。
- 本 Reviewer 只提交 handoff 后 clean STOP，等待 root 调度；无 main/merge/push。
