# TASK-014 Phase B-1 — Codex Smoke Executor（公开 YouTube 字幕 smoke）

你是 TASK-014 Phase B-1 的唯一 Codex Smoke Executor。本授权包登记未来单次真实资源 smoke 的严格边界；
它本身不启动 Executor。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、
`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、
`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/ACCEPTANCE_REPORT.md`、
`docs/operations.md`、Phase A Implementer/Reviewer 包与本包。若文件、实际 CLI 配置或授权边界冲突，停止并报告。

## 固定分配

```text
Task: TASK-014 Phase B-1 — Final public YouTube subtitle smoke execution
Role: Smoke Executor
Agent: Codex
Control-plane baseline: main@3165009df00c54f62c9b92a8f154bfd7ed664bea
Worktree: /Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1-final
Branch: codex/task-014-release-readiness-phase-b1-final
Reviewer: 全新独立 Codex Reviewer（本包不启动）
Reuse decision: DIRECT — 已锁定的 yt-dlp Adapter、项目 CLI 与 Python/Git 文本资料；不新增或复制第三方代码
```

旧 `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1` 建立在 B0 合并前主线；不得访问、修改、
合并、cherry-pick 或复用其中的 blocker evidence。旧
`/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-b1-execution` 建立在 Phase A 合并前主线；
同样不得访问、修改、合并、清理或复用。只可使用本 worktree 中已整合的 `smoke-public-subtitles` 入口。

## 产品目标与完成标准

只对 2–3 个稳定官方频道的公开视频执行一次低频 smoke，确认已批准 Adapter 在真实公开资源上能够：

1. 发现视频并读取元数据；
2. 发现字幕轨道并读取仅本次选中的字幕正文；
3. 将每个目标的选择理由、公开 URL/视频 ID、频道归属、时间、结果、错误类别（如有）、未执行项及停止原因记录为
   可审计证据。

成功仅是该受控 smoke 的结果，不是发行批准、法律结论、严格 exactly-once 证明、风险接受或最终 Go。任务整体始终为
`IN_PROGRESS` / `No-Go`；`mutagen` GPL 分发结论、`o200k_base.tiktoken` 文件级归属/NOTICE、真实 Vault 边界、
at-most-once best-effort 风险签署与 PO/TL/QA 最终 Go-No-Go 继续未关闭。

## 精确资源边界

- 只选 2–3 个稳定官方频道的公开公开视频；选择前记录官方频道归属和稳定性理由。若无法证实公开视频/官方归属，
  不调用该目标，改记为未执行并停止，不扩展候选池或高频重试。
- 只允许元数据、字幕目录与选中字幕正文读取；不得下载媒体/音频/视频、调用 ffmpeg、Whisper 或任何模型。
- 全部运行状态必须位于本次新建、独立的临时 SQLite、DATA 与测试 Vault 中；不得读取、写入、列出或探测真实 Vault、
  用户笔记、用户数据、既有 `data/`、既有 `logs/` 或任何生产目录。测试 Vault 必须为空，且不得含用户内容。
- 不登录、不使用 Cookie、浏览器 profile、API key、`.env`、环境变量中的凭据、Keychain 或任何秘密；不得调用
  OpenAI、Ollama、付费 API、launchd 或远程模型。
- 单次运行：每一已选目标最多一次正常尝试；禁止 `retry` 命令、循环重试、并发扇出或为了成功而替换更多目标。任何
  认证提示、付费墙、非公开内容、速率限制、媒体下载倾向、配置要求越界、意外模型/ffmpeg/云/Vault 调用或安全边界
  失败，都必须立即停止对应目标并记录，不规避。

## 唯一允许写入范围

仅可在本 worktree 修改或新建以下路径：

1. `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-PUBLIC-YOUTUBE.md`（本次 smoke 证据、目标选择理由与未执行项）
2. `docs/RELEASE_CHECKLIST.md`（仅追加/建立 Phase B-1 记录；不得改写其他发布门禁）
3. `handoffs/TASK-014.md`（本次命令、临时目录边界、结果、停止条件与红线核验）

当前 main 基线已包含 Phase A 的发行资料；只可对既有发布检查表追加与本次 B-1 直接相关的最小记录，
不得改写 README、SBOM、NOTICE、smoke 矩阵或其他发行资料。不得修改产品代码、测试、配置、
依赖、锁文件、Schema/migration、任务状态、控制面或项目自身 `LICENSE`。

## 执行与证据要求

- 在执行前记录最多 3 个确切目标及选择理由；使用现有批准依赖和项目入口，只允许完成本包所列元数据与字幕读取。
  若现有 CLI/配置不能把调用限定在这些范围内，先停止并报告 `DECISION NEEDED`，不得通过修改代码、配置或调用更宽
  的处理流程来绕过。
- 使用本次新建的临时配置与 SQLite/DATA/测试 Vault；不得将其路径、字幕正文、任何凭据或用户内容提交到仓库。
  证据只保留必要的公开视频 ID/URL、频道、时间、命令类别、状态、计数、错误类别和无敏感摘要。
- 运行结束后仅以 Git/文本检查核对允许路径、工作树状态和证据脱敏；不得运行测试、构建、安装、依赖解析/更新、
  lint、typecheck 或与目标无关的产品命令。
- 完成时创建一个只含允许路径的 commit，报告 SHA，交给全新独立 Reviewer；不得自行设为 `ACCEPTED`/`DONE`、
  合并、push、删除真实文件或启动 Reviewer。

## 绝对禁止

- 不增加目标到 3 个以上，不下载媒体，不调用 ffmpeg、Whisper、模型、Ollama、OpenAI、付费服务或 launchd。
- 不读取或使用登录、Cookie、API key、真实 Vault、真实用户笔记、用户数据、`.env`、Keychain 或其他凭据。
- 不改产品代码、依赖、锁、Schema/migration、测试、任务状态、控制面、项目自身 LICENSE 或发布分发结论。
- 不发布、push、合并、rebase、reset、广泛清理或规避失败/认证/速率限制。
