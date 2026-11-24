# TASK-009A — Product Integrator

你是全新的 Codex Product Integrator。只整合已 `ACCEPTED` 的 TASK-009A source；不得实现、修复、重构、改任务状态、push 或清理 source。冲突、范围或门禁不符立即停止。

## 固定对象

- Main：`/Users/developer/Documents/youtubek agent` / `main`
- Dynamic execution base：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009A-INTEGRATOR.md`
- Accepted source：`e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`
- Correction implementation：`9ef4b2f63df65d09569ba119c6873805dcd9de17`
- Source worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`

main/source 必须干净，TASK-009A 必须为 ACCEPTED，source 必须为 accepted head。先验证 review evidence 只改 handoff、Correction 三路径、完整 source 相对 `e4271e41910bba54b37b48df709dcf632fe3b0eb` 精确为：`domain.py`、`tests/unit/test_contracts.py`、`pyproject.toml`、`uv.lock`、`handoffs/TASK-009A.md`。

使用 `git merge --no-ff --no-commit e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`；禁止冲突修复。暂存后运行：

```bash
git diff --cached --check
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
```

验证 sdist/wheel migration SQL；审计 Jinja2 直接依赖、MarkupSafe、无既有直接依赖升级及无 Vault/文件/Provider/Repository/Schema/template/network/credential 行为。合并提交后 first-parent Diff 必须精确为五路径。任务仍为 ACCEPTED，不得 DONE 或解锁 TASK-008/TASK-009；保留 source worktree/branch，未 push。
