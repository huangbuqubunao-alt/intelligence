# WAITING_MODEL Final P1 验收与采用前记录

本记录对应 `codex/waiting-model-final-fix`。正式采用收据及最终所有 HEAD 位于候选工作树
`.var/waiting-model-final-fix/INTELLIGENCE_THREE_AGENT_FINAL_ADOPTION_REPORT.md`，在发布后生成，
以免用尚未完成的发布冒充成功。本文件保留代码、测试、GUI 和迁移的验收依据。

## 基线、授权与复用

- 正式 main / origin/main 起始：`fad25e6109d02650b25ae777f2f7557dd478309d`。
- 已审核分支 `codex/muse-final-audit`：`9f3b03ead107b769b81bf1c77f76d542a424921c`。
- P1 首次实现：`50995fe06bf77d65b41cd0f224999652baa5a478`；独立审查后最终代码：`d12553d40802722d47c4ffb13407960f6aa62a6d`。
- Owner 明确批准 [精确迁移方案](MIGRATION_PROPOSAL.md)，Schema 36→37 只追加取消表与校验/执行保护 triggers。
- DIRECT：Python 标准库 sqlite3、SQLite 事务及 trigger、既有 invocation ledger/source-run/quiescence/Backup Restore 生命周期。
- ADAPT：沿用 no-new 的不可变终止权威思路，但取消是独立 outcome；不伪造分析完成。
- DIRECT：既有 React 界面组件、语言字典、原生 AppKit Picker、已安装 Playwright、手册 HTML renderer。
- REJECT：直接删除 checkpoint、把 WAITING_MODEL 当成功、inv=0 自动备份豁免、启用不合格模型。
- 无新增/升级依赖、锁文件、凭据、生产配置、模型资格或云授权变更。未重新启动三方完整审核。

## 根因与终止方案

m010 的 checkpoint 终态 trigger 冻结 WAITING_MODEL；resource usage 同样不可变。
取消 source-run 不会终止其独立等待 checkpoint，Backup 因此持续阻塞。
新表 `distillation_waiting_model_cancellations` 保存固定结果
`CANCELLED_BEFORE_MODEL_INVOCATION`，绑定 execution/Content/source/request/model/language/budget/原时间。
原 checkpoint 和 usage 不改写，读取时验证该权威后投影为 CANCELLED。

取消在 BEGIN IMMEDIATE 中验证并落盘，同一请求返回同一结果。必须是本地 ollama，并具备匹配的
WAITING_MODEL/count=0/无结果 checkpoint 及不可变 usage；usage outcome 必须明确为
MODEL_UNAVAILABLE_BEFORE_TRANSPORT，实际模型、token、费用、duration、HTTP 信息均为空。
缺失或未知记录、真实 invocation、云端失败或响应权威、活跃/身份不一致 parent 均拒绝。
取消记录不可改写/删除，checkpoint/child 无法复活或重新挂接执行。

执行启动共享 SQLite 写事务和 claim CAS。发现既有 stale preflight 可能把并发 local claim
从 count=1 写回 0，因此追加 local count 不可减少保护；已知云前置失败保持既有会计规则。
预算、授权、Evidence/provenance/no-new trigger 保持完整。
独立审查发现云前置失败既有记账可降低 invocation_count，故明确把所有云等待排除在本地取消权威之外；
应用、SQL INSERT、恢复读取同样验证 provider，本修复不改变云授权/费用和前置失败处理。

Backup 继续验证全部工作，仅把具有合法取消权威的等待 checkpoint 识别为终止。
MODEL_UNAVAILABLE 的 settled parent 只有全部 child 都满足原终态或有效取消规则才静止。
另一个 PENDING/RUNNING/WAITING_BUDGET/未知任务仍阻塞，取消一项不会全局放行。
恢复也验证表与 trigger 指纹及逐条语义；Schema 34/35/36 备份继续支持，旧库升级不自动取消。

## 验证结果

| 验证 | 结果与证据 |
|---|---|
| 后端完整 | **4008 passed / 1 skipped**, 4009 collected，865.41s；[最终日志](backend-cloud-safe.txt)、[JUnit](backend-cloud-safe.xml) |
| 前端完整 | **292 passed / 19 files**；[日志](frontend-full.txt) |
| TypeScript | PASS；[日志](typecheck.txt) |
| Production build | PASS；[日志](build.txt) |
| Ruff | 最终 PASS；[日志](ruff-final.txt) |
| Strict mypy | 最终 PASS，101 source files；[日志](mypy-cloud-fix.txt) |
| git diff --check | PASS；[日志](diff-check.txt) |
| 迁移/恢复/取消定向 | **55 passed**；[日志](migration-final.txt)、[JUnit](migration-final.xml) |
| 最终取消与云边界 | **192 passed**（55 Backup/取消 + 137 Intelligence/云授权）；[日志](cloud-boundary.txt)、[JUnit](cloud-boundary.xml) |
| 手册实际渲染 | 所有图片成功加载，取消操作存在，旧限制已更新；[证据](manual-verification.json) |

覆盖：零调用取消、幂等、重启和继续执行不调用 transport、备份开放/恢复一致性、
已 claim/已调用/未知预算和响应/实际费用禁止取消、直接 SQL 写入/更新/删除保护、
4 轮并发 claim 与 preflight/cancel XOR、损坏 sidecar/ledger/trigger fail-closed、
其他 checkpoint 与同一 parent 的另一个待办继续阻塞、WAITING_BUDGET/PENDING 保持规则。
完整回归包含现有 RUNNING、云授权/账本/exactly-once、no-new、Evidence/provenance、路由与导入测试。

生成日志为满足 diff --check 仅规范化行尾空白与多余 EOF 空行；原字节保存在候选忽略目录，
[原/规范化 SHA](LOG_FORMAT_NORMALIZATION.json) 保留可核对的来源，未修改测试结果或错误信息。

唯一 skip 是既有 canonical-o200k 外部资产未 provision；未新增 skip、删除测试或弱化断言。
两项 fixture warning 是恶意重复 ZIP member 与故意绕过 enum 构造测试。
前端已有 act warning 保留，测试全部通过。

## 真实 macOS GUI 与数据证明

最终代码 fresh Schema 37：真实 headful Google Chrome / AppKit / 独立 API 5799 和 UI 5798，使用隔离 DB/DATA/Vault。
真实导入 YouTube `aircAruvnKk` 后点击提炼，生产资格门禁仍关闭，获得真实 WAITING_MODEL。
取消成功 → Backup ready → 创建并下载 ZIP → 修改输出语言证明恢复差异 → 检查及确认恢复
→ API restart boundary → APPLIED → Content 显示 CANCELLED，等待列表为空，Backup ready。

[最终 GUI 结果](final-gui/gui-result.json) 无 pageerror、无云确认请求、无凭据访问。
[最终逐表一致性证明](final-gui/gui-consistency-proof.json)
原始快照保存在候选忽略目录 `.var/waiting-model-final-fix/validation-private/final-gui/`，不把 Content 原文提交到仓库。
对比覆盖 **71 张表、6 个 DATA 文件、2 条 Content、15 条 Evidence**：取消仅新增一条 sidecar，
其余所有表和文件完全相同；恢复后完整快照与备份时完全一致。
追加的手册截图再次真实取消一项零调用任务：[结果](final-gui/gui-manual-screenshots.json)。

D2-01：最终 GUI 再次真实原生导入 wait-note.txt，Summary/原文/Evidence 可读，Content 深链接 reload/back/forward 通过。最终完整 driver 通过，realAppKitImport / contentDeepLinkReloadBackForward 均为 true。
[明确分阶段证据](gui-native-proof.json) 来自 [原始 driver 记录](gui-native-result.json)。
原 driver 在已通过本地导入之后尝试提炼本地 Content，既有产品不支持该入口，故后续阶段失败；
未扩大功能，改用真实 YouTube Content 完成提炼与取消验收。
D2-02：原生/import/APFS 实现及既有验收文件逐项哈希相同，
[8 项比对](d2-native-compatibility.json) 支持复用 [2 GiB 既有验收](../dogfood-day2-d2-02/README.md)。

截图：[等待与取消](final-gui/screenshots/03c-waiting-model-panel.png)、[取消反馈](final-gui/screenshots/05c-cancelled-panel.png)、
[备份阻塞](final-gui/screenshots/04-backup-blocked.png)、[备份开放](final-gui/screenshots/06-backup-ready.png)、
[备份创建](final-gui/screenshots/07-backup-created.png)、[恢复确认](final-gui/screenshots/09-restore-confirm.png)、
[恢复后取消](final-gui/screenshots/10c-restored-cancelled-panel.png)、[真实 macOS](final-gui/screenshots/11-macos-restored.png)。
统一中文手册：[Markdown](../muse-final-audit/USER_MANUAL.md)、[图文 HTML](../muse-final-audit/USER_MANUAL.html)。

## 失败记录与修复

保留首次 full [日志](backend-full.txt)：3999 passed/3 failed/1 skipped。3 例均源于
D2 Schema 35 fixture 用 migrations[:-1]，追加 037 后错成 36。已改成精确 <=35；
rollback fixture 精确损坏 036，原 35/36、历史数据/完整性和 immutable assertions 保留。
第二轮全量完全通过。随后独立审查发现已 claim 云任务可能被 stale preflight 写为零调用而取得取消权威；
已将本次取消限制为 ollama，并新增六个有真实持久化授权的纯离线云边界案例，192 项定向全部通过。
最终代码第三轮全量 4008 passed / 1 skipped 与 fresh Schema 37 GUI 全部通过，早期通过没有替代最终结果。
初始定向失败包括缺少 migration registry、schema/table expected list、API fixture ISO offset、
新增测试 digest 缺少 sha256 前缀；逐项按实际契约修正，失败 XML 和最终通过结果均保留。
GUI driver 路径偏一级，以及原生“前往”面板未完成造成 Open 禁用，按实际 AX 控件修正，未改导入实现。

## 独立复审

[受限审查完整记录](BOUNDED_REVIEW.md)：首次发现并阻塞一个云取消 bypass P1，修正后 APPROVE。
Reviewer 独立运行 6 个授权云边界案例，全部通过；本取消变更没有未解决 P0/P1。
既有云前置记账状态不代表零调用证明，云等待继续 fail-closed，不扩大云整改范围。

## 发布与保留策略

全部门禁通过后再次核验 main/origin/main 与候选拓扑，仅 ff-only，一次采用既有审核成果和本修复。
发布前停止仅属于正式 worktree 的 launcher 进程，在线 SQLite backup 与 APFS DATA clone
保存至候选忽略的私有目录；真实数据不用于测试或 reset。
采用后批准的 037 在停止状态执行，逐表验证旧行、DATA/config hash 和旧迁移历史完全保留，
然后 push origin/main、正式 frontend build、served build-provenance 和启动检查。
正式数据快照永不提交；发布不写外部 Vault，不更改凭据/config，不 force push。
不满足条件则保留候选，输出 THREE_AGENT_ADOPTION_BLOCKED。

剩余产品限制：本地 Intelligence 资格仍关闭；预算等待/真实执行/未知执行仍 fail-closed；
既有转写模型与 Bilibili 可用性限制保持。本任务完成后停止，不启动其他开发阶段。
