# TASK-013 交接报告

## 元数据

- Task: `TASK-013`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `main@2a59dfe3860161a5989f2c08161f03c73aa4ca86`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-013-rebuild`
- Branch: `codex/task-013-e2e-acceptance-rebuild`
- Head commit: use `git rev-parse HEAD` after this handoff commit.

## 目标与范围

- 任务目标：用可重复离线服务流重新建立 MVP 验收证据，取代直接 SQLite 状态推进的旧 E2E 方法。
- 允许修改：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、本交接文件。
- 实际修改：两份新 e2e 测试、验收报告和本交接文件；未新建夹具，因为复用已登记的固定字幕夹具。
- 明确未做：未修改生产代码、CLI、配置、Schema/migration、依赖、锁文件、既有测试或测试配置；未触发真实资源。

## 服务流与复用

| 用户情形 | 真实生产边界 | 外部边界 |
|---|---|---|
| 人工字幕 | `PipelineOrchestrator` → `SubtitleAcquisitionService.fetch` | Fake `SubtitleAdapter` + `manual_en.json3` |
| 自动字幕 | `PipelineOrchestrator` → `SubtitleAcquisitionService.fetch` | Fake `SubtitleAdapter` + `auto_zh.vtt` |
| 无字幕 | `SubtitleAcquisitionService` 的 `TranscriptionRequired` → `LocalTranscriptionService.transcribe` | Fake Whisper executor、受控音频 Artifact |
| 低价值 | `RepositoryBackedScoringService` → production orchestrator 低价值完成路径 | Fake 本地评分；云 Fake 与凭据 resolver 为零调用 |
| 高价值 | `RepositoryBackedScoringService` → `RepositoryBackedAnalysisService` → `ObsidianNoteSink` → `WeeklyReportService` | Fake 评分/分析/凭据；临时 Vault |

- Reuse decision: `DIRECT` — 现有项目服务、已有锁定依赖与 Python 标准库；外部边界全部 Fake Adapter。
- 来源/许可证：未复制第三方代码，未添加依赖或许可证义务；已登记依赖及其许可证继续以 `docs/REUSE_REGISTER.md` 为准。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| PRD 10.1 五类样例 | PASS | `tests/e2e/test_mvp_flow.py` 的五个场景和真实服务组合。 |
| PRD 10.2 幂等 | PASS | 重跑断言稳定的 DB 计数、Fake 调用计数与周报字节。 |
| PRD 10.3 失败恢复 | PASS | `tests/e2e/test_failure_recovery.py` 参数化六个服务边界。 |
| PRD 10.4 云关闭 | PASS | 云 Fake/credential resolver 皆零调用且流程完成。 |
| PRD 10.5 昂贵步骤不重调 | PASS | 成功后再次运行不会增加 Whisper、评分、分析调用计数。 |
| PRD 10.6–10.8 | PASS | 全量质量命令、脱敏扫描、Frontmatter/双链/用户区保留见验收报告。 |
| 真实资源冒烟 | BLOCKED | `NOT AUTHORIZED`；未执行。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 84 packages resolved。 |
| `uv sync --locked --offline` | PASS | 61 packages checked。 |
| `uv run python -m pytest tests/e2e -m 'not network and not cloud'` | PASS | 8 passed。 |
| `uv run python -m pytest tests/e2e/test_mvp_flow.py` | PASS | 2 passed。 |
| `uv run python -m pytest tests/e2e/test_failure_recovery.py` | PASS | 6 passed。 |
| `uv run python -m pytest` | PASS | 444 passed。 |
| `uv run mypy src` | PASS | 23 source files，无问题。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常。 |
| `uv build --offline` | PASS | sdist 和 wheel 均生成。 |

## Diff 复核

- 修改文件：仅任务允许的两份 e2e 测试、验收报告和本交接文件。
- 是否存在任务范围外修改：待提交前最终 `git diff`/`git status` 核验。
- 是否存在生成文件或格式化噪声：`dist/`、`.venv/` 为忽略构建/环境产物，未纳入改动。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：初版夹具错误调用不存在的 `get_cursor`；改为既有集成测试使用的最小元数据预置。初版 retry policy 错用 `max_attempts` 参数；已按生产 `RetryPolicy` 接口改正。手动编辑 Note 后周报哈希保护拒绝重跑；测试顺序调整为先验证周报幂等，再验证笔记用户区保留。
- 跳过检查及原因：真实资源冒烟未授权。
- 剩余风险：离线 Fake 不替代真实 Provider、网络、模型质量、模型资源或真实 Vault 验收；用户编辑后的周报可信哈希刷新仍由后续策略处理。
- `DECISION NEEDED`: `None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：use `git rev-parse HEAD` after this handoff commit.
- 复现/验证说明：按验收报告的三条 e2e 命令运行；真实路径保持未授权。

## Reviewer 结论（2026-07-26，rebuild 独立审查）

- Reviewer agent/session：Codex（全新独立 Reviewer）
- 审查授权：main 中 `agent-prompts/TASK-013-REBUILD-REVIEWER-CODEX.md` 的最后修改提交为 `a7c670c232e3129972138dd45a1a0c21877e35e0`；main 的 TASK-013 状态为 `IN_REVIEW`。
- 审查对象：`codex/task-013-e2e-acceptance-rebuild@0a9e16887e7dc0b287be941a34e2908766e3992e`，唯一父提交为 `2a59dfe3860161a5989f2c08161f03c73aa4ca86`；审查开始时 worktree 干净。

### 已重新运行的检查

| 命令/检查 | 结果 | 关键证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages`。 |
| `uv sync --locked --offline` | PASS | `Checked 61 packages`，未联网。 |
| `uv run python -m pytest tests/e2e -m 'not network and not cloud'` | PASS | `8 passed in 7.35s`。 |
| 全受审 Diff 的 `git diff --check 2a59dfe...HEAD` | PASS | 退出码 0。 |
| 允许路径核验 | PASS | 仅 `tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`docs/ACCEPTANCE_REPORT.md`、本 handoff；未触及生产 CLI/编排、配置、Schema/migration、依赖、锁文件、测试配置或既有测试。 |
| 凭据格式扫描 | PASS | 对工作树执行报告中同一 `sk-...` / `AIza...` PCRE 扫描（排除锁文件与 tokenizer 资源），退出码 1、无匹配；未见真实密钥格式。 |

### 独立探针与发现

- 五路径/无状态捷径：人工、自动字幕通过 `SubtitleAcquisitionService` 的不同 Fake 轨道；无字幕由 `TranscriptionRequired` 进入 `LocalTranscriptionService`；没有测试手写 `complete_stage` 或 SQL 更新。`advance_pipeline` 仅用于最小 `DISCOVERED -> METADATA_READY` 初始夹具准备。低价值的云 Fake/credential resolver 为零调用；高价值经过评分、分析、笔记和周报生产服务。
- 隐私与范围：临时 Vault、SQLite、DATA 和 Fake Adapter 均在 pytest `tmp_path` 下；真实 YouTube、Whisper 模型/ffmpeg、Ollama/模型、OpenAI/API/密钥/付费调用、网络、真实 Vault、媒体及 launchd 均未执行且仍为 `NOT AUTHORIZED`。未复制第三方代码或引入依赖；复用结论仍为既有 `DIRECT` 组件与 Python 标准库，无新增许可证义务。
- **P1-1（阻断）— 未证明进程重启后的恢复，PRD 10.5 不能标记 PASS。** `tests/e2e/test_failure_recovery.py:30-40` 在失败、恢复与重跑期间始终复用同一个 `_OfflineMvpFlow` 实例；`tests/e2e/test_mvp_flow.py:300-303` 将 `TranscriptReady`、评分和分析结果保留在进程内 `transcripts`、`scores`、`analyses` 字典，且下游服务直接读取这些字典（例如 `:450-451`、`:474`、`:503-504`）。测试没有销毁并从同一 SQLite/DATA/Vault 重建服务组合，因此无法证明成功产物会在进程内存丢失后由持久化 Artifact/Provider-call/Job 恢复，也无法证明昂贵步骤不被重新调用。现有 8 项 E2E 通过不能覆盖这一 PRD 10.5 和任务级恢复验收缺口。

### 跳过的门禁

依据审查 prompt 的“发现 P0/P1 后停止未开始的无关门禁”规则，未执行：两个单文件 pytest 命令、全量 pytest、mypy、Ruff、CLI help 和离线 build。它们没有被表述为通过。

### PRD 10 验收复核

| PRD 项 | Reviewer 状态 | 说明 |
|---|---|---|
| 10.1 | PASS | 五个固定用户情形使用所列生产服务边界。 |
| 10.2 | PASS | 同实例重跑的 Provider-call/Artifact/Report/Job 计数及外部 Fake 调用不变。 |
| 10.3 | PASS | 六个阶段的单次失败后恢复在离线 E2E 中通过。 |
| 10.4 | PASS | 云关闭时云 Fake 与 resolver 零调用且流程完成。 |
| 10.5 | FAIL | P1-1：未重建进程/服务组合，不能证明重启恢复和缓存复用。 |
| 10.6 | BLOCKED | P1 后停止未开始的全量质量门禁。 |
| 10.7 | PASS | 可复现扫描无匹配；Fake credential 仅为内存固定测试值。 |
| 10.8 | PASS | 临时 Vault 验证可解析 Frontmatter、双链与 `我的思考` 保留。 |

- Findings：P0=0；P1=1（P1-1）；P2=0；P3=0。
- Verdict：`REJECT`
- 未解决 P0/P1：P1-1。修复必须仅在已授权的两份 E2E 测试/fixtures/验收报告/handoff 范围内，加入从同一持久化 SQLite/DATA/Vault 重新构建服务组合并验证后续阶段恢复、昂贵 Fake 调用不重复的回归证据；不得修改生产编排、状态、Schema、依赖或真实资源边界。

## Correction 1（2026-07-26，Implementer；待独立审查）

- Authorization/lineage: main 的替代授权提示词最新提交为 `9ce5bf68bf4c0608fc0a198def9c582f3e2a5389`；实现仅从 `codex/task-013-e2e-acceptance-rebuild@3cf8b5fd8e7abec8f8a6595227a8919a7a8804e1` 开始，唯一父提交为被拒绝的审查证据 `0a9e16887e7dc0b287be941a34e2908766e3992e`。未访问历史拒绝 worktree。
- Reuse decision: `DIRECT` — 既有项目服务、锁定依赖和 Python 标准库；字幕、Whisper、评分、分析与凭据边界仅用测试内 Fake Adapter；无第三方代码复制、无新增依赖或许可证义务。
- RED: 新增 `restore=True` 重建断言后，`uv run python -m pytest tests/e2e/test_mvp_flow.py::test_mvp_service_flow_covers_five_user_scenarios_and_is_idempotent -q` 先失败，证明原组合无法在既有 Vault 目录上重新构建（`FileExistsError`）。初始运行还暴露固定测试时钟已落后于分析服务的真实 UTC 时钟，导致 `LeaseConflict`；仅将测试内固定 `NOW` 前移到 `2100-01-01`，不修改生产时钟或编排。
- GREEN / destruction boundary: 第一次完整服务流和周报完成后，测试只保留持久路径、DB 计数、周报 bytes/hash 等标量证据，删除 `report` 与整个 `flow`，再执行 `gc.collect()`。不把旧的 Repository、Provider、`transcripts`、`scores`、`analyses`、计数器或其他内存对象传给后续断言。
- Second composition / persistent recovery: 同一 pytest `tmp_path` 的 SQLite、DATA 与 Vault 上新建 `_OfflineMvpFlow(..., restore=True)`，它创建新的 Repository、服务与 Fake Provider、跳过初始 fixture 写入，且断言四个内存缓存为空。重跑 orchestration 和 `WeeklyReportService` 后，Artifact、Provider-call、Report、Job 计数与周报 bytes/hash 完全不变；Pipeline 仍为 `COMPLETE`，用户可见笔记与周报未重复。新的字幕枚举/读取、Whisper、评分、分析与凭据 Fake 计数均为 `0`。
- P1-1 scope result: 已用服务组合和持久 SQLite/DATA/Vault 证明重启后恢复及昂贵处理缓存；未使用通用 handler、直接 `complete_stage`、直接 SQL 更新或伪造 Job/Pipeline。最小 initial fixture 只在第一次组合准备 `DISCOVERED -> METADATA_READY`，重建组合不写入 fixture。
- Verification completed before commit: `uv lock --check` → `Resolved 84 packages`; `uv sync --locked --offline` → `Checked 61 packages`; `uv run python -m pytest tests/e2e -m 'not network and not cloud'` → `9 passed`; focused MVP/failed-recovery files → `3 passed` / `6 passed`; `uv run python -m pytest` → `445 passed`; `uv run mypy src` → 23 source files clean; `uv run ruff check .` → pass; `uv run python -m youtube_intel --help` → pass; `uv build --offline` → sdist + wheel. `rg --pcre2 -n '(?i)(sk-[a-z0-9]{20,}|AIza[0-9A-Za-z_-]{20,})' tests/e2e docs/ACCEPTANCE_REPORT.md handoffs/TASK-013.md` produced no match (expected exit 1). `git diff --check` passed; final Diff/path and staged-secret checks are recorded immediately before commit.
- Real-resource status: `NOT AUTHORIZED`。未使用真实 YouTube/网络、媒体、ffmpeg、Whisper/Ollama/OpenAI 模型或 API、凭据、真实 Vault、付费服务或 launchd；所有写入仅为 pytest `tmp_path`。
- This section is implementer evidence only. It does not start a Reviewer, change TASK status, merge, push, or claim an approval verdict.

## Correction 1 — Independent Reviewer 2 (2026-07-26)

- Reviewer agent/session: Codex（全新独立 Reviewer 2）
- Dynamic authorization: `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-CORRECTION-1-REVIEWER-CODEX.md` resolved to `001eaa96dfc1737169323a3e4503a9415b0b39c9`; main states TASK-013 Correction 1 is awaiting independent review / `IN_REVIEW`.
- Reviewed source: `codex/task-013-e2e-acceptance-rebuild@ae724990f6f3628a054bfca000e9e28d83f3def7`; worktree was clean; its sole parent is `3cf8b5fd8e7abec8f8a6595227a8919a7a8804e1`.

### Re-run checks completed before the blocking finding

| Command / check | Result | Evidence |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages in 9ms`. |
| `uv sync --locked --offline` | PASS | `Resolved 84 packages`; `Checked 61 packages`; existing local uv cache was read only after sandbox permission blocked normal cache access. No network or lockfile change. |
| `uv run python -m pytest tests/e2e -m 'not network and not cloud'` | PASS | `9 passed in 7.66s`. |
| Correction-1 scope/lineage/Diff check | PASS | sole parent exact; relative to original base only `tests/e2e/test_mvp_flow.py`, `tests/e2e/test_failure_recovery.py`, `docs/ACCEPTANCE_REPORT.md`, and this handoff; `git diff --check 2a59dfe...HEAD` exited 0. No production code, CLI/orchestration, config, Schema/migration, dependencies, lockfile, or test configuration changed. |
| Success-path fresh-composition review | PASS, non-blocking | `test_mvp_flow.py` deletes the first Flow/report, calls `gc.collect()`, creates `restore=True` against the same temporary SQLite/DATA/Vault, asserts new caches empty and all new expensive Fake call counts zero. This closes only the successful `COMPLETE` rerun case. |

### Blocking independent recovery probe

- **P1-1 — failed-stage recovery still depends on old in-memory objects.** `tests/e2e/test_failure_recovery.py:30-49` keeps the original `_OfflineMvpFlow` alive for each injected failure and calls `flow.run()` again. However, later production-stage shims read `self.transcripts` in scoring/analysis (`test_mvp_flow.py:438-462`) and `self.transcripts`, `self.scores`, and `self.analyses` in note writing (`:481-501`). Those dictionaries are empty in a fresh `restore=True` composition.
- Independent offline probe used a new temporary SQLite/DATA/Vault, injected the existing `scoring` failure, destroyed the first Flow, called `gc.collect()`, built `_OfflineMvpFlow(root, restore=True)`, and reran one minute later. It produced `high-value` at `TRANSCRIPT_READY` and its scoring Job at `RETRY_PENDING` with `last_error_code=LOCAL_RESOURCE`; all fresh Fake counters were `0`. The retry cannot recover the persisted Transcript Artifact because the handler attempts `self.transcripts[video_id]` instead of loading verified persistent state. The same unproven in-memory dependency applies to analysis and note recovery.
- Therefore the 9 passing E2E tests demonstrate same-process failure retries only; they do not establish the required failure recovery after destroying all composition objects, nor the requirement that recovery never depend on an old Repository/Fake/cache object. This violates the Correction 1 review package item 3 and leaves the original persistence/restart acceptance incomplete.

### Stopped / not run after P1

- Per the review authorization, after P1-1 I did not start the remaining unrelated mandatory gates: the two focused E2E file commands, full pytest, mypy, Ruff, CLI help, offline build, or additional resource/privacy probes. They are not represented as passing.
- No real YouTube/network/media/ffmpeg/Whisper model/Ollama/OpenAI/API/credential/paid service/real Vault/launchd path was used. The sole independent probe used Python `tempfile` with Fake providers and temporary SQLite/DATA/Vault only.

### Reviewer matrix and conclusion

| Review requirement | Result | Evidence |
|---|---|---|
| First complete run destruction + fresh complete-composition rerun | PASS | New `restore=True` flow, empty caches, zero new expensive Fake calls, unchanged persistent counts/report bytes on the successful terminal path. |
| Persistent artifacts/provider calls/jobs/pipeline/user-visible files avoid duplicate work after terminal restart | PASS | Same successful terminal-path assertions; no old Flow object is retained. |
| All injected boundary failures recover after a fresh composition without old memory | FAIL / P1-1 | Scoring recovery probe leaves `RETRY_PENDING` / `TRANSCRIPT_READY`; failure test retains old Flow dictionaries. |
| Stable same-process rerun | PASS but insufficient | Existing failure test verifies unchanged counts/calls only while retaining the first Flow. |
| Scope, reuse/license, and real-resource boundary | PASS | DIRECT existing services/locked dependencies/stdlib; no third-party code or dependency change; only temporary Fake paths. |

- Findings: P0=0; P1=1 (P1-1); P2=0; P3=0.
- Verdict: `REJECT`.
- Required correction: within the already authorized E2E/fixture/report/handoff scope, reconstruct a brand-new composition after each applicable injected failure and make its retry stages load and verify the required persisted Artifact/Provider-call/Job/Pipeline data rather than prior in-memory dictionaries. Prove zero fresh expensive Fake calls whenever the verified persistent cache should satisfy the stage. Do not modify production code, state/Schema, dependencies, or real-resource boundaries.

## Correction 2（2026-07-26，Implementer；待独立审查）

- Authorization/lineage: main 的 Correction 2 授权提示词最新提交为 `9b5c4b53537ba0dfd2319f849d5269a1a033c568`；唯一 source 是 `codex/task-013-e2e-acceptance-rebuild@4aecab7c3f88f0a108ee815c05436d12dd0dfdd8`，其唯一父级为 Correction 1 实现 `ae724990f6f3628a054bfca000e9e28d83f3def7`。未访问历史 `task-013` worktree/branch。
- Reuse decision: `DIRECT` — 现有服务、锁定依赖与 Python 标准库；外部边界继续仅为测试内 Fake Adapter。未复制第三方代码，未新增依赖或许可证义务。
- RED: 评分失败后删除首次 `_OfflineMvpFlow` 并 `gc.collect()`，从同一临时 SQLite/DATA/Vault 创建 `restore=True` 组合。重启后的评分 Job 留在 `TRANSCRIPT_READY`/`RETRY_PENDING`，因为旧 shim 从 `self.transcripts[video_id]` 读取。该复现没有使用旧 Repository、Fake、缓存或 SQL 更新。
- GREEN / persistent recovery: 新组合的恢复 shim 只读 SQLite 中目标视频的 Artifact 索引，验证其 DATA 根边界、SHA-256 与 UTF-8 后构造恢复所需输入；评分、分析和笔记阶段同样从已验证的结构化 Artifact 读取必要的已完成结果。没有直接 `complete_stage`、SQL 更新、通用 handler 或伪造 Job/Pipeline；状态推进仍由 `PipelineOrchestrator` 和现有应用服务完成。
- Fresh composition boundary: 每个字幕、转写、评分、分析、笔记和周报注入失败后都删除第一次 Flow；周报失败额外删除仍持有旧 Repository 的 `WeeklyReportService`。第二次 `_OfflineMvpFlow(..., restore=True)` 使用新 Repository、服务、Fake Provider、缓存和无冲突 Job ID 前缀，并先断言所有新缓存与昂贵 Fake 计数均为空/零。
- Scoring restart proof: `scoring` 场景中，新组合保留并验证已持久的 canonical Transcript Artifact；新字幕/Whisper Fake 调用为 `0`，只作失败的评分 1 次和后续必要分析 1 次，凭据 resolver 1 次，最终完成笔记与周报。之后稳定重跑不改变 Artifact、Provider-call、Report、Job 计数、视频笔记数或周报数。
- Other failure boundaries: 字幕、转写、分析、笔记和周报同样在新组合而非同进程 retry 中恢复至 `COMPLETE`；所有完成后的稳定重跑无重复输出。
- Verification before final gate: scoring RED → FAIL；focused scoring recovery → `1 passed`; failure-recovery file → `6 passed`; MVP flow file → `3 passed`; `uv lock --check` → 84 packages; `uv sync --locked --offline` → 61 packages; E2E offline marker → `9 passed`; full pytest → `445 passed`; `uv run mypy src` → 23 source files clean; `uv run ruff check .` → pass (test import order mechanically fixed, then rechecked); CLI help → pass; `uv build --offline` → sdist + wheel. Secret scan, final Diff/path and staged checks follow immediately before commit.
- Real-resource status: `NOT AUTHORIZED`。未使用真实 YouTube/网络、媒体、ffmpeg、Whisper/Ollama/OpenAI 模型或 API、凭据、真实 Vault、付费服务或 launchd；所有写入仅在 pytest `tmp_path`。
- This is implementer evidence only; it does not start a Reviewer, change task status, merge, push, or claim approval.
