# TASK-011 Correction 2 — Codex Implementer

你是原 TASK-011 Codex Implementer。只修复独立审查发现的受管视频 NoteRef 完整性 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-CORRECTION-2-CODEX.md` 必须解析为本 Correction 2 控制面提交，且 main 中 TASK-011=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-011` / `codex/task-011-weekly-report`。
- 起始 source HEAD：`6f9c75df90e10b964b36dbcefc52618422d83216`，唯一父为 Correction 1 `f4e30a56ddcf7d654bda4e0579f6080af59698f5`；worktree 必须干净。
- 分配 base：`44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；source 卡/状态为冻结快照，不得修改。

## 唯一允许修改

- `src/youtube_intel/reporting.py`
- `tests/unit/test_week_period.py`
- `tests/integration/test_weekly_report.py`
- `handoffs/TASK-011.md`

禁止 `state.py`、`providers/obsidian.py`、模板、fixtures、依赖/锁、共享契约、Schema/migration、`complete_stage`、CLI、TASK-012 或 main 变更。不要在 source 运行会写 `.codebase-memory/` 的索引动作。

## P1 与完成标准

在调用 Knowledge Sink 或 reports upsert 前，验证每一个候选的受管视频 NoteRef：路径必须相对并锚定在 pytest Vault，拒绝 symlink、路径逃逸与非普通文件；文件须存在，内容 SHA-256 须与受管 Artifact/NoteRef identity 一致，video/provenance 不匹配亦须拒绝。任意缺失、篡改或不匹配都必须 fail-closed，且零周报 Vault/reports 写入。

补充 pytest `tmp_path` 最小 Vault 的缺失、篡改、symlink/逃逸与 identity mismatch 回归；保留 verified Analysis-only 趋势聚合、ISO 周窗口、候选资格、稳定 reports upsert、固定模板、临时 Vault 原子写/DB 失败补偿和零 Provider/云调用。不得访问真实 Vault、网络、模型、凭据或测试目录外文件。

若现有冻结对象不能同时验证文件与 identity 而必须扩展 public domain/state 契约，停止并报告 `DECISION NEEDED`；不得自行扩大范围。

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

完成后追加 handoff，创建单父提交（父必须是 `6f9c75d...`），记录复用、验证策略、测试、风险和未授权路径；不得启动 Reviewer 或改状态。
