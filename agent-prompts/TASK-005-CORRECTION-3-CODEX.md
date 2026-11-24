# TASK-005 字幕获取与规范化 — Codex Correction 3

## 身份与目标

你是 TASK-005 原 Codex Implementer，负责修复第三次独立 Reviewer 在 evidence
`30c665181db77607648aa1a6fdbb1d5502b71d7d` 中确认的 3 个 P1，并补充对应的
RED/GREEN 行为回归。第三次 Reviewer 已结束且不得修代码；本轮不得争辩、弱化测试、
只处理已知 yt-dlp Adapter 而忽略公共 Provider 边界，或把真实资源缺陷继续降级为
P2。

你不负责重新审查、主控验收、main 整合、ADR-007、TASK-006/007 或任何真实网络、
认证、媒体、ffmpeg、Vault/密钥操作。

## 固定恢复状态

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main correction authorization：动态执行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-CORRECTION-3-CODEX.md`
- Correction authorization parent：
  `2c8492b54e045547b7b3bad742419d8f6fdf0089`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Original implementation：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- First review evidence：`515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Correction 1：`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Second review evidence：`5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Correction 2：`f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Third review evidence / starting HEAD：
  `30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Starting HEAD parent：`f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

开始时 main 必须位于动态 correction authorization commit 且干净；source 必须位于
固定 third review evidence HEAD、分支正确且干净。任一基线、父链、身份、洁净度、
Review Verdict 或范围不符，立即停止并报告 `BLOCKED`。不得 stash、reset、
checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

不得 amend/rebase 既有实现、审查或 Correction。Correction 3 必须创建新的非 merge
commit，唯一父提交为 `30c6651...`。

## 必读与事实优先级

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
4. `tasks/TASK-005-subtitle-pipeline.md`
5. TASK-005 原 Implementer、三个 Reviewer、Correction 1/2 的全部任务包
6. `handoffs/TASK-005.md` 的全部历史证据
7. 本 Correction 3 包

技术事实以第三次 Reviewer 的独立反例为准。现有 ADR-006 已足以定义 Service 安全
边界和资源 fail-closed；不需要新产品阈值。若 P1-2 的可信 provenance binding 在
现有 Artifact/Provider-call 字段内确实无法实现，必须停止并输出
`DECISION NEEDED`，按 ADR-006 T-13 升级，而不是伪造验证或修改 Schema。

不得使用 wrapper、monkey patch、`Any`、宽 `object`、自由 `dict`、`cast`、
`type: ignore`、进程内锁或仅靠异常显示隐藏问题。

## 唯一允许修改的路径组

1. `src/youtube_intel/transcripts.py`
2. `src/youtube_intel/providers/subtitles.py`
3. `tests/unit/test_subtitle_policy.py`
4. `tests/integration/test_subtitle_provider.py`
5. `tests/fixtures/subtitles/**`
6. `handoffs/TASK-005.md`

不得修改 `domain.py`、`tests/unit/test_contracts.py`、`state.py`、migration、
`complete_stage`、配置、CLI、discovery/youtube Adapter、`pyproject.toml`、
`uv.lock`、任务/ADR 或 main。不得新增产品模块或公开测试 hook；可在两个允许的产品
文件内提取窄的具名私有 helper。

## P1 修复矩阵

### P1-1：公共 SubtitleAdapter 错误必须在 Service 信任边界重建

Reviewer 证据：

- 自定义公开 `SubtitleAdapter` 抛出 `RATE_LIMITED/retryable/retry-after=23`；
- message 含 marker、临时 URL 和绝对路径；
- `video_id="wrong-video"`、`stage=METADATA`；
- Service 外层原样保留了敏感 message 和错误的身份/阶段。

要求：

- 把任何 `SubtitleAdapter` 实现都视为不可信 Provider，包括已经抛出的
  `TranscriptError/AppError`；`enumerate_tracks` 与 `read_track` 两个公共边界都必须
  统一重建安全应用错误；
- 只允许从 Adapter 错误保留合法 `ErrorCode`、retryable 和已验证的
  `retry_after_seconds`；message 必须改为按操作/错误码生成的固定安全文本；
- `video_id` 强制使用当前 Service 请求的 video ID，`stage` 强制为
  `ProcessingStage.TRANSCRIPT`；不得信任 Provider 提供的身份和阶段；
- 原异常 message、args、属性、cause/context、traceback、URL、路径和正文不可进入
  新异常、Provider-call 错误记录或日志；
- 新异常必须在活动 `except` 外抛出，`__cause__`/`__context__` 为 `None`；
- 不改变错误分类：RATE_LIMITED/TRANSIENT_NETWORK/PERMISSION_DENIED 等仍保持原
  code、retryable 和合法 retry-after；
- 使用至少两个 hostile Adapter：目录枚举错误和正文读取错误；覆盖错误
  stage/video、嵌套 cause/context、敏感 message，并通过完整 Service + SQLite
  路径建立 RED/GREEN。

### P1-2：cache provenance 必须绑定可信生产记录，而非仅 token 自洽

Reviewer 证据：

1. raw token `manual_subtitle -> auto_subtitle`，同步 token/path 后仍命中；
2. raw token `actual_language en -> en-US`，当前偏好 `("en",)` 仍可匹配并命中；
3. canonical quality token `s -> rs`，正文/hash 不变，伪造
   `ROLLING_CUES_DEDUPED` 后仍命中并推进。

要求：

- artifact path/token 的 canonical encoding 只证明“自洽”，不能作为可信来源；
  verified cache 必须同时绑定现有 `provider_calls` 成功记录、稳定
  `response_artifact_key`、确定性 artifact key 和文件 SHA；
- raw artifact 的 source type、requested language、actual language、source format、
  Provider/版本和 refresh generation 必须与最初 selection/Provider-call 结果绑定；
  不得仅验证“仍能匹配当前语言偏好”；
- canonical artifact 的 quality flags、provider/model、normalization/quality
  version 和 raw provenance 必须与可信生产记录/确定性 key 绑定；
- 对 `ROLLING_CUES_DEDUPED` 等无法仅从 canonical 正文证明的 flag，必须：
  - 由已验证的 raw 重新确定性推导并比对；或
  - 由现有 Provider-call response key/确定性 artifact key 提供不可歧义的绑定；
  不能只相信可修改的 path token；
- 普通 verified cache 命中仍须满足 AC-2：不得联网或重复下载。若选择本地重新推导
  metadata，只能在必要的 provenance 验证范围内，不得重复远端获取；
- source type、actual/requested language、format、quality flags、provider/model、
  producer/version、path/token/key 任一不一致时，零网络、nonretryable
  `LOCAL_RESOURCE`，Job/Pipeline 不推进；
- valid raw→canonical、ordinary canonical hit、canonical-only rebuild、第二次稳定
  hit 和 refresh generation 保持通过；旧 Artifact 不修改、不重绑定；
- 优先复用现有 `provider_calls.response_artifact_key` 与稳定 key/path；不得修改
  `state.py`、Schema、migration 或 `complete_stage`。

如果无法在现有字段中同时满足可信 binding 与 AC-2，立即 `DECISION NEEDED`，不得
继续提交貌似通过的实现。

### P1-3：嵌套 metadata 必须流式、提前、按已有边界拒绝

Reviewer 证据：

- 一个 track name 的 `runs` 含 500,000 个单字符片段，Adapter 全量复制后才发现超过
  name 1,000 code points；
- 200,000 个 entry list 为空的 language buckets 绕过 512-track 限制，被完整遍历
  后返回普通 0 tracks。

本轮不新增产品阈值，直接从已冻结边界推导结构上限：

- name 最大 1,000 code points，因此 name `runs`：
  - 必须逐项流式验证并累计字符数；
  - 累计到第 1,001 code point 时立即 `INVALID_RESPONSE`，不得消费剩余 runs；
  - run 条目数本身也不得超过 1,000，包括空字符串/空片段，防止零长度条目绕过；
  - 不得先构建完整 `pieces`/joined string 再检查；
- 目录最大 512 tracks，因此 language bucket 数：
  - 所有 bucket 都计数，包括空列表；
  - 第 513 个 bucket 立即 `INVALID_RESPONSE`，不得继续遍历；
  - 非空 track entries 继续受总数 512 上限；
- 任一结构非法、超限或迭代异常都必须在 opener/正文读取前 fail-closed，
  nonretryable `INVALID_RESPONSE`，安全 message，无底层 payload；
- 使用可记录消费次数的自定义 iterable/sequence 建立回归，证明：
  - 500,000 runs 场景最多消费到首次越界；
  - 200,000 buckets 场景最多消费 513 个；
  - Adapter 不额外复制完整输入；
  - 1,000 run/codepoint、512 bucket/track 边界仍通过，+1 精确失败；
- R3 已通过的真实 `HTTPMessage`、track/name/language/ext/URL 边界和 response close
  不得回归。

## P2 处理边界

第三次 Reviewer 只剩一个 P2：`SubtitleAcquisitionService` 职责聚合与 integration
tests 私有 hook 耦合。

本轮不要求拆新公共模块或全面重写 998 行 Service。修复三个 P1 时必须：

- 提取窄的 Service boundary sanitizer、trusted provenance validator 和 streaming
  metadata parser；
- 避免再次扩大 `fetch`、`_load_cached`、`_fetch_reserved` 或重复 cleanup 分支；
- 新测试优先走公开 Adapter/Service + 真实 SQLite；不得新增公开 test hook；
- 在 handoff 如实报告 Service/私有 hook P2 是否改善或继续保留。

若职责聚合导致新的正确性、安全或 cleanup 缺陷，则按 P1 修复；否则可继续登记为
P2，由下一次 Reviewer 独立判断。

## TDD 与检查

先把第三次 Reviewer 的三个反例组写成失败测试并记录 RED，再逐项实现 GREEN。不得
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
git diff --check 30c665181db77607648aa1a6fdbb1d5502b71d7d...HEAD
```

`uv sync --locked` 只允许既有锁定包；不得下载新依赖、重锁或改清单。build 必须
offline，并验证 migration、`transcripts.py`、`providers/subtitles.py` 仍进入
sdist/wheel；只清理本轮被忽略的 `dist/`。

额外检查：

- `pyproject.toml`/`uv.lock` 与 base 字节不变；
- Correction 3 Diff 只属于 6 个允许路径组；
- 完整 `b28f52d...HEAD` 产品范围仍属于原 8 个路径组；
- source 无真实 URL/响应、密钥、Cookie、媒体、数据库、cache 或构建产物；
- 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
  真实 Vault/密钥不得运行。

## Handoff 与提交

保留全部历史证据，在 `handoffs/TASK-005.md` 追加
`Implementer Correction 3`，逐项记录：

- 三个 P1 的 RED/GREEN 输入、期望/实际、测试和代码位置；
- hostile public Adapter 的安全错误重建矩阵；
- source/language/rolling quality 等 provenance 与可信 record/key 的绑定证据；
- runs/buckets 的消费计数、边界、错误分类和内存复制证据；
- P2 是否改善或继续保留；
- 全部命令、Diff、复用/许可证、跳过项和剩余风险。

只在全部门禁通过后创建新 commit：

```text
fix: secure subtitle boundaries and metadata limits
```

提交后确认：

- 新 commit 唯一父提交为
  `30c665181db77607648aa1a6fdbb1d5502b71d7d`；
- 不 amend/rebase 历史；
- worktree 干净；
- TASK-005 状态仍由 main 控制面保持 `IN_PROGRESS`，不得自行改状态或启动 Reviewer；
- 不 merge、push、清理分支/worktree。

## 回传格式

```text
Task: TASK-005
Role: Codex Implementer (Correction 3)
Starting review evidence: 30c665181db77607648aa1a6fdbb1d5502b71d7d
Correction commit:
Changed files:
P1-1 public Adapter boundary evidence:
P1-2 trusted provenance evidence:
P1-3 streaming bounds evidence:
P2 handling:
Checks:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
