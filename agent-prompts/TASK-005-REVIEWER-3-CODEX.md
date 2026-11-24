# TASK-005 Correction 2 — 第三次独立 Codex Reviewer

## 身份与目标

你是一个全新的、独立的 Codex Reviewer。你没有参与 TASK-005 原实现、两次
Correction 或前两次审查，不得复用 Implementer、第一次 Reviewer 或第二次
Reviewer 会话。

你只审查 Correction 2
`f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f` 是否真正关闭第二次 Reviewer 的
3 个 P1，同时确认第一次审查已关闭的 VTT/HTTP 等行为、TASK-005 全部 AC、
ADR-006 T-01 至 T-15、五轴质量、范围、复用和红线没有回归。

不得修改业务代码、测试、fixture、依赖、锁文件、任务状态或 main。唯一允许写入并
提交的是 source worktree 中 `handoffs/TASK-005.md` 的第三次 Reviewer 部分。
Verdict 只能为 `APPROVE` 或 `REJECT`，不得自行修复 finding。

## 固定审查对象

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main review authorization：动态执行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-REVIEWER-3-CODEX.md`
- Main authorization parent：`e4ab5638d599a5688f75d8e0da03e4a15950da3e`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Implementation base：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Original implementation：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- First review evidence：`515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Correction 1：`55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Second review evidence：`5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Reviewed Correction 2 head：
  `f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Correction 2 parent：`5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

开始时 main 必须位于动态 review authorization commit 且干净；source 必须位于固定
Correction 2 head、分支正确且干净。任一 SHA、父链、身份、洁净度、范围或授权不符，
立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、
pull、清理或选择其他 SHA。

审查开始后你独占 source worktree；Implementer 和其他会话不得并发写入 source，
其他会话也不得在你的严格主线基线检查期间写 main。

## 必读

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
6. `docs/REUSE_REGISTER.md`
7. `tasks/TASK-005-subtitle-pipeline.md`
8. 原 Implementer、两个 Reviewer、Correction 1、Correction 2 的全部任务包
9. source `handoffs/TASK-005.md` 的全部历史证据
10. 本 Reviewer 包

技术预期以 ADR-006、前两次 Reviewer 的可复现反例和 Correction 2 的固定 Diff 为
准。不得依赖 Implementer 自报、测试数量或 handoff 中的 GREEN 结论替代独立验证。

## Git 与范围门禁

确认：

1. `98d197...` 唯一父提交为 base；
2. `515c348...` 唯一父提交为 `98d197...`，且只修改 handoff；
3. `55156f9...` 唯一父提交为 `515c348...`，Correction 1 精确为 5 个允许文件；
4. `5bb750e8...` 唯一父提交为 `55156f9...`，且只修改 handoff；
5. `f95bdb1...` 唯一父提交为 `5bb750e8...`，非 amend/rebase/merge；
6. Correction 2 Diff 精确为：
   - `handoffs/TASK-005.md`
   - `src/youtube_intel/providers/subtitles.py`
   - `src/youtube_intel/transcripts.py`
   - `tests/integration/test_subtitle_provider.py`
   - `tests/unit/test_subtitle_policy.py`
7. 完整 base...Correction 2 产品范围仍精确属于原批准的 8 个路径组/11 个文件；
8. `domain.py`、contracts test、`state.py`、migration、配置、CLI、
   discovery/youtube Adapter、`pyproject.toml` 和 `uv.lock` 未被 Correction 2
   修改；
9. `pyproject.toml`/`uv.lock` 相对 base 字节不变；
10. 无真实数据、凭证、Cookie、媒体、数据库、cache 或构建产物进入提交。

Correction 2 为约 1,281 additions/221 deletions，不能仅因 234 tests 自动批准，
也不能仅按行数拒绝。

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
git diff --check b28f52d0e4950f78dba315d4afe211ea5f75b93c...f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f
```

Implementer 自报期望计数为 contracts 50、policy 30、integration 68、全量 234；
Reviewer 记录实际结果，不以计数本身代替语义审查。

`uv sync --locked` 只允许既有锁定包；build 必须 offline。检查 sdist/wheel 包含
migration、`transcripts.py`、`providers/subtitles.py` 后，只清理本轮 ignored
`dist/`。不得联网、重锁或更改依赖。

## 三个 P1 独立关闭探针

### Q1：完整异常图脱敏与错误语义

使用与现有测试不同的独立 marker、临时 URL 和绝对路径，至少覆盖：

- `YtDlpSubtitleAdapter.enumerate_tracks` 的底层 `DownloadError`；
- `read_track`/短读/Provider 错误；
- ordinary canonical cache 的非法 UTF-8；
- recovered raw decode/quality 失败；
- reservation 后原子文件写 `PermissionError`；
- Repository/stage 外层包装。

递归遍历每个异常节点的 message、args、`vars()`、`__cause__`、`__context__` 和格式化
traceback。要求：

- marker、字幕 bytes、临时 URL、绝对路径和底层异常对象均不可达；
- 所有新外层异常的 cause/context 均为 `None`，不能只靠显示抑制；
- 原 `ErrorCode`、retryable、stage、video ID 和有效 retry-after 保持准确；
- 候选失败后的合法回退仍工作，不把安全转换变成泛化
  `PROVIDER_UNAVAILABLE`。

### Q2：pre-enumeration reservation、终态重放与失败释放

使用真实临时 `SQLiteStateRepository`、受控 UTC 时钟和两个独立 Service 实例，验证：

- 无记录时，reservation 在任何目录枚举前已经存在且 lease 为默认 300 秒；
- 两个 Service 通过 barrier 同时竞争同一稳定 raw request，恰好一个 owner；
  `enum_total=1`、`body_total<=1`，失败方零文件/Artifact/Pipeline 副作用；
- active `PENDING`、not-due `FAILED_RETRYABLE`：零目录、零正文；
- no tracks、no matching language、all-invalid 首次和重复调用均稳定、零额外网络，
  Provider record 不遗留 owner/lease；
- 非 all-invalid `FAILED_FINAL` 精确重放持久化的合法 `ErrorCode`、retryable 和
  stage，不漂移为其他类别；
- 原子文件 `PermissionError`、Provider/解析错误、Artifact/Provider/Pipeline 三个
  stage 故障点均不会留下 active `PENDING`；
- retryable 失败清除 owner/lease，并在 2 秒 Job retry 时可恢复；nonretryable
  失败进入稳定终态；
- `SUCCEEDED` verified cache、raw recovery 和 canonical hit 均零网络，重复运行不
  耗尽 Job attempts 或错误推进 Pipeline。

不得用进程内全局锁、sleep、轮询或 Fake-only 行为证明跨 Service CAS。

### Q3：raw/canonical provenance 与 cache fail-closed

以有效正向样例为起点，分别单变量篡改：

- raw/canonical artifact key、video、kind、storage root、deleted_at、relative
  path、parent request hash、SHA、producer/version；
- raw metadata token 的 ordered language preferences、requested language、actual
  language、source type、format、Provider/version、refresh generation；
- raw/canonical `provider`、`model`、normalization/quality version 和 quality
  token；
- raw 与 canonical 文件的 missing/tampered/invalid UTF-8/symlink/realpath escape。

要求：

- `requested_language` 必须与当前有序偏好和实际匹配选择一致，不能仅为列表成员或
  结构合法；
- manual/auto 当前预期为空的 model 不得接受非空或 record/token 间不一致值；
- 已索引 cache 的任一不一致均零网络、nonretryable `LOCAL_RESOURCE`，Job/Pipeline
  不推进；
- 新写入目标的 DATA 边界/写权限错误仍保持 ADR-006 T-11 的
  `PERMISSION_DENIED`，不得混淆两类场景；
- valid raw→new canonical、ordinary canonical hit 和第二次稳定 hit 均成功，旧
  Artifact 保留且不重绑定。

## 已关闭路径与完整回归

### Q4：R2/R3 安全回归

独立重放至少以下已通过路径：

- VTT 单/多 speaker、嵌套样式、NOTE 控制块和 NOTE 前缀合法 cue ID；
- 真实 `HTTPMessage` Content-Length 合法/短读/重复/冲突/超限；
- 512/513 tracks、name/language/ext/URL 冻结边界；
- unsupported-only/mixed、危险 URL/redirect、response 全路径关闭；
- no Cookie/login/`.netrc`、remote components、ffmpeg、subprocess、媒体写入。

Correction 2 不得通过重写已关闭路径换取新探针通过。

### Q5：P2、资源与架构复核

第二次 Reviewer 保留两个 P2：

1. Service/文件/cache/Provider 状态职责聚合与 integration tests 私有 hook 耦合；
2. name `runs` 和空 language bucket 的嵌套 metadata 资源放大面。

独立判断：

- 新 helper 是否真正降低异常、reservation 和 provenance 的重复状态分支；
- `fetch`、cache load/rebuild 和 reservation owner 路径是否仍存在死分支、重复
  状态或不可证明的 cleanup；
- 新测试是否主要验证公开 Adapter/Service + 真实 SQLite，还是复制实现和依赖私有
  hook；
- 对大量空 language buckets、极碎 name runs 和最大允许 payload 做有界离线压力
  探针，确认没有明显超线性 CPU/内存放大或在冻结字段上限前大量复制完整 payload。

P2 可以明确保留并登记后续加固；但若资源输入可导致无界处理、绕过现有硬上限、
安全失败或新的正确性缺陷，应升级为 P1 并 `REJECT`。不得仅按模块行数决定 Verdict。

## AC、ADR、公共契约与五轴

完成 Q1-Q5 后，逐项复核：

- TASK-005 AC-1 至 AC-5；
- ADR-006 T-01 至 T-15；
- 原 Reviewer A-F；
- correctness、readability、architecture、security、performance；
- TASK-006 所依赖的 `TranscriptProvider`、`TranscriptArtifact`、三个
  `TranscriptQualityFlag` 和三个 `TranscriptionReason` 公共形状是否仍冻结；
- 复用/许可证：仅既有 yt-dlp/标准库；无新依赖、Schema、远端服务或代码复制。

## Finding 与 Verdict

使用 P0/P1/P2/P3，给出文件/行号、独立输入、期望/实际和影响：

- 任一未解决/新 P0/P1、必需门禁失败或跳过：`REJECT`；
- Q1-Q4 任一不能被独立证明：`REJECT`；
- Q5 发现实际无界/安全/正确性缺陷：按 P1 `REJECT`；
- 只有明确的 P2/P3 且全部 AC/T 条款通过：可以 `APPROVE`；
- 不得修改产品代码/测试或自行降低验收标准。

## 写入 evidence

只在 `handoffs/TASK-005.md` 追加第三次 Reviewer 结论，保留所有历史证据。记录：

- 固定 SHA/父链/范围；
- 全部命令及实际计数；
- Q1-Q5、A-F、AC/T/五轴矩阵；
- Findings、Verdict、跳过项、剩余风险；
- TASK-006 最终公共契约复核是否仍成立。

只暂存并提交 handoff：

```text
docs: review TASK-005 correction 2
```

提交后：

- evidence commit 唯一父提交为
  `f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`；
- commit 只修改 `handoffs/TASK-005.md`；
- source/main 均干净；
- 不 merge、push、改任务状态或清理。

## 回传格式

```text
Task: TASK-005
Role: Third Independent Codex Reviewer
Reviewed Correction 2 head: f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f
Review evidence commit:
Checks rerun:
P1 closure probes Q1-Q3:
Regression Q4:
P2/architecture probe Q5:
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
