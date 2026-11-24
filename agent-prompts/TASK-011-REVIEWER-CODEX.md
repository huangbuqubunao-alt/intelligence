# TASK-011 — Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-011 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-011.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-REVIEWER-CODEX.md`；main 中 TASK-011 必须为 `IN_REVIEW`。
- Source/base：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e` / `44fc64be2cb4602cb93c1d03f84d6dd2a1677750`。
- Source 唯一父为 fixed base；完整允许范围严格为 `reporting.py`、`state.py`、`providers/obsidian.py`、`templates/weekly.md`、`test_week_period.py`、`test_weekly_report.py`、`tests/fixtures/weekly/**`、source handoff。
- Source 卡/状态为分配 base 快照；不得写回 source。TASK-012 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 source 运行会写 `.codebase-memory/` 的索引动作；用已配置 graph 只读查询或直接对固定 Diff 做窄范围审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff、未变依赖/锁和范围；禁止 Schema/migration、`complete_stage`、CLI、TASK-012、真实资源变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、full pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/video/weekly template inclusion、固定 Diff check。
3. pytest 临时 SQLite/最小 Vault 独立探针：
   - ISO 跨年、非 DST 时区周界、空周、Top N/并列稳定排序与 repeated run 的同一 reports key/同一 NoteRef；
   - 候选必须为 COMPLETE/high-value/受管 NoteRef，且 verified Score/Analysis/NoteRef 任何篡改或缺失均 fail-closed；
   - 只读取 verified local facts，零 Provider/云调用；关键词、趋势与持续方向确定性；
   - Jinja ImmutableSandboxedEnvironment + StrictUndefined，固定包内模板；
   - Vault 锚定、相对路径、symlink、同目录 temporary/fsync/replace、写入失败及 DB upsert 失败的补偿/重复恢复；不得触及真实 Vault 或测试目录外文件。
4. 复核 ADR-010 W-01..W-08、AC、五轴、复用/许可证。将 checks、探针、矩阵、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT` 追加到 source handoff，单独提交；不得改任务状态、merge、push 或清理。
