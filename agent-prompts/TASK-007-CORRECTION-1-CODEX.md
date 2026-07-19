# TASK-007 Ollama 本地评分 — Codex Implementer Correction 1

## 身份、目标与动态授权

你是原 TASK-007 的 **Codex Implementer**。修复第一轮独立审查的两个 P1：

1. 任何公开 Ollama 评分失败都必须以具名、脱敏的应用错误返回，完整异常链不得保存或泄漏
   原始响应、Prompt、字幕正文、临时 URL 或绝对路径；短读、畸形和超限响应必须按 ADR-007 L-09
   失败关闭。
2. 评分成功必须复用已有 SQLite Provider Call/Artifact/评分摘要/`complete_stage` 契约，在一个
   `TRANSCRIPT_READY -> SCORED` 事务中持久化、CAS 并完成 Job；不能继续只以进程内缓存宣称可恢复。

在开始写入前，从 main
`/Users/hua/Documents/youtubek agent` 执行：

```bash
git log -1 --format=%H -- agent-prompts/TASK-007-CORRECTION-1-CODEX.md
```

该命令必须解析到最新的 Correction 1 授权提交；main 的 `tasks/TASK-007-local-scoring.md` 必须为
`IN_PROGRESS`/原 Codex Implementer。source worktree 的旧任务卡 `BLOCKED/UNASSIGNED` 是创建时
冻结快照，不是停止理由。若 main 控制面、source HEAD、父链、权限或任务范围不一致，立即停止。

## 固定 source

- Worktree：`/Users/hua/Documents/yia-worktrees/task-007`
- Branch：`codex/task-007-local-scoring`
- 共同 base：`6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Starting review evidence：`266c488c17fc82cb648053b5e1066211a7bea9a9`
- Evidence 的唯一父提交必须是原实现 `258358fcd5227e144c9294beafdf7ec6e2feea63`；它只能修改
  `handoffs/TASK-007.md`。
- Correction commit 必须以 `266c488c...` 为唯一父提交。禁止 amend、rebase、cherry-pick、
  merge、main 写入、任务状态改变或启动 Reviewer。

TASK-006 正由独立 Implementer 修复。不得读取、运行检查、修改、清理、等待或报告
`/Users/hua/Documents/yia-worktrees/task-006`。

## 唯一允许范围

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- 仅在负例确有必要时：`tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

禁止改动：`state.py`、Schema/migration、`domain.py`、`config.py`、Prompt、其他测试、
`pyproject.toml`、`uv.lock`、任务状态和 main。不得新增依赖、SDK、自由形状公共对象或新的公开
领域契约。若只用这些范围无法满足既有共享契约，报告 `DECISION NEEDED`，不要绕过它。

## 必须复用的既有契约

- `DIRECT`：Python 标准库 `urllib`/`json`、现有 SQLite Repository、现有锁定依赖。
- `REFERENCE/DEFER`：Ollama HTTP 仅为 Fake transport 边界；不安装、启动、请求真实 loopback、
  拉取 `qwen3:8b`、访问 cloud tag 或远程地址。
- 使用现有 `ProviderCallRequest`、`ProviderCallCompletion`、`ArtifactWrite`、
  `ScoringSummaryWrite` 和 `SQLiteStateRepository.complete_stage`，不复制或重新设计其 Schema/
  事务语义。

## Correction 1 完成标准

### P1-1：Ollama 边界和异常图

- 保持 loopback-only、固定 `/api/tags` 与 `/api/generate`、`stream=false`、`think=false`、
  Schema format、一次且仅一次 repair、有限读取与总是关闭 response；所有测试只能使用注入的
  Fake transport。
- 主响应或 repair 响应的 JSON/Schema/信封/`response` 缺失或超限、非法 UTF-8、短读
  (`http.client.IncompleteRead`) 及 transport/read 例外都必须被统一安全边界捕获。
- 映射必须遵守 ADR-007 L-09：timeout/短读为 `TRANSIENT_NETWORK`；429 为 `RATE_LIMITED`；
  5xx/未启动为 `PROVIDER_UNAVAILABLE`；401/403 为 `PERMISSION_DENIED`；畸形或超限响应为
  `INVALID_RESPONSE`。安全错误保留请求 `video_id`、stage/可重试语义，禁止把不可信内容连接到
  message。
- 用 `raise ... from None` 或等效设计确保 `message`、`__cause__`、`__context__`、traceback 和
  内嵌异常对象均不能到达原始模型正文、Prompt、字幕、临时 URL 或本机绝对路径。新增哨兵测试必须
  递归检查完整异常图，不能只检查顶层 `str(exc)`。

### P1-2：持久 Provider Call、Artifact 与原子评分完成

- 保留当前纯策略/采样的可测性，但为真实应用路径增加一个明确的 repository-backed 评分完成入口；
  该入口不得让 Provider 直接写 SQLite，也不得将 SQLite 具体类型泄漏为新的公共领域契约。
- 在调用前按既有 `ProviderCallRequest` 预留，使用稳定 operation/request hash 与确定性 Artifact
  key；已有成功且经验证的同一请求只能复用，不得二次调用 Fake Provider。改变规范输入、模型、
  Prompt、Schema 或 operation 必须未命中。
- 成功时，在现有 `complete_stage` 的一个事务中写入：
  - 原始 Provider 响应 `SCORING_RAW` / `RAW_RESPONSE_30D`；
  - 结构化评分 `SCORING_STRUCTURED` / `LONG_LIVED`；
  - 对应成功 `ProviderCallCompletion`；
  - `ScoringSummaryWrite(score, final_should_summarize)`；
  - `TRANSCRIPT_READY -> SCORED` Pipeline CAS 与对应 Job 成功。
- 每一个 Artifact 必须与当前 job/video、确定性 key 和哈希一致。成功 Provider Call 必须绑定其
  原始响应 Artifact；结构化结果、最终阈值决策和模型分歧诊断仍须可审计。不要让模型建议覆盖
  应用最终 `score >= threshold` 策略。
- 在 Artifact 写入、Provider Call 完成、评分摘要或 Pipeline 更新后的任意 injected failure 都
  必须完整回滚；失败不得留下成功 Artifact、Provider Call、分数、Pipeline 或 Job。失败 Provider
  Call 按已有 Repository 语义安全记录/释放，不得伪造成功。

### 必须新增的离线证据

- Fake transport：完整异常链脱敏，短读、缺失/超长/畸形 primary/repair 响应、一次 repair 和
  精确错误映射。
- 临时真实 SQLite：首次成功的 raw/structured Artifact、Provider Call、评分摘要、Pipeline 和
  Job 是一次提交；注入后写失败完整回滚；同一已验证请求不调用第二次 Fake；每一个 cache-key
  维度改变都不重用。测试只能写临时测试目录，绝不碰真实数据或 Vault。

## Required checks

在 source worktree（不联网）依次运行：

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_scoring.py
uv run python -m pytest tests/integration/test_ollama_provider.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 266c488c17fc82cb648053b5e1066211a7bea9a9...HEAD
git status --short
```

检查 sdist/wheel 都包含 `youtube_intel/migrations/001_initial.sql`。`uv sync --locked --offline`
若缓存缺失即停止，不得联网补包。禁止真实 Ollama/网络、模型、媒体/YouTube、Cookie、remote
components、ffmpeg、Vault/凭据或任何删除路径。

## 交接和回传

在 `handoffs/TASK-007.md` 记录：P1 闭环矩阵、完整异常图哨兵、真实 SQLite 原子/回滚/cache
探针、Reuse/许可证、所有命令结果、完整 Diff、未运行资源路径和风险。创建一个范围明确 commit，
报告 SHA、父提交、范围、检查、风险与 `Decision needed`。不要在 main 改任务状态，不要自行审查、
合并或关闭任务。
