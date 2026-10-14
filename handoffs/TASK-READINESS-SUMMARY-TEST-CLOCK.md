# TASK-READINESS-SUMMARY-TEST-CLOCK 交接

## 元数据与边界

- Role Implementer / caption_resume；Reviewer intel_bounded_review，提交后 STOP。
- Base `5cfbad10141ea89d001e8006fe5c30919201cd24`。
- Worktree `/Users/hua/Documents/yia-worktrees/readiness-summary-test-clock`。
- Branch `codex/task-readiness-summary-test-clock`，2026-10-15。
- 仅 `tests/integration/test_summary_live_cutover.py` 与本 handoff。
- DIRECT 标准库 datetime/pytest monkeypatch、已有 SQLite/RecordingProvider/ref registry，
  不新增组件/依赖。复用 root .venv 为忽略 symlink，不安装或写共享 runtime。

## 根因与最小修改

旧 NOW 在模块 collection/import 时取 UTC，原 `_claim_analysis_job` 默认参数也捕获
该 NOW。完整 suite 超过10分钟后仍以导入时刻认领，生产 analyze 正确使用执行时刻，
故 complete_analysis_stage 的既有 `_owned_running_job` 拒绝过期 lease。
原完整日志 4445 PASS /7 LeaseConflict FAIL /1既有 SKIP /1303.93s 保留：root
`.var/end-to-end-user-readiness/backend-full-fb067-checkpoint.log`，不能改称 PASS。
普通生产 owned_running_job/complete_analysis_stage 从已审9f3至fb067相同，Schema38
未改普通 Analysis。此前只读 runpy 尝试因 provider refs 缺失先停，不冒充额外复现。

现在只让 test helper 默认 now=None 时在认领当次取 datetime.now(UTC)，restart
原测试不再显式传模块 NOW。原元数据/registry/hash 输入 NOW 表达式不变，仍冻结。
10min lease、生产 clock/拒绝保护、所有原断言及 provider identity/缓存合同均未改变。

新增两个真实 service+私有 SQLite 控制时钟测试：

1. 模块 NOW 后11分钟进行当次认领与 analyze 成功、job SUCCEEDED、ANALYSIS_READY、
   Evidence 已合法提升；再过11分钟新句柄认领重启 job，重建 registry/request identity
   一致，缓存复用成功、第二个 provider **0** generation、原 provider 仍1。
2. 真正于 NOW 认领，NOW+11分钟完成时仍抛精确 LeaseConflict，未提升 Summary Evidence，
   structured artifact 不存在，pipeline SCORED、job RUNNING；测试 recording provider
   调用1次不等于实际模型调用，所有网络/model/cloud均0。

## 检查与原失败证据

- `PYTHONPATH=src:. .venv/bin/python -m py_compile tests/integration/test_summary_live_cutover.py`
  PASS（TDD前与最终均验证语法）。
- TDD 新2项：**1 FAIL /1 PASS /19 deselected /1.15s**，
  `/tmp/summary-test-clock-tdd-red.log`。正控完整 analyze 在 state.py:2958 真正抛
  `LeaseConflict: job lease is not owned or has expired`；真正过期负控从修前即 PASS。
- 最终完整本模块：**21 PASS /8.44s**，`/tmp/summary-test-clock-final-module.log`。
  前一版21 PASS/8.74s后，仅新增非空类型证明断言再次验证，没有删弱旧断言。
- `pytest -q tests/integration/test_state_store.py -k 'lease or renew or claim or expired or complete_analysis'`：
  **6 PASS /40 deselected /2.14s**，`/tmp/summary-test-clock-lease.log`；deselected 是专项
  选择而非新skip，原 lease/renew/claim/expiration正负规则保持。
- Ruff 检查该测试 PASS，`/tmp/summary-test-clock-final-ruff.log`。
- `MYPYPATH=src PYTHONPATH=src:. .venv/bin/mypy --strict src`：
  **102 source files PASS**，`/tmp/summary-test-clock-mypy-src.log`。
- 额外测试文件严格 mypy **未通过**：初次漏 MYPYPATH 错读 installed module，保留
  `/tmp/summary-test-clock-mypy-test.log`；正确 local path 后现有23历史错误及新增6个
  Optional读取错误，保留 `/tmp/summary-test-clock-mypy-test-local.log`。只在新增测试
  补非空断言解决新6项。最终 `--strict` 本模块与原base `--shadow-file` 均23历史错误，
  error消息列表逐条相等，未再重复尝试或修改旧测试类型/断言。证据
  `/tmp/summary-test-clock-final-mypy-test.log`、`/tmp/summary-test-clock-base-mypy-test.log`。
  历史测试文件不是生产src strict gate；不能宣称其严格类型检查 PASS。
- AST 独立机械比较 **全部110原断言不变**，除claim helper/restart参数之外所有旧函数
  AST不变；src/config/deps完整 diff为空，`/tmp/summary-test-clock-final-proof.log`。
- `git diff --check` PASS，无 generated/config/deps/Schema/owner/model写入。

## 结论与剩余门禁

建议 IN_REVIEW；只提交两文件并 STOP，不自审、不整合、不改公共任务状态。
未跑新完整 backend/frontend/build/真实GUI：本卡为test-only，完整后端必须由root
在最新已接受整合候选再跑，当前27个专项通过不能替代完整回归或正式采用。
原全suite失败证据与独立批准门禁仍保留，生产10min过期保护未放宽。


## 2026-10-15 独立 Reviewer / intel_bounded_review

**APPROVE** 作者 `184d9446b77da5ebc153362eb9aff5e70e5a7267`，固定 base
`5cfbad10141ea89d001e8006fe5c30919201cd24`。作者 STOP/clean 后审查，唯一 Reviewer；
仅追加此 handoff，不改测试、生产、配置、Schema、其他树或公共 task 状态。审查后
STOP，不自合并/发布，也未调用模型、网络、凭据或 owner 数据。

重读原任务与 root agent package，沿用 AGENTS/协作/规格/reuse 规则；graph-first
定位旧 lease/summary 路径（本新增测试不在旧索引），再核实际固定候选完整两文件
差异。Standards 与 Spec 两轴没有 P0/P1/P2。修改只有测试 claim helper 默认 UTC
取值改为调用时刻、restart 不再传导入 NOW，以及明确时钟正负控；生产 `_utcnow`/
10min lease/complete-analysis 拒绝保护字节完全不变，不用 fixture 修复弱化标准。

独立实际证据：

- `PYTHONPATH=src:. python -m pytest -q tests/integration/test_summary_live_cutover.py`：
  **21 PASS /8.97s**，`/tmp/summary-clock-review-module.log`。
- `pytest -q tests/integration/test_state_store.py -k 'lease or renew or claim or expired or complete_analysis'`：
  **6 PASS /40 deselected /2.07s**，`/tmp/summary-clock-review-lease.log`。限定选择
  不是新增 skip；原 full-suite 失败没有改称通过，根后续全后端仍必需。
- py_compile 与 scoped Ruff PASS；`MYPYPATH=src PYTHONPATH=src:. mypy --strict src`：
  **102 source files PASS**，`/tmp/summary-clock-review-mypy-src.log`。
- 额外该测试模块 strict mypy 与原 base `--shadow-file` 均有 **23 历史 errors**，
  去掉行号后逐条消息完全相等，没有新增 errors；分别
  `/tmp/summary-clock-review-mypy-test.log` 与 `/tmp/summary-clock-review-mypy-base.log`。
  不声称 test-module strict gate PASS，不顺便修改历史测试类型。
- 逐 symbol AST 比较全部原断言完全相同：**110 个原顶层函数断言（含 helper）+
  RecordingProvider class 的 3 个断言，共 113**。除 `_claim_analysis_job` 与原
  restart 测试调用参数外，所有原函数/class AST 完全相同。原 tuple/ref identity/
  hydration/cache/次数/Evidence 断言没有削弱。检查
  `/tmp/summary-clock-review-symbol-proof.log`。
- 原 base→HEAD 精确只测试与本 handoff；src/frontend/config/deps/Schema/CI 差异
  为空、production lease 合同字节相同；diff check PASS。根共同祖先就是 fixed
  base，当前产品整合修改不与本测试 diff 重叠。

时钟正控确实在 module NOW 后11分钟认领/analyze，job SUCCEEDED、ANALYSIS_READY
与 Evidence 合法提升；再11分钟重启新 job 后，registry/request identity 不变，第二
RecordingProvider generation=0、原 provider=1。真正过期负控仅在 NOW 认领，却于
NOW+11分钟完成，精确 LeaseConflict、job RUNNING、pipeline SCORED、0 promoted
Evidence、无 structured artifact。recording provider 是私有 fixture，不等于真实
模型调用；这些成功不能授生产资格或假称真实 GUI 模型验收。

临时机械审查器计数错误保留：最初将包含 class 的全113断言硬比较为任务所称110，
随后误将110理解为仅 `test_` 前缀函数，两次仅计数的 AssertionError；原断言逐项
比较始终相同。停止该硬编码计数方法，逐符号检查确认作者110是所有非class顶层
函数、另有class3。`/tmp/summary-clock-review-proof.log`、
`/tmp/summary-clock-review-proof-corrected.log` 与工具输出保留；最后采用完整逐符号
比较通过，不修改产品/测试或弱化原断言，不把检查器计数错误算产品失败。

本切片没有产品代码，未重复完整后端/前端/build/真实GUI；根接受后仍须用最新
完整候选重跑全后端，确认原长 suite 7 个 LeaseConflict 假失败确已消除，不能用
27 专项代替。原4445PASS/7FAIL/1skip与所有失败日志保留。
Verdict **APPROVE / P0=0 / P1=0 / P2=0**，仅提交独立 review 后 STOP。
