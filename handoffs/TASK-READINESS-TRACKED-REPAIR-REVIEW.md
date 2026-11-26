# TRACKED F1/F2/F3 固定返修独立复审

2026-10-19；Reviewer `subtitle_recovery_preflight_oct19`，非作者。**Verdict: APPROVE。** 原4950db REJECT的F1/F2/F3已关闭，本次新增P0/P1/P2/P3发现0；限累计tracked工程及本窄返修，不代表真实旧源最终验收或完整Goal完成。

## 范围与证据纪律

- Base `b14788c6575ffb9796d62c72be8a6e4bb9ca255a` → candidate `166ab39207136e5fe572ad730a9cf73a0494b221`。独立WT `/Users/developer/Documents/yia-worktrees/readiness-tracked-repair-review`，branch `codex/review-readiness-tracked-repair`；作者clean STOP，起点clean。
- 已读root复审包、TASK、最新执行合同、原4950db REJECT与原私有反证、新交接/validation及全部16文件diff。产品仅store/worker；F3仅当前正常升级期望39→40一行；前端、Schema/迁移、依赖、配置、资格零diff。未删除/削弱原断言或特殊ZIP安全规则。
- 使用 code-review-and-quality、git-workflow-and-versioning；图查询无新符号，fallback固定candidate源码。DIRECT既有stdlib/SQLite/事件和Backup边界，无外部实现或依赖。Jev因禁止网络/模型未调用，审查未降级。
- 全部运行使用root既有venv，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:.`；实际打印模块路径确认来自本reviewWT。无真实源/用户库/owner/凭据、holdout、thinking、网络、tokenizer、模型或付费IO。仅隔离fixture/临时SQLite/DATA；review只新增本报告。

## 原发现关闭核验

**F1（原P2）：已关闭。** `tracked_retry_store.py:338–457`从0重放本地次数；START及INLINE_RESULT见证精确字段/类型、before→after、phase、状态、epoch/action、3次上限均复验。最终投影和history closure receipt必须等于重放次数。合法无event heartbeat保留revision间隙，不改变次数。worker `:640–650,668–675`在实际开始或单槽结果事务中写见证，没有增加事件槽/尝试上限、伪造provider/preparation/model调用。inline阈值只取历史index与重放次数，不借当前投影。旧同owner FINALIZING RECOVERED可唯一确定+1；旧未充分证明inline拒绝，既有历史不回填/改写。

- 原 `test_new_invariants.py`逐字复跑通过：trigger允许的伪heartbeat加count后，历史command重放现拒绝。独立补验API、worker和verify_all同时拒绝，adapter构造/本地Summary调用均为0。
- 原quota driver逐字跑会在`service.run`入口先抛`RetryIntegrity`，未再走到旧“仅2次真实失败却count3”末端断言；保留其1FAIL，不冒称原driver全绿。新增独立正常路径计数确认为**3次真实Summary失败、3个连续START见证**，纯本地RESUME不再enumerate/read，第三次后可Close且终态幂等。
- 原有效metadata重建Backup counter1正控stage通过、counter0负控拒；追加counter2拒。原counter源码SHA未变，重建保持全部原trigger SQL、FK/integrity；本次fixed正式集合同时覆盖0/1/2精确ownership错误断言。
- 新独立typed矩阵覆盖缺/多字段、null/list/string、phase/before/after bool/float/string/错值、错epoch/state/action与投影±1/类型；旧普通start正控。四种重复raw JSON字段在全sqlite_master SQL/原trigger逐条相等、FK/integrity正常的新隔离DB中被真实read拒绝。
- 独立实际worker117/118/119邻域覆盖START与INLINE_RESULT，最终成功次数2、反改投影拒绝；缺见证/重复事件/错phase/无证明旧COMPLETED拒绝。另有结构合法typed正控的历史变体保留早期open start、随后换owner，删除最终inline见证不能借旧start解释成功（明确为synthetic typed对抗，不冒充真实故障执行）。
- 独立重hash CLOSE_HISTORY_LIMIT input与command/checksum后，counter±1、bool/float/string、缺/多字段仍拒绝，原正确receipt通过。

**F2（原P2）：已关闭。** `test_tracked_content_retry.py:12–41`复制原ZipInfo；新增DATA明确S_IFREG。两组每个恶意包前均有不变重包stage/cancel正控，prepared正控还完整restore比对iterdump与所有DATA bytes。恶意DB commit后关闭，用`immutable=1`新连接逐项比较实际main的完整dump与预期损坏dump再取入包bytes，避免WAL中变更未入包。12项所有权/文件及prepared4项现在分别要求具体FK、Summary、DATA producer、dispatch或ownership错误，不能因special-file/hash错误判绿。原prepared全表/全DATA断言保留。

作者保留的ZipInfo修正后14FAIL/6PASS是WAL未入包harness错误，**不是14个产品漏洞**；compressed原log及解压原字节hash已独立核对。未放宽Backup特殊文件检查、未把无效恶意包当语义通过。Schema38另一组manifest负控的既有metadata验证缺口由root另行记录，不属于本返修闭合或授权扩修。

**F3（原P2）：已关闭。** `tests/integration/test_creator_following.py:674`仅latest正常升级改40；33失败回滚及原数据/历史断言保留。原失败test定向独立**1 PASS/1.09s**。

## 实际独立检查（全部最终固定candidate）

- `mypy --strict src`：PASS，111 source files；Ruff src及两修改test文件PASS；`git diff --check b14788c..166ab392` PASS。
- 原foundation probe逐字SHA `1df82ec3274fc218cb75cd1d1da4a98f7d95fc990ffda9e14b10dd4a5b328497`：原7项 **7 PASS/4.65s**；原其余11项已有b147独立绿证据，未无故重复。
- 原两counter文件逐字SHA分别 `9586573c61edd2dc8b01997e4d58958190a026f5a575df6a24a3579cb2d2ef08` / `d1b02029410cfa560bb2e156687e4d059dc31f6cf2a25a8916089d5bc90e3189`：**3 PASS/1 FAIL/5.60s**；唯一FAIL为上述更早完整性拒绝，未删改原driver。
- 新私有独立对抗首跑 **9 PASS/2 harness FAIL/13.40s**；两项因复用history helper后未还原其故意禁止adapter的factory哨兵而中断，未进入被验边界。保留首版source/log；仅改私有调用还原fixture factory后，三邻域 **3 PASS/4.79s**（与首轮119有重叠，不相加）；后续新增receipt/旧owner对抗 **2 PASS/2.72s**。没有改产品/正式测试。
- 首次把带`pytest_plugins=['conftest']`的原私有probe与正式test混收，collection因conftest重复注册exit2；拆开独立命令后原probe逐字通过，不当作产品FAIL或PASS。
- affected11文件最终fixed集合：**478 PASS /1既有duplicate ZIP path warning /406.97s**，实际pytest exit0。作者早期475集合后新增三项duplicate JSON参数用例；本次最终收集478，未照抄旧数量。含34–40全表/all DATA恢复、1051完整父链/中间损坏、128/3真实中断边界、全部16有效重包语义负控与各自正控、全部阶段counter±1及三次真实local故障。

affected命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. <root-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/test_tracked_content_retry.py tests/integration/test_retained_subtitle_derivations.py tests/integration/test_provider_dispatch_crash_recovery.py tests/unit/test_state_transitions.py tests/integration/test_state_store.py tests/integration/test_runtime_composition.py tests/integration/test_youtube_following.py tests/unit/test_backup_restore.py tests/unit/test_local_api.py tests/integration/test_task023a_source_run_persistence.py tests/integration/test_task024_processing_orchestration.py`。

新私有source/log均在本WT `.var/tracked-repair-review/`；hash清单见同目录`evidence-sha256.json`。作者validation全部当前source/check-in log hash及gzip compressed/解压原hash一致。作者475/383加载最后guard之前的时点限度保留；本次独立affected命令从最终166ab392启动，运行期间product源码未变。

前端零diff，沿用原b147独立956前端/TSbuild/Chrome24证据，本次未重启浏览器/API，也未重跑383。root最终全仓检查、真实旧tracked全DATA副本普通GUI→字幕/Summary/Evidence→真实重启→全表/all DATA恢复仍须接受整合后独立进行；本报告不授模型资格，不代表mixed38、正式发布或完整Goal完成。

**APPROVE 后由root整合并执行最终检查与真实旧tracked验收。** 本review只提交本新handoff；candidate产品与正式tests零修改，提交后clean STOP；不合main、不发布、不更改任务状态。
