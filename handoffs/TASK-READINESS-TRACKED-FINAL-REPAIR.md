# TRACKED F1/F2/F3 最终窄返修交接 — 2026-10-19

## 范围与状态

Implementer `long_lossless_codec_oct19`，按 root 5184fe8 任务包接替已 terminal/撤销写权的原作者；保留原 WT `/Users/hua/Documents/yia-worktrees/readiness-tracked-content-retry`、branch `codex/task-readiness-tracked-content-retry`，base `b14788c6575ffb9796d62c72be8a6e4bb9ca255a`。没有覆盖旧成果，也不是独立 Reviewer。

产品/协议测试提交 `f336338`；F3单行提交 `76e042b`。本合同、证据与交接为其后docs-only提交。状态 **IN_REVIEW，作者clean STOP，非APPROVE/DONE**。

本交接仅 F1/F2/F3。修改两个原协议源码文件、对应 tracked 测试、creator_following 一条 latest 断言及执行合同/本证据。没有 Schema/迁移号、128/3、原错误/文件、Budget/Cloud、依赖/配置/凭据、前端或资格变更。0外部网络、tokenizer、模型权重/context/生成、真实用户库/holdout/thinking。仅隔离离线 fixture；不迁移正式数据、不 main/push。

## F1：从事件唯一重放本地配额

`tracked_retry_store._verify_events()`从0重放所有历史，execution各阶段 count 和 CLOSE_HISTORY_LIMIT receipt count 都须精确相等。无事件 heartbeat 可以增加 revision，不能改变次数；API幂等重放、worker入口、正反向closure与Backup均经同一 typed reader，坏 count 在任何本地工作前拒绝。

新 writer 只生成以下带见证事件（不增加事件槽）：

- `LOCAL_ATTEMPT_STARTED`：FINALIZING→FINALIZING，同 epoch，真实本地工作前持久化；`local_attempt={phase:"START",before:n,after:n+1}`。
- `LOCAL_INLINE_ATTENTION` / `LOCAL_INLINE_COMPLETED`：FINALIZING→ATTENTION/SUCCEEDED，同 epoch，实际本地工作后将结果、count及见证一次提交；phase 为 `INLINE_RESULT`。

见证精确三字段，phase严格字符串、before/after严格整数，拒bool/float、缺失/额外/重复JSON字段、错phase/epoch/action、非连续次数或超过3。inline合法性仅由已经重放的 n 和该结果前事件数 i 判定：`i+4*(3-n)+2>128`；不把当前execution投影当oracle。

旧普通 same-epoch FINALIZING→FINALIZING RECOVERED可独立证明一次start，继续确定重放，不要求补见证。新事件名的缺见证则可区分并拒绝。无充分开始/次数证明的旧040 inline关闭读取且保留原历史/文件，不回填/伪造；旧普通结果在容量分支范围也不能借之前open attempt解释。040仍未正式采用；34–39不变，正常普通040历史正控保留。详见原 `TRACKED_CONTENT_RETRY_EXECUTION_CONTRACT.md` 新增精化。

固定验证包含：QUEUED/ACQUIRING/FINALIZING/ATTENTION/SUCCEEDED/FAILED/CANCELLED/AMBIGUOUS全观察阶段count±1、合法无event heartbeat、history closure receipt重hash count±1、普通旧start正控、新见证缺失/坏类型/多字段/错phase/epoch/重复字段、count=1时117/118/119条inline阈值邻域、阈值下伪inline拒绝、counter=1重建备份正控与0/2负控。原100+真实predispatch/local中断、全部3次真实本地配额及Close仍保留；新增独立计数断言确认为3次实际Summary失败，不用投影证明自己。

## F2：修复负控 harness 并验证真正语义拒绝

完整失败链分别保留，不能相加冒充独立通过数量：

1. 在base复制 Reviewer 两个私有probe到本WT `.var/tracked-final-repair/`，未改探针，得到 **3 FAIL / 1 PASS**：无事件count变更未拒、实际仅2次本地失败却count3、重建counter0 Backup被接受；counter1重包正控通过。原 quota-effect probe在修复后会更早于worker入口抛RetryIntegrity；新的正式heartbeat/worker测试明确断言此时0本地工作，正常配额测试断言3次真实失败，未把原探针改弱。
2. 原12+prepared4负控只用名称写ZIP，丢失S_IFREG，原“通过”由特殊文件拒绝造成。现复用原ZipInfo副本，新增未关联DATA明确S_IFREG；每个损坏前先无修改重包stage/cancel正控，prepared正控还完整restore并比较所有table dump/全部DATA bytes。
3. 保留ZipInfo后出现 **14 FAIL / 6 PASS**，14个DB负控DID NOT RAISE。不是14个产品漏洞：原harness的sqlite连接上下文只commit不close，WAL未写入入包main bytes，实际ZIP仍是有效原库。原始红日志完整保留。
4. 仅修隔离恶意库harness：提交后记录完整预期iterdump，关闭连接，再用新 `immutable=1` 只读连接核对实际main的完整iterdump逐项等于预期，再将这些bytes写入ZIP。正常重建counter测试同时保留全部trigger原SQL、integrity_check及FK正控。不是仅检查hash变化。
5. 最终12+4真正语义负控均有精确错误：future_target为FK authority、missing_file为source Summary authority、prepared provider为unresolved dispatch、extra_file为缺DATA producer，其余为Content retry ownership/file closure。原ZIP特殊文件规则与其负控完全未改。

## F3：只修latest版本期望

`test_migration34_failure_is_atomic_and_upgrade_preserves_bilibili_authority` 的最后完整migrations初始化期望改为40。此前33原库、故意34失败/原值保持、历史39断言均保留。扩展7文件383 PASS。

## 检查、加载时点与证据

证据目录 `docs/validation/end-to-end-user-readiness/tracked-final-repair-checks/`，`validation.json`含当前源码hash、原始日志hash/路径、两次广测加载store的重建hash及0模型/正式数据声明。原始所有中间失败仍在本WT `.var/tracked-final-repair/`；首次counter红与ZipInfo/WAL十四红的原始完整日志另外入库。

- 最终 `mypy --strict src`：111 source files PASS；`ruff check src tests/integration/test_tracked_content_retry.py tests/integration/test_creator_following.py` PASS；diff check PASS。
- 中间累计107 PASS/1 deselected（125.79s），包含当时完整tracked、creator最新期望、独立mutation和重建count0/1探针；集合有重叠，不作总数。
- 最终源码边界补验：16 PASS/92 deselected（17.40s）。包含history容量、三个inline邻域、各阶段count、receipt和重复JSON字段。
- 最终源码语义/heartbeat/重建counter：21 PASS/87 deselected（41.08s）。含全部12+4负控的逐个正控与精确语义错误、prepared完整恢复、counter1正控/counter0和2负控。
- 扩展7文件：383 PASS（103.84s）。字幕provider/timed/creator/background/policy/directory/quiescence。
- 受影响11文件：475 PASS/1 warning（410.76s）；含Schema34–40非空全表/全DATA恢复矩阵。warning是既有duplicate-path负控主动构造重复ZIP项，未隐藏。
- 最后仅加强测试的阶段覆盖集合断言：5 PASS/103 deselected（5.24s），确认实际观察到ACQUIRING与FINALIZING。

两个广测启动后，只再收紧一处store guard：旧无见证COMPLETED/LOCAL_ATTENTION在容量分支范围全部拒绝，而不只检查无open LOCAL_ATTENTION。源码仅这一处后改；worker未变。另追加阈值下伪inline和3个重复JSON测试，最后仅增强阶段覆盖集合断言并补验5项。广测不冒称加载最终store；上述最终16和21项均加载最终源码，覆盖这处guard及其受影响正常容量/旧兼容/closure路径。独立Reviewer须按最终固定SHA再验；前端无diff，未重跑无关956/24/UI检查。

仍待 root：固定diff独立窄复审、最终root全仓检查与真实tracked全DATA隔离副本GUI/重启/恢复。模型/ASR资格保持关闭，不把旧tuple receipt当新代码合格。本作者不自审通过，不自行采用/发布。
