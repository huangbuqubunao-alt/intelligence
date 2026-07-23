# TASK-009 — Codex Product Integrator

你是全新的 Codex Product Integrator。只整合已验收的 TASK-009 source；不得修业务代码、修改 source、重写历史、推送或清理 worktree。任何范围、质量门禁或安全扫描失败均立即停止，不得在 merge 中修复。

## 固定对象

- Acceptance/execution base：main 最新提交必须由 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-INTEGRATOR.md` 解析为本授权提交。
- Source：`/Users/hua/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes@e675feef7f12d19561f1ca439e181a47f4a521b8`。
- Source review evidence：`e675feef...` 唯一父为 Correction 2 `22147b087157a6bbb0adc7e78f2f5d3eae700f8e`，且只修改 source handoff，Verdict=`APPROVE`、P0–P3=0。
- Original source base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整允许范围严格为：
  - `src/youtube_intel/notes.py`
  - `src/youtube_intel/providers/obsidian.py`
  - `src/youtube_intel/templates/video.md`
  - `tests/fixtures/notes/**`
  - `tests/unit/test_note_rendering.py`
  - `tests/integration/test_obsidian_sink.py`
  - `handoffs/TASK-009.md`
- TASK-008 source/worktree 不得读取、修改、清理或等待。

## 合并前门禁

1. main/source 均干净；身份为 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。
2. 核验 source 父链、review handoff-only scope、完整七路径 source Diff、无依赖/锁/公共契约/config/`state.py`/Schema/migration/CLI/TASK-008 变更，并通过 `git diff --check`。
3. 以 `--no-ff` 合并固定 source。不得 fast-forward、cherry-pick、rebase 或手动改冲突。合并内容必须只包含上述七个允许路径；在创建 merge commit 前运行 `git diff --cached --check` 和范围检查。

## 必须复跑的离线门禁

- `uv lock --check`
- `uv sync --locked`
- `uv run python -m pytest tests/unit/test_note_rendering.py`
- `uv run python -m pytest tests/integration/test_obsidian_sink.py`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`
- 核验 sdist/wheel 均包含 `youtube_intel/templates/video.md` 与 `youtube_intel/migrations/001_initial.sql`。

构建产物若已忽略，只可精确清理本轮产生的 `dist/` 文件，不能清理预存用户文件。验证 first-parent Diff 精确七路径、merge 有正确两个父提交且 source 成为 main 祖先。所有文件 I/O 只限于已批准的测试临时 Vault/SQLite；不得访问真实 Vault、用户笔记、网络、云端、凭据、媒体或模型。

## 交付

回报 merge SHA、两个父提交、范围和各门禁结果。TASK-009 保持 `ACCEPTED`，不得自行改为 `DONE`；source branch/worktree 必须保留且干净。不得 push、清理 source 或改 TASK-008。
