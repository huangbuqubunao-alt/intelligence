# TASK-013 — Codex Implementer (Correction 1: real service-flow evidence)

你是原 TASK-013 Codex Implementer。修正独立审查发现的验收证据缺口：让离线 E2E 真实经过各服务边界，并让报告提供可复现的秘密扫描证据。不得改生产代码、CLI/production composition、依赖、锁文件、配置、Schema/migration、测试配置、既有测试、任务状态或真实资源边界。

## 固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-CORRECTION-1-CODEX.md` 必须解析为本 Correction 控制面提交，且 main 中 TASK-013=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance`；starting evidence 必须为 `2afd95a8dde9ae2d907480fd190bcb2c54efccb4`，唯一父提交为 `fd22c8ced0343a38e4cb8acdde0ef608bc6d8708`，worktree 必须干净。

## 唯一允许修改

- `tests/e2e/test_mvp_flow.py`
- `tests/e2e/test_failure_recovery.py`
- `tests/e2e/fixtures/**`
- `docs/ACCEPTANCE_REPORT.md`
- `handoffs/TASK-013.md`

## 必须关闭的发现

### P1：真实服务路径，而非直接状态写入

- 每个五类场景必须在测试内通过既有的字幕选择/读取、转写、评分、云分析、笔记/周报服务与真实临时 SQLite Repository；允许固定 Fake Adapter/executor/transport，但不得以通用 handler、手写 `complete_stage` 或直接数据库状态推进替代这些服务。
- 字幕、Whisper、评分、云分析、笔记写入的失败注入必须分别命中对应服务边界与可区分的阶段；恢复路径要证明成功的昂贵步骤经真实 ProviderCall/Artifact 缓存复用，不重复调用 Fake。
- 保持测试内 composition；不得修改当前 CLI 的 `_UnavailableOperations` 安全默认值或增加生产 composition。

### P2：PRD 10.7 的可复现隐私证据

- 在 `docs/ACCEPTANCE_REPORT.md` 与 handoff 记录一个可复现、只读、仓库范围的秘密扫描命令、执行结果和对既有合成测试 sentinel 的精确处理。不得把未执行扫描写为 PASS；若不能可靠执行，标为 FAIL/PARTIAL 并报告。
- 继续明确日志/报告中不含真实字幕全文、真实凭据或 Provider 原始响应；真实冒烟仍只能写为 `NOT AUTHORIZED`。

## 强制验证

- `uv lock --check`
- `uv sync --locked --offline`（缓存缺失即停止报告，不得联网）
- `uv run python -m pytest tests/e2e -m 'not network and not cloud'`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`
- 修正后执行并记录仓库范围的只读秘密扫描
- `git diff --check 9462b6a162a1e9a738b4073fa5e8b2252101f6af...HEAD`

完成后追加 handoff，给出 P1/P2 的 RED/GREEN 证据、五类用户结果、五个失败阶段、重跑幂等、真实资源未授权声明、复用/许可证与剩余风险。创建单父提交，父必须为 `2afd95a8dde9ae2d907480fd190bcb2c54efccb4`；不得启动 Reviewer 或改状态。
