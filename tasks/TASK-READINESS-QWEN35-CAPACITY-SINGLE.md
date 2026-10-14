# TASK-READINESS-QWEN35-CAPACITY-SINGLE

2026-10-14 READY，精确用户批准已写 QWEN35_CAPACITY_SINGLE_CASE_PROPOSAL.md。Orchestrator/真实执行唯一签许可root，Implementer intel_bounded_review（须先完成当前独立UIReview并STOP），Reviewer caption_resume（须在Schema作者STOP后，仅预输出审查不自审）。新独立worktree readiness-qwen35-capacity-single / codex/task-readiness-qwen35-capacity-single，Base为本卡提交后的最新已验收root候选。不得写旧V2/原资格/Schema树。

目标：研究单变量输出容量，原V2英文length4096/empty final失败不覆盖。只新增research profile `readiness-qwen35-9b-thinking-capacity6144-single-v3`，num_predict6144，其余model/digest/native thinking/runtime/prompt角色/schema/parser/input/corpus/semantic政策全部固定原V2；ctx8192/timeout300不变，seed20261013/T1/top_p.95/top_k20/min_p0/presence1.5/repeat1。唯一可prepare/execute的case real-deepthink-en，每次研究总最多一次，成功失败均STOP，不授权后3例/LOCAL8/生产资格。

仅 scripts/qualify_readiness_qwen35_intelligence.py 研究profile/单例case与许可约束、tests/unit/test_readiness_qwen35_research.py追加或新focusedtests、独立新版profile/freeze/input-hash receipts、此task/handoff。允许新freeze不改旧V1/V2全部冻文件/结果/样例/语义门槛。不改生产src/runtime/local_api/state/intelligence_read/schema/deps/config/资格reader/支付或任何正式数据。不下载/升级，DIRECT既有installedfixed9b+Ollama0.40.1和已接受research harness/parser，REFERENCE原官方模式参数依据。

复用当前已安装精确manifest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90、原7blob6550825550bytes/runtime固定身份/staticprovenance。新版freeze需绑定oldV2profile/freeze/harness/实际requestSHA与原verifiedinput/18DATA集合；prepare-only新DB/执行ID，输入semantic摘要/Evidence/source/消息结构必须原样不截断。导出的 actual请求projection除num_predict外与old真实request.json深度完全相同，并且new profile/hash/version区别只研究执行，不改v5协议。若real prompt/input发生差异先停，不用样例重新抓取造成变化。旧实验执行不重开或reroll。

先语法/strictmypy/Ruff；合同负控：新profile只能指定EN且无合法外部rootpermit不能execute；后3case prepare/execute均在文件/DB/请求动作前拒绝；不能换model/options/prompt/schema/input/语义阈值，旧冻/失败bytes不变；重复许可/重复已有result/未知执行不再调用；timeout/length/6144budget/emptypublicfinal/schema/语义失败正常拒绝/已调用ledger保留。旧73合同全部继续。文件存在不overwrite/不删除/不改CI。普通parser不得修改输出内容，private thinking不读不展示，仅opaquehash封存。

实现者只prepare-only，不推理、不自签许可；sealed input/code/profile/freeze checks和自测完成→handoff精确SHA提交STOP，独立Reviewer审整个diff+输入+原requestdeepequal/固定资源身份，rootaccept/integrate后才fresh resources/无任何本任务其它heavy/用户任务不抢占→外部绑定exact一次permit。请求300秒内，任何timeout/unknown保留不重试；只有公开finalcontent/nativemetadata供现parser和独立原语义审查。容量912+6144=7056<8192不是不截断的充分证明；真实输入计数和projection需核对，不能自行延timeout/ctx。

Parallel now caption Schema38 approved P1fix core，research只 scripts/tests/freeze 不重叠，显式准许两独立writer；唯一Reviewer先UI，研究预输出等caption STOP；没有modelsheavyparallel。Waiting Schema38接受/LOCAL_TEXT工程/后续完整资格（本次无调用权限）/真实全GUI+最终新full回归及另批采用。提交后STOP不宣布生产合格或全部链路完成。
