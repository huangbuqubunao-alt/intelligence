# TASK-009A — Codex Implementer (Correction 1)

你是原 TASK-009A Codex Implementer。只在 source worktree 修复首轮独立审查的一个 P1；不得合并、push、改 main/任务状态、启动 Reviewer 或扩大范围。

## 固定上下文

- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`
- Starting review evidence：`f73b28756c371d80fb7525bd7e4defb6b82b1a3c`
- Reviewed implementation：`75158be08d6442a7b18099f459654e9da86ebcee`
- Original base：`e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Main dynamic authorization：
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009A-CORRECTION-1-CODEX.md`
  必须解析为含 TASK-009A=`IN_PROGRESS` 的当前 main 提交。

source 中旧任务卡状态是固定快照；main 控制面和本包才是当前授权。若 source HEAD/父链、main 授权、范围或工作树不符，立即 `BLOCKED`。

## 唯一允许修改

1. `src/youtube_intel/domain.py`
2. `tests/unit/test_contracts.py`
3. `handoffs/TASK-009A.md`

不得修改 `pyproject.toml`、`uv.lock`、配置、Vault/文件/模板/Provider/Repository、Schema/migration、`state.py`、`complete_stage`、CLI 或任务/ADR/main。

## 必须实现

保持 ADR-009 N-02 的公开 `KnowledgeSink.upsert_video_note` keyword-only 参数和 `NoteRef` 返回类型不变，但把它从纯 Protocol 改为具执行边界的抽象基类：

1. 公共入口必须在委派前 fail-closed 验证 `processed_at` 是 UTC-aware、`pipeline_version` 非空且没有首尾空白、`scoring` 是最终可写的高价值 outcome（`final_should_summarize=false` 一律拒绝）。
2. `AnalysisCompleted` 和 `AnalysisSkipped` 都维持合法结构化输入；不得编造分析内容。
3. 成功后才调用受保护的 abstract 实现钩子；未来 Vault sink 实现该钩子，不能绕过公共校验入口。不要泄漏 Vault/用户内容，也不要在此任务实现 I/O。
4. 补完整正反测试：naive/非 UTC 时间、空/首尾空白版本、低价值评分、位置参数、合法 completed/skipped 分析和合法高价值路径；确认失败时受保护钩子零调用。

使用已有异常/验证语义，禁止新增 ErrorCode、依赖或旁路 API。接口变化需清楚记录在 handoff，说明为什么保持公开调用签名以符合 ADR-009。

## 必须验证

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check f73b28756c371d80fb7525bd7e4defb6b82b1a3c...HEAD
```

填写 handoff、复核 correction 仅三路径且完整产品范围仍为原五路径；创建范围明确、唯一父为 review evidence 的 commit，工作树干净后回传检查、Diff、风险与 SHA。真实 Vault、笔记、文件 I/O、云端和凭据继续不运行。
