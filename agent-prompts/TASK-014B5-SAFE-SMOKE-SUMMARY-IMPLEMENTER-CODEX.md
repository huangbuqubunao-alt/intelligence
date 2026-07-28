# TASK-014B5 — 安全 smoke 摘要输出 Implementer

你是 TASK-014B5 的唯一 Codex Implementer。只在固定 worktree 实现安全摘要；不得扩大为通用日志、诊断、下载或真实资源工作。本包不启动实施。

## 固定分配

```text
Task: TASK-014B5 — safe smoke summary output
Role: Implementer
Agent: Codex
Base: main@b1ea7a66aaf513aa0fa8262780f9c59072cc18b4
Worktree: /Users/hua/Documents/yia-worktrees/task-014b5-safe-smoke-summary
Branch: codex/task-014b5-safe-smoke-summary
Reuse decision: DIRECT — existing restricted smoke CLI, PublicSubtitleSmoke, fixed safe error codes, ADR-015 diagnostics, JsonlLogger, and offline Fake/integration tests; no dependency or copied third-party code
```

- 开始前 source HEAD 必须精确为 `b1ea7a66aaf513aa0fa8262780f9c59072cc18b4` 且工作树干净；任一不符立即停止并报告。
- B-1 execution evidence、旧 B-1 worktree 和 B-1 directory diagnostic worktree 均不得访问、修改、合并、清理或复用。
- TASK-014 保持 `IN_PROGRESS / No-Go`；本离线任务不授权真实 YouTube、真实 smoke、发布或最终 Go。

## 唯一允许范围与行为

仅可修改：

1. `src/youtube_intel/public_subtitle_smoke.py`
2. `src/youtube_intel/cli.py`
3. `tests/integration/test_public_subtitle_smoke.py`
4. `tests/integration/test_operations.py`
5. `handoffs/TASK-014.md`

为每个 `smoke-public-subtitles` 目标输出一条固定、脱敏、安全摘要。摘要仅可含公开稳定目标标识、metadata/enumerate/read
整数计数、最终固定安全错误码，以及目录 `INVALID_RESPONSE` 时的固定 `directory_diagnostic`。字段顺序和成功错误码必须稳定；
禁止 URL、正文、标题、语言、字段值、原始异常、路径、Cookie、token、payload、用户数据或凭据形状。不得改变 JSONL schema、
`logging.py`、默认 CLI 结构或 CLI 退出码语义。

directory-only 成功与目录失败必须每目标为 1/1/0；默认 smoke 仍读取既有一份正文。非 smoke 标志拒绝、smoke 全局配置参数
早拒绝、输入/临时根/timeout/无重试与所有 fail-closed 边界必须保持不变。

## 离线验证与禁止项

- 只可先运行一次 `uv sync --locked --offline`；缓存缺失、任何下载/网络迹象、锁变化或失败立即停止。禁止其他 `uv` 命令、
  安装和锁文件操作。
- 仅在已有离线 `.venv` 可用时，运行任务卡所列两份聚焦 pytest、mypy、Ruff、绝对 `.venv/bin/youtube-intel --help` 与
  `git diff --check`。不得运行真实 smoke、其他 CLI 子命令、构建、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、登录、Cookie、认证、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、launchd、push、合并、source 清理及范围外文件。

完成后只创建一个包含五条允许路径的 commit，并在 handoff 中记录直接复用、离线检查、精确 Diff 与泄漏扫描；不得自行
`ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
