# TASK-011 assignment sync — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。只创建获批 worktree/branch 并提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Implementer/Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@44fc64be2cb4602cb93c1d03f84d6dd2a1677750`，必须干净且为唯一父基线。
- 目标 worktree：`/Users/developer/Documents/yia-worktrees/task-011`；目标分支：`codex/task-011-weekly-report`。两者开始时必须不存在。
- 产品负责人已批准 ADR-010 和正式分配：Codex 为唯一 Implementer，完成后由全新独立 Codex Reviewer 审查。
- TASK-012 保持 `BLOCKED/UNASSIGNED`；不得读取、修改或创建其 worktree。

## source 唯一允许路径组

1. `src/youtube_intel/reporting.py`
2. `src/youtube_intel/state.py`（只读周报候选查询；不改 Schema/migration/既有完成语义）
3. `src/youtube_intel/providers/obsidian.py`（周报 upsert）
4. `src/youtube_intel/templates/weekly.md`
5. `tests/unit/test_week_period.py`
6. `tests/integration/test_weekly_report.py`
7. `tests/fixtures/weekly/**`
8. `handoffs/TASK-011.md`

禁止依赖/锁、配置契约、Schema/migration、`complete_stage`、CLI、TASK-012、真实 Vault/用户笔记、云调用、网络和外部删除。仅允许 pytest 临时目录的最小 Vault 原子写/replace/fsync/symlink 安全测试。

## 唯一允许提交范围

1. `agent-prompts/TASK-011-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-011-IMPLEMENTER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-011-weekly-report.md`

## 必须执行

1. 核验 main identity `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、分支/HEAD、empty index/worktree、目标路径/分支不存在与精确五文件范围。
2. 从固定 base 创建目标 branch/worktree，核验 branch、HEAD 与洁净度。source 内 `READY/UNASSIGNED` 是固定 base 快照；实时控制面只在 main。
3. 对准备文件做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验；字节漂移立即停止。
4. main 将 TASK-011 设为 `IN_PROGRESS/Codex`，记录 worktree、分支、base、范围和资源边界；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-012 保持 BLOCKED。
5. 提交信息：`docs: assign TASK-011 weekly report worktree`。提交后 main/source 必须干净，确认 Implementer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-011 assignment sync
Base / Head: <base> -> <head>
Worktree/branch/base: <path> / <branch> / <base>
Committed files: <exact five>
States: TASK-011=IN_PROGRESS/Codex; TASK-012=BLOCKED/UNASSIGNED
Checks: <Git-only/worktree gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
