# TASK-014B8：受限键名级字幕目录诊断

- Status: `IN_PROGRESS / Codex`
- Assignee: `Codex Implementer`
- 依赖：TASK-014B3/B4/B5/B6/B7 `DONE`、ADR-019 `Accepted`
- 实施基线：`main@43f2c748c43215facb231f76a0c93ac45d350657`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b8-restricted-directory-keyname-diagnostic`
- Branch：`codex/task-014b8-restricted-directory-keyname-diagnostic`
- Required source HEAD: `43f2c748c43215facb231f76a0c93ac45d350657`
- Reuse decision：`DIRECT` — 既有 subtitle Adapter、B4 directory-only、B5 安全摘要、ADR-017/ADR-018 固定分类及离线 integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

未合并 B-1 B7 evidence `8f5dfce33ac77a45800f4ff53ff6e7054d8f68b0` 仅作只读失败 evidence；不得合并、重写、重跑或写成通过。实现 ADR-019 的单次、受限键名例外：仅在目录映射 `unknown` 边界向既有安全摘要提供可审计且无值的键名集合，不修复真实兼容性、不扩大解析。

## 冻结契约

- 仅同时满足 directory-only、目录 `INVALID_RESPONSE`、`directory_origin_mapping`、`directory_fingerprint_unknown` 且 `read=0` 时，可附加可选 `directory_key_names`。
- 只能输出完整通过 `[A-Za-z][A-Za-z0-9_]{0,63}` 的直接映射键名：去重、稳定 ASCII 字典序、最多 16 项。任一候选不合格、超过上限或候选集不可靠时，整个字段必须省略；不得截断、部分输出、哈希、替换或递归读取值。
- 禁止字段值、URL、正文、标题、语言值、轨道值、路径、原始异常、Cookie、token、payload、用户数据或凭据。仅可用合成安全键名覆盖允许/拒绝/上限；不得加入真实目录 fixture、URL、身份、语言、轨道或字段值。
- B6/B7 诊断与词表、默认/directory-only 计数、退出码、CLI、临时根、ID 上限、无重试、零业务记录与 fail-closed 边界必须不变；不得扩大目录解析接受面、增加兼容规则或真实资源权限。
- TASK-014 始终 `IN_PROGRESS / No-Go`；B8 不构成真实 B-1 成功、真实服务验证或发行批准。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

不得修改依赖、`uv.lock`、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence、fixture 路径或任何其他路径。

## 唯一离线检查

开始前核验 source 分支、HEAD 和洁净度；不符立即停止。Implementer 仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止。只有已有离线 `.venv` 可用时才可按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 红线与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、OpenAI、付费调用、push、合并、source 清理、测试/检查外产品命令与 `.codebase-memory` 工件。
- 只创建一个仅含允许路径的 Implementer commit，并追加 `handoffs/TASK-014.md`。不得改任务/状态/ADR/prompt，不得自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
