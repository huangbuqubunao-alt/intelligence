# TASK-014B7 — 字幕目录安全来源与结构指纹独立 Reviewer

你是 TASK-014B7 的独立 Codex Reviewer。只审查固定 source 的离线实现与证据；不得修复、重构、重新设计、启动真实资源或修改产品代码。本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint
Role: Independent Reviewer
Control-plane baseline: main@bcf8f1427ea129484979e6584cde9746a6a8ceca
Execution main: dynamic clean main at the single-parent review authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Reviewed source branch: codex/task-014b7-safe-directory-origin-fingerprint
Reviewed source HEAD: 8d06197557de4ce92c2752f4a8ef74582a0efdca
Required sole parent of implementation: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Complete review range: 5b7dcca2ba9bd9e52e254a8944e584542838e24b...8d06197557de4ce92c2752f4a8ef74582a0efdca
```

- 开始前只读核验 dynamic main 与 source 的分支、HEAD、父链、完整 Diff 范围和洁净度；任一不符立即停止并报告。
- 完整 B7 Diff 必须严格且仅为：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `src/youtube_intel/public_subtitle_smoke.py`
  3. `tests/fixtures/subtitles/directory_origin_fingerprint.json`
  4. `tests/integration/test_subtitle_provider.py`
  5. `tests/integration/test_public_subtitle_smoke.py`
  6. `handoffs/TASK-014.md`

- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，仅追加审查 evidence，且 evidence 必须以 `8d061975…` 为唯一父提交。
  不得修改业务代码、测试、ADR、任务/状态控制面或其他 source 路径。

## 必须审查与负向验证

- 精确审查 ADR-018 的四个固定无值 `directory_origin`：`directory_origin_extractor`、`directory_origin_decode`、
  `directory_origin_mapping`、`directory_origin_unknown`；以及六个固定无值 `directory_fingerprint`：
  `directory_fingerprint_top_level_not_mapping`、`directory_fingerprint_subtitle_bucket_missing_or_not_mapping`、
  `directory_fingerprint_language_bucket_missing_or_not_sequence`、`directory_fingerprint_track_entry_not_mapping`、
  `directory_fingerprint_required_field_missing`、`directory_fingerprint_unknown`。
- 验证 ADR-017 B6 `directory_diagnostic` 的原语义和七个固定值保持不变。origin/fingerprint 仅在目录 `INVALID_RESPONSE`
  且 enumerate=`1`/read=`0` 时进入既有安全 stdout/JSONL；正文 `INVALID_RESPONSE`、成功、非目录阶段或非 `INVALID_RESPONSE`
  不得输出这些新标签。
- 独立验证 stdout、stderr、JSONL 和 fixture 不泄露字段名、字段值、URL、字幕正文、标题、语言、轨道名、路径、原始异常、Cookie、
  token、payload 或用户数据。
- 验证不扩大解析接受面：身份、URL、格式、长度、数量、语言、条目与不支持目录仍 fail-closed；default 一次正文读取、
  directory-only `1/1/0`、退出码、CLI 拒绝、临时根、1--3 唯一 ID、无重试和零业务记录边界不退化。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行两份 B7 聚焦 pytest、mypy Provider/smoke、Ruff B7 source/tests、
  `.venv/bin/youtube-intel --help`、`git diff --check` 与静态范围/泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI
  子命令、Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、
  launchd、push、合并、source 清理和 `.codebase-memory` 工件。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查和未运行项。TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查不构成
  真实服务验证、发行批准或最终 Go。
