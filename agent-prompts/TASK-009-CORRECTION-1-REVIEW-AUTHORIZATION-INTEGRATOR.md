# TASK-009 Correction 1 审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@2717609961e054001a0aef800f8c568c568b51ef`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes@60ed077452faf5fe41b105b21b4221f89cb6e02c`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Correction：`60ed077...` 唯一父为 reviewer-2 evidence `f778163dca83807f1baec5e568c4dbd734829171`；Correction 仅改 `notes.py`、`providers/obsidian.py`、`test_obsidian_sink.py` 与 `handoffs/TASK-009.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-009 七个批准路径组中的六个实际路径，无依赖/锁、共享契约、`state.py`、Schema/migration、CLI、TASK-008 改动。
- Source 的任务/项目状态为分配前冻结快照；实时状态只能以 main 本提交中 TASK-009=`IN_REVIEW` 为准。

## Correction 关闭目标

- Reviewer 2 evidence `f778163...` 为 `REJECT`：标题变化时不能恢复首次 NoteRef；同 video_id 非受管/多候选/NFC/casefold 冲突不 fail-closed；`vault_subdir="C:"` 未拒绝。
- Correction 自报以既有 VIDEO_NOTE Artifact 恢复首次稳定路径，写入/验证/补账前枚举候选并 fail-closed，拒绝盘符子目录；临时 Vault/SQLite 回归与全部离线检查均 PASS。
- 这些只是 Implementer 自报，必须由新 Reviewer 独立复跑；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。

## 唯一允许提交范围

1. `agent-prompts/TASK-009-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-009-REVIEWER-3-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009-obsidian-notes.md`

不得访问或修改 TASK-008 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、干净 index/worktree、Correction 四路径及完整范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 和精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-009 标为 `IN_REVIEW`，授权全新独立 Reviewer 3；TASK-008 必须保持 `IN_REVIEW` 且未触碰。
5. 提交信息：`docs: authorize TASK-009 note identity review`。提交后 main/source 必须干净，并确认 Reviewer 3 prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-009 Correction 1 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-009=IN_REVIEW
Committed files: <exact five>
Checks: <git-only gates>
TASK-008 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1/P2 verification / unauthorized paths>
```
