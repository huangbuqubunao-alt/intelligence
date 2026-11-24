# TASK-005 字幕获取与规范化 — Codex Correction 2

## 身份与目标

你是 TASK-005 原 Codex Implementer，负责修复第二次独立 Reviewer 在 evidence
`5bb750e8d2f1336b321dbca64e7c409f66853b0f` 中确认的 3 个 P1，并补充对应的
RED/GREEN 行为回归。第二次 Reviewer 已结束且不得修代码；本轮不得争辩、弱化测试、
只隐藏异常显示或扩大产品范围。

你不负责重新审查、主控验收、main 整合、ADR-007、TASK-006/007 或任何真实网络、
认证、媒体、ffmpeg、Vault/密钥操作。

## 固定恢复状态

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main correction authorization：动态执行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-CORRECTION-2-CODEX.md`
- Correction authorization parent：
  `a3954bf782430678fa5e0040084bf0d907a52d05`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Original implementation：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- First review evidence：`515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Correction 1：`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Second review evidence / starting HEAD：
  `5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Starting HEAD parent：`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

开始时 main 必须位于动态 correction authorization commit 且干净；source 必须位于
固定 second review evidence HEAD、分支正确且干净。任一基线、父链、身份、洁净度、
Review Verdict 或范围不符，立即停止并报告 `BLOCKED`。不得 stash、reset、
checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

不得 amend/rebase 既有实现、审查或 Correction 1。Correction 2 必须创建新的非
merge commit，唯一父提交为 `5bb750e8...`。

## 必读与事实优先级

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
4. `tasks/TASK-005-subtitle-pipeline.md`
5. `agent-prompts/TASK-005-IMPLEMENTER-CODEX.md`
6. `agent-prompts/TASK-005-REVIEWER-CODEX.md`
7. `agent-prompts/TASK-005-CORRECTION-1-CODEX.md`
8. `agent-prompts/TASK-005-REVIEWER-2-CODEX.md`
9. `handoffs/TASK-005.md` 的全部 Implementer/Reviewer/Correction 历史
10. 本 Correction 2 包

技术事实以第二次 Reviewer 的独立反例为准。ADR-006 已足以冻结期望，不需要新 ADR。
发现修复必须修改 `state.py`、Schema、migration、`complete_stage`、domain 公共
对象、依赖/锁或范围外文件时，立即 `DECISION NEEDED`。不得使用 wrapper、
monkey patch、`Any`、宽 `object`、自由 `dict`、`cast`、`type: ignore` 或仅靠
`raise ... from None` 隐藏问题。

## 唯一允许修改的路径组

1. `src/youtube_intel/transcripts.py`
2. `src/youtube_intel/providers/subtitles.py`
3. `tests/unit/test_subtitle_policy.py`
4. `tests/integration/test_subtitle_provider.py`
5. `tests/fixtures/subtitles/**`
6. `handoffs/TASK-005.md`

不得修改 `domain.py`、`tests/unit/test_contracts.py`、`state.py`、migration、
配置、CLI、discovery/youtube Adapter、`pyproject.toml`、`uv.lock`、任务/ADR 或
main。不得新增产品模块或公开测试 hook；可在两个允许的产品文件内提取窄的具名私有
helper/component，避免继续扩大 Service/fetch 的状态交织。

## P1 修复矩阵

### P1-1：所有外层异常图必须真正脱敏

Reviewer 证据：

- `providers/subtitles.py:564-585`、`:634-688` 的真实 Adapter 目录错误；
- `transcripts.py:1579-1587` 的已索引 canonical 非法 UTF-8；
- 外层 `TranscriptError.__context__` 仍保存原始 `DownloadError` 或
  `UnicodeDecodeError.object`，可读取正文 marker、临时 URL 和绝对路径。

要求：

- 在 Adapter、cache decode 和 Service 包装边界捕获敏感底层异常时，只提取枚举型
  错误码、retryable、阶段和已脱敏的固定诊断；不得把原异常对象、args、payload、
  header、正文、URL 或绝对路径保存到新对象、闭包、属性或 diagnostic；
- 必须在离开活动 `except` 后抛出新的安全异常，或采用能独立证明
  `__cause__ is None` 且 `__context__ is None` 的等价结构；
- `raise ... from None` 只隐藏展示，若 `__context__` 仍引用原异常则不合格；
- 对完整异常图递归检查 message、args、属性、`__cause__`、`__context__` 和格式化
  traceback；不得出现独立 marker、字幕 bytes、临时 URL 或绝对路径；
- 保留既有错误码、retryable、stage 和 `video_id`，不能用统一
  `PROVIDER_UNAVAILABLE` 掩盖安全转换；
- malformed JSON3、非法 UTF-8、Adapter `DownloadError`、canonical cache decode、
  recovered raw 和 Service 外层路径均建立 RED/GREEN 回归。

### P1-2：Provider-call 状态、reservation 生命周期与真实竞态必须一致

Reviewer 证据：

1. 首次正文读取保存 nonretryable `PERMISSION_DENIED`，重复同一 request 时漂移为
   `PROVIDER_UNAVAILABLE`；
2. 已取得 reservation 后原子文件写入抛 `PermissionError`，Provider call 仍为
   active `PENDING`、owner/300 秒 lease 未清除；
3. 两个真实 SQLite Service 同时通过“无记录”预检时都执行目录枚举，
   `enum_total=2`，只有正文读取被去重。

要求：

- 对既有 `FAILED_FINAL`，按持久化的合法 `ErrorCode`、retryable、stage 和安全消息
  稳定重放；只有明确由本任务记录的 all-invalid 终态才映射
  `TranscriptionRequired(ALL_CANDIDATES_INVALID)`，不得把其他终态泛化；
- raw request hash 按 ADR-006 T-09 只使用调用前已知的稳定输入：video ID、有序语言
  偏好、selection/format policy、Provider/版本和 refresh generation；临时 URL 不
  得进入 key；
- 在任何远端目录枚举或正文读取前，用现有 `provider_calls` CAS/租约能力取得上述
  稳定 request 的 reservation。竞争失败方必须零目录枚举、零正文读取、零文件写入，
  并根据当前 record 返回稳定结果或安全 retryable 错误；
- reservation owner 才能枚举目录和读取正文；无轨道、无匹配、all-invalid、Provider
  错误、解析失败、原子文件失败、Artifact/Provider/Pipeline 提交失败等所有退出路径，
  都必须把 reservation 按同一原始 `AppError` 语义完成或失败，不能留下 active
  `PENDING`；
- retryable 失败清除 owner/lease 并写入可重试时间；nonretryable 失败保存原
  `ErrorCode` 并进入稳定终态。释放/持久化失败不得覆盖原始业务错误；
- 两个 Service 使用真实临时 SQLite 和 barrier 竞争时，最多一个目录枚举、一个正文
  读取；失败方不得耗尽 Job attempts、推进 Pipeline 或产生文件/DB 副作用；
- 默认 2 秒 Job backoff、300 秒 Provider lease、stage/file failure、终态重复调用、
  no tracks/no match/all-invalid 和 SUCCEEDED cache 全矩阵建立 RED/GREEN 回归；
- 不修改 TASK-003 Repository 或 Schema，不以进程内锁、sleep、轮询、宽 wrapper
  掩盖跨 Service CAS 问题。

### P1-3：verified raw/canonical provenance 必须与当前请求严格一致

Reviewer 证据：

1. 当前请求语言为 `("en",)`，raw metadata token 使用结构合法的
   `requested_language="fr"` 仍重建并推进；
2. 已索引 raw 文件为越界 symlink 时返回 `PERMISSION_DENIED`，而缓存失效契约要求
   安全 `LOCAL_RESOURCE`；
3. ordinary canonical Artifact 的 `model` 被篡改为非空值后仍命中，返回时又以 raw
   的 `model=None` 掩盖索引不一致。

要求：

- verified raw 的 artifact key/path、metadata token 和文件内容必须共同、可逆地绑定
  当前 video、raw request hash、有序语言偏好、实际触发的 requested language、
  source type、actual language、format、Provider/版本、producer/selection/format
  version 和 refresh generation；
- `requested_language` 必须来自当前有序偏好并与 key/path/token 的选择结果一致；
  不得只验证 token 结构合法；
- canonical cache 必须验证记录自身的 kind、video、storage root、deleted_at、path、
  SHA、provider、model、producer/normalization/quality version、raw provenance 和
  metadata token；不得用 raw 字段覆盖或掩盖 canonical 记录中的不一致；
- 对 yt-dlp manual/auto 当前预期为空的 `model`，非空或与 raw/current expectation
  不一致必须 fail-closed；
- 已索引 cache 文件缺失、篡改、symlink/realpath 越界、token/path/provenance 不一致
  均零网络返回 nonretryable `LOCAL_RESOURCE`，Job/Pipeline 不推进；这不改变新写入
  目标的 DATA 边界/权限错误仍按 ADR-006 T-11 使用 `PERMISSION_DENIED`；
- valid raw→new canonical、ordinary canonical hit、第二次稳定 hit、语言/token、
  provider/model、producer/version、format、path、symlink 和 quality failure 建立
  RED/GREEN 矩阵。

## P2 处理边界

第二次 Reviewer 仍保留：

- P2-1：Service/文件/cache/Provider 状态职责聚合，integration tests 依赖私有 hooks；
- P2-2：name `runs` 和空 language bucket 的嵌套 metadata 资源放大面。

本轮不要求新增公共模块、依赖或未冻结资源阈值。修复三个 P1 时必须：

- 使用窄的具名私有 helper 分离安全异常转换、reservation 生命周期和 provenance
  校验，避免继续扩大 `fetch`、`_load_cached` 或重复分支；
- 测试优先走公开 Adapter/Service、真实 SQLite 和 Fake transport；不得新增公开
  test hook；
- 不使嵌套 metadata 处理更无界，不复制完整 payload 或异常对象。

若 P2 已形成新的正确性、安全或资源无界缺陷，则按 P1 修复；否则在 handoff 保留并
交给第三次 Reviewer 独立判断，不得谎称已关闭。

## TDD 与检查

先把第二次 Reviewer 的三个反例组写成失败测试并记录 RED，再逐项实现 GREEN。不得
删除、跳过、放宽既有测试或修改期望以适应错误行为。

必须运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest tests/unit/test_subtitle_policy.py
uv run python -m pytest tests/integration/test_subtitle_provider.py
uv run python -m pytest
uv run mypy src
env MYPYPATH=src uv run mypy -c 'from pathlib import Path
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.transcripts import TranscriptRepository
repository: TranscriptRepository = SQLiteStateRepository(Path("state.sqlite3"))'
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 5bb750e8d2f1336b321dbca64e7c409f66853b0f...HEAD
```

`uv sync --locked` 只允许既有锁定包；不得下载新依赖、重锁或改清单。build 必须
offline，并验证 migration、`transcripts.py`、`providers/subtitles.py` 仍进入
sdist/wheel；只清理本轮被忽略的 `dist/`。

额外检查：

- `pyproject.toml`/`uv.lock` 与 base 字节不变；
- Correction 2 Diff 只属于 6 个允许路径组；
- 完整 `b28f52d...HEAD` 产品范围仍属于原 8 个路径组；
- source 无真实 URL/响应、密钥、Cookie、媒体、数据库、cache 或构建产物；
- 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
  真实 Vault/密钥不得运行。

## Handoff 与提交

保留全部历史证据，在 `handoffs/TASK-005.md` 追加
`Implementer Correction 2`，逐项记录：

- 三个 P1 的 RED/GREEN 输入、期望/实际、测试和代码位置；
- exception graph 递归脱敏证据；
- pre-enumeration reservation、终态重放、失败释放和真实双 Service 竞态矩阵；
- raw/canonical provenance、metadata token、model 和 symlink 分类矩阵；
- P2 是否改善或继续保留；
- 全部命令、Diff、复用/许可证、跳过项和剩余风险。

只在全部门禁通过后创建新 commit：

```text
fix: close subtitle recovery and redaction gaps
```

提交后确认：

- 新 commit 唯一父提交为
  `5bb750e8d2f1336b321dbca64e7c409f66853b0f`；
- 不 amend/rebase 历史；
- worktree 干净；
- TASK-005 状态仍由 main 控制面保持 `IN_PROGRESS`，不得自行改状态或启动 Reviewer；
- 不 merge、push、清理分支/worktree。

## 回传格式

```text
Task: TASK-005
Role: Codex Implementer (Correction 2)
Starting review evidence: 5bb750e8d2f1336b321dbca64e7c409f66853b0f
Correction commit:
Changed files:
P1-1 exception-graph redaction evidence:
P1-2 Provider state/reservation evidence:
P1-3 provenance/cache evidence:
P2 handling:
Checks:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
