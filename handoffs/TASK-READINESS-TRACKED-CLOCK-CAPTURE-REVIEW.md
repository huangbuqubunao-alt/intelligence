# TRACKED-CLOCK-CAPTURE-RECOVERY 独立复审

2026-10-19–20；Reviewer `subtitle_recovery_preflight_oct19`，非作者。**Verdict: APPROVE（本固定范围独立工程审查）；新增P0/P1/P2/P3发现0。** root完整backend已通过，真GUI后继仍待；本结论不代表正式采用或完整Goal完成。

## 范围与纪律

- Base `bc306d16289f7cf8938851f05c9b35b9cc4f9781` → candidate `c036847484cc437a20d04e300d960fd4c2047119`；test维护 `f4e3b7f`、产品/新test `2d4a338`、末docs `c036847`。独立WT `/Users/hua/Documents/yia-worktrees/readiness-tracked-clock-capture-review`，branch `codex/review-readiness-tracked-clock-capture`；起点clean、作者clean STOP，原166工作不动。
- 已读root精确包/最新task、当前8KB PROJECT_STATUS、真实GUI失败与4.683ms clock JSON、作者handoff/合同/evidence及完整61文件diff。使用 code-review-and-quality、git-workflow-and-versioning；图未覆盖新helper/当前源码，fallback固定SHA源。DIRECT既有stdlib/SQLite/managed files/父链/Backup/offline fixtures；无新增外部实现/依赖。Jev因0网络/模型约束不调用。
- 产品仅五个tracked文件（含新helper），维护24旧tests及1新test；Schema/state.register/旧迁移/依赖/配置/frontend/资格零diff。未删除/skip/弱化断言或CI。review只新增本报告及ignored私有证据；无真实HTTP、模型/tokenizer/ASR/Cloud、owner/凭据、holdout/thinking或原frozen写入。
- 所有运行以既有root venv，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:.`；打印确认新helper来自本reviewWT。未重复root完整backend或作者566/478大组。

## 核验结论

**单事务真实时间。** `tracked_retry_worker.py:194–207,326–334,410–453`以一次真实claimed_at派生claim/reserve/takeover及五分钟lease；后续检查仍取实时值，旧`started>updated`/未来updated/available不能被接管修好，claim后倒退在adapter方法前fence。`state.register_subtitle_source_capture`严格原谓词未变，无clamp/历史修补。

独立不均匀1µs/5ms/7µs/9ms时钟实测，在首preflight读到claim事件、execution.updated、provider started/updated/available、真实attempt.started逐字同一时刻，lease也全同；reserve只调用一次，now==available，lease==now+5min；最终真实fixture canonical/timed/Summary/Evidence成功。另从固定base提取**仅旧run方法**，在私有进程内临时替换/恢复，当前其余依赖和原strict register不改：直接观察旧provider `started=.025000 > updated=.005000`，结果FAILED/LOCAL_FINALIZATION_FAILED/local0、VERIFIED capture、无job artifacts。此为明确的旧方法因果对照，不是完整旧候选或真GUI positive。原真实4.683ms与作者3项旧红证据保留。

**严格已知capture后继。** `tracked_retry_capture_failure.py:45–165`及store迭代分支要求FAILED/LOCAL_FINALIZATION_FAILED/local0，job/provider真实attempt各1、精确错误/message/终结时刻、clear owner/lease、FAILED_KNOWN、末marker/终事件/epoch和完整typed历史。用`is not None`拒response/input_tokens/output_tokens/cost，独立验证三种用量值**0**及合法capture artifact作为非空response也拒，不存在truthy放行。execution类别先选严格分支，wrong provider error不能退generic；generic LOCAL_RESOURCE名单未扩。

每个1/2 CAPTURE均要VERIFIED、原bytes/size/hash/producer/path/proof全重算、同epoch、精确ABSENT buffer且实际不存在；两份必须合法plain/native同源语言pair。可选capture index全字段匹配且非authority，任何其他artifact/timed/Summary/Evidence/partial/多余行等仍closed。fresh手工command、父EX锁、同command幂等/只消费一次保持；原父终态/捕获/历史不变。旧独立MIXED unindexed DATA不因此被删、跳过或宣称全ready。

**每层父链与闭包。** store仍迭代，无reader回调递归。独立AST核对四个调用层全部生产`read/_read/verify_old_failure`调用显式传data_root，service/status/actions/history、worker、reader/Backup覆盖。独立1/2 capture各建立两个连续已知capture失败祖先，再grandchild成功；缺root/相对root/错绝对root拒绝。最深祖先usage0后，当前/历史command/status/action/worker/verify_request/verify_all和Backup都拒绝，前后SQL不变。有效原ZipInfo重包stage/cancel正控通过；损坏副本原sqlite_master全部SQL/trigger不变、FK/integrity正常，关闭连接后immutable main检查确认usage0实际在ZIP内，再重hash manifest，确实命中ownership语义错误，非special-file/哈希提前拒绝。专项60还实际覆盖1/2捕获restart/全iterdump/all DATA restore、父锁、39条件与native cap2反控。

**测试维护。** 私有运行作者AST审计仅改证据输入/输出路径；实际84 AST变化/24文件，输出逐项等于入库artifact。另独立核对维护路径精确覆盖除新focused文件外的全部test diff，每文件assert节点数前后相等。逐条diff只current40/name/checksum、040追加、015..040（缺029）slice25、future41及显式历史039注入选择；历史38 rollback和tracked旧39初始化/rollback断言保留，不把039注入错指040。实际代表测试含完整历史顺序、future41拒绝、doctor40、旧039失败仍38、旧040失败仍39及current40/saved/schema slice，均通过。

## 原真实冻结父：只读验证

原root `tracked-real-failure-frozen-20261019` 先确认WAL=0，连接`mode=ro&immutable=1`以避免SHM读标记写入，`PRAGMA query_only=ON`后BEGIN。直接对原ed60ddcd父调用`verify_old_failure`和明确原DATA root通过；77表COUNT与原receipt一致、integrity/FK正常、19physical DATA。全部**23个原物理文件**（DB/WAL/SHM/receipt/19DATA）前后大小/SHA逐一相等。没有admit、运行worker或HTTP，亦未读取无关模型正文。此是原真实父证明，不是新GUI成功；本次没有重新宣称全部77表内容重hash。

## 实际检查与证据

| 检查 | 实际结果 |
|---|---|
| final固定focused文件 | **60 PASS /63.77s**，exit0 |
| 新独立非均匀clock/usage0三类/1–2 capture双祖先+ZIP闭包 | **6 PASS /11.21s** |
| 固定base旧run内存因果对照 | **1 PASS /1.46s**（断言原坏时间与诚实失败，非新实现正控） |
| 非NULL response独立反控 | **1 PASS /1.62s** |
| 迁移/history/future41/原typed counter两负控 | **9 PASS /5.42s** |
| strict src | PASS，114 source files |
| Ruff src/新test及24维护tests；diffcheck | PASS |
| 20份gzip压缩/解压原字节hash、所有loaded source/test hash | PASS |
| 独立AST84/24及同artifact/精确scope/断言数/root传递审计 | PASS |

私有绝对目录 `/Users/hua/Documents/yia-worktrees/readiness-tracked-clock-capture-review/.var/clock-capture-review/`，含所有脚本、实际log、frozen-parent-proof.json和`evidence-sha256.json`。首次60命令重定向与私有目录创建并行，shell未能创建log、pytest未启动；目录存在后原命令只实际启动一次并通过，launch-note保留，不当产品失败或一次受测结果。其余本轮测试无FAIL。

作者原3clock红、helper首4FAIL、22FAIL/次1FAIL harness与genericfallback真缺口、562PASS/4slice FAIL均保留并分类，20份原gzip hash已独立核对。四份diagnostic receipt明示事后只读snapshot，原即时trace没有raw日志，未伪称原执行日志；独立旧run因果对照、实际root因果字段与fixed60足以支持本修复，无需伪造旧trace。

root完整backend由其唯一session49511在QA `ffcb3ed0bb47a771e161df5a3ed675ef007a8821`执行；相对2d4a338的src/tests仅已接受pure `long_card_canonical.py`与对应test两个新文件。报告恢复时已只读核验root终态：**5334 PASS /1既有SKIP /2既有warnings /1727.97s，pytest exit0**。result的407文件source-before/source-after清单逐项相等、module指向该QA源，完整原log SHA256为 `af9e1890e6bd4a1e62b8678020e7715c8dda60e0e04bb008791519cef9c43083`，与result及根控给定值完全一致。SKIP与重复ZIP/Pydantic construct-bypass警告保留。外证目录 `/Users/hua/Documents/yia-worktrees/readiness-clock-full-qa/.var/clock-full-backend-20261019/`。这是**root的独立全量运行**，本Reviewer未重跑；此前草稿的RUNNING记录现按实际终态更新。full与本review已绿，最终ACCEPT/根控整合由root执行；真实原working stock GUI新command/字幕/timed/Summary/Evidence/重启仍由root做，不写原frozen。前端零diff，无额外Chrome/API；不授模型资格，不代表mixed/长协议或Goal完成。

**APPROVE，report-only提交后clean STOP。** 不main/push/发布，不改任务状态。
