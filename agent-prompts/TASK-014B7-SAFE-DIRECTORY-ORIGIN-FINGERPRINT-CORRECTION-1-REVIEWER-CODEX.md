# TASK-014B7 — 字幕目录安全来源与结构指纹 P1 Correction 1 独立 Reviewer

你是 TASK-014B7 P1 Correction 1 的全新独立 Codex Reviewer。只审查固定 source 的离线 Correction 与证据；不得修复、重构、
重新设计、启动真实资源或修改产品代码。本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint P1 Correction 1
Role: Independent Reviewer
Control-plane baseline: main@41dd2e260b7bed3713840f24f91bddaaeb74ed26
Execution main: dynamic clean main at the single-parent Correction 1 review authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Reviewed source branch: codex/task-014b7-safe-directory-origin-fingerprint
Reviewed source HEAD: 069e62ececada5152871fb7c626e64c146a270ad
Required sole parent of Correction 1: 8d06197557de4ce92c2752f4a8ef74582a0efdca
Required sole parent of original implementation: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Correction review range: 8d06197557de4ce92c2752f4a8ef74582a0efdca...069e62ececada5152871fb7c626e64c146a270ad
Complete B7 review range: 5b7dcca2ba9bd9e52e254a8944e584542838e24b...069e62ececada5152871fb7c626e64c146a270ad
```

- 开始前只读核验 dynamic main 与 source 的分支、HEAD、双重父链、Correction/完整 Diff 范围、fixture 删除状态和洁净度；任一不符立即停止并报告。
- Correction Diff 必须严格且仅为：

  1. 删除 `tests/fixtures/subtitles/directory_origin_fingerprint.json`
  2. `tests/integration/test_subtitle_provider.py`
  3. `tests/integration/test_public_subtitle_smoke.py`
  4. `handoffs/TASK-014.md`

- 完整 B7 Diff 必须为原六路径允许范围的五路径子集：`src/youtube_intel/providers/subtitles.py`、
  `src/youtube_intel/public_subtitle_smoke.py`、两份 integration test 与 `handoffs/TASK-014.md`；被删除 fixture 不得存在或在其他路径重现。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，仅追加审查 evidence，且 evidence 必须以 `069e62e…` 为唯一父提交。
  不得修改业务代码、测试、ADR、任务/状态控制面或其他 source 路径。

## 必须审查与负向验证

- 验证不合规 fixture 已删除。无字段名、字段值、URL、语言、轨道名、原始响应、Cookie、token、payload 或用户数据的内存 Mapping
  替身必须覆盖 ADR-018 四个 `directory_origin`、六个 `directory_fingerprint`、ADR-017 B6 `directory_diagnostic`、目录
  `INVALID_RESPONSE` enumerate=`1`/read=`0`、正文 `INVALID_RESPONSE` 无 origin/fingerprint，以及 stdout/stderr/JSONL
  无泄漏断言。
- 独立验证 fixture、测试和输出均不泄露上述受限数据；不合规 fixture 不得以改名、移动、嵌入或其他路径重现。
- 确认 Correction 没有改动生产代码、依赖、锁文件、Schema、CLI、`logging.py`、配置、解析接受面、默认/directory-only 计数、
  退出码、临时根、ID 上限、无重试、零业务记录或任何 fail-closed 边界。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行两份 B7 聚焦 pytest、mypy Provider/smoke、Ruff B7 tests、
  `.venv/bin/youtube-intel --help`、`git diff --check` 与静态范围/泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI
  子命令、Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、
  launchd、push、合并、source 清理和 `.codebase-memory` 工件。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查和未运行项。TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查不构成
  真实服务验证、发行批准或最终 Go。
