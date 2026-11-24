# TASK-READINESS-TRACKED-CONTENT-RETRY 最终累计独立审查

2026-10-19；Reviewer `subtitle_recovery_preflight_oct19`，非本产品作者。**Verdict: REJECT。** 原foundation三个发现已修复；以下新发现仍须原作者返修，不能整合/采用此候选。

## 精确范围与纪律

- Base `c312ee4a544556616c9b102d57ec44cf56a21b90` → candidate `b14788c6575ffb9796d62c72be8a6e4bb9ca255a`；独立WT `/Users/developer/Documents/yia-worktrees/readiness-tracked-final-review`，branch `codex/review-readiness-tracked-final`。起点clean，作者clean STOP。
- 读取root最终任务/精确迁移提案/EXECUTION_CONTRACT/本仓库规范/作者handoff及全部累计产品与测试diff。累计包含已接受picker历史，未把它当作新tracked实现需重复整合。
- 使用 code-review-and-quality、git-workflow-and-versioning。图优先查询未覆盖新tracked符号，fallback固定candidate源码，未改图/工具链。DIRECT既有SQLite/fcntl/managed路径/native字幕/timed/Evidence/extractive Summary/Backup边界，无新依赖或第三方实现。
- 本review只新增本报告。所有运行使用隔离fixture/temp SQLite/DATA、既有root venv，并设置 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:.`；打印确认模块来自本review WT。没有真实源、owner/config/凭据、holdout、thinking、外部网络、tokenizer、模型或付费IO。

## F1 — P2：本地尝试计数未绑定真实事件，可损失合法额度且坏计数备份可恢复

主位置：`src/youtube_intel/tracked_retry_store.py:407–410`；配套 `tracked_retry_reader.py:92–180` 和 `migrations/040_add_tracked_content_retry.sql:78–90`。

reader重放了state/revision/epoch/action，却不从合法本地尝试阶段/事件派生并核对 `local_attempt_count`。SQL只限定单次计数增加0或1，没有要求计数增加必须有对应本地attempt事件；因此一个伪heartbeat可保持原events_json并消耗额度。不能用更强的revision==event revision条件代替修复：合法heartbeat本来允许revision单调增加而不追加状态事件。

三个独立反证（没有修改产品或正式测试）：

1. 通过真实专属worker claim，在 `_preflight` 前 `KeyboardInterrupt`，因此provider仍NOT_DISPATCHED、target RUNNING、local count0。仅执行现有trigger允许的 `UPDATE ... SET revision=revision+1,local_attempt_count=1`；events_json逐字不变、所有trigger保留。相同command的 `service.request()` 完整历史/文件reader仍返回成功，预期 `RetryIntegrity`，实际 **DID NOT RAISE RetryIntegrity**。
2. 从同一错误计数继续普通worker与明确本地RESUME，注入可恢复Summary故障。**仅2次实际本地失败后已持久count3、can_resume=false、只剩Close**；应有3次真实本地额度。反证断言报 `lost actual local attempt: only 2 actual local failures but persisted count is 3`。这不是假造prep attempt或再次HTTP来制造现象。
3. 成功fixture有1次真实local attempt。在新的隔离候选DB按原SQLite dump重构，仅将该counter从1改0；最终所有trigger name/SQL逐条完全相同，integrity/FK正常，未DROP原trigger。保留原ZIP ZipInfo/S_IFREG并重算DB大小/hash与manifest：counter1的同构重包正控stage成功，**counter0坏包也stage成功**，预期BackupRestoreError却 **DID NOT RAISE**。因此终态/Restore亦缺counter一致性核验，不只是live API问题。

请在统一typed verifier重放合法local尝试开始/结果及特殊容量分支，核对全部阶段的counter，普通heartbeat不得改变它。零调用父链及HISTORY_LIMIT_CLOSED已有部分count0检查，不等于普通ACQUIRING/FINALIZING/ATTENTION/终态已闭合；本次直接证实ACQUIRING与SUCCEEDED缺口。返修须保留完整合法heartbeat/128预算/3次真正local配额/纯本地SUC恢复，不伪造attempt、不扩大上限。

证据：本WT `.var/tracked-final-review/test_new_invariants.py`、`new-invariants-first.log`；`test_counter_closure.py`、`counter-closure-red.log`、`counter-restore-valid-zip.log`。原负控与真实额度负控各1FAIL；合法ZIP重包集合1PASS正控/1FAIL负控，4.95s，实际pytest exit1。

## F2 — P2：两组rehashed Restore负控因ZIP格式先拒绝，未证明语义闭包

位置：`tests/integration/test_tracked_content_retry.py:723–727`、`:1013–1017`。

两组重包均用 `target.writestr(name,body)`，未保留原ZipInfo。当前Python默认生成的权限没有S_IFREG；`backup_restore.py:777–779` 首先报 `Backup archive contains a symbolic or special file.`，在DB/协议authority核验之前就结束。因此12种关联破坏及prepared-parent四种损坏的绿测试，不能单独作为rehashed语义损坏已被拒绝的证据。

本review第一版私有重包也踩到同问题，明确保留 `test_counter_closure.first.py.txt`、`test_counter_closure.diagnostic.py.txt`、`counter-restore-diagnostic.log`，**该首版PASS不计作counter保护**；只修private ZIP metadata并加入不变counter正控后，F1的实际Restore缺口才显现。不是放宽产品ZIP安全检查。

请保留原ZipInfo（新增DATA项设置合法regular metadata）、重算真正变更的manifest，并加合法无损重包必须stage成功的正控。再验证每个损坏触及预期authority拒绝路径；不删除/弱化现有ZIP特殊文件负控。

## F3 — P2：扩展旧恢复检查仍失败于过时latest版本期望

位置：`tests/integration/test_creator_following.py:674`。

独立扩展回归实际 **382 PASS / 1 FAIL，108.43s**。`test_migration34_failure_is_atomic_and_upgrade_preserves_bilibili_authority` 先验证失败回滚到33，随后正常按全部migrations升级，仍期待latest39，而本候选正确返回40。错误行：`assert repo.initialize(now=NOW).version == 39`，实际40。

这是遗漏更新的latest期望，不是产品升级40异常。请只更新当前正常升级期望并保留33回滚、既有历史39等断言；不能把本次未通过检查称为全扩展回归通过。原log `.var/tracked-final-review/extended-regression.log` 保留；review没有改或重复运行该失败。

## 原foundation F1/F2/F3独立复验

原probe逐字复制，SHA256仍为 `1df82ec3274fc218cb75cd1d1da4a98f7d95fc990ffda9e14b10dd4a5b328497`，未做fixture adapter修改：

- `-k 'generic_ambiguous or reader_must or verified_file'`：**7 PASS，4.70s**。generic ambiguous无authority拒绝；未知event/伪action/错epoch/target冲突/consumed旧attempt损坏拒绝；VERIFIED NULL schema组合拒绝。
- `-k 'other_generic or orphan_future or cross_process_same_inode or populated39'`：**11 PASS，6.69s**。其余generic provider隔离、未来prefix、真实两进程稳定inode锁、非空39迁移回滚/旧领域行与DATA保持复验通过。
- 原source与原失败历史没有被修改；两个独立日志为 `previous-seven.log`、`previous-eleven.log`。

## 其余实际独立检查与时点

全部对本fixed最终candidate运行，不能与作者旧覆盖时点相混：

| 命令/范围 | 实际结果 |
|---|---|
| `mypy --strict src` | PASS：111 source files，先处理类型/语法 |
| `ruff check src tests/integration/test_tracked_content_retry.py tests/e2e/tracked_content_retry_fixture_server.py` | PASS |
| `git diff --check c312ee4..b14788c`、源码/check文件hash及gzip完整性 | PASS |
| affected11文件pytest（下列明确路径） | **461 PASS，404.75s**，保留1条原重复ZIP路径负控warning |
| fresh `tests/integration/test_tracked_content_retry.py tests/unit/test_local_api.py` | **125 PASS，119.37s**，含最终historical action与错Content零写增强 |
| 扩展7文件pytest（下列明确路径） | **382 PASS / 1 FAIL，108.43s**，F3 |
| `npm --prefix frontend test -- --run` | **956 PASS**，19.98s，原React act warnings保留 |
| `npm --prefix frontend run build` | PASS：TypeScript+Vite |
| 独立Chrome工程fixture | **24 PASS**，en/zh-CN×1440/320×六状态，真实DOM/HTTP/SQLite/worker；取消→新command→local ATTENTION→RESUME→Summary/Evidence |

461集合：`tests/integration/test_tracked_content_retry.py tests/integration/test_retained_subtitle_derivations.py tests/integration/test_provider_dispatch_crash_recovery.py tests/unit/test_state_transitions.py tests/integration/test_state_store.py tests/integration/test_runtime_composition.py tests/integration/test_youtube_following.py tests/unit/test_backup_restore.py tests/unit/test_local_api.py tests/integration/test_task023a_source_run_persistence.py tests/integration/test_task024_processing_orchestration.py`。

扩展集合：`tests/integration/test_subtitle_provider.py tests/integration/test_verified_timed_transcript.py tests/integration/test_creator_following.py tests/integration/test_background_following.py tests/unit/test_subtitle_policy.py tests/unit/test_subtitle_directory_limits.py tests/integration/test_phase11r_source_run_quiescence.py`。

已逐行核对并在上述集合独立运行known receipt前后中断、unknown不重发、SUC仅本地、1051完整持久父链与中间破坏、真实多次claim中断/3次local配额/128事件预算、两个实际进程过期lease锁、所有文件窗口/终态全table与DATA恢复、34–40七种版本全table/DATA及原历史保持。重hash负控的语义限度见F2，不因pytest绿而忽略。旧034–039 SQL未变，已有历史39断言保留；原测试修改主要是latest40/040登记及新断言，未见删除/减弱原断言或改CI脚本。

Chrome优先技能agent-browser CLI不可用（command not found），未安装或外连；按browser-testing-with-devtools原则使用已装Chrome+已有Playwright脚本fallback。private副本只调整Playwright导入、独立输出路径及禁后台网络launch flags，未改产品/assertion。API6238/Vite6239仅指向本隔离fixture，四个真实document分别载入，24截图/DOM状态断言、无横溢/页面console error-warning/外部页面请求均通过；另人工查看中文320 ATTENTION截图。结果位于本WT `.var/tracked-final-review/browser/`。这不是真实旧tracked source验收。两个自有服务已停止，未触正式5488/5489或其它进程。

## 证据、限度与STOP

所有私有probe/实际日志与hash清单：`/Users/developer/Documents/yia-worktrees/readiness-tracked-final-review/.var/tracked-final-review/evidence-sha256.json`。原7probe SHA已核；作者validation列出全部源码/正常输出hash与三份gzip的compressed及解压原始hash均独立一致。原known-window/historical-action红日志保留且未改成成功；作者461先于最终action增强的时点缺口已由本次fresh461/125覆盖。

未运行全仓最终regression，也未读取/运行真实旧tracked完整副本；后者普通GUI→真正字幕/Summary/Evidence→实际重启→全table/all DATA恢复须root在返修、独立接受和整合后做。无模型资格或长协议结论。Jev因0网络/模型约束未调用，审查未降级。

**退回原作者窄返修F1/F2/F3，随后重新独立审查。** Reviewer只提交本新报告，candidate产品与正式tests零修改，工作区clean STOP；不合main、不发布、不改任务状态。
