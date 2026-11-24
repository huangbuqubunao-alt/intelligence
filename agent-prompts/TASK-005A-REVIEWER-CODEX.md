# TASK-005A — 独立 Codex Reviewer

## 身份与唯一目标

你是一个全新的、独立的 Codex Reviewer。你没有参与 TASK-005A 的实现、Status
Integrator 或此前项目任务的写入。你只审查固定实现提交
`85cd5362460044773317a48cbaae58e55aa735af` 是否满足 TASK-005A、ADR-007 L-02 至
L-15 中该任务负责的共享契约，以及五轴质量、范围、复用和红线。

你不得修改业务代码、测试、fixture、依赖、锁文件、任务状态或 main。唯一允许写入并
提交的是 source worktree 的 `handoffs/TASK-005A.md` Reviewer 部分。Verdict 只能为
`APPROVE` 或 `REJECT`；不得自行修复任何 finding。

## 固定对象与启动门禁

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main review authorization：动态运行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005A-REVIEWER-CODEX.md`
- Required authorization parent：`3ee490c19950482ecd014668ce510ba5c742b743`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Implementation base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Reviewed implementation head：`85cd5362460044773317a48cbaae58e55aa735af`
- Required identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

开始时 main 必须位于动态 authorization commit、该 commit 是 Required authorization
parent 的单一直接后继、main 干净；source 必须处于固定 head、分支正确且干净。main 的
TASK-005A 状态必须为 `IN_REVIEW`。source 从 assignment 前 base 创建，source 内
任务/状态文件的历史 `BLOCKED/UNASSIGNED` 是预期快照，不能阻塞或被修改。

任一 SHA、父链、身份、洁净度、范围或授权不符，立即报告 `BLOCKED`。不得 stash、
reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。审查期间你
独占 source worktree，其他写入会话不得并发写 main 或 source。

## 必读

完整读取 source 的：

1. `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`
2. ADR-002、ADR-003、ADR-005、ADR-006、ADR-007 与 `docs/REUSE_REGISTER.md`
3. `tasks/TASK-005A-local-model-shared-contracts.md`、`handoffs/TEMPLATE.md`
4. source `handoffs/TASK-005A.md` 和本 Reviewer 包

从 main 读取动态 authorization、TASK-005A 任务卡与 Project Status，确认实时审查
控制面。先用 Codebase Memory 图谱定位配置模型、公开领域契约、`complete_stage` 与
Artifact 索引的调用/类型边界；图谱不足才读精确文件。不得以 Implementer 自报或测试
数量替代独立验证。

## Git、范围与红线门禁

确认：

1. implementation head 的唯一父提交为 base，非 merge/amend/rebase；
2. base...head 精确为以下 8 个路径：
   - `config/settings.example.yaml`
   - `handoffs/TASK-005A.md`
   - `src/youtube_intel/config.py`
   - `src/youtube_intel/domain.py`
   - `src/youtube_intel/state.py`
   - `tests/integration/test_state_store.py`
   - `tests/unit/test_contracts.py`
   - `tests/unit/test_state_transitions.py`
3. `pyproject.toml`、`uv.lock` 相对 base 字节不变；无 migration、Provider、
   `transcripts.py`、`discovery.py`、CLI、任务/ADR、真实数据、凭证、模型、媒体、
   cache 或构建产物改动；
4. 复用仅为既有 Pydantic、SQLite/Artifact Repository 与标准库；未复制或引入外部
   模型/SDK/ORM/迁移框架。

真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体下载、
mlx-whisper/Ollama 安装或服务、模型下载、真实 Vault/密钥与任何文件删除均不授权，
不得运行。

## 必须独立复跑

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
git diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...85cd5362460044773317a48cbaae58e55aa735af
```

Implementer 自报 focused 52/10/34、全量 250；记录实际计数。`uv sync --locked` 仅可
补齐既有锁定包缓存；build 必须 offline。检查 sdist/wheel 仍包含
`youtube_intel/migrations/001_initial.sql` 后，只可清理本轮生成且被忽略的 `dist/`。

## 四组独立探针

### A：配置与资源门禁只表达、且 fail-closed

以不复用现有测试的输入，验证 transcription 固定 revision/权重哈希/参数策略、固定
解码参数、8 GiB/6 GiB/2_000_000_000 边界和示例值。验证 Local Scoring：只接受
`http` loopback `127.0.0.1`、`localhost`、`::1` 的空路径 base URL；拒绝非 http、
非 loopback、userinfo、query、fragment、非空 path、周边空白、错误 digest、描述
`-1`/`20001` 与 transcript `0..2`。确认错误/repr 不泄露任何配置的敏感环境变量名或
假值，也没有导入/调用模型、Provider 或网络。

### B：公开领域对象与最终策略不可被混淆

构造并尝试破坏 frozen `TranscriptSample`、`ScoringInput`、`ScoringDecision` 和
`ScoringOutcome`：sample 的 selected count、完整哈希 binding、`sampling-v1`、最小
内容边界、输入 hash 不匹配必须拒绝；评分恰等于/略低于 threshold、模型建议同/不同的
组合必须使 final decision 严格等于 `score >= threshold`，且 model suggestion 保持在
`ScoreResult` 未被覆盖。审查公开注解与 `__all__`：不得以自由 `dict`、`Any`、宽
`object`、`cast` 或 `type: ignore` 绕过这些契约。

### C：真实 SQLite 评分摘要的单事务与回滚

使用真实临时 SQLite 和不同于既有断言的 job/video/artifact/provider-call，验证只允许
`TRANSCRIPT_READY -> SCORED` 携带有效 `ScoringSummaryWrite`；缺 summary、在其他
转换携带 summary、bool/NaN/infinity/越界 score、pipeline/job CAS 失配均 fail-closed。
对 artifact、provider call、评分摘要、pipeline/job 成功的各故障点注入失败：每次均
不得留下 Artifact/Provider call/score/should_summarize/Pipeline/Job 的部分写入。确认
成功路径将 `ScoreResult` 模型建议与最终 `ScoringSummaryWrite.should_summarize` 的
职责保持分离。

### D：Artifact 清理索引不是文件删除器

使用真实临时 SQLite 验证 `mark_artifact_deleted` 的有效 hash CAS、未知 ID、哈希不符、
重复调用与 UTC 参数；验证 `list_expired_artifacts` 只返回指定 retention class、未删除、
已过期记录，遵守正 limit 和 `expires_at/created_at/artifact_id` 稳定排序。确认 API 不
删除/枚举未登记路径，且文件系统不因这些方法改变。

## 验收、Finding 与 evidence

逐项判定 TASK-005A 的 5 个 AC，以及 ADR-007 L-02 至 L-15 中属于共享契约切片的
条款；明确 L-07/L-09/L-12/L-13 等仍由后续任务实现的边界。按 correctness、
architecture、security、performance、readability 五轴审查。

- 任一未解决 P0/P1、必需门禁失败或探针无法独立证明：`REJECT`；
- 仅明确 P2/P3 且所有 AC/本任务 ADR 条款通过：可 `APPROVE`；
- 不得因为后续未经授权的模型/媒体/网络路径未运行而拒绝。

只在 `handoffs/TASK-005A.md` 追加 Reviewer 结论，然后只暂存该文件并提交：

```text
docs: review TASK-005A shared contracts
```

evidence commit 的唯一父提交必须是 reviewed head，且只修改 handoff。提交后 source/
main 均应干净；不得 merge、push、修改状态、启动 TASK-006/007 或清理 worktree。

## 回传格式

```text
Task: TASK-005A
Role: Independent Codex Reviewer
Reviewed implementation head: 85cd5362460044773317a48cbaae58e55aa735af
Review evidence commit:
Checks rerun:
Probe A configuration/resource boundary:
Probe B public contracts/final policy:
Probe C SQLite scoring atomicity:
Probe D Artifact cleanup index:
Acceptance matrix:
ADR-007 traceability:
Findings: P0/P1/P2/P3
Five-axis/scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
