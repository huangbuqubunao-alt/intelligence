# TASK-READINESS-LOCAL-INTELLIGENCE-TIMED 交接报告

## 元数据

- Task: TASK-READINESS-LOCAL-INTELLIGENCE-TIMED
- Role: Implementer `/root/source_context`; Reviewer `/root/intel_bounded_review`
- Base: `67d6e9a930fa0289c9d97c4ad3119e493b16ce0e`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-local-intelligence-timed`
- Branch: `codex/task-readiness-local-intelligence-timed`
- Head: 本分支的限定实现提交，以主控报告 SHA 为准。
- Reported: 2026-10-13
- Suggested status: IN_REVIEW；实现者不设置 DONE、不整合 main。

## 目标、批准与范围

用户已明确批准 `docs/validation/end-to-end-user-readiness/LOCAL_INTELLIGENCE_CHAIN_PROPOSAL.md` 的精确隔离范围。本提交仅第一 LOCAL_TIMED 切片：真实本地音视频已有可信时间轴、完整 canonical Evidence 与当前 Summary 时，允许明确手动提炼命令通过来源准入。所有模型、预算、ledger、取消与未知状态门禁保留；不自动运行本地资料库。

本轮固定 9b 原资格首例被主控发现决定性语义失败；剩余三例已停止。本实现没有真实模型、Whisper 或云端调用，没有创建资格收据，没有修改运行时 reader 或启用 LOCAL 生产资格。实际 LOCAL 模型正向及 GUI 验收仍 BLOCKED，不能把本轮夹具 PASS 当成真实资格或完整用户链路完成。

实际改动：`src/youtube_intel/distillation.py`、`local_api.py`、`state.py`、专用 integration test、本任务卡和本交接。没有前端修改、Schema、依赖/锁文件、配置/凭据、正式数据库、模型 profile、runtime composition、字幕 raw/历史清理或长内容分批。

## 实现与复用

DIRECT：既有 `source_authority.verify_source`、绑定 DATA 根、`get_verified_timed_transcript`、`ExtractiveSummaryService.read`、当前 Summary 指针、完整 canonical coverage 与精确 Evidence resolver、SQLite BEGIN IMMEDIATE、原 sealed input/hash、ledger/预算/取消、BackupRestoreService。均为仓库现有代码与 Python 标准库；没有新增第三方组件或许可证变化。

ADAPT：

- LOCAL manual readiness 复核实际 LOCAL / LOCAL_LIBRARY / DISCOVER_ONLY 来源、来源关联、真实 READY 音视频快照、verified timed 与 canonical 绑定、当前可信 Summary 与全部 canonical Evidence（保持既有最多 20 条限制）。关闭或未启用资料库仍可明确手动处理；所有非 MANUAL_CONTENT LOCAL 执行拒绝，即使资料库启用且 filter 为 RELEVANT。
- 新 LOCAL-only context hash 绑定 snapshot/source/canonical/timed/Summary 身份与内容 hash、Summary 语言、全覆盖 Evidence IDs；加入 LOCAL semantic hash，默认 YT 的 wire 和 semantic payload 保持原有字段。持久化 sealed identity 在恢复时正规重建；不新增存储。
- 正向 Intelligence 与 NO_NEW 的成功事务，在 BEGIN IMMEDIATE 内重新读取可信来源与当前 Summary/context，拒绝执行期间变更。不是仅检查记录 EXISTS，也不授予 Evidence/Summary 权威。
- API 读取实际可信 LOCAL 内容能力。原 Cloud API 早期拒绝保留；service 新请求和历史未 claim 请求在组装 Evidence payload 前拒绝 LOCAL；所有现有 Cloud transport 在授权、凭据、payload 与 invoke 前拒绝 LOCAL。伪造默认 YOUTUBE marker 的真实 local-ID 也拒绝。
- 旧 YT qwen3:8b production receipt 不授 LOCAL 资格；正常 production transport 即使该 receipt 对 YT 有效，LOCAL 仍 WAITING_MODEL / 零调用。独立 qualification seam 不用于普通 factory 激活。
- LOCAL card 外链为 NULL，保留实际 content/source ID、真实时间与现有内部 Content 深链。实际 YT 外链保持原投影；缺 provider 的旧投影 fixture 按原行为兼容，不改变 LOCAL 准入判断。

REJECT/DEFER：TEXT_RANGE/nullable 引用协议、任何新模型资格/profile reader、伪造时间/来源、库自动执行、Cloud LOCAL 权限、派生旧 canonical 归档、长内容 capacity/批处理均不在本实现中。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 原 LOCAL manual 缺口 | RED → PASS | `/tmp/local-timed-admission-red.log`：可信 timed LOCAL 被 `manual Content requires completed trusted source material` 拒绝；最小实现后同路径通过。 |
| LOCAL manual / NO_NEW / 正向 card | PASS（夹具） | `test_local_intelligence_timed.py`：禁用资料库手动命令、真实持久化 timed/Summary/Evidence、NO_NEW、正向 card、内部 Content/原证据回跳。转写 Executor 和 distillation transport 均为明确 fixture，没有真实模型调用。 |
| 来源与事务 CAS | PASS | 外来来源、未绑定 DATA、未定时文本拒绝；执行前 Summary hash 变更零调用；执行中 source bytes/canonical/Summary/timed reader/link/正规新 Summary 指针变更，正向和 NO_NEW 都拒绝，零新 Intelligence 且不重试执行。 |
| Cloud LOCAL | PASS | OpenAI/Nvidia/Moonshot/NonThinking 的明确 LOCAL 与伪默认 YT marker 均零凭据/零 payload/零调用；API review/confirm、service reserve、历史 review/authorize/continue 均拒绝，零 Cloud authorization rows。原 YT Cloud 回归保持。 |
| 门禁与恢复 | PASS | WAITING_MODEL / WAITING_BUDGET 零调用；只有合法 WAITING_MODEL 可幂等取消；重启不复活；未知执行 AMBIGUOUS 不重派；并发同 command 只有一个 reservation 与一次 fixture dispatch；旧 YT receipt 不扩 LOCAL 资格。 |
| Backup / Restore | PASS（隔离数据库） | 取消与 NO_NEW 两种终态：真实 readiness 按状态变化；备份/恢复后所有 SQLite 表逐行相等、全部 DATA path/hash 相等，来源/Summary/Evidence 可重新可信读取，终态不重执行。没有改 Backup 判定。 |
| 真实 LOCAL 模型与 macOS GUI | BLOCKED | 主控报告固定 9b 原资格首例语义 FAIL；当前仅代码/夹具验收。未伪造真实 Whisper/模型资格，未操作 owner 数据。 |

## 检查结果

- 新专项：39 PASS / 32.19 秒，`/tmp/local-timed-final.log`。
- 8 相关文件：269 PASS / 133.41 秒，`/tmp/local-timed-regression.log`：personalized distillation、reservation、source context、local wire branches、LocalContent/adversarial、offline transcription、local API。该次在最终 LOCAL 外链投影前运行，最终投影另重新验证 API 和 source context。
- 3 Backup 文件：82 PASS / 43.92 秒，`/tmp/local-timed-backup-regression.log`：unit BackupRestore、phase1b BackupRestore、Research BackupRestore；唯一 warning 为既有 duplicate-ZIP 攻击 fixture。
- 最终投影兼容修复后的新专项 + unit local API + source context：78 PASS / 45.14 秒，`/tmp/local-timed-final-api-corrected.log`；包括原 YT provenance/source URL 断言。
- Ruff（3 生产文件 + 新测试）、strict mypy（3 生产文件）、py_compile（3 生产文件 + 新测试）、git diff --check：PASS；提交前再次核验。
- 前端未修改，未运行前端/TS/build。主控整合后的完整后端、前端、TS/build 与真实 GUI 仍需执行；实现者不标记为已通过。

## 失败、Diff 复核与风险

保留失败日志与过程：首次测试遗漏 PYTHONPATH 导致 import error，改为显式 `PYTHONPATH=src`；源码使用的真实 locator 是 TIMED_MEDIA，初始 helper 的 TIMED 已纠正。Summary 变更负控先尝试设置既有同语言，未产生变更；再尝试语言切换被既有不可变 trigger 拒绝，两次方法失败后已向主控报告并停止重复该 SQL 方法，改为真实现有 Summary producer/read/promote 的新有效指针，原 REJECTED_OUTPUT/无新 Intelligence 断言保留。最终 DTO 复核原三项 API fixture 缺 provider 导致 AttributeError（`/tmp/local-timed-final-api-regression.log`）；只修兼容 getter，不改旧测试断言。

Diff 仅获批文件，无删除/跳过/弱化测试、门槛、CI；无广泛格式化或历史改写；无网络、推理、付费、正式数据、配置、Schema 或 main/push。部分负控直接修改/删除临时 fixture 的字节/关联以验证 fail-closed，仅限 pytest 独立数据库和临时 DATA。

剩余风险/限制：本切片仍保持既有最多 20 Evidence 和原 timed wire；不支持本地纯文本/长内容批处理。可信 reader 对实际媒体反复校验 hash，真实大文件性能需在之后的受控 GUI 验收观察，不在本次擅自优化安全边界。旧模型资格不足以使用户真正完成 LOCAL 提炼，不能宣称所有用户链路已通。

DECISION NEEDED：本实现范围内无新增审批请求；真实模型依赖、后续 LOCAL_TEXT 与整体采用由主控另行处理。

## 实现者结论

建议 IN_REVIEW。提交 SHA 由本分支最终提交报告提供。代码验收与模型资格验收明确分开；提交后停止写业务代码，等待独立审查。

## Reviewer / 主控验收 / 整合结果

### 独立 Reviewer `/root/intel_bounded_review`

**APPROVE（仅获批 LOCAL_TIMED 代码切片），P0/P1 = 0。** 实现 SHA `f399034d837807d9850cf16cebabdd32f6039478`，基线 `67d6e9a930fa0289c9d97c4ad3119e493b16ce0e`。作者 STOP、接手及检查后工作树均 clean。模型资格、真实 LOCAL 八例和完整用户旅程没有获批或被声明通过。

独立审查完整六文件 diff 与具体批准提案：只有显式 manual LOCAL_LIBRARY/DISCOVER_ONLY、同来源 READY 音视频、完整 verified timed/canonical/Summary/Evidence 可以构造 LOCAL seal。源文件、canonical、timed、当前 extractive Summary 和完整 coverage 进入 context hash；正规 reservation identity 重建后，正向与 NO_NEW 在 BEGIN IMMEDIATE 内再次验证相同 context。可信 reader 中嵌套读连接在该写事务保护下没有给予其他数据库 writer 变更窗口；文件字节仍按既有可信 reader 重新验 hash。未知、纯文本、外来来源、非手动 LOCAL 均不扩大权限。

Cloud API 的既有早拒绝、service 的 reserve/历史恢复拒绝、各真实 Cloud transport 的授权与 request 拒绝覆盖 LOCAL；默认 YT marker 搭配真实 local-ID 也不能构造 Cloud 请求。没有凭据/payload/dispatch 授权增加。旧 YT production receipt 在正规 composer 输出 LOCAL marker 时返回不合格，普通续跑保持 WAITING_MODEL/零调用；qualification seam 没有连接普通 UI。YT wire/semantic payload、模型参数、资格 reader 不变。LOCAL card 使用 NULL 外链、真实 Content/source/Evidence ID 与真实时间。

独立检查：

- 新专项 + source-context + unit API：**78 PASS / 41.95 秒**，包括执行中六类 authority 变更（正向与 NO_NEW）、取消/重启、全表全 DATA Backup/Restore、实际外链投影与旧 YT 投影兼容。
- 原 personalized distillation/reservation/local wire branches + Ollama/OpenAI/Moonshot adapter/dispatch：**224 PASS / 87.04 秒**。合计 302 项，未删/跳过/改断言或门槛。
- 额外独立正常 LOCAL fixture 并发 probe `/tmp/readiness-local-timed-independent-races.py`：第一续跑 claim 后阻塞；取消拒绝；另一个真实 repository 实例续跑转 AMBIGUOUS；释放第一调用后两者同终态。**总一次 fixture dispatch、第二零调用、零 card、重启后不重派**。无真实网络或模型。首次临时路径未 resolve，既有 NOFOLLOW 拒绝 macOS `/var` 符号链接（NotADirectoryError）；只修 probe 的临时根为真实路径，未改产品安全 reader 或测试。
- Ruff（3 生产文件 + 新测试）、strict mypy（3 生产文件）、py_compile、git diff --check：PASS。
- 与 root `8ba165f011121ec4ee26d68712d2a252b9a20473` 的只读 merge-tree：无冲突，结果树 `233b0955ed7bbf6e4697ef31ec8042fdd042d9d2`；未执行实际 merge/cherry-pick。
- 前端/TS/build 未执行：无前端改动。主控整合后的完整回归和真实 GUI 仍需执行。

剩余限制：固定 9b 原真实语义 FAIL，LOCAL 真实模型/GUI验收仍 BLOCKED；最多 20 Evidence、TEXT_RANGE、长内容处理及 Schema38 归档均未实现于此切片。大媒体反复可信 hash 的响应时间应在随后受控 GUI 中观察，本审查没有实测该性能或假称所有普通用户链路可用。未触及正式数据、配置、迁移、推理、资格收据或 main。

Reviewer 只补本交接并提交审查记录；任务状态与 ACCEPT/REJECT/整合/最终验收由主控决定。
