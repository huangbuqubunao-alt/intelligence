# 已知字幕失败混合结清

- Status: BLOCKED（等待 TRACKED-CONTENT-RETRY40 的共享 state/Backup 写入结束及验收；此时仅完成只读诊断）
- Owner: root 分配独立 Implementer，随后独立 Reviewer；root 不写产品代码。
- Authorization: CONTINUING_AUTHORIZATION_2026_10_15.md 所记用户持续默认批准；本任务是当前真实链路 P1 的必要补修，无逐文件新审批。
- Reuse: DIRECT 现有两类严格证明、SQLite BEGIN IMMEDIATE、protected operation gate、restore/stage 锁及完整 DATA 读验。无依赖/Schema/正式配置调整。

## 真实现场及完成标准

root@5c8c52e，隔离全量37旧库正常迁移39。公开真实字幕+一次获批窄事务故障：caption-repair-34322e… FAILED_FINAL，当前 v2 请求 c03e58f4… 精确 LOCAL_RESOURCE “subtitle files were saved but stage persistence failed”，真实2 raw captures+1 derived 文件，回滚未新增 authority/Evidence。普通新 Check 命令后继 source-run:81ef78e… COMPLETED，真实 timed/Summary/Evidence 成功；另一旧 Iwgl PENDING 经真实 Chrome Content“重试”成功。原历史及全部原 DATA 保留，0新模型执行。

此时 active jobs=[]、dispatch=[]，但旧 v1/429 两条32ee6ce9…/65f7dbbc…加新 v2/LOCAL_RESOURCE一条仍 unresolved；retained=0。真实 Settings 创建备份禁用。`SCHEMA38_REAL_MIXED_FAILURE_2026_10_18.json`、截图及 root 私有完整74表/19DATA快照为证。独立只读 reviewer 确认：state.py4424–4471 retire要求全部unresolved为v1/429；4530–4531 archive全部送proof，transcripts.py1165–1178却要求v2/LOCAL_RESOURCE。换调用顺序无效。不得拿纯类正向或retained0恢复当已解决。

完成：在现有严格安全前提下处理两类“可证明已知失败”的并集，无任何未知/PENDING/活跃执行放行；全部证明通过后原子结清、保留各自历史与归档；真实此现场 readiness→GUI create/download/native picker/strict preview→RESTORE→正常重启→全部表行和全部DATA路径/大小/hash精确相同。

## 最小安全设计约束（实施前复核）

同一 protected window/SQLite transaction 内对全部 unresolved 严格分类，逐条调用原两类完整验证，任一未知/不合格则整批不变；避免分别过滤后绕过异类、拆事务部分结清、放宽 quiescence、删除/改写历史、伪造 authority。旧 v1终止仍保留原错误+既有POLICY_RETIRED注释；v2终止仅原有status/finished/updated CAS+不可变归档，原错误/计数不改。未知文件/混合坏证明/冲突/restore并发整批回滚。现有旧纯类入口和 worker idle 行为保持兼容。具体可复用内部 verifier/共用单一协调器，由作者提交精确方法和受影响范围；不得为复用做无关重构。

## 验收

两类各纯正向、混合正向、重复/重启、逐类不合格+未知第三项、所有 lease/response/dispatch/usage/cost/Cloud/PENDING/RUNNING负控、transaction中途失败全不变、归档不授authority、全部DATA无遗漏、旧34–39及新40兼容、现 tracked40独立所有权和Backup判定不回归。保留原测试和失败证据；affected tests/static后作者clean STOP→独立Review APPROVE→root整合复验。最终整项目完整检查仍单独必需。正式数据绝不参与。
