# TASK-READINESS-LONG-MODEL-PROJECTION 独立审查

- Role：Reviewer `subtitle_recovery_preflight_oct19`，非产品作者；2026-10-19。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-long-projection-review`；branch `codex/task-readiness-long-projection-review`。
- Base：`fe4cfba56bb981c917c218747f54f1aeffd4ed8e`；candidate：`4c455826e0c8063952bf5b5bb3b6018084a95a96`。作者 clean STOP；review 起点 clean，无本 review 遗留测试进程。
- 依 root `agent-prompts/TASK-READINESS-LONG-PROJECTION-REVIEW.md`、最新任务与仓库规范独立审查全部三新增文件，先测试再逐行产品源码；使用 code-review-and-quality 五轴及 git-workflow-and-versioning 提交纪律。图检索没有新模块，直接读取指定 fixed candidate；不改图索引。
- **Verdict：APPROVE，仅未注册纯 projection 工程切片。Actionable P0/P1/P2/P3：无。** 本报告不是生产接线、模型执行/资格、容量或用户完整Goal验收。

## 独立核对

1. 与 accepted `build_local_distillation_request` 实际源码及纯函数构造核对：模型 context 恰保留九字段 `video_id/video_title/source_display_name/evidence/personalization/focus/ignore/style/output_language`；只有 Evidence 用冻结 alias、原范围、同 Evidence 内相邻逐字符相同 cue 的 RLE 投影，未截20条输入。原 YT_TIMED 受信 prompt 完整保留为前缀，固定追加说明及两个新版本绑定消息身份；源文本/metadata/策略字符串没有拼入 system。
2. packet 先由已接受 codec 验证；value 的 video/provider、完整 Evidence 数量/顺序与每一标量字段严格同类型同值匹配。类型先验先于递归复制；错误 bool/None/float/container/cycle 不冒充合法 slot。完整逐cue index/time/hash仍存于packet侧证明，模型可见原Evidence范围没有降低；没有推断单cue时间。
3. opaque source/Summary/policy 非空对象快照只严格检查JSON/UTF8/资源并原字节冻结，未知业务字段按约定保留，Summary不进入模型。raw字节/hash、完整原value、packet、context/messages hash与版本都在side中绑定；合法JSON或hash一致不能证明快照完整/真实。未来factory仍必须验证全部业务来源/关系/期望hash，不能把此结果或旧profile字段当准入。
4. 返回只有冻结 bytes/hash，无 schema/options/transport/registry/qualification。caller原对象或解析后的JSON修改不能改变已存bytes。selected model、semantic/profile/context身份仅side保存，没有借旧short预算或资格执行。positive≤20及NO_NEW全N规则是固定说明，实际新长schema和严格输出仍须未来独立合同/codec验证。
5. `fe4cfba..4c45582` 只有新 module/tests/作者handoff。旧 short/Cloud、codec、state/Backup、profile、schema/registry、资格、依赖/lock/config及前端均零diff。DIRECT标准库及已接受纯值/codec/prompt；无新增外部组件或许可证资产。本review只新增本报告。

## 实际独立检查

Python/工具复用 root 既有 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/`；设置 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`。实际打印模块路径确认来自本review WT，未借其他editable项目。

| 检查 | 结果 |
|---|---|
| `mypy --strict src` | PASS：107 source files，先于测试完成 |
| `ruff check src/youtube_intel/long_grounding_projection.py tests/unit/test_long_grounding_projection.py` | PASS |
| `python -m pytest -q tests/unit/test_long_grounding_projection.py tests/unit/test_long_grounding_codec.py tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_harness.py tests/unit/test_local_grounding_qualification.py tests/integration/test_local_grounding_proof.py` | **291 passed，52.07s** |
| `python .var/projection-independent-review-20261019/adversarial.py` | PASS：以下独立合成对抗/边界 |
| `git diff --check fe4cfba..4c45582`、精确文件scope/旧核心zero-diff检查 | PASS |

独立private QA路径：`/Users/hua/Documents/yia-worktrees/readiness-long-projection-review/.var/projection-independent-review-20261019/adversarial.py`；同目录 `adversarial.log`。不是作者测试自述，也不是实际Sasha或模型样本：

- **实际资源临界值**：完整原value恰8000000 bytes、context恰5000000、messages恰6000000、semantic side恰16000000分别成功，独立多1 byte分别拒绝；测试使其他上限保持可通过，避免错误地由另一guard代为拒绝。未修改产品常量来构造通过。
- 三种opaque快照各恰1000000 bytes原字节保留，多1 byte拒绝；depth16成功/17拒绝；escaped同名key、-Infinity、lone surrogate、UTF8 BOM严格拒绝。
- 所有Evidence字段逐项注入None/bool/float/foreign container/循环对象，均在复制前ValueError拒绝；没有RecursionError或静默改值。
- 合成2406 cue/114 Evidence逐条精确展开，repeat为exact正整数；另80个固定种子Unicode/组合字符/空白/换行/NUL/注入文本与随机分段完整往返。side原value、原packet、codec input hash逐项相等；完整九字段、消息/侧hash绑定、返回bytes不可变均实测通过。

本review无测试失败；没有修改产品、作者测试或既有断言。未使用真实源/SQLite/holdout/thinking，0 network/tokenizer/model/load/generation。Jev因本任务明确0网络/模型限制未调用，未据此降低审查深度。

## 限度与STOP

未跑全仓suite/frontend build：本次是未接入产品的纯新增模块，已按指定运行291相关回归及全src静态检查。真实源完整render/tokenizer/slot/host资源、长schema/profile/inputproof/receipt/反向reader闭包、Backup Restore、真实模型语义资格和最终全仓验收仍待root安排后续串行工作。主控真实QA不计为本review自己的证据。无当前阻塞；本报告提交后clean STOP，不合main、不改任务状态或shared core。
