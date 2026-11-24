# TASK-014B7 — 字幕目录安全来源与结构指纹 P1 Correction 1 Implementer

你是 TASK-014B7 P1 Correction 1 的 Codex Implementer。只在固定 source 中移除唯一不合规 fixture，并以无值内存测试替身维持
ADR-018 覆盖；不得修改生产代码、放宽解析、修改控制面或启动真实资源。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint P1 Correction 1
Role: Implementer
Agent: Codex
Control-plane baseline: main@c25c2cfe0358259f66b36ebd8edb28372b5eab03
Worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Branch: codex/task-014b7-safe-directory-origin-fingerprint
Required source HEAD: 8d06197557de4ce92c2752f4a8ef74582a0efdca
Required sole parent of Correction 1: 8d06197557de4ce92c2752f4a8ef74582a0efdca
Required sole parent of original implementation: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017 B6 diagnostics, ADR-018 fixed labels, and offline integration tests; no dependency or third-party code change
```

- 开始前 source 分支、HEAD、双重父链和洁净度必须精确匹配；不符立即停止。原 Reviewer 发现 P1 后停止，未创建 evidence commit；不得伪造
  或引用不存在的 Reviewer SHA。
- TASK-014 保持 `IN_PROGRESS / No-Go`，TASK-014B7 保持 `IN_PROGRESS / Codex`；离线 Correction 不构成真实 B-1 成功、
  真实服务验证或发行批准。

## P1、唯一允许范围与契约

P1：`tests/fixtures/subtitles/directory_origin_fingerprint.json` 明文含目录响应字段名、字段值、语言值及 URL，违反 ADR-018。
用户已明确批准删除此唯一不合规 fixture。

Correction 1 只可修改：

1. 删除 `tests/fixtures/subtitles/directory_origin_fingerprint.json`
2. `tests/integration/test_subtitle_provider.py`
3. `tests/integration/test_public_subtitle_smoke.py`
4. `handoffs/TASK-014.md`

- 必须以无字段名、字段值、URL、标题、语言、轨道名、路径、原始异常、Cookie、token、payload 或用户数据的内存测试替身替代 fixture。
  保持或增强 ADR-018 四个固定 `directory_origin`、六个固定 `directory_fingerprint`、ADR-017 B6 `directory_diagnostic` 不变、
  目录 `INVALID_RESPONSE` enumerate=`1`/read=`0`、正文 `INVALID_RESPONSE` 无 origin/fingerprint、stdout/stderr/JSONL
  无泄漏的断言覆盖。
- 严禁修改任何生产代码、依赖、`uv.lock`、Schema/migration、CLI、`logging.py`、配置、解析接受面、默认/directory-only 计数、退出码、
  临时根、ID 上限、无重试、零业务记录、fail-closed 边界或真实资源权限。

## 唯一离线检查

Implementer 仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止；不得运行其他 `uv` 命令、安装或替代环境。仅在已有离线 `.venv` 可用时，才可按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 绝对禁止与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、
  OpenAI、付费调用、push、合并、source 清理、测试/检查外的产品命令和 `.codebase-memory` 工件。
- 完成时只创建一个只含上述四项范围的 Correction commit，追加 handoff，报告 SHA 与实际检查；不得修改任务/状态/ADR/prompt，不得自行
  `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
