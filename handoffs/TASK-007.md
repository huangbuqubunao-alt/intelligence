# TASK-007 交接报告

## 元数据

- Task: `TASK-007`
- Role: `Implementer`
- Agent/session: `Codex /root`
- Base branch/commit: `main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-007`
- Branch: `codex/task-007-local-scoring`
- Head commit: 本报告与实现提交在同一 HEAD；最终 SHA 由主控回传记录。
- Started: `2026-07-19`
- Reported: `2026-07-19`

## 目标与范围

- 任务目标：离线实现本地评分的三段采样、版本感知缓存和阈值策略；以严格 JSON Schema
  解析、一次格式修复及 Fake transport 实现 Ollama Adapter。
- 允许修改：`scoring.py`、`providers/ollama.py`、`prompts/scoring.md`、两份任务测试、
  `tests/fixtures/scoring/**` 与本报告。
- 实际修改：上述允许路径，新增评分服务、Ollama Adapter、版本化 Prompt、5 个固定响应夹具
  和 10 个离线测试。
- 明确未做：未改 `pyproject.toml`、`uv.lock`、Schema/migration、`config.py`、`domain.py`、
  `state.py`、任务状态或 `main`；未实现模型安装、服务生命周期、模型拉取或真实评分冒烟。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| AC-1：合法、越界、缺字段、非法 JSON、修复成功和失败 | PASS | `tests/integration/test_ollama_provider.py` 使用 5 个固定夹具；6 项 Fake transport 测试通过。 |
| AC-2：开头/正文/结尾采样、长度限制与重复评分缓存 | PASS | `test_sample_transcript_uses_bounded_head_center_tail_segments` 和缓存命中测试通过；同一规范输入只调用 Fake Provider 一次。 |
| AC-3：阈值最终决策与模型建议冲突诊断 | PASS | `ScoringService` 保留模型建议，以 `score >= threshold` 产生最终值，并记录 `MODEL_POLICY_DISAGREEMENT`。 |
| 严格 Provider 边界 | PASS | Adapter 仅构造 `GET /api/tags` 与 `POST /api/generate`；`stream=false`、`think=false`、有限读取、固定 JSON Schema，且默认 transport 未在测试中调用。 |

## 版本、复用与许可证

- Prompt/schema/sampling：`scoring-prompt-v1`、`score-result-v1`、`sampling-v1`。
- `DIRECT`：Python 3.12 `urllib.request` 与 `json`（标准库）；既有锁定 Pydantic 评分对象和
  Provider-call 哈希契约。未新增依赖。
- `DIRECT-PENDING`：Ollama HTTP API 与 `qwen3:8b` 仅作为配置和 Fake 响应的未来运行时边界；
  未安装、启动、拉取、探测或调用。Ollama MIT / qwen3:8b 上游 Apache-2.0 的登记证据见
  `docs/REUSE_REGISTER.md` §7 与 ADR-007 L-08。
- `REJECT`：未引入 `httpx`、Ollama Python SDK、cloud tag 或自动服务/模型 bootstrap。
- 黄金夹具：固定夹具只验证结构、边界和修复语义，不宣称模型质量或人工标注偏差已经校准；
  经批准的本机模型和人工黄金样例校准留待后续资源门禁。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 34 个锁定包已解析；无锁文件修改。 |
| `uv sync --locked --offline` | PASS | 首次 `uv run` 发现构建后端缓存未就绪后按任务包允许的离线同步；30 个已有锁定包安装成功，未联网下载。 |
| `uv run python -m pytest tests/unit/test_scoring.py` | PASS | `4 passed`。 |
| `uv run python -m pytest tests/integration/test_ollama_provider.py` | PASS | `6 passed`，全部为 Fake transport。 |
| `uv run python -m pytest` | PASS | `261 passed`。 |
| `uv run mypy src` | PASS | `Success: no issues found in 11 source files`。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | sdist 与 wheel 均构建成功。 |
| 包内容检查 | PASS | 两个产物均含 `youtube_intel/migrations/001_initial.sql`。 |
| Fake/no-real-Ollama 审查 | PASS | 测试注入 `_FakeTransport`；未运行 Ollama、`qwen3:8b`、`127.0.0.1:11434` 或其他网络服务。 |

## Diff 复核

- 修改文件：仅任务批准的 7 个路径组（2 个源模块、Prompt、2 个测试、夹具目录、本报告）。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：`dist/` 和 `.venv/` 为忽略的本地检查产物，未暂存或提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：首次 `uv run` 因缓存中缺少构建后端而尝试网络并被拦截；随后
  `uv sync --locked --offline` 成功，所有后续命令均离线执行。
- 跳过检查及原因：未运行任何真实 Ollama/模型/网络/媒体/Vault/密钥/ffmpeg/删除路径；它们未获授权。
- 剩余风险：真实 Ollama `0.32.x` 与固定 `qwen3:8b` digest 的运行时兼容性、模型质量和
  人工黄金样例偏差仍待独立资源授权；当前 Adapter 只由 Fake transport 证明。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：见包含本报告的实现提交；主控回传精确 SHA。
- 复现/验证说明：在此 worktree 执行上表命令；Provider 集成测试只使用测试内的
  `_FakeTransport`，不使用默认 `urllib` transport。
