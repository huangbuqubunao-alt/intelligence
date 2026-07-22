# TASK-008 交接报告

## 元数据

- Task: `TASK-008`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `473119704c7638d7afd4e68d84d00e85064ceabd`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-008`
- Branch: `codex/task-008-deep-analysis`
- Started: `2026-07-22T06:50:33Z`
- Reported: `2026-07-22T06:50:33Z`

## 目标与范围

- 任务目标：离线实现可选 OpenAI 深度分析的隐私门禁、隔离 SDK Adapter、SQLite 完成与恢复。
- 允许修改：`analysis.py`、`providers/cloud_llm.py`、summary prompt、分析夹具/测试及本报告。
- 实际修改：策略/持久化 Adapter、固定 prompt、unit/integration tests、本报告（六个允许路径组；无需新增 fixture）。
- 明确未做：未读取真实密钥，未调用 API/网络/真实 Vault；未修改依赖、Schema、`state.py`、领域/配置契约或 TASK-009。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 零调用门禁与单次成功 | PASS | `test_analysis_policy.py` 覆盖关闭、低价值、缓存、预算/凭据顺序；Fake transport 成功路径一次调用。 |
| 最小 payload、采样、确定性哈希 | PASS | unit test 验证字段白名单、稳定输入与 4k code-point sample；包内固定 `o200k_base`。 |
| Structured Outputs/错误/证据 | PASS | `test_summary_provider.py` 覆盖 strict `store=False`、refusal、无效响应、429、5xx 和精确 evidence grounding。 |
| Artifact/Provider-call/事务/恢复 | PASS | 临时 SQLite 测试覆盖两类 Artifact、精确 30-day retention、`stage.after_provider_call` 回滚/文件清理，以及成功 Provider call/Artifact 重排零 transport 调用。 |
| SDK 与隐私边界 | PASS | SDK 仅在无继承环境的 child import；Fake transport 是默认测试路径，异常不含 payload/凭据。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | lock 一致。 |
| `uv sync --locked` | PASS | 61 packages checked。 |
| focused unit/integration | PASS | 4 policy + 9 provider/SQLite tests。 |
| `uv run python -m pytest` | PASS | 340 passed。 |
| `uv run mypy src` | PASS | Success: no issues。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| CLI help / `uv build --offline` | PASS | CLI 可用；sdist/wheel 成功。 |
| 包内容检查 | PASS | sdist/wheel 均含 `prompts/summary.md` 和固定 tokenizer resource。 |

## Diff 复核

- 修改文件：六个允许路径组；未使用 fixture 路径组。无依赖、Schema、配置、CLI、任务状态或 main 修改。
- 红线：未触及真实密钥、真实 Vault、云调用、网络资源或调度。
- 复用：`DIRECT` 已锁定 OpenAI SDK（仅 child import/Fake transport）、tiktoken 固定本地资源、既有 Artifact/Provider-call/SQLite `complete_stage`；未写 HTTP client、第二 Provider、SDK retry 或 token-count endpoint。

## 失败、跳过与风险

- 已解决失败：`uv` 沙箱缓存权限被提升权限的同一离线验证命令解决；非代码失败。
- 跳过检查：真实云端冒烟（未授权，留 TASK-013）。
- 剩余风险：真实凭据/API 路径未执行，符合任务门禁。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：待创建
- 复现/验证说明：仅 Fake transport 和临时 SQLite；无真实资源。

## Reviewer 结论

- Reviewer agent/session: `Codex`（独立新会话）
- 授权记录：`main` 中本 Reviewer 工作包最新提交为
  `83bd1f1fcfdef5d4949f59b513033803113c3d8a`；实时控制面将 TASK-008
  列为等待独立审查，审查对象为
  `codex/task-008-deep-analysis@10478a9083df4eedae061d99d941c88cb4954179`。
- Base/历史快照：唯一父提交为
  `473119704c7638d7afd4e68d84d00e85064ceabd`；source 的旧
  `BLOCKED/UNASSIGNED` 文档快照未作为冲突处理。
- 范围与完整 Diff：worktree 起始时 clean；`base...HEAD` 仅包含六个允许路径
  （handoff、`analysis.py`、`providers/cloud_llm.py`、固定 prompt、两份指定测试），
  无依赖、锁、公共契约、Schema/state、CLI 或 TASK-009 变更；固定
  `git diff --check` 通过。

### 独立检查

| 命令/探针 | 结果 | 证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages in 14ms`。 |
| `uv sync --locked` | PASS | 首次受沙箱外 uv cache 权限限制；获批准后以同一 locked 命令执行，`Checked 61 packages`。 |
| `uv run python -m pytest tests/unit/test_analysis_policy.py` | PASS | `4 passed`。 |
| `uv run python -m pytest tests/integration/test_summary_provider.py` | PASS | `9 passed`。 |
| A：Repository 持久化路径 token 门禁 | **FAIL / P1** | 临时 SQLite + Fake Provider/Resolver，`CloudSettings(enabled=True, model="gpt-4.1-mini", max_local_input_tokens_per_video=1)` 与普通 transcript：输出 `provider 1 credential 1`。不应读取凭据或调用 transport。 |
| 其余强制命令与 B–E 探针 | SKIPPED | 工作包规定发现任一 P0/P1 立即 `REJECT` 并停止；未继续运行全量 pytest、mypy、Ruff、CLI、offline build、包检查或其他探针。 |

### Findings（P0–P3）

- **P1 — 持久化分析路径绕过本地 token 零调用门禁。**
  `RepositoryBackedAnalysisService.analyze` 在
  [`src/youtube_intel/analysis.py:423`](../src/youtube_intel/analysis.py#L423)
  直接构造输入并在
  [`src/youtube_intel/analysis.py:453`](../src/youtube_intel/analysis.py#L453)
  读取凭据、在
  [`src/youtube_intel/analysis.py:459`](../src/youtube_intel/analysis.py#L459)
  调用 provider；它没有复用 `AnalysisService` 在
  [`src/youtube_intel/analysis.py:357`](../src/youtube_intel/analysis.py#L357)-[`src/youtube_intel/analysis.py:359`](../src/youtube_intel/analysis.py#L359)
  执行的 `_input_tokens(...) > max_local_input_tokens_per_video` 检查。故实际任务路径在
  local-token 超限时仍会把 payload 交给 transport，违反 TASK-008 AC 和工作包探针 A 的
  “token 门禁零 transport、凭据最后读取”要求；真实环境会造成未经允许的云端内容发送与付费调用。

- P0：无（审查在首个 P1 后按授权停止）。
- P2/P3：未继续评估；不构成已审查通过的结论。

### AC / ADR / 五轴矩阵

| 项目 | 状态 | 说明 |
|---|---|---|
| AC：token 超限零调用 | **FAIL** | 上述 P1 已以临时 SQLite/Fake transport 复现。 |
| 其余 AC、ADR-008 A-01 至 A-17、复用/许可证、五轴完整审查 | BLOCKED | 发现 P1 后强制停止，不能标记为通过。 |
| 真实 OpenAI、凭据、付费、网络、Vault/用户内容 | NOT RUN | 未授权且未触发。 |

- Verdict：`REJECT`
- 未解决 P0/P1：P1（持久化路径必须先完成和普通路径相同的零调用门禁；补充该真实 SQLite/Fake transport 回归后再重新独立审查）。
- 复用/许可证：本次只复核声明的 DIRECT 边界；未新增依赖或许可证义务。未因 P1 对其余复用项作通过结论。

## Correction 1 — Implementer

- 授权：`TASK-008-CORRECTION-1-CODEX.md`，main control-plane
  `03a5f6ea83ca3c452808d255fffd438cb33c0c78`；起始 source HEAD
  `b61f46f6bca3303d5590aac76d8c8c9b53ec4131`，唯一父为 reviewed implementation
  `10478a9083df4eedae061d99d941c88cb4954179`。
- 修复：`RepositoryBackedAnalysisService.analyze` 在任何 Repository 预留、凭据解析或
  Provider 调用前，复用普通路径的固定本地 request 构造与 token 计数；超限返回
  `INPUT_TOO_LARGE`，不创建 Provider call 或 Artifact。
- 新离线回归：临时 SQLite、`max_local_input_tokens_per_video=1`、合成 transcript 验证
  Resolver=0、Fake transport=0、ProviderCall/Artifact=None、Pipeline=`SCORED`、已领取
  Job=`RUNNING`。既有成功、rollback、重排及 RAW_RESPONSE_30D tests 保留并通过。
- 检查：focused `4 + 10`，full `341 passed`，mypy、Ruff、CLI help、locked sync、offline
  build 全 PASS；sdist/wheel 均含 migration、summary prompt 和固定 tokenizer resource。
- 范围：仅 `analysis.py`、两份指定测试和本 handoff；未修改 `cloud_llm.py`、prompt、fixture、
  state/Schema/依赖/配置/CLI/main/TASK-009；未运行真实资源。
- 复用：继续 `DIRECT` 使用既有 tiktoken 本地资源与 SQLite Provider-call/Artifact/
  `complete_stage` 接口；无新依赖、HTTP client、Provider 或 token-count endpoint。
- `DECISION NEEDED`：`None`。
- Commit SHA：待创建（父提交将严格为 `b61f46f...`）。
