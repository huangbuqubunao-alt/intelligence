# TASK-014B10 — 安全内容可用性诊断 Correction 1 独立 Reviewer 2

你是 TASK-014B10 的全新独立 Codex Reviewer 2。只审查固定 source 上的 Correction 1 与完整 B10 离线产品 Diff；不得依赖
Implementer 自报结论，不得修复、重构、重新设计、修改产品代码或启动真实资源。本包只创建授权，不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B10 — safe content availability diagnostic, Correction 1 review
Role: Independent Reviewer 2
Control-plane baseline: main@78bb8b402ee47403ed37f38a27f0ffd5a359b719
Execution main: dynamic clean main at the single-parent Reviewer 2 authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic
Reviewed source branch: codex/task-014b10-safe-content-availability-diagnostic
Reviewed Correction HEAD: c65502e3680d14a88ae52a1c27eea47d42b5e8b0
Required sole parent of Correction: 2ea3455246a596f8304d2b0c00435862f8f3ea9e
First Reviewer evidence: 2ea3455246a596f8304d2b0c00435862f8f3ea9e (sole parent 3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20; handoff-only; REJECT, P1=1)
Original implementation: 3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20
Original implementation base: 6fd7b5cc3fae6466fb6181151513f4854d196683
Correction review range: 2ea3455246a596f8304d2b0c00435862f8f3ea9e...c65502e3680d14a88ae52a1c27eea47d42b5e8b0
Complete B10 review range: 6fd7b5cc3fae6466fb6181151513f4854d196683...c65502e3680d14a88ae52a1c27eea47d42b5e8b0
Read-only B9 failure evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2 (must remain unmerged; do not modify, clean, rewrite, or call passing)
Reuse decision: DIRECT — locked yt-dlp typed exceptions, existing subtitle Adapter catch/convert boundary, ADR-020 vocabulary, B4 directory-only, B5 safe summary, B6--B8 diagnostics, and offline integration infrastructure; no dependency or third-party change
```

- 开始前只读核验 dynamic main、source 分支/HEAD、implementation→first review evidence→Correction 的逐提交唯一父链、双方洁净度、
  B9 evidence 未合并状态及 `git diff --check`。Correction Diff 必须严格且仅为
  `src/youtube_intel/providers/subtitles.py`、`tests/integration/test_subtitle_provider.py`、`handoffs/TASK-014.md`；完整 B10 Diff
  必须严格且仅为上述三路径加 `src/youtube_intel/public_subtitle_smoke.py`、
  `tests/integration/test_public_subtitle_smoke.py`。任一固定身份、父链、洁净度或范围不符，立即停止且不得写 evidence。
- 确认无 fixture、依赖、`uv.lock`、Schema/migration、配置、默认 CLI、`logging.py`/日志 schema、认证边界、控制面产品改动或字幕
  目录/正文解析接受面扩张。不得合并、修改、清理或改写 B9 evidence、first review evidence 或任何 source 历史。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，且只能追加独立审查 evidence；evidence commit 必须以
  `c65502e3680d14a88ae52a1c27eea47d42b5e8b0` 为唯一父提交并保持 handoff-only。不得修改业务代码、测试、ADR、任务/状态控制面或
  其他 source 路径。

## 必须独立审查

1. **生产映射边界与正确性**：必须通过生产 `YtDlpSubtitleAdapter` 捕获/转换入口和既有无网络替身构造精确外层
   `DownloadError` 包装链，覆盖真实 Adapter mapping；不得只调用私有分类函数、私有 error helper 或直接构造私有分类状态作为证据。
2. **可信类型链 fixed mapping**：只在精确 `DownloadError` 外层及有限、可靠、类型化 cause/exception info 链均成立时，验证
   `GeoRestrictedError` → `content_availability_environment_restricted`、`UnavailableVideoError` →
   `content_availability_video_unavailable`、其他可靠 `ExtractorError` →
   `content_availability_extractor_compatibility`。这些是后续行动分类，不得把推断写成真实原因或已确认事实。
3. **unknown fail-closed**：普通 `DownloadError`、直接而未形成可信生产包装链的提取异常、缺失可靠 cause/exception info、畸形、
   不确定、循环或超过 8 层的异常链，以及任何其他不能安全证明的来源，都必须为固定 `content_availability_unknown`。不得依据异常
   message/字符串、URL、状态文本、响应字段或任何外部值推断分类。
4. **安全出口与回归**：四项 fixed vocabulary 只能在受限 directory-only、最终 `CONTENT_UNAVAILABLE`、enumerate=`1`、read=`0`
   全部成立时进入既有安全 stdout 摘要与 JSONL `safe_message`。验证 default smoke 仍恰有一次正文读取，directory-only 计数、退出码、
   无重试、临时根、ID 上限、零业务记录、B4--B8 fixed classification、其他 B10 分类及全部 fail-closed 边界不退化。
5. **隐私、安全与架构**：独立扫描 stdout、stderr、JSONL、测试新增行和 handoff；不得包含 URL、标题、语言、轨道、响应字段名/值、
   异常原文、原始响应、路径、Cookie、token、payload、用户数据或凭据。确认无新增/恢复/内嵌/移动 fixture，无依赖、锁文件、
   Schema、配置、默认 CLI、JSONL/logging schema 或认证变化，且字幕解析接受面未扩大。ADR-019 既有受限合成键名例外不得扩大。

## 独立离线门禁与停止规则

- 不得复用 Implementer 的 `137 passed`、mypy、Ruff、CLI help 或泄漏扫描自报。仅可先运行一次 `uv sync --locked --offline`；缓存
  缺失、锁变化、下载/网络迹象或失败立即停止，不得重试、修复环境或使用替代命令。同步成功且固定 source 的绝对 `.venv` 工具存在时，
  按序独立运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check 2ea3455246a596f8304d2b0c00435862f8f3ea9e...c65502e3680d14a88ae52a1c27eea47d42b5e8b0
git diff --check 6fd7b5cc3fae6466fb6181151513f4854d196683...c65502e3680d14a88ae52a1c27eea47d42b5e8b0
```

- 另做 Correction 三路径、完整 B10 五路径、全部禁止路径以及 stdout/stderr/JSONL/test/handoff 全输出面泄漏扫描。不得运行 full pytest、
  build、真实 smoke、其他 CLI 子命令、网络或任何真实资源。
- 以 P0、P1、P2、P3 分级记录全部发现，并给出 `APPROVE` 或 `REJECT`。一旦确认 P0 或 P1，立即停止后续产品命令，不修复、不重试；
  只可把已取得证据、未运行项与 `REJECT` 追加到 source handoff，并创建唯一 handoff-only evidence commit。P2/P3 仍须如实记录并完成
  其余门禁，除非继续执行本身不安全。
- 禁止真实 YouTube、网络、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、
  push、merge、source 清理和 `.codebase-memory` 工件。TASK-014B10 保持 `IN_REVIEW`，TASK-014 保持 `IN_PROGRESS / No-Go`；
  Correction 与离线审查不构成真实服务验证、事实性根因确认、发行批准或最终 Go。
