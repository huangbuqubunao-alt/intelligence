# TASK-009A — Second Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 Correction 1 source，唯一可写文件是 source `handoffs/TASK-009A.md`；不得改业务代码、测试、依赖、锁文件、main、任务状态，不得合并/push/清理。

## 固定对象

- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`
- Reviewed correction：`9ef4b2f63df65d09569ba119c6873805dcd9de17`
- Required parent：`f73b28756c371d80fb7525bd7e4defb6b82b1a3c`
- Original base：`e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009A-REVIEWER-2-CODEX.md` 必须解析为当前 TASK-009A=`IN_REVIEW` 的 main 提交。

source 任务卡的旧状态是固定 base 快照；main 控制面和本包为当前授权。若 SHA、父链、清洁度、Correction 三路径、完整五路径范围或 main 授权不符，立即 `BLOCKED`。

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
git diff --check f73b28756c371d80fb7525bd7e4defb6b82b1a3c...9ef4b2f63df65d09569ba119c6873805dcd9de17
```

复核 sdist/wheel migration SQL 包含性。真实 Vault、笔记、任何文件 I/O、云端、凭据、网络和模型均不得运行。

## 强制独立探针

1. 使用最小 concrete 子类验证位置参数、naive 和非 UTC 时间、空/首尾空白版本、低价值评分均 fail-closed，受保护钩子调用计数为零。
2. 验证合法 UTC-aware 时间、clean pipeline version、高价值评分，以及 `AnalysisCompleted` 和 `AnalysisSkipped` 均恰好调用一次钩子并返回 `NoteRef`。
3. 检查 public `upsert_video_note` 的参数/返回形状仍精确符合 ADR-009 N-02；受保护 hook 不泄漏成替代公共 API，且没有通过直接调用绕过公共边界的项目生产调用路径。
4. 回归 NoteRef 安全、Jinja2/MarkupSafe 直接依赖与许可证、完整五路径/无 I/O 红线；按 correctness、readability、architecture、security、performance 给出 P0–P3、AC 与 ADR-009 N-01 至 N-04/N-14 矩阵。

只在 handoff 写审查证据并以 correction 为唯一父创建 evidence commit；明确 `APPROVE` 或 `REJECT`，不自行修复、变更任务状态或合并。
