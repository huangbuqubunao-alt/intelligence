# TASK-005 Correction 1 — 第二次独立 Codex Reviewer

## 身份与目标

你是一个全新的、独立的 Codex Reviewer。你没有参与原实现、第一次审查或
Correction 1，不得复用任何先前会话。你只审查 Correction 1
`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf` 是否真正关闭第一次 Reviewer 的
5 个 P1，同时确认 TASK-005 全部 AC、ADR-006 T-01 至 T-15、五轴质量、范围和红线
没有回归。

不得修改业务代码、测试、fixture、依赖、锁文件、任务状态或 main；唯一允许写入并
提交的是 source worktree 中 `handoffs/TASK-005.md` 的第二次 Reviewer 部分。
Verdict 只能为 `APPROVE` 或 `REJECT`，不得自行修复 finding。

## 固定审查对象

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main review authorization：动态执行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-REVIEWER-2-CODEX.md`
- Main authorization parent：`4df3ff13732e98665732e2ba7bfc8b90c4c141aa`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Implementation base：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Original implementation：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- First review evidence：`515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Reviewed Correction 1 head：
  `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Correction parent：`515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

开始时 main 必须位于本 review authorization commit 且干净；source 必须位于固定
Correction head、分支正确且干净。任一 SHA、父链、身份、洁净度、范围或授权不符，
立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、
pull、清理或选择其他 SHA。

审查开始后你独占 source worktree；不得与 Implementer 或其他 Reviewer 并发写入。

## 必读

完整读取 main 最新控制面、ADR-006、TASK-005 卡、原 Implementer 包、第一次
Reviewer 包、Correction 1 包，以及 source handoff 的 Implementer/Reviewer/
Correction 1 全部证据。技术预期以 ADR-006 与第一次 Reviewer 的可复现 P1 为准，
不得依赖 Correction 自报替代独立验证。

## Git 与范围门禁

确认：

1. `98d197...` 唯一父提交为 base；
2. `515c348...` 唯一父提交为 `98d197...` 且只修改 handoff；
3. `55156f9...` 唯一父提交为 `515c348...`，非 amend/rebase/merge；
4. Correction Diff 精确为：
   - `handoffs/TASK-005.md`
   - `src/youtube_intel/providers/subtitles.py`
   - `src/youtube_intel/transcripts.py`
   - `tests/integration/test_subtitle_provider.py`
   - `tests/unit/test_subtitle_policy.py`
5. 完整 base...Correction 产品范围仍精确属于原批准的 8 个路径组/11 个文件；
6. `domain.py`、contracts test、`state.py`、migration、配置、CLI、discovery/youtube
   Adapter、`pyproject.toml` 和 `uv.lock` 未被 Correction 修改；
7. 无真实数据、凭证、Cookie、媒体、数据库、cache 或构建产物进入提交。

Correction 为 1,489 行新增/修改，不能仅因 219 tests 自动批准；也不能仅按行数拒绝。

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
git diff --check b28f52d0e4950f78dba315d4afe211ea5f75b93c...55156f9f53a610ccbf9c8806f19f19f2c16bb1cf
```

`uv sync --locked` 只允许既有锁定包；build 必须 offline。检查 sdist/wheel 包含
migration、`transcripts.py`、`providers/subtitles.py` 后，只清理本轮 ignored
`dist/`。不得联网、重锁或更改依赖。

## 五个 P1 独立关闭探针

### R1：异常链与正文脱敏

使用独立敏感 marker 覆盖 malformed JSON3、非法 UTF-8、unindexed recovered raw、
候选回退和 Service 外层错误。检查：

- 新异常 message、args、属性、`__cause__`、`__context__` 均无 marker/raw；
- 格式化 traceback、异常链和外层 `TranscriptError` 无正文、临时 URL、绝对路径；
- 不得仅因 `raise ... from None` 隐藏显示而仍在 `__context__` 保存原异常；
- 合法候选在前一个候选解析失败后仍可继续。

### R2：VTT speaker/cue 语义

独立覆盖：

- 单 voice、多 voice、相邻/嵌套样式中的 voice、无 voice；
- `NOTE`、`NOTE text`、`NOTE\ttext` 控制块；
- `NOTEworthy-cue-id` 及其他以 NOTE 开头的合法 cue ID；
- cue ID、时间行、正文顺序和 marker/speaker 共同出现。

必须保留所有 speaker 身份和正文顺序，不静默丢块、不产生虚假前缀。

### R3：Adapter fail-closed

使用真实 `http.client.HTTPMessage` 与 Fake response 独立覆盖：

- Content-Length 大小写、缺失、合法、短读、负数、非数字、多个相同值、多个冲突值、
  超过正文上限；
- 轨道数 512/513、name 1000/1001、language 128/129、ext 32/33、URL 8192/8193；
- unsupported-only、支持/不支持混合、字段非字符串、危险 URL/redirect；
- 所有拒绝必须发生在 opener/正文读取之前，错误码/retryable 与 ADR-006 一致；
- response 在所有成功/失败路径关闭，异常链不保留 header/body。

确认边界检查不是仅存在于测试 Fake，而是真实 Adapter 路径执行。

### R4：Provider-call 幂等、竞态与快速恢复

使用真实临时 SQLite 和受控时钟验证完整状态矩阵：

- 无记录：正常枚举；有 ranked candidate 后在正文读取前取得 reservation；
- active PENDING、not-due FAILED_RETRYABLE：零目录枚举、零正文读取；
- SUCCEEDED：只走 verified Artifact/cache，零网络；
- 本任务 all-invalid FAILED_FINAL：零网络且稳定返回
  `ALL_CANDIDATES_INVALID`；其他 FAILED_FINAL 不得被错误映射为 all-invalid；
- 两个 Service 竞争同一 request：最多一个正文读取/持有 reservation，另一方无
  副作用；
- `complete_stage` 在 Artifact/Provider/Pipeline 任一故障点失败后，原 reservation
  被安全释放为立即可重试，原 stage 错误不被释放失败覆盖；
- 默认 300 秒 Provider lease 与 2 秒 Job backoff 下，下一 attempt 验证已有文件并
  补索引，不等待 lease；
- 重复调用不漂移为错误的 `PROVIDER_UNAVAILABLE`、不耗尽 Job attempts、不错误推进
  Pipeline。

### R5：verified raw → canonical-only 重建

独立构造 raw Artifact/文件存在、当前 canonical 缺失的情形，验证：

- video、kind、storage root、deleted_at、producer version、provider/model、路径、
  metadata token、format、大小和 SHA-256 全部校验；
- normalization/quality 版本变化时零枚举、零正文 opener，只从 verified raw 重建；
- 只新增当前 Job canonical Artifact，旧 raw 不重绑定/不修改，旧 canonical 保留；
- 新 canonical key/path/hash/flags/计数与当前版本一致；
- 第二次运行命中 verified canonical，不重新规范化；
- raw 缺失、篡改、symlink 越界、provider/model/producer/path/token/format 不一致及
  当前 policy 质量失败均安全 `LOCAL_RESOURCE`，Pipeline/Job 不推进。

## 回归、架构与五轴

完成 R1-R5 后，再复核原 Reviewer A-F、AC-1 至 AC-5、ADR-006 T-01 至 T-15，特别
确认修复没有破坏人工/自动排序、refresh、普通 cache、首次事务完成和安全 options。

对 P2 独立判断：

- 新 helper 是否真正分离 VTT、HTTP bounds、Provider 状态和 canonical rebuild；
- `fetch`/Service 是否继续出现难以证明的重复状态或死分支；
- 新增测试是否以公开行为/真实 SQLite 为主，还是复制实现、过度依赖私有 hooks；
- 目录/文件读取是否仍有界，竞争路径是否产生额外远端或内存放大。

P2 可保留并登记后续风险，但任何由复杂度导致的正确性、安全或恢复缺陷仍是 P1。

## Finding 与 Verdict

使用 P0/P1/P2/P3，给出文件/行号、输入、期望/实际和影响：

- 任一未解决/新 P0/P1、必需门禁失败或跳过：`REJECT`；
- R1-R5 任一不能被独立证明：`REJECT`；
- 只有明确的 P2/P3 且全部 AC/T 条款通过：可以 `APPROVE`；
- 不得修改产品代码/测试或自行降低验收标准。

## 写入 evidence

只在 `handoffs/TASK-005.md` 追加第二次 Reviewer 结论，保留所有历史证据。记录：

- 固定 SHA/父链/范围；
- 全部命令；
- R1-R5、A-F、AC/T/五轴矩阵；
- Findings、Verdict、跳过项、剩余风险；
- TASK-006 最终公共契约复核是否仍成立。

只暂存并提交 handoff：

```text
docs: re-review TASK-005 subtitle correction
```

提交后：

- evidence commit 唯一父提交为
  `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`；
- commit 只修改 `handoffs/TASK-005.md`；
- source/main 均干净；
- 不 merge、push、改任务状态或清理。

## 回传格式

```text
Task: TASK-005
Role: Second Independent Codex Reviewer
Reviewed Correction head: 55156f9f53a610ccbf9c8806f19f19f2c16bb1cf
Review evidence commit:
Checks rerun:
P1 closure probes R1-R5:
Regression A-F:
Acceptance matrix:
ADR-006 traceability:
Five-axis review:
Findings: P0/P1/P2/P3
Scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Skipped checks:
Remaining risks:
TASK-006 final-contract recheck:
Decision needed: None | details
Post-commit status:
```
