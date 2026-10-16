# TASK-READINESS-TRACKED-CONTENT-RETRY — 后端基础检查点

## 元数据与当前范围

- Implementer: `local_text_repair_resume`；base `c312ee4a544556616c9b102d57ec44cf56a21b90`。
- WT `/Users/hua/Documents/yia-worktrees/readiness-tracked-content-retry`；branch `codex/task-readiness-tracked-content-retry`。
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
