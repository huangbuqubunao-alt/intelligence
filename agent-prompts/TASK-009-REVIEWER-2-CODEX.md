# TASK-009 — 第二位独立 Codex Reviewer（清理后复审）

你是全新独立 Codex Reviewer。只审查 TASK-009 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-009.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-REVIEWER-2-CODEX.md`；main 中 TASK-009 必须为 `IN_REVIEW`。
- Source/base：`/Users/hua/Documents/yia-worktrees/task-009` /
  `codex/task-009-obsidian-notes@d16498fe2a1939c6bec7babd03039e623782d027` /
  `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Source head 的唯一父为 implementation `956e37a15ab29106f16c45873fccb813cc5a959f`；首轮 evidence 仅追加 handoff。
- 完整允许范围：`notes.py`、`providers/obsidian.py`、`templates/video.md`、`tests/fixtures/notes/**`、
  `test_note_rendering.py`、`test_obsidian_sink.py`、`handoffs/TASK-009.md`。
- Source 卡和项目状态是固定 base 的历史 `BLOCKED/UNASSIGNED` 快照；不得作为冲突或写回 source。TASK-008 source 不得读取、修改或清理。

## 清理前置门禁

首轮审查只因范围外未跟踪 `.codebase-memory/` 索引工件拒绝。产品负责人已授权删除这三个生成文件，并已执行。审查开始时 `git status --short --untracked-files=all` 必须无输出；若仍出现 `.codebase-memory/` 或其他工件，立即 `REJECT`，不自行清理。

为避免重现同一范围错误，不得在 TASK-009 source 运行会写入 `.codebase-memory/` 的代码索引动作；直接针对本包已固定的文件和 Git Diff 进行窄范围只读审查即可。

## 强制审查

1. 核验 main/source HEAD、父链、洁净度、完整 Diff 和范围；禁止依赖/锁、公共契约、`state.py`、Schema/migration、CLI、云 Provider、TASK-008 或真实 Vault 变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、sdist/wheel 的 template 与 migration SQL inclusion、固定 `git diff --check`。
3. 独立探针：
   - A：低价值零写、completed/skipped analysis、frontmatter/StrictUndefined/资源上限与不可信文本。
   - B：Unicode/保留名/casefold/穿越、symlink/目录替换/legacy/marker/非法 UTF-8 全部 fail-closed；原文件不变且异常不泄露绝对路径。
   - C：`我的思考` 区逐字节保留、无变化重排不 replace、成功 `NOTE_WRITTEN`/`COMPLETE` 重排零改写、标题变化不改名。
   - D：仅测试临时 Vault 与临时 SQLite 内验证同目录临时文件、短写/fsync/replace 失败、补账恢复、Artifact/Pipeline/Job 原子性和回滚；不得接触真实 Vault 或测试目录外文件。
   - E：ADR-009 N-01 至 N-15、AC、五轴、复用/许可证和范围；无 Vault/用户笔记/网络/云端/凭据/模型路径。
4. 在 source handoff 追加 checks、探针、AC/ADR matrix、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。
