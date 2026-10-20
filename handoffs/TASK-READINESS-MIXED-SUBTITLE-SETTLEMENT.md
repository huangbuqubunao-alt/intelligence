# MIXED-SUBTITLE-SETTLEMENT 实现交接

## 元数据

- Task: `TASK-READINESS-MIXED-SUBTITLE-SETTLEMENT`
- Role: Implementer（独立 Reviewer 与 root GUI 最终验收仍待）
- Base: `codex/task-end-to-end-user-readiness@4e20793e08ce7c223e3e5dd03468e1f6424d1c8a`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-mixed-subtitle-settlement`
- Branch: `codex/task-readiness-mixed-subtitle-settlement`
- 日期：2026-10-20（Asia/Shanghai）
- 用户持续默认授权；root 已接受开工前方法、范围和风险说明。
- root 后续明确追加相邻 UI 范围：真实字幕重试完成后 Evidence 保持旧空态，直到浏览器刷新。

## 实现范围和复用

`DIRECT` 原有 v1/429 完整判定、v2/LOCAL_RESOURCE 完整确定性证明、SQLite
`BEGIN IMMEDIATE`、Backup protected operation gate、stage/restore 锁及完整 DATA
读验；仅 Python 标准库及既有 React/测试工具，无新增第三方源码或许可要求。

- `state.py`：两旧入口共享单一内部协调器。对**全部 unresolved** 逐条证明，
  全部成功后才写入；同一 protected window/同一事务完成 v1 原错误追加原
  POLICY_RETIRED 注释、v2 不可变归档及原 CAS 终止，随后完整文件验证。
  任一未知、坏证明、未知文件、其他活动执行或恢复并发则整批不变；运行时
  故障/冲突传播时事务回滚。旧入口返回各自类别的子集、纯类和 worker idle 兼容。
- v1 predicate 与基线抽取后 AST **完全相等**，没有改变原允许的非空错误文本。
- `transcripts.py`：仅冻结 `2026.7.4`、`2026.07.04` 两个 exact 版本，联合语言
  候选唯一重算，绑定原 capture 和后继。新增唯一已证实历史 parent pair
  `(subtitle-selection-v2-original-tracks, subtitle-format-v1)`。
  不 normalize、不读取可变安装值、不改历史身份或 proof-v1。
- 字幕测试：混合两入口/worker 正向、重复/重启/全量恢复、两类别的严格负控、
  未知第三项/活跃工作/坏文件/restore/background gate、事务中途失败回滚，
  两 exact provider 版本、未知版本及两历史 parent pair/未知 pair。
- 七项 manifest-neutral ZIP 负控保留 ZipInfo/regular metadata，先做同构不变
  重包 stage 成功正控，再匹配各自语义拒绝原因。另增加匹配数据库/manifest 外层
  size/SHA、保留完整 schema 的 proof-hash 损坏反控，直接到达严格 proof verifier。
  既有 special-file 防线未修改。
- Backup UI：有限中英文原因映射，区分完整性不可验证与未完成工作；未知原因
  中性 closed。保留多原因，包括 pending restore 同时存在的其他原因；不显示
  后端原始错误或路径。
- Content UI：已验证成功 request_id/revision 的结果身份使 Evidence 与 Deep
  Analysis 重新 GET；新结果使旧 preflight 失效。独立于人工状态读取和普通
  Evidence 刷新计数，避免借此清除 Deep Analysis 的未知 dispatch 状态。
  Content ID 导航仍使用既有 keyed panel，不带入前一内容的证据，不增加 POST。
- `DESIGN.md`：仅补持久化反馈原则一段。

未改 Schema、迁移、依赖/锁文件、生产/正式配置、凭据、模型资格、Cloud、原冻结
现场或正式数据。未合并、push、发布；公共任务和状态文件未编辑。

## 真实冻结现场的完整副本证明

唯一输入：root `.var/end-to-end-user-readiness/schema38-mixed-failure-frozen-20261018`，
74 张表 / 19 DATA。完整目录逐文件 size/SHA（包括 DB/WAL/SHM/receipt）复制到本 WT
ignored `.var/mixed-subtitle-settlement/frozen-copy4`，原始库仅 `immutable=1` 读取。

- 普通 `build_local_source_run_runtime` + `NoCredentials`，无 fake provider/data；
  原已批准历史 QA 配置只读加载，内存中经完整模型校验重定位到副本空 Vault。
  不启动 worker/server；socket 连接抛 OSError，工厂本地 availability 探测正常
  走离线分支，实际无 HTTP、模型执行或新资格。
- 工厂迁移副本至现行 40、77 tables；readiness 原为
  `[PROVIDER_CALL_UNRESOLVED]`，维护后三条请求一起终止、一个 23-field archive，
  readiness=true。
- create/download/strict stage/confirm/apply 后再次正常工厂启动：全部 **77 表全部
  行**及 **19 DATA path/size/SHA** 与结算后完全相等。
- 原 74 表逐行比较：全部历史保留，provider keyset 不变，仅三条指定终止字段
  变化（v1 注释 exact）；原 migration receipts 保留。所有其他原表行完全相等。
- 操作前后**原现场全部 SQL 和全部物理文件**不变，SHA/size 包含 SHM 一并验证。
- 私有完整证明/脚本位于本 WT `.var/mixed-subtitle-settlement/`：
  `frozen-proof.json`、`prove_frozen.py`、`verify_preservation.py`、
  `frozen-proof4.log`、`preservation.log`。完整私有行和 DATA 内容不提交。
- 此证明不能替代 root 之后的 macOS 普通 GUI create/download/Native Picker/
  strict preview/RESTORE/restart 实测。

## 检查

执行环境：不安装依赖，复用 root 的 `.venv/bin/python` 和 frontend/node_modules；
所有 Python 命令使用本 WT `PYTHONPATH=$PWD/src`，真实冻结证明显式验证 module origin。

| 检查 | 结果 | 私有完整日志 |
|---|---|---|
| `python -m compileall -q src tests/integration/test_retained_subtitle_derivations.py` | PASS | 实际退出 0 |
| `python -m mypy --strict src/youtube_intel` | PASS / 115 source files | `mypy-final.log` |
| `python -m ruff check src tests` | PASS | `ruff-complete.log` |
| `pytest tests/integration/test_retained_subtitle_derivations.py tests/integration/test_retired_subtitle_failures.py -q` | **193 PASS / 265.27s** | `backend-final.log` |
| 新增归档 DB/hash 精确 proof-verifier 负控单项 | **1 PASS / 3.04s**（合计 194 distinct current cases） | `zip-proof-corrected.log` |
| 七原 ZIP 语义负控 + 多类别纠正负控 | 39 PASS / 72.91s | `backend-corrected.log` |
| 历史 parent 策略 exact/未知专项 | 3 PASS / 8.07s | `historical-parent.log` |
| `pytest tests/unit/test_backup_restore.py tests/integration/test_runtime_composition.py tests/integration/test_tracked_content_retry.py -q` | **198 PASS / 192.84s** / 1 预期重复 ZIP 名称 warning；含 Schema34–40 matrix | `backend-adjacent.log` |
| Schema39 恢复/恶意重算归档专项 | **19 PASS / 11 deselected / 55.94s** | `local39-compat.log` |
| frontend `npm test` | **964 PASS / 36 files / 19.05s** | `frontend-final2.log` |
| frontend `npm run typecheck` | PASS | `ts-final2.log` |
| frontend `npm run build` | PASS | `build-final.log` |
| 全量真实冻结副本备份恢复/正常重启/所有原行保存 | PASS | `frozen-proof.json` / `preservation.log` |
| Diff 复核、`git diff --check` | PASS；仅本任务范围 | Git diff / 源文件 SHA receipt |

首个最终批次收集 193 项后，补加第 194 项以明确到达 proof verifier，单独通过；
没有把相同测试重复次数相加为 distinct 计数。整个项目后端完整批次按分工留给 root，
本轮没有启动重复全后端。

## 保留的失败证据与修正

所有日志保存在本 WT `.var/mixed-subtitle-settlement/`，不删除失败。

1. `red.log`：原基线 4 FAIL / 2 PASS；混合两入口/worker 均不能结清，exact
   `2026.07.04` 不可验，旧 exact 版本和未知版本 closed 控制通过。
2. 首轮 `backend-targeted.log`：189 PASS / 1 FAIL。新测试误认为 v1 任意不同的
   非空原错误文本不合格；原 v1 仅要求非空并保留全文，AST 未变。查看原断言
   后把新增负控改为真正非法的空文本，未改产品判定或既有测试。
3. UI RED：实际缺少 integrity/unknown copy 和成功轮询后 Evidence 不重新读取。
   新测试最初出现表驱动数组被展开、Evidence DTO 使用错误字段、pending restore
   双 status selector 等测试编写问题，分别按实际 DTO/DOM 修正，未移除断言。
   一个修复命令 cwd 错误导致 FileNotFoundError，日志保留；有效 fixture 的
   `frontend-red-valid-fixture.log` 仍准确复现两类 UI 缺陷。
4. 冻结证明脚本前三次是 harness setup：配置禁止 model_copy(update)、副本空
   Vault 尚未创建、socket AssertionError 不属于正常 offline 异常。分别采用
   config model_validate、创建独立空 Vault、OSError socket 禁止后普通工厂通过。
   未修改产品代码绕过配置或网络安全，四个完整副本和各错误日志保留。
5. 额外恶意归档 proof-hash 反控首轮 7 PASS / 1 FAIL：临时 SQLite 变更仍在 WAL，
   只改了 manifest，实际到达 metadata mismatch 而非 proof verifier。显式关闭
   测试归档连接、确认 WAL 为空且数据库字节实际改变后重算外层 size/SHA；
   原 `zip-final.log` 保留，修正结果见 `zip-proof-corrected.log`。
6. Jev 路由调用 HTTP451 不可用；按既定 strong workflow 继续，未降级。

## 剩余验收与风险

- 独立 Reviewer 必须审查整个 `4e20793...HEAD`，不能仅审 UI 提交。
- root 负责当前候选完整后端最终门禁及普通 macOS 真实 GUI 恢复、重启与逐表/
  DATA 验收；本实现者未把任务设为 DONE。
- 前端完整测试有既有 React act(...) 警告（ExistingSourceForm 等）；未屏蔽。
- 原错误/资格/安全/证据/Backup 闭合标准均保留，无新的生产运行或外部承诺。


## 固定证据摘要

`docs/validation/end-to-end-user-readiness/MIXED_SUBTITLE_SETTLEMENT_IMPLEMENTER_2026_10_20.json`
记录本次完整命令结果、全部实现文件 SHA、私有脚本/日志 SHA 和原冻结库/完整文件
索引 SHA。私有完整行和文件内容未复制进受跟踪报告。

## 提交与交接状态

- UI：`9927324`，真实 Backup 原因与自动字幕结果刷新。
- 核心和测试：`19d8107`，混合严格结清、有限历史兼容、ZIP 语义反控。
- 实现者建议：`IN_REVIEW`，提交后 clean STOP，等待独立 Reviewer。
- Reviewer / Orchestrator / Integrator 结论：待相应角色独立填写。
