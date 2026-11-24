# TASK-012 Correction 1 — Second Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-012 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-012.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-012-REVIEWER-2-CODEX.md`；main 中 TASK-012 必须为 `IN_REVIEW`。
- Source/base/head：`/Users/developer/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations@d046c394e3c6bcf47c05231f71dbf50db4c1f5f8` / `8e322f362d2ff0972ee987b7c06c8453a9dce73d`。
- Correction 1 唯一父为 Reviewer 1 evidence `9b5dec5d24e87ab942dff4268f7a95c35947d411`，其唯一父为 original implementation `7c83283eac83b01c88a7625b4a216790d14514b2`。
- 完整允许范围严格为 12 个 TASK-012 路径；Correction 1 只可改 `cli.py`、`logging.py`、operations integration test 与 handoff。`pyproject.toml` 例外仅为 source-include；依赖、lock、build backend 不得变化。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 source 运行会写入 `.codebase-memory/` 的索引动作；任何范围外工件必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、Correction/完整 Diff、12 路径范围、未变依赖/锁及 pyproject 例外；禁止 Schema/migration、state/domain/config、Provider、网络、真实 Vault、真实用户内容、凭据、`launchctl` 和任务状态变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、operations tests、full pytest、mypy、Ruff、CLI help、两份 `plutil -lint`、offline build、sdist/wheel migration/resource listing、固定 Diff check。
3. 独立临时目录/Fake probe：
   - 不存在 `logs/`、Vault 或数据库 parent 时，`doctor` 必须只在内存生成 UUID4 run_id；零 JSONL/logger 打开或写入、零 logs/Vault 目录创建、零 Job/Repository 写入、零 Provider/loopback/网络/credential resolver 调用、零 Vault 内容读取。
   - 保留其余命令的退出码 `0/1/2/3`、部分失败语义和 JSONL 必填字段/敏感信息脱敏；不得以 doctor 例外削弱其他命令日志证据。
   - 复核静态 plist、无 `launchctl`、无自动日志删除与 sdist/wheel root/package-resource bytes/hash 一致。
4. 复核 ADR-011 O-01..O-06、AC、五轴、复用/许可证。将 checks、探针、矩阵、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT` 追加到 source handoff，单独提交；不得改任务状态、merge、push 或清理。
