# TASK-014B0 — Codex Implementer（受限公开字幕 smoke 组合入口）

你是 TASK-014B0 的唯一 Codex Implementer。本包只登记正式实施分配；它本身不启动 Implementer。开始前完整阅读
`AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、
`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、
`tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`、`docs/operations.md`、B-1 source 的
`be230490a5b5779c7f1eb1e46c0fd717055fc28c` evidence 与本包。若任一项冲突，停止并报告。

## 固定分配

```text
Task: TASK-014B0 — Restricted public subtitle smoke entry
Role: Implementer
Agent: Codex
Control-plane parent baseline: main@28223cc98f9da18fc877289231a92e240cc711d0
Worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke
Branch: codex/task-014-phase-b0-restricted-public-subtitle-smoke
Reviewer: 全新独立 Codex Reviewer（本包不启动）
Reuse decision: DIRECT — 已锁定 yt-dlp Adapter、SQLite migration、JsonlLogger、Python 标准库；不新增/复制第三方代码
```

## 交付契约

按 ADR-013 新增 `smoke-public-subtitles`。它只接受不存在的绝对 `--temporary-root` 与 1–3 个不同的
`--video-id`，不加载 YAML/环境/密钥。它在根内创建临时 SQLite、DATA、空测试 Vault 与日志目录，以 UUID4
run ID 写脱敏 JSONL；每个目标只能顺序执行一次 `fetch`、一次 `enumerate_tracks`、按既有
`rank_subtitle_candidates` 选择第一候选、一次 `read_track`。固定 HTTP timeout 为 30 秒、无重试、无并发。

选中字幕正文只能在内存中读取后丢弃；不得写入 SQLite/DATA/JSONL/Vault/异常/提交证据。不得创建 Pipeline、
Job、ProviderCall 或 Artifact 业务记录。`check/process/retry/weekly/doctor` 与默认 fail-closed 行为必须保持不变。

## 唯一允许修改范围

1. `src/youtube_intel/cli.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_operations.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `docs/operations.md`
6. `handoffs/TASK-014B0.md`

不得触及 B-1 source evidence，也不得修改 Provider Adapter、`state.py`、domain/config、Schema/migration、依赖、
锁文件、任务/状态控制面、LICENSE 或任何其他路径。

## 本阶段禁止事项

- 不联网，不运行真实 B-1 smoke，不查公开视频，不进行目标选择。
- 不读取 `.env`、环境变量值、Cookie、浏览器 profile、API key、Keychain、真实 Vault、用户笔记或用户数据。
- 不下载媒体/音频/视频/缩略图，不调用 ffmpeg、Whisper、模型、Ollama、OpenAI、付费服务或 launchd。
- 不新增依赖、修改 Schema/migration、默认 CLI/Pipeline/Job/Repository 语义、发布状态或 Go/No-Go。
- 不合并、push、rebase、reset、清理或启动 Reviewer。

## 交付和验证

仅用离线 Fake 覆盖：参数上限/唯一性/临时根、一次调用/无重试、失败映射、根隔离、正文不落盘不入日志、
SQLite 初始化无业务记录、默认命令 fail-closed 无回归和 Adapter 安全选项。运行任务卡列出的离线检查后，
只提交允许路径并填写 handoff；不得自行把 TASK-014 或 TASK-014B0 标为 `IN_REVIEW`、`ACCEPTED` 或 `DONE`。
