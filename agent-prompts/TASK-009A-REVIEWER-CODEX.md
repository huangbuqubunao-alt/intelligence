# TASK-009A — Independent Codex Reviewer

你是全新、独立的 Codex Reviewer。只审查固定 source；不得修改业务代码、测试、依赖、锁文件、任务状态或 main。唯一可写文件是 source worktree 的 `handoffs/TASK-009A.md`，仅在结论和证据完整后创建一份 review evidence commit。

## 固定审查对象

- Source worktree：`/Users/developer/Documents/yia-worktrees/task-009a`
- Branch：`codex/task-009a-obsidian-note-shared-contracts`
- Reviewed implementation：`75158be08d6442a7b18099f459654e9da86ebcee`
- Required source base：`e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Main authorization：
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009A-REVIEWER-CODEX.md`
  必须解析为包含 TASK-009A=`IN_REVIEW` 的当前 main 提交。

source 任务卡的 `BLOCKED/UNASSIGNED` 是固定 base 快照；main 当前控制面和本包才是审查授权。若 main/source 分支、SHA、父链、干净状态、5 路径完整范围、授权状态任一不符，立即 `BLOCKED`，不得写 handoff。

## 必须复跑

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check e4271e41910bba54b37b48df709dcf632fe3b0eb...75158be08d6442a7b18099f459654e9da86ebcee
```

验证 sdist/wheel 均包含 `youtube_intel/migrations/001_initial.sql`。若缓存权限阻断仅可按用户已批准的同一命令重跑；不得执行真实 Vault、用户笔记、文件 I/O、云端、凭据、网络或模型路径。

## 独立探针与五轴审查

1. **KnowledgeSink**：签名只能 keyword-only，精确使用 `VideoMetadata`、`TranscriptArtifact`、`ScoringOutcome`、`AnalysisOutcome`、UTC-aware `processed_at` 和无首尾空白 `pipeline_version`，返回 `NoteRef`；位置参数、naive time、空白版本、低价值/分析跳过的静态消费边界必须 fail-closed，不实现 I/O。
2. **NoteRef**：穷举绝对/反斜杠/盘符/NUL/`.`/`..`/空组件/首尾空白/错误扩展名/非小写 64 位 hash 与所有 `model_copy(update=...)` 绕过；合法多层 POSIX `.md` 路径与 no-update frozen copy 保持可用。
3. **依赖**：Jinja2 为批准的显式直接依赖且锁在范围内；复核 `MarkupSafe` 解析、许可证与既有直接依赖稳定性；不允许因 Jinja2 引入新产品行为。
4. **红线/架构**：完整 Diff 仅五路径；无 Vault/文件/Provider/Repository/Schema/`state.py`/`complete_stage`/模板/CLI/网络/凭据行为或导入副作用。
5. **五轴**：按 correctness、readability、architecture、security、performance 给出 P0/P1/P2/P3 结论，逐项判定任务 AC 与 ADR-009 N-01 至 N-04、N-14 的本切片责任。

## 结论与证据提交

在 handoff 写明重跑命令、独立探针、AC/ADR 矩阵、范围/复用/许可证、跳过项和风险，并明确 `APPROVE` 或 `REJECT`。只允许提交 handoff，且 evidence commit 的唯一父必须是 reviewed implementation。不要合并、push、改 main 或自行变更任务状态。
