# TASK-READINESS-TRACKED-CONTENT-RETRY — 2026-10-19 完整作者交接

## 当前结论与精确提交

- Implementer: `tracked_retry_resume_oct19`，恢复既有WIP；没有重新开任务、覆盖旧作者或第二writer。
- WT `/Users/developer/Documents/yia-worktrees/readiness-tracked-content-retry`；branch `codex/task-readiness-tracked-content-retry`。
- 累计基础为 `c312ee4a544556616c9b102d57ec44cf56a21b90`；恢复时HEAD `4b9aa0ad34bb56e82cbab0e6061948b217866c6a`，包含基础 `43e0c75` 及已审picker `26a2984/4b9aa0a`。
- 后端/恢复/迁移/协议测试/精确合同：`7809c61`。
- UI、双语copy、前端测试、普通factory隔离fixture、真实Chrome脚本与截图：`30372a6`。
- 本交接及检查证据为随后docs-only提交；**建议IN_REVIEW，作者clean STOP，不设DONE、不自行main/push/发布**。原foundation REJECT须独立累计复审，不能仅凭作者自审接受。

## 实际完成范围

- 补专属worker、provider/dispatch/epoch、实际store/request flock生命周期、write-ahead文件/buffer闭包、严格正反向reader、timed/Evidence/extractive Summary本地完成、3次本地恢复与明确取消/关闭出口；普通runtime factory/worker/API/中英文Content UI已接线。
- 修原foundation F1：`mark_provider_dispatch_ambiguous`同事务require_provider，generic不能持旧owner改本协议；F2：typed事件、action/receipt/hash/epoch、原job真实最后attempt、target/provider/文件及完成投影重验；F3：040 VERIFIED observed hash/size明确非NULL，INSERT与更新负控保留。
- 新command初始准入保留generic五项白名单与真实最后attempt。协议attempt0后继由完整不可变父request、取消/本地失败receipt、零provider/dispatch/attempt/artifact/files、真实父request锁证明；不造attempt。另对真实prep attempt1的容量关闭用独立typed receipt、NOT_DISPATCHED/无intent marker、完整provider/attempt/文件证明才授新人工后继，不扩generic名单。
- 父链迭代全量验证，无递归/截断；循环、错source、缺祖先/receipt/marker、错epoch/attempt、未知provider、残留文件与活writer拒绝。1051条合法取消历史可新建command，中间祖先receipt被删仍拒绝。
- 固定128事件。acquisition/claim/preHTTP预留16；剩余local `r`次在claim/finalize前预留`4*r+2`、RESUME前`4*r+1`。逼近预算时不消耗新的claim，直接做真实纯本地结果，保留后续所有合法attempt及Close。本版普通执行不制造“126+SUC+尚有合法本地attempt却只能Close”。详见执行补充合同。
- typed明确adapter失败先持久化provider FAILED_FINAL+FAILED_KNOWN同事务，再由worker结清执行/文件；receipt前中断仍未知，receipt后中断重启恢复已知失败，不重复HTTP，原错误code/message保留。
- API历史action按不可变request校验路由Content归属，新child建立后旧取消同command仍可重放；错Content在写入前拒绝，重放也重验完整authority。
- Backup显式兼容34–40，40按精确Schema与manifest引用/字节全闭包验证，live/finalizing/attention阻塞；已持锁诚实结清的专属AMBIGUOUS保留未知语义并可备份。旧schema不backfill协议记录，实际原文件全部保留。

## 验收证据与覆盖时点

可重验命令、原始输出及source SHA-256：`docs/validation/end-to-end-user-readiness/tracked-retry-checks/validation.json`。以下各集合重叠，不能相加冒称独立总数。

| 检查 | 实际结果 | 精确覆盖说明 |
|---|---|---|
| 11文件累计后端 | **461 PASS**，405.90s | 含最终known receipt修复；启动早于后来historical-action API修复，不冒称整套加载后者 |
| fresh tracked协议 + Local API | **125 PASS**，119.72s | 最终产品代码，覆盖新历史action路由/完整服务重放验证 |
| 最后错Content无写断言 | **1 PASS**，2.15s | 同一API测试额外增强，产品代码未再改 |
| 字幕adapter/policy/timed/following/SourceRun扩展 | **351 PASS**，82.72s | 普通字幕路径与原跟踪边界；早于最后known/action两项，后者由上述新集合覆盖 |
| Schema34–40 | **7 PASS**，5.33s | 非空fixture每种版本全部table/行与全部DATA bytes，恢复前后完全相同；迁移后旧领域行/旧migration历史仍同，协议三表为空 |
| known receipt前后真实中断及unknown/失败 | **6 PASS**，4.51s | 新服务实例重启；中断前未知关闭，中断后known可明确新请求；包含在125中 |
| 真实多次崩溃的源头预算 | **2 PASS**，8.96s | 112次predispatch claim中断后114事件诚实关闭，attempt1保留、新command成功；SUC后百次级local claim中断仍用足3次local attempt及Close，0字幕重取，事件≤128；包含在125中 |
| prepared容量父链全量恢复/重新hash破坏 | **5 PASS**，10.33s | 所有table dump和全部DATA bytes；receipt/marker/attempt/provider破坏即使重算ZIP hash仍拒绝；包含在125中 |
| strict mypy src | **111 source files PASS** | pyproject strict=true，不变更工具链/依赖 |
| Ruff / diff check | **PASS** | 全src及全部相关Python变化，staged diff再次复核 |
| frontend全套 + TS/Vite build | **956 PASS** / **PASS** | 35 files；原有React act warnings未隐藏，新增组件19项无新警告 |
| 真实Chrome | **24 PASS** | en/zh-CN × 1440/320 × eligible/queued/cancelled/attention/finalizing/succeeded；每次真实document加载，并断言DOM状态文案后截图/核API，不使用hash-only旧DOM；无横溢/console error或warning/浏览器外部请求 |

Chrome使用普通`build_local_source_run_runtime`、真实loopback API/SQLite/专属worker，仅字幕provider和失败窗口为离线可控边界。取消后新command、一次目录+一次body、local ATTENTION→RESUME→真实Summary/Evidence通过；完成2条Evidence，原取消target attempt0、新成功target attempt1。完整JSON与24截图位于`docs/validation/end-to-end-user-readiness/tracked-retry-browser/`；脚本为`frontend/tracked-content-retry.e2e.mjs`及`tests/e2e/tracked_content_retry_fixture_server.py`。这不是root真实旧tracked数据的验收替代。

## 原失败与修正均保留

- 共享venv初始未指定PYTHONPATH，导入`/Users/developer/youtube-intel`旧代码导致collection失败；后续全部`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.`指向当前WT，没有改环境或安装依赖。
- 额外源头预算前对event revision误作精确等于projection，合法heartbeat只增revision不加event的双进程反证失败；恢复原monotonic gap合同，epoch/typed事件仍严格；真实process后重验通过。
- 扩展旧测试的latest39期望导致48个setup失败；仅更新latest40和追加040 migration期望，保留全部旧历史/断言；48重跑通过。混合来源恢复版本39断言同样精确改40，单项通过。
- Chrome初版`/tmp`祖先symlink被managed_directory拒绝，HTTP500；只修隔离fixture root.resolve，不放宽产品路径保护。又发现同hash导航保留旧DOM，旧截图不算PASS；改真实document加载+每状态文案断言，最终重新输出全部截图。
- known failure窗口原`AMBIGUOUS != FAILED`红例保留；初修只加repository hook仍失败，持久状态证明私有_fetch_reserved不经outer fetch、实际仍PENDING/INTENT；停下重复方案，改typed adapter callback源头receipt后绿，before/after反证完整。
- 历史取消API原latest-only归属检查在新child后返回409，红例保留；改immutable request归属及full authority重放后绿，错Content SQL dump无变化。
- 原始正/反例日志在`tracked-retry-checks`及manifest列出的`/tmp`路径中；未删除/跳过测试、未弱化断言/阈值或改CI脚本掩盖失败。预期重复ZIP路径warning与既有React act warnings完整保留。

## Diff / 复用 / 剩余门禁

- DIRECT：已批准SQLite事务/外键、fcntl、managed_directory/hash、现provider request builder、native字幕验证、timed/Evidence authority、extractive Summary、现Backup background gate。ADAPT仅专属authority/dispatch/file hooks；来源均当前仓库已审基线，无外部复制代码或新许可证义务。REJECT：假SourceRun成功、全pipeline drain、复活旧job/provider、假m038 successor、动态失败数生成provider身份、客户端自报权限。
- 没有依赖/lockfile/toolchain/config/credentials/正式Vault变更，没有模型资格签发、付费模型生成或正式用户数据写入。040仅隔离fixture/恢复副本验收，没有正式迁移。旧034–039 SQL未改；额外三份老测试仅当前版本期望及完整性增强。
- 仍需：独立累计审查原foundation三项+全部新diff、root正式候选全仓回归、root真实旧CHANNEL/ENROLLED失败全DATA隔离副本的普通GUI→字幕/Summary/Evidence→实际重启→全表全DATA恢复。
- root另行记录的真实38混合字幕兼容任务保持串行，不扩入本次，也不以本fixture成功冒称它已解决。
- 当前无作者已知仍失败的本任务检查。最终接收/合并/发布由root决定；本作者STOP后不继续写产品或替代Reviewer。

---

以下完整保留2026-10-17基础检查点，属于历史，不是当前范围/结论。

# TASK-READINESS-TRACKED-CONTENT-RETRY — 后端基础检查点

## 元数据与当前范围

- Implementer: `local_text_repair_resume`；base `c312ee4a544556616c9b102d57ec44cf56a21b90`。
- WT `/Users/developer/Documents/yia-worktrees/readiness-tracked-content-retry`；branch `codex/task-readiness-tracked-content-retry`。
- 2026-10-17 checkpoint，**尚非完整任务/不可整合采用**。按root要求在合适后端检查点commit clean STOP，供root顺序整合已审picker UI提交后继续本任务。
- 此段仅040三表、冻结admission/基础reader、稳定锁、generic隔离和对应测试；没有API/runtime/worker/IO/Backup接线，没有frontend变化。
- DIRECT SQLite/fcntl/managed_directory/现provider hash builder/verify_tracking/现字幕metadata类型；无新依赖。ADAPT仅新协议边界，不造SourceRun/旧stage成功。

## 已落地的基础合同

- 040新增immutable request、CAS execution和file intent三表及identity/state/history/同源互斥保护。observation复合FK精确引用现表`(source_id,canonical_identity)`。
- request固定完整客户端输入、原job全行快照、actual metadata/语言/adapter/selection/native等参数、稳定target和refresh generation、provider request身份；同command同输入返回历史，不因paused或adapter当前不可构造而重做；oldjob唯一消费、一个事务admit。
- 真实tracked资格校验含CHANNEL/ENROLLED/METADATA_READY/已知TRANSCRIPT FAILED_FINAL及最后attempt/无活跃或未知provider；OFFLINE历史不清。SourceRun/check两序guard及同源live唯一约束。
- generic claim/reclaim/activate/rerun/create/provider reserve/recovery/完成保护排除新协议target和被消费旧job；显式job_id和未来协议prefix不授generic执行权限。新专属worker的authority context尚待后续接线。
- store/request稳定flock目录不随DATA/DB payload替换，不unlink锁文件；排他创建后打开既有inode、核owner/type/link/inode。锁与epoch接口不等于已证明完整worker/child生命周期。

## 原库只读核对

按task明确授权，使用SQLite URI `mode=ro` + `query_only=ON`，不initialize、不复制、不迁移原库。实际userversion **37**；指定public Content为METADATA_READY/runtime-v1，old job `0c925f83-abb1-4ad1-9f7d-236dd0d86b37` 为TRANSCRIPT/FAILED_FINAL/INVALID_RESPONSE/attempt1 max3、lease空；attempt14同码且finished；CHANNEL enabled/DISCOVER_ONLY，ENROLLED baseline0/content_id/link一致，source last_error OFFLINE保留。所有后续运行均新隔离fixture，无正式写入。

## 检查和保留失败证据

- 初始RED `/tmp/tracked-retry-initial-red.log`：缺新module；schema测试初版漏initialize(now)亦保留，修正测试调用，无断言移除。
- `/tmp/tracked-retry-admission-third.log`：新target被generic claim领取的真实反证；隔离后基础2 PASS（`/tmp/tracked-retry-store-green.log`）。
- fixture问题日志 `/tmp/tracked-retry-foundation-tests.log`：SourceRunWrite缺priority；unknown负控原只UPDATE不存在dispatch row未真正造坏状态。分别补正确必需参数、INSERT真实ambiguous关联并断言负控已建立；原资格/历史/无写断言全部保留。
- 首次扩大检查 `/tmp/tracked-retry-checkpoint-tests.log`：两个admission并发开锁时O_CREAT返回ENOENT。隔离8线程/1000次真实探针复现2次，`/tmp/tracked-retry-lock-race-diagnostic2.log`；第一版探针因/var祖先symlink被managed_directory正确拒绝，原log也保留。改为O_CREAT|O_EXCL原子创建，EEXIST才无O_CREAT打开既有inode，不盲重试、不删除锁。
- `PYTHONPATH=src:. .venv/bin/pytest -q tests/integration/test_tracked_content_retry.py tests/unit/test_state_transitions.py`：**25 PASS**，9.38s，`/tmp/tracked-retry-checkpoint-tests2.log`。含15新协议基础测试/真实spawn进程阻止抢锁和Backup穿越/1000并发开锁同inode/040回滚与39领域行保持。
- state/provider老测试首轮 `/tmp/tracked-retry-foundation-legacy-tests.log`：44 PASS/9 FAIL，均为最新schema仍期待39、table/index集合未含40。只更新latest版本/checksum/registry和新增精确table/index期望；旧39 history断言保留且新增40 history断言，不弱化检查。重跑结果待下条最终checkpoint补录。
- `.venv/bin/ruff check` scoped7files：PASS；`.venv/bin/mypy src`：**108 source files PASS**。日志 `/tmp/tracked-retry-checkpoint-{ruff,mypy}.log`。语法compile检查通过，`git diff --check`通过。

## 下一段必须完成，不能用此检查点冒充可用

1. 专属claim、same logical attempt/epoch、preHTTP intent、typed known/unknown失败隔离、native timing gate、同步adapter/child/callback真实证明。
2. 新协议file write hooks/journal/buffer保留与严格正反向reader，不能漏文件或复用m038伪successor。
3. job成功后timed/Evidence/extractive Summary本地恢复，合法终态/RESUME_LOCAL/CLOSE_LOCAL/取消幂等、无重HTTP；未知仍closed。
4. worker/runtime/API严格接线；Schema40 Backup条件manifest、quiescence/store lock、unknown专属settled证明、34–40完整恢复与rehashed破坏矩阵；doctor版本和历史migration测试适配。
5. root整合picker已审UI commits并明确解锁后，才实现Retry frontend与全frontend/TSbuild/真实Chrome状态矩阵；独立review及root真实旧tracked副本全链后才可能DONE。

未运行完整backend/真实恢复矩阵/worker/Chrome；它们尚未实现，不能报告PASS。模型/付费/外网/正式数据写入均0，未改frontend/依赖/config/资格/旧034–039 SQL/公共状态。当前无未解决基础段失败时提交；整个任务仍IN_PROGRESS，等待root安排续作。

### 检查点最终结果

- state/provider老回归重跑 **53 PASS**，15.68s（`/tmp/tracked-retry-foundation-legacy-tests2.log`）。本检查点合计78项通过；不是完整任务验收。
- 基础段diff经范围/测试期望/旧history保留复核，无未解决基础段失败。按root要求提交后clean STOP，不自行整合picker或继续写frontend。
