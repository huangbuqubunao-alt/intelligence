# TASK-014B10：安全内容可用性诊断

- Status: `DONE`
- Assignee: `Codex Product Integrator（已完成离线整合）`
- Reviewer: `全新独立 Codex Reviewer 2（APPROVE，P0–P3=0）`
- 依赖：TASK-014B4/B5/B6/B7/B8 `DONE`、ADR-020 `Accepted`
- 实施基线：`main@6fd7b5cc3fae6466fb6181151513f4854d196683`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic`
- Branch：`codex/task-014b10-safe-content-availability-diagnostic`
- Implementation HEAD：`3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20`（唯一父提交
  `6fd7b5cc3fae6466fb6181151513f4854d196683`）
- First Reviewer evidence：`2ea3455246a596f8304d2b0c00435862f8f3ea9e`（唯一父提交为 implementation；仅追加
  `handoffs/TASK-014.md`）
- Correction 1 HEAD：`c65502e3680d14a88ae52a1c27eea47d42b5e8b0`（唯一父提交为 First Reviewer evidence）
- Accepted source / Reviewer 2 evidence：`880e796622e393842a8cfe1a365af25868a3e98f`（唯一父提交为 Correction 1；仅追加
  `handoffs/TASK-014.md`）
- Merge commit：`5b485fa5856654d2a8d9f588b5ef1ab807b52bc3`（有序双父为
  `0f051049385e9fc1b7a15cd6cfa6e6fdf3fa8352`、`880e796622e393842a8cfe1a365af25868a3e98f`）
- Reuse decision：`DIRECT` — 既有锁定 subtitle Adapter、B4 directory-only、B5 安全摘要、ADR-015--ADR-019 固定诊断、JsonlLogger
  safe_message 与离线 integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

三个不同公开视频均在 metadata/enumerate 后、正文读取前以 `CONTENT_UNAVAILABLE` 停止。B9 evidence
`bd770ef9d212ebe75689b8f33145bf2556fe93c2` 仅是未合并的只读失败证据，不得合并、修改、清理或写成成功。B10 不再选择或验证
更多视频，而是在既有受限 directory-only smoke 的安全出口增加固定、无敏感值的可用性来源分类，帮助区分视频不可用、访问环境受限、
提取器兼容性不足或无法安全确定。

## 冻结契约

- 仅当 directory-only 受限路径最终安全码为 `CONTENT_UNAVAILABLE` 且正文 `read=0` 时，可在既有安全 stdout 摘要与既有 JSONL
  `safe_message` 输出一个 ADR-020 固定 `content_availability` code。
- 词表严格且仅为 `content_availability_video_unavailable`、`content_availability_environment_restricted`、
  `content_availability_extractor_compatibility`、`content_availability_unknown`。前三者只可由既有本地无值内部状态/固定映射分支选择；
  无法安全判定时必须为 unknown。
- 不新增 JSONL schema 字段、`logging.py`、Provider metadata、CLI 参数、配置、Schema/migration、依赖或锁文件。不得改变退出码、
  重试、计数、默认 smoke 的一次正文读取、临时根、ID 上限、零业务记录、认证或 fail-closed 边界。
- ADR-015--ADR-019 的 `INVALID_RESPONSE` 诊断和词表保持不变；默认 smoke、成功、其他错误码、任何正文读取或不可靠分类不得输出
  availability code。不得扩大字幕解析接受面或增加兼容规则。
- 禁止 URL、标题、语言、轨道、字段名/字段值、原始响应、异常原文、路径、Cookie、token、payload、用户数据或凭据。测试只能使用无值
  内部状态/替身；不得新增或恢复真实或结构化目录 fixture。
- TASK-014 始终 `IN_PROGRESS / No-Go`；B10 只帮助决定下一步，不构成真实验证通过、真实服务验证、发行批准或最终 Go。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

最终 Diff 可以是上述允许范围的最小子集；不得为满足文档制造无关改动。不得修改 fixture 路径、依赖、`uv.lock`、Schema/migration、
`logging.py`、默认 CLI、配置、认证边界、发布状态、B-1/B9 evidence 或任何其他路径。

## Implementation evidence 与独立 Reviewer 控制面

- Git-only 核验确认 source `3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20` 是冻结实施基线的唯一子提交，source 干净；完整
  Diff 严格且仅为上述五路径，`git diff --check` 通过，且无 fixture、依赖、锁、Schema/migration、配置、默认 CLI 或日志 schema 改动。
- Implementer 在 source `handoffs/TASK-014.md` 记录了 focused `127 passed`、mypy、Ruff、CLI help、锁定离线同步、范围及
  全输出面泄漏扫描均通过；这些是 implementation evidence，尚不是独立 Reviewer 通过证据。
- 正式 Reviewer 包为
  `agent-prompts/TASK-014B10-SAFE-CONTENT-AVAILABILITY-DIAGNOSTIC-REVIEWER-CODEX.md`；本控制面不启动 Reviewer。
- Reviewer 必须独立验证固定词表/unknown、严格触发条件、后续行动语义而非事实断言、默认 smoke 与 B4--B8 回归、全输出面隐私、
  无 parser/schema/依赖/CLI/logging 扩张，并独立运行任务包规定的离线 focused tests、mypy、Ruff、CLI help、范围和泄漏扫描。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，只能追加 evidence 并创建以 implementation HEAD 为唯一父的 handoff-only
  commit；不得修改业务代码、测试、控制面或任务状态。发现 P0/P1 时按 Reviewer 包立即停止后续产品命令并记录 `REJECT`。
- B9 evidence `bd770ef9d212ebe75689b8f33145bf2556fe93c2` 仍未合并，只作只读失败证据；不得合并、修改、清理或写成成功。

## First review REJECT 与 Correction 1

- 第一轮独立 Reviewer evidence `2ea3455246a596f8304d2b0c00435862f8f3ea9e` 仅追加 source handoff，Verdict=`REJECT`，
  `P0=0`、`P1=1`。Reviewer 在确认 P1 后按包立即停止；未运行 uv、focused tests、mypy、Ruff、CLI help、最终 Diff check 或正式
  全输出面泄漏扫描，任何未运行项都不是通过证据。
- P1：生产 yt-dlp 会以 `DownloadError` 包装 `ExtractorError`，而 implementation 的 extractor-compatibility 分支只接受直接
  `ExtractorError`，导致生产 Adapter 映射无法到达该分类；现有测试直接构造私有状态，未验证生产映射边界。普通或来源不可靠的
  提取异常不得标为兼容性问题，必须回退固定 unknown。
- Correction 1 必须以 Reviewer evidence 为唯一父提交，先由生产 Adapter 异常映射入口 RED 复现；只有有限、可靠、类型化异常链能证明
  底层 `ExtractorError` 时才允许既定 compatibility code。普通 `DownloadError`、缺失可靠 cause/info、畸形/循环/超限链或任何不确定
  情况必须 unknown；禁止依据异常字符串、URL、状态文本或外部字段值猜测。
- 正式 Correction 1 Implementer 包为
  `agent-prompts/TASK-014B10-SAFE-CONTENT-AVAILABILITY-DIAGNOSTIC-CORRECTION-1-IMPLEMENTER-CODEX.md`；本控制面不启动
  Implementer。允许范围仍为本卡五路径上限的最小子集，smoke source/test 只有确有必要时才可修改；不新增 fixture、依赖、锁、Schema、
  配置、CLI、日志 schema 或真实资源权限。
- Correction 1 已提交为 `c65502e3680d14a88ae52a1c27eea47d42b5e8b0`，唯一父提交为 first review evidence。Git-only
  核验确认 Correction Diff 严格为 Adapter、Provider integration test 与 `handoffs/TASK-014.md` 三路径，完整 B10 Diff 仍严格位于
  原五路径；两组 `git diff --check` 通过，source 干净，B9 evidence 仍未合并。Correction handoff 记录的 focused `137 passed`、mypy、
  Ruff、CLI help、锁定离线同步、范围与泄漏扫描均只是 Implementer evidence，不是独立 Reviewer 2 通过证据。
- 正式 Reviewer 2 包为
  `agent-prompts/TASK-014B10-SAFE-CONTENT-AVAILABILITY-DIAGNOSTIC-CORRECTION-1-REVIEWER-2-CODEX.md`；本控制面不启动
  Reviewer。Reviewer 2 必须从生产 Adapter 捕获/转换入口独立覆盖精确 wrapped `DownloadError` 类型链、全部 fixed mapping 与
  unknown fail-closed 矩阵，并重新运行包内离线门禁；不得依赖 Implementer 自报结果。
- Reviewer 2 唯一可写路径是 source `handoffs/TASK-014.md`，只能追加独立审查 evidence 并创建以 Correction HEAD 为唯一父提交的
  handoff-only commit；不得修改业务代码、测试、控制面或任务状态。该阶段 TASK-014B10 进入 `IN_REVIEW`；TASK-014 始终
  `IN_PROGRESS / No-Go`，第一轮 REJECT 和 Correction 均不构成真实验证、发行批准或最终 Go。

## Second review APPROVE 与 Product Integrator 授权

- Reviewer 2 evidence `880e796622e393842a8cfe1a365af25868a3e98f` 是 Correction 1 的 handoff-only 唯一子提交，Verdict=`APPROVE`，
  `P0=0`、`P1=0`、`P2=0`、`P3=0`。独立门禁包括锁定离线同步、Provider/Smoke focused `137 passed`、mypy、Ruff、CLI help、
  Correction/完整 B10 `git diff --check`、三/五路径范围、fixture/禁止路径与 stdout/stderr/JSONL/test/handoff 泄漏扫描。
- Reviewer 的补充内联生产 Adapter 探针有两次在自定义替身构造阶段退出 `1`，未进入目标 Adapter case；Reviewer 已明确将其排除，
  不得记录或复用为通过证据。正式 focused `137` 和其他独立门禁才是本次验收证据。Reviewer 未运行 full pytest 或 build；这些未运行项
  必须由 Product Integrator 在合并前独立完成。
- Git-only 验收确认 source/Reviewer evidence、完整逐提交唯一父链和双方洁净度匹配；Correction Diff 严格为 Adapter、Provider
  integration test 与 handoff 三路径，完整 B10 Diff 严格为本卡五路径，evidence 严格 handoff-only。无 fixture、依赖、`uv.lock`、
  Schema/migration、配置、默认 CLI、`logging.py`/日志 schema 或范围外变更；B9 evidence 仍未合并。
- Product Integrator 已按正式包完成 lock check、locked offline sync、Provider/Smoke focused `137 passed`、full pytest
  `508 passed`、mypy、Ruff、CLI help、offline build、完整五路径、Correction 三路径、Reviewer handoff-only、`git diff --check`
  与 stdout/stderr/JSONL/test/handoff/fixture 泄漏扫描，并执行唯一获准的
  `git merge --no-ff 880e796622e393842a8cfe1a365af25868a3e98f`。Reviewer 的失败补充内联探针仍明确排除，未计入通过证据。
- 合并后双父顺序、accepted source 祖先关系、first-parent 五路径、锁/依赖及 fixture/Schema/config/默认 CLI/日志 schema 不变、
  main/source 洁净度均通过 Git-only 核验；source 保留且干净，B9 evidence 仍未合并。
- TASK-014B10 现为 `DONE`；TASK-014 始终 `IN_PROGRESS / No-Go`。B10 离线实现与整合不构成真实 YouTube/smoke 成功、普遍
  yt-dlp 兼容性证明、事实性根因确认、发行批准或最终 Go。

## 离线验收与交付

- 离线回归必须覆盖四个固定 classification 与 unknown 回退；stdout、stderr、JSONL 无敏感材料；directory-only 维持 `1/1/0`，
  默认 smoke 保持一次正文读取，B6/B7/B8、CLI 和全部 fail-closed 边界不退化。
- Implementer 首个产品提交必须以 `6fd7b5cc3fae6466fb6181151513f4854d196683` 为唯一父提交。控制面文档不进入 source；完成后由全新独立
  Reviewer 审查。
- 仅可先运行一次 `uv sync --locked --offline`；缓存缺失、锁文件变化、下载/网络迹象或失败立即停止。仅在已有离线 `.venv` 可用时，允许按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、合并、source 清理、测试/检查外产品命令与 `.codebase-memory` 工件。完成时只创建一个允许路径内的 Implementer
  commit 并追加 handoff；不得自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
