# TASK-014B10 — 安全内容可用性诊断 Correction 1 Implementer

你是 TASK-014B10 的原 Codex Implementer。只在固定 source 谱系离线修复第一轮 Reviewer 的唯一 P1：生产 yt-dlp 异常包装边界必须
能够以类型化、可靠证据选择 extractor-compatibility；任何不可靠来源必须回退 fixed unknown。本包只创建授权，不启动 Implementer。

## 固定分配

```text
Task: TASK-014B10 — safe content availability diagnostic, Correction 1
Role: Implementer
Agent: original Codex Implementer
Control-plane baseline: main@16f168b032d060fc9f2e46ced5744d81b7db6d2b
Execution main: dynamic clean main at the single-parent Correction 1 authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Worktree: /Users/developer/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic
Branch: codex/task-014b10-safe-content-availability-diagnostic
Implementation: 3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20
First Reviewer evidence / required source HEAD: 2ea3455246a596f8304d2b0c00435862f8f3ea9e
Required sole parent of first Correction commit: 2ea3455246a596f8304d2b0c00435862f8f3ea9e
Original implementation base: 6fd7b5cc3fae6466fb6181151513f4854d196683
Read-only B9 failure evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2 (must remain unmerged; do not modify, clean, rewrite, or call passing)
Maximum allowed Correction scope: src/youtube_intel/providers/subtitles.py; src/youtube_intel/public_subtitle_smoke.py only if demonstrably necessary; tests/integration/test_subtitle_provider.py; tests/integration/test_public_subtitle_smoke.py only if demonstrably necessary; handoffs/TASK-014.md
Reuse decision: DIRECT — existing locked yt-dlp exception types, subtitle Adapter mapping boundary, ADR-020 vocabulary, B4 directory-only, B5 safe summary, B6--B8 diagnostics, and offline integration infrastructure; no dependency or third-party change
```

- 开始前只读核验 dynamic main、source 分支/HEAD、implementation→Reviewer evidence 唯一父链、source/main 洁净度、B9 未合并状态、
  第一轮 evidence handoff-only 范围及完整 B10 五路径范围；任一不符立即停止。不得修改或重写 Reviewer evidence。
- 第一轮 Reviewer Verdict=`REJECT`、`P1=1`：生产 yt-dlp 以 `DownloadError` 包装 `ExtractorError`，而 implementation 仅在捕获对象
  本身为直接 `ExtractorError` 时选择 extractor-compatibility，导致真实 Adapter 映射不可达；测试又绕过生产映射边界直接构造私有状态。

## 严格 TDD 与冻结修复

1. **先 RED**：在修改生产代码前，通过现有无网络 Fake factory 调用生产 `YtDlpSubtitleAdapter.enumerate_tracks` 异常映射入口，构造一个
   `DownloadError` 包装的无值合成异常边界，证明当前代码不能从可靠的类型化 `ExtractorError` 链得到既定
   `content_availability_extractor_compatibility`。必须记录该失败；不得仅直接调用私有分类函数、私有状态或私有 error helper 代替。
2. **可靠类型链才允许 compatibility**：只有有限、有界且防循环的类型化异常链能够可靠证明底层为 `ExtractorError` 时，才可选择既定
   extractor-compatibility code。只检查异常对象/类型身份及锁定 yt-dlp 提供的类型化 cause/exception information；不得读取或依据
   异常字符串、URL、HTTP/status 文本、响应字段名/字段值或其他动态材料猜测。
3. **unknown fail-closed**：普通 `DownloadError`、缺少可靠 cause/exception information、畸形或循环异常链、链深超限及任何其他不确定
   来源，必须得到固定 `content_availability_unknown`。通用提取异常不能仅因名称、message 或外层异常类型被标为兼容性问题。
4. **回归不变**：保持 `directory-only + CONTENT_UNAVAILABLE + enumerate=1 + read=0` 输出门禁、四项固定词表、video-unavailable、
   environment-restricted 与 unknown 语义、默认 smoke 一次正文读取、退出码、metadata/enumerate/read 计数、无重试、临时根、ID 上限、
   零业务记录、B4--B8 分类及所有 fail-closed 边界不变。不得扩大字幕目录/正文解析接受面或新增兼容规则。
5. **无值测试材料**：测试不得包含真实异常文本、URL、标题、语言、轨道、响应字段名/字段值、原始响应、路径、Cookie、token、payload、
   用户数据或凭据。若异常构造器需要文本，只能使用不含任何分类 marker 的固定通用安全占位，并且分类不得读取或断言该文本。

实际 Correction Diff 必须是最大允许范围的最小子集；不要求修改 smoke source/test，只有生产映射和必要回归确实需要时才可触及。
不得新增/恢复/移动 fixture，不得修改依赖、`uv.lock`、Schema/migration、配置、默认 CLI、`logging.py`/日志 schema、认证边界、ADR、
任务状态、Reviewer prompt 或其他控制面。

## 离线验证与交付

- 仅可先运行一次 `uv sync --locked --offline`；缓存缺失、锁变化、下载/网络迹象或失败立即停止，不得重试、修复环境或替代命令。
  同步成功且固定 source 的 `.venv` 工具存在时，按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

- 交付前核验 Correction Diff 和完整 B10 Diff 都是允许范围的最小子集，并扫描 stdout、stderr、JSONL、测试新增行及 handoff；不得出现
  未授权动态/敏感材料，ADR-019 既有受限合成键名例外不得扩大。只在 source `handoffs/TASK-014.md` 追加 Correction evidence，创建
  一个以 `2ea3455246a596f8304d2b0c00435862f8f3ea9e` 为唯一父提交的 Correction commit，报告 RED/GREEN 与实际门禁。
- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、full pytest、build、push、merge、source 清理和 `.codebase-memory` 工件。不得自行设置 `IN_REVIEW`、`ACCEPTED` 或 `DONE`，
  不得启动 Reviewer。TASK-014B10 保持 `IN_PROGRESS / Codex`，TASK-014 保持 `IN_PROGRESS / No-Go`；Correction 不构成真实验证、
  兼容性结论、发行批准或最终 Go。
