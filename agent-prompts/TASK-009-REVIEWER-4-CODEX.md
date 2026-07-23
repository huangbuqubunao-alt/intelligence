# TASK-009 Correction 2 — 第四位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-009 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-009.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-REVIEWER-4-CODEX.md`；main 中 TASK-009 必须为 `IN_REVIEW`。
- Source/base：`/Users/hua/Documents/yia-worktrees/task-009` /
  `codex/task-009-obsidian-notes@22147b087157a6bbb0adc7e78f2f5d3eae700f8e` /
  `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Correction 2 的唯一父为 reviewer-3 evidence `f4a231b503ea6c1a25bf73c7d8aa584147cbdc03`；证据链继续回到 Correction 1 `60ed077...` 和 implementation `956e37...`。
- 完整允许范围：`notes.py`、`providers/obsidian.py`、`templates/video.md`、`tests/fixtures/notes/**`、
  `test_note_rendering.py`、`test_obsidian_sink.py`、`handoffs/TASK-009.md`。Correction 2 本身只可改 Obsidian Adapter、集成测试和 handoff。
- Source 卡和项目状态是固定 base 的历史快照；不得作为冲突或写回 source。TASK-008 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 TASK-009 source 运行会写入 `.codebase-memory/` 的索引动作；直接针对本包固定文件与 Git Diff 做窄范围只读审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff 和范围：Correction 2 只可改 `providers/obsidian.py`、`test_obsidian_sink.py` 和 handoff；禁止依赖/锁、公共契约、`state.py`、Schema/migration、CLI、云 Provider、TASK-008 或真实 Vault 变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、sdist/wheel template 与 migration SQL inclusion、固定 `git diff --check`。
3. 独立验证 ADR-009 N-13：在 pytest 临时 Vault/SQLite 中分别注入 `EACCES`、`EPERM`、`EROFS`，断言为 `ErrorCode.PERMISSION_DENIED`；注入 `ENOSPC` 以及 errno-less fsync、replace 失败，断言为 `ErrorCode.LOCAL_RESOURCE`。每个失败路径都须验证原托管笔记逐字节不变、仅本次临时文件被清理、Pipeline 保持 `ANALYSIS_READY`、Job 保持 `RUNNING`、且没有 `VIDEO_NOTE` Artifact；错误不得泄露绝对路径、用户内容或底层异常文本。
4. 复核 Correction 1 已关闭的稳定 NoteRef、非受管候选冲突、盘符、用户区、原子写、补账和低价值零写语义没有回归；不得只因新增回归通过而忽略完整任务卡范围。
5. 在 source handoff 追加 checks、独立探针、AC/ADR matrix、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。

## 资源边界

所有 I/O 只能发生在 pytest 创建的临时 Vault/SQLite。严禁真实 Vault、用户笔记、测试目录外写入/删除/移动、真实 OpenAI/网络/云端/凭据/媒体或模型路径。
