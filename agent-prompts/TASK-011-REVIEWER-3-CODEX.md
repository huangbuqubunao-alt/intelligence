# TASK-011 Correction 2 — Third Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-011 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-011.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-REVIEWER-3-CODEX.md`；main 中 TASK-011 必须为 `IN_REVIEW`。
- Source/base/head：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@0f589aca501ea4559aeb7f4dd7aeab2a41f52b79` / `44fc64be2cb4602cb93c1d03f84d6dd2a1677750`。
- Correction 2 唯一父为 Reviewer 2 evidence `6f9c75df90e10b964b36dbcefc52618422d83216`，其唯一父为 Correction 1 `f4e30a56ddcf7d654bda4e0579f6080af59698f5`。
- 完整允许范围严格为 `reporting.py`、`state.py`、`providers/obsidian.py`、`templates/weekly.md`、`test_week_period.py`、`test_weekly_report.py`、`tests/fixtures/weekly/**`、source handoff；Correction 2 只能改 `reporting.py`、两份既定周报 tests 与 handoff。
- Source 卡/状态为分配 base 快照；不得写回 source。TASK-012 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 source 运行会写入 `.codebase-memory/` 的索引动作；用已配置 graph 的只读查询或直接对固定 Diff 做窄范围审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、Correction/完整 Diff、未变依赖/锁和范围；禁止 Schema/migration、`complete_stage`、CLI、TASK-012、真实资源变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、`tests/unit/test_week_period.py`、`tests/integration/test_weekly_report.py`、full pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/video/weekly template inclusion、固定 Diff check。
3. pytest 临时 SQLite/最小 Vault 独立探针：
   - 每个候选必须有受管 NoteRef，且在 Knowledge Sink 或 reports 写入前验证相对锚定路径、拒绝路径逃逸和 root/subdir/Videos/file symlink、拒绝非普通或缺失文件，并复核实际内容 SHA-256、video/pipeline/provenance identity；任一缺失、篡改或 mismatch 必须零 Vault/reports 写入。
   - 复跑 verified Analysis-only 趋势、关键词和持续方向，以及 NFC、空白/casefold、频率/并列排序；不得退回 Score topics fallback。
   - 复跑 ISO 跨年、非 DST 时区周界、空周、Top N/并列稳定排序与 repeated run 的同一 reports key/同一 NoteRef；候选必须为 COMPLETE/high-value，且 verified Score/Analysis/NoteRef 任一缺失或篡改均 fail-closed。
   - Jinja `ImmutableSandboxedEnvironment` + `StrictUndefined`、固定包内模板；Vault 同目录 temporary/fsync/replace、写入失败及 DB upsert 失败补偿/重复恢复；不得触及真实 Vault 或测试目录外文件。
   - 零 Provider/云调用；不得读取网络、凭据或真实用户内容。
4. 复核 ADR-010 W-01..W-08、AC、五轴、复用/许可证。将 checks、探针、矩阵、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT` 追加到 source handoff，单独提交；不得改任务状态、merge、push 或清理。
