# TASK-009A 首轮审查拒绝与 Correction 1 同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 TASK-009A 首轮 `REJECT` 与 Correction 1 控制面；不得实现、审查、安装依赖、运行 `uv`、pytest、mypy、Ruff、build、网络、Vault、数据库或产品命令，不得改 source、启动 Worker、合并、push 或清理。

## 固定事实

- main Required base：`7331e23381d68b1e601ca30e367989c704fbc0d2`
- Source review evidence：`f73b28756c371d80fb7525bd7e4defb6b82b1a3c`
- Reviewed implementation：`75158be08d6442a7b18099f459654e9da86ebcee`
- Source base：`e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Source worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`

## 唯一允许提交范围

仅以下五个主控预写 Markdown 文件：

1. `agent-prompts/TASK-009A-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-009A-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009A-obsidian-note-shared-contracts.md`

初始 main 必须在 Required base、暂存区为空且工作树只含上述五个预写变更。source 必须干净并固定在 review evidence；证据提交唯一父必须为 reviewed implementation，且只修改 source handoff。任何哈希变化、范围外/并发变更或链路不符均立即 `BLOCKED`；不得覆盖、取消暂存或清理。

## P1 与批准的 Correction 1

首轮 Reviewer `REJECT` 的唯一 P1：纯 `Protocol` 只约束签名，不能在调用边界 fail-closed 地拒绝 naive `processed_at`、首尾空白 `pipeline_version` 或低价值 `final_should_summarize=false` 的笔记写入。

产品负责人已批准以下修复，不修改 ADR-009 N-02 的公开 keyword-only 调用签名：

- 将 `KnowledgeSink` 升级为具公共验证入口的抽象基类；公开 `upsert_video_note(...)` 保持 N-02 现有参数/返回类型，先验证 UTC-aware `processed_at`、无首尾空白的非空 `pipeline_version` 和高价值评分资格。
- 校验成功后仅调用受保护抽象实现钩子；未来实际 Vault sink 只能实现该钩子，所有生产写入必经公共 fail-closed 边界。
- `AnalysisSkipped` 仍是合法的结构化输入；本 Correction 不实现 I/O、Vault、模板、Provider、Repository、Schema、`state.py`、`complete_stage` 或依赖变化。
- Correction source 仅允许 `src/youtube_intel/domain.py`、`tests/unit/test_contracts.py`、`handoffs/TASK-009A.md`。

main 控制面必须将 TASK-009A 改回 `IN_PROGRESS`，原 Codex Implementer 执行 Correction 1；Reviewer 已结束，尚未授权下一 Reviewer。TASK-008A 保持 DONE，TASK-008/TASK-009 及下游保持 BLOCKED/UNASSIGNED。

执行身份/分支/索引/source/范围、LF/EOF、尾随空白、`git diff --check`、暂存范围、`git diff --cached --check`、唯一父链、提交范围和 main/source 最终洁净度；不得运行产品命令。

全部通过后创建单父提交：

```text
docs: return TASK-009A for sink boundary correction
```
