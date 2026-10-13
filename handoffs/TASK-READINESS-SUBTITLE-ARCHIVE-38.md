# TASK-READINESS-SUBTITLE-ARCHIVE-38 交接报告

## 元数据与具体授权

- Implementer：`/root/caption_resume`；Reviewer：`/root/intel_bounded_review`，实现者不自审。
- Base：`a2c668bbe32d1acc4bcf83176a331eb3e850e09b`。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-subtitle-archive-38`。
- Branch：`codex/task-readiness-subtitle-archive-38`。
- 具体批准：`FAILED_SUBTITLE_ARCHIVE_APPROVAL.md` / `FAILED_SUBTITLE_ARCHIVE_MIGRATION_PROPOSAL.md`；只隔离实施、迁移与验收，不授权正式数据迁移或采用。
- 主控补充范围：`runtime.py::_database_check` 仅将现有 doctor 的当前版本判断 37→38，配套 schema38 PASS / future39 FAIL；冻结语言候选仅 `en` 与 `zh,en`，adapter 版本 `2026.7.4`，来源为主控隔离配置的非敏感字段及现有锁定版本。没有将当前配置当作旧输入。

## 实现与复用

DIRECT 既有事务迁移、SQLite `BEGIN IMMEDIATE`、protected background/restore staged lock、provider CAS、raw capture 身份、冻结字幕 normalization/quality、managed DATA reader、真实 ORIGINAL Evidence resolver、普通 Summary reader与 Backup 路径/限额/ZIP校验。ADAPT 仅批准的中性归档及新旧 manifest 分支；没有新的 Provider 或执行系统。复用项目已有代码/标准库，无外部代码、依赖或许可证变更。

- Migration 038 只追加 `retained_subtitle_derivations` 表，全部 23 个批准字段、FK、hash/size/枚举/path/JSON/时间形状 CHECK、request/job/path 唯一索引、UPDATE/DELETE 拒绝触发器；注册 migration38。未改旧表、旧 migration 或历史 schema receipt。验证实际 DDL 与包装的精确 migration DDL 相同，不仅检查版本号。
- `state.archive_failed_caption_repairs` 在相同数据库的 Backup authority、idle protected gate、restore/stage 锁和 SQLite 写事务内，要求阻塞原因精确只为 unresolved provider calls；先验证全批全部项目，再追加中性 proof 并 CAS 旧 ledger 为 `FAILED_FINAL`。原 error/message/attempt/available 与全部 job/attempt/source-run 保留；只改变 status/finished_at/updated_at。任何项目、未知文件或事务注入失败整批回滚。
- `transcripts._retained_caption_proof` 只接受 current-v2 `subtitle.fetch/yt-dlp/model=NULL` 的精确 completion 持久化错误，明确终结的 caption-repair child 与全部 attempts、无 owner/lease/response/usage/cost/dispatch、正规 UTC/整数计数；唯一同源 run/job SHA关系、父 plain 原始字幕、固定原输入 hash/capture 全身份、文件原 hash与按冻结算法重算的 derived bytes/path/canonical request 均必须吻合。
- 后继必须为同源真实完成的新 repair child、当前 trusted timed transcript/current deterministic Summary/完整 ORIGINAL Evidence，provider response、canonical、binding、Summary bytes/request/每项 excerpt 均重新证明。中性文件不登记普通 Artifact，不赋 Transcript、时间轴、Evidence 或成功输出权力。归档 proof 保存原 ledger/attempt/input和后继历史完整绑定；以后备份验证这些固定后继历史，不要求当前 Summary 指针永久不变。
- 普通 idle maintenance 在既有旧政策退休前调用正规归档接口；不重新 GET 字幕、不调用模型、不重放执行。重复、重启、恢复后已终结记录无新增执行。
- Backup/Restore schema38 合并普通 Artifact 与中性引用，同 path 同 hash/size，一份物理字节只计一次；38 精确 record 加 `retained_subtitle_derivations` refs、counts 加 `retained_derivations`。旧34–37 record/count形状不变，显式支持37。新包验证全部 proof、完整 refs coverage/排序/唯一性及文件 hash；缺失/额外/重复/tamper 拒绝。public preview 原 flat 计数字段保持不变。
- readiness/create 对物理 DATA 全集与已验证索引全集做精确比较，扫描仅检查覆盖，不推广未知文件；任一未知文件继续阻塞，不能静默丢弃。原路径、symlink、regular-file、size/ZIP/磁盘限制与 quiescence 保留。

## 兼容、恢复与风险

Schema34–37 包按其原严格 manifest 合同恢复，再启动迁移只追加空中性表；恢复全表/文件与旧版本相同。038 DDL 故障回滚 schema/history/userversion37，正常重新迁移可恢复。Schema38 包不能交旧程序伪兼容；若回退，应使用迁移前完整备份及原程序，不删表、不降版本、不 reset 数据。

归档只处理能够完整重建原输入、已有 pre-stage raw、明确失败且有真实成功后继的批准集合；无法证明的历史、其它 provider/policy、未知执行或 extra DATA 仍阻塞。主要风险为错误退休、权力提升、遗漏字节和旧包兼容；由严格 proof、独立不可变表、whole-batch CAS 与全文件恢复负控控制。真实 macOS GUI与隔离当前失败库是否满足白名单是主控后续门禁，不能由受控 fixture PASS 替代。

## 检查与外部证据

日志保留于本 tree `.var/subtitle-archive-38/`（不提交测试数据库/构建/runtime symlink）。

| 检查 | 实际结果 |
|---|---|
| 52 项 archive-focused integration | PASS / 86.81s，`focused-extra.log` |
| state store / lineage / doctor 65 项 | PASS / 19.18s，`schema-final.log` |
| Bilibili current-schema全文件 15 项 | PASS / 5.21s，`bilibili-schema-corrected.log` |
| Domain persistence 全文件 8 项 | PASS / 1.68s，`domain-current-schema-corrected.log` |
| 最后 suffix-only 修正后 Saved Intelligence 全文件 48 项 | PASS / 19.27s，`saved-migration-suffix-final.log` |
| py_compile | PASS |
| Ruff src/tests/scripts | 最终 PASS，`ruff-commit-final.log` |
| strict mypy src / MYPYPATH=src | 最终 PASS / 102 source files，`mypy-commit-final.log` |
| Backend 全量 4312 cases | 4310 PASS / 1 FAIL / 1 既有 SKIP / 2 warnings / 1151.97s，`backend-final.log`。唯一 FAIL 是 saved 当前迁移名称 suffix22 与精确23条断言不匹配；后续仅 suffix→23，whole-file48 PASS。**不声称完整全量 PASS**；主控明确不重复旧基线19分钟，接受整合后仍需最新完整回归。 |
| git diff --check | PASS；提交前再核验 |
| Frontend/TS/Production build | 本切片未改前端；主控整体门禁仍必需 |
| 真 macOS GUI Backup/download/preview/RESTORE/restart 全表全 DATA | 主控验收待完成，不声明 PASS |

52 项覆盖：真实 adapter identity 的本地受控 transport 正常 plain→事务失败→显式新child成功；归档全历史保持、不可变性、重复/重启/恢复0新 GET；Backup stage/confirm/restart全表与全部物理 DATA bytes精确一致；owner/live或旧lease/response/dispatch/usage/cost/unknown/PENDING；policy/provider/model/source/time/count；raw/derived合法变字节、missing/changed Summary、extra未知file、未结attempt/otherjob/checkpoint；全批失败回滚、before_commit故障、锁/restore gate、旧请求重启 reservation race只一方胜；zh/en冻结输入；历史后继当前pointer改变仍可恢复；普通/中性同path bytes只计一次；old34/35/36/37 与38完整恢复、DDL回滚、manifest缺漏/重复/错hash/错count/旧形状全部拒绝。

## 失败证据与处置

- `tdd-red.log`：接口未实施 AttributeError，保留初始红证据。
- `green-full-restore.log` / `green-full-restore-fixed.log`：先误读 `RestorePreview.counts` AttributeError，再误读 `preview['counts']` KeyError；停止猜测，独立读取现有 `_public_preview` flat API 后按真实 preview 合同和 ZIP manifest 验证。未扩大 public API、删断言或改测试脚本。
- `negative-first.log` / `negative-fixed.log`：负控 fixture 使用非法 job scope，检查现有合同后改为真实 `channel:UC_ARCHIVE_NEGATIVE:discovery`；最终 focused52 PASS，保护检查未削弱。
- `focused-wide.log`：现有精确 table/index 集合缺38追加，修复保留旧条目后的 schema65 PASS。
- `backend-full.log`：PYTHONPATH 仅 src，4 项 tests/scripts 导入 collection errors；无测试执行，改为 `PYTHONPATH=src:. python -m pytest`，没有改依赖/toolchain/scripts。
- `backend-full-corrected.log` / `bilibili-current-schema-failure.log`：Bilibili当前 schema expected37 vs actual38；该轮 687 PASS/1FAIL 后只中断已核对 cwd 的本 worker 测试进程。修正遗漏的当前版本断言以及精确迁移名称列表追加38/后缀22→23，保留历史37回滚断言。最终文件重跑全量，未将中断轮当通过。
- `backend-final.log`：完整4312项中4310通过，唯一失败 `test_task025a_saved_intelligence.py:50` 的 `names[-22:]`，预期列表完整包含23项。只改为 `[-23:]`，未改预期值/删断言；该全文件48项及语法/Ruff/mypy/diff随后通过。既有 skip 仅 `test_o200k_provisioning.py` 要求显式 provision 的 canonical asset，本任务无依赖/下载授权；两 warnings 是重复 ZIP path 负控和 Pydantic construct-bypass 负控。主控具体要求保留上述 FAIL，不在旧基线重复19分钟套件，最终采用前另跑接受整合后的完整套件。
- 初 Ruff/typecheck logs 保留；只修本范围语法/类型与新增测试格式，未新增 ignore、skip 或阈值修改。
- Root 原真实 Restore 全文件失败证据及 V1 模型真实 FAIL 不改；本切片模型/cloud 调用0、资格门禁不变，不操作正式 owner/config。

## Diff 与交接状态

业务变更严格为五个既有 backend 文件、追加 migration038；其余现有测试仅更新当前版本及追加精确迁移 table/columns/index/history 条目，原历史断言、所有旧 tests 与保护保留；新增一个 focused integration 文件、本交接。runtime.py 是主控明确同意的单行 doctor 补充，无其它行为。无前端、Schema旧表、deps/lockfiles/config/credential/model/corpus/threshold变化，无生成文件进入提交。

实现者建议：`IN_REVIEW`，本交接所属提交完成后停止写入；完整全量/真实 GUI 与资格依赖均不得由本提交替代。独立审查及真实主控 GUI 未满足前不得采用，不自行 DONE/main。

## 主控真实 GUI 复现准备（仅说明，没有执行）

使用真实已导入且缺 trusted timing 的隔离 plain Content 快照，保留原 raw/authority；fresh native import 已 timed 时不可人为剥离 authority 来造此状态。accepted38 后在单任务隔离 runtime 安装一次性 `repository._inject_failure(point: str)` hook，仅 `caption_repair.after_authority` 抛 RuntimeError；该点处于 `complete_caption_repair` 同一写事务，real raw/canonical/timed/Evidence 已尝试写入、Job success 尚未提交。GUI 正常第一次 Source check→real yt-dlp native fetch→事务故障；还原 hook后另一个明确 command正常 retry→真实新child成功；下一次 idle worker 调用正规 archive。只读核对原 failed ledger/全部历史与所有 DATA，再 GUI Backup/download/preview/RESTORE/restart精确比较所有表与物理文件路径/bytes/hash。不得改 provider identity/原数据/假时间，不额外调用模型，不直接改 DB 放行；旧失败库复用需如实声明，不称新鲜故障实测。

## Reviewer / 主控验收

待独立 Reviewer，待主控真实隔离 GUI 全表全 DATA 恢复与整体回归。实现者不填写 APPROVE/ACCEPT。

## 独立审查 1 — REJECT（2026-10-14）

Reviewer：`/root/intel_bounded_review`，审查固定实现
`29f1e50f08a90407e8d0c7a5c331306dfa62ec39`，基线
`a2c668bbe32d1acc4bcf83176a331eb3e850e09b`。作者 STOP/clean 后开始；因仅允许一个
Reviewer，期间按主控要求暂停并等待小 UI 独立审查结束，再恢复。只读业务文件；
唯一仓库写入是本审查段。没有模型、provider、云端或正式 owner 操作。

阅读具体批准/提案/任务/仓库协议、全部 38 文件 diff、52 新测试完整边界；graph-first
查询本 worktree 未索引，按明确分配文件读取 fallback，没有建立或修改索引。
23 字段新增表/不可变 triggers、37 支持/34–37 原 manifest 形状、38 refs/counters、
DATA 全集检测、protected gate/BEGIN IMMEDIATE/whole-batch CAS、旧 ledger 原字段保留、
历史后继与当前指针分离的设计方向符合批准范围。现有测试改动仅更新当前版本和
精确新增迁移/table/index/columns；保留旧历史与回滚断言，没有删测试/skip/弱门禁。
这些正确部分不能覆盖下面的成功后继证明缺口。

### P1-1：未完整证明后继执行终结，仍错误终止旧请求并开放 Backup

位置：`transcripts.py:1203–1243` 的 `_retained_caption_proof`，准入和历史复核共用。
后继 job 只核对 SUCCEEDED/scope/identity、created 下界与 finished 上界；没有正规验证
后继全部 `job_attempts` 的终结状态/计数和租约记录，也没有约束 job/provider
`created/started <= finished <= updated`。`_quiescence_reasons` 的 terminal 状态枚举
无法证明这些被遗漏的执行字段。`state.py:4488–4499` 随后把该不完整 proof 写成
不可变归档并 CAS 旧调用为 FAILED_FINAL，Backup 的同一 proof reader 继续接受。

独立复现使用候选原 `_repaired_failure`：普通 API check/worker 的受控本地 transport
先产生精确完成事务失败，再正常另一个明确命令生成真实成功后继；之后分别只修改
该后继一项记录，全部在 fresh TemporaryDirectory 隔离数据库中。未伪造模型/源资格，
没有网络/推理。复现代码 `/tmp/readiness-archive38-independent-probe.py`，完整输出
`/tmp/readiness-archive38-independent-probe.txt`。命令：

```sh
PYTHONPATH=src:tests:. .venv/bin/python /tmp/readiness-archive38-independent-probe.py
```

| 单独损坏字段 | 实际结果（每例相同） |
|---|---|
| successor provider_calls.finished_at = `2000-01-01T00:00:00Z`（早于开始） | archived=true / ready=true / tables_changed=true / extra_fetch=0 |
| successor jobs.finished_at = 同一早于 created 的时间 | archived=true / ready=true / tables_changed=true / extra_fetch=0 |
| successor job_attempts.finished_at=NULL 且 outcome=NULL（尚未终结） | archived=true / ready=true / tables_changed=true / extra_fetch=0 |
| successor job_attempts.outcome=`LEASE_EXPIRED`（执行不明） | archived=true / ready=true / tables_changed=true / extra_fetch=0 |
| successor jobs.attempt_count=1.5（非整数/与真实 attempts 不符） | archived=true / ready=true / tables_changed=true / extra_fetch=0 |

预期每例都是整个批次不变、零归档、旧请求仍阻塞 Backup。特别是未终结或状态不明的
后继不能只凭 SUCCEEDED 行与现存输出解除安全阻塞。这违背获批“同源后继真实成功、
无未知执行、全部字段正规解析、时间/计数异常 fail-closed”条件，属于必须修复的 P1。
没有另一个已确认独立 P0/P1；这里的五项是同一后继 proof 完整性缺陷的不同反证。

要求原作者在批准的现有 proof 边界内补足：后继 job/全部 attempts/provider ledger/
source-run 身份与正规类型、UTC、完整时间关系、计数连续一致、已知成功终结、无活跃
owner/lease/未知 dispatch、usage/cost/null 状态保护；准入及不可变历史验证使用同一
完整证明，不能把当前可变行/terminal 字符串当历史可信快照。保留旧失败的全部证明。
必须新增上述五项及 malformed UTC/计数缺漏/未知执行/usage/owner/null 负控，含混合
批次原子不变、归档后篡改历史 proof 拒绝恢复；正常后继、future refresh/current
pointer、旧包恢复与无新增执行正控仍通过。此要求不扩大迁移表字段、provider 白名单
或资格范围，不需要新批准；Reviewer 不代作者修改。

### 独立检查和证据限制

| 检查 | 结果 |
|---|---|
| 先 py_compile 五个改动 Python 文件 | PASS |
| archive-focused + state store + lineage/doctor + saved Intelligence | **165 PASS / 116.44s**，`/tmp/readiness-archive38-review-tests.txt` |
| `.venv/bin/ruff check src tests scripts` | PASS，`/tmp/readiness-archive38-review-ruff.txt` |
| `MYPYPATH=src .venv/bin/mypy --strict src` | PASS / 102 source files，`/tmp/readiness-archive38-review-mypy.txt` |
| 五项独立后继负控 | **FAIL 安全预期**，输出如上；不能被 165 PASS 抵消 |
| git diff --check / 范围复核 | PASS，仅允许审查说明追加 |

165 命令为 `PYTHONPATH=src:. .venv/bin/python -m pytest -q
tests/integration/test_retained_subtitle_derivations.py tests/integration/test_state_store.py
tests/integration/test_task016c_phase_h2c_lineage_schema.py
tests/integration/test_task025a_saved_intelligence.py`，含全部新增52项、旧34–37/38恢复、
故障回滚、CAS竞态和 suffix 修正全文件。作者完整日志确为 4310 PASS / 1 FAIL /
1 既有资产 SKIP，后续48专项通过不是完整全量 PASS；不重跑19分钟旧候选完整套件。
真实 GUI/最终整合后的完整后端/前端/TS/build仍由主控完成，当前不能声明迁移验收。

**Verdict: REJECT；未解决 P0=0、P1=1。** 不整合此实现、不操作正式 Schema/main；
保留失败和原实现，由原作者修复后提交新 SHA 再独立复审。Reviewer 完成审查提交后 STOP。

## 原作者 P1 返修交接：2026-10-14

基线为上述独立 REJECT `658cd53c946054d1e184a7743929279cdcffc3bf`，原实现
`29f1e50f08a90407e8d0c7a5c331306dfa62ec39` 保留，不改原审查/五项失败探针或旧完整
回归日志。主控明确本返修在既有获批后继完整证明范围，无新增迁移或权限。

实际四文件：`transcripts.py`、`state.py`、此 archive integration tests、本交接。
没有修改 migration038、23字段、旧34–37合同、配置/模型/Cloud/依赖或正式数据。

- 新有界 `_retained_successor_execution` 正规验证 SUCCEEDED Transcript Job 的类型、
  attempt/max整数计数、可用/创建/完成/更新时间完整顺序，无 owner/lease/错误或跨
  scoring 权力字段；全部 attempts 连续编号、对应 Job、非空历史 owner、正规 UTC/
  起止/租约顺序、最后唯一 SUCCEEDED 与 Job 完成时间吻合，之前仅已知已终结
  RETRY_PENDING+正规错误。不接受 open/LEASE_EXPIRED/未知结果或缺计数。
- 后继 provider call 必须精确成功、正整数与 Job attempts 相容、完整开始/完成/
  更新时间和 available UTC 顺序、response绑定，没有 owner/lease/usage/cost/残留
  错误或任何 dispatch。普通 request/raw/canonical/Summary/Evidence 完整证明仍保留。
- 后继 SourceRun 同源唯一明确 command；复用既有 source-run ID/idempotency builders
  与状态转换规则，校验 scope/priority/trigger/reference、成功终结、UTC与 Job 起止，
  并检查有界不可变事件链的起始、连续合法状态/时间和最终完成，不能只信状态枚举。
- 在原 canonical `proof_json` 中追加 `successor_execution`，完整绑定 Job/provider/
  全 attempts/SourceRun/事件全部字段；state 精确 key 与 hash reader同步。准入和
  历史 Backup/Restore 共用上述完整重算，后来合法-looking 字段改动也不能漂移
  已有不可变历史证明。没有扩表或改 proof authority，归档仍非 Transcript/Evidence。
- 已拒绝的未发布旧 candidate38 proof缺该字段，继续 fail-closed，不静默 upgrade
  或改写不可变行；旧私有包不宣称支持。真正已支持34–37包不变，新鲜38 proof正常
  保留与恢复；future current Summary pointer变更正控保留。

新增26项，旧52项及其所有断言完整保留：18 successor实时负控（含五项审查复现、
naive/future/小数count/编号/lease/owner/usage/dispatch/source-run顺序），混合未解决
批次不变，六项归档后历史与重新计算 ZIP DB hash 的 Restore tamper拒绝（含仍
合法 max_attempts改变检测），以及未发布 incomplete proof拒绝且无不可变升级。
每项确认表/物理文件保持原状、无新 GET；正常真实controller fixture、幂等/恢复/
future pointer/old34–37正控均继续执行。

检查：

- 新18负控在旧实现 **14 FAIL / 4 PASS**，`successor-tdd-red.log`，作为红证据。
  其中两个 owner fixture原尝试 SUCCEEDED+owner，被现有 SQLite CHECK拒绝，不是
  业务负控通过；首 green **18 PASS / 2 fixture FAIL**，`successor-first-green.log`。
  停止重复并读取 CHECK后改为合法 RUNNING/PENDING+owner/lease/nullfinished，保护
  SQL原样保留，未降低 Schema或负控预期。
- 首77项完整 archive专项 **77 PASS / 119.34s**，`successor-focused-final.log`；包含
  原52及当时新增25，最后 incomplete proof专项另与状态/schema/saved回归运行。
- 原 Reviewer `/tmp/readiness-archive38-independent-probe.py` 未改，重新执行输出另存
  `successor-external-probe-after.log`：五项均 **archived=false / ready=false /
  tables_changed=false / extra_fetch=0**。这是原探针结果对照，不自填独立 APPROVE。
- 额外 incomplete proof + state store/lineage/doctor/saved整文件回归运行日志
  `successor-schema-regression.log`：**114 PASS / 37.46s**。78 archive案例的77项
  首轮专项与最后一项本轮执行均通过，没有称其为单轮完整78输出。
- 最终 py_compile PASS；strict mypy src **102 files PASS** / Ruff src/tests/scripts
  PASS / diff check PASS，`successor-commit-mypy.log` / `successor-commit-ruff.log`。
  初新增 local import I001 已仅整理新增 import，不改工具链或既有代码格式。
- **本返修没有运行完整后端/前端/GUI验收**。原完整4310 PASS / 1 schema assertion
  FAIL / 1既有skip /2warnings保留；后续48专项 PASS不冒充完整通过。主控明确不重复
  旧基线19分钟套件，最终接受整合后仍需最新完整后端、前端、TS/build及真实GUI。

作者提交本有界返修后 STOP，建议 IN_REVIEW。待另一角色独立复审，无自审、采用或
生产资格声明；当前 main/正式 owner未操作。主控实际 rollback→real新child→idle
archive→GUI Backup/Restore全表全DATA流程仍是接受门禁，不由 fixture替代。

## 独立复审 2 — REJECT（2026-10-14）

Reviewer `/root/intel_bounded_review`；固定候选
`4f80c2b76ca6ebd7ade0b1fe6ebf9bf4bd03b0eb`，原完整基线
`a2c668bbe32d1acc4bcf83176a331eb3e850e09b`，返修比较点为前次审查
`658cd53c946054d1e184a7743929279cdcffc3bf`。作者 STOP/clean 后复审，只有本交接
追加；没有业务修复、模型/provider/云调用或正式 owner/Schema/main 操作。
沿用仓库要求的单 Reviewer，按完整规格、批准和已读图谱/fallback文件审查两种 diff。

### 返修已证明的正确部分

原五个独立 successor 探针原脚本不改重新执行，全部现在
`archived=false / ready=false / tables_changed=false / extra_fetch=0`。
新 successor Job/provider/all attempts/SourceRun/event 快照、完整时序、连续计数和终结
检查有效；同一个 CHECK 合法但状态链不连续的追加事件，在 successor 正确拒绝。
正常归档、原52项、新26项、future current pointer、old34–37/new38恢复、混批/锁/
竞态/回滚/不授 authority 正控及已写负控都通过。但旧失败 child 仍没有对应完整证明。

### P1-1：原失败 child 的完整执行与历史证明仍缺失

位置 `transcripts.py:1224–1240`，以及 `1384–1390` 的 proof payload；历史复验为
`state.py:4527–4542`。原 Job 只验证部分身份、attempt_count、状态与部分时间，未严格
解析 max_attempts、最终 attempt 与 Job 的终结一致性、最终 lease/完整时序、原
SourceRun UTC/身份/事件链；payload 保存 original_ledger 和 attempts，却不绑定原
Job/SourceRun/其事件的完整不可变快照。当前对 successor 的修复不能证明原请求安全。

独立使用同一正常 API/worker fixture：plain import → 精确 completion 回滚 → 另一个
明确 check 成功，随后在 fresh TemporaryDirectory 私有数据库只损坏原失败 child。
不是把未知执行伪装成模型结果，没有网络或真实模型。四项均实测为
`archived=true / ready=true / tables_changed=true / files_changed=false / extra_fetch=0`：

| 原失败 child 单独变化 | 原本应拒绝的原因 |
|---|---|
| jobs.max_attempts=1.5 | 非整数计数没有正规解析 |
| 最后 job_attempts.outcome=RETRY_PENDING | 最终 attempt 没有证明 FAILED_FINAL，与 Job 不符 |
| job_attempts.lease_until=started_at | 完结在已到期 lease 之后，无法证明正规 owned 完结 |
| source_runs.updated_at=无时区 ISO 字符串 | 原 SourceRun 时间未正规 UTC 验证 |

租约项已核对实际语义：`renew_job` 同时更新 active attempt 的 lease_until；`fail_job`
调用 `_owned_running_job` 要求 `lease_until > now`。不能把结束晚于最终 attempt lease
当普通合法完结而放宽 proof。原 SourceRun 事件 UPDATE 正确被既有 immutable trigger
拒绝，保留该 SQL 失败，不称业务安全失败；改为只追加一条 enum/FK/CHECK 合法但
prior_state 不连续的事件，原 child 仍错误归档/ready=true，successor 对照正确拒绝。

历史反证更直接：先正常归档和创建包，再把原 Job.max_attempts 合法改为4，或把原
SourceRun.updated_at 改为 created_at，live readiness 均仍 true。保持源 ZIP 原
ZipInfo/regular-file属性，checkpoint 私有变更数据库、重算 database manifest hash/
size 后，**这两种实际变更包都可 stage_restore**。没有 confirm/apply；live 表/文件
在 stage 操作前后不变，额外获取0。同法对 successor.max_attempts=4 的对照包则明确
拒绝 `Neutral subtitle retention proof failed validation.`，live readiness=false。
所以不是 ZIP 包装/哈希校验失效，而是 original Job/SourceRun 不在已封存 proof 中。

要求原作者在现有已批准范围内补足原失败 Job/全部 attempts/provider/SourceRun/事件
的类型、terminal、UTC、计数、租约、身份和完整历史 snapshot 验证，准入与恢复重算
共用同一边界；缺旧 proof 保持关闭，不猜测或静默升级。整批在全部 proof 通过前不变，
正常后继/current pointer future refresh 仍合法。没有新增迁移字段或扩大 provider/
资格权限的需求；Reviewer 不代作者修复。

### P2-1：新 Restore tamper 测试提前因 ZIP 属性拒绝，未测到 proof 边界

`test_retained_subtitle_derivations.py:901–942` 的6个新历史 Restore负控，用
`target.writestr(name, body)` 重包，丢失原 regular-file ZipInfo。独立复核其提前拒绝
原因是 `Backup archive contains a symbolic or special file.`，不是历史 proof。
还需显式 checkpoint 被篡改的私有 SQLite，再读取单文件 bytes，避免 WAL 修改没有
进入被测试包。应保留原 ZipInfo、确认序列化DB内实际变更并断言 proof-specific拒绝，
保持所有原断言。独立修正探针包装后才得到上面的 original接受/successor拒绝对照。
原始错误包装输出保留，不冒充有效 Restore 安全证明。

### 独立命令与证据

- 原5项：`PYTHONPATH=src:tests:. .venv/bin/python /tmp/readiness-archive38-independent-probe.py`；
  输出 `/tmp/readiness-archive38-independent-probe-rereview.txt`，5项正确关闭。
- 原 child 4项：同前缀运行 `/tmp/readiness-archive38-rereview-old-proof.py`；输出
  `/tmp/readiness-archive38-rereview-old-proof.txt`。随后直接事件 UPDATE 被 immutable
  trigger拒绝退出1，这项不列为业务反例；正规追加事件另在下一脚本执行。
- 原/后继事件与原历史：同前缀运行 `/tmp/readiness-archive38-rereview-history.py`；
  最终有效输出 `/tmp/readiness-archive38-rereview-history-checkpoint.txt`。
- 后继历史正确对照：同前缀运行 `/tmp/readiness-archive38-rereview-successor-zipinfo.py`；
  有效输出 `/tmp/readiness-archive38-rereview-successor-checkpoint.txt`。
  两个最终脚本均保留原 ZipInfo 并 checkpoint；最早无属性输出/history-final与未
  checkpoint输出/history-zipinfo保留但不作为有效恢复结论。
- `PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/integration/test_retained_subtitle_derivations.py tests/integration/test_state_store.py tests/integration/test_task016c_phase_h2c_lineage_schema.py tests/integration/test_task025a_saved_intelligence.py`
  → **191 PASS /154.09s**，`/tmp/readiness-archive38-rereview-tests.txt`。
- `PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/unit/test_backup_restore.py`
  → **55 PASS /18.01s**，`/tmp/readiness-archive38-rereview-backup-unit.txt`；1 warning是
  既有 duplicate ZIP path负控。
- 5业务 Python py_compile PASS；Ruff src/tests/scripts PASS；strict mypy src
  **102 files PASS**；diff check PASS，分别有 `/tmp/readiness-archive38-rereview-{ruff,mypy}.txt`。
- 完整38文件与返修4文件 diff 已复核：旧tests只更新当前schema/精确名称与追加表/index/
  columns，历史34–37/回滚断言保留，无删/skip/忽略新增。23字段/immutable表不变，
  doctor只当前38。root在核验时bb2dfc3包含原基线，后续修改集中前端/研究/docs，
  未改本切片5个业务文件；这只是兼容拓扑信息，REJECT不能据此整合。

不重复19分钟旧候选完整后端；作者旧全量4310 PASS/1 FAIL/1既有SKIP以及suffix修正
48通过仍按原事实保留。最新整合后的全量与真实macOS GUI是主控后续门禁，不能由
本次246项通过替代。另只读核对真实GUI提出的时间问题：caption服务成功提交复用
fetch入口now、capture另取实时now，普通 import也有入口时间复用；真实长IO下 lease/
terminal clock需另精确核验，不能放宽历史证明或倒填已有时间。未作该问题实测PASS。

**Verdict REJECT；P0=0，P1=1（original执行/历史证明缺口），P2=1（Restore负控包）。**
不整合、不采用、不授资格；退回原实现者。审查提交后 STOP，等待明确新任务。
