# TASK-005 字幕获取与规范化 — 独立 Codex Reviewer

## 身份与审查目标

你是一个全新的、独立的 Codex Reviewer。你没有参与 TASK-005 实现，不得复用
Implementer 对话或其推理。你只审查固定实现 commit
`98d19700818bcae14efc412aaaaeb6eed97a1535` 是否严格满足 ADR-006 T-01 至
T-15、TASK-005 AC-1 至 AC-5、仓库架构、安全、复用和范围门禁。

你不得修改业务代码、测试、fixture、依赖、锁文件、任务状态或 main；唯一允许写入并
提交的是 source worktree 中的 `handoffs/TASK-005.md` Reviewer 部分。Verdict 只能
是 `APPROVE` 或 `REJECT`，不能自行修复 finding。

## 固定审查对象

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main review authorization：动态执行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-REVIEWER-CODEX.md`
- Main authorization parent：`38f1caa1c957b4b305afbe0f87c2e082b1ffc929`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Implementation base：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Reviewed implementation head：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- Implementation head parent：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

开始时 main 必须位于 review authorization commit 且干净；source 必须位于固定实现
head、分支正确且干净。任一基线、父链、身份、洁净度、范围或授权不符，立即停止并
报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、
清理、选择其他 SHA 或等待另一个写入者。

审查开始后 source worktree 由你独占。不得与 Implementer 或其他 Reviewer 同时操作。

## 必读事实源

先从 main review authorization commit 读取最新控制面，再读取 source：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. `docs/PRODUCT_DECISIONS.md`
6. `docs/REUSE_REGISTER.md`
7. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
8. `tasks/TASK-005-subtitle-pipeline.md`
9. `agent-prompts/TASK-005-IMPLEMENTER-CODEX.md`
10. `handoffs/TASK-005.md`

不得依赖 Implementer 摘要替代规格或代码。发现规格冲突时输出 `REJECT` 或
`DECISION NEEDED`，不得自行选择解释。

## 固定范围门禁

相对 base 的产品 Diff 必须精确为以下 11 个文件，且只属于批准的 8 个路径组：

- `handoffs/TASK-005.md`
- `src/youtube_intel/domain.py`
- `src/youtube_intel/providers/subtitles.py`
- `src/youtube_intel/transcripts.py`
- `tests/fixtures/subtitles/auto_zh.vtt`
- `tests/fixtures/subtitles/info_tracks.json`
- `tests/fixtures/subtitles/malformed.json3`
- `tests/fixtures/subtitles/manual_en.json3`
- `tests/integration/test_subtitle_provider.py`
- `tests/unit/test_contracts.py`
- `tests/unit/test_subtitle_policy.py`

必须确认：

- 未修改 `state.py`、migration、`complete_stage`、discovery/youtube Adapter、配置、
  CLI、`pyproject.toml`、`uv.lock`、任务/ADR 或其他产品文件；
- `pyproject.toml` 与 `uv.lock` 相对 base 字节未变；
- 无 `.env`、密钥、Cookie、真实响应、绝对本机路径、媒体、缓存、数据库或构建产物；
- 实现只有一个非 merge commit，review commit 尚不存在。

## 必须独立复跑

在 source worktree 运行：

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
git diff --check b28f52d0e4950f78dba315d4afe211ea5f75b93c...98d19700818bcae14efc412aaaaeb6eed97a1535
```

`uv sync --locked` 仅在缓存缺失时允许下载 `uv.lock` 中已有包；不得更新、重锁或新增
依赖。`uv build --offline` 不得联网。检查 sdist/wheel 必须包含
`youtube_intel/migrations/001_initial.sql`、`youtube_intel/transcripts.py` 和
`youtube_intel/providers/subtitles.py`，随后只清理本轮被忽略的 `dist/` 构建产物。

## 五轴审查与独立探针

### A. 公共领域契约

独立检查 `TranscriptFetchResult` 判别联合、`TranscriptArtifact` 的字幕/Whisper
可空组合、SHA-256、路径、计数、枚举基数和 Provider call 元数据。公共导出、Protocol
和注解不得出现自由 `dict`、`Any`、宽 `object`、未冻结字符串枚举或私有原始
yt-dlp payload。确认没有新增 `ErrorCode`。

必须记录 TASK-006 在 TASK-005 最终契约上可依赖的精确字段与可空规则，作为 ADR-007
后续复核证据；不得在本审查中修改 ADR-007。

### B. 选择、解析与质量

不要只运行已有测试；至少设计独立表驱动探针覆盖：

- 人工全局优先、人工候选全部无效后自动回退、语言 exact/base/variant 和稳定
  tie-break；
- JSON3/VTT/SRT 的 BOM、非法 UTF-8、CRLF、HTML/NFC、speaker、marker、滚动前缀；
- T-08 每个阈值的边界前后、超限输入、极端 segment 数和异常压缩比；
- refresh 只使 raw generation 变化，规范/质量版本只使 canonical key 变化。

检查实现是否错误接受 malformed payload、静默截断、语义重写、模糊修复或依赖测试
私有实现细节才能成立。

### C. yt-dlp/HTTP/安全边界

独立证明：

- `extract_info(..., download=False)`，安全 options 无 Cookie/登录/`.netrc`、
  remote components、ffmpeg、postprocessor 或媒体写入；
- 临时字幕 URL 只在内存，重定向的每一跳均验证 scheme/host，响应大小和短读受限，
  所有成功/异常路径关闭 response；
- URL/track/payload 使用 allowlist 与长度边界，不能通过 DNS/redirect/编码变化绕过
  SSRF 防线或 DATA 路径边界；
- 401/403、正文 403/404、429/Retry-After、timeout、短读、5xx、危险 URL、内容
  不可用、磁盘/权限分类符合 ADR-006；
- 异常、cause/context、traceback、日志、SQLite 和 handoff 不泄漏 URL、字幕正文、
  Cookie、密钥或绝对路径。

不得运行真实 YouTube、字幕、RSS、Cookie、登录、remote components、ffmpeg、媒体、
真实 Vault 或密钥路径。

### D. Artifact、缓存与真实 SQLite 恢复

使用临时 DATA/SQLite 独立验证：

- 首次成功的两个 Artifact、Provider call、Pipeline 和 Job 同事务；
- verified cache 命中零网络、零重新规范化，并以空 Artifact completion 推进新 Job；
- 文件先成功、`complete_stage` 注入失败后 DB 全回滚，下一 attempt 验证确定性文件并
  补索引；
- DB 有记录但文件缺失、篡改、路径越界或 symlink 越界时 fail-closed；
- refresh 生成新路径且不覆盖旧 Artifact；
- 并发/重复执行不产生错误绑定、重复 Provider call 或错误 Pipeline 推进。

真实静态 Repository wiring 必须重新验证，不得通过 `cast`、`type: ignore`、wrapper
或 monkey patch 掩盖接口不兼容。

### E. 可读性、架构与变更规模

本实现为 4,384 行新增/修改，其中 `transcripts.py` 1,664 行、integration test
1,020 行，明显超过普通单次变更规模。不能仅因测试通过而批准。必须独立判断并记录：

- 模块是否同时承担选择、解析、文件、缓存、Repository 编排等过多职责；
- 是否存在重复分支、难以证明的状态组合、过深控制流、无效抽象或只为测试存在的生产
  hooks；
- 测试是否主要验证外部行为，还是复制实现算法/依赖大量私有符号导致“实现和测试一起
  错”；
- 是否存在死代码、兼容 shim、超大函数/类、无界内存拷贝、重复全文件读取或潜在性能
  问题；
- 若建议拆分，是否属于阻断正确性/维护性的 P1，还是可登记到后续任务的 P2/P3。

大变更本身不是自动 `REJECT` 理由；若无具体问题，不得仅按行数拒绝。反之，不得以
“以后重构”推迟真实 P0/P1。

### F. 范围、复用与许可证

确认只直接复用 `yt-dlp==2026.7.4` 和标准库；外部 MIT 项目仅参考测试思想、没有
复制代码。复核锁文件中的 `mutagen` GPL 风险仍只属于 TASK-014 分发门禁，没有被
本实现扩大。确认无依赖、Schema、认证、真实网络、媒体或 Vault 红线。

## 验收矩阵与 Finding 规则

逐项给出：

- AC-1 至 AC-5；
- ADR-006 T-01 至 T-15；
- 五轴 correctness/readability/architecture/security/performance；
- 复用、许可证、范围和红线。

Findings 使用 `P0/P1/P2/P3`，给出文件、行号、可复现输入、期望/实际和影响：

- 任一未解决 P0/P1：`REJECT`；
- 必需门禁失败或跳过：`REJECT`；
- 公共契约、缓存恢复、安全边界或真实 Repository 组合未被外部证据证明：`REJECT`；
- 只有 P2/P3 时，可在明确风险/跟踪责任后 `APPROVE`；
- 无 finding 且全部门禁通过：`APPROVE`。

不得修改产品代码或测试来让检查通过。

## 写入审查证据

完成审查后，只编辑 `handoffs/TASK-005.md` 的 Reviewer 部分，记录：

- Reviewer session 与固定 source SHA；
- 所有复跑命令和结果；
- 独立探针 A-F；
- AC/T-01..T-15/五轴矩阵；
- Findings、Verdict、跳过项、剩余风险和 TASK-006 最终契约复核；
- 明确未运行的真实网络/认证/媒体/Vault 路径。

确保完整 handoff 无尾随空白，随后只暂存并提交该文件：

```text
docs: review TASK-005 subtitle pipeline
```

提交后必须满足：

- review evidence commit 唯一父提交为
  `98d19700818bcae14efc412aaaaeb6eed97a1535`；
- review commit 只修改 `handoffs/TASK-005.md`；
- source worktree 干净；
- main 未修改且仍干净；
- 不合并、不改任务状态、不 push、不清理分支/worktree。

## 回传格式

```text
Task: TASK-005
Role: Independent Codex Reviewer
Reviewed implementation head: 98d19700818bcae14efc412aaaaeb6eed97a1535
Review evidence commit:
Checks rerun:
Independent probes A-F:
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
