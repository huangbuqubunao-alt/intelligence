# TASK-009 第二轮审查拒绝与 Correction 1 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理任何 worktree。

## 固定对象

- Main base：`main@8c9f266da1eac00f39789f56062f5de6816065cf`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes@f778163dca83807f1baec5e568c4dbd734829171`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Reviewer 2 evidence：`f778163...` 唯一父必须为 first-review evidence `d16498fe2a1939c6bec7babd03039e623782d027`，其唯一父为 implementation `956e37a15ab29106f16c45873fccb813cc5a959f`；evidence 只改 `handoffs/TASK-009.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-009 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 审查拒绝事实

- Verdict=`REJECT`；P0=0、P1=2、P2=1。
- P1：标题变化时重新从标题派生路径，已完成笔记普通重排找不到首次路径而失败；同一 video_id 的非受管候选未拒绝，仍创建第二份笔记。违反 ADR-009 N-03/N-05 的稳定一对一身份与 fail-closed 冲突。
- P2：`vault_subdir="C:"` 未被拒绝，违反 ADR-009 N-06 盘符约束。
- P1 后 Reviewer 按工作包停止：package archive inclusion 和其余扩展探针不得写为通过。

## 唯一允许提交范围

1. `agent-prompts/TASK-009-SECOND-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-009-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009-obsidian-notes.md`

不得访问或修改 TASK-008 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、evidence 单文件范围和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-009 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 1；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-008 必须保持 `IN_REVIEW` 且未触碰。
5. 提交信息：`docs: return TASK-009 for note identity correction`。提交后 main/source 必须干净，并确认 Correction prompt 的动态授权解析为本提交。

## Correction 1 边界

- 只授权 source `notes.py`、`providers/obsidian.py`、两份既有 note 测试和 `handoffs/TASK-009.md`。
- 必须以既有批准契约/Artifact/NoteRef 语义恢复或验证首次稳定路径；在写入或补账前按 video_id 检测所有候选，并对多候选、NFC/casefold 冲突与任何非受管占位 fail-closed。不得通过重命名、删除、移动或接管既有笔记规避冲突。
- 普通已完成重排在标题变化时必须返回首次 NoteRef、零改写；`vault_subdir` 必须拒绝盘符（含 `C:`）及既有路径边界非法值。
- 不得新增 Schema/migration/Repository 方法、依赖/锁、公共契约、CLI 或真实 Vault/用户笔记/测试目录外 I/O。若现有契约不足以保存或恢复稳定路径，必须 `DECISION NEEDED`。

## 回传格式

```text
Task: TASK-009 second review reject / Correction 1 sync
Base / Head: <base> -> <head>
Source/evidence/status: <chain>; TASK-009=IN_PROGRESS
Committed files: <exact five>
Checks: <git-only gates>
TASK-008 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1/P2 / unauthorized paths>
```
