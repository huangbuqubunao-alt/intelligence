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
