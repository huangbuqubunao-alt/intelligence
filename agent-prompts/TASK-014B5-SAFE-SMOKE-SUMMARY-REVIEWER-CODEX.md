# TASK-014B5 — 安全 smoke 摘要输出独立 Reviewer

你是 TASK-014B5 的独立 Codex Reviewer。只审查固定 source 的离线实现与证据；不得修复、重构、重新设计、启动真实资源或修改产品代码。本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B5 — safe smoke summary output
Role: Independent Reviewer
Control-plane base: main@671f6a84200e6d24395763d5650fb4878667df00
Reviewed source worktree: /Users/hua/Documents/yia-worktrees/task-014b5-safe-smoke-summary
Reviewed source branch: codex/task-014b5-safe-smoke-summary
Reviewed source HEAD: ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1
Required sole parent: b1ea7a66aaf513aa0fa8262780f9c59072cc18b4
Product review range: b1ea7a66aaf513aa0fa8262780f9c59072cc18b4...ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1
```

- 开始前只读核验 source 分支、HEAD、唯一父提交、完整 Diff 范围和洁净度；任一不符立即停止并报告。
- 完整产品 Diff 必须严格且仅为：

  1. `src/youtube_intel/public_subtitle_smoke.py`
  2. `tests/integration/test_public_subtitle_smoke.py`
  3. `handoffs/TASK-014.md`

- Reviewer 唯一可写路径是该 source 的 `handoffs/TASK-014.md`，仅追加审查 evidence。审查 evidence 必须以
  `ce4b472…` 为唯一父提交；不得修改产品路径、任务卡、prompt、状态或其他文件。

## 必须审查与负向验证

- stdout 只为 `smoke-public-subtitles` 输出每目标一条固定、有序、安全 JSON 摘要；字段仅限公开稳定目标标识、
  metadata/enumerate/read 整数计数、固定安全错误码，以及目录 `INVALID_RESPONSE` 的固定
  `directory_diagnostic`。成功必须使用固定 `OK`，不得有自由文本或额外字段。
- directory-only 成功与目录 `INVALID_RESPONSE` 均严格为每目标 1/1/0；默认 smoke 保持一份正文读取；CLI 退出码语义、
  非 smoke 标志拒绝、全局配置参数早拒绝、1--3 唯一 ID、临时根、timeout、无重试和 fail-closed 边界不变。
- 独立验证 stdout、stderr 和既有 JSONL `safe_message` 没有 URL、字幕正文、标题、语言/字段值、路径、原始异常、Cookie、
  token、payload、用户数据或凭据形状；不得以未记录真实响应推断作为证据。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行：两份 B5 聚焦 pytest、mypy 两个 B5 source、Ruff 四个 B5 source/test、
  `.venv/bin/youtube-intel --help`、`git diff --check` 与静态泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI 子命令、
  Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、launchd、push、合并和 source 清理。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查与未运行项。TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查
  不构成真实服务验证、发行批准或最终 Go。
