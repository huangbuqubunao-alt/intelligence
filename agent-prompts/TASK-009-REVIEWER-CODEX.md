# TASK-009 — Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-009 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-009.md`。冲突、范围异常、未授权资源路径或任何 P0/P1 立即 `REJECT` 并停止。

source worktree 固定在分配前 base，因此其中的 `tasks/` 与 `docs/PROJECT_STATUS.md` 显示旧 `BLOCKED/UNASSIGNED` 是历史快照；实时审查状态只能以本包动态解析的 main commit 中 TASK-009=`IN_REVIEW` 为准。不得把该快照当作冲突，也不得更新 source 的任务状态文档。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-REVIEWER-CODEX.md`
- Source/base：`/Users/hua/Documents/yia-worktrees/task-009` /
  `codex/task-009-obsidian-notes@956e37a15ab29106f16c45873fccb813cc5a959f` /
  `473119704c7638d7afd4e68d84d00e85064ceabd`
- Full allowed scope：`notes.py`、`providers/obsidian.py`、`templates/video.md`、`tests/fixtures/notes/**`、
  `test_note_rendering.py`、`test_obsidian_sink.py`、`handoffs/TASK-009.md`。

## 强制审查

1. 核验 source 分支/HEAD/唯一父/cleanliness、main 授权状态和完整 Diff；禁止范围外、依赖/锁、公共契约、Schema/state/CLI/cloud Provider/TASK-008 改动。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、template 与 migration SQL package inclusion、固定 `git diff --check`。
3. 独立探针必须覆盖：
   - A：低价值零写；completed/skipped analysis 的稳定 frontmatter/正文；StrictUndefined、资源上限与不可信内容安全渲染。
   - B：安全 filename/relative NoteRef、Unicode/保留名/casefold 冲突、路径穿越、symlink、目录替换、legacy/malformed marker/invalid UTF-8 全部 fail-closed，原文件不变且诊断不泄漏绝对路径。
   - C：用户 `我的思考` 区在合法重排中逐字节保留；无变化/已完成普通重排零替换；标题变化不自动 rename/delete。
   - D：仅用测试临时 Vault 与真实临时 SQLite，验证同目录临时文件、short-write/fsync/replace 失败、replace 后 SQLite 失败补账、VIDEO_NOTE Artifact/Pipeline/Job 原子性与恢复；测试目录外、真实 Vault/用户笔记/外部文件不得读写或删除。
   - E：N-01 至 N-15、AC、五轴、复用/许可证和范围审查；无凭据、云端、网络或模型路径。
4. 在 source handoff 写 checks、探针、AC/ADR matrix、P0–P3、skipped/risks、`APPROVE` 或 `REJECT`；单独提交该 handoff。不得改 task state、merge、push 或清理。
