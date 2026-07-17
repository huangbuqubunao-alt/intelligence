# TASK-005A 本地模型共享契约 — Codex Implementer

你是 TASK-005A 的唯一 Codex Implementer。你只在指定 source worktree 实现 ADR-007
L-02 至 L-06、L-08、L-10、L-11、L-14、L-15 所归属的共享配置、领域和 Repository
契约；不负责 Provider、模型、服务、媒体或后续 TASK-006/TASK-007 的实现。

## 固定执行状态

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main assignment authorization：动态运行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005A-ASSIGNMENT-INTEGRATOR.md`
- Required assignment parent / source base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始前，main 的动态 assignment authorization 必须是 Required assignment parent 的单一
直接后继；source branch/HEAD 必须精确为 source base、source worktree 干净。若 main
或 source 的基线、父链、身份、分支、洁净度、TASK-005A `IN_PROGRESS` 状态或本包范围
不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、
pull、清理、修改 main 或自行选择其他 SHA。

## 必读与事实优先级

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/SYSTEM_DESIGN.md`
3. ADR-002、ADR-003、ADR-005、ADR-006、ADR-007
4. `docs/REUSE_REGISTER.md`
5. `tasks/TASK-005A-local-model-shared-contracts.md`
6. `handoffs/TEMPLATE.md`
7. 本 Implementer 包

先用 Codebase Memory 图谱定位现有配置、`ScoringInput`/`ScoreResult`、Artifact 与
`SQLiteStateRepository.complete_stage` 的调用/类型边界；若图谱不足再读精确文件。若
ADR-007、现有 Schema 或任务卡冲突，停止并报告 `DECISION NEEDED`，不得自行扩大范围。

## 唯一允许修改的路径

1. `src/youtube_intel/config.py`
2. `src/youtube_intel/domain.py`
3. `src/youtube_intel/state.py`
4. `config/settings.example.yaml`
5. `tests/unit/test_contracts.py`
6. `tests/unit/test_state_transitions.py`
7. `tests/integration/test_state_store.py`
8. `handoffs/TASK-005A.md`

相对 source base 的完整 Diff 只能属于以上 8 个路径。禁止修改 `migrations/**`、
`pyproject.toml`、`uv.lock`、任何 Provider、`transcripts.py`、`discovery.py`、CLI、
任务/ADR、main 或其他测试。不得新增模块、依赖、Schema/migration、系统工具、模型、
服务、网络、真实媒体、Cookie/登录、Vault/密钥操作。

## 实现契约

### 配置与公开领域

- 在已有具名 Pydantic 设置上冻结 ADR-007 的转写 revision、`mlx-whisper-v1` 参数策略、
  固定解码参数和 L-15 的 `8 GiB`/`6 GiB`/`2_000_000_000` 资源门禁；只表达/校验，
  不导入或调用 mlx-whisper。
- `local_scoring` 必须支持受限 loopback `http` base URL、预期 `sha256:` model digest、
  `max_description_chars=4000`（0..20000）及 `max_transcript_chars >= 3`；拒绝非
  loopback、非 http、userinfo、query、fragment 和非空 path。
- 新增不可变具名 `TranscriptSample`、`ScoringDecision`、`ScoringOutcome`，并更新
  `ScoringInput` 以使用 sample 与完整内容哈希。`sampling-v1`、三段不重叠、预算、
  `sample.source_content_hash` 的一致性，以及最终分数阈值决定不得含糊；不得以自由
  `dict`、`Any`、宽 `object`、`cast` 或 `type: ignore` 规避契约。
- `ScoreResult.should_summarize` 保持模型建议；`ScoringDecision.final_should_summarize`
  必须严格等于结果分数和 threshold 的比较，`model_disagrees` 必须严格表示两者是否不一致。

### SQLite 完成与 Artifact 索引

- 新增具名 `ScoringSummaryWrite`，将它作为 `complete_stage` 可选参数；只有
  `TRANSCRIPT_READY -> SCORED` 允许且要求非空，其他转移必须拒绝非空。相同事务必须
  写入 Artifacts、Provider call、视频 `score`/最终 `should_summarize`、Pipeline CAS 与
  Job success；所有错误/故障注入完整回滚。
- 在现有 Artifact 索引上实现精确的 `mark_artifact_deleted` 与
  `list_expired_artifacts` 契约。它们仅更新/返回已登记记录，不删除文件；保留类别、
  UTC、hash/CAS、limit、稳定排序、未知/已删除/未过期/哈希失配边界须有测试。
- 不得修改迁移或新增列；若既有 Schema 无法满足上述原子性，报告 `DECISION NEEDED`。

### TDD、复用与安全

- 先为每个验收点写会失败的测试，再做最小实现使其通过；不得删除、跳过、弱化既有测试
  或改预期掩盖错误。
- `DIRECT` 复用已有 Pydantic、SQLite Repository/事务、Artifact/Provider-call/视频
  字段和 Python 标准库；MLX/Ollama/httpx/SDK/ORM/migration 框架保持 `DEFER/REJECT`。
- 错误、repr、日志和测试快照不包含密钥；本任务不读实际环境密钥。

## 必须运行的检查

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest tests/unit/test_state_transitions.py
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...HEAD
```

`uv sync --locked` 仅允许已有锁定依赖的缓存缺失包下载；不得锁定、添加、升级或下载
模型/二进制。还必须证明 `pyproject.toml`/`uv.lock` 相对 base 字节不变，并检查
sdist/wheel 仍包含 `migrations/001_initial.sql`。只清理本轮产生且被忽略的 `dist/`。

提交前检查完整 Diff、禁止路径、敏感信息和所有测试证据；创建一个新的非 merge commit，
唯一父提交必须为 source base。不得 amend。按 `handoffs/TEMPLATE.md` 创建交接，给出
ADR-007 逐项追溯、实际复用/许可证、检查、范围、跳过项和风险。

## 完成报告

```text
Task: TASK-005A
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria:
Checks:
ADR-007 traceability:
Reuse/license:
Diff review:
Skipped checks:
Remaining risks:
Decision needed:
```

建议状态只能是 `IN_REVIEW` 或 `BLOCKED`。不要自行启动 Reviewer、修改任务状态、合并
main、push 或清理 worktree。
