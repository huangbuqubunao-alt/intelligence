# TASK-011 Correction 1 — Codex Implementer

你是原 TASK-011 Codex Implementer。只修复独立审查发现的 ADR-010 W-03 趋势聚合 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-CORRECTION-1-CODEX.md` 必须解析为本 Correction 1 控制面提交，且 main 中 TASK-011=`IN_PROGRESS`。
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report`。
- 起始 source HEAD：`3759d54a74abaa8e6627b8107298d0938fbe3441`，唯一父为 implementation `0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`；worktree 必须干净。
- 分配 base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；source 卡/状态为冻结快照，不得修改。

## 唯一允许修改

- `src/youtube_intel/reporting.py`
- `tests/unit/test_week_period.py`
- `tests/integration/test_weekly_report.py`
- `handoffs/TASK-011.md`

禁止 `state.py`、`providers/obsidian.py`、模板、fixtures、依赖/锁、共享契约、Schema/migration、`complete_stage`、CLI、TASK-012 或 main 变更。不要在 source 运行会写 `.codebase-memory/` 的索引动作。

## P1 与完成标准

实现 ADR-010 W-03：趋势、关键词和持续关注方向只从 verified `AnalysisResult`、`ScoreResult` 与受管 `NoteRef` 聚合；Analysis 是必要输入，不能回退为仅用 `ScoreResult.topics`。明确并测试文本规范化、稳定排序、频率/并列和空周；缺失、篡改或身份不匹配的 Analysis 必须 fail-closed，不产生误导趋势或继续写入。

保留 ISO 周窗口、候选资格、稳定 reports upsert、Jinja 固定模板、临时 Vault 原子写/DB 失败补偿和零 Provider/云调用。只使用 pytest 临时 SQLite/Vault，禁止真实 Vault、网络、模型、凭据或外部文件操作。

若现有冻结对象不能验证 Analysis 而必须扩展 public domain/state 契约，停止并报告 `DECISION NEEDED`；不得自行扩大范围。

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

完成后追加 handoff，创建单父提交（父必须是 `3759d54...`），记录复用、算法、测试、风险和未授权路径；不得启动 Reviewer 或改状态。
