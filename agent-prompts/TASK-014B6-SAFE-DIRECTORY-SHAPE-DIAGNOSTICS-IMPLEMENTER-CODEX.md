# TASK-014B6 — 安全字幕目录结构诊断 Implementer

你是 TASK-014B6 的 Codex Implementer。只在固定 worktree 实现 ADR-017 的有限、无值目录结构诊断；不得修复真实兼容性、放宽解析、修改控制面或启动真实资源。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B6 — safe subtitle directory shape diagnostics
Role: Implementer
Agent: Codex
Implementation baseline: main@7983bf5bfa0ce08529d189a9ac07f41f042bc6a1
Worktree: /Users/developer/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics
Branch: codex/task-014b6-safe-directory-shape-diagnostics
Required source HEAD: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1
Read-only failure evidence: c7a3f403c910ab8e50e74f08b1c5ead057a5e4fa (must not merge, rewrite, or call passing)
Reuse decision: DIRECT — integrated subtitle Adapter, ADR-015 directory_diagnostic, B4 directory-only, B5 safe summary, existing JsonlLogger, and offline fixture/integration tests; no dependency or third-party code change
```

- 开始前 source 分支、HEAD 和洁净度必须精确匹配；不符立即停止。`c7a3f403…` 仅可只读引用为失败 evidence，不得 merge、cherry-pick、rebase、reset、修改或用来执行真实资源。
- TASK-014 保持 `IN_PROGRESS / No-Go`，TASK-014B6 保持 `IN_PROGRESS / Codex`；离线实现不构成真实 B-1 成功、真实服务验证或发布批准。

## 唯一允许范围与契约

只可修改：

1. `src/youtube_intel/providers/subtitles.py`
2. `tests/fixtures/subtitles/` 下一个新增的脱敏结构 fixture
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

仅在目录阶段最终为 `INVALID_RESPONSE` 时，生成 ADR-017 的一个固定、无值 code：

```text
directory_shape_missing
directory_shape_not_object
directory_shape_not_list
directory_shape_empty_list
directory_shape_unsupported_entry
directory_extractor_directory_error
directory_shape_unknown
```

- code 只描述安全校验分支；不得输出或保存字段值、URL、字幕正文、标题、语言、轨道名称、路径、原始异常、Cookie、token、payload、
  用户数据或凭据形状。只复用既有 `directory_diagnostic`、安全 stdout 摘要和 JSONL `safe_message`，不得新增 schema/字段。
- 默认与 directory-only 的读取、退出码、临时根、1--3 唯一 ID、无重试、零业务记录、非 smoke/全局配置拒绝与所有 fail-closed
  边界必须保持不变。不得扩大目录解析接受面；兼容修复等待独立审查和新的真实授权。
- 禁止依赖/锁文件、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或任何其他路径。

## 唯一离线检查

Implementer 仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止；不得运行其他 `uv` 命令、安装或替代环境。仅在已有离线 `.venv` 可用时，才可按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 绝对禁止与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、
  OpenAI、付费调用、push、合并、source 清理、测试/检查外的产品命令和 `.codebase-memory` 工件。
- 完成时只创建一个包含允许路径的 Implementer commit，追加 handoff，报告 SHA 与实际检查；不得修改任务/状态/ADR/prompt，不得
  自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
