# TASK-012 first review reject / Correction 1 sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@e87f73cebb4ca9f7c5f981872760774209f3ebdb`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@9b5dec5d24e87ab942dff4268f7a95c35947d411`，必须干净。
- Reviewer evidence `9b5dec5...` 的唯一父为 implementation `7c83283eac83b01c88a7625b4a216790d14514b2`，且只修改 source handoff；implementation 唯一父为 fixed base `8e322f362d2ff0972ee987b7c06c8453a9dce73d`。
- 完整 source Diff 仍严格为 12 个批准路径；`pyproject.toml` 例外、依赖/锁和 build backend 边界不变。

## 审查拒绝事实

- Verdict=`REJECT`，P0=0、P1=1。Reviewer 在 P1 后停止，后续离线门禁/探针不得写为通过。
- P1：`doctor` 在诊断前初始化 JSONL logger，创建 `logs/` 目录，违反 ADR-011 O-02 的严格零副作用边界；现有测试没有断言不存在的 logs/Vault 目录保持不存在。

## 唯一允许提交范围

1. `agent-prompts/TASK-012-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-012-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-012-cli-operations.md`

不得访问、修改或创建 TASK-013/014 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、evidence handoff-only scope、完整 12 路径范围与未变依赖/锁。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据、launchctl、plutil 或任何产品文件 I/O 命令。
4. main 将 TASK-012 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 1；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-013/014 保持 BLOCKED。
5. 提交信息：`docs: return TASK-012 for doctor side-effect correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 1 边界

- 只授权 source `src/youtube_intel/cli.py`、`src/youtube_intel/logging.py`、`tests/integration/test_operations.py` 和 `handoffs/TASK-012.md`。
- `doctor` 可在内存生成 run_id/安全诊断结果，但在任何路径上均不得创建/打开/写入 JSONL、logs 目录、Vault 目录、Job、Provider、loopback、网络或读取密钥值/Vault 内容；配置/SQLite/Vault 边界只在 pytest 临时对象上只读验证。
- 新增临时项目目录不存在 `logs/`/Vault 时的回归，并保留五命令退出码、JSONL 脱敏、plist、archive、依赖/锁与真实资源边界。
- 不得改 `__main__.py`、`pyproject.toml`、package resources、plist、operations 文档、依赖/锁、Schema/migration、state/domain/config、Provider、CLI public command set、TASK-013/014 或真实资源。若 O-01 run_id 与 O-02 零日志无法在现有内部结构同时实现，报告 `DECISION NEEDED`。

## 回传格式

```text
Task: TASK-012 first review reject / Correction 1 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-012=IN_PROGRESS
Committed files: <exact five>
Checks: <Git-only gates>
TASK-013/014 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
