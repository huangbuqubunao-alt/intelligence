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


## 2026-10-19 真实证明兼容性补修（同任务必需范围）

root exact accepted verifier在冻结真实现场只读运行，transcripts.py1215失败：恢复常量2026.7.4与真实adapter原值2026.07.04不同；只有exact (2026.07.04, zh/en)重算匹配原raw26b7…。这不是网络失败，不可把版本字符串normalize后重写历史身份。允许最小的**有限已知冻结原版本字符串**逐项唯一重算与完整raw/capture/后继绑定，任何多义/未知仍关闭，不从当前可变安装值推断历史。现proof-v1历史必须继续可验；无Schema或依赖升级。原版本修正后下游parent identity独立诊断仍失败（preflight定位中），不能把首个检查通过冒称全proof通过。真实输入proof/raw/path/旧parent/后继所有边界需逐项查明历史构造版本，只有可完整确定性证明的旧输入才准入，不容错猜hash、不给未知文件授authority。证据 SCHEMA38_REAL_PROVIDER_VERSION_PROOF_FAIL_2026_10_19.json，原失败保留。


2026-10-19 独立preflight与root独立复跑确认：版本单独补正后，第二FAIL精确为parent策略缺失 `(subtitle-selection-v2-original-tracks, subtitle-format-v1)`；fixed SHA3745bc44c3dd3321ae7a2fa93fcea9061676b056 原常量证实是正式历史，不是推测。私有内存候选只改该exact pair与exact版本两处字符串，完整原verifier和固定后继历史重验PASS/23字段/114Evidence完全相等，DB+WAL+19DATA共21文件大小/SHA前后不变、retained仍0/ledger原样。原两个FAIL保留。产品实现必须有限保留两原版本字符串唯一重算，**不能全局替换**旧值；旧proof兼容及完整混合事务/负控/GUI恢复仍待。root证据 SCHEMA38_READONLY_COMPATIBILITY_DIAGNOSTIC_2026_10_19.json。


2026-10-19 补充必需验证修复（仍等tracked40接受，非新功能/审批）：独立针对ZipInfo陷阱预检确认 test_retained_subtitle_derivations.py535–579七项manifest-neutral负控在570用writestr(name,body)丢S_IFREG，仅通用BackupRestoreError使其先被special-file guard挡；wrong-proof-hash实际未到proof。此为已证实验证缺口，不等于新产品接受漏洞。作者在本任务原测试范围内保留ZipInfo/合法regular metadata、加同构不变重包stage成功正控，重算真实DB/manifest后再证七类语义拒绝，尽量匹配具体拒绝原因，不能放宽特殊ZIP安全规则。LOCAL39和38历史original/successor两组已保留metadata并在独立6例中实际抵达语义拒绝；不需要泛化重写它们。native capture直接create_backup缺失/损坏反控不受重包影响。证据 ZIP_METADATA_TARGETED_PREFLIGHT_2026_10_19.json；原tmp38日志部分缺失如实记录，不当现证据。

## 2026-10-19 真实Backup错误反馈同任务补齐
新tracked GUI已确认原18DATA里两旧unindexed文件导致readiness reasons=[DATABASE_UNAVAILABLE]、message='DATA contains unindexed files; Backup cannot omit stored bytes.'，但App.backupReadiness对未识别reason误说仍有其他工作执行。加入本真实失败链的最小UI反馈修复：只在既有Backup panel用有限明确reason分类与中英提示准确区分未完成工作/文件或数据库完整性不可用/尚未确定；未知reason仍closed中性，不展示未经验证内部路径/原始错误，不把所有错误解释为运行任务。允许App.tsx/uiLanguage.tsx及相应现有/新focused UI测试、DESIGN.md必要一段，不新增功能/接口/设置。多原因时保留所有真实阻塞，不只一项；ready=false不能因取消或归档一项无条件放行。真实修复前截图failed-readiness.png已保存，最终须普通GUI验证实际reason及恢复。此scope等共享核心钟修复接受后同mixed任务串行实施，不重复审批。
