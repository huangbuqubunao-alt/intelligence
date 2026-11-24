# TASK-009 第三轮审查拒绝与 Correction 2 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@bafe9636002af92d92583c1c423808a89db7386b`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes@f4a231b503ea6c1a25bf73c7d8aa584147cbdc03`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer-3 evidence：`f4a231b...` 唯一父为 Correction 1 `60ed077452faf5fe41b105b21b4221f89cb6e02c`；evidence 只改 `handoffs/TASK-009.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-009 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查拒绝事实

- Verdict=`REJECT`；P0=0、P1=1。
- P1：`obsidian.py` 将所有 Vault `OSError` 统一映射为 `LOCAL_RESOURCE`。ADR-009 N-13 要求 `EACCES`、`EPERM`、`EROFS` 映射为 `PERMISSION_DENIED`；仅 `ENOSPC`、`EDQUOT`、`EIO`、fsync/replace 等资源失败保持 `LOCAL_RESOURCE`。
- Reviewer 3 的 lock/sync、focused `4/12`、full pytest `343`、mypy、Ruff、CLI、offline build、template/migration package inclusion 均 PASS；P1 后扩展探针停止，不得表述为通过。

## 唯一允许提交范围

1. `agent-prompts/TASK-009-THIRD-REVIEW-REJECT-CORRECTION-2-INTEGRATOR.md`
2. `agent-prompts/TASK-009-CORRECTION-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009-obsidian-notes.md`

不得访问或修改 TASK-008 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、evidence 单文件范围和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-009 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 2；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-008 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: return TASK-009 for permission error correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 2 边界

- 只授权 source `providers/obsidian.py`、`tests/integration/test_obsidian_sink.py` 和 `handoffs/TASK-009.md`。
- 必须以 errno-aware 且安全脱敏的方式将 `EACCES`、`EPERM`、`EROFS` 映射到 `PERMISSION_DENIED`，将 `ENOSPC`、`EDQUOT`、`EIO`、fsync/replace 等资源失败保持 `LOCAL_RESOURCE`；不得改变已有的非 OSError 映射、路径边界、原子写、Artifact/Pipeline/Job 语义或公共契约。
- 必须在 pytest 临时 Vault 中加入 `EACCES`、`EPERM`、`EROFS` 和代表性资源 errno 回归；不得触碰真实 Vault 或测试目录外文件。
- 不得新增 Schema/migration/Repository 方法、依赖/锁、公共契约、配置、CLI 或真实网络/云端/凭据/媒体/模型路径。

## 回传格式

```text
Task: TASK-009 third review reject / Correction 2 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-009=IN_PROGRESS
Committed files: <exact five>
Checks: <git-only gates>
TASK-008 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 / unauthorized paths>
```
