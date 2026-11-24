# TASK-009 Correction 2 — Codex Implementer

你是原 TASK-009 Codex Implementer。只修复独立审查发现的 ADR-009 N-13 错误分类 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009-CORRECTION-2-CODEX.md` 必须解析为本 Correction 2 控制面提交，且 main 中 TASK-009=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes`。
- 起始 source HEAD：`f4a231b503ea6c1a25bf73c7d8aa584147cbdc03`，唯一父为 Correction 1 `60ed077452faf5fe41b105b21b4221f89cb6e02c`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`473119704c7638d7afd4e68d84d00e85064ceabd`。source 任务卡/项目状态的旧 `BLOCKED/UNASSIGNED` 是历史快照；不得修改它们。

## 唯一允许修改

- `src/youtube_intel/providers/obsidian.py`
- `tests/integration/test_obsidian_sink.py`
- `handoffs/TASK-009.md`

禁止 notes、模板、fixture、依赖/锁、共享契约、配置、`state.py`、Schema/migration、CLI、TASK-008 或 main 变更。不要在 source 运行会写入 `.codebase-memory/` 的索引动作。

## P1 与完成标准

Vault 操作的 `OSError` 映射必须满足 ADR-009 N-13：`EACCES`、`EPERM`、`EROFS` 安全映射至 `ErrorCode.PERMISSION_DENIED`；`ENOSPC`、`EDQUOT`、`EIO` 和无 errno 的 fsync/replace 资源失败保持 `ErrorCode.LOCAL_RESOURCE`。错误不得泄露绝对临时路径、用户内容或底层异常文本。

在 pytest 临时 Vault/SQLite 回归中，对 `EACCES`、`EPERM`、`EROFS` 与至少一个资源 errno 注入断言正确 ErrorCode、原文件不变、本次临时文件清理和 Pipeline/Job/Artifact 不提前完成。保留稳定 NoteRef、候选冲突、盘符、用户区、原子写、补账和低价值零写行为。

## 强制验证

运行任务卡全部离线命令：lock check、locked sync、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel template 与 migration inclusion、`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`。审查完整 diff；记录复用和未授权路径未运行。

所有 I/O 只能发生在 pytest 创建的临时 Vault/SQLite。严禁真实 Vault、用户笔记、测试目录外写入/删除/移动、真实 OpenAI/网络/云端/凭据/媒体或模型路径。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `f4a231b...`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
