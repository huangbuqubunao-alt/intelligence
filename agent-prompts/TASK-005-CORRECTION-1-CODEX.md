# TASK-005 字幕获取与规范化 — Codex Correction 1

## 身份与目标

你是 TASK-005 原 Codex Implementer，负责修复第一次独立 Reviewer 在 evidence
`515c34894bb138115a4658d962fb5ef0aa7d9d80` 中确认的 5 个 P1，并补充行为回归。
Reviewer 已结束且不得修代码；本轮不得争辩、弱化测试或扩大产品范围。

你不负责重新审查、主控验收、main 整合、ADR-007、TASK-006/007 或任何真实网络/
媒体操作。

## 固定恢复状态

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main correction authorization：动态执行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-CORRECTION-1-CODEX.md`
- Correction authorization parent：
  `095380b7263aa3d04c7d133c1e17d8f4f2fea082`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Original implementation：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- Review evidence / starting HEAD：
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Starting HEAD parent：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`

开始时 main 必须位于 correction authorization commit 且干净；source 必须位于固定
review evidence HEAD、分支正确且干净。任一基线、父链、身份、洁净度、Review
Verdict 或范围不符，立即停止并报告 `BLOCKED`。不得 stash、reset、checkout、
merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

不得 amend/rebase `98d197...` 或 `515c348...`。Correction 必须创建新的非 merge
commit，唯一父提交为 `515c348...`。

## 必读与事实优先级

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
4. `tasks/TASK-005-subtitle-pipeline.md`
5. `agent-prompts/TASK-005-IMPLEMENTER-CODEX.md`
6. `agent-prompts/TASK-005-REVIEWER-CODEX.md`
7. `handoffs/TASK-005.md` Reviewer 部分
8. 本 Correction 包

技术事实以 Reviewer 的可复现证据为准。发现修复必须修改 `state.py`、Schema、
domain 公共对象、依赖/锁或范围外文件时，立即 `DECISION NEEDED`，不得使用
wrapper、monkey patch、`Any`、宽 `object`、自由 `dict`、`cast` 或
`type: ignore` 隐藏问题。

## 唯一允许修改的路径组

1. `src/youtube_intel/transcripts.py`
2. `src/youtube_intel/providers/subtitles.py`
3. `tests/unit/test_subtitle_policy.py`
4. `tests/integration/test_subtitle_provider.py`
5. `tests/fixtures/subtitles/**`
6. `handoffs/TASK-005.md`

不得修改 `domain.py`、`tests/unit/test_contracts.py`、`state.py`、migration、
配置、CLI、discovery/youtube Adapter、`pyproject.toml`、`uv.lock`、任务/ADR 或
main。不得新增产品模块；为关闭 P2 可在上述两个产品文件内提取具名私有 helper/
component，但不做与 P1 无关的全面重写。

## P1 修复矩阵

### P1-1：异常链不得保留字幕正文

Reviewer 证据：`transcripts.py:382`、`:631`；`JSONDecodeError.doc` 与
`UnicodeDecodeError.object` 保留 raw 字幕。

要求：

- 在解析边界捕获 JSON/Unicode 底层异常，转换为不携带 raw payload 的
  `InvalidSubtitleCandidate`；
- 不得只使用 `raise ... from None` 后假定安全：Python 仍可能在 `__context__`
  保存原异常。必须在离开活动 `except` 后再抛出新的安全异常，或采用等价方式确保
  `__cause__ is None` 且 `__context__ is None`；
- 新异常的 message、`__cause__`、`__context__`、格式化 traceback 和外层
  `TranscriptError` 均不得包含 marker、正文、raw bytes、临时 URL 或绝对路径；
- 不把底层异常对象保存为属性、diagnostic 或日志字段；
- 以含唯一敏感 marker 的 malformed JSON3、非法 UTF-8 和嵌套 Adapter/Service
  路径建立回归。

### P1-2：VTT 合法 speaker/cue 语义必须保留

Reviewer 证据：`transcripts.py:431`、`:469`。

要求：

- `<v Alice>...</v> <v Bob>...</v>` 必须保留两个具名 speaker，不得合并成单一
  `Alice:` 前缀或丢失 `Bob`；
- `NOTE` 控制块只在语法上为独立 NOTE token 时识别；合法 cue identifier
  `NOTEworthy-cue-id` 不得被 `startswith("NOTE")` 误删；
- 覆盖多个 voice span、单 voice、无 voice、NOTE block 与 NOTE 前缀 cue ID；
- 不用模糊修复或改变非 speaker 正文顺序。

### P1-3：Adapter 对短读、格式和目录 payload fail-closed

Reviewer 证据：`providers/subtitles.py:215`、`:316`、`:576`。

冻结本轮边界：

- `Content-Length` 必须兼容真实 `http.client.HTTPMessage` 及大小写变化；声明长度
  大于实际读取长度时返回 retryable `TRANSIENT_NETWORK`；
- 非法/重复/负数/超限 Content-Length fail-closed，不泄漏 header/body；
- 轨道目录非空但全部格式均不属于 JSON3/VTT/SRT 时返回 nonretryable
  `INVALID_RESPONSE`，不得伪装为 `NO_TRACKS`；
- 最大轨道数 `512`；
- 单个 track name 最大 `1_000` Unicode code points；
- 单个 language tag 最大 `128` code points；
- 单个 ext 最大 `32` code points；
- 单个字幕 URL 最大 `8_192` code points；
- 超限、危险或非法字段必须在 opener/正文读取前以安全 `INVALID_RESPONSE` 拒绝；
- 同时存在支持与不支持格式时，只允许支持格式进入候选，但任何结构非法或字段超限
  仍使整个目录响应 fail-closed。

回归必须使用真实 `HTTPMessage`、短读、unsupported-only、混合格式、边界值和第一
超限值；不得只用与生产不一致的 Fake Mapping。

### P1-4：Provider call 顺序、失败释放和负结果稳定

Reviewer 证据：`transcripts.py:1389`、`:1414`、`:1570`、`:1618`。

要求：

- 在任何远端目录枚举/正文读取前检查既有 Provider call 状态；可把现有
  `SQLiteStateRepository.get_provider_call` 以窄具名方法加入
  `TranscriptRepository`，但不得修改 `state.py`；
- 已有未过期 PENDING/尚未到期 FAILED_RETRYABLE 时零 Provider 调用并返回安全
  retryable `PROVIDER_UNAVAILABLE`；
- 已有 SUCCEEDED 时只走 verified Artifact/cache；
- 已有由本任务记录的 FAILED_FINAL all-invalid 时零 Provider 调用并稳定返回
  `TranscriptionRequired(ALL_CANDIDATES_INVALID, attempted_track_count=0)`；`call`
  可由安全 Provider-call record、当前 Adapter 版本和稳定时间字段构造，不得依赖
  raw payload；
- 首次无既有记录时仍可枚举目录以区分 `NO_TRACKS`/`NO_MATCHING_LANGUAGE`；确认有
  ranked candidate 后必须在正文读取前取得 reservation；
- reservation 未取得时不得读取字幕正文；
- `complete_stage` 失败后，在抛出外层 retryable `LOCAL_RESOURCE` 前立即调用现有
  `fail_provider_call(..., retryable=True, available_at=now)` 释放 owner/lease；
  failure 记录失败不得覆盖原始 stage persistence 错误；
- 默认 2 秒 Job 退避后的下一 attempt 必须能够重新取得 reservation，验证确定性
  source/canonical 文件并补索引，不等待 300 秒；
- 重复 all-invalid、既有 PENDING、stage failure 快速恢复、两个 Service 竞争均需
  真实临时 SQLite 回归；禁止修改 TASK-003 状态语义。

### P1-5：canonical-only 失效从 verified raw 重建

Reviewer 证据：`transcripts.py:1141`。

要求：

- raw Artifact/文件存在且 video、kind、DATA 路径、metadata token、SHA-256 和格式
  均验证通过，而当前 canonical key 不存在时，不访问远端；
- 从 verified raw 重新执行当前 normalization/quality policy，写入新 canonical
  确定性文件和当前 Job 的 canonical Artifact，并以 `provider_call=None` 完成阶段；
- 不把旧 raw Artifact 重新绑定当前 Job，不修改旧 Artifact，不新增 manifest 或
  Repository 语义；
- raw 缺失/篡改/metadata 不一致继续 `LOCAL_RESOURCE` fail-closed；
- normalizer/quality version 变化只使 canonical 失效；Provider/selection/format/
  refresh 变化才使 raw request 失效；
- 回归证明零枚举、零正文 opener、旧 raw/旧 canonical 保留、新 canonical key/path
  可追踪且重复运行稳定。

## P2 处理边界

Reviewer 的职责聚合/私有 hook finding 为 P2，不要求本轮把整个 1,664 行模块拆成新
文件。修复 P1 时应：

- 把 Provider-call 状态判断、raw→canonical 重建、VTT block/voice 解析和 HTTP
  length/bounds 分成具名私有 helper；
- 避免继续扩大 284 行 `fetch`；
- 新测试优先通过公开 Service/Adapter 行为或窄 Fake transport 验证；不得新增公开
  测试 hook。

若能在允许文件内安全降低复杂度则执行；不得为了追求行数做高风险重写。

## TDD 与检查

先把 Reviewer 五个反例写成失败测试并记录 RED，再逐项实现 GREEN。不得删除、跳过、
放宽既有测试或修改期望以适应错误行为。

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
git diff --check 515c34894bb138115a4658d962fb5ef0aa7d9d80...HEAD
```

`uv sync --locked` 只允许既有锁定包；不得下载新依赖、重锁或改清单。build 必须
offline，并验证 migration、`transcripts.py`、`providers/subtitles.py` 仍进入
sdist/wheel；只清理本轮被忽略的 `dist/`。

额外检查：

- `pyproject.toml`/`uv.lock` 与 base 字节不变；
- correction Diff 只属于 6 个允许路径组；
- 完整 `b28f52d...HEAD` 产品范围仍属于原 8 个路径组；
- source 无真实 URL/响应、密钥、Cookie、媒体、数据库、cache 或构建产物；
- 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
  真实 Vault/密钥不得运行。

## Handoff 与提交

保留 Reviewer 原文，在 `handoffs/TASK-005.md` 追加
`Implementer Correction 1`，逐项记录：

- 5 个 P1 的 RED/GREEN 回归与代码位置；
- Provider-call 状态矩阵和真实 SQLite 恢复证据；
- raw→canonical 重建证据；
- P2 是否局部改善；
- 全部命令、Diff、复用/许可证、跳过项和剩余风险。

只在全部门禁通过后创建新 commit：

```text
fix: harden subtitle parsing and recovery
```

提交后确认：

- 新 commit 唯一父提交为
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`；
- 不 amend/rebase 历史；
- worktree 干净；
- TASK-005 状态仍由 main 控制面保持 `IN_PROGRESS`，不得自行改状态或启动 Reviewer；
- 不 merge、push、清理分支/worktree。

## 回传格式

```text
Task: TASK-005
Role: Codex Implementer (Correction 1)
Starting review evidence: 515c34894bb138115a4658d962fb5ef0aa7d9d80
Correction commit:
Changed files:
P1-1 redaction evidence:
P1-2 VTT semantics evidence:
P1-3 Adapter fail-closed evidence:
P1-4 Provider state/recovery evidence:
P1-5 canonical rebuild evidence:
P2 handling:
Checks:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
