# TASK-005A：本地模型共享契约

- Status: `IN_REVIEW`
- Assignee: `Codex`
- Reviewer: `Codex`（Correction 1 后由全新独立会话审查）
- Owner role: Codex Independent Reviewer（Correction 1）
- Size: M
- Risk: High
- Depends on: TASK-005
- Decision gate: `ADR-007` 为 `Accepted`；产品负责人已于 2026-07-17 批准 L-01 至 L-15
- Execution gate: 已授权固定 worktree/分支、Codex Implementer、全新独立 Codex
  Reviewer 和既有锁定依赖的离线门禁；不得新增 Schema/migration、依赖或锁文件

## 目标

在不实现 Whisper 或 Ollama Provider 的前提下，冻结 TASK-006/TASK-007 共同需要的
配置、领域和 SQLite Repository 契约，使两项后续任务可从同一 `DONE` main 基线安全
并行。

## 范围

- 扩展具名配置模型和 `config/settings.example.yaml`：
  - 转写模型 revision、`mlx-whisper-v1` 参数策略版本、ADR-007 L-10 固定解码参数、
    以及 L-15 的磁盘/内存/音频字节资源门槛；不解析、安装或下载模型。
  - 本地评分 loopback base URL、预期模型 digest、`max_description_chars=4000`
    （范围 `0..20000`）和 `max_transcript_chars >= 3`；拒绝非 loopback、userinfo、
    query、fragment 或非空路径的 URL。
- 扩展不可变具名领域对象：`TranscriptSample`、`ScoringDecision`、`ScoringOutcome`，
  并把 `ScoringInput` 固化为携带样本和完整内容哈希的有限评分输入。不得使用自由
  `dict`、`Any` 或宽 `object` 表达公共契约。
- 冻结 `TranscriptSample` 的 `sampling-v1` 字段、三段非重叠规则、字符预算与完整
  内容哈希绑定；实际 sampling 函数和 Prompt 属于 TASK-007。
- 新增具名 `ScoringSummaryWrite(score, should_summarize)`，让 `complete_stage` 可在且
  仅可在 `TRANSCRIPT_READY -> SCORED` 时原子写入 `videos.score` 与最终
  `videos.should_summarize`，连同 Artifact、Provider call、Pipeline CAS 和 Job 成功。
  `SCORED` 时摘要必须存在，其他阶段必须为 `None`；任一失败完整回滚。
- 在现有 Artifact 索引上增加 `mark_artifact_deleted(artifact_id, expected_content_hash,
  now) -> bool` 与 `list_expired_artifacts(retention_class, now, limit) -> tuple[ArtifactRecord, ...]`。
  它们只记录/枚举已登记产物，不执行文件删除；删除方仍须在 DATA 根、哈希匹配和路径
  边界通过后操作。未知、哈希不符、已删除或未过期对象不得被错误确认。
- 为上述契约补充配置、领域、状态转换和真实 SQLite 事务/回滚测试。

## 范围外

- 不实现 `transcription.py`、`scoring.py`、Whisper/Ollama Provider、Prompt、音频下载、
  本地模型子进程、模型/服务预检或任何网络访问。
- 不新增 Schema/migration、依赖或系统工具；不修改 `pyproject.toml`、`uv.lock`。
- 不安装 `mlx-whisper`、Ollama、ffmpeg 或模型；不访问真实 YouTube/字幕、Cookie、
  登录、remote components、媒体、真实 Vault 或密钥。
- 不实现 TASK-010 的 180 分钟 `--force` 编排/审计 migration，也不让本任务决定 Job
  的 `SKIPPED_DURATION_LIMIT`。

## 验收标准

- [ ] 配置的默认值、边界、未知字段拒绝、loopback URL、digest 和示例配置均满足
  ADR-007 L-06、L-08、L-10、L-11、L-15，且错误/`repr` 不泄露密钥。
- [ ] `TranscriptSample`、`ScoringDecision`、`ScoringOutcome` 和评分输入是不可变具名
  对象；模型建议与应用最终决定不被混淆，`final_should_summarize == score >= threshold`。
- [ ] 评分摘要只在 `TRANSCRIPT_READY -> SCORED` 的单个事务中写入；缺失/越界/错误阶段
  和故障注入全部回滚 Artifact、Provider call、视频摘要、Pipeline 与 Job。
- [ ] Artifact 删除确认和过期枚举具有 hash/CAS、UTC、保留类别、limit 和稳定排序边界；
  不触及未登记文件或执行删除。
- [ ] 无 Provider SDK、网络、模型、Schema/migration 或锁文件改动；TASK-006/007 所需
  公共契约可由静态类型检查直接消费。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv run python -m pytest tests/unit/test_contracts.py`
- [ ] `uv run python -m pytest tests/unit/test_state_transitions.py`
- [ ] `uv run python -m pytest tests/integration/test_state_store.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build --offline`
- [ ] `git diff --check <base>...HEAD`
- [ ] 人工审计：无模型/Provider/网络访问，`pyproject.toml` 与 `uv.lock` 字节不变，
  sdist/wheel 仍包含 `migrations/001_initial.sql`。

## 预计触达文件

- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `src/youtube_intel/state.py`
- `config/settings.example.yaml`
- `tests/unit/test_contracts.py`
- `tests/unit/test_state_transitions.py`
- `tests/integration/test_state_store.py`
- `handoffs/TASK-005A.md`

不包含 `migrations/**`、`pyproject.toml`、`uv.lock`、任何 Provider、`transcripts.py`、
`discovery.py`、CLI、任务状态或 ADR 文档。若现有 Schema/字段不足以完成评分摘要原子
写入或 Artifact 删除确认，必须报告 `DECISION NEEDED`，不得私自新增 migration。

## 复用决定

- `DIRECT`：既有 Pydantic 配置/领域边界、TASK-003 SQLite Repository/事务、现有
  Artifact/Provider-call/视频摘要列，以及 Python 标准库 URL/时间/哈希能力。
- `REFERENCE`：ADR-007 的官方 MLX Whisper、Ollama 和模型来源仅用于冻结参数与
  许可证/供应链证据；本任务不导入、调用、下载或复制外部实现。
- `REJECT/DEFER`：ORM、迁移框架、httpx、Ollama Python SDK、mlx-whisper、ffmpeg、
  模型下载及真实服务，分别留给已批准后的 TASK-006/007 和后续门禁。

## 交付证据

- ADR-007 L-02 至 L-15 的逐项追溯表，以及哪些条款由 TASK-006、TASK-007、TASK-010
  或 TASK-012 延后实现的明确边界。
- 配置/领域/Repository 测试和故障注入结果；真实 SQLite 原子写评分摘要的证据。
- 复用、许可证与未新增依赖/模型/网络的审计。
- 后续 TASK-006/TASK-007 可共同使用的 main merge SHA；在此之前两项不得分配。

## 正式分配记录

- Approved base：`main@82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Branch：`codex/task-005a-local-model-shared-contracts`
- Implementer：Codex 独立会话，独占该 worktree 写入权
- Reviewer：全新独立 Codex 会话；只在 Implementer 提交并由主控固定 source SHA 后启动
- Implementer packet：`agent-prompts/TASK-005A-IMPLEMENTER-CODEX.md`
- 仅允许本卡列出的 8 个路径；允许 `uv sync --locked` 只为已有锁定依赖的缓存缺失包
  下载及本卡离线验证/构建。任何模型、Provider、真实网络、服务、Schema/migration、
  依赖或锁文件操作仍被禁止。

## 审查授权记录

- Source implementation head：`85cd5362460044773317a48cbaae58e55aa735af`
- Source implementation parent/base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Source 范围：精确为本卡列出的 8 个路径；`pyproject.toml` 与 `uv.lock` 相对 base
  无差异，source worktree 已由主控静态核验为干净。
- Reviewer：必须为未参与本实现的全新独立 Codex 会话，只能在 source worktree 的
  `handoffs/TASK-005A.md` 追加审查证据并创建单一 evidence commit；不得改业务代码、
  测试、依赖、锁文件、任务状态或 main。
- Reviewer packet：`agent-prompts/TASK-005A-REVIEWER-CODEX.md`；其 main 动态授权
  必须由本次控制面同步 commit 解析。独立审查通过前不得设为 `ACCEPTED`、整合或关闭。

## 第一轮审查拒绝与 Correction 1

- Reviewer evidence：`3cec2d6a7b60b11912c10e714dc1473197d7374f`，唯一父提交为原实现
  `85cd5362460044773317a48cbaae58e55aa735af`，且只修改 source handoff。
- Verdict：`REJECT`。P1：四个新增公开 Pydantic 领域对象可被
  `model_copy(update=...)` 在不经字段/模型验证下构造成非法 `TranscriptSample`、
  hash 不匹配 `ScoringInput`、错误类型 `ScoringDecision` 与违背 `score >= threshold`
  的 `ScoringOutcome`，阻断 AC-2 与 ADR-007 L-03/L-05/L-06。
- 已独立通过：所有离线门禁，Probe A（配置）、C（SQLite 原子性）和 D（Artifact
  index）。拒绝只针对该 P1；不重开后续模型、服务、媒体或文件删除边界。
- Correction 1 source scope：只能修改 `src/youtube_intel/domain.py`、
  `tests/unit/test_contracts.py` 和 `handoffs/TASK-005A.md`。它必须使公开 functional
  update 重新验证或拒绝未验证 update，并为全部四个对象加入回归；不得把行为改动扩展
  到既有非本任务领域对象、Schema、依赖、锁文件或其他产品路径。
- Correction packet：`agent-prompts/TASK-005A-CORRECTION-1-CODEX.md`。修复提交后
  必须再次获得全新独立 Codex Reviewer 审查；不得直接验收、整合或关闭。

## Correction 1 审查授权

- Correction 1 source head：`3a7df1029a77b7dec84a76c304c10e372f755b77`；唯一父提交为
  第一轮 reviewer evidence `3cec2d6a7b60b11912c10e714dc1473197d7374f`。
- Correction Diff：精确为 `src/youtube_intel/domain.py`、
  `tests/unit/test_contracts.py` 和 `handoffs/TASK-005A.md`；原始 base 的完整产品范围
  仍精确为 8 个批准路径，lock/config 未变。
- 修复策略：仅对本任务四个新增评分公开对象禁止所有带 `update` 的
  `model_copy`；无 update 复制继续保留。它不得改变既有非本任务 `_DomainModel` 的
  public 行为。
- Reviewer packet：`agent-prompts/TASK-005A-REVIEWER-2-CODEX.md`。独立审查尚未启动；
  未通过前不得设为 `ACCEPTED`、整合或关闭。
