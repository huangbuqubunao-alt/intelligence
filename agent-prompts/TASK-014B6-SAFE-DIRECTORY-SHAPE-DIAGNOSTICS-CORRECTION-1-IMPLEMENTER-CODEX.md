# TASK-014B6 — 安全字幕目录结构诊断 P1 Correction 1 Implementer

你是 TASK-014B6 的原 Codex Implementer。只修复已确认的 P1：未知目录 `INVALID_RESPONSE` 的安全摘要 fallback 必须使用
ADR-017 精确固定 code `directory_shape_unknown`。不得修复其他问题、重新设计、放宽解析或修改控制面。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B6 — safe subtitle directory shape diagnostics P1 Correction 1
Role: Implementer
Agent: Codex
Control-plane base: main@e5d91ef1271271e0ba5f33e38a78211a35127431
Execution main: dynamic clean main at the single-parent Correction 1 authorization commit containing this prompt; it must descend from the control-plane base and contain no unreviewed product changes
Worktree: /Users/hua/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics
Branch: codex/task-014b6-safe-directory-shape-diagnostics
Required source HEAD / sole parent of Correction 1: 9403e37eedbd2513aea631c7272c6d650d41ef40
Required sole parent of 9403e37: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1
```

- 开始前 main/source 身份、source 分支、HEAD、唯一父提交和洁净度必须精确匹配；不符立即停止。Reviewer 发现 P1 后停止，
  没有 Reviewer evidence commit；不得伪造或引用任何 Reviewer SHA。
- TASK-014 保持 `IN_PROGRESS / No-Go`，TASK-014B6 保持 `IN_PROGRESS`；Correction 1 不构成真实 B-1 成功、真实服务验证或发布批准。

## P1 与唯一允许范围

P1：未知目录 `INVALID_RESPONSE` fallback 仍输出旧 B3 `directory_unknown_invalid_response`，但 ADR-017 固定词表要求
`directory_shape_unknown`。

只可修改：

1. `src/youtube_intel/public_subtitle_smoke.py`
2. `tests/integration/test_public_subtitle_smoke.py`
3. `handoffs/TASK-014.md`

- 所有未知目录 `INVALID_RESPONSE` 必须只输出精确固定码 `directory_shape_unknown`，并新增回归，确认安全 stdout 与 JSONL
  `directory_diagnostic` 没有旧 fallback、动态值或泄漏。
- 不得修改 ADR-017 的既有七类 vocabulary、Provider、CLI、`logging.py`、依赖、锁文件、Schema/migration、默认配置、
  解析接受面、B-1 evidence、发布状态或任何其他路径。默认/directory-only 计数、退出码、临时根、ID 上限、无重试、
  零业务记录和所有 fail-closed 边界必须不变。

## 唯一离线检查

仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止；不得运行其他 `uv` 命令、安装或替代环境。仅在已有离线 `.venv` 可用时，才可按序运行：

```text
.venv/bin/pytest tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 绝对禁止与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、
  OpenAI、付费调用、push、合并、source 清理、测试/检查外的产品命令和 `.codebase-memory` 工件。
- 完成时只创建一个包含三条允许路径的 Correction 1 commit，追加 handoff，报告 SHA 与实际检查；不得自行 `IN_REVIEW`、
  `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。后续必须由新的独立 Reviewer 审查。
