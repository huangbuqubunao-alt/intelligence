# TASK-002 Grok Correction Packet

## 身份与目标

你仍是 `TASK-002` 的唯一 Grok Implementer。主控只读预审确认原实现的 Git 基线与 8 文件范围正确，但发现三个既有验收契约未真正满足。本轮只追加最小修复与回归证据，不领取 Reviewer、Integrator 或后续任务角色。

## 固定上下文

在原 worktree 中完整读取其现有版本：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/SYSTEM_DESIGN.md` 第 5、6、7、12、14 节
5. `docs/decisions/ADR-002-config-domain-contracts.md`
6. `agent-prompts/TASK-002-IMPLEMENTER-GROK.md`
7. `handoffs/TEMPLATE.md`

再从 main 控制面只读以下绝对路径；不得修改、暂存、merge 或 cherry-pick：

8. `/Users/developer/Documents/youtubek agent/docs/decisions/ADR-003-sqlite-state-store-contract.md` 中 `target_stage` 的职责
9. `/Users/developer/Documents/youtubek agent/tasks/TASK-002-config-domain-contracts.md` 的“主控预审修复轮”
10. `/Users/developer/Documents/youtubek agent/agent-prompts/TASK-002-CORRECTION-GROK.md`

worktree 基于较早控制面 commit，可能看不到本修复包及最新任务卡，这是预期隔离。本文件内容由主控直接分配，不得把最新 `main` merge/cherry-pick 到任务分支。

## 开工包

- Task: `TASK-002`
- Role: `Implementer correction round`
- Agent: `Grok`
- Original base: `main@46f8497e771e1461034942dd7967f19d85f79f81`
- Required current head before changes: `4355a59f6f95e409bcf15b3b8004bb112d0033b3`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-002`
- Branch: `grok/task-002-config-domain-contracts`
- Reviewer: Codex，继续等待修复证据
- Reuse decision: `DIRECT` 使用现有 Pydantic/PyYAML；不新增组件或依赖
- Parallel now: Status Integrator 可在 main 同步本修复轮控制面
- Waiting: Codex Reviewer、TASK-003、TASK-004 写入实现

先运行 `pwd`、`git branch --show-current`、`git rev-parse HEAD`、`git status --short`。目录、分支、HEAD 或干净状态不符立即停止。

## 允许范围

本轮只允许修改：

- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `handoffs/TASK-002.md`

原任务相对 base 的总范围仍必须恰好属于已批准的 8 个文件。不得修改依赖、锁文件、示例配置、CLI、任务状态、ADR 或其他 worktree；不得改写、amend、rebase 或删除原实现提交。

## 必须修复

### F-01：异常中的密钥样式输入

已复现：`CloudSettings(api_key_env="sk-redaction-probe-123")` 的 Pydantic 错误包含原始 `input_value`，违反 AC-8。

- 先新增失败测试，再做最小修复。
- 受控哨兵必须真实传入 `CloudSettings` 和 YAML/`load_settings` 路径。
- `ValidationError`、`ConfigError`、配置对象 `repr`/dump 均不得包含该哨兵。
- 错误仍需包含可定位字段路径；不得读取任何环境变量值。

### F-02：公开自由形状字典

原实现公开导出 `load_yaml_mapping() -> dict[str, Any]`，违反“公共接口不使用自由形状 `dict`”。

- 原始 YAML mapping 加载只能是内部边界实现，不能留在 `__all__` 或其他公共入口。
- 对外加载入口返回已验证的具名对象。
- 回归测试必须检查模块公开导出和公开函数返回注解，不能只检查少量模型字段。
- 恶意 YAML tag 仍须通过公开加载路径证明被 SafeLoader 拒绝。

### F-03：可变公共状态表

原实现把 Pipeline/Job 转换表作为可变公共 `dict` 导出，违反公共集合只读语义。

- 转换表改为私有实现，或使用运行时不可变映射。
- `can_transition_*` 与 `transition_*` 行为保持不变。
- 回归测试证明调用方不能改变合法转换集合。

### F-04：冻结集合和职责自审

- 公共 `ErrorCode` 只保留 System Design 第 12 节冻结的八项；`InvalidTransitionError` 不得借此扩展统一 Provider/应用错误码。
- `target_stage` 的数据库字段和 Job 持久化由 ADR-003/TASK-003 实现；本轮不新增 Job 存储模型。
- 重新核对 Provider 的 request correlation 与 `ProviderCallMetadata` 要求。若满足它需要新增未冻结 Wrapper、结果字段或其他公共类型，停止该部分并在最终输出给出 `DECISION NEEDED`；不得自行设计。

## 提交与验证

1. 先为代码和测试创建追加修复 commit，建议：`fix: harden configuration and domain contracts`。
2. 再单独更新 `handoffs/TASK-002.md`，明确区分原实现 commit、修复代码 commit 和最终证据 head；交接 commit 不得把自身 SHA 伪装成已知值。
3. 运行：

   ```bash
   uv lock --check
   uv sync --locked
   uv run python -m pytest tests/unit/test_contracts.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   uv run python -m youtube_intel --help
   git diff --check 46f8497e771e1461034942dd7967f19d85f79f81..HEAD
   git status --short
   ```

4. 完整复核 `46f8497e771e1461034942dd7967f19d85f79f81...HEAD`，确认总范围仍为原 8 文件且没有密钥、真实 Vault、生成物或范围外修改。

## 最终输出

```text
Task: TASK-002 correction round
Role: Implementer
Original implementation commit: 4355a59f6f95e409bcf15b3b8004bb112d0033b3
Correction code commit:
Final evidence head:
Changed files in correction:
F-01/F-02/F-03/F-04: PASS/FAIL/BLOCKED + evidence
Checks:
Full base...HEAD scope review:
Handoff accuracy:
Remaining risks:
Decision needed: None | details
```
