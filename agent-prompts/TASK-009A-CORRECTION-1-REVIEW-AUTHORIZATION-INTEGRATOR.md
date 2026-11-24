# TASK-009A Correction 1 审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 TASK-009A Correction 1 独立审查授权控制面；不得实现、审查、安装依赖、运行产品命令、修改 source、启动 Reviewer、合并、push 或清理。

## 固定事实

- main Required base：`c5f74d5b5ab97a69b6dbececc9af76d7aabca32b`
- Source correction：`9ef4b2f63df65d09569ba119c6873805dcd9de17`
- Source parent/review evidence：`f73b28756c371d80fb7525bd7e4defb6b82b1a3c`
- Original implementation/base：`75158be08d6442a7b18099f459654e9da86ebcee` / `e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Source worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`

## 唯一允许提交范围

仅以下五个预写 Markdown 文件：

1. `agent-prompts/TASK-009A-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-009A-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009A-obsidian-note-shared-contracts.md`

main 初始必须位于 Required base、暂存区为空且只有该五文件未提交变更；source 必须干净且固定在 correction SHA。准备哈希变化、范围外变更、源父链/范围不符均立即 `BLOCKED`。

## 必须核验

1. Correction 只有 `domain.py`、`test_contracts.py`、source handoff 三路径，唯一父为首轮 review evidence；完整 `e427...HEAD` 仍精确为原五路径，依赖/锁文件没有更新。
2. P1 修复保持 ADR-009 N-02 keyword-only 公开签名与 `NoteRef` 返回类型不变，公共抽象基类入口在委派前验证 UTC-aware 时间、无首尾空白非空版本与高价值评分，成功后才调用受保护抽象钩子；`AnalysisCompleted`/`AnalysisSkipped` 都可作为合法结构化输入。
3. main 仅改为 `IN_REVIEW`，固定 correction SHA，授权全新独立 Codex Reviewer 2；不得预写 APPROVE、ACCEPTED、merge 或 DONE。
4. TASK-008A 保持 DONE；TASK-008/TASK-009 及下游保持 BLOCKED/UNASSIGNED；真实 Vault/文件 I/O/云端/凭据继续未授权。

执行身份、索引、source、父链、范围、LF/EOF、尾随空白、Diff、五文件双轮 SHA-256、暂存范围、cached Diff、提交范围/父链与最终洁净度；不得运行产品命令。

仅当全部通过时创建：

```text
docs: authorize TASK-009A correction review
```
