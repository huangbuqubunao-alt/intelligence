# TASK-009 Correction 1 — 第三位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-009 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-009.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-REVIEWER-3-CODEX.md`；main 中 TASK-009 必须为 `IN_REVIEW`。
- Source/base：`/Users/hua/Documents/yia-worktrees/task-009` /
  `codex/task-009-obsidian-notes@60ed077452faf5fe41b105b21b4221f89cb6e02c` /
  `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Correction 唯一父为 reviewer-2 evidence `f778163...`，其证据链继续回到 implementation `956e37...`。
- 完整允许范围：`notes.py`、`providers/obsidian.py`、`templates/video.md`、`tests/fixtures/notes/**`、
  `test_note_rendering.py`、`test_obsidian_sink.py`、`handoffs/TASK-009.md`。
- Source 卡和项目状态是固定 base 的历史 `BLOCKED/UNASSIGNED` 快照；不得作为冲突或写回 source。TASK-008 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 TASK-009 source 运行会写入 `.codebase-memory/` 的索引动作；直接针对本包固定文件与 Git Diff 做窄范围只读审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff 和范围：Correction 只可改 `notes.py`、Obsidian Adapter、集成测试和 handoff；禁止依赖/锁、公共契约、`state.py`、Schema/migration、CLI、云 Provider、TASK-008 或真实 Vault 变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、sdist/wheel template 与 migration SQL inclusion、固定 `git diff --check`。
3. 独立探针：
   - A：首次成功后标题变化的普通重排必须返回首次 NoteRef、零 replace、零新文件；成功 `NOTE_WRITTEN`/`COMPLETE` 重排也零改写。
   - B：写入、验证和补账前，同 video_id 的非受管候选、多候选、NFC/casefold 冲突均 fail-closed，原文件逐字节不变、零新文件、不得接管/删除/重命名/移动任何既有笔记。
   - C：`vault_subdir="C:"` 及盘符、Unicode/保留名、穿越、symlink/目录替换/legacy/marker/非法 UTF-8 均安全拒绝且不泄露绝对路径。
   - D：低价值零写、completed/skipped、frontmatter/StrictUndefined/资源上限、用户 `我的思考` 字节保留、无变化零 replace。
   - E：仅临时 Vault/SQLite 中验证短写/fsync/replace、补账、Artifact/Pipeline/Job 原子性/回滚；ADR-009 N-01 至 N-15、AC、五轴、复用/许可证和范围；无真实 Vault/用户笔记/网络/云端/凭据/模型或测试目录外 I/O。
4. 在 source handoff 追加 checks、探针、AC/ADR matrix、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。
