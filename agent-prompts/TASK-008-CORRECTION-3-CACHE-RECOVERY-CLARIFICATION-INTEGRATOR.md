# TASK-008 Correction 3 缓存恢复语义澄清同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@cc7bb1670ca4c3efbb411be8c6057371422b3039`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`，必须干净且无未跟踪工件。
- Source evidence `b380a8c...` 的唯一父为 `71e1c249...`，且 evidence 只修改 `handoffs/TASK-008.md`；完整范围仍为七个批准路径组中的六个实际路径。

## 已确认的产品决定

ADR-008 A-12 与既有恢复测试优先：缓存命中绝不读取凭据、调用 transport、创建新的 ProviderCall 或 Artifact；但若当前 Job 尚未完成，可复用已成功且完全匹配的 Artifact/ProviderCall，调用既有 `complete_stage` 原子推进 `SCORED -> ANALYSIS_READY`。这属于恢复性状态完成，不是新的云端或 Provider 副作用。

关闭、低价值、token 超限、预算耗尽与缺凭据仍必须完全零状态副作用；缺凭据不得创建或失败化 ProviderCall。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-3-CACHE-RECOVERY-CLARIFICATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-THIRD-REVIEW-REJECT-CORRECTION-3-INTEGRATOR.md`
3. `agent-prompts/TASK-008-CORRECTION-3-CODEX.md`
4. `tasks/TASK-008-deep-analysis.md`

不得访问 TASK-009 source/worktree，也不得改任何产品文件、状态摘要、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree 和上述范围。
2. 准备文件仅限上述四个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. TASK-008 必须保持 `IN_PROGRESS`；不预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-009 不得触碰。
5. 提交信息：`docs: clarify TASK-008 cache recovery semantics`。提交后 main/source 必须干净；`git log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-3-CODEX.md` 必须解析为新提交。

## 回传格式

```text
Task: TASK-008 Correction 3 cache recovery clarification sync
Base / Head: <base> -> <head>
Committed files: <exact four>
Source/status: <source SHA>; clean; TASK-008=IN_PROGRESS
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
