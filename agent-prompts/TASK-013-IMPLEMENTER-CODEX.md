# TASK-013 — Codex Implementer (offline acceptance only)

你是 TASK-013 的唯一 Codex Implementer。目标是用固定夹具和临时目录，证明五种用户情形从输入到知识产物的离线体验及可恢复性；只写测试、验收报告和交接证据。不得把测试便利性带入生产代码，不得自行合并、推送或改 main 任务状态。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-IMPLEMENTER-CODEX.md` 必须解析为本分配控制面提交，且 main 中 TASK-013=`IN_PROGRESS`、Assignee=`Codex`。
- Worktree/branch/base：`/Users/developer/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance` / `9462b6a162a1e9a738b4073fa5e8b2252101f6af`；worktree 必须干净。
- source 卡/状态为分配 base 的冻结快照；不得写回 source 任务卡。TASK-011 与 TASK-012 已整合，允许在测试内组合其既有服务。

## 唯一允许修改

- `tests/e2e/test_mvp_flow.py`
- `tests/e2e/test_failure_recovery.py`
- `tests/e2e/fixtures/**`
- `docs/ACCEPTANCE_REPORT.md`
- `handoffs/TASK-013.md`

禁止修改生产源码、CLI/生产 composition、配置、Schema/migration、依赖、锁文件、测试配置、既有测试、任务状态和其他文档。不得运行 `.codebase-memory` 索引动作。

## 产品完成标准

1. **五种可见结果**：在固定离线输入下证明人工字幕、自动字幕、无字幕/假 Whisper、低价值和高价值各一条完整路径。高价值路径必须形成可核验的视频笔记和周报；低价值路径必须显示为可解释的跳过，且云分析零调用。
2. **用户信任**：同一批次重跑不会复制视频记录、昂贵 Provider 调用、笔记或周报；视频笔记 Frontmatter/双链可解析并保留 `我的思考` 区域。
3. **可恢复**：分别注入字幕、转写、评分、云分析与笔记写入失败；验证重试或明确终态，已成功的昂贵步骤不重复执行。
4. **隐私边界**：默认套件使用固定夹具、现有 Fake adapters、合成凭据和 pytest 临时 SQLite/data/Vault 目录。断言无网络、无真实凭据、无真实 Vault、无测试目录外写入。
5. **验收报告**：`docs/ACCEPTANCE_REPORT.md` 将 PRD 第 10 节 1–8 逐条标为 PASS/FAIL/NOT AUTHORIZED，链接对应测试或人工证据；真实冒烟必须写为 `NOT AUTHORIZED`，不能伪报执行。

## 关键实现边界

- 测试内可直接组合现有服务与 Fake，不得修改当前 CLI 的 `_UnavailableOperations` 安全默认值，也不得新增 production composition。验收报告必须明确：这是离线服务组合证据，不是已授权的真实 CLI/Provider 冒烟。
- 不增加 pytest markers 或配置；测试应可由现有默认收集方式发现。
- 只使用已锁定组件和标准库。复用结论：`DIRECT` 为 pytest、sqlite3、临时目录、既有 fixed fixtures/Fake adapters；`REFERENCE` 为现有集成测试；`REJECT/DEFER` 为新依赖、外部框架及真实资源。
- 真实 YouTube、Whisper 模型/ffmpeg、Ollama/模型、OpenAI/API/密钥/付费调用、真实 Vault/用户笔记、网络、媒体和 launchd 一律不运行。

## 强制验证

- `uv lock --check`
- `uv sync --locked --offline`（若缓存缺失，停止报告，不切换为联网下载）
- `uv run python -m pytest tests/e2e -m 'not network and not cloud'`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`
- `git diff --check 9462b6a162a1e9a738b4073fa5e8b2252101f6af...HEAD`

完成后追加 handoff，记录 PRD 验收矩阵、每个临时资源边界、命令结果、真实冒烟未授权声明、复用/许可证和剩余风险；创建单父提交（父必须为 `9462b6a162a1e9a738b4073fa5e8b2252101f6af`）。不得启动 Reviewer 或改任务状态。
