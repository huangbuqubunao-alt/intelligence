# TASK-005A 交接报告

## 元数据

- Task: `TASK-005A`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `codex/task-005a-local-model-shared-contracts@82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-005a`
- Branch: `codex/task-005a-local-model-shared-contracts`
- Head commit: `Pending creation of this single implementation commit`
- Started: `2026-07-17`
- Reported: `2026-07-17`

## 目标与范围

- 任务目标：冻结 ADR-007 为 TASK-006/TASK-007 共享的配置、领域与 SQLite Repository 契约，不实现任何模型或 Provider。
- 允许修改：`config.py`、`domain.py`、`state.py`、无密钥 settings 示例、三个指定测试文件和本报告。
- 实际修改：新增固定转写/评分配置、具名评分领域对象、评分摘要原子完成、Artifact 删除确认/过期枚举及离线回归测试。
- 明确未做：未修改 migration、依赖、锁文件、Provider、`transcripts.py`、CLI、任务/ADR 或 main；未访问网络 Provider、模型、媒体、Cookie、Vault 或密钥。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 配置与示例 | PASS | `TranscriptionSettings` 固定 revision、`mlx-whisper-v1` 解码参数和 8 GiB/6 GiB/2,000,000,000 资源门禁；`LocalScoringSettings` 校验 loopback `http`、digest、3 字符下限与 4,000 字符描述默认值。`test_contracts.py` 52 PASS。 |
| 具名评分领域契约 | PASS | 新增 frozen `TranscriptSample`、`ScoringDecision`、`ScoringOutcome`；`ScoringInput` 绑定 sample 与完整 SHA-256，Outcome 校验分数阈值和模型分歧。 |
| SQLite 评分摘要原子性 | PASS | `ScoringSummaryWrite` 只允许 `TRANSCRIPT_READY -> SCORED`；同一事务提交 Artifact、Provider call、视频摘要、Pipeline CAS 和 Job 成功。故障注入验证全部回滚。`test_state_store.py` 34 PASS。 |
| Artifact 索引契约 | PASS | `mark_artifact_deleted` 使用 artifact ID + content hash CAS，仅写 `deleted_at`；`list_expired_artifacts` 按 retention、UTC 截止时间与稳定排序枚举已登记未删除记录，不删除文件。 |
| 范围/红线 | PASS | 相对 base 的产品 Diff 仅限批准 8 路径；无 migration、Provider、模型、网络、依赖或锁文件变更。 |

## ADR-007 追溯

| 条款 | 落地或明确延后 |
|---|---|
| L-01 | 已以 TASK-005 `DONE` 后的指定 base 开工；TASK-006/TASK-007 未分配、未修改。 |
| L-02 | 本交付即共享契约切片；范围严格限于配置、领域、Repository、示例和测试。 |
| L-03 | `ScoringDecision` 保留最终应用决定；`ScoringOutcome` 强制 `score >= threshold` 与 `model_disagrees` 关系，不覆盖 `ScoreResult.should_summarize`。 |
| L-04 | `ScoringSummaryWrite` 与 `complete_stage` 在单一 SQLite 事务中写入最终摘要并回滚所有关联写入。 |
| L-05 | `TranscriptSample` 固定 `sampling-v1`、三段字段、字符计数和完整哈希绑定；实际 head/body/tail 采样函数、Prompt 属 TASK-007。 |
| L-06 | 配置冻结 4,000 字符描述预算，领域绑定完整内容哈希；稳定元数据编排和 request hash 计算属 TASK-007。 |
| L-07 | 配置拒绝非 loopback/非 `http`/userinfo/query/fragment/path；标准库 HTTP 实现、`/api/tags` 与 `/api/generate` 属 TASK-007。 |
| L-08 | 示例和配置固定 `qwen3:8b` 的批准 `sha256:` digest；Ollama 安装、服务和模型验证未执行。 |
| L-09 | Repository 已能随评分阶段原子索引 response Artifact/Provider call；JSON 修复、Provider 错误映射和缓存流程属 TASK-007。 |
| L-10 | 配置表达并校验固定 MLX Whisper revision policy、解码参数和参数版本；不导入或调用 `mlx-whisper`。 |
| L-11 | 配置表达模型 revision、weights 大小和 SHA-256；下载、清单验证与许可证清单属 TASK-006/TASK-014。 |
| L-12 | 音频获取、ffmpeg、真实媒体与安装均未实现，留给具备单独授权的 TASK-006。 |
| L-13 | 180 分钟门禁、`--force` 与审计 migration 均留给 TASK-010。 |
| L-14 | 实现 audio Artifact 的删除 CAS 与按保留类别的过期索引枚举；实际 DATA 根文件删除由 TASK-006/TASK-012 执行。 |
| L-15 | 配置冻结 8 GiB/6 GiB/2,000,000,000 初始资源门禁；spawn 子进程超时与真实资源校准属 TASK-006。 |

## 复用与许可证

- `DIRECT`：既有 Pydantic 2.13.4（MIT）配置/领域模型、既有 SQLite Repository 事务与已有 `videos`/Artifact/Provider-call Schema；Python 标准库 `urllib.parse`、`math` 与 SQLite（CPython/PSF 与 SQLite public-domain 组件）能力。
- `REFERENCE`：ADR-007 中的 MLX Whisper、Ollama、Qwen 和 ffmpeg 版本/许可证事实，只用于冻结字段；未复制、导入、下载或调用外部实现。
- `REJECT/DEFER`：`mlx-whisper`、Ollama SDK、`httpx`、ORM、迁移框架、模型下载、服务和网络调用均未引入；无新增依赖或许可证义务。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 锁定环境解析成功。 |
| `uv sync --locked` | PASS | 使用锁定 34 packages；仅补齐缓存缺失的既有 `uv-build` 构建依赖。 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | 52 passed。 |
| `uv run python -m pytest tests/unit/test_state_transitions.py` | PASS | 10 passed。 |
| `uv run python -m pytest tests/integration/test_state_store.py` | PASS | 34 passed。 |
| `uv run python -m pytest` | PASS | 250 passed。 |
| `uv run mypy src` | PASS | Success: no issues in 9 source files。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| `uv run python -m youtube_intel --help` | PASS | CLI help returned successfully。 |
| `uv build --offline` | PASS | sdist/wheel built; both contain `youtube_intel/migrations/001_initial.sql`。 |
| `pyproject.toml` / `uv.lock` blob audit | PASS | Base and worktree blob IDs matched exactly; no byte changes。 |

## Diff 复核

- 修改文件：`config/settings.example.yaml`、`src/youtube_intel/{config,domain,state}.py`、`tests/unit/{test_contracts,test_state_transitions}.py`、`tests/integration/test_state_store.py`、本报告。
- 是否存在任务范围外修改：否；仅上述 8 个批准路径。
- 是否存在生成文件或格式化噪声：否；离线 build 产生的、已忽略的 `dist/` 已在验证后移除。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：TDD RED 先确认新增领域/状态公开类型缺失；一次 `uv sync --locked` 因沙箱网络限制失败，获批准后仅下载锁定构建依赖并成功。
- 跳过检查及原因：无。真实模型、Ollama 服务、ffmpeg、媒体、网络、Cookie、Vault 与密钥操作未运行，因为不在授权范围内。
- 剩余风险：实际采样算法、Ollama JSON/HTTP 处理、MLX 安装/模型完整性、资源实测和文件删除者仍需后续任务独立验证。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`Pending creation of this single implementation commit`
- 复现/验证说明：使用上述锁定 uv 命令；默认测试完全离线，无 Provider、模型或真实文件系统资源调用。
