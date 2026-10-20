# TASK-READINESS-LOCAL-REJECTION-ACCOUNTING

## 元数据与范围

- Role: Implementer; agent `local_rejection_accounting`.
- Base: `a989873773c0f4018cc696930789566925e88c7c`; task/package由root提交于`4614a25`，根目录原件已读，未复制改写。
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-local-rejection-accounting`; branch `codex/task-readiness-local-rejection-accounting`。
- Product/test commit: `ac2ea9d4585f3215b9f2330da4062f6fed95b1f5`；此报告/摘要单独后续提交。
- 日期：2026-10-20。目标只修复真实R13响应拒绝收尾与对应诊断串案；不授模型资格，不调整预算。
- 实际产品范围：`src/youtube_intel/distillation.py`、`scripts/qualify_local_grounding_v1.py`；新增隔离回归文件与本报告/结果摘要。

## 根因与实现

1. 新本地profile验证发现截断等拒绝条件时抛出不带result的KnownLocalDistillationResponseError。服务按REJECTED_OUTPUT/调用1/实际身份None写入；state正确拒绝实际身份缺失，整笔事务回滚，原已claim任务留下PENDING/DISPATCH_CLAIMED/调用1。
2. 响应已明确携带非空实际model时，新旧本地响应共用最小观测投影：保留真实model和完整可靠的SQLite signed64非负整数token对，布尔/负数/缺失/超界或仅一侧可靠均为双侧None；不用选中模型补身份，不编造零用量或费用。拒绝结果保留原LOCAL_RESPONSE_*原因。错模型也保留其真实响应标识，禁止准入。
3. 没有实际身份、JSON不合法、越限或非对象响应：持久化现有AMBIGUOUS/调用1/TRANSPORT_OUTCOME_UNKNOWN。原Schema028 trigger只允许有限4个AMBIGUOUS原因；原LOCAL_RESPONSE_*不能直接放在该usage列。初次尝试精确原因被该trigger拒绝，已报告root；root明确选择复用现有限码与独立诊断，未修改state、Schema或Backup白名单。未知执行始终未知，不能取消、重发或变成成功。既有规则允许完整终态AMBIGUOUS归档备份，该归档不授执行或成功权限。
4. transport独立保留`last_grounding_response_error`，once harness以`local_response_error`写入独占/fsync的result.json。这里只是失败诊断，不产生CaseReceipt或资格。真实generate复用回归发现旧final/completion/rawhash可串到新失败；每次generate开始清空全部5项诊断，再记录本次实际观察。不会读取thinking字段。

## 外部证据与检查

精确结果与日志hash见`docs/validation/end-to-end-user-readiness/LOCAL_REJECTION_ACCOUNTING_IMPLEMENTER_2026_10_20.json`。原r3/r4失败数据库、OpenCode freeze/permit/receipt及模型权重完全未写入；全部新数据库/DATA在pytest隔离临时目录。真实模型/外网/付费云调用均0。

- 新回归覆盖：6144 cap、length/donefalse、错模型、缺失/布尔/负值/不配对计数、未知身份、损坏JSON/UTF8、非对象/越限响应、并发重复调用、重启不复活、不能误取消、原Evidence/DATA无变动、其他PENDING继续阻塞、已知拒绝与未知终态的全SQLite行/全部DATA完整Backup/Restore、超时与claim后readinesslost、真实transport fakeHTTP精确诊断、独占result.json以及复用实例串案。
- 编译、全仓Ruff、strict mypy 117 source files通过；signed64补充前固定源码15文件完整受影响组**506 passed / 423.33s**。该版本source/test SHA明确保存在摘要pre-overflow字段。随后root批准仅补整数上界；最终全部37新增回归与原本地adapter/dispatch增量组另记实际结果，不冒称506项在增量后重跑。
- 四个Cloud transport类与原LocalTextDistillationProfile AST相对base逐字等；profile、qualification、capacity、state、Backup、source_authority和固定资格资源7文件字节等。资源仍`records=[]`、旧预算6144、无Schema/依赖/配置/正式数据变化。
- 无前端源码变化；本切片不重复无关前端测试/构建。最终Goal完整回归和真实模型/GUI仍由root执行，不能把本工程离线测试当资格。

## 失败证据与纠正

所有失败日志保留于ignored `.var/local-rejection-accounting/`，未弱化原测试/断言：

- `red.log`最初漏必填expected_model_digest，属于新fixture错误；修复构造后`red-valid-fixture.log`真实22失败/1通过，主要为报告中的身份收尾崩溃。新用例早期误按对象读取readiness，实际DTO为字典，已校正访问方式；另第二PENDING需不同Content而非违反既有单内容reservation约束，改为普通导入第二TXT，未改产品准入规则。
- `green-first.log`中已知响应通过，未知8项被现有Schema有限原因trigger拒绝；root作上述明确表示决策后，测试按批准契约验证既有AMBIGUOUS归档语义，未修改Schema/安全检查以迁就测试。
- `focused-v2.log`29通过；随后追加未知响应完整恢复和复用3例，最终组覆盖全部33例。
- `affected.log`命令漏项目根PYTHONPATH（仅src），15个既有historical脚本导入失败。经root指示、核验自有PID/cwd后SIGINT，304通过/15导入失败/中断；原15项正确`PYTHONPATH=src:.`实际15通过，未改测试。`affected-correct-environment.log`在root要求补复用诊断修复后核验自有PID/cwd并SIGINT，211通过/无失败/中断。
- `reuse-diagnostic-red.log`3失败均证实旧final串案；同断言`reuse-diagnostic-green.log`3通过。随后最终源码冻结，仅跑一次正确环境完整15文件组，不将中断跑记为完整通过。
- 初始Ruff3项仅此次helper替换后的旧局部变量/新测试未用import，已最小清理，最终全仓通过。
- signed64增量：`signed64-red.log`输入/输出溢出两例真实`OverflowError: Python int too large to convert to SQLite INTEGER`，2失败；双侧最大值、仅输入最大值2个正控通过。最小增加`0 <= counter <= 2**63-1`可靠性条件；超界整对未知，绝不clamp或补零。原model保留、原budget/标准不变。随后最终全部37新增+旧local adapter/dispatch三文件**44 passed / 40.45s**；全仓Ruff/strict117/compile/diff最终通过。

## 复用、风险与结论

DIRECT仓库既有stdlib HTTP/JSON、DistillationTransportResult、SQLite事务/不可变usage、调用claim、AMBIGUOUS有限码、once fsync、Backup/Restore和隔离fixtures；无第三方源码复制/依赖新增/许可证变化。拒绝伪造身份、放宽state与迁移方案。

本修复改变执行code hash，旧模型receipt不会自动适用于新代码；root须另行冻结并真实验收。旧已经留下的失败PENDING/调用1现场不由本任务就地修写。未知响应归档后仍不准重执行或取消。全Goal、本地资格、长内容协议及发布均未声称完成。

Implementer提交后clean STOP，建议IN_REVIEW；独立Reviewer、root验收、整合结果待另记。作者不自签APPROVE/DONE，不合main。
