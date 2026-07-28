# TASK-014B4：受限 directory-only 公开字幕目录 smoke

- Status: `READY`
- Assignee: `Codex Implementer（本控制面不启动）`
- Reviewer: `全新独立 Codex Reviewer（Implementer 提交后再分配）`
- 依赖：TASK-014B0 `DONE`、TASK-014B2 `DONE`、TASK-014B3 `DONE`、ADR-016
- 基线：`main@bdf2bf2adeb337b61747d869fa91619e3163a298`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b4-directory-only-smoke`
- Branch：`codex/task-014b4-directory-only-smoke`
- Reuse decision：`DIRECT` — 既有锁定 yt-dlp Adapter、`PublicSubtitleSmoke`、CLI、
  `ProviderCallMetadata`、`JsonlLogger` 和离线 Fake/integration 基础设施；不新增依赖或复制第三方代码。

## 目标

实现 ADR-016：为既有 `smoke-public-subtitles` 增加受限 `--directory-only` 模式。该模式对每个
目标只执行一次元数据读取和一次字幕目录映射，成功时也必须零正文读取；目录 `INVALID_RESPONSE`
继续仅以 ADR-015 的固定、脱敏 `directory_diagnostic` 分类审计。

## 控制面与隔离

- 本任务唯一 source 为上述 worktree/branch。开始实施前必须核验该分支上的控制面 HEAD 干净，且其唯一父提交为
  `bdf2bf2adeb337b61747d869fa91619e3163a298`。
- `/Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-diagnostic` 仅为未执行的历史诊断
  worktree；禁止访问、修改、合并、清理或复用。
- 本任务的 ADR、任务卡、实施包和状态记录由本控制面提交创建；Implementer 不得再改写这些控制面资料。

## Implementer 最小允许范围

1. `src/youtube_intel/cli.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_operations.py`（只限 CLI 解析/拒绝路径所需的离线 Fake 覆盖）
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014B4.md`

不得修改 Provider Adapter、`logging.py`、domain/config、默认 CLI 行为、依赖、`uv.lock`、Schema/migration、
README、发布结论、B-1 evidence、任务状态或任何其他路径。

## 验收标准

- [ ] 只有 `smoke-public-subtitles --directory-only` 接受该标志；非 smoke 子命令拒绝该标志，且不构造
  runner/Adapter、不初始化临时根。
- [ ] directory-only 对每个合法目标恰为 `metadata=1 / enumerate=1 / read=0`；目录成功不读取正文，
  默认 smoke 仍为既有 `metadata=1 / enumerate=1 / read=1` 行为。
- [ ] 目录 `INVALID_RESPONSE` 在 directory-only 中仅写 ADR-015 白名单 `directory_diagnostic=<fixed-code>`；
  无新增 JSONL 字段、URL、标题、字段值、正文、Cookie、token、payload、异常文本或用户数据。
- [ ] directory-only 与全局配置参数组合必须在任何 runner/Adapter/临时根动作前被拒绝；既有 1--3 个唯一 ID、
  不存在绝对 temporary root、超限/重复 ID、无重试和 30 秒 timeout 边界保持有效。
- [ ] 离线 Fake 覆盖成功、目录失败、非 smoke 标志拒绝、全局配置拒绝、超限 ID 和默认模式回归；不触发网络、
  媒体、认证或真实资源。
- [ ] TASK-014 仍为 `IN_PROGRESS / No-Go`；离线实现通过不构成真实 B-1、发布批准或最终 Go。

## 允许的离线检查（仅在 Implementer 启动后）

仅在已有离线 `.venv` 可用时运行：

```text
.venv/bin/pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/cli.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/cli.py src/youtube_intel/public_subtitle_smoke.py
git diff --check
```

环境不可用或任一检查失败时停止并记录；禁止 `uv sync`、安装、下载、网络、真实 smoke 或替代入口。

## 红线与交付

- 禁止真实 YouTube/网络、媒体下载、ffmpeg、模型、Ollama、OpenAI、Cookie/登录/API key、真实 Vault/用户数据、
  付费调用、launchd、`.codebase-memory` 工件、重试和任何额外产品命令。
- Implementer 仅可创建一个包含允许路径的 commit，并交由新独立 Reviewer；不得自行 `ACCEPTED`、`DONE`、合并、push、
  启动 Reviewer 或真实验证。
