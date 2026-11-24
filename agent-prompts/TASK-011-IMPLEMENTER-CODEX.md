# TASK-011 — Codex Implementer

你是 TASK-011 的唯一 Codex Implementer。实现 ADR-010 的确定性周报服务；不得改 main、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-IMPLEMENTER-CODEX.md` 必须解析为本 assignment 控制面提交，且 main 中 TASK-011=`IN_PROGRESS`、Assignee=`Codex`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report`。
- 起始 source base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；worktree 必须干净。source 中的 `READY/UNASSIGNED` 为冻结 base 快照，不得修改。

## 唯一允许修改

- `src/youtube_intel/reporting.py`
- `src/youtube_intel/state.py`（仅新增只读周报候选查询；不得改 Schema/migration/`complete_stage` 或既有 Repository 语义）
- `src/youtube_intel/providers/obsidian.py`
- `src/youtube_intel/templates/weekly.md`
- `tests/unit/test_week_period.py`
- `tests/integration/test_weekly_report.py`
- `tests/fixtures/weekly/**`
- `handoffs/TASK-011.md`

禁止新增依赖/锁、配置/公共领域契约、CLI、TASK-012、Schema/migration、真实 Vault/用户笔记、云调用、网络、媒体、凭据和测试目录外删除。不要在 source 运行会写 `.codebase-memory/` 的索引动作。

## 完成标准

实现 ADR-010 W-01 至 W-08：completed_at 的配置时区 ISO 周边界、跨年 `Weekly/YYYY-Www.md`、COMPLETE/高价值/受管 NoteRef 候选、`score DESC/video_id ASC`、Top N 与确定性关键词/趋势/持续关注方向、空周稳定报告、既有 reports 唯一 upsert、包内 Jinja2 ImmutableSandboxedEnvironment + StrictUndefined 模板。

周报不是 `video_id=None` Job；直接复用 reports upsert、受控 Repository 查询和 Knowledge Sink 周报 upsert。只在 pytest 临时最小 Vault 中测试锚定根目录、相对路径、无 symlink、同目录临时文件、fsync/replace、重复运行与崩溃补偿；不得访问真实 Vault。趋势只读取验证的 Analysis/Score/NoteRef，不得调用任何模型或 Provider。

## 强制验证

- `uv lock --check`
- `uv sync --locked`
- `uv run python -m pytest tests/unit/test_week_period.py`
- `uv run python -m pytest tests/integration/test_weekly_report.py`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`，核验 sdist/wheel 含 migration SQL、video/weekly templates
- `git diff --check 44fc64be2cb4602cb93c1d03f84d6dd2a1677750...HEAD`

完成后追加 handoff，创建单父提交（父必须是固定 base），记录复用、许可证、实际临时 Vault I/O、检查、风险和未授权路径；不得启动 Reviewer 或改状态。
