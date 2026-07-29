# TASK-014B10 — 安全内容可用性诊断 Implementer

你是 TASK-014B10 的 Codex Implementer。只在固定 source worktree 离线实现 ADR-020 的固定、无值 availability 分类；不得选择新视频、
修复真实兼容性、放宽解析、修改控制面或启动真实资源。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B10 — safe content availability diagnostic
Role: Implementer
Agent: Codex
Implementation baseline: main@6fd7b5cc3fae6466fb6181151513f4854d196683
Control-plane execution main: dynamic clean main at the single-parent authorization commit containing this prompt; it must descend from the implementation baseline and contain no unreviewed product changes
Worktree: /Users/hua/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic
Branch: codex/task-014b10-safe-content-availability-diagnostic
Required source HEAD: 6fd7b5cc3fae6466fb6181151513f4854d196683
Required sole parent of first product commit: 6fd7b5cc3fae6466fb6181151513f4854d196683
Read-only B9 failure evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2 (must not merge, modify, clean, or call passing)
Allowed scope: src/youtube_intel/providers/subtitles.py; src/youtube_intel/public_subtitle_smoke.py; tests/integration/test_subtitle_provider.py; tests/integration/test_public_subtitle_smoke.py; handoffs/TASK-014.md
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-015--ADR-019 diagnostics, existing JsonlLogger safe_message, and offline integration tests; no dependency or third-party change
```

- 开始前只读核验 dynamic main、source 分支/HEAD、source/main 洁净度、固定父链和 B9 evidence 的未合并只读状态；任一不符立即停止。
  source 不得暂存或提交控制面文件，首个产品提交必须以 fixed baseline 为唯一父。

## 冻结实现契约

- 只在 `smoke-public-subtitles --directory-only` 的最终安全码为 `CONTENT_UNAVAILABLE` 且正文 `read=0` 时，才可经既有安全 stdout
  摘要和既有 JSONL `safe_message` 输出一个 `content_availability` code。不得新增 JSONL schema 字段、`logging.py`、Provider metadata、
  CLI 参数、配置或持久化模型。
- 词表严格且仅为：`content_availability_video_unavailable`、`content_availability_environment_restricted`、
  `content_availability_extractor_compatibility`、`content_availability_unknown`。前三者只可由既有本地、无值内部状态或固定映射分支选择；
  任何不可靠、部分或不安全判断都必须输出 unknown，绝不猜测或拼接动态文本。
- 默认 smoke、成功、其他错误码、任何正文读取或非 directory-only 路径必须省略 availability code。ADR-015--ADR-019 的
  `INVALID_RESPONSE` 诊断/词表、退出码、重试、metadata/enumerate/read 计数、默认一次正文读取、CLI、临时根、ID 上限、零业务记录、
  认证和所有 fail-closed 边界不得改变。
- 不得读取、输出或持久化 URL、标题、语言、轨道、字段名/字段值、原始响应、异常原文、路径、Cookie、token、payload、用户数据或凭据；
  不得扩大解析接受面或新增兼容规则。测试只能用无值内部状态/替身；不得新增、恢复或读取真实或结构化目录 fixture。

## 允许检查与交付

- 仅可先运行一次 `uv sync --locked --offline`；缓存缺失、锁变化、下载/网络迹象或任何失败立即停止。只有已有离线 `.venv` 可用时，允许按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

- 交付前核验完整 Diff 是允许范围的最小子集、无 fixture/依赖/锁/Schema/CLI/logging/control-plane 变更，且 stdout/stderr/JSONL/test/handoff
  仅含固定无值 code 和其他授权安全材料。只创建一个首父为 fixed baseline 的 Implementer commit，并追加 source handoff；不得自行设置
  `IN_REVIEW`、`ACCEPTED` 或 `DONE`，不得启动 Reviewer、合并、push 或清理 source。
- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用和 `.codebase-memory` 工件。TASK-014 始终 `IN_PROGRESS / No-Go`；B10 离线实现不构成真实验证通过、发行批准或最终 Go。
