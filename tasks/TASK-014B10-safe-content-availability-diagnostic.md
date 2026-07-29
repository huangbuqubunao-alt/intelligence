# TASK-014B10：安全内容可用性诊断

- Status: `IN_PROGRESS`
- Assignee: `Codex Implementer（已分配，尚未启动）`
- Reviewer: `待独立 Codex Reviewer 授权`
- 依赖：TASK-014B4/B5/B6/B7/B8 `DONE`、ADR-020 `Accepted`
- 实施基线：`main@6fd7b5cc3fae6466fb6181151513f4854d196683`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic`
- Branch：`codex/task-014b10-safe-content-availability-diagnostic`
- Reuse decision：`DIRECT` — 既有锁定 subtitle Adapter、B4 directory-only、B5 安全摘要、ADR-015--ADR-019 固定诊断、JsonlLogger
  safe_message 与离线 integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

三个不同公开视频均在 metadata/enumerate 后、正文读取前以 `CONTENT_UNAVAILABLE` 停止。B9 evidence
`bd770ef9d212ebe75689b8f33145bf2556fe93c2` 仅是未合并的只读失败证据，不得合并、修改、清理或写成成功。B10 不再选择或验证
更多视频，而是在既有受限 directory-only smoke 的安全出口增加固定、无敏感值的可用性来源分类，帮助区分视频不可用、访问环境受限、
提取器兼容性不足或无法安全确定。

## 冻结契约

- 仅当 directory-only 受限路径最终安全码为 `CONTENT_UNAVAILABLE` 且正文 `read=0` 时，可在既有安全 stdout 摘要与既有 JSONL
  `safe_message` 输出一个 ADR-020 固定 `content_availability` code。
- 词表严格且仅为 `content_availability_video_unavailable`、`content_availability_environment_restricted`、
  `content_availability_extractor_compatibility`、`content_availability_unknown`。前三者只可由既有本地无值内部状态/固定映射分支选择；
  无法安全判定时必须为 unknown。
- 不新增 JSONL schema 字段、`logging.py`、Provider metadata、CLI 参数、配置、Schema/migration、依赖或锁文件。不得改变退出码、
  重试、计数、默认 smoke 的一次正文读取、临时根、ID 上限、零业务记录、认证或 fail-closed 边界。
- ADR-015--ADR-019 的 `INVALID_RESPONSE` 诊断和词表保持不变；默认 smoke、成功、其他错误码、任何正文读取或不可靠分类不得输出
  availability code。不得扩大字幕解析接受面或增加兼容规则。
- 禁止 URL、标题、语言、轨道、字段名/字段值、原始响应、异常原文、路径、Cookie、token、payload、用户数据或凭据。测试只能使用无值
  内部状态/替身；不得新增或恢复真实或结构化目录 fixture。
- TASK-014 始终 `IN_PROGRESS / No-Go`；B10 只帮助决定下一步，不构成真实验证通过、真实服务验证、发行批准或最终 Go。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

最终 Diff 可以是上述允许范围的最小子集；不得为满足文档制造无关改动。不得修改 fixture 路径、依赖、`uv.lock`、Schema/migration、
`logging.py`、默认 CLI、配置、认证边界、发布状态、B-1/B9 evidence 或任何其他路径。

## 离线验收与交付

- 离线回归必须覆盖四个固定 classification 与 unknown 回退；stdout、stderr、JSONL 无敏感材料；directory-only 维持 `1/1/0`，
  默认 smoke 保持一次正文读取，B6/B7/B8、CLI 和全部 fail-closed 边界不退化。
- Implementer 首个产品提交必须以 `6fd7b5cc3fae6466fb6181151513f4854d196683` 为唯一父提交。控制面文档不进入 source；完成后由全新独立
  Reviewer 审查。
- 仅可先运行一次 `uv sync --locked --offline`；缓存缺失、锁文件变化、下载/网络迹象或失败立即停止。仅在已有离线 `.venv` 可用时，允许按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、合并、source 清理、测试/检查外产品命令与 `.codebase-memory` 工件。完成时只创建一个允许路径内的 Implementer
  commit 并追加 handoff；不得自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
