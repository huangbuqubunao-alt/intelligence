# TASK-014B4 — 受限 directory-only 公开字幕 smoke Implementer

你是 TASK-014B4 的唯一 Codex Implementer。本包登记已批准但尚未启动的离线实现分配；本包本身不启动实现、测试、`uv`、网络或真实 smoke。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`docs/decisions/ADR-013-restricted-public-subtitle-smoke-entry.md`、`docs/decisions/ADR-015-public-subtitle-directory-diagnostics.md`、`docs/decisions/ADR-016-directory-only-public-subtitle-smoke.md`、`tasks/TASK-014-release-readiness.md`、`tasks/TASK-014B4-directory-only-public-subtitle-smoke.md`、`tasks/README.md`、`docs/operations.md`、B-1 evidence 与本包。边界冲突时停止并报告。

## 固定分配

```text
Task: TASK-014B4 — restricted directory-only public subtitle smoke
Role: Implementer
Agent: Codex
Architecture lineage base: main@bdf2bf2adeb337b61747d869fa91619e3163a298
B4 allocation control commit: ccc747800b59e2bacc918f1e7b81e065b1520d9a
Implementation base: bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d
Worktree: /Users/developer/Documents/yia-worktrees/task-014b4-directory-only-smoke
Branch: codex/task-014b4-directory-only-smoke
Reviewer: 全新独立 Codex Reviewer（本包不启动）
Reuse decision: DIRECT — existing CLI, PublicSubtitleSmoke, locked yt-dlp Adapter, ProviderCallMetadata, JsonlLogger, and offline Fake/integration tests; no dependency or copied third-party code
```

- 开始前 source HEAD 必须精确为 `bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d` 且工作树干净。
  Implementer 的首个产品提交必须以该提交为唯一父提交；实现与审查的产品 Diff 固定为
  `bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d...HEAD`。`bdf2bf2adeb337b61747d869fa91619e3163a298`
  仅是 B4 架构谱系基线，不是当前实施 HEAD 或产品 Diff 基线。
- source 不得对控制面文档进行暂存、提交或改动；本基线修正由独立控制面分支持有，不能写回 source。
- 禁止访问、修改、合并、清理或复用 `/Users/developer/Documents/yia-worktrees/task-014-phase-b1-directory-diagnostic`；它是未执行的
  历史诊断 worktree。
- B-1 evidence `9acab5d…` 是真实 smoke `FAIL`，不得合并、重写为成功或重新执行网络。TASK-014 始终为
  `IN_PROGRESS / No-Go`。

## 唯一允许范围

1. `src/youtube_intel/cli.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_operations.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014B4.md`

实现 ADR-016 的 `smoke-public-subtitles --directory-only`：该模式只执行每个目标一次 metadata 与一次
目录枚举，目录成功或失败都必须 `read_track_calls=0`。默认未带标志的 smoke 仍必须保持原先至多一份正文读取的行为。
目录 `INVALID_RESPONSE` 只复用 ADR-015 的固定 `directory_diagnostic=<code>` 通过既有 `safe_message` 输出；不增加 JSONL 字段，
不记录 URL、标题、字段值、正文、Cookie、token、payload、异常文本或用户数据。

必须拒绝 `--directory-only` 与非 smoke 子命令、smoke 路径中的 `--project-root`/`--settings`/`--channels`、超限或重复 ID，且在
拒绝时不得构造 runner/Adapter 或初始化临时根。不得改动 URL allowlist、HTTPS/端口/凭据/fragment 拒绝、身份/语言/结构/
长度/数量/格式校验、30 秒 timeout、无重试、默认 CLI 行为、临时根边界、Provider Adapter、依赖/锁文件或 Schema/migration。

## 检查与禁止项

- 仅在已有离线 `.venv` 可用时，运行任务卡列出的两份聚焦 pytest、Ruff、mypy 和 `git diff --check`。环境缺失或任一检查失败立即停止；禁止 `uv sync`、安装、下载或锁文件操作。
- 禁止真实 YouTube/网络、真实 smoke、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、OpenAI、
  付费调用、launchd、`.codebase-memory` 工件、重试和任何额外产品命令。
- 完成时只提交允许路径的一个 Implementer commit，更新 handoff 并报告 SHA；不得自行 `ACCEPTED`/`DONE`、合并、push、
  启动 Reviewer 或真实验证。
