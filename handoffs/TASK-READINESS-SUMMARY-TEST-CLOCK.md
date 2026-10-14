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
