# TASK-014B8 — 受限键名级字幕目录诊断 Implementer

你是 TASK-014B8 的 Codex Implementer。只在固定 worktree 实现 ADR-019 的单次、受限、无值键名诊断；不得修复真实兼容性、放宽解析、修改控制面或启动真实资源。本包不启动 Implementer。

## 固定分配

```text
Task: TASK-014B8 — restricted directory keyname diagnostic
Role: Implementer
Agent: Codex
Implementation baseline: main@43f2c748c43215facb231f76a0c93ac45d350657
Worktree: /Users/developer/Documents/yia-worktrees/task-014b8-restricted-directory-keyname-diagnostic
Branch: codex/task-014b8-restricted-directory-keyname-diagnostic
Required source HEAD: 43f2c748c43215facb231f76a0c93ac45d350657
Read-only failure evidence: 8f5dfce33ac77a45800f4ff53ff6e7054d8f68b0 (must not merge, rewrite, rerun, or call passing)
Reuse decision: DIRECT — integrated subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017/ADR-018 diagnostics, and offline integration tests; no dependency or third-party code change
```

开始前 source 分支、HEAD 和洁净度必须精确匹配；不符立即停止。TASK-014 继续 `IN_PROGRESS / No-Go`，TASK-014B8 保持 `IN_PROGRESS / Codex`；离线实现不构成真实 B-1 成功、真实服务验证或发行批准。

## 唯一允许范围与契约

只可修改：

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

仅当 directory-only、目录阶段最终为 `INVALID_RESPONSE`、`directory_origin=directory_origin_mapping`、`directory_fingerprint=directory_fingerprint_unknown` 且正文 `read=0` 同时成立时，既有安全 stdout 摘要/JSONL `safe_message` 才可附加 `directory_key_names`。

- 只检查 Adapter 目录映射边界的直接键名，绝不递归或读取值。每项必须完整匹配 `[A-Za-z][A-Za-z0-9_]{0,63}`；去重后稳定 ASCII 字典序，最多 16 项。
- 任一候选不合格、超过 16 项或候选集不可靠时，整个字段必须省略；不得截断、部分输出、替换、哈希或记录拒绝项。
- 这是用户明确批准的唯一字段名例外。禁止字段值、URL、正文、标题、语言值、轨道值、路径、原始异常、Cookie、token、payload、用户数据或凭据；测试只能使用有限合成安全键名，不能引入真实目录 fixture、URL、身份、语言、轨道或字段值。
- B6/B7 固定诊断、default/directory-only 计数、退出码、CLI、临时根、ID 上限、无重试、零业务记录与 fail-closed 边界必须保持不变。不得扩大解析接受面、增加兼容规则、修改依赖/锁、Schema、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或其他路径。

## 唯一离线检查

仅可先运行一次：

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

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、OpenAI、付费调用、push、合并、source 清理、测试/检查外产品命令和 `.codebase-memory` 工件。
- 完成时只创建一个仅含允许路径的 Implementer commit，追加 handoff，报告 SHA 与实际检查；不得修改任务/状态/ADR/prompt，不得自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
