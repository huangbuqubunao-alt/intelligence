# TASK-011 — Product Integrator

你是全新的 Codex Product Integrator。只整合已验收的 TASK-011 source；不得开发、修复、重写历史、推送或清理 source worktree。

## 动态授权与固定对象

- Execution base：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-INTEGRATOR.md` 必须解析为本授权提交，且 main 中 TASK-011=`ACCEPTED`。
- Source：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report@1ecd4bc8c6138bab6683a011cbbecddf281263c3`，必须干净。
- Accepted Reviewer evidence 的唯一父为 Correction 2 `0f589aca501ea4559aeb7f4dd7aeab2a41f52b79`；原始 base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`。
- 完整 source Diff 只能为 `reporting.py`、`state.py`、`providers/obsidian.py`、`templates/weekly.md`、两份既定 tests 和 `handoffs/TASK-011.md`；无 fixtures 变更可接受。依赖/锁不得变化。

## 前置门禁

1. 核验 main/source 分支、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、source/main 初始洁净度、accepted verdict、handoff-only review evidence 与全范围。
2. 重跑：`uv lock --check`、`uv sync --locked`、两个周报 focused pytest、full pytest、mypy、Ruff、CLI help、`uv build --offline`；核验 sdist/wheel 包含 migration SQL、video/weekly templates。
3. 验证无依赖/锁/Schema/migration/`complete_stage`/CLI/TASK-012 异常，`git diff --check`、敏感字面量扫描和五轴/ADR-010 W-01..W-08/AC 证据。只允许 pytest 临时 SQLite/Vault，不得运行真实 Vault、网络、Provider/云调用、模型、凭据或外部文件操作。

## 整合与收尾

1. 合并前只读复核 source 产品 Diff 的精确范围和 `git diff --check`；index 必须为空。
2. 使用 `git merge --no-ff --no-commit 1ecd4bc8c6138bab6683a011cbbecddf281263c3`，复核合并后的 cached scope 与 `git diff --cached --check`；不得解决冲突或修改代码。若冲突或范围异常，终止并报告。
3. 创建双父 merge commit，第一父必须为 execution base，第二父为 accepted source；提交信息 `merge: integrate TASK-011 weekly report`。
4. 合并后复跑上述离线门禁，确认第一父差异精确为七个实际批准路径、依赖/锁未变、main/source 均干净。source branch/worktree 必须保留。
5. TASK-011 保持 `ACCEPTED`，不得自行写 DONE；TASK-012 继续 BLOCKED。不得 push 或清理。

## 回传格式

```text
Task: TASK-011
Role: Product Integrator
Execution base: <sha>
Source head: 1ecd4bc...
Merge commit: <sha>
Merge parents: <base>, <source>
Checks: <results>
Post-merge task status: ACCEPTED
Verdict: INTEGRATED | BLOCKED
```
