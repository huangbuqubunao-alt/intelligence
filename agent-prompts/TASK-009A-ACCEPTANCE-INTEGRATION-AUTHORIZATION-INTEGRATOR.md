# TASK-009A 验收与最终整合授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控预写的 TASK-009A 验收控制面和 Product Integrator 包；不得实现、审查、合并、运行产品命令、修改 source、push 或清理。

## 固定事实

- Required main base：`43489b61de78ae8b11f1aebcbdf4bd7a6f8a7a2c`
- Accepted source：`e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`
- Correction：`9ef4b2f63df65d09569ba119c6873805dcd9de17`
- Review evidence：`e30b40c7bfb388748ff1aee0420177f2ee6c2e2e` 的唯一父必须为 Correction，且只改 source handoff。
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`

## 唯一允许提交范围

1. `agent-prompts/TASK-009A-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-009A-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009A-obsidian-note-shared-contracts.md`

初始 main 必须在 Required base、暂存区为空、仅有以上五个预写 Markdown 变更；source 必须固定/干净。哈希变化、范围外变更、父链或范围不符立即 `BLOCKED`。

## 验收条件

- Correction 精确三路径、完整 `e427...e30` 为五批准路径，依赖/锁文件仅为原已批准的 Jinja2 基线。
- Reviewer `APPROVE`，P0–P3 均无；contracts `75`、全量 `327`、mypy、Ruff、CLI、locked sync、offline build、migration inclusion、KnowledgeSink/NoteRef 探针均 PASS。
- 控制面将 TASK-009A 标为 `ACCEPTED`，记录 source/review SHA；不得写 merge 或 DONE。
- Product Integrator 包固定 source、`--no-ff` merge、相应离线门禁、五路径 first-parent scope、无 Vault/file I/O/网络红线和整合后仍为 ACCEPTED。
- TASK-008A 维持 DONE；TASK-008/TASK-009 与下游继续 BLOCKED/UNASSIGNED。

核验身份、source、父链、范围、LF/EOF、两轮 SHA-256、Diff、暂存范围、cached Diff、提交父链和最终洁净度；不运行产品命令。全部通过后仅创建：

```text
docs: accept and authorize TASK-009A integration
```
