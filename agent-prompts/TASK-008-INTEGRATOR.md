# TASK-008 — Codex Product Integrator

你是全新的 Codex Product Integrator。只整合已验收的 TASK-008 source；不得修业务代码、修改 source、重写历史、推送或清理 worktree。任何范围、质量门禁或安全扫描失败均立即停止，不得在 merge 中修复。

## 固定对象

- Acceptance/execution base：main 最新提交必须由 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-INTEGRATOR.md` 解析为本授权提交。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@6914312eaac0e3d65f1d2895ea2e3c0c2c39f4d8`。
- Source review evidence：`6914312...` 唯一父为 `dcbbd38...`，只修改 handoff，Verdict=`APPROVE`、P0–P3=0。
- Original source base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整允许范围严格为：
  - `src/youtube_intel/analysis.py`
  - `src/youtube_intel/providers/cloud_llm.py`
  - `src/youtube_intel/prompts/summary.md`
  - `tests/unit/test_analysis_policy.py`
  - `tests/integration/test_summary_provider.py`
  - `handoffs/TASK-008.md`
- TASK-009 source/worktree 不得读取、修改、清理或等待。

## 合并前门禁

1. main/source 均干净；身份为 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。
2. 核验 source 父链、review handoff-only scope、完整六路径 source Diff、无依赖/锁/公共契约/config/`state.py`/Schema/migration/CLI/TASK-009 变更，并通过 `git diff --check`。
3. 在 main 暂存 source 的精确六路径产品差异，先执行 `git diff --cached --check` 与范围检查；然后以 `--no-ff` 合并固定 source。不得 fast-forward、cherry-pick、rebase 或手动改冲突。

## 必须复跑的离线门禁

- `uv lock --check`
- `uv sync --locked`
- `uv run python -m pytest tests/unit/test_analysis_policy.py`
- `uv run python -m pytest tests/integration/test_summary_provider.py`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`
- 核验 sdist/wheel 均包含 `youtube_intel/migrations/001_initial.sql`、`youtube_intel/prompts/summary.md` 与固定 `o200k_base.tiktoken`（大小 `3,613,922`、SHA-256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`）。

构建产物若已忽略，只可精确清理本轮产生的 `dist/` 文件，不能清理预存用户文件。验证 first-parent Diff 精确六路径、merge 有正确两个父提交且 source 成为 main 祖先。无测试或构建凭据、真实 API、网络、Vault、用户内容或其他未授权资源。

## 交付

回报 merge SHA、两个父提交、范围和各门禁结果。TASK-008 保持 `ACCEPTED`，不得自行改为 `DONE`；source branch/worktree 必须保留且干净。不得 push、清理 source 或改 TASK-009。
