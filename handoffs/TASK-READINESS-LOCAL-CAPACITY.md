# TASK-READINESS-LOCAL-CAPACITY 交接报告

## 元数据

- Task: `TASK-READINESS-LOCAL-CAPACITY`
- Role: Implementer
- Agent: `native_scan_resume`
- Base: `e4c693f80ffff388bc494e1c27c6b9269255742e`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-local-capacity`
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
