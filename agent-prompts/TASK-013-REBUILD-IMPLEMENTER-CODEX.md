# TASK-013 — Codex Implementer (real service-flow acceptance rebuild)

你是 TASK-013 的唯一 Codex Implementer。当前实现以 main 的动态分配提交为唯一实时控制面；source worktree 的 `BLOCKED/UNASSIGNED` 任务卡是固定 base 快照，不构成冲突。先完整阅读 `AGENTS.md`、协作/状态/PRD/System Design/Reuse Register、TASK-013 卡、ADR-012 和本包；若冲突，停止报告。

## 产品目标

用可重复的离线证据证明用户真实经历的 MVP：视频有人工字幕、自动字幕、无字幕但可转写、低价值跳过、以及高价值产出笔记和周报。测试必须驱动现有生产服务边界，而不是用通用 handler 或测试手写 `complete_stage` 把 SQLite 推到下一阶段。

## 允许修改范围

1. `tests/e2e/test_mvp_flow.py`
2. `tests/e2e/test_failure_recovery.py`
3. `tests/e2e/fixtures/**`
4. `docs/ACCEPTANCE_REPORT.md`
5. `handoffs/TASK-013.md`

允许新建这些路径。不得创建 `.codebase-memory/` 或其他索引工件；没有代码图工具时可用只读 `rg`。

## 必须证明的用户行为

1. **字幕路径**：人工字幕和自动字幕分别经现有字幕服务的不同真实选择路径完成规范转写，能够继续被评分消费。
2. **无字幕路径**：字幕服务给出无字幕结果后，使用已整合的 `LocalTranscriptionService` 与 Fake Whisper executor 形成真实、可恢复的 TRANSCRIPT 结果；不得直接推进 SQLite 状态。
3. **价值路径**：低分视频明确跳过云分析且 Fake 云边界零调用；高分视频经现有离线 Fake 分析、笔记和周报服务生成可验证的用户可见结果。
4. **恢复与幂等**：对字幕、转写、评分、分析、笔记和周报在服务边界注入失败，再次运行应恢复或进入明确终态；已成功的昂贵步骤不得重复调用、产生重复 Artifact/Provider-call/笔记/周报。
5. **用户信任**：临时 Vault 中保留 `我的思考`，Frontmatter/链接正确；报告逐项映射 PRD 10.1–10.8，真实资源清晰写为 `NOT AUTHORIZED`；提供可复现、脱敏的凭据扫描证据。

## 固定测试与资源边界

- 只在 pytest 临时 SQLite/DATA/Vault、固定夹具和 Fake 外部 Adapter 中运行。可实例化现有生产服务，但不改生产 composition 或 CLI。
- 不得通过通用测试 handler、直接 `complete_stage`、直接 SQL 更新或伪造最终 Pipeline/Job 来代替所测服务的实际行为；初始夹具准备除外。
- 不得修改任何生产代码、依赖/锁、配置、Schema/migration、CLI、测试配置或既有测试。
- 不下载/加载模型，不运行 ffmpeg、媒体/YouTube、网络、真实 OpenAI/Ollama、真实 Vault/用户笔记、凭据、付费调用或测试目录外写入。

## 复用

只 `DIRECT` 复用现有项目服务、锁定依赖和 Python 标准库；外部边界全部通过 Fake Adapter。不得复制第三方代码或引入依赖。真实模型、上游 payload 与许可证风险继续由 TASK-014 跟踪。

## 必须验证

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/e2e -m 'not network and not cloud'
uv run python -m pytest tests/e2e/test_mvp_flow.py
uv run python -m pytest tests/e2e/test_failure_recovery.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check <base>...HEAD
git status --short
```

完成时 handoff 必须提供 PRD 10.1–10.8 矩阵、五场景/服务边界、失败恢复/幂等、秘密扫描命令和结果、复用/许可证、未授权真实路径与剩余风险。提交只能包含允许范围，工作树必须干净；不得自行启动 Reviewer、合并、推送、清理或改状态。
