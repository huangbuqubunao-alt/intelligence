# TASK-014B3 — 公开字幕目录兼容性诊断 Implementer

你是 TASK-014B3 的唯一 Codex Implementer。本包登记一项已批准但尚未启动的离线实现分配；本包本身不启动实现。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`docs/decisions/ADR-015-public-subtitle-directory-diagnostics.md`、`tasks/TASK-014B3-public-subtitle-directory-diagnostics.md`、`tasks/README.md`、`docs/operations.md`、B-1 Scout 报告、B-1 evidence 与本包。若任一边界冲突，停止并报告。

## 固定分配

```text
Task: TASK-014B3 — public subtitle directory compatibility diagnostics
Role: Implementer
Agent: Codex
Base: main@371788d2a6c9c42f20ebaed93da7a021f0febeb0
Worktree: /Users/hua/Documents/yia-worktrees/task-014b3-public-subtitle-diagnostics
Branch: codex/task-014b3-public-subtitle-diagnostics
Reviewer: 全新独立 Codex Reviewer（本包不启动）
Reuse decision: DIRECT — existing yt-dlp Adapter, ProviderCallMetadata, JsonlLogger, public smoke, and offline fixtures/tests; no new dependency or copied third-party code
```

- 开始前 source HEAD 必须精确为 `371788d2a6c9c42f20ebaed93da7a021f0febeb0` 且工作树干净。
- B-1 evidence `9acab5d…` 是真实 smoke `FAIL`，只证明目录映射前失败；不得合并、改写为成功、重新执行网络或从中复制原始数据。
- TASK-014 始终为 `IN_PROGRESS / No-Go`。B3 离线通过不构成真实兼容性、发布批准或最终 Go。

## 唯一允许范围

只可修改：

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `tests/fixtures/subtitles/**`（仅脱敏目录形状 fixture）
6. `handoffs/TASK-014B3.md`

实现 ADR-015 的固定诊断 code：仅在目录枚举的 `INVALID_RESPONSE` 时，从 Adapter 的既有 diagnostics 向 smoke 的既有
`safe_message` 传递 `directory_diagnostic=<fixed-code>`。不新增任意 JSONL 字段，不记录 URL、标题、正文、字段值、
Cookie、token、完整 payload、异常文本或用户数据；无法可靠分类时必须使用固定 unknown code。

不得修改 URL allowlist、HTTPS/端口/凭据/fragment 拒绝、身份检查、语言/条目类型、长度/数量上限、格式限制、调用顺序、
默认 CLI、参数、退出码、临时根边界、Schema/migration、依赖/锁文件或 B-1 evidence。

## 检查和禁止项

- 只在预先存在的批准离线环境中运行聚焦 pytest、Ruff、mypy 与 `git diff --check`；环境不可用立即停止报告，禁止
  `uv sync`、安装、下载、锁文件/依赖操作。
- 禁止网络、YouTube、真实 smoke、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、OpenAI、
  付费调用、launchd、`.codebase-memory` 工件、重试和任何真实资源。
- 完成时仅创建一个允许路径的 commit，报告 SHA 和离线证据，交由全新独立 Reviewer；不得自行 `ACCEPTED`/`DONE`、合并、
  push、启动 Reviewer 或真实验证。
