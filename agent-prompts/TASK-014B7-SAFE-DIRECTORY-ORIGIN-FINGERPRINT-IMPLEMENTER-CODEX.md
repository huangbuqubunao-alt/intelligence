# TASK-014B7 — 字幕目录安全来源与结构指纹 Implementer

你是 TASK-014B7 的 Codex Implementer。只在固定 worktree 实现 ADR-018 的有限、无值目录来源与结构指纹；不得修复真实兼容性、
放宽解析、修改控制面或启动真实资源。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint
Role: Implementer
Agent: Codex
Implementation baseline: main@5b7dcca2ba9bd9e52e254a8944e584542838e24b
Worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Branch: codex/task-014b7-safe-directory-origin-fingerprint
Required source HEAD: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Read-only failure evidence: 17bfe9062677f3b3117df4dd192848d27690541c (must not merge, rewrite, or call passing)
Reuse decision: DIRECT — integrated subtitle Adapter, ADR-015 directory_diagnostic, B4 directory-only, B5 safe summary, ADR-017 B6 diagnostics, existing JsonlLogger, and offline fixture/integration tests; no dependency or third-party code change
```

- 开始前 source 分支、HEAD 和洁净度必须精确匹配；不符立即停止。`17bfe906…` 仅可只读引用为失败 evidence，不得 merge、
  cherry-pick、rebase、reset、修改或用来执行真实资源。
- TASK-014 保持 `IN_PROGRESS / No-Go`，TASK-014B7 保持 `IN_PROGRESS / Codex`；离线实现不构成真实 B-1 成功、真实服务验证或发行批准。

## 唯一允许范围与契约

只可修改：

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/fixtures/subtitles/` 下一个新增的脱敏指纹 fixture
4. `tests/integration/test_subtitle_provider.py`
5. `tests/integration/test_public_subtitle_smoke.py`
6. `handoffs/TASK-014.md`

仅在目录阶段最终为 `INVALID_RESPONSE` 时，保留 ADR-017 原有 `directory_diagnostic` 并可仅向既有安全 stdout 摘要/JSONL
`safe_message` 附加下列可选、固定、无值标签：

```text
directory_origin_extractor
directory_origin_decode
directory_origin_mapping
directory_origin_unknown

directory_fingerprint_top_level_not_mapping
directory_fingerprint_subtitle_bucket_missing_or_not_mapping
directory_fingerprint_language_bucket_missing_or_not_sequence
directory_fingerprint_track_entry_not_mapping
directory_fingerprint_required_field_missing
directory_fingerprint_unknown
```

- 标签只能表示已命中的安全本地边界；无可靠安全分类时使用相应 `*_unknown` 或省略。不得新增 B6 code、替换 B6 code、字段名、字段值、
  URL、字幕正文、标题、语言、轨道名、路径、原始异常、Cookie、token、payload、用户数据或凭据形状；不得新增 JSONL schema/字段、
  `logging.py`、CLI 参数、配置或 Provider 元数据。
- 默认与 directory-only 的读取、退出码、临时根、1--3 唯一 ID、无重试、零业务记录、非 smoke/全局配置拒绝与所有 fail-closed
  边界必须保持不变。不得扩大目录解析接受面或增加兼容规则；真实验证等待独立审查后的单独授权。
- 禁止依赖/锁文件、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或任何其他路径。

## 唯一离线检查

Implementer 仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止；不得运行其他 `uv` 命令、安装或替代环境。仅在已有离线 `.venv` 可用时，才可按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 绝对禁止与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、
  OpenAI、付费调用、push、合并、source 清理、测试/检查外的产品命令和 `.codebase-memory` 工件。
- 完成时只创建一个包含允许路径的 Implementer commit，追加 handoff，报告 SHA 与实际检查；不得修改任务/状态/ADR/prompt，不得
  自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
