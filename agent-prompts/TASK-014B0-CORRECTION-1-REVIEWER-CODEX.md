# TASK-014B0 Correction 1 — 独立 Codex Reviewer（受限字幕 smoke 配置输入拒绝）

你是 TASK-014B0 Correction 1 的独立 Codex Reviewer。本授权包只登记未来独立审查的边界；它本身不启动 Reviewer。
开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、
`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、
`tasks/TASK-014-release-readiness.md`、`tasks/TASK-014B0-restricted-public-subtitle-smoke-entry.md`、ADR-013、
原 Implementer/Reviewer/Correction 1 包、source `handoffs/TASK-014B0.md` 与本包。如任一文件冲突，停止并报告。

## 固定审查对象

```text
Task: TASK-014B0 Correction 1 — reject global configuration inputs for the restricted smoke entry
Role: Independent Reviewer
Agent: Codex Reviewer
Control-plane base: main@578a90d52c835f6b58bc58cd14f96ca228f7d64e
Only source worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b0-restricted-public-subtitle-smoke
Source branch: codex/task-014-phase-b0-restricted-public-subtitle-smoke
Source HEAD: cafcde82eaa032bfae3bcee8049ef60ebda6d650
Required sole parent: f8e336a8c3b09a8c0c0e5857148495f2cb2281aa
Required change range: f8e336a8c3b09a8c0c0e5857148495f2cb2281aa...cafcde82eaa032bfae3bcee8049ef60ebda6d650
Reuse decision: DIRECT — review the existing argparse surface, locked smoke runner, Python standard library and offline Fake tests; do not add or copy third-party code
```

## 唯一写入权限

只能向 source worktree 的既有 `handoffs/TASK-014B0.md` **追加** Correction 1 Reviewer 结论和证据。不得修改、替换或
格式化既有内容；不得修改 source 的任何其他路径或 main 控制面。审查 evidence 提交只能包含该 handoff 追加；不得创建
worktree/branch、项目自身 `LICENSE`、许可证文本、依赖或 Schema 变更。

审查开始时和追加 handoff 前后，都必须确认 source 仍指向固定 HEAD、唯一父提交正确、范围恰为以下三路径且工作树没有
无关变更：

1. `src/youtube_intel/cli.py`
2. `tests/integration/test_public_subtitle_smoke.py`
3. `handoffs/TASK-014B0.md`

先用 Git/文本核验：`git rev-parse`、`git log -1`、`git diff --name-status`、`git diff --check`、`git status --short` 及
相关源码、任务卡、ADR、锁文件元数据的 `git diff`/`rg`/`sed`。只允许离线 Fake 验证；不得联网、执行真实 B-1 smoke、
读取凭据/Cookie/真实 Vault 或用户数据。不得运行构建、安装、打包、模型/API、媒体或 ffmpeg 命令。

## 独立核验要求

独立审查完整 `base...HEAD` Diff、所有改动、Correction handoff 与 ADR-013。至少确认：

1. `--project-root`、`--settings`、`--channels` 的每一种均在 smoke 子命令前或后、分离值或 `--flag=value` 形式时
   fail-closed；退出必须发生在 `PublicSubtitleSmoke` runner、Adapter 或临时根的构造/初始化之前。离线 Fake 必须证明零
   Adapter 调用且目标临时根不存在。
2. 修复只作用于 `smoke-public-subtitles`；`check/process/retry/weekly/doctor` 的既有参数与默认 fail-closed 语义不变。
3. 输入仍仅是一个不存在的绝对临时根及 1–3 个互异显式视频 ID；无 channel/URL/playlist/discovery/YAML/环境/配置输入。
4. 仍是一次 metadata、一次字幕目录、一次选中正文读取，30 秒、无并发、无重试；正文只在内存中，JSONL 审计脱敏，
   临时根无 Pipeline/Job/ProviderCall/Artifact 业务记录。
5. 无登录、Cookie、API key、媒体下载、ffmpeg、Whisper、模型、Ollama、OpenAI、付费服务、launchd、真实 Vault/
   用户数据或 B-1 网络路径；无依赖、锁文件、Schema/migration、Provider Adapter、domain/config 或控制面变更。
6. handoff 的初始基线、实现 SHA、第一轮 REJECT evidence、Correction 1 SHA、状态和检查结果均与 Git 事实一致；不得
   保留 `pending`，不得把离线 Fake 误称为真实 smoke 或发布批准。

可在不联网的前提下，仅重跑 `tests/integration/test_public_subtitle_smoke.py` 的离线 Fake 验证及任务卡允许的静态 Git
检查；若环境不能证明其不访问真实资源，则不运行并记录为跳过。不得把 Implementer 自报的检查替代独立结果。

任何 P0/P1、范围错误、证据不一致或被放宽的安全边界均须 `REJECT`，提供 P 级、文件/行和最小修复建议；不得自行
修复。若通过，也仅为 Correction 1 离线审查 `APPROVE`，不构成真实 B-1 smoke、发布批准、法律结论、严格
exactly-once 证明、风险接受或 TASK-014 Go。

## 禁止事项

- 不发布、合并、push、rebase、reset、清理或删除任何真实文件。
- 不联网，不访问 YouTube、OpenAI、Ollama、ffmpeg、Whisper、launchd 或其他服务。
- 不读取 `.env`、环境变量值、凭据、Keychain、真实 Vault、SQLite、日志、缓存、媒体或用户数据。
- 不运行真实资源、真实 B-1 smoke、构建、安装、打包、模型/API 调用；不得修改 source、main、依赖、锁、Schema、
  Provider Adapter、任务状态、ADR、LICENSE 或 B-1 evidence，唯一例外是本包授权的 source handoff 追加。

## 审查交接

只在 `handoffs/TASK-014B0.md` 末尾追加：固定 base/source HEAD/parent、三路径和清洁度、依赖/Schema 无差异、静态与
离线 Fake 证据、明确未运行的命令/资源、所有 P0–P3 或“无 P0–P3”，以及 `APPROVE` 或 `REJECT`。追加后只可用 Git/文本
检查确认 handoff 是唯一 source 工作树改动；不得启动其他角色、改变任务状态或宣称任务完成。
