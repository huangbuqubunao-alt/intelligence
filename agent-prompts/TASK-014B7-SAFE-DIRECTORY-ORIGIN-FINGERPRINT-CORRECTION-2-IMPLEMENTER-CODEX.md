# TASK-014B7 — 字幕目录安全来源与结构指纹 P1 Correction 2 Implementer

你是 TASK-014B7 P1 Correction 2 的 Codex Implementer。只实现最小、无值的 Adapter 内部状态分类接口，并移除测试源码中的受限数据；
不得改变解析接受面、控制面或启动真实资源。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint P1 Correction 2
Role: Implementer
Agent: Codex
Control-plane baseline: main@a3f874677dc090be0f99efe8485a4fec12120cf1
Worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Branch: codex/task-014b7-safe-directory-origin-fingerprint
Required source HEAD: 069e62ececada5152871fb7c626e64c146a270ad
Required sole parent of Correction 2: 069e62ececada5152871fb7c626e64c146a270ad
Required sole parent of Correction 1: 8d06197557de4ce92c2752f4a8ef74582a0efdca
Required sole parent of original implementation: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017 B6 diagnostics, ADR-018 fixed labels, and offline integration tests; no dependency or third-party code change
```

- 开始前 source 分支、HEAD、三重父链和洁净度必须精确匹配；不符立即停止。两位 Reviewer 都在发现 P1 后停止，均未创建 evidence commit；
  不得伪造或引用任何 Reviewer SHA。
- TASK-014 保持 `IN_PROGRESS / No-Go`，TASK-014B7 保持 `IN_PROGRESS / Codex`；离线 Correction 不构成真实 B-1 成功、
  真实服务验证或发行批准。

## P1、唯一允许范围与契约

P1：fixture 已删除，但测试源码仍内嵌受限字段值、URL 和身份值，违反 ADR-018。

Correction 2 只可修改：

1. `src/youtube_intel/providers/subtitles.py`
2. `tests/integration/test_subtitle_provider.py`
3. `tests/integration/test_public_subtitle_smoke.py`
4. `handoffs/TASK-014.md`

- 只允许最小内部拆分：原始目录结构的检查继续封装在 Adapter 内；供测试使用的“结构状态 → 固定安全分类”内部接口只接受无字段名、
  无字段值的枚举/类型状态。该接口不得成为新的 CLI、Provider、配置、logging、JSONL schema 或公共输出面。
- 测试和 handoff 不得含字段名、字段值、URL、语言、轨道名、身份值、原始响应、Cookie、token、payload 或用户数据。必须保持或增强
  ADR-018 四个 origin、六个 fingerprint、ADR-017 B6 diagnostic、目录 `INVALID_RESPONSE` enumerate=`1`/read=`0`、正文
  `INVALID_RESPONSE` 无 origin/fingerprint 及 stdout/stderr/JSONL 无泄漏断言。
- 已删除 fixture 不得恢复、替代或在任何路径重现。严禁改变解析接受面、CLI、`logging.py`、依赖、`uv.lock`、Schema/migration、配置、
  读取计数、退出码、默认/directory-only 行为、临时根、ID 上限、无重试、零业务记录、fail-closed 边界或真实资源权限。

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
- 完成时只创建一个只含上述四项范围的 Correction commit，追加 handoff，报告 SHA 与实际检查；不得修改任务/状态/ADR/prompt，不得自行
  `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
