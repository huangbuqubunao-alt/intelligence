# TASK-012 — Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-012 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-012.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-012-REVIEWER-CODEX.md`；main 中 TASK-012 必须为 `IN_REVIEW`。
- Source/base/head：`/Users/hua/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@7c83283eac83b01c88a7625b4a216790d14514b2` / `8e322f362d2ff0972ee987b7c06c8453a9dce73d`；source 唯一父为 fixed base。
- 完整允许范围严格为 `__main__.py`、`cli.py`、`logging.py`、`pyproject.toml`、根目录 daily/weekly plist、`docs/operations.md`、三份 package resources、`test_operations.py` 与 source handoff。
- `pyproject.toml` 只允许 `[tool.uv.build-backend].source-include` 的归档路径；不得改变 build backend、依赖、版本、工具链或 `uv.lock`。package resources 必须与根目录文件逐字节相同。
- Source 卡/状态为分配 base 快照；不得写回 source。TASK-013/014 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 source 运行会写入 `.codebase-memory/` 的索引动作；用已配置 graph 只读查询或直接对固定 Diff 做窄范围审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff、12 路径范围、pyproject 例外、未变依赖/锁；禁止 Schema/migration、state/domain/config、Provider、网络、真实 Vault、真实用户内容、凭据、`launchctl` 和任务状态变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、`tests/integration/test_operations.py`、full pytest、mypy、Ruff、CLI help、两份 `plutil -lint`、offline build、sdist/wheel migration/resource listing、固定 Diff check。
3. 独立临时目录/Fake probe：
   - 五个命令的帮助、参数、退出码 `0/1/2/3` 与部分失败语义；配置/前置条件必须在 handler/昂贵路径前失败。
   - 每次命令 UUID4 `run_id`；JSONL 必填字段、可选关联字段与安全消息；包括 secret-shaped 值、字幕/模型文本、绝对路径和异常链均不得泄漏。
   - `doctor` 只检查配置、项目内路径、临时 SQLite/迁移、Vault 边界与启用 Provider 配置；零 Job、Provider/loopback/网络调用、密钥值/Vault 内容读取或 Vault/日志目录创建。
   - daily/weekly plist 静态有效、互斥计划和占位符/WorkingDirectory/log redirect 说明正确；代码和测试不得执行 `launchctl`，日志只记录 30 天策略，不删除任何文件。
   - sdist 含 root plist/docs 与 migration；wheel 含 migration 和三份 package resources；每对静态文件 SHA-256/字节必须相同。
4. 复核 ADR-011 O-01..O-06、AC、五轴、复用/许可证。将 checks、探针、矩阵、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT` 追加到 source handoff，单独提交；不得改任务状态、merge、push 或清理。
