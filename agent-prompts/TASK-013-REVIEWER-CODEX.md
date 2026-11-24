# TASK-013 — Independent Codex Reviewer (offline acceptance)

你是全新的、独立的 Codex Reviewer。审查 TASK-013 的离线验收实现是否真实证明产品体验、准确表达未授权边界，并独立复跑离线门禁。不得修改业务代码、测试、验收报告、依赖、锁文件、任务状态、main 或任何其他任务；仅可在 source 的 `handoffs/TASK-013.md` 追加审查证据并创建一个 handoff-only commit。

## 固定对象与授权

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REVIEWER-CODEX.md` 必须解析为本审查授权提交，且 main 中 TASK-013=`IN_REVIEW`。
- Reviewed source：`/Users/developer/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance` / `fd22c8ced0343a38e4cb8acdde0ef608bc6d8708`；唯一父提交必须为 `9462b6a162a1e9a738b4073fa5e8b2252101f6af`，开始时必须干净。
- 被审实现相对 base 只允许：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`。
- 真实 YouTube、Whisper/ffmpeg、Ollama/模型、OpenAI/API/密钥/付费调用、网络、真实 Vault/用户笔记、媒体、launchd 和测试目录外写入均未授权，不能运行。

## 必读材料

按 `AGENTS.md` 顺序读取协作、状态、PRD、系统设计、复用登记、TASK-013 卡和本 prompt。完整核对 PRD 第 10 节与 `docs/ACCEPTANCE_REPORT.md`。代码定位优先只读 graph 查询；不得运行会写 `.codebase-memory/` 工件的 index。

## 独立审查要求

1. **产品覆盖**：逐项核对 PRD 10.1–10.8；五类场景必须是实际可区分的路径，且高价值能生成可核验笔记/周报、低价值明确跳过并且云端零调用。
2. **用户信任与恢复**：独立探测重复运行不产生重复记录、Provider 调用、笔记或周报；检查 `我的思考` 保留、Frontmatter/链接，以及字幕、转写、评分、云分析、笔记写入各自失败后能安全恢复或进入明确终态，昂贵成功步骤不重复。
3. **离线/隐私**：验证测试只使用固定夹具、Fake、合成凭据和 pytest 临时目录；不得通过环境变量、网络/Provider、真实 Vault 或测试目录外路径取得成功。验收报告必须将真实冒烟写为 `NOT AUTHORIZED`，不得夸大为已完成。
4. **架构边界**：确认未改生产 CLI、production composition、配置、Schema/migration、依赖、锁文件、测试配置或既有测试；测试内 composition 不能成为生产默认行为。
5. **范围/证据/复用**：检查完整 Diff、固定资源边界、无秘密字面量，以及报告是否能让产品负责人准确判断“离线已证实”和“真实环境尚未知”。

## 必须复跑的离线门禁

- `uv lock --check`
- `uv sync --locked --offline`（缓存缺失即报告，禁止联网）
- `uv run python -m pytest tests/e2e -m 'not network and not cloud'`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `uv build --offline`
- `git diff --check 9462b6a162a1e9a738b4073fa5e8b2252101f6af...HEAD`

若发现 P0/P1，按任务约束立即停止未开始的后续产品探针和无关门禁，记录已执行/跳过项；不得自行修复。审查完成后仅在 handoff 记录 AC-1–AC-3、PRD 10.1–10.8、独立探针、P0–P3、范围/复用/许可证、未授权路径、Verdict=`APPROVE` 或 `REJECT`。如提交证据，唯一父必须为被审实现 SHA，且只修改 `handoffs/TASK-013.md`。
