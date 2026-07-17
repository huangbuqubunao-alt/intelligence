# TASK-005 Correction 3 — 第四次独立 Codex Reviewer

## 身份与目标

你是一个全新的、独立的 Codex Reviewer。你没有参与 TASK-005 原实现、任一次 Correction 或前三次审查，不得复用 Implementer、前三个 Reviewer 或 Status Integrator 会话。

你只审查 Correction 3 `abf2acba25f9732a9511ecd54c4b92ef6c0d68e1` 是否真正关闭第三次 Reviewer 的 3 个 P1，同时确认此前已关闭的 Q2/Q4 路径、TASK-005 全部 AC、ADR-006 T-01 至 T-15、五轴质量、范围、复用和红线没有回归。

不得修改业务代码、测试、fixture、依赖、锁文件、任务状态或 main。唯一允许写入并提交的是 source worktree 中 `handoffs/TASK-005.md` 的第四次 Reviewer 部分。Verdict 只能为 `APPROVE` 或 `REJECT`，不得自行修复 finding。

## 固定审查对象

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main review authorization：动态执行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-REVIEWER-4-CODEX.md`
- Main authorization parent：`d783f705bd749b9e691456fd85f8af1635d9f32f`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Implementation base：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Third review evidence：`30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Reviewed Correction 3 head：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`
- Correction 3 parent：`30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始时 main 必须位于动态 review authorization commit 且干净；source 必须位于固定 Correction 3 head、分支正确且干净。任一 SHA、父链、身份、洁净度、范围或授权不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

审查开始后你独占 source worktree；Implementer 和其他会话不得并发写入 source，其他会话也不得在你的严格主线基线检查期间写 main。

## 必读

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
6. `docs/REUSE_REGISTER.md`
7. `tasks/TASK-005-subtitle-pipeline.md`
8. TASK-005 原 Implementer、前三个 Reviewer、Correction 1/2/3 的全部任务包
9. source `handoffs/TASK-005.md` 的全部历史证据
10. 本 Reviewer 包

技术预期以 ADR-006、前三次 Reviewer 的可复现反例和 Correction 3 的固定 Diff 为准。不得依赖 Implementer 自报、测试数量或 handoff 中的 GREEN 结论替代独立验证。

## Git 与范围门禁

确认：

1. 原实现和前三次 review/correction 链连续、均为预期单父提交；`30c665...` 只修改 handoff；
2. `abf2acb...` 唯一父提交为 `30c665...`，非 amend/rebase/merge；
3. Correction 3 Diff 精确为：
   - `handoffs/TASK-005.md`
   - `src/youtube_intel/providers/subtitles.py`
   - `src/youtube_intel/transcripts.py`
   - `tests/integration/test_subtitle_provider.py`
4. 完整 base...Correction 3 产品范围仍精确属于原批准的 8 个路径组/11 个文件；
5. `domain.py`、contracts test、`state.py`、migration、`complete_stage`、配置、CLI、discovery/youtube Adapter、`pyproject.toml` 和 `uv.lock` 未被 Correction 3 修改；
6. `pyproject.toml`/`uv.lock` 相对 base 字节不变；
7. 无真实数据、凭证、Cookie、媒体、数据库、cache 或构建产物进入提交。

Correction 3 为约 1,039 additions/86 deletions，不能仅因测试数量自动批准，也不能仅按行数拒绝。

## 必须独立复跑

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
git diff --check b28f52d0e4950f78dba315d4afe211ea5f75b93c...abf2acba25f9732a9511ecd54c4b92ef6c0d68e1
```

Implementer 自报期望计数为 contracts 50、policy 30、integration 77、全量 243；Reviewer 记录实际结果，不以计数本身代替语义审查。

`uv sync --locked` 只允许既有锁定包；build 必须 offline。检查 sdist/wheel 包含 migration、`transcripts.py`、`providers/subtitles.py` 后，只清理本轮 ignored `dist/`。不得联网、重锁或更改依赖。

## 三个 P1 独立关闭探针

### A：公共 Adapter 作为不可信边界

以不同于历史测试的 marker、临时 URL、绝对路径、错误 `video_id` 和 `stage` 构造两个公开 `SubtitleAdapter`：一个在 `enumerate_tracks`，一个在 `read_track` 失败。错误至少覆盖 `RATE_LIMITED`（合法 retry-after）、`PERMISSION_DENIED` 和嵌套 cause/context。

递归遍历 Service 向外错误、Provider-call 错误记录及 traceback 的 message、args、属性、`__cause__`、`__context__`。要求：

- 只保留合法 ErrorCode、retryable 与已验证的 retry-after；
- 安全错误使用当前请求 video ID、`ProcessingStage.TRANSCRIPT` 和固定安全 message；
- marker、URL、绝对路径、字幕正文、底层异常对象与不可信 stage/video 均不可达；
- 新异常在活动 `except` 外抛出，`__cause__`/`__context__` 均为 `None`；
- 分类/重试语义不退化，合法候选回退仍可工作。

### B：可信 provenance，而非 token 自洽

使用真实临时 SQLite、现有成功 Provider-call、response Artifact、文件 SHA 和零网络 Adapter，从有效 raw/canonical cache 开始逐个篡改或替换：source type、requested/actual language、format、provider/version、refresh generation、response artifact key/ID、deterministic key、producer provenance ID、raw/canonical hash、model、normalization/quality version 与 `ROLLING_CUES_DEDUPED` 等 quality flag。

要求：

- 任何单项不一致都零网络、nonretryable `LOCAL_RESOURCE`，Job/Pipeline 不推进；
- 不接受只与当前语言偏好“仍匹配”或 token/path “自洽”的对象；
- 普通 verified canonical hit、raw→canonical rebuild、canonical-only rebuild 与第二次稳定 hit 仍成功、零网络、旧 Artifact 不重绑定；
- 无法仅从正文证明的 rolling flag 必须从可信 raw/provenance 重新确定性验证；
- 读 cache 的失败与新写入 DATA 边界/权限失败仍按 ADR-006 T-11 区分。

若现有字段实际上无法支持这些验证，判为 `REJECT` 并记录 `DECISION NEEDED`；不得接受伪造或循环自证的 binding。

### C：流式 metadata 边界与提前停止

使用记录消费次数的自定义 iterable/sequence（含在越界后抛异常的后续元素），独立验证：

- name runs 在第 1001 code point 或第 1001 个 run（包括空 run）立刻 `INVALID_RESPONSE`，不消费剩余元素、不构造完整复制；
- language buckets 对空/非空均计数，在第 513 bucket 立刻 `INVALID_RESPONSE`，不消费剩余 bucket；非空 track 仍受 512 总数限制；
- 精确 1,000 code points/runs、512 buckets/tracks 的边界通过；+1 精确失败；
- iterator 异常/结构异常都在 opener/正文读取前 fail-closed，错误 message 不含 payload。

不得只读取新增测试；必须通过消费计数和实际路径证明没有隐藏的 `list()`、全量 joined string 或再次遍历。

## 已关闭路径与五轴复核

独立复核此前通过的 Q2/Q4：pre-enumeration reservation/CAS、终态重放、lease 释放、2 秒恢复、VTT speaker/cue、HTTPMessage 短读/Content-Length、redirect、response close 和安全 yt-dlp options。然后逐项核对 AC-1 至 AC-5、ADR-006 T-01 至 T-15、公共 `TranscriptProvider`/`TranscriptArtifact`/质量和转写原因形状、复用/许可证与 correctness、readability、architecture、security、performance 五轴。

既有 Service/私有 hook 聚合可以登记 P2；但若 Correction 3 引入新的职责膨胀、死分支、不可证明 cleanup、无界资源或安全/正确性缺陷，按 P1 `REJECT`。

## Finding、Verdict 与 evidence

使用 P0/P1/P2/P3，给出文件/行号、独立输入、期望/实际和影响：

- 任一未解决/新 P0/P1、必需门禁失败或跳过：`REJECT`；
- A-C 任一不能被独立证明：`REJECT`；
- 仅明确 P2/P3 且全部 AC/T 条款通过：可以 `APPROVE`。

只在 `handoffs/TASK-005.md` 追加第四次 Reviewer 结论，保留历史证据。只暂存并提交 handoff：

```text
docs: review TASK-005 correction 3
```

提交后 evidence commit 唯一父提交必须为 `abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`，只修改 handoff；source/main 均干净；不 merge、push、改任务状态或清理。

## 回传格式

```text
Task: TASK-005
Role: Fourth Independent Codex Reviewer
Reviewed Correction 3 head: abf2acba25f9732a9511ecd54c4b92ef6c0d68e1
Review evidence commit:
Checks rerun:
P1 probe A public Adapter boundary:
P1 probe B trusted provenance:
P1 probe C streaming bounds:
Regression and five-axis review:
Acceptance matrix:
ADR-006 traceability:
Findings: P0/P1/P2/P3
Scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Skipped checks:
Remaining risks:
TASK-006 final-contract recheck:
Decision needed: None | details
Post-commit status:
```
