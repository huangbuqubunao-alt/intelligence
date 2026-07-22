# TASK-009 Correction 1 — Codex Implementer

你是原 TASK-009 Codex Implementer。只修复独立审查发现的两个 P1 和一个 P2；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-CORRECTION-1-CODEX.md` 必须解析为本 Correction 1 控制面提交，且 main 中 TASK-009=`IN_PROGRESS`。
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes`。
- 起始 source HEAD：`f778163dca83807f1baec5e568c4dbd734829171`，唯一父为 first-review evidence `d16498fe2a1939c6bec7babd03039e623782d027`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/notes.py`
- `src/youtube_intel/providers/obsidian.py`
- `tests/unit/test_note_rendering.py`
- `tests/integration/test_obsidian_sink.py`
- `handoffs/TASK-009.md`

禁止模板、fixture、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-008 或 main 变更。不要在 source 运行会写入 `.codebase-memory/` 的索引动作。

## P1/P2 与完成标准

1. 同一 video_id 的首次稳定受管 NoteRef 必须在普通已完成重排和标题变化时被恢复/验证，返回同一首次路径并零改写；不得依当前标题重派生而失败或改名。
2. 在写入、替换或补账前，必须按 video_id 检测全部候选；多候选、NFC/casefold 冲突和非受管占位都必须 fail-closed，且不得创建第二份、重命名、删除、移动或接管任何已有笔记。
3. `vault_subdir` 必须拒绝盘符样式（包括 `C:`）及既有非法路径边界。

用临时 Vault/SQLite 回归覆盖：首次写入后标题变化的普通重排、非受管 `--<video_id>.md` 候选、多个候选/NFC/casefold 冲突、`C:`；失败路径确认原文件逐字节不变、零新文件、无外部路径操作。若现有批准契约无法恢复首次路径，不得臆造 Schema/Repository 方法，报告 `DECISION NEEDED`。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel template 与 migration inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查所有完整 diff；记录复用和未授权路径未运行。

所有 I/O 只能发生在 pytest 创建的临时 Vault/SQLite。严禁真实 Vault、用户笔记、测试目录外写入/删除/移动、真实 OpenAI/网络/云端/凭据/媒体或模型路径。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `f778163...`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
