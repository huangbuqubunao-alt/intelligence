# TASK-014B0 Correction 1 — Codex Implementer（受限字幕 smoke 配置输入拒绝）

你是 TASK-014B0 的原 Codex Implementer，只处理第一轮 Reviewer `REJECT` 的 Correction 1。本包只登记正式修复分配；
它本身不启动 Implementer。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、
`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、
`tasks/TASK-014-release-readiness.md`、`tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`、ADR-013、原 Implementer/
Reviewer 包、source `handoffs/TASK-014B0.md` 与本包。如任一文件冲突，停止并报告。

## 固定分配

```text
Task: TASK-014B0 Correction 1 — reject global configuration inputs for the restricted smoke entry
Role: Original Implementer
Agent: Codex
Control-plane base: main@40df8093fe67a8a0fe3bfe4175acbb42ede2286e
Only source worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke
Source branch: codex/task-014-phase-b0-restricted-public-subtitle-smoke
Correction base/source HEAD: f8e336a8c3b09a8c0c0e5857148495f2cb2281aa
Required sole parent of correction commit: f8e336a8c3b09a8c0c0e5857148495f2cb2281aa
First-review evidence: f8e336a8c3b09a8c0c0e5857148495f2cb2281aa (REJECT; P1 and P2)
Reuse decision: DIRECT — existing argparse surface, locked smoke runner, Python standard library and existing offline Fake tests; no new or copied third-party code
```

## Correction 1 目标

关闭以下已确认问题，且只关闭这些问题：

1. `smoke-public-subtitles` 必须拒绝顶层 `--project-root`、`--settings`、`--channels` 的任意出现位置和
   `--name=value` 形式；这些配置路径在任何 runner、Adapter 或临时根初始化前都必须以既有参数错误退出。
2. 更新 source handoff，使初始控制面/实现/review evidence/Correction 1 提交和状态均与 Git 事实一致，删除
   `pending` 占位；不得把离线 Fake 结果写成真实 B-1 smoke 或发布批准。

`smoke-public-subtitles` 仍且只能接受一个不存在的绝对 `--temporary-root` 与 1–3 个互异显式 `--video-id`。
不得改变现有 `check/process/retry/weekly/doctor` 的参数或默认 fail-closed 行为。

## 唯一允许修改范围

1. `src/youtube_intel/cli.py`
2. `tests/integration/test_public_subtitle_smoke.py`
3. `handoffs/TASK-014B0.md`

不得修改任何其他 source 路径，包括 `public_subtitle_smoke.py`、`test_operations.py`、`docs/operations.md`、Provider
Adapter、`state.py`、domain/config、Schema/migration、依赖、锁文件、任务/状态控制面、LICENSE 或 B-1 evidence。
范围不足时停止并报告 `DECISION NEEDED`。

## 必须保持的边界

- 一次 metadata、一次字幕目录、一次选中正文读取；固定 30 秒、无并发、无自动重试。
- 正文仅内存存在；不写 SQLite/DATA/JSONL/Vault/异常/证据；审计保持脱敏，且无 Pipeline/Job/ProviderCall/Artifact
  业务记录。
- 不读取配置、YAML、环境值、凭据、Cookie、Keychain、真实 Vault 或用户数据；不运行真实网络/B-1 smoke。
- 不下载媒体/音频/视频/缩略图，不调用 ffmpeg、Whisper、模型、Ollama、OpenAI、付费服务或 launchd。
- 不新增依赖，不改 Schema/migration、默认 CLI、Pipeline/Job/Repository 语义、发布状态或 Go/No-Go；不合并、push、
  rebase、reset、清理或启动 Reviewer。

## 离线验收与交付

只添加最小 Fake 断言，证明每个禁用全局选项（包括位置与 `=` 形式）均在 runner/Adapter/临时根前失败，同时保留
原 B0 离线边界。仅在后续正式启动的 Implementer 回合运行任务卡已有离线检查；不得联网。提交前核验
`f8e336…...HEAD` 严格只有三条授权路径、无依赖/Schema 改动、`git diff --check` 与工作树状态；填写 handoff 后
提交 Correction 1。不得自行将 TASK-014B0 标为 `IN_REVIEW`、`ACCEPTED` 或 `DONE`。
