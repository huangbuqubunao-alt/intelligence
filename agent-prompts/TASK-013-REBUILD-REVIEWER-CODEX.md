# TASK-013 — Independent Codex Reviewer (real service-flow offline acceptance)

你是全新的、独立的 Codex Reviewer。审查 rebuilt TASK-013 是否真的证明用户经历的五条服务流程、失败恢复和幂等，而不是借由直接 SQLite 状态推进获得假阳性。不得修改业务代码、测试、验收报告、依赖、锁文件、任务状态、main 或其他任务；只可在 source 的 `handoffs/TASK-013.md` 追加审查证据并创建 handoff-only commit。

## 固定对象与授权

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-REVIEWER-CODEX.md` 必须解析为本审查授权提交，且 main 中 TASK-013=`IN_REVIEW`。
- Reviewed source：`/Users/hua/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@0a9e16887e7dc0b287be941a34e2908766e3992e`；开始时必须干净，唯一父提交为 `2a59dfe3860161a5989f2c08161f03c73aa4ca86`。
- 历史 `task-013` worktree/branch 是已拒绝证据，禁止访问或修改。
- 相对 base 只允许：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`。
- 真实 YouTube、Whisper 模型/ffmpeg、Ollama/模型、OpenAI/API/密钥/付费调用、网络、真实 Vault/用户笔记、媒体、launchd、测试目录外写入均未授权。

## 必读材料

按 `AGENTS.md` 顺序阅读协作、状态、PRD、System Design、Reuse Register、TASK-013、ADR-012 和本 prompt。不得运行会写 `.codebase-memory/` 的索引；无代码图工具时可用只读 `rg`。

## 独立审查探针

1. **五个用户路径**：人工与自动字幕必须通过 `SubtitleAcquisitionService` 的不同实际选择路径；无字幕必须由其 `TranscriptionRequired` 接到 `LocalTranscriptionService`；低价值必须让云 Fake 与 credential resolver 零调用；高价值必须通过评分、分析、笔记、周报的既有生产服务形成可核验结果。
2. **没有状态捷径**：检查测试没有通用 handler、测试手写 `complete_stage`、直接 SQL 更新或伪造最终 Job/Pipeline 来代替正在验收的服务；允许最小初始夹具准备。
3. **恢复/幂等**：独立确认字幕、转写、评分、分析、笔记、周报边界各失败一次后可恢复或进入明确终态；成功后重复运行不增加昂贵 Fake 调用、Provider-call、Artifact、笔记或报告。
4. **用户信任/隐私**：复核临时 Vault 的 Frontmatter、链接和 `我的思考` 保留；验收报告逐项对应 PRD 10.1–10.8；凭据扫描命令可复现、无真实密钥格式，真实资源全部写为 `NOT AUTHORIZED`。
5. **范围/复用**：确认未改生产 CLI/编排、配置、Schema/migration、依赖/锁、测试配置或既有测试；只使用 Fake 外部 Adapter、临时 SQLite/DATA/Vault 和现有 `DIRECT` 组件。

## 必须复跑的离线门禁

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
git diff --check 2a59dfe3860161a5989f2c08161f03c73aa4ca86...HEAD
```

若发现 P0/P1，立即停止未开始的无关门禁或探针，记录已执行/跳过项；不得自行修复。审查完成后仅在 handoff 记录 PRD 10.1–10.8、五路径、恢复/幂等、秘密扫描、P0–P3、范围/复用/许可证、未授权路径和 `APPROVE` 或 `REJECT`。如提交证据，唯一父提交必须为 `0a9e16887e7dc0b287be941a34e2908766e3992e`，且只修改 `handoffs/TASK-013.md`。
