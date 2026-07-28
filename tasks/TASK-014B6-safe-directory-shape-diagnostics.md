# TASK-014B6：安全字幕目录结构诊断

- Status: `IN_REVIEW`
- Assignee: `独立 Codex Reviewer（已授权，尚未启动）`
- Reviewer: `独立 Codex Reviewer`
- 依赖：TASK-014B3 `DONE`、TASK-014B4 `DONE`、TASK-014B5 `DONE`、ADR-017 `Accepted`
- 实施基线：`main@7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics`
- Branch：`codex/task-014b6-safe-directory-shape-diagnostics`
- 当前受审 source：`9403e37eedbd2513aea631c7272c6d650d41ef40`（唯一父
  `7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`）
- Reuse decision：`DIRECT` — 既有锁定的 subtitle Adapter、ADR-015 `directory_diagnostic`、B4 directory-only、B5 安全摘要、JsonlLogger 与离线 fixture/integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

未合并的 B-1 auditable evidence `c7a3f403c910ab8e50e74f08b1c5ead057a5e4fa` 仅作为只读失败 evidence；不得合并、重写、重跑或写成通过。
实现 ADR-017 的有限、固定、无值目录结构 code，使目录 `INVALID_RESPONSE` 可经既有安全摘要/JSONL 审计，而不保存响应内容或放宽解析。

## 冻结契约

- 仅为目录 `INVALID_RESPONSE` 产生 ADR-017 的固定 code：缺失、非对象、非列表、空列表、不支持条目形状、提取器目录错误或未知。
- 禁止字段值、URL、字幕正文、标题、语言、轨道名称、路径、原始异常、Cookie、token、payload、用户数据或凭据形状。
- 默认和 directory-only 的读取/退出码/临时根/ID 上限/无重试/零业务记录/fail-closed 边界保持不变；不得因此扩大目录解析接受面。
- 兼容修复必须等待独立审查和新的真实授权。TASK-014 始终为 `IN_PROGRESS / No-Go`；B6 离线完成不构成 B-1 成功、真实服务验证或发布批准。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `tests/fixtures/subtitles/` 下一个新增的脱敏结构 fixture
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

不得修改依赖、`uv.lock`、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或任何其他路径。

## 审查控制面

- 完整产品 Diff `7983bf5…...9403e37…` 严格为 `src/youtube_intel/providers/subtitles.py`、
  `tests/fixtures/subtitles/directory_shape_diagnostics.json`、两份 integration test 与 `handoffs/TASK-014.md`。Reviewer
  只能在该 source 追加 `handoffs/TASK-014.md` 的审查 evidence；不得修改产品、fixture、任务/状态文档或 prompt。
- Reviewer 必须审查 ADR-017 七种固定、无值目录结构分类、未知 fallback、既有安全 stdout/JSONL 出口与不扩大解析
  接受面的负向回归；独立验证 stdout/stderr/JSONL 与 fixture 不泄露 URL、正文、标题、语言、轨道名、字段值、路径、原始异常、
  Cookie、token、payload 或用户数据。
- 默认/directory-only 计数、退出码、CLI 边界、临时根、ID 上限、无重试、零业务记录和 fail-closed 边界必须保持不变。

## 验收与离线检查

- 离线 fixture/test 覆盖 ADR-017 的每个固定、无值 code，以及未知回退；断言 stdout/JSONL 只使用既有安全出口，不含禁止内容。
- 回归默认一次正文读取、directory-only 1/1/0、退出码、临时根、ID 上限、无重试、零业务记录、CLI 拒绝和 fail-closed 边界。
- Implementer 仅可先运行一次 `uv sync --locked --offline`；缓存缺失、下载/网络迹象、锁文件变化或失败立即停止。
- 仅在已有离线 `.venv` 可用时，允许按任务实际范围运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 红线与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、合并、source 清理和任何额外产品命令。
- 完成时只提交上述允许路径的一个 Implementer commit，追加 `handoffs/TASK-014.md` 并报告 SHA；不得自行 `ACCEPTED`、`DONE`、
  合并、push 或启动真实验证。
